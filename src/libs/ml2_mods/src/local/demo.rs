use anyhow::anyhow;
use async_trait::async_trait;
use tracing::{info, instrument};

use super::{Error, LocalMods, Result};
use crate::{
    data::Mod,
    spelunkyfyi::http::{DownloadedMod, Mod as ApiMod},
};

#[derive(Debug)]
pub struct LoggingLocalMods;

#[async_trait]
impl LocalMods for LoggingLocalMods {
    #[instrument]
    async fn get(&self, _id: &str) -> Result<Mod> {
        info!("get");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn list(&self) -> Result<Vec<Mod>> {
        info!("list");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn remove(&self, _id: &str) -> Result<()> {
        info!("remove");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn install_local(&self, _source: &str, _dest_id: &str) -> Result<Mod> {
        info!("install_local");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn install_remote(&self, _downloaded: &DownloadedMod) -> Result<Mod> {
        info!("install_remote");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn update_local(&self, _source: &str, _dest_id: &str) -> Result<Mod> {
        info!("update_local");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn update_remote(&self, _downloaded: &DownloadedMod) -> Result<Mod> {
        info!("update_remote");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn update_latest_json(&self, _api_mod: &ApiMod) -> Result<Option<String>> {
        info!("update_latest_json");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }
}
