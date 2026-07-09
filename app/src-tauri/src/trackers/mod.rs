//! Tracker subsystem: axum server, per-tracker tick loops, and the
//! tauri commands the React UI calls to start / stop / peek.
//!
//! One shared server binds `127.0.0.1:{port}`; every tracker owns a
//! `tokio::sync::watch::Sender<TrackerPayload>` that the WS handlers
//! subscribe to. Config changes flow the other direction through a
//! `watch::Sender<Config>` so hot-reload just works.
//!
//! Tick lifecycle: refcounted on active WebSocket connections. Both
//! the popped-out Tauri window and any OBS Browser Source load the
//! same tracker.html, whose JS connects to `/ws/<slug>`, so a single
//! counter per tracker handles both. Zero WS clients means no memory
//! reads, so an idle server costs nothing.
//!
//! Per-tracker plumbing lives on `TrackerSlot`. Adding a new tracker
//! is one line in `TrackersState::new`; the WS route, config commands,
//! persistence, and refcount lifecycle all funnel through the slug.
//!
//! Windows-only in practice (Spel2Process only attaches there), but
//! the module builds on any platform so cross-compilation for CI
//! stays sane; on non-Windows the tick loop reports `Empty` forever.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use ml2_trackers::tracker::{
    CategoryTracker, CoTracker, GemTracker, PacifistTracker, PacinoGolfTracker, TimerTracker,
    TrackerPayload,
};
use serde::Serialize;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tokio::sync::{oneshot, watch};

use consumers::SlotMap;
use slot::{TrackerSlot, build_slot};

pub use consumers::ConsumerRegistry;
pub use server::WindowConfig;

mod consumers;
mod file_task;
mod render;
mod server;
mod slot;
mod tick_task;

/// Default port for the tracker HTTP + WS server.
pub const DEFAULT_TRACKER_PORT: u16 = 9526;

/// Everything a running tracker server holds onto. Dropping this
/// (via `stop_tracker_server`) tears down the axum server; the
/// consumer registry (shared with TrackersState) handles the tick
/// task shutdown.
struct RunningServer {
    port: u16,
    server_shutdown: Option<oneshot::Sender<()>>,
    /// Shutdown handles for currently-running per-tracker file
    /// writers, keyed by slug. Populated when a tracker window opens
    /// with the "log to file" setting on; removed automatically when
    /// that window closes.
    file_writers: HashMap<String, oneshot::Sender<()>>,
}

/// Long-lived state kept on `AppState`. Watchers exist even before
/// the server starts so React can subscribe eagerly; they just carry
/// `Empty` until the tick loop lands its first payload.
pub struct TrackersState {
    running: Arc<Mutex<Option<RunningServer>>>,
    /// One slot per registered tracker. Everything the runtime does
    /// per-tracker (spawn tick, hand a WS route its payload watch,
    /// serve get/set config) reads through this map.
    slots: SlotMap,
    window_config_tx: watch::Sender<WindowConfig>,
    window_config_rx: watch::Receiver<WindowConfig>,
    /// Layout / styling version. Bumped whenever set_window_config
    /// runs; the WS handler forwards a `{"type":"Reload"}` message on
    /// change so already-connected browser sources refetch config
    /// without users touching OBS's refresh button.
    layout_version_tx: watch::Sender<u64>,
    layout_version_rx: watch::Receiver<u64>,
    /// Refcounts WS attachments per tracker; spawns / kills the
    /// producer tick task on the 0<->1 edge. Shared with the axum
    /// ServerState.
    consumers: ConsumerRegistry,
}

