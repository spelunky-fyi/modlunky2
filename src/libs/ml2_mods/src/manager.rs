use std::time::Duration;

use anyhow::anyhow;
use async_trait::async_trait;
use derivative::Derivative;
use tokio::select;
use tokio::sync::{broadcast, mpsc, oneshot, watch};
use tokio::time::MissedTickBehavior;
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle};
use tracing::{debug, info, instrument};

use crate::data::{Change, DownloadProgress, Mod, ModProgress};
use crate::local::cache::DetectedChange;
use crate::local::{Error as LocalError, LocalMods};
use crate::spelunkyfyi::{
    http::{DownloadedMod, RemoteMods},
    Error as RemoteError,
};

#[derive(Derivative)]
#[derivative(Debug)]
enum Command {
    Get {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<Mod>>,
    },
    List {
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<Vec<Mod>>>,
    },
    Remove {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<()>>,
    },
    Install {
        package: ModSource,
        resp: oneshot::Sender<Result<Mod>>,
    },
    Update {
        package: ModSource,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<Mod>>,
    },
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ModSource {
    Local {
        source_path: String,
        dest_id: String,
    },
    Remote {
        code: String,
    },
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("{0}")]
    ModExistsError(#[source] LocalError),
    #[error("{0}")]
    ModNotFoundError(#[source] LocalError),
    #[error("{0}")]
    ModNonDirectoryError(#[source] LocalError),

    #[error("{0}")]
    ManifestParseError(#[source] LocalError),
    #[error("{0}")]
    SourceError(#[source] LocalError),
    #[error("{0}")]
    DestinationError(#[source] LocalError),

    #[error("Channel error: {0}")]
    ChannelError(#[source] anyhow::Error),
    #[error("Unknown error: {0}")]
    UnknownError(#[source] anyhow::Error),
}

pub type Result<R> = std::result::Result<R, Error>;

pub const DEFAULT_RECEIVING_INTERVAL: Duration = Duration::from_millis(20);

#[derive(Derivative)]
pub struct ModManager<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    api_client: Option<A>,
    #[derivative(Debug = "ignore")]
    commands_rx: mpsc::Receiver<Command>,
    #[derivative(Debug = "ignore")]
    detected_rx: broadcast::Receiver<DetectedChange>,
    #[derivative(Debug = "ignore")]
    changes_tx: broadcast::Sender<Change>,
    local_mods: L,
    receiving_interval: Duration,
}

#[derive(Clone, Derivative)]
#[derivative(Debug)]
pub struct ModManagerHandle {
    #[derivative(Debug = "ignore")]
    commands_tx: mpsc::Sender<Command>,
}

#[derive(Clone, Copy, Debug)]
enum OpKind {
    Install(),
    Update(),
}

impl<A, L> ModManager<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    pub fn new(
        api_client: Option<A>,
        local_mods: L,
        changes_tx: broadcast::Sender<Change>,
        detected_rx: broadcast::Receiver<DetectedChange>,
        receiving_interval: Duration,
    ) -> (Self, ModManagerHandle) {
        let (commands_tx, commands_rx) = mpsc::channel(1);
        let manager = ModManager {
            api_client,
            changes_tx,
            commands_rx,
            detected_rx,
            local_mods,
            receiving_interval,
        };
        let handle = ModManagerHandle { commands_tx };
        (manager, handle)
    }

    #[instrument]
    async fn handle_detected(&self, detected: DetectedChange) {
        match detected {
            DetectedChange::Added(r#mod) => self.send_change(Change::Add {
                progress: ModProgress::Finished { r#mod },
            }),
            DetectedChange::Removed(id) => self.send_change(Change::Remove { id }),
            DetectedChange::Updated(r#mod) => self.send_change(Change::Update {
                progress: ModProgress::Finished { r#mod },
            }),
            DetectedChange::NewVersion(id) => self.send_change(Change::NewVersion { id }),
        }
    }

    #[instrument]
    fn send_change(&self, change: Change) {
        let _ = self.changes_tx.send(change);
    }

    #[instrument]
    async fn handle_command(&self, cmd: Command) {
        debug!("Processing command");
        match cmd {
            Command::Get { id, resp } => {
                if resp.send(self.get_mod(&id).await).is_err() {
                    info!("Receiver dropped for Get({:?})", id);
                }
            }
            Command::List { resp } => {
                if resp.send(self.list_mods().await).is_err() {
                    info!("Receiver dropped for List()");
                }
            }
            Command::Remove { id, resp } => {
                if resp.send(self.remove_mod(&id).await).is_err() {
                    info!("Receiver dropped for Remove({:?})", id);
                }
            }
            Command::Install { package, resp } => {
                if resp.send(self.install_mod(package.clone()).await).is_err() {
                    info!("Receiver dropped for Install({:?})", package);
                }
            }
            Command::Update { package, resp } => {
                if resp.send(self.update_mod(package.clone()).await).is_err() {
                    info!("Receiver dropped for Install({:?})", package);
                }
            }
        }
    }

    #[instrument(skip(self))]
    async fn get_mod(&self, id: &str) -> Result<Mod> {
        Ok(self.local_mods.get(id).await?)
    }

    #[instrument(skip(self))]
    async fn list_mods(&self) -> Result<Vec<Mod>> {
        Ok(self.local_mods.list().await?)
    }

    #[instrument(skip(self))]
    async fn remove_mod(&self, id: &str) -> Result<()> {
        self.local_mods.remove(id).await?;
        self.send_change(Change::Remove { id: id.to_string() });
        Ok(())
    }

    #[instrument(skip(self))]
    async fn install_mod(&self, package: ModSource) -> Result<Mod> {
        match package {
            ModSource::Local {
                source_path,
                dest_id,
            } => self.install_local_mod(&source_path, &dest_id).await,
            ModSource::Remote { code } => self.install_remote_mod(&code).await,
        }
    }

    #[instrument(skip(self))]
    async fn install_local_mod(&self, source_path: &str, dest_id: &str) -> Result<Mod> {
        self.send_change(Change::Add {
            progress: ModProgress::Started {
                id: dest_id.to_string(),
            },
        });

        let r#mod = self.local_mods.install_local(source_path, dest_id).await?;

        self.send_change(Change::Add {
            progress: ModProgress::Finished {
                r#mod: r#mod.clone(),
            },
        });
        Ok(r#mod)
    }

    #[instrument(skip(self))]
    async fn install_remote_mod(&self, code: &str) -> Result<Mod> {
        let id = format!("fyi.{}", code);
        self.send_change(Change::Add {
            progress: ModProgress::Started { id },
        });

        let downloaded = self.download_mod(code, OpKind::Install()).await?;
        let r#mod = self.local_mods.install_remote(&downloaded).await?;

        self.send_change(Change::Add {
            progress: ModProgress::Finished {
                r#mod: r#mod.clone(),
            },
        });
        Ok(r#mod)
    }

    #[instrument(skip(self))]
    async fn update_mod(&self, package: ModSource) -> Result<Mod> {
        match package {
            ModSource::Local {
                source_path,
                dest_id,
            } => self.update_local_mod(&source_path, &dest_id).await,
            ModSource::Remote { code } => self.update_remote_mod(&code).await,
        }
    }

    #[instrument(skip(self))]
    async fn update_local_mod(&self, source_path: &str, dest_id: &str) -> Result<Mod> {
        self.send_change(Change::Update {
            progress: ModProgress::Started {
                id: dest_id.to_string(),
            },
        });

        let r#mod = self.local_mods.update_local(source_path, dest_id).await?;

        self.send_change(Change::Update {
            progress: ModProgress::Finished {
                r#mod: r#mod.clone(),
            },
        });
        Ok(r#mod)
    }

    #[instrument(skip(self))]
    async fn update_remote_mod(&self, code: &str) -> Result<Mod> {
        let id = format!("fyi.{}", code);
        self.send_change(Change::Update {
            progress: ModProgress::Started { id },
        });

        let downloaded = self.download_mod(code, OpKind::Update()).await?;
        let r#mod = self.local_mods.update_remote(&downloaded).await?;

        self.send_change(Change::Update {
            progress: ModProgress::Finished {
                r#mod: r#mod.clone(),
            },
        });
        Ok(r#mod)
    }

    #[instrument]
    fn send_download_progress(
        &self,
        id: &str,
        op_kind: OpKind,
        main_progress: &DownloadProgress,
        logo_progress: &DownloadProgress,
    ) {
        let progress = ModProgress::Downloading {
            id: id.to_string(),
            main_file: main_progress.clone(),
            logo_file: logo_progress.clone(),
        };
        match op_kind {
            OpKind::Install() => self.send_change(Change::Add { progress }),
            OpKind::Update() => self.send_change(Change::Update { progress }),
        }
    }

    #[instrument]
    async fn download_mod(&self, code: &str, op_kind: OpKind) -> Result<DownloadedMod> {
        let id = format!("fyi.{}", code);
        // TODO send  updates
        let api_client = self.api_client.as_ref().ok_or_else(|| {
            Error::UnknownError(anyhow!(
                "Tried to access remote mod, but API isn't configured"
            ))
        })?;

        let (main_tx, mut main_rx) = watch::channel(DownloadProgress::Waiting());
        let (logo_tx, mut logo_rx) = watch::channel(DownloadProgress::Waiting());

        // We throttle updates for download progress, because chunks often arrive every 2ms or less.
        let mut last_main = DownloadProgress::Waiting();
        let mut last_logo = DownloadProgress::Waiting();
        let mut bytes_interval = tokio::time::interval(self.receiving_interval);
        bytes_interval.set_missed_tick_behavior(MissedTickBehavior::Delay);
        let mut download_op = api_client.download_mod(code, &main_tx, &logo_tx);
        let mut unsent_update = false;
        loop {
            select! {
                res = (&mut download_op) => {
                    self.send_download_progress(
                        &id,
                        op_kind,
                        &DownloadProgress::Finished(),
                        &DownloadProgress::Finished(),
                    );
                    return Ok(res?)
                }
                _ = bytes_interval.tick(), if unsent_update => {
                    unsent_update = false;
                    self.send_download_progress(&id, op_kind, &last_main, &last_logo);
                }
                Ok(()) = main_rx.changed() => {
                    last_main = main_rx.borrow().clone();
                    match &last_main {
                        DownloadProgress::Receiving { .. } => {
                            unsent_update = true;
                        }
                        _ => {
                            unsent_update = false;
                            self.send_download_progress(&id, op_kind, &last_main, &last_logo)
                        }
                    }
                }
                Ok(()) = logo_rx.changed() => {
                    last_logo = logo_rx.borrow().clone();
                    match &last_logo {
                        DownloadProgress::Receiving { .. } => {
                            unsent_update = true;
                        }
                        _ => {
                            unsent_update = false;
                            self.send_download_progress(&id, op_kind, &last_main, &last_logo)
                        }
                    }
                }
            }
        }
    }
}

impl<A, L> std::fmt::Debug for ModManager<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Omit all contents
        f.debug_struct("ModManager").finish()
    }
}

#[async_trait]
impl<A, L> IntoSubsystem<Error> for ModManager<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    #[instrument(skip_all)]
    async fn run(mut self, subsystem: SubsystemHandle) -> Result<()> {
        loop {
            select! {
                _ = subsystem.on_shutdown_requested() => break,
                Some(cmd) = self.commands_rx.recv() => self.handle_command(cmd).await,
                Ok(detected) = self.detected_rx.recv() => self.handle_detected(detected).await,
            }
        }
        Ok(())
    }
}

impl ModManagerHandle {
    #[instrument]
    pub async fn get(&self, mod_id: &str) -> Result<Mod> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::Get {
                id: mod_id.to_string(),
                resp: tx,
            })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }

    #[instrument]
    pub async fn list(&self) -> Result<Vec<Mod>> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::List { resp: tx })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }

    #[instrument]
    pub async fn remove(&self, mod_id: &str) -> Result<()> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::Remove {
                id: mod_id.to_string(),
                resp: tx,
            })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }

    #[instrument]
    pub async fn install(&self, package: &ModSource) -> Result<Mod> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::Install {
                package: package.clone(),
                resp: tx,
            })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }

    #[instrument]
    pub async fn update(&self, package: &ModSource) -> Result<Mod> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::Update {
                package: package.clone(),
                resp: tx,
            })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }
}

impl From<RemoteError> for Error {
    fn from(err: RemoteError) -> Self {
        Error::UnknownError(err.into())
    }
}

impl From<LocalError> for Error {
    fn from(err: LocalError) -> Self {
        match err {
            LocalError::AlreadyExists(_) => Error::ModExistsError(err),
            LocalError::NotFound(_) => Error::ModNotFoundError(err),
            LocalError::NonDirectory(_) => Error::ModNonDirectoryError(err),
            LocalError::SourceError(_) => Error::SourceError(err),
            LocalError::DestinationError(_) => Error::DestinationError(err),
            LocalError::IoError(_) => Error::UnknownError(err.into()),
            LocalError::UnknownError(_) => Error::UnknownError(err.into()),
        }
    }
}
