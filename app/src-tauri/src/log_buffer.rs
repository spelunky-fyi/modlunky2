//! Runtime tap on tracing output. A tracing-subscriber `Layer` copies
//! every event through a bounded ring buffer AND emits a Tauri
//! `log-line` event once an AppHandle is available (installed at
//! setup-time). The Logs modal in the frontend queries the buffer on
//! open and tails the event stream to live-append new lines.
//!
//! Kept separate from the fmt layer that writes to stderr so tuning one
//! doesn't drag the other along.

use std::collections::VecDeque;
use std::fmt::Write as _;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime, WebviewUrl, WebviewWindowBuilder};
use tracing::field::{Field, Visit};
use tracing::{Event, Level, Subscriber};
use tracing_subscriber::Layer;
use tracing_subscriber::layer::Context;

/// Cap on ring-buffer size. High enough to cover a full debugging
/// session's worth of INFO+ events without pinning too much memory.
const MAX_ENTRIES: usize = 2000;

const LOG_EVENT: &str = "log-line";

/// Serialized wire shape for a single event. camelCase over the wire;
/// the tag `level` is a lowercased Level string so the frontend can
/// filter without a separate map.
#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LogEntry {
    /// Monotonic sequence number the frontend uses to dedupe (event
    /// arrival may race the `get_recent_logs` snapshot). Never resets
    /// during a session.
    pub seq: u64,
    /// Unix millis. Frontend formats.
    pub ts_ms: u64,
    /// Lowercased `Level::to_string()`: "trace"/"debug"/"info"/"warn"/
    /// "error". Matches the level filter dropdown's values.
    pub level: &'static str,
    /// Log target, usually the crate/module path.
    pub target: String,
    /// Formatted message + field values, single line. Multiline events
    /// are collapsed with " | " between fields.
    pub message: String,
}

/// Type-erased emitter: hides the AppHandle's Runtime generic so the
/// buffer stays a single concrete type.
type EmitterFn = Box<dyn Fn(&LogEntry) + Send + Sync>;

struct BufferState {
    entries: VecDeque<LogEntry>,
    seq: AtomicU64,
    /// Filled in during `tauri::Builder::setup`; None until then, in
    /// which case events land only in the buffer.
    emitter: Option<EmitterFn>,
}

impl BufferState {
    fn new() -> Self {
        Self {
            entries: VecDeque::with_capacity(MAX_ENTRIES),
            seq: AtomicU64::new(0),
            emitter: None,
        }
    }

    fn push(&mut self, level: &'static str, target: String, message: String) {
        let seq = self.seq.fetch_add(1, Ordering::Relaxed);
        let ts_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0);
        let entry = LogEntry {
            seq,
            ts_ms,
            level,
            target,
            message,
        };
        if self.entries.len() == MAX_ENTRIES {
            self.entries.pop_front();
        }
        if let Some(emit) = &self.emitter {
            emit(&entry);
        }
        self.entries.push_back(entry);
    }
}

fn buffer() -> &'static Mutex<BufferState> {
    static BUFFER: OnceLock<Mutex<BufferState>> = OnceLock::new();
    BUFFER.get_or_init(|| Mutex::new(BufferState::new()))
}

/// tracing-subscriber layer that formats each event's message + field
/// values into a single line and pushes it into the ring buffer.
pub struct LogBufferLayer;

impl<S: Subscriber> Layer<S> for LogBufferLayer {
    fn on_event(&self, event: &Event<'_>, _ctx: Context<'_, S>) {
        let meta = event.metadata();
        let level = level_slug(meta.level());
        let target = meta.target().to_string();

        let mut visitor = MessageVisitor::default();
        event.record(&mut visitor);
        let message = visitor.into_message();

        let Ok(mut guard) = buffer().lock() else {
            // Poisoned mutex just means an earlier panic mid-push;
            // giving up on this line beats a cascade of panics.
            return;
        };
        guard.push(level, target, message);
    }
}

fn level_slug(level: &Level) -> &'static str {
    match *level {
        Level::TRACE => "trace",
        Level::DEBUG => "debug",
        Level::INFO => "info",
        Level::WARN => "warn",
        Level::ERROR => "error",
    }
}

