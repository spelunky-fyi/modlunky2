//! axum server hosting the OBS browser-source WebSocket routes plus
//! (eventually) a static-file mount for the front-end bundle.
//!
//! Topology:
//! - One `axum::Router` per running server, bound to
//!   `127.0.0.1:{tracker-port}` (configurable, default 9526).
//! - Single `/ws/:slug` route dispatches via the shared SlotMap: any
//!   tracker registered on TrackersState gets a route for free.
//! - Origin check (`http://{host}`) so a random cross-origin page
//!   can't peek at the tracker feed.
//! - Graceful shutdown via `oneshot::Sender<()>` stored in AppState;
//!   the tauri command that starts the server also stashes it.

use std::sync::Arc;
use std::time::Duration;

use axum::Router;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Path, State as AxumState};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::routing::get;
use include_dir::{Dir, include_dir};
use ml2_trackers::tracker::TrackerPayload;
use tokio::sync::{oneshot, watch};

use super::consumers::{ConsumerRegistry, SlotMap};

/// Static OBS-facing bundle: index.html linking to per-tracker pages
/// plus a per-tracker page + shared JS/CSS. Small enough to embed
/// directly in the exe; regenerating means editing the files under
/// `obs-source/` and rebuilding.
static OBS_BUNDLE: Dir<'_> = include_dir!("$CARGO_MANIFEST_DIR/../obs-source");

/// Shared state the axum handlers reach into. Cheap to clone thanks
/// to the Arc-wrapped SlotMap + registry; every request handler gets
/// a fresh clone.
#[derive(Clone)]
pub struct ServerState {
    pub slots: SlotMap,
    pub host_hint: Arc<String>,
    /// Window-styling knobs (chroma-key color, font family, font size)
    /// exposed on `/api/window-config` so the OBS pages pick them up
    /// live without users regenerating URLs. Cloned by the config
    /// endpoint on every request; changes flow in from the tauri
    /// config command via `send()`.
    pub window_config_rx: watch::Receiver<WindowConfig>,
    /// Monotonically-increasing counter the config command bumps
    /// whenever styling changes. WS handlers watch it and push a
    /// `{"type":"Reload"}` message so already-connected browser
    /// sources refetch /api/window-config without a manual OBS
    /// cache-refresh.
    pub layout_version_rx: watch::Receiver<u64>,
    /// Refcount registry. WS handlers `attach` on upgrade and hold
    /// the returned guard for the connection's lifetime so producer
    /// tick tasks only run while at least one client is listening.
    pub consumers: ConsumerRegistry,
}

/// The JSON body of `/api/window-config`. Keep field names camelCase
/// so the OBS JS matches TypeScript conventions without needing a
/// mapping layer.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WindowConfig {
    pub color_key: String,
    pub font_family: String,
    pub font_size: u16,
    pub font_color: String,
    /// Text-outline (stroke) width in px; 0 = no outline. Applies to every
    /// tracker so their look is consistent.
    pub stroke_width: u16,
    pub stroke_color: String,
}

pub async fn serve(port: u16, state: ServerState) -> Result<oneshot::Sender<()>, String> {
    let router = Router::new()
        .route("/ws/{slug}", get(ws_tracker))
        .route("/api/window-config", get(get_window_config))
        .route("/", get(serve_index))
        .route("/{*path}", get(serve_static))
        .with_state(state);

    let addr = format!("127.0.0.1:{port}");
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .map_err(|e| format!("bind {addr}: {e}"))?;

    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();
    tokio::spawn(async move {
        let _ = axum::serve(listener, router)
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
            })
            .await;
    });
    Ok(shutdown_tx)
}

/// Generic WebSocket handler for every tracker. Looks up the slot by
/// slug, attaches a consumer guard for the connection's lifetime,
/// then hands off to `handle_ws`. Returns 404 for unknown slugs
/// instead of upgrading a dead socket.
async fn ws_tracker(
    Path(slug): Path<String>,
    ws: WebSocketUpgrade,
    AxumState(state): AxumState<ServerState>,
    headers: HeaderMap,
) -> impl IntoResponse {
    if !origin_ok(&headers, &state.host_hint) {
        return StatusCode::FORBIDDEN.into_response();
    }
    let Some(slot) = state.slots.get(slug.as_str()) else {
        return StatusCode::NOT_FOUND.into_response();
    };
    let payload_rx = slot.payload_rx.clone();
    let layout_rx = state.layout_version_rx.clone();
    let consumers = state.consumers.clone();
    let slug_owned = slug;
    ws.on_upgrade(move |socket| async move {
        let _guard = consumers.attach(&slug_owned);
        handle_ws(socket, payload_rx, layout_rx).await;
    })
}

