//! spelunky.fyi push-install listener. When the user has an API token
//! configured, opens a WebSocket to `<service_root>/ws/gateway/ml/` and
//! parks on it: the site pushes an `install` action every time the user
//! clicks the "Install in modlunky2" button on a mod page, and the WS
//! client routes that straight into the local mod manager, then acks
//! back with `install-complete` so the site's UI updates.
//!
//! The actual protocol lives in `ml2_mods::spelunkyfyi::web_socket`;
//! this module just owns the subsystem lifecycle, mirrors status
//! transitions into a Tauri event so the UI can show a connection
//! indicator, and lets the settings-save flow restart the client when
//! the token / service root changes.

use std::sync::{Arc, Mutex};
use std::time::Duration;

use ml2_mods::manager::ModManagerHandle;
use ml2_mods::spelunkyfyi::web_socket::{
    ConnectionStatus, DEFAULT_MAX_PING_INTERVAL, DEFAULT_MIN_PING_INTERVAL, DEFAULT_PONG_TIMEOUT,
    WebSocketClient,
};
use rand::distr::Uniform;
use tauri::{AppHandle, Emitter, Manager, Runtime, async_runtime::JoinHandle};
use tokio::sync::{oneshot, watch};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemBuilder, SubsystemHandle, Toplevel};

use crate::state::AppState;

const STATUS_EVENT: &str = "fyi-ws-status";
/// Grace period for the subsystem's shutdown handler to close the WS
/// cleanly before it drops. Matches typical WS close round-trips.
const SHUTDOWN_GRACE: Duration = Duration::from_secs(2);

/// Live handle to a running fyi WebSocket subsystem: the tokio task
/// hosting the tokio_graceful_shutdown Toplevel, a oneshot the token-
/// change flow fires to stop it (the receiving side lives inside the
/// task and calls ShutdownToken::shutdown on itself, since
/// ShutdownToken's type is private to the crate and can't cross a
/// module boundary), plus the last observed status so a new frontend
/// mount can synchronously read where things stand.
pub struct FyiWsHandle {
    #[allow(dead_code)]
    task: JoinHandle<()>,
    shutdown_tx: Option<oneshot::Sender<()>>,
    status_rx: watch::Receiver<ConnectionStatus>,
}

impl FyiWsHandle {
    pub fn current_status(&self) -> ConnectionStatus {
        *self.status_rx.borrow()
    }

    fn shutdown(&mut self) {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
    }
}

/// Session-scoped state for the fyi WS subsystem: one Mutex-guarded
/// handle slot (Some when running) plus the latest published status
/// used by the get-status command when nothing is running.
pub struct FyiWsSlot {
    pub handle: Mutex<Option<FyiWsHandle>>,
}

impl FyiWsSlot {
    pub fn new() -> Self {
        Self {
            handle: Mutex::new(None),
        }
    }

    pub fn status(&self) -> ConnectionStatus {
        self.handle
            .lock()
            .unwrap()
            .as_ref()
            .map(|h| h.current_status())
            .unwrap_or(ConnectionStatus::Disconnected)
    }
}

/// Read the user's token + service root, spawn the subsystem if both
/// are set, and store the handle on the AppState. No-op when either is
/// missing so a fresh install without a token boots without an obvious
/// "trying to connect" spinner in the tab bar.
pub fn start_if_configured<R: Runtime>(app: &AppHandle<R>) {
    let state = app.state::<AppState>();
    let cfg = crate::config::load();
    let Some(token) = cfg.spelunky_fyi_api_token.filter(|s| !s.trim().is_empty()) else {
        return;
    };
    let service_root = cfg
        .spelunky_fyi_root
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| ml2_mods::spelunkyfyi::http::DEFAULT_SERVICE_ROOT.to_string());
    let Some(handle) = state.mods_handle() else {
        tracing::debug!("mods manager not ready, skipping fyi WS start");
        return;
    };

    match spawn_subsystem(app.clone(), &service_root, &token, handle) {
        Ok(new_handle) => {
            let mut guard = state.fyi_ws().handle.lock().unwrap();
            if let Some(mut old) = guard.replace(new_handle) {
                old.shutdown();
                drop(old);
            }
        }
        Err(e) => tracing::warn!("fyi WS start failed: {e}"),
    }
}

