//! Generic tick loop shared by every per-tracker task. Any concrete
//! tracker just calls `spawn` with its `TrackerTicker` instance +
//! payload/config watch pair; the loop itself, attach retry, and
//! payload dedupe are the same everywhere.
//!
//! Runs on `spawn_blocking` because Windows' ReadProcessMemory is
//! synchronous. The 16ms tick + 1s attach backoff hit roughly one
//! read per game frame while keeping the not-attached path cheap.

use std::time::Duration;

use ml2_mem::Spel2Process;
use ml2_trackers::chain_impl::inputs::ChainInputs;
use ml2_trackers::state::State;
use ml2_trackers::tracker::{TrackerContext, TrackerPayload, TrackerTicker};
use tokio::sync::{oneshot, watch};

const TICK_INTERVAL: Duration = Duration::from_millis(16);
const ATTACH_BACKOFF: Duration = Duration::from_secs(1);

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

        loop {
            // Cooperative shutdown check. Non-blocking so the signal
            // is noticed at the next tick boundary.
            match shutdown_rx.try_recv() {
                Ok(()) | Err(oneshot::error::TryRecvError::Closed) => break,
                Err(oneshot::error::TryRecvError::Empty) => {}
            }

            if process.is_none() {
                process = Spel2Process::attach().ok();
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
            }

            let payload = match tick_once(&mut tracker, process.as_ref().unwrap(), &config_rx) {
                Ok(payload) => {
                    consecutive_read_errors = 0;
                    ever_attached = true;
                    payload
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
) -> Result<TrackerPayload, String> {
    let state = State::read_current(process).map_err(|e| e.to_string())?;
    let inputs = ChainInputs::from_process(&state, process);
    let ctx = TrackerContext {
        inputs: Some(&inputs),
        process: Some(process),
    };
    let config = config_rx.borrow().clone();
    Ok(tracker.tick(&ctx, &config))
}
