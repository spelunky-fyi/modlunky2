//! Per-tracker plumbing collapsed into a single type-erased struct.
//!
//! Before this module every new tracker meant ~40 lines of copy-paste
//! plumbing sprinkled across mod.rs, consumers.rs, server.rs, lib.rs.
//! Now a tracker gets one `build_slot::<T>()` call in `TrackersState::
//! new`; the rest (routing, config commands, persistence, tick task
//! lifecycle) all funnel through the slot table keyed by slug.
//!
//! Trade-off: config crosses the Rust <-> Rust boundary as
//! `serde_json::Value` instead of the concrete Config type, so the
//! typed `T::Config` only lives inside each slot's closures. Fine in
//! practice because the settings UI already speaks JSON.

use std::sync::Arc;

use ml2_trackers::tracker::{TrackerPayload, TrackerTicker};
use serde::{Serialize, de::DeserializeOwned};
use serde_json::{Map, Value};
use tokio::sync::{oneshot, watch};

use super::tick_task;

/// One tracker's runtime handle. `TrackersState` owns a shared map of
/// these keyed by slug; `ConsumerRegistry` reaches into it to spawn /
/// stop tick tasks; the axum WS handler + tauri commands look up
/// theirs by slug from the URL / arg. Everything crossing the
/// dyn-Fn boundary is Send + Sync via `Arc`.
pub struct TrackerSlot {
    pub slug: &'static str,
    pub payload_tx: watch::Sender<TrackerPayload>,
    pub payload_rx: watch::Receiver<TrackerPayload>,
    /// Snapshot of `T::never_writes_file()` captured at slot construction
    /// time (the ticker's flag is a compile-time constant per type, so a
    /// snapshot is fine). Consumed by the file-mirror spawn to skip
    /// setting up a writer, and surfaced through `get_tracker_file_path`
    /// so the UI hides the file toggle.
    pub never_writes_file: bool,
    /// Spawns a fresh tick task. Called on every 0 -> 1 consumer
    /// transition; the previous tick task was already killed on the
    /// last 1 -> 0 edge.
    spawn_tick: Arc<dyn Fn() -> oneshot::Sender<()> + Send + Sync>,
    /// Serializes the current config into JSON for a tauri
    /// get-command reply.
    get_config: Arc<dyn Fn() -> Value + Send + Sync>,
    /// Applies a JSON config: deserializes, persists to modlunky2
    /// json (stripping any fields that match the default so the file
    /// stays tidy), then pushes it through the watch channel so the
    /// tick task picks it up.
    set_config: Arc<dyn Fn(Value) -> Result<(), String> + Send + Sync>,
}

impl TrackerSlot {
    /// Spawn a tick task; wraps the type-erased spawner.
    pub fn spawn_tick(&self) -> oneshot::Sender<()> {
        (self.spawn_tick)()
    }
    /// Read the current config as JSON.
    pub fn get_config(&self) -> Value {
        (self.get_config)()
    }
    /// Apply and persist a new config.
    pub fn set_config(&self, cfg: Value) -> Result<(), String> {
        (self.set_config)(cfg)
    }
    /// Reset the payload watch to Empty. Called on the 1 -> 0 edge
    /// so the next attach doesn't see the last run's stale label.
    pub fn reset_payload(&self) {
        let _ = self.payload_tx.send(TrackerPayload::Empty);
    }
}

