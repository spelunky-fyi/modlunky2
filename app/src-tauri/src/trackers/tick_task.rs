//! Generic tick loop shared by every per-tracker task. Any concrete
//! tracker just calls `spawn` with its `TrackerTicker` instance +
//! payload/config watch pair; the loop itself, attach retry, and
//! payload dedupe are the same everywhere.
//!
//! Runs on `spawn_blocking` because the process reads are synchronous on
//! every backend (ReadProcessMemory on Windows, pread on Linux). The 16ms
//! tick + 1s attach backoff hit roughly one read per game frame while
//! keeping the not-attached path cheap.

use std::time::{Duration, Instant};

use ml2_mem::Spel2Process;
use ml2_trackers::chain_impl::inputs::ChainInputs;
use ml2_trackers::state::State;
use ml2_trackers::tracker::{TrackerContext, TrackerPayload, TrackerTicker};
use tokio::sync::{oneshot, watch};

const TICK_INTERVAL: Duration = Duration::from_millis(16);
const ATTACH_BACKOFF: Duration = Duration::from_secs(1);

/// How long to hold an attached process that isn't giving us readings.
///
/// The feedcode marker lands within a second or two of launch, so past this
/// the handle is almost certainly one that will never produce a reading at
/// all: the game exited while we held it, or `attach` caught Spel2.exe on its
/// way out and we are now reading a corpse. That is indistinguishable from a
/// slow launch here -- a dead process enumerates zero pages, and zero pages is
/// reported as `FeedcodeMissing` rather than as a read error.
///
/// Giving the handle up is the only thing that puts `process` back to `None`
/// and so returns the loop to its re-attach path. It costs nothing: the whole
/// point of this state is that there is no successful scan to throw away.
const STALE_HANDLE_GRACE: Duration = Duration::from_secs(5);

/// Gap between feedcode scans while waiting for the marker. Each miss walks
/// the game's whole committed address space, which is far too expensive to
/// repeat at `TICK_INTERVAL`; the marker isn't going to appear mid-frame
/// anyway.
const FEEDCODE_POLL: Duration = Duration::from_millis(250);

/// Decides when the tick loop gives up on the process it is holding.
///
/// Split out of the loop because this is the part with a load-bearing
/// invariant: **every** failure mode has to release the handle eventually.
/// `process` staying `Some` makes the re-attach path at the top of the loop
/// unreachable, so a state that holds on forever doesn't fail loudly, it just
/// leaves the tracker parked on "Spelunky 2 exited" for the rest of the
/// session. As a plain struct the rules are testable without a running game;
/// inline in the loop they were not.
#[derive(Debug, Default)]
struct AttachHealth {
    consecutive_read_errors: u32,
    /// When the handle last stopped producing readings.
    ///
    /// Deliberately cleared by success and by nothing else. Per-failure-mode
    /// counters are not enough on their own: a process on its way out can
    /// alternate between the two modes (a `/proc` map that sometimes fails to
    /// read and sometimes reads back empty), and if each mode resets the
    /// other's bookkeeping, neither ever reaches its limit and the handle is
    /// held forever. This deadline is the backstop that no failure can push
    /// back.
    unhealthy_since: Option<Instant>,
    /// Whether the most recent failure was a missing feedcode.
    scanning: bool,
}

impl AttachHealth {
    /// Three strikes and the handle drops. Small enough that recovery is
    /// quick, large enough that one torn read during a level transition
    /// doesn't cost the attach.
    const READ_ERROR_LIMIT: u32 = 3;

    /// A read succeeded, so the handle is good: forget any accumulated doubt.
    fn on_success(&mut self) {
        *self = Self::default();
    }

    /// The handle is live but the marker isn't readable yet. Returns whether
    /// to drop it.
    ///
    /// Normally this is a game still starting up, worth waiting out. But a
    /// dead process is indistinguishable from here, hence the deadline.
    fn on_feedcode_missing(&mut self, now: Instant) -> bool {
        self.consecutive_read_errors = 0;
        self.scanning = true;
        self.past_deadline(now)
    }

