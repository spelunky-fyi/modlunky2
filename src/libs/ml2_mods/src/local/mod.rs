pub mod cache;
pub mod constants;
pub mod demo;
pub mod disk;

use async_trait::async_trait;
use serde::{Deserialize, Serialize};

use crate::{
    data::Mod,
    spelunkyfyi::http::{DownloadedMod, Mod as ApiMod},
};

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Mod {0} already exists")]
    AlreadyExists(String),
    #[error("Mod {0} wasn't found")]
    NotFound(String),
    #[error("Mod {0} isn't in a directory")]
    NonDirectory(String),

    #[error("Problem with installation source")]
    SourceError(#[source] anyhow::Error),
    #[error("Problem with the destination")]
    DestinationError(#[source] anyhow::Error),

    #[error("I/O error")]
    IoError(#[from] std::io::Error),

    #[error("Unknown error: {0}")]
    UnknownError(#[from] anyhow::Error),
}

pub type Result<R> = std::result::Result<R, Error>;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModLogo {
    pub mime_type: String,
    pub bytes: Vec<u8>,
}

#[async_trait]
pub trait LocalMods {
    async fn get(&self, id: &str) -> Result<Mod>;
    async fn list(&self) -> Result<Vec<Mod>>;
    async fn remove(&self, id: &str) -> Result<()>;
    async fn install_local(&self, source: &str, dest_id: &str) -> Result<Mod>;
    async fn install_remote(&self, downloaded: &DownloadedMod) -> Result<Mod>;
    async fn update_local(&self, source: &str, dest_id: &str) -> Result<Mod>;
    async fn update_remote(&self, downloaded: &DownloadedMod) -> Result<Mod>;
    async fn update_latest_json(&self, api_mod: &ApiMod) -> Result<Option<String>>;
    async fn get_mod_logo(&self, id: &str) -> Result<ModLogo>;
}
