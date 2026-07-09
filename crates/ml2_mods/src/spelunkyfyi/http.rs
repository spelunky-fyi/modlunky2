use std::{
    collections::HashMap,
    fmt::Debug,
    path::{Path, PathBuf},
};

use anyhow::anyhow;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use futures_util::StreamExt as _;
use reqwest::header::{AUTHORIZATION, CONTENT_LENGTH, CONTENT_TYPE, ToStrError};
use serde::{Deserialize, Serialize};
use tempfile::{TempDir, tempdir};
use tokio::{
    fs,
    io::{AsyncWrite, AsyncWriteExt as _},
    join,
    sync::watch,
};
use tracing::instrument;
use url::Url;

use crate::data::DownloadProgress;

use super::{Error, Result};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Mod {
    pub name: String,
    pub slug: String,
    pub self_url: String,
    pub submitter: User,
    pub collaborators: Vec<User>,
    pub description: String,
    pub mod_type: i32, // enum
    pub game: i32,     // enum
    pub logo: Option<String>,
    pub details: String,
    pub comments_allowed: bool,
    pub is_listed: bool,
    pub adult_content: bool,
    pub mod_files: Vec<ModFile>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct User {
    pub username: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModFile {
    pub id: String,
    pub created_at: DateTime<Utc>,
    pub filename: String,
    pub downloads: i64,
    pub download_url: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Image {
    pub id: String,
    pub created_at: DateTime<Utc>,
    pub image_url: String,
}

#[derive(Debug)]
pub struct DownloadedLogo {
    pub content_type: String,
    pub file: PathBuf,
}

#[derive(Debug)]
pub struct DownloadedMod {
    pub r#mod: Mod,
    pub mod_file: ModFile,

    pub main_file: PathBuf,
    pub logo_file: Option<DownloadedLogo>,

    // Kept alive to prevent the TempDir from being deleted
    _dir: TempDir,
}

#[async_trait]
pub trait RemoteMods {
    async fn get_manifest(&self, code: &str) -> Result<Mod>;
    async fn download_mod(
        &self,
        code: &str,
        main_tx: &watch::Sender<DownloadProgress>,
        logo_tx: &watch::Sender<DownloadProgress>,
    ) -> Result<DownloadedMod>;
    /// Ask the API "for each of these slugs, what's the newest ModFile?"
    /// Rolls up N `get_manifest` round trips into one POST. Callers must
    /// batch large lists themselves if they want an explicit progress
    /// hook; `HttpApiMods` implicitly chunks to `MAX_CHECK_UPDATES_SLUGS`
    /// per request and merges the responses.
    async fn check_updates(&self, slugs: &[&str]) -> Result<CheckUpdatesResponse>;
}

/// Server response to `POST /api/mods/check-updates/`. `mods` is keyed by
/// mod slug; `not_found` lists the slugs the server had no known file for
/// (mod was deleted / unlisted / has no ModFile yet). Callers should treat
/// a `not_found` slug as "no update available", not as an error.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckUpdatesResponse {
    pub mods: HashMap<String, ModFile>,
    #[serde(default)]
    pub not_found: Vec<String>,
}

impl CheckUpdatesResponse {
    fn empty() -> Self {
        Self {
            mods: HashMap::new(),
            not_found: Vec::new(),
        }
    }

    fn extend(&mut self, other: CheckUpdatesResponse) {
        self.mods.extend(other.mods);
        self.not_found.extend(other.not_found);
    }
}

/// Server-side cap on slugs per request (mirrors
/// `spelunky_fyi.mods.api.MAX_CHECK_UPDATES_SLUGS`). Requests over this
/// size are chunked and the responses merged before returning to the
/// caller so callers don't have to think about it.
pub const MAX_CHECK_UPDATES_SLUGS: usize = 200;

pub const DEFAULT_SERVICE_ROOT: &str = "https://spelunky.fyi";

#[derive(Clone, derive_more::Debug)]
pub struct HttpApiMods {
    base_url: Url,
    #[debug(skip)]
    auth_token: String,
    #[debug(skip)]
    client: reqwest::Client,
}

impl HttpApiMods {
    pub fn new(service_root: &str, auth_token: &str, client: reqwest::Client) -> Result<Self> {
        // reqwest's Url parser refuses relative bases, which matches what
        // we want: DEFAULT_SERVICE_ROOT is always an absolute URL, and a
        // misconfigured user-provided root should fail construction rather
        // than silently produce broken request URLs later.
        let base_url = Url::parse(service_root)?;
        Ok(HttpApiMods {
            auth_token: auth_token.to_string(),
            base_url,
            client,
        })
    }

    fn url_from_path(&self, path: &str) -> Result<Url> {
        // Url::join treats a leading slash as absolute (replaces the
        // base's path) and a bare segment as relative (appends to the
        // last '/' in the base). Normalize by forcing a leading slash so
        // callers can write "/api/mods/..." consistently regardless of
        // whether service_root had a trailing slash.
        let path = if path.starts_with('/') {
            path.to_string()
        } else {
            format!("/{path}")
        };
        Ok(self.base_url.join(&path)?)
    }

    async fn get_authed(&self, url: Url) -> Result<reqwest::Response> {
        let res = self
            .client
            .get(url)
            .header(AUTHORIZATION, format!("Token {}", self.auth_token))
            .send()
            .await?;
        check_status(res)
    }

    async fn post_json_authed<B: Serialize + ?Sized>(
        &self,
        url: Url,
        body: &B,
    ) -> Result<reqwest::Response> {
        let res = self
            .client
            .post(url)
            .header(AUTHORIZATION, format!("Token {}", self.auth_token))
            .json(body)
            .send()
            .await?;
        check_status(res)
    }

    #[instrument(skip(writer))]
    async fn download(
        &self,
        url: &str,
        writer: &mut (impl AsyncWrite + Debug + Send + Unpin),
        progress: &watch::Sender<DownloadProgress>,
    ) -> Result<String> {
        let _ = progress.send(DownloadProgress::Started());
        let res = self.client.get(url).send().await?;
        let res = check_status(res)?;

        let content_type = res
            .headers()
            .get(CONTENT_TYPE)
            .ok_or_else(|| Error::GenericHttpError(anyhow!("No content type for URL {url}")))?
            .to_str()?
            .to_string();
        let expected_bytes = res
            .headers()
            .get(CONTENT_LENGTH)
            .and_then(|v| v.to_str().ok())
            .and_then(|s| s.parse::<u64>().ok());

        tokio::pin!(writer);
        let mut received_bytes = 0_u64;
        let mut stream = res.bytes_stream();
        while let Some(chunk) = stream.next().await {
            let chunk = chunk?;
            received_bytes += chunk.len() as u64;
            let _ = progress.send(DownloadProgress::Receiving {
                expected_bytes,
                received_bytes,
            });
            writer.write_all(&chunk).await?;
        }
        writer.flush().await?;

        let _ = progress.send(DownloadProgress::Finished());
        Ok(content_type)
    }

    #[instrument(skip_all)]
    async fn download_mod_file(
        &self,
        mod_file: &ModFile,
        dir: &TempDir,
        progress: &watch::Sender<DownloadProgress>,
    ) -> Result<PathBuf> {
        let file_path = dir.path().join(&mod_file.filename);
        let mut file = fs::File::create(&file_path).await?;
        self.download(&mod_file.download_url, &mut file, progress)
            .await?;
        Ok(file_path)
    }

    #[instrument(skip_all)]
    async fn download_logo(
        &self,
        logo_url: &Option<String>,
        dir: &TempDir,
        progress: &watch::Sender<DownloadProgress>,
    ) -> Result<Option<DownloadedLogo>> {
        let Some(logo_url) = logo_url.as_ref() else {
            let _ = progress.send(DownloadProgress::Finished());
            return Ok(None);
        };

        let parsed = Url::parse(logo_url)?;
        let file_name = Path::new(parsed.path())
            .file_name()
            .ok_or_else(|| Error::UnknownError(anyhow!("Logo URL doesn't have a file name")))?;

        let file_path = dir.path().join(file_name);
        let mut file = fs::File::create(&file_path).await?;
        let content_type = self.download(logo_url, &mut file, progress).await?;
        Ok(Some(DownloadedLogo {
            file: file_path,
            content_type,
        }))
    }
}

#[async_trait]
impl RemoteMods for HttpApiMods {
    #[instrument]
    async fn get_manifest(&self, id: &str) -> Result<Mod> {
        let url = self.url_from_path(&format!("/api/mods/{id}"))?;
        let res = self.get_authed(url).await?;
        let m = res.json::<Mod>().await?;
        Ok(m)
    }

    #[instrument]
    async fn download_mod(
        &self,
        code: &str,
        main_tx: &watch::Sender<DownloadProgress>,
        logo_tx: &watch::Sender<DownloadProgress>,
    ) -> Result<DownloadedMod> {
        let api_mod = self.get_manifest(code).await?;

        let mod_file = api_mod
            .mod_files
            .first()
            .ok_or_else(|| Error::UnknownError(anyhow!("Mod had 0 files. Expected at least 1")))?
            .clone();

        let dir = tempdir()?;
        let (main_res, logo_res) = join!(
            self.download_mod_file(&mod_file, &dir, main_tx),
            self.download_logo(&api_mod.logo, &dir, logo_tx)
        );
        let (main_file, logo_file) = (main_res?, logo_res?);
        Ok(DownloadedMod {
            r#mod: api_mod,
            mod_file,
            main_file,
            logo_file,
            _dir: dir,
        })
    }

    #[instrument(skip(self))]
    async fn check_updates(&self, slugs: &[&str]) -> Result<CheckUpdatesResponse> {
        if slugs.is_empty() {
            return Ok(CheckUpdatesResponse::empty());
        }
        let url = self.url_from_path("/api/mods/check-updates/")?;

        // Chunk to the server-side cap. Doing this transparently means
        // callers with 300+ installed mods don't have to think about it.
        let mut merged = CheckUpdatesResponse::empty();
        for chunk in slugs.chunks(MAX_CHECK_UPDATES_SLUGS) {
            let body = CheckUpdatesRequest { slugs: chunk };
            let res = self.post_json_authed(url.clone(), &body).await?;
            let response = res.json::<CheckUpdatesResponse>().await?;
            merged.extend(response);
        }
        Ok(merged)
    }
}

/// Wire shape of the request body, borrowing the slugs slice from the
/// caller to skip allocating a Vec<String> for the round trip.
#[derive(Debug, Serialize)]
struct CheckUpdatesRequest<'a> {
    slugs: &'a [&'a str],
}

fn check_status(res: reqwest::Response) -> Result<reqwest::Response> {
    if !res.status().is_success() {
        return Err(Error::StatusError(res.status()));
    }
    Ok(res)
}

impl From<url::ParseError> for Error {
    fn from(e: url::ParseError) -> Error {
        Error::InvalidUri(e.into())
    }
}

impl From<ToStrError> for Error {
    fn from(e: ToStrError) -> Error {
        Error::GenericHttpError(e.into())
    }
}

impl From<std::num::ParseIntError> for Error {
    fn from(e: std::num::ParseIntError) -> Error {
        Error::GenericHttpError(e.into())
    }
}

impl From<reqwest::Error> for Error {
    fn from(e: reqwest::Error) -> Error {
        Error::GenericHttpError(e.into())
    }
}