    /// A read failed outright. Returns whether to drop the handle.
    fn on_read_error(&mut self, now: Instant) -> bool {
        self.scanning = false;
        self.consecutive_read_errors += 1;
        self.consecutive_read_errors >= Self::READ_ERROR_LIMIT || self.past_deadline(now)
    }

    /// Starts the clock on the first failure after a healthy stretch, and
    /// reports whether it has run out.
    fn past_deadline(&mut self, now: Instant) -> bool {
        let since = *self.unhealthy_since.get_or_insert(now);
        now.duration_since(since) >= STALE_HANDLE_GRACE
    }

    /// Whether the last tick was a feedcode miss, so the loop can back off
    /// instead of rescanning the address space every frame.
    fn waiting_for_feedcode(&self) -> bool {
        self.scanning
    }
}

/// Why attaching to the game is failing, when the reason is something the user
/// can act on rather than just "the game isn't running".
///
/// A process-global slot, the same shape `log_buffer` and `toast_buffer` use,
/// because the tick tasks are spawned from a closure that has no `AppHandle`
/// or `AppState` to write through, and threading one down to them would touch
/// every layer in between for this one string.
///
/// In practice this only ever holds the Linux ptrace case: the game is running
/// but the kernel won't let us read it. Without surfacing that, the trackers
/// sit on "Waiting for Spelunky 2" forever while the game is plainly open,
/// which is impossible to diagnose from the UI.
fn attach_problem() -> &'static std::sync::Mutex<Option<String>> {
    static SLOT: std::sync::OnceLock<std::sync::Mutex<Option<String>>> = std::sync::OnceLock::new();
    SLOT.get_or_init(|| std::sync::Mutex::new(None))
}

fn set_attach_problem(problem: Option<String>) {
    if let Ok(mut guard) = attach_problem().lock() {
        *guard = problem;
    }
}

/// The current actionable attach failure, or `None` when there isn't one.
/// `None` also covers the ordinary "game isn't running" case, which the
/// trackers already communicate on their own.
pub fn current_attach_problem() -> Option<String> {
    attach_problem().lock().ok().and_then(|g| g.clone())
}

