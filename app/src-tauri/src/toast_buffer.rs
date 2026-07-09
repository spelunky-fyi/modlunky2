//! Cross-window toast history. The main window's ToastProvider fire-
//! and-forgets `record_toast` on every push; the Logs window queries
//! `get_recent_toasts` on open (and polls while the tab is active) so
//! it can render the history that fired before it opened. Same ring-
//! buffer shape as `log_buffer`, just with a different payload.

use std::collections::VecDeque;
use std::sync::{Mutex, OnceLock};

use serde::{Deserialize, Serialize};

/// Cap on retained history. Matches the frontend's own bounded
/// `historyRef` cap so behavior is consistent whether the user views
/// via the Rust buffer or an in-window ref.
const MAX_ENTRIES: usize = 200;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ToastEntry {
    /// Client-generated id, unique within a session.
    pub id: String,
    /// "success" | "error" | "info", matching ToastProvider's variants.
    pub variant: String,
    pub message: String,
    /// Client-side unix ms.
    pub ts_ms: u64,
}

fn buffer() -> &'static Mutex<VecDeque<ToastEntry>> {
    static BUFFER: OnceLock<Mutex<VecDeque<ToastEntry>>> = OnceLock::new();
    BUFFER.get_or_init(|| Mutex::new(VecDeque::with_capacity(MAX_ENTRIES)))
}

/// Called by ToastProvider on every push. Silent on bad input (poisoned
/// mutex, oversized message); toast history is a debug affordance,
/// never worth failing the user's action for.
#[tauri::command]
pub fn record_toast(entry: ToastEntry) {
    let Ok(mut guard) = buffer().lock() else {
        return;
    };
    if guard.len() == MAX_ENTRIES {
        guard.pop_front();
    }
    guard.push_back(entry);
}

/// Snapshot the ring buffer. Cloned out so callers don't hold the lock.
#[tauri::command]
pub fn get_recent_toasts() -> Vec<ToastEntry> {
    let Ok(guard) = buffer().lock() else {
        return Vec::new();
    };
    guard.iter().cloned().collect()
}

/// Reset the buffer. Currently unused; wired up for symmetry with
/// `log_buffer::clear_logs` in case the Logs window grows a Clear
/// button for the toast tab.
#[tauri::command]
pub fn clear_toasts() {
    if let Ok(mut guard) = buffer().lock() {
        guard.clear();
    }
}
