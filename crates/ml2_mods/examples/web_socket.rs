use std::time::Duration;

use clap::Parser;

use ml2_mods::{
    local::demo::LoggingLocalMods,
    manager::{DEFAULT_RECEIVING_INTERVAL, ModManager},
    spelunkyfyi::{
        demo::LoggingRemoteMods,
        web_socket::{
            DEFAULT_MAX_PING_INTERVAL, DEFAULT_MIN_PING_INTERVAL, DEFAULT_PONG_TIMEOUT,
            WebSocketClient,
        },
    },
};
use rand::distr::Uniform;
use tokio::sync::broadcast;
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemBuilder, SubsystemHandle, Toplevel};

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
struct Cli {
    #[clap(short = 't', long)]
    token: String,
    #[clap(long, default_value_t = String::from("https://spelunky.fyi"))]
    service_root: String,

    #[clap(long)]
    ping_min_interval: Option<u64>,
    #[clap(long)]
    ping_max_interval: Option<u64>,
    #[clap(long)]
    pong_timeout: Option<u64>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    let cli = Cli::parse();

    // These are "dangling" because this example doesn't wire up a full system
    let (_detected_tx, detected_rx) = broadcast::channel(10);
    let (changes_tx, _changes_rx) = broadcast::channel(10);
    let (manager, manager_handle) = ModManager::new(
        Some(LoggingRemoteMods),
        LoggingLocalMods,
        changes_tx,
        detected_rx,
        DEFAULT_RECEIVING_INTERVAL,
    );
    let ping_interval_dist = Uniform::new(
        cli.ping_min_interval
            .map(Duration::from_secs)
            .unwrap_or(DEFAULT_MIN_PING_INTERVAL),
        cli.ping_max_interval
            .map(Duration::from_secs)
            .unwrap_or(DEFAULT_MAX_PING_INTERVAL),
    )
    .expect("min ping interval < max");
    let pong_timeout = cli
        .pong_timeout
        .map(Duration::from_secs)
        .unwrap_or(DEFAULT_PONG_TIMEOUT);
    let client = WebSocketClient::new(
        &cli.service_root,
        &cli.token,
        manager_handle,
        ping_interval_dist,
        pong_timeout,
    )?;

    Toplevel::new(async move |s: &mut SubsystemHandle| {
        s.start(SubsystemBuilder::new(
            "ModManager",
            manager.into_subsystem(),
        ));
        s.start(SubsystemBuilder::new("WebSocket", client.into_subsystem()));
    })
    .catch_signals()
    .handle_shutdown_requests(Duration::from_millis(1000))
    .await?;
    Ok(())
}
