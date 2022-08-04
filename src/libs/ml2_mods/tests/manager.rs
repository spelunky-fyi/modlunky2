use std::io;
use std::path::PathBuf;

use anyhow::anyhow;
use async_trait::async_trait;
use ml2_mods::constants::MANIFEST_FILENAME;
use ml2_mods::local::{DiskMods, Error as LocalError};
use ml2_mods::manager::{InstallResponse, ModManagerHandle, RemoveResponse};
use ml2_mods::spelunkyfyi::http::{Api, ApiClient, Error as ApiError, Mod as ApiMod};
use tempfile::{tempdir, TempDir};
use tokio::fs::{self, OpenOptions};

use ml2_mods::{
    constants::{MODS_SUBPATH, MOD_METADATA_SUBPATH},
    data::{Manifest, ManifestModFile, Mod},
    manager::{Error, GetResponse, InstallPackage, ListResponse, ModManager},
};
use tokio::io::AsyncWrite;

fn make_provincial_mod() -> Mod {
    Mod {
        id: "provincial".to_string(),
        manifest: None,
    }
}
fn make_remote_control_mod() -> Mod {
    Mod {
        id: "fyi.remote-control".to_string(),
        manifest: Some(Manifest {
            name: "Remote Control".to_string(),
            slug: "remote-control".to_string(),
            description: "A fake mod for tests".to_string(),
            logo: "mod_logo.png".to_string(),
            mod_file: ManifestModFile {
                id: "QBRJYOGMYDCZ2VC269B6MKMHTQ".to_string(),
                created_at: "2017-08-09T01:23:45.678901Z".to_string(),
                download_url:
                    "https://example.com/mods/m/remote-control/download/QBRJYOGMYDCZ2VC269B6MKMHTQ/"
                        .to_string(),
            },
        }),
    }
}

fn testdata_install_dir() -> String {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(r"tests\data\install_dir")
        .to_str()
        .unwrap()
        .into()
}

struct MockApi {}

#[async_trait]
impl Api for MockApi {
    async fn get_manifest(&mut self, _id: &str) -> Result<ApiMod, ApiError> {
        unimplemented!()
    }
    async fn download(
        &mut self,
        _uri: &str,
        _writer: &mut (impl AsyncWrite + std::fmt::Debug + Send + Unpin),
    ) -> Result<(), ApiError> {
        unimplemented!()
    }
}

#[tokio::test]
async fn test_get() {
    let local_mods = DiskMods::new(&testdata_install_dir());
    let (manager, handle): (ModManager<ApiClient, DiskMods>, ModManagerHandle) =
        ModManager::new(None, local_mods);
    let manager_join = manager.spawn();

    let resp = handle.get("provincial").await.unwrap();
    assert_eq!(
        resp,
        GetResponse {
            r#mod: make_provincial_mod()
        }
    );

    let resp = handle.get("fyi.remote-control").await.unwrap();
    assert_eq!(
        resp,
        GetResponse {
            r#mod: make_remote_control_mod()
        }
    );

    let err = handle.get("does-not-exist").await.unwrap_err();
    if let Error::ModNotFoundError(LocalError::NotFound(id)) = err {
        assert_eq!(id, "does-not-exist")
    } else {
        panic!("Unexpected error from manager: {:?}", err)
    }

    drop(handle);
    manager_join.await.unwrap();
}

#[tokio::test]
async fn test_list_exists() {
    let local_mods = DiskMods::new(&testdata_install_dir());
    let (manager, handle): (ModManager<ApiClient, DiskMods>, ModManagerHandle) =
        ModManager::new(None, local_mods);
    let manager_join = manager.spawn();

    let resp = handle.list().await.unwrap();
    assert_eq!(
        resp,
        ListResponse {
            mods: vec![make_remote_control_mod(), make_provincial_mod()]
        }
    );

    drop(handle);
    manager_join.await.unwrap();
}

#[tokio::test]
async fn test_list_nonexistent() {
    let dir = tempdir().unwrap();
    let path: String = dir.path().join("bogus_dir").to_str().unwrap().into();

    let local_mods = DiskMods::new(&path);
    let (manager, handle): (ModManager<ApiClient, DiskMods>, ModManagerHandle) =
        ModManager::new(None, local_mods);
    let manager_join = manager.spawn();

    let resp = handle.list().await.unwrap();
    assert_eq!(resp, ListResponse { mods: vec![] });

    drop(handle);
    manager_join.await.unwrap();
}

async fn touch_file(path: PathBuf) {
    let file = OpenOptions::new()
        .create(true)
        .write(true)
        .open(path.clone())
        .await
        .unwrap();
    file.sync_all().await.unwrap();
}

