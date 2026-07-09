use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
    time::Duration,
};

use async_trait::async_trait;
use derive_more::Debug;
use serde::{Deserialize, Serialize};
use tokio::{
    select,
    sync::{Mutex, broadcast, mpsc, oneshot},
    time,
};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle};
use tracing::{debug, instrument, trace, warn};

use super::{LocalMods, ModLogo, Result};
use crate::{
    data::Mod,
    local::Error,
    spelunkyfyi::http::{DownloadedMod, Mod as ApiMod, RemoteMods},
};

#[derive(Clone, Debug)]
pub struct ModCache<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    api_client: Option<A>,
    api_poll_interval: Duration,
    cache: Arc<Mutex<HashMap<String, Mod>>>,
    #[debug(skip)]
    detected_tx: broadcast::Sender<DetectedChange>,
    local_mods: L,
    local_scan_interval: Duration,
    #[debug(skip)]
    ready_tx: mpsc::Sender<()>,
    /// On-demand scan request channel. Senders (through `ModCacheHandle`)
    /// hand off a oneshot sender to request an immediate `local_scan()`
    /// and get notified when it finishes. Wrapped in Arc<Mutex<Option<..>>
    /// so `ModCache` can stay `Clone` (used by both the running subsystem
    /// and the `ModManager` that borrows it as `LocalMods`); the running
    /// subsystem takes ownership by `Option::take` inside `run`.
    #[debug(skip)]
    scan_req_rx: Arc<Mutex<Option<mpsc::Receiver<oneshot::Sender<()>>>>>,
}

#[derive(Clone, Debug)]
pub struct ModCacheHandle {
    #[debug(skip)]
    ready_rx: Arc<Mutex<mpsc::Receiver<()>>>,
    #[debug(skip)]
    scan_req_tx: mpsc::Sender<oneshot::Sender<()>>,
}

impl ModCacheHandle {
    pub async fn ready(self) {
        let mut rx = self.ready_rx.lock().await;
        rx.recv().await;
    }

    /// Asks the running ModCache to perform an immediate `local_scan()` and
    /// returns once it's done. Use when the caller knows the mods folder
    /// changed outside the cache-managed flow (e.g. the level editor just
    /// scaffolded a new pack) and needs the fresh state to be reflected
    /// before the poll interval elapses.
    pub async fn scan_now(&self) -> std::result::Result<(), &'static str> {
        let (tx, rx) = oneshot::channel();
        self.scan_req_tx
            .send(tx)
            .await
            .map_err(|_| "ModCache is not running")?;
        rx.await.map_err(|_| "ModCache dropped the scan request")?;
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum DetectedChange {
    Added(Mod),
    Updated(Mod),
    Removed(String),
    NewVersion(String),
}

impl<A, L> ModCache<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    pub fn new(
        api_client: Option<A>,
        api_poll_interval: Duration,
        detected_tx: broadcast::Sender<DetectedChange>,
        local_mods: L,
        local_scan_interval: Duration,
    ) -> (Self, ModCacheHandle) {
        let (ready_tx, ready_rx) = mpsc::channel(1);
        let (scan_req_tx, scan_req_rx) = mpsc::channel(4);
        let poller = ModCache {
            api_client,
            api_poll_interval,
            cache: Arc::new(Mutex::new(HashMap::new())),
            detected_tx,
            local_mods,
            local_scan_interval,
            ready_tx,
            scan_req_rx: Arc::new(Mutex::new(Some(scan_req_rx))),
        };
        let handle = ModCacheHandle {
            ready_rx: Arc::new(Mutex::new(ready_rx)),
            scan_req_tx,
        };

        (poller, handle)
    }

    #[instrument(skip(self))]
    async fn list_mods_to_fetch(&self) -> Vec<String> {
        if self.api_client.is_none() {
            return Vec::new();
        }
        debug!("Listing mods");
        match self.list().await {
            Ok(mods) => mods
                .into_iter()
                .filter_map(|m| m.manifest.map(|mm| mm.slug))
                .collect(),
            Err(e) => {
                warn!("Error listing mods: {}", e);
                Vec::new()
            }
        }
    }

