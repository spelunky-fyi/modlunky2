use anyhow::anyhow;
use async_trait::async_trait;
use derivative::Derivative;
use tokio::select;
use tokio::sync::{mpsc, oneshot};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle};
use tracing::{debug, info, instrument};

use crate::data::Mod;
use crate::local::{Error as LocalError, LocalMods};
use crate::spelunkyfyi::http::{DownloadedMod, RemoteMods};

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

#[derive(Derivative)]
pub struct ModManager<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    api_client: Option<A>,
    commands_rx: mpsc::Receiver<Command>,
    local_mods: L,
}

#[derive(Clone, Derivative)]
#[derivative(Debug)]
pub struct ModManagerHandle {
    #[derivative(Debug = "ignore")]
    commands_tx: mpsc::Sender<Command>,
}

impl<A, L> ModManager<A, L>
where
    A: RemoteMods + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    pub fn new(api_client: Option<A>, local_mods: L) -> (Self, ModManagerHandle) {
        let (commands_tx, commands_rx) = mpsc::channel(1);
        let manager = ModManager {
            api_client,
            commands_rx,
            local_mods,
        };
        let handle = ModManagerHandle { commands_tx };
        (manager, handle)
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
        Ok(())
    }

    #[instrument(skip(self))]
    async fn install_mod(&self, package: ModSource) -> Result<Mod> {
        match package {
            ModSource::Local {
                source_path,
                dest_id,
            } => self
                .local_mods
                .install_local(&source_path, &dest_id)
                .await
                .map_err(|e| e.into()),
            ModSource::Remote { code } => self.install_remote_mod(&code).await,
        }
    }

    #[instrument(skip(self))]
    async fn install_remote_mod(&self, code: &str) -> Result<Mod> {
        let downloaded = self.download_mod(code).await?;
        let r#mod = self.local_mods.install_remote(&downloaded).await?;
        Ok(r#mod)
    }

    #[instrument(skip(self))]
    async fn update_mod(&self, package: ModSource) -> Result<Mod> {
        match package {
            ModSource::Local {
                source_path,
                dest_id,
            } => self
                .local_mods
                .update_local(&source_path, &dest_id)
                .await
                .map_err(|e| e.into()),
            ModSource::Remote { code } => self.update_remote_mod(&code).await,
        }
    }

    #[instrument(skip(self))]
    async fn update_remote_mod(&self, code: &str) -> Result<Mod> {
        let downloaded = self.download_mod(code).await?;
        let r#mod = self.local_mods.update_remote(&downloaded).await?;
        Ok(r#mod)
    }

    #[instrument]
    async fn download_mod(&self, code: &str) -> Result<DownloadedMod> {
        let downloaded = self
            .api_client
            .as_ref()
            .ok_or_else(|| {
                Error::UnknownError(anyhow!(
                    "Tried to access remote mod, but API isn't configured"
                ))
            })?
            .download_mod(code)
            .await
            .map_err(|e| Error::UnknownError(e.into()))?;
        Ok(downloaded)
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

impl From<LocalError> for Error {
    fn from(original: LocalError) -> Self {
        match &original {
            LocalError::AlreadyExists(_) => Error::ModExistsError(original),
            LocalError::NotFound(_) => Error::ModNotFoundError(original),
            LocalError::NonDirectory(_) => Error::ModNonDirectoryError(original),
            LocalError::SourceError(_) => Error::SourceError(original),
            LocalError::DestinationError(_) => Error::DestinationError(original),
            LocalError::IoError(_) => Error::UnknownError(original.into()),
            LocalError::UnknownError(_) => Error::UnknownError(original.into()),
        }
    }
}
