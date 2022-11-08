use std::ffi::OsString;
use std::io;
use std::path::{Path, PathBuf};

use anyhow::anyhow;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use tempfile::{tempdir, TempDir};
use tokio::fs;
use tracing::{debug, instrument};
use zip::result::ZipError;
use zip::ZipArchive;

use super::ModLogo;
use super::{
    constants::{LATEST_FILENAME, MANIFEST_FILENAME, MODS_SUBPATH, MOD_METADATA_SUBPATH},
    Error, LocalMods, Result,
};
use crate::data::{Manifest, ManifestModFile, Mod};
use crate::spelunkyfyi::http::{DownloadedLogo, DownloadedMod, Mod as ApiMod};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
struct LatestFile {
    id: String,
}

#[derive(Clone, Debug)]
pub struct DiskMods {
    install_path: PathBuf,
}

impl DiskMods {
    pub fn new(install_path: &str) -> Self {
        Self {
            install_path: install_path.into(),
        }
    }

    fn mods_dir_path(&self, id: &str) -> PathBuf {
        self.install_path.join(MODS_SUBPATH).join(id)
    }

    fn manifest_dir_path(&self, id: &str) -> PathBuf {
        self.install_path.join(MOD_METADATA_SUBPATH).join(id)
    }

    #[instrument(skip(self))]
    async fn create_manifest_dir(&self, id: &str) -> Result<PathBuf> {
        let manifest_dir = self.manifest_dir_path(id);
        debug!("Creating manifest dir {:?}", manifest_dir);
        fs::create_dir_all(&manifest_dir).await?;
        Ok(manifest_dir)
    }

    #[instrument(skip(self))]
    async fn load_latest(&self, id: &str) -> Result<Option<String>> {
        let path = self.manifest_dir_path(id).join(LATEST_FILENAME);
        let json = if let Some(content) = try_read(path).await? {
            content
        } else {
            return Ok(None);
        };
        let latest: LatestFile = serde_json::from_slice(&json[..])?;
        Ok(Some(latest.id))
    }

    #[instrument(skip(self))]
    async fn load_mod_manifest(&self, id: &str) -> Result<Option<Manifest>> {
        let path = self.manifest_dir_path(id).join(MANIFEST_FILENAME);
        let json = if let Some(content) = try_read(path).await? {
            content
        } else {
            return Ok(None);
        };
        Ok(serde_json::from_slice(&json[..])?)
    }

    #[instrument(skip(self))]
    async fn write_mod_manifest(&self, id: &str, manifest: &Manifest) -> Result<()> {
        debug!("Writing manifest");
        self.create_manifest_dir(id).await?;
        let manifest_path = self.manifest_dir_path(id).join(MANIFEST_FILENAME);
        let json = serde_json::to_string(manifest).map_err(|e| Error::UnknownError(e.into()))?;
        debug!("Writing manifest JSON to {:?}", manifest_path);
        fs::write(manifest_path, json).await?;
        Ok(())
    }

    async fn make_dest_dir(&self, dest_id: &str) -> Result<PathBuf> {
        let dest_dir_path = self.mods_dir_path(dest_id);

        if path_metadata(&dest_dir_path).await?.is_some() {
            return Err(Error::AlreadyExists(dest_id.to_string()));
        }
        fs::create_dir_all(&dest_dir_path)
            .await
            .map_err(|e| Error::DestinationError(e.into()))?;
        Ok(dest_dir_path)
    }

    #[instrument(skip(self))]
    async fn install_main(&self, source: &PathBuf, dest_dir: &PathBuf) -> Result<()> {
        debug!("Installing main file");
        let source = source.clone();
        let dest_dir = dest_dir.clone();
        let copy_type = CopyType::for_path(&source);
        match copy_type {
            CopyType::SingleFile(name) => fs::copy(source, dest_dir.join(name))
                .await
                .map(|_| ()) // to make match-arm types equivalent
                .map_err(|e| Error::UnknownError(anyhow!("Error copying file: {:?}", e)))?,
            CopyType::ZipFile() => {
                tokio::task::spawn_blocking(move || extract_zip_archive(&source, &dest_dir))
                    .await
                    .map_err(|e| Error::UnknownError(anyhow!("Error extrating zip {:?}", e)))??
            }
        }
        Ok(())
    }

