use anyhow::anyhow;
use async_trait::async_trait;
use tracing::{info, instrument};

use super::{
    http::{DownloadedMod, Mod, RemoteMods},
    Error, Result,
};

#[derive(Debug)]
pub struct LoggingRemoteMods;

#[async_trait]
impl RemoteMods for LoggingRemoteMods {
    #[instrument]
    async fn get_manifest(&self, _code: &str) -> Result<Mod> {
        info!("get_manifest");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }

    #[instrument]
    async fn download_mod(&self, _code: &str) -> Result<DownloadedMod> {
        info!("download_mod");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }
}
