use clap::{Parser, Subcommand};

use ml2_mods::manager::{InstallPackage, ModManager};

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
struct Cli {
    #[clap(short = 'd', long, value_parser)]
    install_dir: String,

    #[clap(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Get { id: String },
    List {},
    Remove { id: String },
    InstallLocal { source: String, id: String },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();

    let (manager, handle) = ModManager::new(&cli.install_dir);
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
    }

    drop(handle);
    manager_join.await?;

    Ok(())
}
