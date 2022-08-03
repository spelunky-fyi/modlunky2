use std::{fmt::Debug, path::Path};

use anyhow::anyhow;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use derivative::Derivative;
use http::{
    header::{HeaderName, InvalidHeaderValue},
    uri::{InvalidUri, InvalidUriParts},
    HeaderValue, Request, Response, StatusCode, Uri,
};
use hyper::{
    body::{Buf, HttpBody},
    Body,
};
use hyper_tls::HttpsConnector;
use serde::{Deserialize, Serialize};
use tokio::{
    io::{AsyncWrite, AsyncWriteExt as _},
    sync::Mutex,
};
use tower::{util::BoxService, Service as _, ServiceBuilder, ServiceExt as _};
use tower_http::{
    classify::{NeverClassifyEos, ServerErrorsFailureClass},
    trace::{DefaultOnBodyChunk, DefaultOnEos, DefaultOnFailure, ResponseBody},
    ServiceBuilderExt,
};
use tracing::instrument;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Mod {
    name: String,
    slug: String,
    self_url: String,
    submitter: User,
    collaborators: Vec<User>,
    description: String,
    mod_type: i32, // enum
    game: i32,     // enum
    logo: String,
    details: String,
    comments_allowed: bool,
    is_listed: bool,
    adult_content: bool,
    mod_files: Vec<ModFile>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct User {
    username: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModFile {
    id: String,
    created_at: DateTime<Utc>,
    filename: String,
    downloads: i64,
    download_url: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Image {
    id: String,
    created_at: DateTime<Utc>,
    image_url: String,
}

type TracedResponse<B> = ResponseBody<
    B,
    NeverClassifyEos<ServerErrorsFailureClass>,
    DefaultOnBodyChunk,
    DefaultOnEos,
    DefaultOnFailure,
>;

type TracedHyperService = BoxService<Request<Body>, Response<TracedResponse<Body>>, hyper::Error>;

#[derive(Derivative)]
#[derivative(Debug)]
pub struct ApiClient {
    base_uri: Uri,
    #[derivative(Debug = "ignore")]
    client: Mutex<TracedHyperService>,
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Invalid URI: {0:?}")]
    InvalidUri(#[from] anyhow::Error),
    #[error("Invalid auth token")]
    InvalidToken(#[from] InvalidHeaderValue),

    #[error("HTTP status: {0}")]
    StatusError(StatusCode),
    #[error("HTTP error: {0}")]
    GenericHttpError(#[source] anyhow::Error),

    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    JsonError(#[from] serde_json::Error),

    #[error("Unknown error: {0:?}")]
    UnknownError(#[source] anyhow::Error),
}

type Result<R> = std::result::Result<R, Error>;

#[async_trait]
pub trait Api {
    async fn get_manifest(&mut self, id: &str) -> Result<Mod>;
    async fn download(
        &mut self,
        uri: &str,
        writer: &mut (impl AsyncWrite + Debug + Send + Unpin),
    ) -> Result<()>;
}

impl ApiClient {
    pub fn new(service_root: &str, auth_token: &str) -> Result<Self> {
        let authz_value = HeaderValue::from_str(&format!("Token {}", auth_token))?;
        let base_uri = service_root.parse::<Uri>()?;

        let authz_name = HeaderName::from_static("authorization");
        let inner_client =
            hyper::client::Client::builder().build::<_, hyper::Body>(HttpsConnector::new());
        let client = ServiceBuilder::new()
            // TODO: add a layer for retries with backoff
            .sensitive_headers([authz_name.clone()])
            .trace_for_http()
            .override_request_header(authz_name, authz_value)
            .follow_redirects()
            .service(inner_client);

        // Note: We're using BoxService to avoid writing out the type of `client`.
        // BoxService doesn't have a Sync bound, which forces us to wrap it in a
        // mutex despite the concrete type being Sync.
        let client = Mutex::new(BoxService::new(client));

        Ok(ApiClient { client, base_uri })
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

    fn checked_uri(&self, uri: &str) -> Result<Uri> {
        let uri = uri.parse::<Uri>()?;

        // We check that the supplied URI at least roughly corresponds to our base_uri
        if self.base_uri.scheme() != uri.scheme() {
            return Err(Error::InvalidUri(anyhow!(
                "expected scheme {:?}, got {:?}",
                self.base_uri.scheme(),
                uri.scheme()
            )));
        }
        if self.base_uri.authority() != uri.authority() {
            return Err(Error::InvalidUri(anyhow!(
                "expected authority {:?}, got {:?}",
                self.base_uri.authority(),
                uri.authority()
            )));
        }
        if !Path::new(uri.path()).starts_with(self.base_uri.path()) {
            return Err(Error::InvalidUri(anyhow!(
                "expected path to start with {:?}, got {:?}",
                self.base_uri.path(),
                uri.path()
            )));
        }

        Ok(uri)
    }

    async fn get_uri(&mut self, uri: &Uri) -> Result<Response<TracedResponse<Body>>> {
        let request = Request::get(uri)
            .version(http::Version::HTTP_11)
            .body(Body::empty())
            .map_err(|e| Error::UnknownError(e.into()))?;

        let res = self
            .client
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
}

#[async_trait]
impl Api for ApiClient {
    #[instrument]
    async fn get_manifest(&mut self, id: &str) -> Result<Mod> {
        let uri = self.uri_from_path(Path::new("/api/mods/").join(id))?;
        let res = self.get_uri(&uri).await?;
        let body = hyper::body::aggregate(res).await?;
        let m = serde_json::from_reader(body.reader())?;
        Ok(m)
    }

    #[instrument(skip(writer))]
    async fn download(
        &mut self,
        uri: &str,
        writer: &mut (impl AsyncWrite + Debug + Send + Unpin),
    ) -> Result<()> {
        let uri = self.checked_uri(uri)?;
        let mut res = self.get_uri(&uri).await?;
        tokio::pin!(writer);
        while let Some(chunk) = res.body_mut().data().await {
            let chunk = chunk?;
            writer.write_all(&chunk).await?;
        }
        Ok(())
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