impl TrackersState {
    pub fn new() -> Self {
        // Every tracker is one line here. Persistence paths use the
        // `trackers.<name>` nested block layout so existing config
        // files round-trip.
        let slot_list: Vec<TrackerSlot> = vec![
            build_slot::<CategoryTracker>(
                "category",
                &["trackers", "category"],
                CategoryTracker::new,
            ),
            build_slot::<PacifistTracker>(
                "pacifist",
                &["trackers", "pacifist"],
                PacifistTracker::new,
            ),
            build_slot::<TimerTracker>("timer", &["trackers", "timer"], TimerTracker::new),
            build_slot::<GemTracker>("gem", &["trackers", "gem"], GemTracker::new),
            build_slot::<PacinoGolfTracker>(
                "pacino-golf",
                &["trackers", "pacino-golf"],
                PacinoGolfTracker::new,
            ),
            build_slot::<CoTracker>("co", &["trackers", "co-tracker"], CoTracker::new),
        ];
        let slots: SlotMap = Arc::new(slot_list.into_iter().map(|s| (s.slug, s)).collect());

        // Window config: seed from persisted preferences so a
        // returning user's color/font applies on first render.
        let cfg = crate::config::load();
        let (window_config_tx, window_config_rx) = watch::channel(WindowConfig {
            color_key: cfg.tracker_color_key,
            font_family: cfg.tracker_font_family,
            font_size: cfg.tracker_font_size,
            font_color: cfg.tracker_font_color,
            stroke_width: cfg.tracker_stroke_width,
            stroke_color: cfg.tracker_stroke_color,
        });
        let (layout_version_tx, layout_version_rx) = watch::channel(0u64);
        let consumers = ConsumerRegistry::new(slots.clone());

        Self {
            running: Arc::new(Mutex::new(None)),
            slots,
            window_config_tx,
            window_config_rx,
            layout_version_tx,
            layout_version_rx,
            consumers,
        }
    }
}

impl Default for TrackersState {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------

/// Snapshot of whether the server is running + the port it's on.
/// Returned by `get_tracker_server_status` so the React UI can render
/// "Start / Stop" plus the copyable URLs.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TrackerServerStatus {
    pub running: bool,
    pub port: Option<u16>,
}

