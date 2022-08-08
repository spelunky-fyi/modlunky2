use std::time::Duration;

use clap::{Parser, Subcommand};

use ml2_mods::{
    cache::ModCache,
    local::DiskMods,
    manager::{InstallPackage, ModManager},
    spelunkyfyi::http::ApiClient,
};
use tokio::{select, signal, sync::broadcast};

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
    let (mods_tx, mut mods_rx) = broadcast::channel(10);
    let (mod_cache, mod_cache_handle) = ModCache::new(
        api_client.clone(),
        Duration::from_secs(cli.api_poll_delay_sec),
        Duration::from_secs(cli.api_poll_delay_sec),
        mods_tx,
        DiskMods::new(&cli.install_path),
        Duration::from_secs(cli.local_scan_interval_sec),
    );
    let (manager, handle) = ModManager::new(api_client.clone(), mod_cache.clone());
    let mod_cache_join = mod_cache.spawn().await?;
    let manager_join = manager.spawn();

    match cli.command {
        Commands::Get { id } => {
            println!("{:#?}", handle.get(&id).await?);
        }
        Commands::List {} => {
            println!("{:#?}", handle.list().await?);
        }
        Commands::Remove { id } => {
            println!("{:#?}", handle.remove(&id).await?);
        }
        Commands::InstallLocal { source, id } => {
            let package = InstallPackage::Local {
                source_path: source,
                dest_id: id,
            };
            println!("{:#?}", handle.install(&package).await?);
        }
        Commands::InstallRemote { code } => {
            let package = InstallPackage::Remote { code };
            println!("{:#?}", handle.install(&package).await?);
        }
        Commands::Poll {} => loop {
            select! {
                res = signal::ctrl_c() => {
                    res?;
                    break
                },
                res = mods_rx.recv() => {
                    match res {
                        Ok(change) => println!("{:#?}", change),
                        Err(_) => break,
                    }
                },
            }
        },
    }

    mod_cache_handle.shutdown();
    drop(handle);
    manager_join.await?;
    mod_cache_join.await?;

    Ok(())
}
