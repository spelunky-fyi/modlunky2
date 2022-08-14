#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod mods;

use std::time::Duration;

use anyhow::anyhow;
use directories::{BaseDirs, ProjectDirs};
use ml2_mods::spelunkyfyi::http::DEFAULT_SERVICE_ROOT;
use ml2_net::http::new_http_client;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, Runtime};
use tokio::select;
use tokio_graceful_shutdown::{SubsystemHandle, Toplevel};
use tracing::info;

use crate::mods::setup_mod_management;

// IMPORTANT: This definition is incomplete and shouldn't be persisted
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub(crate) struct Config {
    install_dir: Option<String>,
    spelunky_fyi_api_token: Option<String>,
    spelunky_fyi_root: Option<String>,
}

impl Config {
    pub(crate) fn spelunky_fyi_root(&self) -> &str {
        self.spelunky_fyi_root
            .as_ref()
            .map(|s| s.as_str())
            .or(Some(DEFAULT_SERVICE_ROOT))
            .unwrap()
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let conf_subpath = ProjectDirs::from("", "spelunky.fyi", "modlunky2")
        .ok_or_else(|| anyhow!("Unable to determine config subdirectory"))?
        .project_path()
        .join("config.json");
    let conf_path = BaseDirs::new()
        .ok_or_else(|| anyhow!("Unable to determine config directory"))?
        .data_local_dir()
        .join(conf_subpath);
    info!("Config path: {:?}", conf_path);
    // This will fail if config doesn't exist!
    let config_json = tokio::fs::read(conf_path).await?;
    let config: Config = serde_json::from_slice(&config_json[..])?;

    tauri::async_runtime::set(tokio::runtime::Handle::current());
    let tauri_app = tauri::Builder::default().build(tauri::generate_context!())?;
    let app_handle = tauri_app.handle();

    let (exit_tx, exit_rx) = tokio::sync::oneshot::channel();
    let mut exit_tx_wrap = Some(exit_tx);
    let toplevel = {
        let app_handle = app_handle.clone();
        Toplevel::new()
            .catch_signals()
            .start("Exit Waiter", |subsys| {
                wait_for_exit(subsys, app_handle, exit_rx)
            })
    };

    let http_client = new_http_client();
    let toplevel = if config.install_dir.is_some() {
        let (toplevel, mod_manager_handle) =
            setup_mod_management(toplevel, app_handle.clone(), http_client, &config)?;
        tauri_app.manage(mod_manager_handle);
        toplevel
    } else {
        toplevel
    };

    let graceful_handle =
        tokio::spawn(toplevel.handle_shutdown_requests(Duration::from_millis(1000)));
    tauri_app.run(move |_app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            let inner = exit_tx_wrap.take();
            if inner.is_some() {
                let _ = inner.unwrap().send(());
            }
        }
    });

    graceful_handle.await??;
    Ok(())
}

/// This function bridges between Tauri events and the graceful shutdown system
async fn wait_for_exit<R: Runtime>(
    subsys: SubsystemHandle,
    app_handle: AppHandle<R>,
    exit_rx: tokio::sync::oneshot::Receiver<()>,
) -> anyhow::Result<()> {
    select! {
        ()  = subsys.on_shutdown_requested() => {app_handle.exit(0)},
        _ = exit_rx => {},
    }
    subsys.request_global_shutdown();
    Ok(())
}
