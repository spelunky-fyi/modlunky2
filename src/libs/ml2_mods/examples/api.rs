use std::path::PathBuf;

use anyhow::anyhow;
use clap::{Parser, Subcommand};
use ml2_net::http::new_http_client;
use tokio::fs;

use ml2_mods::spelunkyfyi::http::{HttpApiMods, RemoteMods};

#[derive(Parser)]
#[clap(author, version, about, long_about = None)]
struct Cli {
    #[clap(short = 't', long)]
    token: String,
    #[clap(long, default_value_t = String::from("https://spelunky.fyi"))]
    service_root: String,
    #[clap(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Info { code: String },
    DownloadMod { code: String, dir: String },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();

    let http_api_mods = HttpApiMods::new(&cli.service_root, &cli.token, new_http_client())?;

    match cli.command {
        Commands::Info { code } => {
            let manifest = http_api_mods.get_manifest(&code).await?;
            println!("{:#?}", manifest)
        }
        Commands::DownloadMod { code, dir } => {
            let downloaded = http_api_mods.download_mod(&code).await?;

            let dir = PathBuf::from(dir);
            fs::create_dir_all(&dir).await?;

            let main_dest = dir.join(
                downloaded
                    .main_file
                    .file_name()
                    .ok_or_else(|| anyhow!("No file name for main file"))?,
            );
            fs::copy(downloaded.main_file, main_dest).await?;

            if downloaded.logo_file.is_some() {
                println!("Ignoring mod logo");
            }

            println!("done!")
        }
    }

    Ok(())
}
