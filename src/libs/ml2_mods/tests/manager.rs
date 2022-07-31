use std::io;
use std::path::PathBuf;

use anyhow::anyhow;
use ml2_mods::constants::MANIFEST_FILENAME;
use ml2_mods::manager::{InstallResponse, RemoveResponse};
use tempfile::TempDir;
use tokio::fs::{self, OpenOptions};
use tokio::sync::{mpsc, oneshot};

use ml2_mods::{
    constants::{MODS_SUBPATH, MOD_METADATA_SUBPATH},
    data::{Manifest, ManifestModFile, Mod},
    manager::{Command, GetResponse, InstallPackage, ListResponse, ModManager},
};

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

#[tokio::test]
async fn test_get() {
    let (manager, commands_tx) = ModManager::new(&testdata_install_dir());
    let manager_handle = manager.spawn();

    let (tx, rx) = oneshot::channel();
    commands_tx
        .send(Command::Get {
            id: "provincial".to_string(),
            resp: tx,
        })
        .await
        .unwrap();
    assert_eq!(
        rx.await.unwrap().unwrap(),
        GetResponse {
            r#mod: make_provincial_mod()
        }
    );

    let (tx, rx) = oneshot::channel();
    commands_tx
        .send(Command::Get {
            id: "fyi.remote-control".to_string(),
            resp: tx,
        })
        .await
        .unwrap();
    assert_eq!(
        rx.await.unwrap().unwrap(),
        GetResponse {
            r#mod: make_remote_control_mod()
        }
    );

    drop(commands_tx);
    manager_handle.await.unwrap();
}

#[tokio::test]
async fn test_list() {
    let (manager, commands_tx) = ModManager::new(&testdata_install_dir());
    let manager_handle = manager.spawn();

    let (tx, rx) = oneshot::channel();
    commands_tx.send(Command::List { resp: tx }).await.unwrap();
    assert_eq!(
        rx.await.unwrap().unwrap(),
        ListResponse {
            mods: vec![make_remote_control_mod(), make_provincial_mod()]
        }
    );

    drop(commands_tx);
    manager_handle.await.unwrap();
}

async fn touch_file(path: PathBuf) -> Result<(), io::Error> {
    let file = OpenOptions::new()
        .create(true)
        .write(true)
        .open(path.clone())
        .await?;
    file.sync_all().await?;
    Ok(())
}

#[tokio::test]
async fn test_remove() {
    let mod_id = "some-mod";
    let dir = tempfile::tempdir().unwrap();

    let mod_path = dir.path().join(MODS_SUBPATH).join(mod_id);
    fs::create_dir_all(mod_path.clone()).await.unwrap();

    let lua_path = mod_path.join("main.lua");
    touch_file(lua_path.clone()).await.unwrap();

    let metadata_dir_path = dir.path().join(MOD_METADATA_SUBPATH).join(mod_id);
    fs::create_dir_all(metadata_dir_path.clone()).await.unwrap();

    let manifest_path = mod_path.join(MANIFEST_FILENAME);
    touch_file(manifest_path.clone()).await.unwrap();

    let dir_path = dir.path().to_str();
    if dir_path.is_none() {
        panic!("tempdir isn't valid unicode: {:?}", dir.path());
    }
    let (manager, commands_tx) = ModManager::new(dir_path.unwrap());
    let manager_handle = manager.spawn();

    let (tx, rx) = oneshot::channel();
    commands_tx
        .send(Command::Remove {
            id: mod_id.to_string(),
            resp: tx,
        })
        .await
        .unwrap();
    let resp = rx.await.unwrap().unwrap();
    assert_eq!(resp, RemoveResponse {});

    drop(commands_tx);
    manager_handle.await.unwrap();

    for p in [mod_path, lua_path, metadata_dir_path, manifest_path] {
        match fs::metadata(&p).await {
            Ok(_) => panic!("File/dir still exists: {:?}", p),
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => (),
                _ => panic!("Unexpected IO error: {:?}", e),
            },
        }
    }
    drop(dir);
}

async fn install_from_local_sources(
    commands_tx: &mpsc::Sender<Command>,
    source_file: &str,
    dest_id: &str,
) {
    let source_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(r"tests\data\local_sources")
        .join(source_file)
        .as_os_str()
        .to_str()
        .unwrap()
        .to_string();
    let (tx, rx) = oneshot::channel();
    commands_tx
        .send(Command::Install {
            package: InstallPackage::Local {
                source_path,
                dest_id: dest_id.to_string(),
            },
            resp: tx,
        })
        .await
        .unwrap();
    let resp = rx.await.unwrap().unwrap();
    assert_eq!(resp, InstallResponse {})
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
    let (manager, commands_tx) = ModManager::new(&dir.path().as_os_str().to_str().unwrap());
    let manager_handle = manager.spawn();

    let mod_id = "unchanged";
    install_from_local_sources(&commands_tx, "unchanged.txt", mod_id).await;
    assert_exits_in(&dir, mod_id, "unchanged.txt").await;

    let mod_id = "rename-lua";
    install_from_local_sources(&commands_tx, "rename_me.lua", mod_id).await;
    assert_exits_in(&dir, mod_id, "main.lua").await;

    let mod_id = "multi-lua";
    install_from_local_sources(&commands_tx, "multi_lua.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "ok.lua").await;
    assert_exits_in(&dir, mod_id, "fine.lua").await;

    let mod_id = "varying-prefixes";
    install_from_local_sources(&commands_tx, "varying_prefixes.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "a/foo.txt").await;
    assert_exits_in(&dir, mod_id, "b/bar.txt").await;

    let mod_id = "single-file";
    install_from_local_sources(&commands_tx, "single_file.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "lonely.txt").await;

    let mod_id = "only-mod-data";
    install_from_local_sources(&commands_tx, "only_mod_data.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "Data/inner.txt").await;

    let mod_id = "empty-dirs";
    install_from_local_sources(&commands_tx, "empty_dirs.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "x").await;
    assert_exits_in(&dir, mod_id, "y").await;

    let mod_id = "single-dir";
    install_from_local_sources(&commands_tx, "single_dir.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "foo.txt").await;

    let mod_id = "single-lua";
    install_from_local_sources(&commands_tx, "single_lua.zip", mod_id).await;
    assert_exits_in(&dir, mod_id, "main.lua").await;
    assert_exits_in(&dir, mod_id, "unchanged.txt").await;

    // let mod_id = "unicode";
    // install_from_local_sources(&commands_tx, "unicode.zip", mod_id).await;
    // assert_exits_in(&dir, mod_id, "unicode👀.txt").await;

    drop(commands_tx);
    manager_handle.await.unwrap()
}