/// Spawn a tick loop for `tracker`. Returns immediately with a
/// `oneshot::Sender` the caller signals to shut the loop down.
///
/// - `payload_tx` receives every distinct payload the tracker emits.
///   Consecutive equal payloads are dropped (avoids WS + file writer
///   churn on the very common "nothing changed this frame" tick).
/// - `config_rx` is read at the top of every tick so the UI can
///   push new settings without stopping the task.
pub fn spawn<T: TrackerTicker>(
    mut tracker: T,
    payload_tx: watch::Sender<TrackerPayload>,
    config_rx: watch::Receiver<T::Config>,
) -> oneshot::Sender<()> {
    let (shutdown_tx, mut shutdown_rx) = oneshot::channel::<()>();
    // Grab the tracker's display name up-front so tracing lines carry
    // it (`tracker.name()` is `&'static str`, no lifetime concerns).
    let name = tracker.name();
    tokio::task::spawn_blocking(move || {
        tracing::info!(tracker = name, "tick task: enter");
        let mut process: Option<Spel2Process> = None;
        let mut last_payload = TrackerPayload::Empty;
        let mut health = AttachHealth::default();
        // Sticky bit: any successful tick sets it, and once set the
        // idle payload flips from `Empty` (never seen game) to
        // `Detached` (game closed). Lets the UI distinguish the
        // pre-attach "Waiting for game" label from the post-death one.
        let mut ever_attached = false;
        // Latch so a persistent attach failure is logged once, not once per
        // second. Cleared on a successful attach so a later failure is heard.
        let mut reported_attach_error = false;

        loop {
            // Cooperative shutdown check. Non-blocking so the signal
            // is noticed at the next tick boundary.
            match shutdown_rx.try_recv() {
                Ok(()) | Err(oneshot::error::TryRecvError::Closed) => break,
                Err(oneshot::error::TryRecvError::Empty) => {}
            }

            if process.is_none() {
                process = match Spel2Process::attach() {
                    Ok(p) => Some(p),
                    Err(ml2_mem::MemError::NotAttached) => {
                        // The overwhelmingly common case: the game just isn't
                        // running. The trackers already say so on their own.
                        set_attach_problem(None);
                        None
                    }
                    Err(e) => {
                        // Anything else means the game is there but we can't
                        // read it, which the user has to fix. Publish it for
                        // the Trackers page, and log once per attach sequence
                        // rather than once a second.
                        //
                        // AccessDenied carries a message written for the user;
                        // the full Display adds a pid and a /proc path that
                        // belong in the log, not in the UI.
                        set_attach_problem(Some(match &e {
                            ml2_mem::MemError::AccessDenied { msg, .. } => msg.clone(),
                            other => other.to_string(),
                        }));
                        if !reported_attach_error {
                            reported_attach_error = true;
                            tracing::warn!(tracker = name, "cannot attach to the game: {e}");
                        }
                        None
                    }
                };
                if process.is_none() {
                    // Not attached. Park at Empty on the initial wait
                    // or Detached if the game was previously attached
                    // and lost, then back off so the OS process list
                    // isn't hammered every 16 ms.
                    let idle = if ever_attached {
                        TrackerPayload::Detached
                    } else {
                        TrackerPayload::Empty
                    };
                    let _ = payload_tx.send_if_modified(|current| {
                        if *current != idle {
                            *current = idle.clone();
                            true
                        } else {
                            false
                        }
                    });
                    std::thread::sleep(ATTACH_BACKOFF);
                    continue;
                }
                // Attach edge: wipe any tracker state that was tied to
                // the old process (address-space LUTs, wall-clock
                // baselines captured on first observation, per-run
                // accumulators). Runs on both first attach and every
                // reattach after the game exits and comes back.
                tracker.on_attach();
                health.on_success();
                reported_attach_error = false;
                set_attach_problem(None);
            }

            // Any idle tick reports the same thing: `Empty` before we have
            // ever seen the game, `Detached` once we have and lost it.
            let idle_payload = || {
                if ever_attached {
                    TrackerPayload::Detached
                } else {
                    TrackerPayload::Empty
                }
            };

            let payload = match tick_once(&mut tracker, process.as_ref().unwrap(), &config_rx) {
                Ok(payload) => {
                    health.on_success();
                    ever_attached = true;
                    payload
                }
                Err(ml2_mem::MemError::FeedcodeMissing) => {
                    if health.on_feedcode_missing(Instant::now()) {
                        tracing::debug!(
                            tracker = name,
                            "no feedcode after {STALE_HANDLE_GRACE:?}; \
                             dropping the handle to re-attach"
                        );
                        process = None;
                    }
                    idle_payload()
                }
                Err(_) => {
                    if health.on_read_error(Instant::now()) {
                        process = None;
                    }
                    idle_payload()
                }
            };

            if payload != last_payload {
                let _ = payload_tx.send(payload.clone());
                last_payload = payload;
            }

            // A feedcode miss just walked the whole address space; repeating
            // that every 16ms would burn a core for as long as the wait lasts.
            let sleep = if health.waiting_for_feedcode() {
                FEEDCODE_POLL
            } else {
                TICK_INTERVAL
            };
            std::thread::sleep(sleep);
        }
        tracing::info!(tracker = name, "tick task: exit");
    });
    shutdown_tx
}