#[tauri::command]
pub async fn start_tracker_server(
    port: Option<u16>,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<TrackerServerStatus, String> {
    let port = port.unwrap_or(DEFAULT_TRACKER_PORT);
    let trackers = state.trackers();

    if let Some(running_port) = {
        let guard = trackers.running.lock().unwrap();
        guard.as_ref().map(|r| r.port)
    } {
        return Ok(TrackerServerStatus {
            running: true,
            port: Some(running_port),
        });
    }

    let host_hint = format!("127.0.0.1:{port}");
    let server_state = server::ServerState {
        slots: trackers.slots.clone(),
        host_hint: Arc::new(host_hint),
        window_config_rx: trackers.window_config_rx.clone(),
        layout_version_rx: trackers.layout_version_rx.clone(),
        consumers: trackers.consumers.clone(),
    };
    let server_shutdown = server::serve(port, server_state).await?;

    let mut guard = trackers.running.lock().unwrap();
    *guard = Some(RunningServer {
        port,
        server_shutdown: Some(server_shutdown),
        file_writers: HashMap::new(),
    });

    Ok(TrackerServerStatus {
        running: true,
        port: Some(port),
    })
}

#[tauri::command]
pub fn stop_tracker_server(
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<TrackerServerStatus, String> {
    let trackers = state.trackers();
    let mut guard = trackers.running.lock().unwrap();
    if let Some(mut running) = guard.take() {
        if let Some(s) = running.server_shutdown.take() {
            let _ = s.send(());
        }
        for (_slug, s) in running.file_writers.drain() {
            let _ = s.send(());
        }
    }
    drop(guard);
    trackers.consumers.shutdown_all();
    Ok(TrackerServerStatus {
        running: false,
        port: None,
    })
}

#[tauri::command]
pub fn get_tracker_server_status(
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<TrackerServerStatus, String> {
    let trackers = state.trackers();
    let guard = trackers.running.lock().unwrap();
    Ok(match guard.as_ref() {
        Some(r) => TrackerServerStatus {
            running: true,
            port: Some(r.port),
        },
        None => TrackerServerStatus {
            running: false,
            port: None,
        },
    })
}

/// Returns the current payload for `slug` without waiting for a
/// change event. Used by the React UI's live preview panel.
#[tauri::command]
pub fn get_tracker_payload(
    slug: String,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<TrackerPayload, String> {
    let trackers = state.trackers();
    let slot = trackers
        .slots
        .get(slug.as_str())
        .ok_or_else(|| format!("unknown tracker: {slug}"))?;
    Ok(slot.payload_rx.borrow().clone())
}

/// Generic config read: returns the current config for `slug` as a
/// JSON value. TS side wraps this with typed helpers.
#[tauri::command]
pub fn get_tracker_config(
    slug: String,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<serde_json::Value, String> {
    let trackers = state.trackers();
    let slot = trackers
        .slots
        .get(slug.as_str())
        .ok_or_else(|| format!("unknown tracker: {slug}"))?;
    Ok(slot.get_config())
}

/// Generic config write: deserializes + persists + pushes to the
/// tick task via the slot's watch channel.
#[tauri::command]
pub fn set_tracker_config(
    slug: String,
    config: serde_json::Value,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<(), String> {
    let trackers = state.trackers();
    let slot = trackers
        .slots
        .get(slug.as_str())
        .ok_or_else(|| format!("unknown tracker: {slug}"))?;
    slot.set_config(config)
}

#[tauri::command]
pub fn get_window_config(
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<WindowConfig, String> {
    let trackers = state.trackers();
    Ok(trackers.window_config_rx.borrow().clone())
}

#[tauri::command]
pub fn set_window_config(
    config: WindowConfig,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<(), String> {
    let trackers = state.trackers();
    crate::config::apply_patch(crate::config::ConfigPatch {
        tracker_color_key: Some(config.color_key.clone()),
        tracker_font_size: Some(config.font_size),
        tracker_font_family: Some(config.font_family.clone()),
        tracker_font_color: Some(config.font_color.clone()),
        tracker_stroke_width: Some(config.stroke_width),
        tracker_stroke_color: Some(config.stroke_color.clone()),
        ..Default::default()
    })?;
    let _ = trackers.window_config_tx.send(config);
    trackers.layout_version_tx.send_modify(|v| *v += 1);
    Ok(())
}

/// Native-window setting: whether popped-out tracker windows stay above
/// other windows. Persists to config and applies immediately to every
/// currently-open `tracker-*` window so the change is visible without
/// closing and reopening.
#[tauri::command]
pub fn get_tracker_always_on_top() -> Result<bool, String> {
    Ok(crate::config::load().tracker_always_on_top)
}

#[tauri::command]
pub fn set_tracker_always_on_top(value: bool, app: tauri::AppHandle) -> Result<(), String> {
    crate::config::apply_patch(crate::config::ConfigPatch {
        tracker_always_on_top: Some(value),
        ..Default::default()
    })?;
    // Apply live to every tracker window that exists right now. Main
    // window + any editor windows are skipped by the label prefix
    // check.
    for (label, window) in app.webview_windows() {
        if !label.starts_with("tracker-") {
            continue;
        }
        if let Err(e) = window.set_always_on_top(value) {
            tracing::warn!("set_always_on_top failed on {label}: {e}");
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------
// File writer + diagnostics
// ---------------------------------------------------------------------

/// File-output settings the sidebar exposes. `output_dir = None` means
/// "use the default under install-dir". `enabled = true` couples the
/// file writer's lifetime to the tracker window.
#[derive(Debug, Clone, Serialize, serde::Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct FileOutputSettings {
    pub output_dir: Option<String>,
    pub enabled: bool,
}

#[tauri::command]
pub fn get_file_settings(
    _state: tauri::State<'_, crate::state::AppState>,
) -> Result<FileOutputSettings, String> {
    let cfg = crate::config::load();
    Ok(FileOutputSettings {
        output_dir: cfg.tracker_output_dir,
        enabled: cfg.tracker_file_enabled,
    })
}

#[tauri::command]
pub fn set_file_settings(
    settings: FileOutputSettings,
    app: tauri::AppHandle,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<(), String> {
    crate::config::apply_patch(crate::config::ConfigPatch {
        tracker_output_dir: Some(settings.output_dir.clone().unwrap_or_default()),
        tracker_file_enabled: Some(settings.enabled),
        ..Default::default()
    })?;

    let trackers = state.trackers();
    let mut guard = trackers.running.lock().unwrap();
    let Some(running) = guard.as_mut() else {
        return Ok(());
    };

    if !settings.enabled {
        for (_slug, s) in running.file_writers.drain() {
            let _ = s.send(());
        }
        return Ok(());
    }

    let cfg = crate::config::load();
    let Some(output_dir) = file_task::effective_output_dir(&cfg) else {
        return Ok(());
    };

    let open_slugs: Vec<String> = app
        .webview_windows()
        .keys()
        .filter_map(|label| label.strip_prefix("tracker-").map(String::from))
        .collect();

    for slug in open_slugs {
        if let Some(s) = running.file_writers.remove(&slug) {
            let _ = s.send(());
        }
        if slot_never_writes_file(trackers, &slug) {
            continue;
        }
        if let Some(rx) = tracker_payload_rx(trackers, &slug) {
            let handle = file_task::spawn(slug.clone(), output_dir.clone(), rx);
            running.file_writers.insert(slug, handle);
        }
    }

    Ok(())
}

#[tauri::command]
pub fn get_tracker_diagnostics(
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<Vec<consumers::ConsumerSnapshot>, String> {
    Ok(state.trackers().consumers.snapshot())
}

#[tauri::command]
pub fn get_tracker_file_path(tracker: String) -> Result<String, String> {
    let cfg = crate::config::load();
    let dir = file_task::effective_output_dir(&cfg)
        .ok_or_else(|| "Set install directory in Settings first.".to_string())?;
    Ok(dir
        .join(format!("{tracker}.txt"))
        .to_string_lossy()
        .into_owned())
}

#[tauri::command]
pub async fn open_tracker_file_dir(app: tauri::AppHandle) -> Result<(), String> {
    let cfg = crate::config::load();
    let dir = file_task::effective_output_dir(&cfg)
        .ok_or_else(|| "Set install directory in Settings first.".to_string())?;
    tokio::fs::create_dir_all(&dir)
        .await
        .map_err(|e| format!("mkdir {}: {e}", dir.display()))?;
    use tauri_plugin_opener::OpenerExt;
    app.opener()
        .open_path(dir.to_string_lossy(), None::<&str>)
        .map_err(|e| format!("open: {e}"))
}

/// Look up a tracker's payload receiver by slug. Used by the file
/// writer (which subscribes directly on the Rust side).
fn tracker_payload_rx(
    trackers: &TrackersState,
    slug: &str,
) -> Option<watch::Receiver<TrackerPayload>> {
    trackers.slots.get(slug).map(|s| s.payload_rx.clone())
}

/// Whether this tracker opts out of file-mirroring. Currently only Timer
/// does, because its ms-precision string changes every frame and would
/// otherwise pound the disk.
fn slot_never_writes_file(trackers: &TrackersState, slug: &str) -> bool {
    trackers
        .slots
        .get(slug)
        .map(|s| s.never_writes_file)
        .unwrap_or(false)
}

/// Opens (or focuses) an always-on-top tracker window pointed at the
/// browser-source URL for the tracker.
#[tauri::command]
pub async fn open_tracker_window(
    tracker: String,
    app: tauri::AppHandle,
    state: tauri::State<'_, crate::state::AppState>,
) -> Result<(), String> {
    let trackers = state.trackers();
    let port = {
        let guard = trackers.running.lock().unwrap();
        guard
            .as_ref()
            .map(|r| r.port)
            .ok_or_else(|| "Tracker server is not running.".to_string())?
    };

    let url = format!("http://127.0.0.1:{port}/{tracker}.html");
    let label = format!("tracker-{tracker}");

    if let Some(existing) = app.get_webview_window(&label) {
        let _ = existing.show();
        let _ = existing.set_focus();
        return Ok(());
    }

    let url = url
        .parse::<url::Url>()
        .map_err(|e| format!("bad tracker url {url}: {e}"))?;
    let cfg = crate::config::load();
    let window = WebviewWindowBuilder::new(&app, &label, WebviewUrl::External(url))
        .title(format!("modlunky2 {tracker} tracker"))
        .inner_size(480.0, 120.0)
        .resizable(true)
        .always_on_top(cfg.tracker_always_on_top)
        .decorations(true)
        .build()
        .map_err(|e| format!("open window: {e}"))?;
    if let Err(e) = crate::window_icon::apply_window_icon(&window) {
        tracing::warn!("failed to set crisp window icon on {label}: {e}");
    }

    if cfg.tracker_file_enabled
        && !slot_never_writes_file(trackers, &tracker)
        && let Some(output_dir) = file_task::effective_output_dir(&cfg)
        && let Some(rx) = tracker_payload_rx(trackers, &tracker)
    {
        let handle = file_task::spawn(tracker.clone(), output_dir, rx);
        let mut guard = trackers.running.lock().unwrap();
        if let Some(running) = guard.as_mut()
            && let Some(old) = running.file_writers.insert(tracker.clone(), handle)
        {
            let _ = old.send(());
        }
    }
    let running_arc = trackers.running.clone();
    let slug_for_close = tracker.clone();
    window.on_window_event(move |event| {
        if matches!(event, tauri::WindowEvent::Destroyed) {
            let mut guard = running_arc.lock().unwrap();
            if let Some(running) = guard.as_mut()
                && let Some(s) = running.file_writers.remove(&slug_for_close)
            {
                let _ = s.send(());
            }
        }
    });
    Ok(())
}
