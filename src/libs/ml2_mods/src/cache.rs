use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
    time::Duration,
};

use async_trait::async_trait;
use derivative::Derivative;
use rand::{distributions::Uniform, Rng};
use tokio::{
    select,
    sync::{broadcast, mpsc, Mutex},
    time,
};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle};
use tracing::{debug, instrument, trace, warn};

use crate::{
    data::Change,
    local::Error,
    spelunkyfyi::http::{Api, DownloadedMod, Mod as ApiMod},
};
use crate::{
    data::Mod,
    local::{LocalMods, Result},
};

#[derive(Clone, Derivative)]
#[derivative(Debug)]
pub struct ModCache<A, L>
where
    A: Api + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    api_client: Option<A>,
    api_poll_interval: Duration,
    api_step_dist: Uniform<Duration>,
    cache: Arc<Mutex<HashMap<String, Mod>>>,
    #[derivative(Debug = "ignore")]
    changes_tx: broadcast::Sender<Change>,
    local_mods: L,
    local_scan_interval: Duration,
    #[derivative(Debug = "ignore")]
    ready_tx: mpsc::Sender<()>,
}

#[derive(Derivative)]
#[derivative(Debug)]
pub struct ModCacheHandle {
    #[derivative(Debug = "ignore")]
    ready_rx: mpsc::Receiver<()>,
}

impl<A, L> ModCache<A, L>
where
    A: Api + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    pub fn new(
        api_client: Option<A>,
        api_poll_interval: Duration,
        api_step_max_delay: Duration,
        changes_tx: broadcast::Sender<Change>,
        local_mods: L,
        local_scan_interval: Duration,
    ) -> (Self, ModCacheHandle) {
        let (ready_tx, ready_rx) = mpsc::channel(1);
        let poller = ModCache {
            api_client,
            api_poll_interval,
            api_step_dist: Uniform::new(Duration::from_nanos(0), api_step_max_delay),
            cache: Arc::new(Mutex::new(HashMap::new())),
            changes_tx,
            local_mods,
            local_scan_interval,
            ready_tx,
        };
        let handle = ModCacheHandle { ready_rx };

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

    #[instrument(skip(self))]
    async fn fetch_sleep(&self) {
        let t = rand::thread_rng().sample(self.api_step_dist);
        trace!("Step sleeping for {:?}", t);
        time::sleep(t).await
    }

    /// Fetches and broadcasts a mod. Returns false if all receivers have been dropped.
    /// This function takes an Option for ease of use with Vec::pop.
    #[instrument(skip(self))]
    async fn fetch_mod(&self, id: Option<String>) {
        let id = if let Some(id) = id {
            id
        } else {
            warn!("No mod to fetch");
            return;
        };
        trace!("Fetching mod {}", id);
        let api_client = if let Some(c) = self.api_client.as_ref() {
            c
        } else {
            warn!("Trying to fetch mods without API client");
            return;
        };
        let update_res = match api_client.get_manifest(&id).await {
            Ok(m) => self.update_latest_json(&m).await,
            Err(e) => {
                warn!("Error fetching mod info for {}: {}", id, e);
                return;
            }
        };
        if let Err(e) = update_res {
            warn!("Error updating latest {}: {}", id, e);
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
            self.send_change(Change::Removed { id }).await;
        }

        for new in mods.iter() {
            let old = cache.get(&new.id);
            let change = match old.map(|o| o == new) {
                None => Some(Change::Added { r#mod: new.clone() }),
                Some(true) => None,
                Some(false) => Some(Change::Updated { r#mod: new.clone() }),
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
        self.send_change(Change::Added { r#mod: new.clone() }).await
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
        self.send_change(Change::Added { r#mod: new.clone() }).await
    }

    #[instrument(skip(self))]
    async fn send_change(&self, change: Change) {
        trace!("Sending change {:?}", change);
        if self.changes_tx.send(change).is_err() {
            debug!("All receivers dropped");
        }
    }
}

#[async_trait]
impl<A, L> IntoSubsystem<Error> for ModCache<A, L>
where
    A: Api + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    #[instrument(skip_all)]
    async fn run(mut self, subsystem: SubsystemHandle) -> Result<()> {
        self.populate_cache().await;
        let _ = self.ready_tx.send(()).await;

        let mut api_interval = time::interval(self.api_poll_interval);
        let mut local_scan_interval = time::interval(self.local_scan_interval);
        // If we fall behind, delay further updates
        api_interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);
        local_scan_interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);
        let mut codes: Vec<String> = Vec::new();
        loop {
            select! {
                _ = subsystem.on_shutdown_requested() => break,
                _ = local_scan_interval.tick() => self.local_scan().await,
                _ = api_interval.tick(), if codes.is_empty() => codes = self.list_mods_to_fetch().await,
                _ = self.fetch_sleep(), if !codes.is_empty() => self.fetch_mod(codes.pop()).await,
            }
        }
        Ok(())
    }
}

#[async_trait]
impl<A, L> LocalMods for ModCache<A, L>
where
    A: Api + Send + Sync + 'static,
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
        self.send_change(Change::Removed { id: id.to_string() })
            .await;
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
            self.send_change(Change::NewVersion { id: id.clone() })
                .await
        }
        Ok(changed)
    }
}

impl ModCacheHandle {
    pub async fn ready(mut self) {
        self.ready_rx.recv().await;
    }
}
