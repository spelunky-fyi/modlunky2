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
use tauri::{AppHandle, Runtime};
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
            .as_deref()
            .unwrap_or(DEFAULT_SERVICE_ROOT)
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
    let tauri_app = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            mods::get_mod,
            mods::list_mods,
            mods::remove_mod,
            mods::install_local_mod,
            mods::install_remote_mod,
            mods::update_local_mod,
            mods::update_remote_mod
        ])
        .build(tauri::generate_context!())?;

    let (exit_tx, exit_rx) = tokio::sync::oneshot::channel();
    let mut exit_tx_wrap = Some(exit_tx);
    let toplevel = {
        let app_handle = tauri_app.handle();
        Toplevel::new()
            .catch_signals()
            .start("Exit Waiter", |subsys| {
                wait_for_exit(subsys, app_handle, exit_rx)
            })
    };

    let http_client = new_http_client();
    let toplevel = if config.install_dir.is_some() {
        setup_mod_management(toplevel, tauri_app.handle(), http_client, &config)?
    } else {
        toplevel
    };

    let graceful_handle =
        tokio::spawn(toplevel.handle_shutdown_requests(Duration::from_millis(1000)));
    tauri_app.run(move |_app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            if let Some(inner) = exit_tx_wrap.take() {
                let _ = inner.send(());
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
