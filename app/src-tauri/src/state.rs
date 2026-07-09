use std::collections::HashSet;
use std::sync::{Arc, Mutex};

use ml2_mods::local::cache::ModCacheHandle;
use ml2_mods::manager::ModManagerHandle;
use tauri::async_runtime::JoinHandle;

use crate::extract::ExtractStatusSlot;
use crate::fyi_ws::FyiWsSlot;
use crate::trackers::TrackersState;

/// The pieces of mod-subsystem state that get swapped atomically on rebuild.
/// Held behind a Mutex on AppState so hot-reload can drop the old task and
/// install a new handle without exposing a half-swapped state to commands.
pub struct ModsSlot {
    pub handle: Option<ModManagerHandle>,
    pub cache_handle: Option<ModCacheHandle>,
    pub task: Option<JoinHandle<()>>,
}

impl ModsSlot {
    pub fn empty() -> Self {
        Self {
            handle: None,
            cache_handle: None,
            task: None,
        }
    }
}

pub struct AppState {
    mods: Arc<Mutex<ModsSlot>>,
    updates_available: Arc<Mutex<HashSet<String>>>,
    trackers: TrackersState,
    fyi_ws: Arc<FyiWsSlot>,
    extract: ExtractStatusSlot,
}

impl AppState {
    pub fn new(
        slot: ModsSlot,
        updates_available: Arc<Mutex<HashSet<String>>>,
        fyi_ws: Arc<FyiWsSlot>,
    ) -> Self {
        Self {
            mods: Arc::new(Mutex::new(slot)),
            updates_available,
            trackers: TrackersState::new(),
            fyi_ws,
            extract: ExtractStatusSlot::new(),
        }
    }

    pub fn extract(&self) -> &ExtractStatusSlot {
        &self.extract
    }

    /// TrackersState's fields are all internally thread-safe
    /// (`Arc<Mutex<...>>` and `watch::channel` handles), so callers
    /// only ever need an immutable reference.
    pub fn trackers(&self) -> &TrackersState {
        &self.trackers
    }

    pub fn fyi_ws(&self) -> &FyiWsSlot {
        &self.fyi_ws
    }

    /// Clones the current ModManagerHandle if one is installed. Callers use
    /// this to avoid holding the mods mutex across await points.
    pub fn mods_handle(&self) -> Option<ModManagerHandle> {
        self.mods.lock().unwrap().handle.clone()
    }

    pub fn cache_handle(&self) -> Option<ModCacheHandle> {
        self.mods.lock().unwrap().cache_handle.clone()
    }

    pub fn mods_slot(&self) -> &Arc<Mutex<ModsSlot>> {
        &self.mods
    }

    pub fn updates_available(&self) -> &Arc<Mutex<HashSet<String>>> {
        &self.updates_available
    }
}
