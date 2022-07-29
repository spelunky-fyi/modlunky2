use std::io;
use std::path::PathBuf;

use derivative::Derivative;
use thiserror;
use tokio::fs;
use tokio::sync::{mpsc, oneshot};
use tokio::task;
use tracing::{debug, info, instrument};

use crate::constants::{MANIFEST_FILENAME, PACKS_SUBPATH, PACK_METADATA_SUBPATH};
use crate::data::{Manifest, Mod};

#[derive(Derivative)]
#[derivative(Debug)]
pub enum Command {
    Install {
        package: InstallPackage,
        resp: oneshot::Sender<Result<InstallResponse, InstallError>>,
    },
    Update {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<UpdateResponse, UpdateError>>,
    },
    Remove {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<RemoveResponse, RemoveError>>,
    },
    Get {
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<GetResponse, GetError>>,
    },
    List {
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<ListResponse, ListError>>,
    },
    Shutdown(),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum InstallPackage {
    Local { path: String },
    Remote { code: String },
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InstallResponse {}

#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
pub enum InstallError {}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UpdateResponse {}

#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
pub enum UpdateError {}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RemoveResponse {}

#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
pub enum RemoveError {}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GetResponse {
    pub r#mod: Mod,
}

#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
pub enum GetError {
    #[error("Mod isn't installed")]
    NotFoundError(),
    #[error("Mod isn't in a directory")]
    NonDirectoryError(),
    #[error("Couldn't read manifest for mod")]
    ManifestParseError(String),
    #[error("Unknown error: {0}")]
    UnknownError(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ListResponse {
    pub mods: Vec<Mod>,
}

#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
pub enum ListError {
    #[error("Mods directory doesn't exist")]
    NotFoundError(),
    #[error("Unknown error: {0}")]
    UnknownError(String),
}

#[derive(Derivative)]
#[derivative(Debug)]
pub struct ModManager {
    install_path: PathBuf,
    #[derivative(Debug = "ignore")]
    commands_rx: mpsc::Receiver<Command>,
}

impl ModManager {
    pub fn new(install_path: &str) -> (Self, mpsc::Sender<Command>) {
        let (tx, rx) = mpsc::channel(1);
        let manager = ModManager {
            install_path: install_path.into(),
            commands_rx: rx,
        };
        (manager, tx)
    }

    // Consumes the ModManager, starting a task and returning its JoinHandle
    pub fn spawn(mut self) -> task::JoinHandle<()> {
        tokio::spawn(async move { self.run().await })
    }

    #[instrument(skip(self))]
    async fn run(&mut self) -> () {
        while let Some(cmd) = self.commands_rx.recv().await {
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
                Command::Shutdown() => {
                    // Prevent additional messages from being sent
                    self.commands_rx.close();
                }
                _ => unimplemented!(),
            }
        }
    }

    #[instrument(skip(self))]
    async fn get_mod(&self, id: &str) -> Result<GetResponse, GetError> {
        // First, check that the mod exists
        let mod_path = self.install_path.join(PACKS_SUBPATH).join(id);
        let metadata = fs::metadata(mod_path).await.map_err(|e| match e.kind() {
            io::ErrorKind::NotFound => GetError::NotFoundError(),
            _ => GetError::UnknownError(format!("{:?}", e)),
        })?;
        if !metadata.is_dir() {
            return Err(GetError::NonDirectoryError());
        }

        let manifest = self
            .load_mod_manifest(id)
            .await
            .map_err(GetError::ManifestParseError)?;
        let id = id.to_string();
        Ok(GetResponse {
            r#mod: Mod { id, manifest },
        })
    }

    #[instrument(skip(self))]
    async fn load_mod_manifest(&self, id: &str) -> Result<Option<Manifest>, String> {
        let path = self
            .install_path
            .join(PACK_METADATA_SUBPATH)
            .join(id)
            .join(MANIFEST_FILENAME);
        let json_result = fs::read(&path).await;
        if let Err(e) = json_result {
            match e.kind() {
                io::ErrorKind::NotFound => return Ok(None),
                _ => return Err(format!("{:?}", e)),
            }
        }
        let json = json_result.unwrap();
        let manifest: Manifest =
            serde_json::from_slice(&json[..]).map_err(|e| format!("{:?}", e))?;
        Ok(Some(manifest))
    }

    #[instrument(skip(self))]
    async fn list_mods(&self) -> Result<ListResponse, ListError> {
        let packs_path = self.install_path.join(PACKS_SUBPATH);
        let mut dir = fs::read_dir(packs_path).await.map_err(|e| match e.kind() {
            io::ErrorKind::NotFound => ListError::NotFoundError(),
            _ => ListError::UnknownError(format!("{:?}", e)),
        })?;

        let mut mods = Vec::new();
        while let Some(entry) = dir
            .next_entry()
            .await
            .map_err(|e| ListError::UnknownError(format!("{:?}", e)))?
        {
            if entry.file_name() == ".db" {
                continue;
            }
            let id = entry
                .file_name()
                .into_string()
                .map_err(|e| ListError::UnknownError(format!("{:?}", e)))?;
            let res = self.get_mod(&id).await;
            match res {
                Ok(data) => mods.push(data.r#mod),
                Err(GetError::NonDirectoryError()) => {}
                Err(e) => return Err(ListError::UnknownError(format!("{:?}", e))),
            }
        }

        Ok(ListResponse { mods })
    }
}
