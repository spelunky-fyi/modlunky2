use std::{
    fmt::Debug,
    path::{Path, PathBuf},
    sync::Arc,
};

use anyhow::anyhow;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use derivative::Derivative;
use http::{
    header::{ToStrError, AUTHORIZATION, CONTENT_TYPE},
    uri::{InvalidUri, InvalidUriParts},
    HeaderValue, Request, Response, Uri,
};
use hyper::{
    body::{Buf, HttpBody},
    Body,
};
use ml2_net::http::{HttpClient, TracedResponse};
use serde::{Deserialize, Serialize};
use tempfile::{tempdir, TempDir};
use tokio::{
    fs,
    io::{AsyncWrite, AsyncWriteExt as _},
    sync::Mutex,
};
use tower::{Service as _, ServiceExt as _};
use tracing::instrument;

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

    // We cart this around to prevent the TempDir from being deleted
    _dir: TempDir,
}

#[async_trait]
pub trait RemoteMods {
    async fn get_manifest(&self, code: &str) -> Result<Mod>;
    async fn download_mod(&self, code: &str) -> Result<DownloadedMod>;
}

pub const DEFAULT_SERVICE_ROOT: &str = "https://spelunky.fyi";

#[derive(Clone, Derivative)]
#[derivative(Debug)]
pub struct HttpApiMods {
    base_uri: Uri,
    #[derivative(Debug = "ignore")]
    auth_token: String,
    #[derivative(Debug = "ignore")]
    http_client: Arc<Mutex<HttpClient>>,
}

enum Auth {
    Yes(),
    No(),
}

impl HttpApiMods {
    pub fn new(service_root: &str, auth_token: &str, http_client: HttpClient) -> Result<Self> {
        Ok(HttpApiMods {
            auth_token: auth_token.to_string(),
            base_uri: service_root.parse::<Uri>()?,
            http_client: Arc::new(Mutex::new(http_client)),
        })
    }

    fn uri_from_path(&self, path: impl AsRef<Path> + Debug) -> Result<Uri> {
        let path = Path::new(self.base_uri.path()).join(path);
        let path = path
            .to_str()
            .ok_or_else(|| Error::InvalidUri(anyhow!("Failed to convert {:?}", path)))?;

        let mut parts = self.base_uri.clone().into_parts();
        parts.path_and_query = Some(path.try_into()?);

        let uri = Uri::from_parts(parts)?;
        Ok(uri)
    }

    async fn get_uri(&self, uri: &Uri, auth: Auth) -> Result<Response<TracedResponse<Body>>> {
        let request = Request::get(uri).version(http::Version::HTTP_11);
        let request = match auth {
            Auth::Yes() => {
                let authz_value = HeaderValue::from_str(&format!("Token {}", self.auth_token))?;
                request.header(AUTHORIZATION, authz_value)
            }
            Auth::No() => request,
        };

        let request = request
            .body(Body::empty())
            .map_err(|e| Error::UnknownError(e.into()))?;

        let res = self
            .http_client
            .lock()
            .await
            .ready()
            .await?
            .call(request)
            .await?;
        if !res.status().is_success() {
            return Err(Error::StatusError(res.status()));
        }
        Ok(res)
    }

    #[instrument(skip(writer))]
    async fn download(
        &self,
        uri: &str,
        writer: &mut (impl AsyncWrite + Debug + Send + Unpin),
    ) -> Result<String> {
        let uri = uri.parse::<Uri>()?;
        let mut res = self.get_uri(&uri, Auth::No()).await?;
        let content_type = res
            .headers()
            .get(CONTENT_TYPE)
            .map(|v| v.to_str())
            .transpose()?
            .map(|s| s.to_string());
        tokio::pin!(writer);
        while let Some(chunk) = res.body_mut().data().await {
            let chunk = chunk?;
            writer.write_all(&chunk).await?;
        }
        content_type
            .ok_or_else(|| Error::GenericHttpError(anyhow!("No content type for URI {}", uri)))
    }

    #[instrument(skip_all)]
    async fn download_mod_file(&self, mod_file: &ModFile, dir: &TempDir) -> Result<PathBuf> {
        let file_path = dir.path().join(&mod_file.filename);
        let mut file = fs::File::create(&file_path).await?;
        self.download(&mod_file.download_url, &mut file).await?;
        Ok(file_path)
    }

    #[instrument(skip_all)]
    async fn download_logo(
        &self,
        logo_url: &Option<String>,
        dir: &TempDir,
    ) -> Result<Option<DownloadedLogo>> {
        if logo_url.is_none() {
            return Ok(None);
        }
        let logo_url = logo_url.as_ref().unwrap();

        let uri = logo_url.parse::<Uri>()?;
        let file_name = Path::new(uri.path())
            .file_name()
            .ok_or_else(|| Error::UnknownError(anyhow!("Logo URL doesn't have a file name")))?;

        let file_path = dir.path().join(&file_name);
        let mut file = fs::File::create(&file_path).await?;
        let content_type = self.download(logo_url, &mut file).await?;
        let logo = DownloadedLogo {
            file: file_path,
            content_type,
        };
        Ok(Some(logo))
    }
}

#[async_trait]
impl RemoteMods for HttpApiMods {
    #[instrument]
    async fn get_manifest(&self, id: &str) -> Result<Mod> {
        let uri = self.uri_from_path(Path::new("/api/mods/").join(id))?;
        let res = self.get_uri(&uri, Auth::Yes()).await?;
        let body = hyper::body::aggregate(res).await?;
        let m = serde_json::from_reader(body.reader())?;
        Ok(m)
    }

    #[instrument]
    async fn download_mod(&self, code: &str) -> Result<DownloadedMod> {
        let api_mod = self.get_manifest(code).await?;

        let mod_file = api_mod
            .mod_files
            .first()
            .ok_or_else(|| Error::UnknownError(anyhow!("Mod had 0 files. Expected at least 1")))?
            .clone();

        let dir = tempdir()?;
        let main_file = self.download_mod_file(&mod_file, &dir).await?;
        let logo_file = self.download_logo(&api_mod.logo, &dir).await?;
        Ok(DownloadedMod {
            r#mod: api_mod,
            mod_file,
            main_file,
            logo_file,
            _dir: dir,
        })
    }
}

impl From<InvalidUri> for Error {
    fn from(e: InvalidUri) -> Error {
        Error::InvalidUri(e.into())
    }
}

impl From<InvalidUriParts> for Error {
    fn from(e: InvalidUriParts) -> Error {
        Error::InvalidUri(e.into())
    }
}

impl From<ToStrError> for Error {
    fn from(e: ToStrError) -> Error {
        Error::GenericHttpError(e.into())
    }
}

impl From<http::Error> for Error {
    fn from(e: http::Error) -> Error {
        Error::GenericHttpError(e.into())
    }
}

impl From<hyper::Error> for Error {
    fn from(e: hyper::Error) -> Error {
        Error::GenericHttpError(e.into())
    }
}
