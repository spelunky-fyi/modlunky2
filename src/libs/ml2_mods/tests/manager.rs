use std::io;
use std::path::PathBuf;
use std::time::Duration;

use anyhow::anyhow;
use ml2_mods::{
    data::{Manifest, ManifestModFile, Mod},
    local::{
        constants::{MANIFEST_FILENAME, MODS_SUBPATH, MOD_METADATA_SUBPATH},
        disk::DiskMods,
        Error as LocalError,
    },
    manager::{Error, ModManager, ModManagerHandle, ModSource},
    spelunkyfyi::http::HttpApiMods,
};
use tempfile::{tempdir, TempDir};
use tokio::fs::{self, OpenOptions};
use tokio_graceful_shutdown::{IntoSubsystem, Toplevel};

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
            logo: Some("mod_logo.png".to_string()),
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

fn setup(install_path: &str) -> ModManagerHandle {
    let local_mods = DiskMods::new(install_path);
    let (manager, handle): (ModManager<HttpApiMods, DiskMods>, ModManagerHandle) =
        ModManager::new(None, local_mods);
    let toplevel = Toplevel::new().start("ModManager", manager.into_subsystem());
    tokio::spawn(toplevel.handle_shutdown_requests(Duration::from_millis(1000)));
    handle
}

#[tokio::test]
async fn test_get() {
    let handle = setup(&testdata_install_dir());

    let resp = handle.get("provincial").await.unwrap();
    assert_eq!(resp, make_provincial_mod());

    let resp = handle.get("fyi.remote-control").await.unwrap();
    assert_eq!(resp, make_remote_control_mod());

    let err = handle.get("does-not-exist").await.unwrap_err();
    if let Error::ModNotFoundError(LocalError::NotFound(id)) = err {
        assert_eq!(id, "does-not-exist")
    } else {
        panic!("Unexpected error from manager: {:?}", err)
    }
}

#[tokio::test]
async fn test_list_exists() {
    let handle = setup(&testdata_install_dir());

    let resp = handle.list().await.unwrap();
    assert_eq!(resp, vec![make_remote_control_mod(), make_provincial_mod()]);
}

#[tokio::test]
async fn test_list_nonexistent() {
    let dir = tempdir().unwrap();
    let path: String = dir.path().join("bogus_dir").to_str().unwrap().into();

    let handle = setup(&path);

    let resp = handle.list().await.unwrap();
    assert_eq!(resp, vec![]);
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

    let handle = setup(dir.path().to_str().unwrap());

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

    handle.remove(mod_id).await.unwrap();

    let err = handle.remove("does-not-exist").await.unwrap_err();
    if let Error::ModNotFoundError(LocalError::NotFound(id)) = err {
        assert_eq!(id, "does-not-exist")
    } else {
        panic!("Unexpected error from manager: {:?}", err)
    }

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
        .install(&ModSource::Local {
            source_path,
            dest_id: dest_id.to_string(),
        })
        .await
        .unwrap();
    assert_eq!(
        resp,
        Mod {
            id: dest_id.to_string(),
            manifest: None,
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

    let handle = setup(dir.path().to_str().unwrap());

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
}
