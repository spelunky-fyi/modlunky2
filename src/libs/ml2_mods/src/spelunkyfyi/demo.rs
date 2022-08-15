use anyhow::anyhow;
use async_trait::async_trait;
use tokio::sync::watch;
use tracing::{info, instrument};

use crate::data::DownloadProgress;

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
    async fn download_mod(
        &self,
        _code: &str,
        _main_tx: &watch::Sender<DownloadProgress>,
        _logo_tx: &watch::Sender<DownloadProgress>,
    ) -> Result<DownloadedMod> {
        info!("download_mod");
        Err(Error::UnknownError(anyhow!("Not implemented")))
    }
}
