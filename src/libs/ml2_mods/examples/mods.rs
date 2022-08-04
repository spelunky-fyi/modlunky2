use clap::{Parser, Subcommand};

use ml2_mods::{
    local::DiskMods,
    manager::{InstallPackage, ModManager},
    spelunkyfyi::http::ApiClient,
};

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
struct Cli {
    #[clap(short = 'i', long)]
    install_path: String,
    #[clap(short = 't', long)]
    token: Option<String>,
    #[clap(long, default_value_t = String::from("https://spelunky.fyi"))]
    service_root: String,

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
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();
    let api_client = cli
        .token
        .map(|token| ApiClient::new(&cli.service_root, &token))
        .transpose()?;
    let local_mods = DiskMods::new(&cli.install_path);
    let (manager, handle) = ModManager::new(api_client, local_mods);
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
    }

    drop(handle);
    manager_join.await?;

    Ok(())
}
