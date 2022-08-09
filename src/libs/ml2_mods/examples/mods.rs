use std::time::Duration;

use clap::{Parser, Subcommand};

use ml2_mods::{
    cache::{ModCache, ModCacheHandle},
    data::Change,
    local::DiskMods,
    manager::{InstallPackage, ModManager, ModManagerHandle},
    spelunkyfyi::http::ApiClient,
};
use tokio::{select, sync::broadcast};
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemHandle, Toplevel};

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
struct Cli {
    #[clap(short = 'i', long)]
    install_path: String,
    #[clap(short = 't', long)]
    token: Option<String>,
    #[clap(long, default_value_t = String::from("https://spelunky.fyi"))]
    service_root: String,
    #[clap(long, default_value_t = 15)]
    api_poll_interval_sec: u64,
    #[clap(long, default_value_t = 1)]
    api_poll_delay_sec: u64,
    #[clap(long, default_value_t = 5)]
    local_scan_interval_sec: u64,

    #[clap(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Get { id: String },
    List {},
    Remove { id: String },
    InstallLocal { source: String, id: String },
    InstallRemote { code: String },
    UpdateLocal { source: String, id: String },
    UpdateRemote { code: String },
    Poll {},
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();
    let api_client = cli
        .token
        .map(|token| ApiClient::new(&cli.service_root, &token))
        .transpose()?;
    let (mods_tx, mods_rx) = broadcast::channel(10);
    let (mod_cache, mod_cache_handle) = ModCache::new(
        api_client.clone(),
        Duration::from_secs(cli.api_poll_delay_sec),
        Duration::from_secs(cli.api_poll_delay_sec),
        mods_tx,
        DiskMods::new(&cli.install_path),
        Duration::from_secs(cli.local_scan_interval_sec),
    );
    let (manager, handle) = ModManager::new(api_client.clone(), mod_cache.clone());
    Toplevel::new()
        .catch_signals()
        .start("ModCache", mod_cache.into_subsystem())
        .start("ModManager", manager.into_subsystem())
        .start("CLI", |h| {
            run(h, cli.command, handle, mod_cache_handle, mods_rx)
        })
        .handle_shutdown_requests(Duration::from_millis(1000))
        .await?;

    Ok(())
}

async fn run(
    subsystem: SubsystemHandle,
    cmd: Commands,
    manager: ModManagerHandle,
    cache: ModCacheHandle,
    mut mods_rx: broadcast::Receiver<Change>,
) -> anyhow::Result<()> {
    cache.ready().await;
    match cmd {
        Commands::Get { id } => {
            println!("{:#?}", manager.get(&id).await?);
        }
        Commands::List {} => {
            println!("{:#?}", manager.list().await?);
        }
        Commands::Remove { id } => {
            println!("{:#?}", manager.remove(&id).await?);
        }
        Commands::InstallLocal { source, id } => {
            let package = InstallPackage::Local {
                source_path: source,
                dest_id: id,
            };
            println!("{:#?}", manager.install(&package).await?);
        }
        Commands::InstallRemote { code } => {
            let package = InstallPackage::Remote { code };
            println!("{:#?}", manager.install(&package).await?);
        }
        Commands::UpdateLocal { source, id } => {
            let package = InstallPackage::Local {
                source_path: source,
                dest_id: id,
            };
            println!("{:#?}", manager.install(&package).await?);
        }
        Commands::UpdateRemote { code } => {
            let package = InstallPackage::Remote { code };
            println!("{:#?}", manager.update(&package).await?);
        }
        Commands::Poll {} => loop {
            select! {
                _ = subsystem.on_shutdown_requested() => break,
                Ok(change) = mods_rx.recv() => println!("{:#?}", change),
            }
        },
    }
    subsystem.request_global_shutdown();
    Ok(())
}
