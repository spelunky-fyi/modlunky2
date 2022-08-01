use std::ffi::OsString;
use std::io;
use std::path::{Path, PathBuf};

use anyhow::anyhow;
use derivative::Derivative;
use serde::Serialize;
use thiserror;
use tokio::fs;
use tokio::sync::{mpsc, oneshot};
use tokio::task;
use tracing::{debug, info, instrument};
use zip::ZipArchive;

use crate::constants::{MANIFEST_FILENAME, MODS_SUBPATH, MOD_METADATA_SUBPATH};
use crate::data::{ManagerError, Manifest, Mod};

#[derive(Derivative)]
#[derivative(Debug)]
pub enum Command {
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
        id: String,
        #[derivative(Debug = "ignore")]
        resp: oneshot::Sender<Result<UpdateResponse>>,
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
    #[error("Mod {0} already exists")]
    ModExistsError(String),
    #[error("Mod {0} wasn't found")]
    ModNotFoundError(String),
    #[error("Mod {0} isn't in a directory")]
    ModNonDirectoryError(String),

    #[error("Couldn't parse manifest for mod {0}")]
    ManifestParseError(String, #[source] anyhow::Error),
    #[error("Problem with installation source")]
    SourceError(#[source] anyhow::Error),
    #[error("Problem with the destination")]
    DestinationError(#[source] anyhow::Error),

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
#[derivative(Debug)]
pub struct ModManager {
    install_path: PathBuf,
    #[derivative(Debug = "ignore")]
    commands_rx: mpsc::Receiver<Command>,
}

#[derive(Clone, Derivative)]
#[derivative(Debug)]
pub struct ModManagerHandle {
    #[derivative(Debug = "ignore")]
    commands_tx: mpsc::Sender<Command>,
}

impl ModManager {
    pub fn new(install_path: &str) -> (Self, ModManagerHandle) {
        let (tx, rx) = mpsc::channel(1);
        let manager = ModManager {
            install_path: install_path.into(),
            commands_rx: rx,
        };
        let handle = ModManagerHandle { commands_tx: tx };
        (manager, handle)
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
                Command::Shutdown() => {
                    // Prevent additional messages from being sent
                    self.commands_rx.close();
                }
                _ => unimplemented!(),
            }
        }
    }

    #[instrument(skip(self))]
    async fn get_mod(&self, id: &str) -> Result<GetResponse> {
        let id = id.to_string();
        // First, check that the mod exists
        let mod_path = self.install_path.join(MODS_SUBPATH).join(&id);
        match path_metadata(&mod_path).await? {
            Some(m) => {
                if !m.is_dir() {
                    return Err(Error::ModNonDirectoryError(id));
                }
            }
            None => return Err(Error::ModNotFoundError(id)),
        }

        let manifest = self.load_mod_manifest(&id).await?;
        Ok(GetResponse {
            r#mod: Mod { id, manifest },
        })
    }

    #[instrument(skip(self))]
    async fn load_mod_manifest(&self, id: &str) -> Result<Option<Manifest>> {
        let path = self
            .install_path
            .join(MOD_METADATA_SUBPATH)
            .join(id)
            .join(MANIFEST_FILENAME);
        let json_result = fs::read(&path).await;
        if let Err(e) = json_result {
            match e.kind() {
                // It's OK if the metadata.json doesn't exist
                io::ErrorKind::NotFound => return Ok(None),
                _ => return Err(Error::UnknownError(e.into())),
            }
        }
        let json = json_result.unwrap();
        let manifest: Manifest = serde_json::from_slice(&json[..])
            .map_err(|e| Error::ManifestParseError(id.to_string(), e.into()))?;
        Ok(Some(manifest))
    }

    #[instrument(skip(self))]
    async fn list_mods(&self) -> Result<ListResponse> {
        let mut mods = Vec::new();
        let mod_path = self.install_path.join(MODS_SUBPATH);
        let mut dir = match fs::read_dir(mod_path).await {
            Ok(d) => d,
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => return Ok(ListResponse { mods }),
                _ => return Err(Error::UnknownError(e.into())),
            },
        };

        while let Some(entry) = dir
            .next_entry()
            .await
            .map_err(|e| Error::UnknownError(e.into()))?
        {
            if entry.file_name() == ".db" {
                continue;
            }
            let id = entry.file_name().into_string().map_err(|e| {
                Error::UnknownError(anyhow!("Couldn't convert to unicode: {:?}", e))
            })?;
            let res = self.get_mod(&id).await;
            match res {
                Ok(data) => mods.push(data.r#mod),
                Err(Error::ModNonDirectoryError(_)) => {}
                Err(e) => return Err(Error::UnknownError(e.into())),
            }
        }

        Ok(ListResponse { mods })
    }

    #[instrument(skip(self))]
    async fn remove_mod(&self, id: &str) -> Result<RemoveResponse> {
        let mod_path = self.install_path.join(MODS_SUBPATH).join(id);
        fs::remove_dir_all(mod_path)
            .await
            .map_err(|e| match e.kind() {
                io::ErrorKind::NotFound => Error::ModNotFoundError(id.to_string()),
                _ => Error::UnknownError(e.into()),
            })?;

        let metadata_path = self.install_path.join(MOD_METADATA_SUBPATH).join(id);
        let res = fs::remove_dir_all(metadata_path).await;
        // It's OK if the metadata directory doesn't exist
        match res {
            Ok(()) => Ok(RemoveResponse {}),
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => Ok(RemoveResponse {}),
                _ => Err(Error::UnknownError(e.into())),
            },
        }
    }

    #[instrument(skip(self))]
    async fn install_mod(&self, package: InstallPackage) -> Result<InstallResponse> {
        match package {
            InstallPackage::Local {
                source_path,
                dest_id,
            } => self.install_local_mod(&source_path, &dest_id).await,
            InstallPackage::Remote { code: _code } => unimplemented!(),
        }
    }

    #[instrument(skip(self))]
    async fn install_local_mod(&self, source: &str, dest_id: &str) -> Result<InstallResponse> {
        let dest_dir_path = self.install_path.join(MODS_SUBPATH).join(dest_id);

        if path_metadata(&dest_dir_path).await?.is_some() {
            return Err(Error::ModExistsError(dest_id.to_string()));
        }

        let source_path = PathBuf::from(source);
        path_metadata(&source_path).await?.map_or_else(
            || Err(Error::SourceError(anyhow!("not found"))),
            |m| {
                if m.is_file() {
                    Ok(())
                } else {
                    Err(Error::SourceError(anyhow!("not a file")))
                }
            },
        )?;

        fs::create_dir_all(&dest_dir_path)
            .await
            .map_err(|e| Error::DestinationError(e.into()))?;

        let copy_type = CopyType::for_path(&source_path);
        match copy_type {
            CopyType::SingleFile(name) => fs::copy(source_path, dest_dir_path.join(name))
                .await
                .map(|_| ()) // to make match-arm types equivalent
                .map_err(|e| Error::UnknownError(anyhow!("Error copying file: {:?}", e)))?,
            CopyType::ZipFile() => tokio::task::spawn_blocking(move || {
                extract_zip_archive(&source_path, dest_dir_path)
            })
            .await
            .map_err(|e| Error::UnknownError(anyhow!("Error extrating zip {:?}", e)))??,
        }
        Ok(InstallResponse {
            r#mod: Mod {
                id: dest_id.to_string(),
                manifest: None,
            },
        })
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
    pub async fn shutdown(&self) -> Result<()> {
        self.commands_tx
            .send(Command::Shutdown())
            .await
            .map_err(|e| Error::ChannelError(e.into()))?;
        Ok(())
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

async fn path_metadata(path: impl AsRef<Path>) -> Result<Option<std::fs::Metadata>> {
    let dest_check_result = fs::metadata(path).await;
    match dest_check_result {
        Ok(m) => Ok(Some(m)),
        Err(e) => match e.kind() {
            io::ErrorKind::NotFound => Ok(None),
            _ => Err(Error::UnknownError(e.into())),
        },
    }
}

enum CopyType {
    ZipFile(),
    SingleFile(OsString),
}

impl CopyType {
    fn for_path(path: &Path) -> CopyType {
        match path.extension() {
            None => CopyType::SingleFile(path.file_name().unwrap().into()),
            Some(ext) => {
                if ext == "lua" {
                    CopyType::SingleFile("main.lua".into())
                } else if ext == "zip" {
                    CopyType::ZipFile()
                } else {
                    CopyType::SingleFile(path.file_name().unwrap().into())
                }
            }
        }
    }
}

#[instrument]
fn extract_zip_archive(
    source_path: impl AsRef<Path> + std::fmt::Debug,
    dest: PathBuf,
) -> Result<()> {
    let source = std::fs::File::open(&source_path).map_err(|e| Error::SourceError(e.into()))?;
    let mut archive =
        ZipArchive::new(source).map_err(|e| Error::SourceError(anyhow!("Opening zip {:?}", e)))?;
    let paths = zip_enclosed_paths(&mut archive)?;
    let rename_lua = count_lua_paths(&paths) == 1;
    let remove_first = paths_have_same_prefix(&paths);
    let paths = fix_zip_names(paths, rename_lua, remove_first);
    for (i, dest_subpath) in paths.iter().enumerate().take(archive.len()) {
        let mut file = archive
            .by_index(i)
            .map_err(|e| Error::SourceError(anyhow!("Reading zip {:?}", e)))?;
        let dest_path = dest.join(&dest_subpath);
        debug!("extracting {:?} to {:?}", file.name(), dest_path);
        if file.is_dir() {
            std::fs::create_dir_all(dest_path).map_err(|e| Error::UnknownError(e.into()))?;
        } else {
            match dest_path.parent() {
                None => Ok(()),
                Some(p) => std::fs::create_dir_all(p),
            }
            .map_err(|e| Error::UnknownError(e.into()))?;
            let mut f =
                std::fs::File::create(dest_path).map_err(|e| Error::UnknownError(e.into()))?;
            std::io::copy(&mut file, &mut f).map_err(|e| Error::UnknownError(e.into()))?;
        }
    }
    Ok(())
}

#[instrument(skip(paths))]
fn fix_zip_names(paths: Vec<PathBuf>, rename_lua: bool, remove_first: bool) -> Vec<PathBuf> {
    if !rename_lua && !remove_first {
        return paths;
    }
    paths
        .into_iter()
        .map(|p| {
            let mut p = p;
            let rename_file = rename_lua
                && match p.extension() {
                    None => false,
                    Some(ext) => ext == "lua",
                };
            if rename_file {
                p.set_file_name("main.lua");
            }
            if remove_first {
                p = p.components().skip(1).collect();
            }
            p
        })
        .collect()
}

#[instrument(skip(zip))]
fn zip_enclosed_paths(zip: &mut ZipArchive<std::fs::File>) -> Result<Vec<PathBuf>> {
    let mut paths = Vec::with_capacity(zip.len());
    for i in 0..zip.len() {
        let f = zip
            .by_index_raw(i)
            .map_err(|e| Error::SourceError(anyhow!("Reading zip file {:?}", e)))?;
        let p = f
            .enclosed_name()
            .ok_or_else(|| Error::SourceError(anyhow!("Invalid file name")))?;
        paths.push(p.into());
    }
    Ok(paths)
}

#[instrument(skip(paths))]
fn paths_have_same_prefix(paths: &[PathBuf]) -> bool {
    // Don't rename single files to ""
    if paths.len() == 1 && paths[0].components().count() == 1 {
        return false;
    }

    let mut prefix = None;
    for p in paths {
        let c = p.components().next();
        if let Some(pre) = c {
            // We want to ignore paths that contain mod stuff.
            // If there's one, then either everything is ignored or the prefix varies.
            if let Some(s) = pre.as_os_str().to_str() {
                let low = s.to_ascii_lowercase();
                if low == "data" || low == "soundbank" {
                    return false;
                }
            }

            prefix = c
        }
    }
    paths.iter().all(|p| p.components().next() == prefix)
}

#[instrument(skip(paths))]
fn count_lua_paths(paths: &[PathBuf]) -> usize {
    paths
        .iter()
        .filter(|p| p.extension().map_or(false, |e| e == "lua"))
        .count()
}