    #[instrument(skip(self))]
    async fn install_logo(&self, source: &DownloadedLogo, dest_id: &str) -> Result<OsString> {
        debug!("Installing logo file");
        let extension = match source.content_type.as_str() {
            "image/jpeg" => Ok("jpg"),
            "image/png" => Ok("png"),
            "image/gif" => Ok("gif"),
            _ => Err(Error::UnknownError(anyhow!(
                "unrecognized content-type for logo: {}",
                source.content_type
            ))),
        }?;

        self.create_manifest_dir(dest_id).await?;

        let mut dest_name = OsString::from("mod_logo.");
        dest_name.push(extension);
        let dest_path = self.manifest_dir_path(dest_id).join(&dest_name);
        debug!("Installing logo to path {:?}", dest_path);
        fs::copy(&source.file, dest_path).await?;

        Ok(dest_name)
    }

    async fn prep_for_update(&self, dest_id: &str) -> Result<TempDir> {
        let temp_dir = tempdir()?;
        let temp_mod_path = temp_dir.path().join(dest_id);
        let old_mod_path = self.mods_dir_path(dest_id);
        if path_metadata(&old_mod_path).await?.is_none() {
            return Err(Error::NotFound(dest_id.to_string()));
        }
        fs::rename(&old_mod_path, &temp_mod_path).await?;
        debug!("Stashed old mod version in {:?}", temp_mod_path);
        Ok(temp_dir)
    }

    async fn finish_update(
        &self,
        dest_id: &str,
        temp_dir: TempDir,
        install_result: Result<Mod>,
    ) -> Result<Mod> {
        let temp_mod_path = temp_dir.path().join(dest_id);
        let r#mod = match install_result {
            Err(e) => {
                fs::rename(&temp_mod_path, self.mods_dir_path(dest_id)).await?;
                return Err(e);
            }
            Ok(m) => m,
        };

        let temp_save_path = temp_mod_path.join("save.dat");
        if path_metadata(&temp_save_path).await?.is_some() {
            debug!("Restoring save.dat");
            fs::copy(
                &temp_save_path,
                self.mods_dir_path(dest_id).join("save.dat"),
            )
            .await?;
        }
        Ok(r#mod)
    }
}

