use anyhow::anyhow;
use derivative::Derivative;
use serde::Serialize;
use tokio::sync::{broadcast, mpsc, oneshot};
use tokio::{select, task};
use tracing::{debug, info, instrument, trace, warn};

use crate::data::{ManagerError, Mod};
use crate::local::{Error as LocalError, LocalMods};
use crate::spelunkyfyi::http::{Api, Mod as ApiMod};

#[derive(Derivative)]
#[derivative(Debug)]
enum Command {
    Get {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<GetResponse>>,
    },
    List {
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<ListResponse>>,
    },
    Remove {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<RemoveResponse>>,
    },
    Install {
        package: InstallPackage,
        resp: oneshot::Sender<Result<InstallResponse>>,
    },
    Update {
        package: InstallPackage,
        #[derivative(Debug = "ignore")]
        _resp: oneshot::Sender<Result<UpdateResponse>>,
    },
    Subscribe {
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<broadcast::Receiver<String>>,
    },
    Shutdown(),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum InstallPackage {
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

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GetResponse {
    pub r#mod: Mod,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ListResponse {
    pub mods: Vec<Mod>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RemoveResponse {}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InstallResponse {
    pub r#mod: Mod,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UpdateResponse {
    pub r#mod: Mod,
}

#[derive(Derivative)]
pub struct ModManager<A, L>
where
    A: Api + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    api_client: Option<A>,
    commands_rx: mpsc::Receiver<Command>,
    local_mods: L,
    mods_rx: broadcast::Receiver<ApiMod>,
    updates_tx: broadcast::Sender<String>,
}

#[derive(Derivative)]
#[derivative(Debug)]
pub struct ModManagerHandle {
    #[derivative(Debug = "ignore")]
    commands_tx: mpsc::Sender<Command>,
    updates_rx: broadcast::Receiver<String>,
}

impl<A, L> ModManager<A, L>
where
    A: Api + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    pub fn new(
        api_client: Option<A>,
        local_mods: L,
        mods_rx: broadcast::Receiver<ApiMod>,
    ) -> (Self, ModManagerHandle) {
        let (commands_tx, commands_rx) = mpsc::channel(1);
        let (updates_tx, updates_rx) = broadcast::channel(5);
        let manager = ModManager {
            api_client,
            commands_rx,
            local_mods,
            mods_rx,
            updates_tx,
        };
        let handle = ModManagerHandle {
            commands_tx,
            updates_rx,
        };
        (manager, handle)
    }

    /// Consumes the ModManager, starting a task and returning its [JoinHandle].
    pub fn spawn(mut self) -> task::JoinHandle<()> {
        tokio::spawn(async move { self.run().await })
    }

    #[instrument(skip(self))]
    async fn run(&mut self) -> () {
        loop {
            select! {
                opt_cmd = self.commands_rx.recv() => match opt_cmd {
                    Some(cmd) => self.handle_command(cmd).await,
                    None => break,
                },
                mod_res = self.mods_rx.recv() => match mod_res {
                    Ok(m) => self.handle_mod_polled(m).await,
                    Err(e) => debug!("Poller lost: {:?}", e),
                }
            }
        }
    }

    #[instrument(skip(self, api_mod))]
    async fn handle_mod_polled(&self, api_mod: ApiMod) {
        trace!("Handling mod polled {}", api_mod.slug);
        match self.local_mods.update_latest(&api_mod).await {
            Ok(Some(id)) => {
                if let Err(e) = self.updates_tx.send(id) {
                    warn!("No update listeners: {:?}", e);
                }
            }
            Ok(None) => {}
            Err(e) => warn!("Updating latest.json failed: {:?}", e),
        }
    }

    #[instrument(skip(self))]
    async fn handle_command(&mut self, cmd: Command) {
        debug!("Processing command {:?}", cmd);
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
            Command::Subscribe { resp } => {
                if resp.send(self.updates_tx.subscribe()).is_err() {
                    info!("Receiver dropped for Subscribe()");
                }
            }
            Command::Shutdown() => {
                // Prevent additional messages from being sent
                self.commands_rx.close();
            }
            _ => unimplemented!(),
        }
    }