/// Compare the incoming Origin against the local addresses the server
/// binds on. axum's WebSocketUpgrade doesn't enforce this by default;
/// this check runs because the tracker server exposes live game
/// state. `host_hint` is the 127.0.0.1 form the server bound to, but
/// the browser may resolve the URL as `localhost` if the user typed
/// it that way, accept both plus http/https variants.
fn origin_ok(headers: &HeaderMap, host_hint: &str) -> bool {
    let Some(origin) = headers.get(axum::http::header::ORIGIN) else {
        // Native WebSocket clients (curl, wscat) often skip Origin
        // entirely. Accept the empty case so users can debug from a
        // terminal.
        return true;
    };
    let Ok(origin_str) = origin.to_str() else {
        return false;
    };
    let port = host_hint.rsplit(':').next().unwrap_or("");
    let accepted = [
        format!("http://127.0.0.1:{port}"),
        format!("https://127.0.0.1:{port}"),
        format!("http://localhost:{port}"),
        format!("https://localhost:{port}"),
    ];
    accepted.iter().any(|a| a == origin_str)
}

/// Per-connection loop. Streams payload changes to the socket,
/// sending a heartbeat ping every 15s so intermediate proxies /
/// browsers don't drop the connection during quiet periods.
async fn handle_ws(
    mut socket: WebSocket,
    mut payload_rx: watch::Receiver<TrackerPayload>,
    mut layout_rx: watch::Receiver<u64>,
) {
    let initial = payload_rx.borrow().clone();
    if send_payload(&mut socket, &initial).await.is_err() {
        return;
    }

    let mut heartbeat = tokio::time::interval(Duration::from_secs(15));
    heartbeat.tick().await;

    loop {
        tokio::select! {
            changed = payload_rx.changed() => {
                if changed.is_err() {
                    break;
                }
                let payload = payload_rx.borrow().clone();
                if send_payload(&mut socket, &payload).await.is_err() {
                    break;
                }
            }
            changed = layout_rx.changed() => {
                if changed.is_err() {
                    break;
                }
                if socket
                    .send(Message::Text("{\"type\":\"Reload\"}".into()))
                    .await
                    .is_err()
                {
                    break;
                }
            }
            _ = heartbeat.tick() => {
                if socket.send(Message::Ping(Vec::new().into())).await.is_err() {
                    break;
                }
            }
            msg = socket.recv() => {
                match msg {
                    Some(Ok(Message::Close(_))) | None => break,
                    Some(Err(_)) => break,
                    _ => {}
                }
            }
        }
    }
}

async fn send_payload(socket: &mut WebSocket, payload: &TrackerPayload) -> Result<(), ()> {
    let json = serde_json::to_string(payload).map_err(|_| ())?;
    socket
        .send(Message::Text(json.into()))
        .await
        .map_err(|_| ())
}

async fn get_window_config(AxumState(state): AxumState<ServerState>) -> impl IntoResponse {
    let cfg = state.window_config_rx.borrow().clone();
    let json = serde_json::to_string(&cfg).unwrap_or_else(|_| "{}".to_string());
    ([("content-type", "application/json")], json).into_response()
}

async fn serve_index() -> impl IntoResponse {
    match OBS_BUNDLE.get_file("index.html") {
        Some(f) => ([("content-type", "text/html; charset=utf-8")], f.contents()).into_response(),
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

async fn serve_static(Path(path): Path<String>) -> impl IntoResponse {
    if path.contains("..") {
        return StatusCode::FORBIDDEN.into_response();
    }
    let Some(file) = OBS_BUNDLE.get_file(&path) else {
        return StatusCode::NOT_FOUND.into_response();
    };
    let mime = mime_guess::from_path(&path)
        .first_or_octet_stream()
        .to_string();
    ([("content-type", mime)], file.contents()).into_response()
}
