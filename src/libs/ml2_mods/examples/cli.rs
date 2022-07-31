use clap::{Parser, Subcommand};
use tokio::sync::oneshot;

use ml2_mods::manager::{self, InstallPackage, ModManager};

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

    let (manager, commands_tx) = ModManager::new(&cli.install_dir);
    let manager_handle = manager.spawn();

    match cli.command {
        Commands::Get { id } => {
            let (resp_tx, resp_rx) = oneshot::channel();
            commands_tx
                .send(manager::Command::Get { id, resp: resp_tx })
                .await?;
            println!("{:#?}", resp_rx.await??);
        }
        Commands::List {} => {
            let (resp_tx, resp_rx) = oneshot::channel();
            commands_tx
                .send(manager::Command::List { resp: resp_tx })
                .await?;
            println!("{:#?}", resp_rx.await??);
        }
        Commands::Remove { id } => {
            let (resp_tx, resp_rx) = oneshot::channel();
            commands_tx
                .send(manager::Command::Remove { id, resp: resp_tx })
                .await?;
            println!("{:#?}", resp_rx.await??);
        }
        Commands::InstallLocal { source, id } => {
            let (resp_tx, resp_rx) = oneshot::channel();
            let package = InstallPackage::Local {
                source_path: source,
                dest_id: id,
            };
            commands_tx
                .send(manager::Command::Install {
                    package,
                    resp: resp_tx,
                })
                .await?;
            println!("{:#?}", resp_rx.await??);
        }
    }

    drop(commands_tx);
    manager_handle.await?;

    Ok(())
}
