//! Refcounted lifecycle for per-tracker tick tasks.
//!
//! Every tracker's producer tick task only runs while at least one
//! WS consumer is attached. The Window and Browser Source load the
//! same tracker.html and open the same `/ws/<slug>` connection, so
//! the WS handler alone bumps the count; the tick task's spawn +
//! shutdown is per-slug.
//!
//! Dispatch flows through the shared `SlotMap` so this module has no
//! per-tracker knowledge. Adding a tracker just needs a slot in
//! TrackersState; consumers.rs learns about it via the map.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use tokio::sync::oneshot;

use super::slot::TrackerSlot;

/// Per-slug counter + tick-task shutdown handle.
struct ConsumerEntry {
    count: u32,
    tick_shutdown: Option<oneshot::Sender<()>>,
}

pub type SlotMap = Arc<HashMap<&'static str, TrackerSlot>>;

/// Shared registry cloned into the axum ServerState + used by tauri
/// commands via TrackersState. Cheap Clone: the mutex + slot map are
/// both behind Arcs.
#[derive(Clone)]
pub struct ConsumerRegistry {
    inner: Arc<Mutex<HashMap<String, ConsumerEntry>>>,
    slots: SlotMap,
}

impl ConsumerRegistry {
    pub fn new(slots: SlotMap) -> Self {
        Self {
            inner: Arc::new(Mutex::new(HashMap::new())),
            slots,
        }
    }

    /// Increment the consumer count for `slug`. On the 0 -> 1 edge
    /// spawns the tick task via the slot's registered factory.
    /// Returns a guard whose Drop decrements the count (and kills
    /// the task on the 1 -> 0 edge).
    pub fn attach(&self, slug: &str) -> ConsumerGuard {
        let mut inner = self.inner.lock().unwrap();
        let entry = inner.entry(slug.to_string()).or_insert(ConsumerEntry {
            count: 0,
            tick_shutdown: None,
        });
        entry.count += 1;
        let new_count = entry.count;
        if entry.count == 1 {
            if let Some(slot) = self.slots.get(slug) {
                entry.tick_shutdown = Some(slot.spawn_tick());
                tracing::info!(
                    slug = %slug,
                    consumers = new_count,
                    "tracker tick started (0 -> 1)"
                );
            } else {
                tracing::warn!(slug = %slug, "unknown tracker slug attached");
            }
        } else {
            tracing::debug!(
                slug = %slug,
                consumers = new_count,
                "tracker consumer attached"
            );
        }
        ConsumerGuard {
            registry: self.clone(),
            slug: slug.to_string(),
        }
    }

    /// Kill every running tick task and reset payloads. Called on
    /// `stop_tracker_server`; guards that fire later (WS handlers
    /// finishing) just find their entry drained and noop.
    pub fn shutdown_all(&self) {
        let mut inner = self.inner.lock().unwrap();
        for (slug, mut entry) in inner.drain() {
            if let Some(s) = entry.tick_shutdown.take() {
                let _ = s.send(());
                tracing::info!(slug = %slug, "tracker tick force-stopped (shutdown_all)");
            }
            if let Some(slot) = self.slots.get(slug.as_str()) {
                slot.reset_payload();
            }
        }
    }

    /// Snapshot of per-slug refcount + whether the tick task is live.
    /// Powers the tauri diagnostics command + sidebar Diagnostics card.
    pub fn snapshot(&self) -> Vec<ConsumerSnapshot> {
        let inner = self.inner.lock().unwrap();
        inner
            .iter()
            .map(|(slug, entry)| ConsumerSnapshot {
                slug: slug.clone(),
                consumers: entry.count,
                tick_running: entry.tick_shutdown.is_some(),
            })
            .collect()
    }

    fn detach(&self, slug: &str) {
        let mut inner = self.inner.lock().unwrap();
        let Some(entry) = inner.get_mut(slug) else {
            return;
        };
        entry.count = entry.count.saturating_sub(1);
        let new_count = entry.count;
        if entry.count == 0 {
            if let Some(s) = entry.tick_shutdown.take() {
                let _ = s.send(());
            }
            if let Some(slot) = self.slots.get(slug) {
                slot.reset_payload();
            }
            tracing::info!(
                slug = %slug,
                consumers = new_count,
                "tracker tick stopped (1 -> 0)"
            );
        } else {
            tracing::debug!(
                slug = %slug,
                consumers = new_count,
                "tracker consumer detached"
            );
        }
    }
}

/// Per-slug diagnostics row. `tick_running` is redundant with
/// `consumers > 0` in the normal case; disagreement points to a
/// leaked guard.
#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ConsumerSnapshot {
    pub slug: String,
    pub consumers: u32,
    pub tick_running: bool,
}

/// RAII handle returned by `attach`. Detaches on drop, so a WS
/// handler that panics / bails mid-loop still decrements correctly.
pub struct ConsumerGuard {
    registry: ConsumerRegistry,
    slug: String,
}

impl Drop for ConsumerGuard {
    fn drop(&mut self) {
        self.registry.detach(&self.slug);
    }
}