#[derive(Default)]
struct MessageVisitor {
    message: String,
    fields: String,
}

impl MessageVisitor {
    fn into_message(mut self) -> String {
        if self.message.is_empty() {
            self.message = std::mem::take(&mut self.fields);
        } else if !self.fields.is_empty() {
            self.message.push_str(" | ");
            self.message.push_str(&self.fields);
        }
        self.message
    }

    fn push_field(&mut self, name: &str, value: &dyn std::fmt::Debug) {
        if !self.fields.is_empty() {
            self.fields.push(' ');
        }
        let _ = write!(self.fields, "{name}={value:?}");
    }
}

impl Visit for MessageVisitor {
    fn record_str(&mut self, field: &Field, value: &str) {
        if field.name() == "message" {
            self.message.push_str(value);
        } else {
            self.push_field(field.name(), &value);
        }
    }

    fn record_debug(&mut self, field: &Field, value: &dyn std::fmt::Debug) {
        if field.name() == "message" {
            let _ = write!(self.message, "{value:?}");
        } else {
            self.push_field(field.name(), value);
        }
    }
}

/// Attach a live emitter that forwards each new entry to the frontend
/// via `AppHandle::emit`. Called from `tauri::Builder::setup` once the
/// app is up. Idempotent: replacing the emitter drops the old closure.
pub fn install_emitter<R: Runtime>(app: AppHandle<R>) {
    if let Ok(mut guard) = buffer().lock() {
        guard.emitter = Some(Box::new(move |entry| {
            let _ = app.emit(LOG_EVENT, entry.clone());
        }));
    }
}

/// Snapshot the last `limit` entries (or the whole buffer if None).
/// Cloned out so the caller doesn't hold the buffer's lock.
#[tauri::command]
pub fn get_recent_logs(limit: Option<usize>) -> Vec<LogEntry> {
    let Ok(guard) = buffer().lock() else {
        return Vec::new();
    };
    let cap = limit
        .unwrap_or(guard.entries.len())
        .min(guard.entries.len());
    let start = guard.entries.len().saturating_sub(cap);
    guard.entries.iter().skip(start).cloned().collect()
}

/// Wipe the buffer. The Clear button in the Logs window calls this so
/// the user can start a session with a fresh view.
#[tauri::command]
pub fn clear_logs() {
    if let Ok(mut guard) = buffer().lock() {
        guard.entries.clear();
    }
}

const LOGS_WINDOW_LABEL: &str = "logs";

/// Opens (or focuses if already open) the standalone Logs window.
/// Mirrors `level_editor::open_level_editor_window`: routes through the
/// same app entry, uses an initialization script so the frontend can
/// tell it's the logs window before any of its own JS runs.
///
/// Async for the same reason as the level editor command:
/// `WebviewWindowBuilder::build()` in Tauri v2 needs to round-trip a
/// message to the main runtime thread, and a sync command blocks that
/// reply.
#[tauri::command]
pub async fn open_logs_window(app: AppHandle) -> Result<(), String> {
    if let Some(existing) = app.get_webview_window(LOGS_WINDOW_LABEL) {
        let _ = existing.set_focus();
        let _ = existing.show();
        return Ok(());
    }

    // Same trick as the level editor window: mark this window as the
    // logs shell before any of the app's JS runs so App.tsx can route
    // to <LogsWindow /> synchronously.
    let context = "window.__logsContext = { kind: \"logs\" };";

    let window = WebviewWindowBuilder::new(&app, LOGS_WINDOW_LABEL, WebviewUrl::App("/".into()))
        .title("Logs - Modlunky2")
        .inner_size(1100.0, 720.0)
        .min_inner_size(720.0, 480.0)
        .resizable(true)
        .initialization_script(context)
        .build()
        .map_err(|e| format!("open logs window: {e}"))?;
    if let Err(e) = crate::window_icon::apply_window_icon(&window) {
        tracing::warn!("failed to set crisp window icon on logs: {e}");
    }

    Ok(())
}