/// Stop the running subsystem, if any, and clear the slot. Emits a
/// final Disconnected status so the UI updates immediately.
pub fn stop<R: Runtime>(app: &AppHandle<R>) {
    let state = app.state::<AppState>();
    let taken = state.fyi_ws().handle.lock().unwrap().take();
    if let Some(mut handle) = taken {
        handle.shutdown();
    }
    emit_status(app, ConnectionStatus::Disconnected);
}

/// Idempotent apply of the current config: stop any existing subsystem
/// then start a new one if a token is configured. The settings-save
/// flow calls this so token/root edits take effect without an app
/// restart. Called on boot too.
pub fn refresh<R: Runtime>(app: &AppHandle<R>) {
    stop(app);
    start_if_configured(app);
}

fn spawn_subsystem<R: Runtime>(
    app: AppHandle<R>,
    service_root: &str,
    token: &str,
    manager: ModManagerHandle,
) -> Result<FyiWsHandle, String> {
    let (status_tx, mut status_rx) = watch::channel(ConnectionStatus::Connecting);
    let client = WebSocketClient::new(
        service_root,
        token,
        manager,
        Uniform::new(DEFAULT_MIN_PING_INTERVAL, DEFAULT_MAX_PING_INTERVAL)
            .expect("min ping interval < max"),
        DEFAULT_PONG_TIMEOUT,
    )
    .map_err(|e| format!("build ws client: {e}"))?
    .with_status_channel(status_tx);

    let status_watcher_rx = status_rx.clone();

    // Mirror every status transition into a Tauri event so the tab-bar
    // pill can update without polling. Runs alongside the subsystem
    // task; ends when the sender drops.
    let app_for_emit = app.clone();
    tauri::async_runtime::spawn(async move {
        emit_status(&app_for_emit, *status_rx.borrow_and_update());
        while status_rx.changed().await.is_ok() {
            emit_status(&app_for_emit, *status_rx.borrow());
        }
    });

    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();
    let task = tauri::async_runtime::spawn(async move {
        // Forward the outer oneshot into the subsystem tree via a small
        // sibling subsystem that owns the receiver and calls
        // request_shutdown on itself when the signal arrives; that
        // propagates a global shutdown to the ws client.
        let result = Toplevel::new(async move |s: &mut SubsystemHandle| {
            s.start(SubsystemBuilder::new("fyi-ws", client.into_subsystem()));
            s.start(SubsystemBuilder::new(
                "shutdown-forwarder",
                async move |sh: &mut SubsystemHandle| -> anyhow::Result<()> {
                    tokio::select! {
                        () = sh.on_shutdown_requested() => {}
                        _ = shutdown_rx => sh.request_shutdown(),
                    }
                    Ok(())
                },
            ));
        })
        .handle_shutdown_requests(SHUTDOWN_GRACE)
        .await;
        if let Err(e) = result {
            tracing::warn!("fyi WS subsystem exited: {e:?}");
        }
    });

    Ok(FyiWsHandle {
        task,
        shutdown_tx: Some(shutdown_tx),
        status_rx: status_watcher_rx,
    })
}

fn emit_status<R: Runtime>(app: &AppHandle<R>, status: ConnectionStatus) {
    let _ = app.emit(STATUS_EVENT, status);
}

/// Wire-facing status view. Frontend narrows on the tag string.
#[tauri::command]
pub fn get_fyi_ws_status(state: tauri::State<'_, AppState>) -> ConnectionStatus {
    state.fyi_ws().status()
}

/// Called by settings-save flow (or the frontend directly) to nuke the
/// existing connection and reconnect with the current token + root.
#[tauri::command]
pub fn refresh_fyi_ws<R: Runtime>(app: AppHandle<R>) {
    refresh(&app);
}

/// Sentinel value the setup path uses to construct AppState. Wrapping in
/// Arc here rather than at every call site keeps state.rs clean.
pub fn new_slot() -> Arc<FyiWsSlot> {
    Arc::new(FyiWsSlot::new())
}
