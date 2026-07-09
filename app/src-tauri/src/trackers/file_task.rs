//! File-output writer task. Subscribes to a tracker's payload watch
//! and writes the current display string to a text file whenever it
//! changes.
//!
//! Path is `{output_dir}/{name}.txt`. Content is the tracker's plain
//! display string (e.g. `"No%"`), empty on `Empty` so an OBS Text
//! (GDI+) source rendering the file goes blank when the game isn't
//! attached.
//!
//! Uses `tokio::spawn` (async) because the write is small +
//! non-blocking via `tokio::fs`. A dedicated OS thread would be
//! overkill for one write per state-transition.

use std::path::PathBuf;

use ml2_trackers::tracker::TrackerPayload;
use tokio::sync::{oneshot, watch};

use super::render::payload_to_display;

pub fn spawn(
    slug: String,
    output_dir: PathBuf,
    mut payload_rx: watch::Receiver<TrackerPayload>,
) -> oneshot::Sender<()> {
    let (shutdown_tx, mut shutdown_rx) = oneshot::channel::<()>();
    tokio::spawn(async move {
        if let Err(e) = tokio::fs::create_dir_all(&output_dir).await {
            tracing::warn!(
                "tracker file writer: mkdir {} failed: {e}",
                output_dir.display()
            );
            return;
        }
        let file_path = output_dir.join(format!("{slug}.txt"));

        // Write the current payload once so the file exists with the
        // correct content before the first change fires.
        let initial = payload_rx.borrow().clone();
        let _ = write_atomic(&file_path, &payload_to_display(&initial)).await;

        loop {
            tokio::select! {
                _ = &mut shutdown_rx => break,
                changed = payload_rx.changed() => {
                    if changed.is_err() {
                        break;
                    }
                    let payload = payload_rx.borrow().clone();
                    let text = payload_to_display(&payload);
                    if let Err(e) = write_atomic(&file_path, &text).await {
                        tracing::warn!(
                            "tracker file writer: write {} failed: {e}",
                            file_path.display()
                        );
                    }
                }
            }
        }

        // On graceful shutdown, blank the file so OBS Text sources
        // don't leave a stale end-of-run string on-screen after Stop.
        let _ = write_atomic(&file_path, "").await;
    });
    shutdown_tx
}

/// Atomic write: dump to a `.tmp` sibling then rename. Prevents OBS
/// (or anything else tailing the file) from ever reading a torn
/// half-written string.
async fn write_atomic(path: &std::path::Path, text: &str) -> std::io::Result<()> {
    let tmp = path.with_extension("txt.tmp");
    tokio::fs::write(&tmp, text.as_bytes()).await?;
    tokio::fs::rename(&tmp, path).await?;
    Ok(())
}

/// Resolves the effective output directory. Falls back to
/// `{install-dir}/Mods/Modlunky2/trackers` if the user didn't override
/// it in config; returns None when neither is configured (typically a
/// first-launch user).
pub fn effective_output_dir(cfg: &crate::config::SharedConfig) -> Option<PathBuf> {
    if let Some(dir) = cfg
        .tracker_output_dir
        .as_ref()
        .filter(|s| !s.trim().is_empty())
    {
        return Some(PathBuf::from(dir));
    }
    cfg.install_dir
        .as_ref()
        .map(|d| d.join("Mods").join("Modlunky2").join("trackers"))
}
