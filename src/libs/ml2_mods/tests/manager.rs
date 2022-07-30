use std::io;
use std::path::PathBuf;

use anyhow::{anyhow, bail};
use ml2_mods::constants::MANIFEST_FILENAME;
use ml2_mods::manager::RemoveResponse;
use tokio::fs::{self, OpenOptions};
use tokio::sync::oneshot;

use ml2_mods::{
    constants::{MODS_SUBPATH, MOD_METADATA_SUBPATH},
    data::{Manifest, ManifestModFile, Mod},
    manager::{Command, GetResponse, ListResponse, ModManager},
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
async fn test_remove() -> Result<(), anyhow::Error> {
    let mod_id = "some-mod";
    // Note: panicking will leak the tempdir
    let dir = tempfile::tempdir()?;

    let mod_path = dir.path().join(MODS_SUBPATH).join(mod_id);
    fs::create_dir_all(mod_path.clone()).await?;

    let lua_path = mod_path.join("main.lua");
    touch_file(lua_path.clone()).await?;

    let metadata_dir_path = dir.path().join(MOD_METADATA_SUBPATH).join(mod_id);
    fs::create_dir_all(metadata_dir_path.clone()).await?;

    let manifest_path = mod_path.join(MANIFEST_FILENAME);
    touch_file(manifest_path.clone()).await?;

    let dir_path = dir.path().to_str();
    if dir_path.is_none() {
        bail!("tempdir isn't valid unicode: {:?}", dir.path());
    }
    let (manager, commands_tx) = ModManager::new(dir_path.unwrap());
    let manager_handle = manager.spawn();

    let (tx, rx) = oneshot::channel();
    commands_tx
        .send(Command::Remove {
            id: mod_id.to_string(),
            resp: tx,
        })
        .await?;
    // We'll check this later since assert_eq! may panic
    let resp = rx.await??;

    drop(commands_tx);
    manager_handle.await?;

    for p in [mod_path, lua_path, metadata_dir_path, manifest_path] {
        match fs::metadata(p.clone()).await {
            Ok(_) => Err(anyhow!("File/dir still exists: {:?}", p)),
            Err(e) => match e.kind() {
                io::ErrorKind::NotFound => Ok(()),
                _ => Err(e.into()),
            },
        }?;
    }
    drop(dir);

    assert_eq!(resp, RemoveResponse {});

    Ok(())
}