    /// One batched round-trip against the site's check-updates endpoint,
    /// covering every installed fyi mod. Replaces the previous "list
    /// slugs, then hit /api/mods/<slug>/ once per mod with a jittered
    /// sleep between calls" pattern with one request per poll interval
    /// instead of N. Silent on network failure so a briefly unreachable
    /// server doesn't spam the log.
    #[instrument(skip(self))]
    async fn check_updates_batch(&self) {
        let Some(api_client) = self.api_client.as_ref() else {
            return;
        };
        let slugs = self.list_mods_to_fetch().await;
        if slugs.is_empty() {
            return;
        }
        let slug_refs: Vec<&str> = slugs.iter().map(String::as_str).collect();
        let response = match api_client.check_updates(&slug_refs).await {
            Ok(r) => r,
            Err(e) => {
                warn!("check_updates batch failed: {}", e);
                return;
            }
        };
        // The trait impl on ModCache (below) delegates to the inner
        // LocalMods AND broadcasts a NewVersion change on the detected
        // channel; drive it through the trait so downstream consumers
        // see the update the same way they used to.
        for (slug, mod_file) in &response.mods {
            match self.apply_latest_check_result(slug, &mod_file.id).await {
                Ok(_) => {}
                Err(e) => warn!("Error updating latest.json for {}: {}", slug, e),
            }
        }
    }

    #[instrument(skip(self))]
    async fn populate_cache(&self) {
        debug!("Populating cache");
        let mods = match self.local_mods.list().await {
            Ok(m) => m,
            Err(e) => {
                warn!("Initial cache population failed: {:?}", e);
                return;
            }
        };
        let mut cache = self.cache.lock().await;
        if !cache.is_empty() {
            warn!("Attempted to populate non-empty cache");
            return;
        }
        for m in mods {
            cache.insert(m.id.clone(), m);
        }
    }

    #[instrument(skip(self))]
    async fn local_scan(&self) {
        debug!("Updating local cache");
        let mods = match self.local_mods.list().await {
            Ok(m) => m,
            Err(e) => {
                warn!("Error listing local mods {:?}", e);
                return;
            }
        };

        let mut cache = self.cache.lock().await;
        let new_ids: HashSet<String> = mods.iter().map(|m| m.id.to_string()).collect();
        let removed: Vec<String> = cache
            .keys()
            .filter(|id| !new_ids.contains(*id))
            .cloned()
            .collect();
        for id in removed {
            cache.remove(&id);
            self.send_change(DetectedChange::Removed(id)).await;
        }

        for new in mods.iter() {
            let old = cache.get(&new.id);
            let change = match old.map(|o| o == new) {
                None => Some(DetectedChange::Added(new.clone())),
                Some(true) => None,
                Some(false) => Some(DetectedChange::Updated(new.clone())),
            };
            if let Some(c) = change {
                cache.insert(new.id.to_string(), new.clone());
                self.send_change(c).await;
            }
        }
    }

    #[instrument(skip(self))]
    async fn mod_installed(&self, new: &Mod) {
        let old = self.cache.lock().await.insert(new.id.clone(), new.clone());
        if old.is_some() {
            warn!("When installing mod {:?}, it was already in cache", new.id);
        }
    }

    #[instrument(skip(self))]
    async fn mod_updated(&self, new: &Mod) {
        let old = self.cache.lock().await.insert(new.id.clone(), new.clone());
        if let Some(m) = old {
            if &m == new {
                warn!("When updating mod {:?}, nothing changed", new.id);
            }
        } else {
            warn!("When updating mod {:?}, it was already in cache", new.id);
        }
    }

    #[instrument(skip(self))]
    async fn send_change(&self, change: DetectedChange) {
        trace!("Sending change {:?}", change);
        if self.detected_tx.send(change).is_err() {
            debug!("All receivers dropped");
        }
    }
}

