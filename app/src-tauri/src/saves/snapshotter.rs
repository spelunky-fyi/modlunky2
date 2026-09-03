//! The automatic snapshotter.
//!
//! Watches `savegame.sav` and archives a copy at most once per configured
//! interval, so a save that gets corrupted can be rolled back to something
//! recent without anyone having remembered to take a snapshot.
//!
//! # Why a watcher and an interval
//!
//! The game rewrites the save constantly, on every level transition, so
//! reacting to each write would archive dozens of near-identical files an
//! hour. The interval is what keeps the store small; the watcher is what
//! makes the snapshot *recent*. Together they mean the archived copy is
//! from the end of a play session rather than from whenever a timer
//! happened to fire.
//!
//! Three things stop a redundant capture:
//!
//! - the interval, which is the coarse limit
//! - a debounce, so a burst of writes during play is one consideration
//! - a content hash, so a save that has not actually changed is skipped
//!   even when the interval has elapsed
//!
//! # Lifetime
//!
//! This runs for as long as the app does. It cannot capture anything while
//! modlunky2 is closed, so the first consideration happens shortly after
//! startup: if the app was shut for three days, the save gets archived on
//! the next launch rather than waiting another interval.

use std::path::{Path, PathBuf};
use std::time::Duration;

use notify::{RecommendedWatcher, RecursiveMode, Watcher};
use tauri::{AppHandle, Emitter};
use tokio::sync::mpsc;

use super::store::{self, Library, SaveKind};

/// How long the save has to go quiet before a burst of writes counts as
/// one change. Comfortably longer than the gap between the writes the
/// game makes while moving between levels.
const DEBOUNCE: Duration = Duration::from_secs(10);

/// How often to reconsider without having seen a file event. This is the
/// backstop for a save changed while the app was closed, and for a
/// filesystem the watcher cannot subscribe to.
const IDLE_TICK: Duration = Duration::from_secs(15 * 60);

/// Delay before the first consideration, so the app finishes starting up
/// before anything touches the disk.
const STARTUP_DELAY: Duration = Duration::from_secs(20);

/// Event emitted after a snapshot is taken, so an open Saves tab refreshes
/// without polling.
pub const SNAPSHOT_TAKEN_EVENT: &str = "save-snapshot-taken";

/// Starts the snapshotter. Returns immediately.
pub fn spawn(app: AppHandle) {
    tauri::async_runtime::spawn(async move { run(app).await });
}

async fn run(app: AppHandle) {
    tokio::time::sleep(STARTUP_DELAY).await;

    let (tx, mut rx) = mpsc::channel::<()>(16);
    // Held for as long as the watch should last: a watcher unsubscribes
    // when it drops, so this binding is the subscription.
    let mut watcher: Option<RecommendedWatcher> = None;
    let mut watched_dir: Option<PathBuf> = None;

    loop {
        // The install directory can change under us from Settings, so the
        // watch target is re-derived each time round rather than fixed at
        // startup.
        let wanted_dir = super::save_path().and_then(|p| p.parent().map(PathBuf::from));
        if wanted_dir != watched_dir {
            // Unsubscribe the old directory before subscribing to the new
            // one, so the two watches never overlap.
            drop(watcher.take());
            watcher = wanted_dir
                .as_ref()
                .and_then(|dir| match start_watch(dir, tx.clone()) {
                    Ok(w) => {
                        tracing::debug!("Snapshotter watching {}", dir.display());
                        Some(w)
                    }
                    Err(err) => {
                        // Not fatal: IDLE_TICK still drives considerations, so
                        // the snapshotter degrades to polling rather than
                        // stopping.
                        tracing::warn!("Could not watch {} for save changes: {err}", dir.display());
                        None
                    }
                });
            watched_dir = wanted_dir;
        }

        tokio::select! {
            received = rx.recv() => {
                if received.is_none() {
                    // Every sender is gone, which cannot happen while this
                    // loop holds one. Bail rather than spin.
                    return;
                }
                // Wait for the writes to stop before looking at the file,
                // so a snapshot is never taken from a half-written save.
                // Falling out means a full debounce of quiet, or a closed
                // channel; either way there is nothing more to wait for.
                while let Ok(Some(())) = tokio::time::timeout(DEBOUNCE, rx.recv()).await {}
            }
            () = tokio::time::sleep(IDLE_TICK) => {}
        }

        match consider(&app) {
            Ok(Some(id)) => tracing::info!("Took automatic save snapshot {id}"),
            Ok(None) => {}
            Err(err) => tracing::warn!("Automatic save snapshot failed: {err}"),
        }
    }
}

/// Subscribes to changes in `dir`.
///
/// The directory is watched rather than the save file itself: the game
/// replaces the save rather than editing it in place, and a watch on a
/// path that gets replaced stops firing.
fn start_watch(dir: &Path, tx: mpsc::Sender<()>) -> notify::Result<RecommendedWatcher> {
    let mut watcher = notify::recommended_watcher(move |res: notify::Result<notify::Event>| {
        let Ok(event) = res else { return };
        let touches_save = event.paths.iter().any(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.eq_ignore_ascii_case(super::SAVE_FILENAME))
        });
        if touches_save {
            // A full channel means a consideration is already pending,
            // which is exactly what this would have asked for.
            let _ = tx.try_send(());
        }
    })?;
    watcher.watch(dir, RecursiveMode::NonRecursive)?;
    Ok(watcher)
}

/// Takes a snapshot if one is due. Returns the new snapshot's id, or
/// `None` when nothing needed doing.
fn consider(app: &AppHandle) -> Result<Option<String>, String> {
    let settings = super::settings();
    if !settings.enabled {
        return Ok(None);
    }
    let Some(path) = super::save_path() else {
        return Ok(None);
    };
    if !path.exists() {
        return Ok(None);
    }

    let snapshots = store::list(Library::Snapshots).map_err(|e| e.to_string())?;
    let interval_ms = u64::from(settings.interval_hours).saturating_mul(60 * 60 * 1000);
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);

    // The clock starts from the last automatic capture. A save the user
    // archived by hand does not reset it: someone snapshotting manually is
    // not asking the scheduler to back off.
    if let Some(last) = snapshots.iter().map(|s| s.meta.taken_at_ms).max()
        && now.saturating_sub(last) < interval_ms
    {
        return Ok(None);
    }

    // Catches the common case where the game has rewritten a save whose
    // contents are unchanged. Both libraries count: if the user just
    // archived this exact save by hand, there is nothing to add by
    // archiving it again.
    let hash = store::hash_file(&path).map_err(|e| e.to_string())?;
    let known = store::contains_hash(&hash).map_err(|e| e.to_string())?;
    if known {
        tracing::debug!("Save is unchanged since the last capture; skipping");
        return Ok(None);
    }

    let snapshot = store::capture(&path, "Automatic snapshot", SaveKind::Automatic)
        .map_err(|e| e.to_string())?;
    if let Err(err) = store::apply_retention(&settings.retention) {
        tracing::warn!("Could not apply the retention policy: {err}");
    }
    let _ = app.emit(SNAPSHOT_TAKEN_EVENT, &snapshot.meta.id);
    Ok(Some(snapshot.meta.id))
}