fn tick_once<T: TrackerTicker>(
    tracker: &mut T,
    process: &Spel2Process,
    config_rx: &watch::Receiver<T::Config>,
) -> Result<TrackerPayload, ml2_mem::MemError> {
    let state = State::read_current(process)?;
    let inputs = ChainInputs::from_process(&state, process);
    let ctx = TrackerContext {
        inputs: Some(&inputs),
        process: Some(process),
    };
    let config = config_rx.borrow().clone();
    Ok(tracker.tick(&ctx, &config))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The loop only re-attaches while `process` is `None`, so "does this
    /// state release the handle?" is the whole ballgame.
    #[test]
    fn read_errors_release_the_handle_on_the_third_strike() {
        let mut health = AttachHealth::default();
        let now = Instant::now();
        assert!(!health.on_read_error(now));
        assert!(!health.on_read_error(now));
        assert!(health.on_read_error(now));
    }

    #[test]
    fn a_torn_read_does_not_cost_the_attach() {
        let mut health = AttachHealth::default();
        let now = Instant::now();
        assert!(!health.on_read_error(now));
        health.on_success();
        // The strike count restarts, so intermittent failures never
        // accumulate their way to a drop.
        assert!(!health.on_read_error(now));
        assert!(!health.on_read_error(now));
    }

    /// A game that is still starting up hasn't written the marker yet. Keep
    /// the handle so we aren't re-enumerating from scratch every second.
    #[test]
    fn a_launching_game_keeps_its_handle_through_the_grace() {
        let mut health = AttachHealth::default();
        let start = Instant::now();
        assert!(!health.on_feedcode_missing(start));
        assert!(!health.on_feedcode_missing(start + STALE_HANDLE_GRACE / 2));
        assert!(!health.on_feedcode_missing(start + STALE_HANDLE_GRACE - Duration::from_millis(1)));
    }

    /// The bug this guards. A process that has died reports `FeedcodeMissing`,
    /// not a read error, because it enumerates zero pages. If that state holds
    /// the handle indefinitely then `process` never returns to `None`, the
    /// loop never calls `attach` again, and the tracker sits on "Spelunky 2
    /// exited" for the rest of the session even after the game is relaunched.
    #[test]
    fn a_dead_process_releases_the_handle_once_the_grace_expires() {
        let mut health = AttachHealth::default();
        let start = Instant::now();
        assert!(!health.on_feedcode_missing(start));
        assert!(health.on_feedcode_missing(start + STALE_HANDLE_GRACE));
    }

    /// Whatever a handle does, it has to become droppable in bounded time --
    /// otherwise the tracker stops polling for the game entirely.
    ///
    /// The interleaved case is the one worth pinning: a process on its way out
    /// can produce both failure modes, and per-mode counters that reset each
    /// other would let it dodge every limit indefinitely.
    #[test]
    fn no_sequence_of_failures_holds_the_handle_forever() {
        let start = Instant::now();
        let step = Duration::from_millis(16);
        // Every interleaving of the two failure modes, by period.
        for period in 1..=4u32 {
            for offset in 0..period {
                let mut health = AttachHealth::default();
                let dropped = (0..2_000).any(|i| {
                    let now = start + step * i;
                    if i % period == offset {
                        health.on_feedcode_missing(now)
                    } else {
                        health.on_read_error(now)
                    }
                });
                assert!(dropped, "never released: period {period}, offset {offset}");
            }
        }
    }

    #[test]
    fn success_clears_a_pending_wait() {
        let mut health = AttachHealth::default();
        let start = Instant::now();
        health.on_feedcode_missing(start);
        assert!(health.waiting_for_feedcode());
        health.on_success();
        assert!(!health.waiting_for_feedcode());
        // The deadline restarts from the next failure, not the original one,
        // so a game that reads fine for a while isn't dropped on old history.
        assert!(!health.on_feedcode_missing(start + STALE_HANDLE_GRACE * 2));
    }

    /// The loop backs off to `FEEDCODE_POLL` only while scanning; a plain read
    /// error should stay on the fast tick so a torn read costs one frame.
    #[test]
    fn only_a_feedcode_miss_slows_the_tick() {
        let mut health = AttachHealth::default();
        let now = Instant::now();
        assert!(!health.waiting_for_feedcode());
        health.on_feedcode_missing(now);
        assert!(health.waiting_for_feedcode());
        health.on_read_error(now);
        assert!(!health.waiting_for_feedcode());
    }
}
