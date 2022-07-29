use std::path::PathBuf;

use tokio::sync::oneshot;

use ml2_mods::{
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

fn install_dir() -> String {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join(r"tests\data\install_dir")
        .to_str()
        .unwrap()
        .into()
}

#[tokio::test]
async fn test_get() {
    let (manager, commands_tx) = ModManager::new(&install_dir());
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
    let (manager, commands_tx) = ModManager::new(&install_dir());
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
