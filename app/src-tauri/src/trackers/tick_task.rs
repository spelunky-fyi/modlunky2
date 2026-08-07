//! Generic tick loop shared by every per-tracker task. Any concrete
//! tracker just calls `spawn` with its `TrackerTicker` instance +
//! payload/config watch pair; the loop itself, attach retry, and
//! payload dedupe are the same everywhere.
//!
//! Runs on `spawn_blocking` because the process reads are synchronous on
//! every backend (ReadProcessMemory on Windows, pread on Linux). The 16ms
//! tick + 1s attach backoff hit roughly one read per game frame while
//! keeping the not-attached path cheap.

use std::time::Duration;

use ml2_mem::Spel2Process;
use ml2_trackers::chain_impl::inputs::ChainInputs;
use ml2_trackers::state::State;
use ml2_trackers::tracker::{TrackerContext, TrackerPayload, TrackerTicker};
use tokio::sync::{oneshot, watch};

const TICK_INTERVAL: Duration = Duration::from_millis(16);
const ATTACH_BACKOFF: Duration = Duration::from_secs(1);

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
        let mut consecutive_read_errors: u32 = 0;
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
                consecutive_read_errors = 0;
                reported_attach_error = false;
                set_attach_problem(None);
            }

            let payload = match tick_once(&mut tracker, process.as_ref().unwrap(), &config_rx) {
                Ok(payload) => {
                    consecutive_read_errors = 0;
                    ever_attached = true;
                    payload
                }
                // The game is up but we can't read feedcode yet, which
                // takes a few seconds after launch. Keep the handle
                // (dropping it would throw away the cached scan
                // and re-enumerate every mapping a second later) and wait
                // for it to appear.
                Err(ml2_mem::MemError::FeedcodeMissing) => {
                    consecutive_read_errors = 0;
                    if ever_attached {
                        TrackerPayload::Detached
                    } else {
                        TrackerPayload::Empty
                    }
                }
                Err(_) => {
                    consecutive_read_errors += 1;
                    // Three strikes and the handle drops. Game
                    // probably died. Small threshold so recovery is
                    // quick, not so small that a single torn read
                    // during a level transition costs the attach.
                    if consecutive_read_errors >= 3 {
                        process = None;
                    }
                    if ever_attached {
                        TrackerPayload::Detached
                    } else {
                        TrackerPayload::Empty
                    }
                }
            };

            if payload != last_payload {
                let _ = payload_tx.send(payload.clone());
                last_payload = payload;
            }

            std::thread::sleep(TICK_INTERVAL);
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
