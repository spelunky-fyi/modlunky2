use std::time::Duration;

use clap::Parser;

use ml2_mods::spelunkyfyi::web_socket::WebSocketClient;
use rand::distributions::Uniform;
use tokio_graceful_shutdown::{IntoSubsystem, Toplevel};

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
struct Cli {
    #[clap(short = 't', long)]
    token: String,
    #[clap(long, default_value_t = String::from("https://spelunky.fyi"))]
    service_root: String,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    let cli = Cli::parse();

    let ping_interval_dist = Uniform::new(Duration::from_secs(15), Duration::from_secs(25));
    let pong_timeout = Duration::from_secs(10);
    let client = WebSocketClient::new(
        &cli.service_root,
        &cli.token,
        ping_interval_dist,
        pong_timeout,
    )?;

    Toplevel::new()
        .catch_signals()
        .start("WebSocket", client.into_subsystem())
        .handle_shutdown_requests(Duration::from_millis(1000))
        .await?;
    Ok(())
}