#[tokio::test]
async fn test_remove() {
    let mod_id = "some-mod";
    let dir = tempfile::tempdir().unwrap();

    let mod_path = dir.path().join(MODS_SUBPATH).join(mod_id);
    fs::create_dir_all(mod_path.clone()).await.unwrap();

    let lua_path = mod_path.join("main.lua");
    touch_file(lua_path.clone()).await;

    let metadata_dir_path = dir.path().join(MOD_METADATA_SUBPATH).join(mod_id);
    fs::create_dir_all(metadata_dir_path.clone()).await.unwrap();

    let manifest_path = mod_path.join(MANIFEST_FILENAME);
    touch_file(manifest_path.clone()).await;

    let dir_path = dir.path().to_str();
    if dir_path.is_none() {
        panic!("tempdir isn't valid unicode: {:?}", dir.path());
    }

    let local_mods = DiskMods::new(dir_path.unwrap());
    let (manager, handle): (ModManager<ApiClient, DiskMods>, ModManagerHandle) =
        ModManager::new(None, local_mods);
    let manager_join = manager.spawn();

    let resp = handle.remove(mod_id).await.unwrap();
    assert_eq!(resp, RemoveResponse {});

    let err = handle.remove("does-not-exist").await.unwrap_err();
    if let Error::ModNotFoundError(LocalError::NotFound(id)) = err {
        assert_eq!(id, "does-not-exist")
    } else {
        panic!("Unexpected error from manager: {:?}", err)
    }

    drop(handle);
    manager_join.await.unwrap();

    for p in [mod_path, lua_path, metadata_dir_path, manifest_path] {
        match fs::metadata(&p).await {
            Ok(_) => panic!("File/dir still exists: {:?}", p),
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => (),
                _ => panic!("Unexpected IO error: {:?}", e),
            },
        }
    }
}

async fn install_from_local_sources(handle: &ModManagerHandle, source_file: &str, dest_id: &str) {
    let source_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(r"tests\data\local_sources")
        .join(source_file)
        .as_os_str()
        .to_str()
        .unwrap()
        .to_string();
    let resp = handle
        .install(&InstallPackage::Local {
            source_path,
            dest_id: dest_id.to_string(),
        })
        .await
        .unwrap();
    assert_eq!(
        resp,
        InstallResponse {
            r#mod: Mod {
                id: dest_id.to_string(),
                manifest: None,
            },
        }
    )
}

async fn assert_exits_in(dir: &TempDir, mod_id: &str, path: &str) {
    let path = dir.path().join(MODS_SUBPATH).join(mod_id).join(path);
    fs::metadata(&path)
        .await
        .map_err(|e| anyhow!("checking for {:?}: {:?}", path, e))
        .unwrap();
}

#[tokio::test]
async fn test_install_locall() {
    let dir = tempfile::tempdir().unwrap();

    let local_mods = DiskMods::new(dir.path().as_os_str().to_str().unwrap());
    let (manager, handle): (ModManager<ApiClient, DiskMods>, ModManagerHandle) =
        ModManager::new(None, local_mods);
    let manager_join = manager.spawn();

    let mod_id = "unchanged";
    install_from_local_sources(&handle, "unchanged.txt", mod_id).await;
    assert_exits_in(&dir, mod_id, "unchanged.txt").await;

    let mod_id = "rename-lua";
    install_from_local_sources(&handle, "rename_me.lua", mod_id).await;
    assert_exits_in(&dir, mod_id, "main.lua").await;

    let mod_id = "multi-lua";
    install_from_local_sources(&handle, "multi_lua.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "ok.lua").await;
    assert_exits_in(&dir, mod_id, "fine.lua").await;

    let mod_id = "varying-prefixes";
    install_from_local_sources(&handle, "varying_prefixes.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "a/foo.txt").await;
    assert_exits_in(&dir, mod_id, "b/bar.txt").await;

    let mod_id = "single-file";
    install_from_local_sources(&handle, "single_file.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "lonely.txt").await;

    let mod_id = "only-mod-data";
    install_from_local_sources(&handle, "only_mod_data.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "Data/inner.txt").await;

    let mod_id = "empty-dirs";
    install_from_local_sources(&handle, "empty_dirs.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "x").await;
    assert_exits_in(&dir, mod_id, "y").await;

    let mod_id = "single-dir";
    install_from_local_sources(&handle, "single_dir.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "foo.txt").await;

    let mod_id = "single-lua";
    install_from_local_sources(&handle, "single_lua.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "main.lua").await;
    assert_exits_in(&dir, mod_id, "unchanged.txt").await;

    let mod_id = "unicode";
    install_from_local_sources(&handle, "unicode.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "unicode👀.txt").await;

    drop(handle);
    manager_join.await.unwrap()
}