impl<A, L> IntoSubsystem<Error> for ModCache<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    #[instrument(skip_all)]
    async fn run(self, subsystem: &mut SubsystemHandle) -> Result<()> {
        self.populate_cache().await;
        let _ = self.ready_tx.send(()).await;

        // Move the request channel out of `self` so `select!` can borrow it
        // mutably at the same time as `self.local_scan()` and friends (all
        // `&self`). Since ModCache is `Clone`, the receiver lives behind
        // an Arc<Mutex<Option<..>>>; only the first `run` grabs it.
        let mut scan_req_rx = self
            .scan_req_rx
            .lock()
            .await
            .take()
            .expect("ModCache::run called twice on shared cache");

        let mut api_interval = time::interval(self.api_poll_interval);
        let mut local_scan_interval = time::interval(self.local_scan_interval);
        // If ticks fall behind, delay further updates
        api_interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);
        local_scan_interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);
        loop {
            select! {
                _ = subsystem.on_shutdown_requested() => break,
                _ = local_scan_interval.tick() => self.local_scan().await,
                Some(resp) = scan_req_rx.recv() => {
                    self.local_scan().await;
                    let _ = resp.send(());
                }
                _ = api_interval.tick() => self.check_updates_batch().await,
            }
        }
        Ok(())
    }
}

#[async_trait]
impl<A, L> LocalMods for ModCache<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    #[instrument(skip(self))]
    async fn get(&self, id: &str) -> Result<Mod> {
        let cache = self.cache.lock().await;
        let m = cache
            .get(id)
            .ok_or_else(|| Error::NotFound(id.to_string()))?;
        Ok(m.clone())
    }

    #[instrument(skip(self))]
    async fn list(&self) -> Result<Vec<Mod>> {
        let mods = self.cache.lock().await.values().cloned().collect();
        Ok(mods)
    }

    #[instrument(skip(self))]
    async fn remove(&self, id: &str) -> Result<()> {
        self.local_mods.remove(id).await?;
        Ok(())
    }

    #[instrument(skip(self))]
    async fn install_local(&self, source: &str, dest_id: &str) -> Result<Mod> {
        let new = self.local_mods.install_local(source, dest_id).await?;
        self.mod_installed(&new).await;
        Ok(new)
    }

    #[instrument(skip_all)]
    async fn install_remote(&self, downloaded: &DownloadedMod) -> Result<Mod> {
        let new = self.local_mods.install_remote(downloaded).await?;
        self.mod_installed(&new).await;
        Ok(new)
    }

    #[instrument(skip(self))]
    async fn update_local(&self, source: &str, dest_id: &str) -> Result<Mod> {
        let new = self.local_mods.update_local(source, dest_id).await?;
        self.mod_updated(&new).await;
        Ok(new)
    }

    #[instrument(skip_all)]
    async fn update_remote(&self, downloaded: &DownloadedMod) -> Result<Mod> {
        let new = self.local_mods.update_remote(downloaded).await?;
        self.mod_updated(&new).await;
        Ok(new)
    }

    #[instrument(skip_all)]
    async fn update_latest_json(&self, api_mod: &ApiMod) -> Result<Option<String>> {
        let changed = self.local_mods.update_latest_json(api_mod).await?;
        if let Some(id) = changed.as_ref() {
            self.send_change(DetectedChange::NewVersion(id.clone()))
                .await
        }
        Ok(changed)
    }

    #[instrument(skip(self))]
    async fn apply_latest_check_result(
        &self,
        slug: &str,
        mod_file_id: &str,
    ) -> Result<Option<String>> {
        let changed = self
            .local_mods
            .apply_latest_check_result(slug, mod_file_id)
            .await?;
        if let Some(id) = changed.as_ref() {
            self.send_change(DetectedChange::NewVersion(id.clone()))
                .await
        }
        Ok(changed)
    }

    #[instrument(skip(self))]
    async fn get_mod_logo(&self, id: &str) -> Result<ModLogo> {
        self.local_mods.get_mod_logo(id).await
    }
}
