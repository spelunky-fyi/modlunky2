use std::ffi::OsString;
use std::io;
use std::path::{Path, PathBuf};

use anyhow::anyhow;
use async_trait::async_trait;
use thiserror;
use tokio::fs;
use tracing::{debug, instrument};
use zip::ZipArchive;

use crate::constants::{MANIFEST_FILENAME, MODS_SUBPATH, MOD_METADATA_SUBPATH};
use crate::data::{Manifest, Mod};

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Mod {0} already exists")]
    AlreadyExists(String),
    #[error("Mod {0} wasn't found")]
    NotFound(String),
    #[error("Mod {0} isn't in a directory")]
    NonDirectory(String),

    #[error("Couldn't parse manifest for mod {0}")]
    ManifestParseError(String, #[source] anyhow::Error),
    #[error("Problem with installation source")]
    SourceError(#[source] anyhow::Error),
    #[error("Problem with the destination")]
    DestinationError(#[source] anyhow::Error),

    #[error("Unknown error: {0}")]
    UnknownError(#[source] anyhow::Error),
}

pub type Result<R> = std::result::Result<R, Error>;

#[async_trait]
pub trait LocalMods {
    async fn get(&self, id: &str) -> Result<Mod>;
    async fn list(&self) -> Result<Vec<Mod>>;
    async fn remove(&self, id: &str) -> Result<()>;
    // TODO: ideally this would take a filename and tokio::fs::File.
    // Note that taking AsyncRead is hard because we need a std::io::Read for zip crate.
    async fn install(&self, source: &str, dest_id: &str) -> Result<Mod>;
}

pub struct DiskMods {
    install_path: PathBuf,
}

impl DiskMods {
    pub fn new(install_path: &str) -> Self {
        Self {
            install_path: install_path.into(),
        }
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
}

#[async_trait]
impl LocalMods for DiskMods {
    #[instrument(skip(self))]
    async fn get(&self, id: &str) -> Result<Mod> {
        let id = id.to_string();
        // First, check that the mod exists
        let mod_path = self.install_path.join(MODS_SUBPATH).join(&id);
        match path_metadata(&mod_path).await? {
            Some(m) => {
                if !m.is_dir() {
                    return Err(Error::NonDirectory(id));
                }
            }
            None => return Err(Error::NotFound(id)),
        }

        let manifest = self.load_mod_manifest(&id).await?;
        Ok(Mod { id, manifest })
    }

    #[instrument(skip(self))]
    async fn list(&self) -> Result<Vec<Mod>> {
        let mut mods = Vec::new();
        let mod_path = self.install_path.join(MODS_SUBPATH);
        let mut dir = match fs::read_dir(mod_path).await {
            Ok(d) => d,
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => return Ok(mods),
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
            let res = self.get(&id).await;
            match res {
                Ok(r#mod) => mods.push(r#mod),
                Err(Error::NonDirectory(_)) => {}
                Err(e) => return Err(Error::UnknownError(e.into())),
            }
        }

        Ok(mods)
    }

    #[instrument(skip(self))]
    async fn remove(&self, id: &str) -> Result<()> {
        let mod_path = self.install_path.join(MODS_SUBPATH).join(id);
        fs::remove_dir_all(mod_path)
            .await
            .map_err(|e| match e.kind() {
                io::ErrorKind::NotFound => Error::NotFound(id.to_string()),
                _ => Error::UnknownError(e.into()),
            })?;

        let metadata_path = self.install_path.join(MOD_METADATA_SUBPATH).join(id);
        let res = fs::remove_dir_all(metadata_path).await;
        // It's OK if the metadata directory doesn't exist
        match res {
            Ok(()) => Ok(()),
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => Ok(()),
                _ => Err(Error::UnknownError(e.into())),
            },
        }
    }

    #[instrument(skip(self))]
    async fn install(&self, source: &str, dest_id: &str) -> Result<Mod> {
        let dest_dir_path = self.install_path.join(MODS_SUBPATH).join(dest_id);

        if path_metadata(&dest_dir_path).await?.is_some() {
            return Err(Error::AlreadyExists(dest_id.to_string()));
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
        Ok(Mod {
            id: dest_id.to_string(),
            manifest: None,
        })
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
