use clap::{Parser, Subcommand};
use tokio::fs;

use ml2_mods::spelunkyfyi::http::ApiClient;

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
    Download { uri: String, file: String },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();

    let mut client = ApiClient::new(&cli.service_root, &cli.token)?;

    match cli.command {
        Commands::Info { code } => {
            let manifest = client.get_manifest(&code).await?;
            println!("{:#?}", manifest)
        }
        Commands::Download { uri, file } => {
            let mut f = fs::File::create(file).await?;
            client.download(&uri, &mut f).await?;
            println!("done!")
        }
    }

    Ok(())
}
