use std::time::Duration;

use ml2_mods::{
    data::Change,
    local::{cache::ModCache, disk::DiskMods},
    manager::{ModManager, ModManagerHandle},
    spelunkyfyi::{
        http::HttpApiMods,
        web_socket::{self, WebSocketClient},
    },
};
use ml2_net::http::HttpClient;
use rand::distributions::Uniform;
use tauri::{AppHandle, Manager, Runtime};
use tokio::{
    select,
    sync::broadcast::{self, error::RecvError},
};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle, Toplevel};
use tracing::log::warn;

use crate::Config;

pub(crate) fn setup_mod_management<R: Runtime>(
    toplevel: Toplevel,
    app_handle: AppHandle<R>,
    http_client: HttpClient,
    config: &Config,
) -> anyhow::Result<(Toplevel, ModManagerHandle)> {
    let install_path = config.install_dir.clone().unwrap();
    let token: Option<&String> = config.spelunky_fyi_api_token.as_ref();
    let service_root = config.spelunky_fyi_root();

    let api_client = token
        .map(|token| HttpApiMods::new(&service_root, token, http_client))
        .transpose()?;

    let (mods_tx, mods_rx) = broadcast::channel(10);
    let (mod_cache, _) = ModCache::new(
        api_client.clone(),
        Duration::from_secs(60 * 60),
        Duration::from_secs(10),
        mods_tx,
        DiskMods::new(&install_path),
        Duration::from_secs(15),
    );

    let (manager, manager_handle) = ModManager::new(api_client.clone(), mod_cache.clone());

    let ping_interval_dist = Uniform::new(
        web_socket::DEFAULT_MIN_PING_INTERVAL,
        web_socket::DEFAULT_MAX_PING_INTERVAL,
    );
    let web_socket_client = token
        .as_ref()
        .map(|token| {
            WebSocketClient::new(
                &service_root,
                token,
                manager_handle.clone(),
                ping_interval_dist,
                web_socket::DEFAULT_PONG_TIMEOUT,
            )
        })
        .transpose()?;

    let mut toplevel = toplevel
        .start("Mod Cache", mod_cache.into_subsystem())
        .start("Mod Manager", manager.into_subsystem())
        .start("Mod Change Emmitter", |subsys| {
            emit_mod_changes(subsys, app_handle, mods_rx)
        });
    if let Some(web_socket_client) = web_socket_client {
        toplevel = toplevel.start("WebSocket", web_socket_client.into_subsystem());
    }
    Ok((toplevel, manager_handle))
}

async fn emit_mod_changes<R: Runtime>(
    subsys: SubsystemHandle,
    app_handle: AppHandle<R>,
    mut mods_rx: broadcast::Receiver<Change>,
) -> anyhow::Result<()> {
    loop {
        select! {
            _ = subsys.on_shutdown_requested() => break,
            recv = mods_rx.recv() => match recv {
                Ok(change) => app_handle.emit_all("mod-change", change)?,
                Err(e) => match e {
                    RecvError::Closed => {}
                    RecvError::Lagged(missed) => {
                        warn!("Missed {} mod change events", missed);
                    }
                },
            }
        }
    }
    Ok(())
}
