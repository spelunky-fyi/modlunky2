use std::{sync::Arc, time::Duration};

use derivative::Derivative;
use rand::{distributions::Uniform, Rng};
use tokio::{
    select,
    sync::{broadcast, Notify},
    task, time,
};
use tracing::{debug, instrument, trace, warn};

use crate::manager::{ListResponse, ModManagerHandle};

use super::http::{Api, Mod as ApiMod};

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("{0}")]
    ShutdownError(#[source] anyhow::Error),
    #[error("{0}")]
    RecvError(#[from] broadcast::error::RecvError),
}

type Result<T> = std::result::Result<T, Error>;

#[derive(Derivative)]
#[derivative(Debug)]
pub struct Poller<A>
where
    A: Api + Send + Sync + 'static,
{
    api_client: A,
    manger_handle: ModManagerHandle,
    #[derivative(Debug = "ignore")]
    mods_tx: broadcast::Sender<ApiMod>,
    poll_interval: Duration,
    #[derivative(Debug = "ignore")]
    shutdown: Arc<Notify>,
    step_dist: Uniform<Duration>,
}

#[derive(Derivative)]
#[derivative(Debug)]
pub struct PollerHandle {
    #[derivative(Debug = "ignore")]
    shutdown: Arc<Notify>,
    #[derivative(Debug = "ignore")]
    mods_rx: broadcast::Receiver<ApiMod>,
}

impl<A> Poller<A>
where
    A: Api + Send + Sync + 'static,
{
    pub fn new(
        api_client: A,
        manger_handle: ModManagerHandle,
        poll_interval: Duration,
        step_max_delay: Duration,
    ) -> (Self, PollerHandle) {
        let (mods_tx, mods_rx) = broadcast::channel(10);

        let poller = Poller {
            api_client,
            manger_handle,
            mods_tx,
            poll_interval,
            shutdown: Arc::new(Notify::new()),
            step_dist: Uniform::new(Duration::from_nanos(0), step_max_delay),
        };
        let handle = PollerHandle {
            mods_rx,
            shutdown: poller.shutdown.clone(),
        };

        (poller, handle)
    }

    /// Consumes the Poller, starting a task and returning its JoinHandle
    pub fn spawn(mut self) -> task::JoinHandle<()> {
        tokio::spawn(async move { self.run().await })
    }

    async fn run(&mut self) {
        let mut poll_interval = time::interval(self.poll_interval);
        // If we fall behind, delay further updates
        poll_interval.set_missed_tick_behavior(time::MissedTickBehavior::Delay);
        let mut ids: Vec<String> = Vec::new();
        loop {
            select! {
                _ = self.shutdown.notified() => break,
                _ = poll_interval.tick(), if ids.is_empty() => ids = self.list_mods().await,
                _ = self.step_sleep(), if !ids.is_empty() => if !self.fetch_mod(ids.pop()).await {break},
            }
        }
    }

    #[instrument(skip(self))]
    async fn list_mods(&self) -> Vec<String> {
        debug!("Listing mods");
        match self.manger_handle.list().await {
            Ok(ListResponse { mods }) => mods
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
    async fn step_sleep(&self) {
        let t = rand::thread_rng().sample(self.step_dist);
        trace!("Step sleeping for {:?}", t);
        time::sleep(t).await
    }

    /// Fetches and broadcasts a mod. Returns false if all receivers have been dropped.
    /// This function takes an Option for ease of use with Vec::pop.
    #[instrument(skip(self))]
    async fn fetch_mod(&self, id: Option<String>) -> bool {
        let id = if let Some(id) = id {
            id
        } else {
            warn!("No mod to fetch");
            return true;
        };
        trace!("Fetching mod {}", id);
        let m = match self.api_client.get_manifest(&id).await {
            Ok(m) => m,
            Err(e) => {
                warn!("Error fetching mod info for {}: {}", id, e);
                return true;
            }
        };
        match self.mods_tx.send(m) {
            Ok(_) => true,
            Err(_) => {
                debug!("All receivers dropped");
                false
            }
        }
    }
}

impl PollerHandle {
    pub async fn shutdown(self) {
        self.shutdown.notify_one()
    }

    pub async fn recv(&mut self) -> Result<ApiMod> {
        let m = self.mods_rx.recv().await?;
        Ok(m)
    }
}