#[async_trait]
impl LocalMods for DiskMods {
    #[instrument(skip(self))]
    async fn get(&self, id: &str) -> Result<Mod> {
        let id = id.to_string();
        // First, check that the mod exists
        let mod_path = self.mods_dir_path(&id);
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
        let mod_path = self.mods_dir_path(id);
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
    async fn install_local(&self, source: &str, dest_id: &str) -> Result<Mod> {
        debug!("Installing local mod {:?}", dest_id);
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
        let dest_dir = self.make_dest_dir(dest_id).await?;
        self.install_main(&source.into(), &dest_dir).await?;

        Ok(Mod {
            id: dest_id.to_string(),
            manifest: None,
        })
    }

    #[instrument(skip_all)]
    async fn install_remote(&self, downloaded: &DownloadedMod) -> Result<Mod> {
        let dest_id = id_for_remote(&downloaded.r#mod);
        debug!("Installing remote mod {:?}", dest_id);
        let dest_path = self.make_dest_dir(&dest_id).await?;

        self.install_main(&downloaded.main_file, &dest_path).await?;
        let logo = if let Some(logo_file) = downloaded.logo_file.as_ref() {
            let logo = self.install_logo(logo_file, &dest_id).await?;
            let logo = logo
                .to_str()
                .ok_or_else(|| {
                    Error::UnknownError(anyhow!("Failed to convert logo filename {:?}", logo))
                })?
                .to_string();
            Some(logo)
        } else {
            None
        };

        let mod_file = ManifestModFile {
            id: downloaded.mod_file.id.clone(),
            created_at: downloaded.mod_file.created_at.to_string(),
            download_url: downloaded.mod_file.download_url.clone(),
        };

        let manifest = Manifest {
            name: downloaded.r#mod.name.clone(),
            slug: downloaded.r#mod.slug.clone(),
            description: downloaded.r#mod.description.clone(),
            logo,
            mod_file,
        };
        self.write_mod_manifest(&dest_id, &manifest).await?;
        self.update_latest_json(&downloaded.r#mod).await?;

        Ok(Mod {
            id: dest_id,
            manifest: Some(manifest),
        })
    }

    #[instrument(skip(self))]
    async fn update_local(&self, source: &str, dest_id: &str) -> Result<Mod> {
        let temp_dir = self.prep_for_update(dest_id).await?;
        let install_result = self.install_local(source, dest_id).await;
        self.finish_update(dest_id, temp_dir, install_result).await
    }

    #[instrument(skip_all)]
    async fn update_remote(&self, downloaded: &DownloadedMod) -> Result<Mod> {
        let dest_id = id_for_remote(&downloaded.r#mod);
        let temp_dir = self.prep_for_update(&dest_id).await?;
        let install_result = self.install_remote(downloaded).await;
        self.finish_update(&dest_id, temp_dir, install_result).await
    }

    #[instrument(skip(self, api_mod))]
    async fn update_latest_json(&self, api_mod: &ApiMod) -> Result<Option<String>> {
        let id = id_for_remote(api_mod);
        let latest = if let Some(mod_file) = api_mod.mod_files.first() {
            mod_file.id.clone()
        } else {
            return Ok(None);
        };

        let prev_latest = self.load_latest(&id).await?;
        let same = if let Some(prev) = prev_latest {
            prev == latest
        } else {
            false
        };

        if same {
            Ok(None)
        } else {
            debug!("Writing latest.json for {}", id);
            let json = serde_json::to_string(&LatestFile { id: latest.clone() })?;
            let path = self.create_manifest_dir(&id).await?.join(LATEST_FILENAME);
            fs::write(&path, json).await?;
            Ok(Some(id))
        }
    }

    #[instrument(skip(self))]
    async fn get_mod_logo(&self, id: &str) -> Result<ModLogo> {
        let logo_name = self
            .load_mod_manifest(id)
            .await?
            .ok_or_else(|| anyhow!("Mod {:?} has no manifest. Therefore it has no logo", id))?
            .logo
            .ok_or_else(|| anyhow!("Mod {:?} has no logo", id))?;
        let logo_path = self.manifest_dir_path(id).join(&logo_name);

        let ext = logo_path
            .extension()
            .ok_or_else(|| anyhow!("No extenison in {:?} for mod {:?}", logo_name, id))?
            .to_str()
            .ok_or_else(|| anyhow!("Non-unicode extension in {:?} for mod {:?}", logo_name, id))?;
        let mime_type = match ext {
            "jpg" => "imag/jpeg",
            "gif" => "imag/gif",
            "png" => "image/png",
            _ => {
                return Err(
                    anyhow!("Unexpected extension in {:?} for mod {:?}", logo_name, id).into(),
                )
            }
        }
        .to_string();

        let bytes = fs::read(&logo_path).await?;
        Ok(ModLogo { mime_type, bytes })
    }
}

fn id_for_remote(remote: &ApiMod) -> String {
    format!("fyi.{}", remote.slug)
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

async fn try_read(path: impl AsRef<Path>) -> Result<Option<Vec<u8>>> {
    let content = fs::read(path.as_ref()).await;
    if let Err(e) = content {
        match e.kind() {
            io::ErrorKind::NotFound => return Ok(None),
            _ => return Err(e.into()),
        }
    };
    Ok(Some(content.unwrap()))
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
    dest: &PathBuf,
) -> Result<()> {
    let source = std::fs::File::open(&source_path).map_err(|e| Error::SourceError(e.into()))?;
    let mut archive = ZipArchive::new(source)?;
    let paths = zip_enclosed_paths(&mut archive)?;
    let rename_lua = count_lua_paths(&paths) == 1;
    let remove_first = paths_have_same_prefix(&paths);
    let paths = fix_zip_names(paths, rename_lua, remove_first);
    for (i, dest_subpath) in paths.iter().enumerate().take(archive.len()) {
        let mut file = archive.by_index(i)?;
        let dest_path = dest.join(dest_subpath);
        debug!("extracting {:?} to {:?}", file.name(), dest_path);
        if file.is_dir() {
            std::fs::create_dir_all(dest_path)?;
        } else {
            if let Some(parent_path) = dest_path.parent() {
                std::fs::create_dir_all(parent_path)?;
            }
            let mut f = std::fs::File::create(dest_path)?;
            std::io::copy(&mut file, &mut f)?;
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

impl From<serde_json::Error> for Error {
    fn from(err: serde_json::Error) -> Self {
        Self::UnknownError(err.into())
    }
}

impl From<ZipError> for Error {
    fn from(err: ZipError) -> Self {
        Self::SourceError(err.into())
    }
}