/// Build a slot for one tracker.
///
/// - `slug`: URL segment + WS path + config commands' arg.
/// - `persist_path`: nested key path in the shared modlunky2.json,
///   e.g. `&["trackers", "gem"]`.
/// - `ctor`: factory that returns a fresh `T` for each tick task.
///   Called on every 0 -> 1 consumer edge so the tracker starts
///   from a clean state without carrying stale accumulators from
///   the previous run.
///
/// `T::Config: PartialEq` isn't required by TrackerTicker but is
/// helpful for the strip-defaults persist; skipping it would persist
/// every field verbatim (still valid JSON, just less tidy). JSON
/// equality is used instead so no PartialEq bound is added.
pub fn build_slot<T>(
    slug: &'static str,
    persist_path: &'static [&'static str],
    ctor: impl Fn() -> T + Send + Sync + 'static,
) -> TrackerSlot
where
    T: TrackerTicker,
    T::Config: DeserializeOwned + Default,
{
    let (payload_tx, payload_rx) = watch::channel(TrackerPayload::Empty);
    let initial: T::Config = load_persisted::<T::Config>(persist_path);
    let (config_tx, config_rx) = watch::channel(initial);

    let ctor = Arc::new(ctor);
    // Snapshot the ticker's compile-time capability flags now, then
    // discard the throwaway instance. `never_writes_file()` on the
    // trait is const-in-spirit per type, no per-instance state.
    let never_writes_file = ctor().never_writes_file();
    let spawn_tick = {
        let ctor = ctor.clone();
        let payload_tx = payload_tx.clone();
        let config_rx = config_rx.clone();
        Arc::new(move || tick_task::spawn(ctor(), payload_tx.clone(), config_rx.clone()))
            as Arc<dyn Fn() -> oneshot::Sender<()> + Send + Sync>
    };
    let get_config = {
        let config_rx = config_rx.clone();
        Arc::new(move || serde_json::to_value(config_rx.borrow().clone()).unwrap_or(Value::Null))
            as Arc<dyn Fn() -> Value + Send + Sync>
    };
    let set_config = {
        Arc::new(move |v: Value| -> Result<(), String> {
            let cfg: T::Config =
                serde_json::from_value(v).map_err(|e| format!("decode config: {e}"))?;
            persist_config_stripped(persist_path, &cfg)?;
            let _ = config_tx.send(cfg);
            Ok(())
        }) as Arc<dyn Fn(Value) -> Result<(), String> + Send + Sync>
    };

    TrackerSlot {
        slug,
        payload_tx,
        payload_rx,
        never_writes_file,
        spawn_tick,
        get_config,
        set_config,
    }
}

/// Read the persisted config for a tracker at `path` in modlunky2
/// json, falling back to `T::default()` on missing or malformed
/// blocks. Handles the absent (fresh install) and partial (a version
/// wrote fewer keys) cases uniformly.
fn load_persisted<T: DeserializeOwned + Default>(path: &[&str]) -> T {
    crate::config::get_nested(path)
        .and_then(|v| serde_json::from_value(v).ok())
        .unwrap_or_default()
}

/// Persist `cfg`, dropping any top-level fields that already equal
/// the corresponding field on `T::default()`. A user who never
/// touches a tracker's settings never gets an entry for it in
/// modlunky2.json.
fn persist_config_stripped<T: Serialize + Default>(path: &[&str], cfg: &T) -> Result<(), String> {
    let current = serde_json::to_value(cfg).map_err(|e| format!("encode current: {e}"))?;
    let defaults =
        serde_json::to_value(T::default()).map_err(|e| format!("encode default: {e}"))?;
    let stripped = strip_defaults(&current, &defaults);
    crate::config::set_nested(path, stripped)
}

/// Object diff at the top level only (each tracker's block is flat).
/// Returns None when every field matches defaults so the parent key
/// gets removed entirely.
fn strip_defaults(current: &Value, defaults: &Value) -> Option<Value> {
    match (current, defaults) {
        (Value::Object(cur), Value::Object(def)) => {
            let mut out = Map::new();
            for (k, v) in cur {
                match def.get(k) {
                    Some(dv) if dv == v => {}
                    _ => {
                        out.insert(k.clone(), v.clone());
                    }
                }
            }
            if out.is_empty() {
                None
            } else {
                Some(Value::Object(out))
            }
        }
        // Non-object configs are rare here, but the fallback keeps
        // them round-tripping without corruption.
        _ => Some(current.clone()),
    }
}
