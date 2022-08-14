#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::time::Duration;

use tauri::{AppHandle, Runtime};
use tokio::select;
use tokio_graceful_shutdown::{SubsystemHandle, Toplevel};

async fn impatient(subsys: SubsystemHandle) -> anyhow::Result<()> {
    tokio::time::sleep(Duration::from_secs(5)).await;
    subsys.request_global_shutdown();
    Ok(())
}

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

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    tauri::async_runtime::set(tokio::runtime::Handle::current());
    let tauri_app = tauri::Builder::default().build(tauri::generate_context!())?;
    let app_handle = tauri_app.handle();

    let (exit_tx, exit_rx) = tokio::sync::oneshot::channel();
    let mut exit_tx_wrap = Some(exit_tx);
    let toplevel = Toplevel::new()
        .catch_signals()
        .start("Exit Waiter", |subsys| {
            wait_for_exit(subsys, app_handle, exit_rx)
        })
        .start("Impatient", impatient);

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