    #[instrument(skip(self))]
    async fn get_mod(&self, id: &str) -> Result<GetResponse> {
        let r#mod = self.local_mods.get(id).await?;

        Ok(GetResponse { r#mod })
    }

    #[instrument(skip(self))]
    async fn list_mods(&self) -> Result<ListResponse> {
        let mods = self.local_mods.list().await?;
        Ok(ListResponse { mods })
    }

    #[instrument(skip(self))]
    async fn remove_mod(&self, id: &str) -> Result<RemoveResponse> {
        self.local_mods.remove(id).await?;
        Ok(RemoveResponse {})
    }

    #[instrument(skip(self))]
    async fn install_mod(&self, package: InstallPackage) -> Result<InstallResponse> {
        match package {
            InstallPackage::Local {
                source_path,
                dest_id,
            } => self.install_local_mod(&source_path, &dest_id).await,
            InstallPackage::Remote { code } => self.install_remote_mod(&code).await,
        }
    }

    #[instrument(skip(self))]
    async fn install_local_mod(&self, source: &str, dest_id: &str) -> Result<InstallResponse> {
        let r#mod = self.local_mods.install_local(source, dest_id).await?;
        Ok(InstallResponse { r#mod })
    }

    #[instrument(skip(self))]
    async fn install_remote_mod(&self, code: &str) -> Result<InstallResponse> {
        let downloaded = self
            .api_client
            .as_ref()
            .ok_or_else(|| {
                Error::UnknownError(anyhow!(
                    "Tried to install remote mod, but API isn't configured"
                ))
            })?
            .download_mod(code)
            .await
            .map_err(|e| Error::UnknownError(e.into()))?;
        let r#mod = self.local_mods.install_remote(&downloaded).await?;

        Ok(InstallResponse { r#mod })
    }
}

impl<A, L> std::fmt::Debug for ModManager<A, L>
where
    A: Api + Send + Sync + 'static,
    L: LocalMods + Send + Sync + 'static,
{
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Omit all contents
        f.debug_struct("ModManager").finish()
    }
}

impl ModManagerHandle {
    #[instrument]
    pub async fn get(&self, mod_id: &str) -> Result<GetResponse> {
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
    pub async fn list(&self) -> Result<ListResponse> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::List { resp: tx })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }

    #[instrument]
    pub async fn remove(&self, mod_id: &str) -> Result<RemoveResponse> {
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
    pub async fn install(&self, package: &InstallPackage) -> Result<InstallResponse> {
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
    pub async fn update(&self, package: &InstallPackage) -> Result<UpdateResponse> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::Update {
                package: package.clone(),
                _resp: tx,
            })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        rx.await.map_err(|e| Error::ChannelError(e.into()))?
    }

    #[instrument]
    pub async fn shutdown(&self) -> Result<()> {
        self.commands_tx
            .send(Command::Shutdown())
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        Ok(())
    }

    #[instrument]
    pub async fn duplicate(&self) -> Result<ModManagerHandle> {
        let (tx, rx) = oneshot::channel();
        self.commands_tx
            .send(Command::Subscribe { resp: tx })
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        let updates_rx = rx.await.map_err(|e| Error::ChannelError(e.into()))?;
        let handle = ModManagerHandle {
            commands_tx: self.commands_tx.clone(),
            updates_rx,
        };
        Ok(handle)
    }

    pub async fn recieve_update(&mut self) -> Result<String> {
        self.updates_rx
            .recv()
            .await
            .map_err(|e| Error::ChannelError(e.into()))
    }
}

impl Serialize for Error {
    fn serialize<S>(&self, serializer: S) -> std::result::Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let e: ManagerError = self.into();
        e.serialize(serializer)
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
