use std::{future::Future, time::Duration};

use anyhow::anyhow;
use ml2_mods::{
    data::{Change, ManagerError, Mod},
    local::{cache::ModCache, disk::DiskMods},
    manager::{ModManager, ModManagerHandle, ModSource, DEFAULT_RECEIVING_INTERVAL},
    spelunkyfyi::{
        http::HttpApiMods,
        web_socket::{self, WebSocketClient},
    },
};
use ml2_net::http::HttpClient;
use rand::distributions::Uniform;
use tauri::{
    http::{Request, Response, ResponseBuilder},
    AppHandle, Manager, Runtime,
};
use tokio::{
    select,
    sync::broadcast::{self, error::RecvError},
};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle, Toplevel};
use tracing::{instrument, warn};

use crate::Config;

pub(crate) fn setup_mod_management<R: Runtime>(
    toplevel: Toplevel,
    app_handle: AppHandle<R>,
    http_client: HttpClient,
    config: &Config,
) -> anyhow::Result<Toplevel> {
    let install_path = config.install_dir.clone().unwrap();
    let token: Option<&String> = config.spelunky_fyi_api_token.as_ref();
    let service_root = config.spelunky_fyi_root();

    let api_client = token
        .map(|token| HttpApiMods::new(service_root, token, http_client))
        .transpose()?;

    let (detected_tx, detected_rx) = broadcast::channel(10);
    let (mod_cache, _) = ModCache::new(
        api_client.clone(),
        Duration::from_secs(60 * 60),
        Duration::from_secs(10),
        detected_tx,
        DiskMods::new(&install_path),
        Duration::from_secs(15),
    );

    let (changes_tx, changes_rx) = broadcast::channel(10);
    let (manager, manager_handle) = ModManager::new(
        api_client,
        mod_cache.clone(),
        changes_tx,
        detected_rx,
        DEFAULT_RECEIVING_INTERVAL,
    );
    app_handle.manage(manager_handle.clone());

    let ping_interval_dist = Uniform::new(
        web_socket::DEFAULT_MIN_PING_INTERVAL,
        web_socket::DEFAULT_MAX_PING_INTERVAL,
    );
    let web_socket_client = token
        .as_ref()
        .map(|token| {
            WebSocketClient::new(
                service_root,
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
        .start("Mod Change Emitter", |subsys| {
            emit_mod_changes(subsys, app_handle, changes_rx)
        });
    if let Some(web_socket_client) = web_socket_client {
        toplevel = toplevel.start("WebSocket", web_socket_client.into_subsystem());
    }
    Ok(toplevel)
}

pub(crate) fn handle_mod_logo_request<R: Runtime>(
    app_handle: &AppHandle<R>,
    request: &Request,
) -> Result<Response, Box<dyn std::error::Error>> {
    let mod_id = request
        .uri()
        .strip_prefix("mod-logo://localhost/")
        .ok_or_else(|| anyhow!("Request URI {:?} has unexpected prefix", request.uri()))?;
    let manager: tauri::State<ModManagerHandle> = app_handle.state();

    let logo = {
        let mod_id = mod_id.to_string();
        let manager = manager.inner().clone();
        safe_block_on(async move { manager.get_mod_logo(&mod_id).await })?
    };
    ResponseBuilder::new()
        .status(200)
        .mimetype(&logo.mime_type)
        .body(logo.bytes)
}

// This works around block_on panicking when run from within Tokio.
// The code is copy-pasted from tauri/src/async_runtime.rs
pub(crate) fn safe_block_on<F>(task: F) -> F::Output
where
    F: Future + Send + 'static,
    F::Output: Send + 'static,
{
    if let Ok(handle) = tokio::runtime::Handle::try_current() {
        let (tx, rx) = std::sync::mpsc::sync_channel(1);
        let handle_ = handle.clone();
        handle.spawn_blocking(move || {
            tx.send(handle_.block_on(task)).unwrap();
        });
        rx.recv().unwrap()
    } else {
        tauri::async_runtime::block_on(task)
    }
}

#[instrument(skip_all)]
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

#[tauri::command]
pub(crate) async fn get_mod(
    id: String,
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<Mod, ManagerError> {
    Ok(manager_handle.get(&id).await?)
}

#[tauri::command]
pub(crate) async fn list_mods(
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<Vec<Mod>, ManagerError> {
    Ok(manager_handle.list().await?)
}

#[tauri::command]
pub(crate) async fn remove_mod(
    id: String,
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<(), ManagerError> {
    Ok(manager_handle.remove(&id).await?)
}

#[tauri::command]
pub(crate) async fn install_local_mod(
    source_path: String,
    dest_id: String,
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<Mod, ManagerError> {
    Ok(manager_handle
        .install(&ModSource::Local {
            source_path,
            dest_id,
        })
        .await?)
}

#[tauri::command]
pub(crate) async fn install_remote_mod(
    code: String,
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<Mod, ManagerError> {
    Ok(manager_handle.install(&ModSource::Remote { code }).await?)
}

#[tauri::command]
pub(crate) async fn update_local_mod(
    source_path: String,
    dest_id: String,
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<Mod, ManagerError> {
    Ok(manager_handle
        .update(&ModSource::Local {
            source_path,
            dest_id,
        })
        .await?)
}

#[tauri::command]
pub(crate) async fn update_remote_mod(
    code: String,
    manager_handle: tauri::State<'_, ModManagerHandle>,
) -> Result<Mod, ManagerError> {
    Ok(manager_handle.update(&ModSource::Remote { code }).await?)
}
