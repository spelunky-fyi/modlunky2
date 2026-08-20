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
    /// Enum, and nullable on the server (`mod_type` is `null=True`). A bare
    /// `i32` here fails deserialization outright on an untyped mod, which
    /// turns a cosmetic gap in someone's submission into a failed install.
    pub mod_type: Option<i32>,
    pub game: i32, // enum
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

/// One page of a DRF `LimitOffsetPagination` response.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Page<T> {
    pub count: i64,
    /// Absolute URLs the server built. Kept as strings rather than parsed
    /// because callers only ever test them for presence: paging is driven by
    /// `limit`/`offset` so the client controls page size.
    pub next: Option<String>,
    pub previous: Option<String>,
    pub results: Vec<T>,
}

/// A screenshot an author uploaded to their mod page. First-party: these live
/// on our own media domain, never hotlinked, which is what makes them safe to
/// show in-app when the markdown `details` are not.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct PreviewImage {
    pub id: String,
    pub created_at: DateTime<Utc>,
    pub image_url: String,
}

/// A mod as it appears in a browse listing.
///
/// Deliberately not `Mod`: the detail endpoint carries `details` (markdown a
/// stranger wrote) and the full file history, neither of which a card needs and
/// both of which cost bandwidth on every row. Everything here is either a
/// number, a date, or text the site renders as plain text.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ModListing {
    pub id: String,
    pub slug: String,
    pub name: String,
    pub description: String,
    /// Where to send someone who wants the full page, comments included.
    pub web_url: String,
    pub submitter: User,
    #[serde(default)]
    pub collaborators: Vec<User>,
    /// Nullable on the server, so nullable here. A hard `i32` would fail the
    /// whole page over one untyped mod.
    pub mod_type: Option<i32>,
    pub mod_type_display: Option<String>,
    pub game: i32,
    pub game_display: String,
    /// The author's upload, or null. Prefer `logo_url`.
    pub logo: Option<String>,
    /// Always present: the uploaded logo when there is one, otherwise the
    /// spelunkicon the website generates from the slug. Resolved server-side so
    /// clients do not each invent a placeholder or hardcode that path.
    pub logo_url: String,
    pub adult_content: bool,
    #[serde(default)]
    pub favorited: bool,
    pub downloads: i64,
    pub rating_avg: f64,
    pub rating_count: i64,
    pub comment_count: i64,
    pub favorites_count: i64,
    pub created_at: DateTime<Utc>,
    pub listed_at: Option<DateTime<Utc>>,
    pub updated_at: DateTime<Utc>,
    /// Newest downloadable file. `None` only in states the browse filter
    /// already excludes, but the server can serve this shape elsewhere.
    pub latest_file: Option<ModFile>,
    /// Only sent when the request asked for it, hence the default. Carrying
    /// them on the listing is what lets a detail view render screenshots
    /// without a second round trip.
    #[serde(default)]
    pub preview_images: Vec<PreviewImage>,
}

/// The detail view, minus the prose.
///
/// Note what is *absent*: `details`, the markdown write-up. Modlunky never
/// renders a stranger's markdown, because doing so would put user-authored HTML
/// in the same process as an IPC bridge that can write to the game folder.
/// Everything here is a number, a date, plain text the site stores unformatted,
/// or an image we host ourselves. Anyone who wants the write-up gets `web_url`
/// and a real browser.
///
/// The server still sends `details` because the install path's `Mod` needs it;
/// serde drops unknown fields, so declaring it nowhere here is what makes it
/// unreachable rather than merely unused.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ModDetail {
    pub name: String,
    pub slug: String,
    pub web_url: String,
    pub description: String,
    pub submitter: User,
    #[serde(default)]
    pub collaborators: Vec<User>,
    pub mod_type: Option<i32>,
    pub mod_type_display: Option<String>,
    pub game: i32,
    pub game_display: String,
    /// The author's upload, or null. Prefer `logo_url`.
    pub logo: Option<String>,
    /// Always present: the uploaded logo when there is one, otherwise the
    /// spelunkicon the website generates from the slug. Resolved server-side so
    /// clients do not each invent a placeholder or hardcode that path.
    pub logo_url: String,
    pub adult_content: bool,
    #[serde(default)]
    pub favorited: bool,
    pub downloads: i64,
    pub rating_avg: f64,
    pub rating_count: i64,
    pub comment_count: i64,
    pub favorites_count: i64,
    pub created_at: DateTime<Utc>,
    pub listed_at: Option<DateTime<Utc>>,
    pub updated_at: DateTime<Utc>,
    #[serde(default)]
    pub mod_files: Vec<ModFile>,
    pub latest_file: Option<ModFile>,
    #[serde(default)]
    pub preview_images: Vec<PreviewImage>,
}

/// Filters for `GET /api/mods/`. Every `None` field is simply omitted, which
/// the server reads as "no filter"; sending an empty value instead would be
/// rejected for the typed fields.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct BrowseQuery {
    pub q: Option<String>,
    pub game: Option<i32>,
    pub mod_type: Option<i32>,
    pub favorite: Option<bool>,
    pub rated: Option<String>,
    pub order_by: Option<String>,
    pub limit: Option<u32>,
    pub offset: Option<u32>,
    /// Opt-in heavy fields, e.g. `preview_images`. The server rejects names it
    /// does not know rather than ignoring them, so a typo here is a 400 and not
    /// a silently missing field.
    pub include: Vec<String>,
}

impl BrowseQuery {
    /// Built by hand rather than through serde so that "absent" and "empty"
    /// stay distinguishable. `favorite=` with no value is a 400, not a default.
    fn to_pairs(&self) -> Vec<(&'static str, String)> {
        let mut pairs = Vec::new();
        if let Some(q) = self.q.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()) {
            pairs.push(("q", q.to_string()));
        }
        if let Some(game) = self.game {
            pairs.push(("game", game.to_string()));
        }
        if let Some(mod_type) = self.mod_type {
            pairs.push(("mod_type", mod_type.to_string()));
        }
        if let Some(favorite) = self.favorite {
            pairs.push(("favorite", favorite.to_string()));
        }
        if let Some(rated) = self
            .rated
            .as_ref()
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
        {
            pairs.push(("rated", rated.to_string()));
        }
        if let Some(order_by) = self
            .order_by
            .as_ref()
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
        {
            pairs.push(("order_by", order_by.to_string()));
        }
        if let Some(limit) = self.limit {
            pairs.push(("limit", limit.to_string()));
        }
        if let Some(offset) = self.offset {
            pairs.push(("offset", offset.to_string()));
        }
        if !self.include.is_empty() {
            pairs.push(("include", self.include.join(",")));
        }
        pairs
    }
}

/// A `{value, label}` pair from the browse-options endpoint.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct OrderByChoice {
    pub value: String,
    pub label: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModTypeChoice {
    pub value: i32,
    pub label: String,
    #[serde(default)]
    pub help_text: String,
}

/// Everything the filter bar needs, straight from the enums the server
/// validates against. Fetched rather than hardcoded because mod types are
/// per-game and drift the moment a new one is added.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BrowseOptions {
    pub game: Option<i32>,
    pub mod_types: Vec<ModTypeChoice>,
    pub order_by: Vec<OrderByChoice>,
    pub default_order_by: String,
    pub rated: Vec<OrderByChoice>,
    /// The account's own display preferences, so a client can honor the same
    /// choices the website does rather than showing someone the adult mods or
    /// the star ratings they asked not to see.
    pub allow_adult: bool,
    pub hide_ratings: bool,
}

/// The one include the browse grid asks for. Mirrors
/// `spelunky_fyi.mods.api.LIST_INCLUDES`.
pub const INCLUDE_PREVIEW_IMAGES: &str = "preview_images";

/// `Mod.game` value for Spelunky 2. Modlunky only ever browses this one.
pub const GAME_SPELUNKY_2: i32 = 1;

/// The client id this app identifies as when linking an account. Must match an
/// entry in `spelunky_fyi.user_account.app_links.APP_LINK_CLIENTS`.
pub const APP_LINK_CLIENT_ID: &str = "modlunky2";

#[derive(Debug, Serialize)]
struct AppLinkExchangeRequest<'a> {
    code: &'a str,
    code_verifier: &'a str,
    client_id: &'a str,
}

/// What the site hands back once a link code is redeemed.
#[derive(Clone, Debug, PartialEq, Eq, Deserialize)]
pub struct AppLinkToken {
    pub token: String,
    pub username: String,
}

/// Trade a one-time link code, plus the PKCE verifier that never left this
/// process, for the user's API token.
///
/// Unauthenticated by definition: a client calling this is precisely one that
/// does not have a token yet, which is why it takes a bare service root rather
/// than going through `HttpApiMods`.
///
/// Every server-side failure is the same opaque 400, so there is nothing useful
/// to distinguish here either. The caller shows one message and lets the user
/// start over.
#[instrument(skip(code, code_verifier, client))]
pub async fn exchange_app_link_code(
    service_root: &str,
    code: &str,
    code_verifier: &str,
    client: &reqwest::Client,
) -> Result<AppLinkToken> {
    let base = Url::parse(service_root)?;
    let url = base.join("/api/app-link/exchange/")?;
    let res = client
        .post(url)
        .json(&AppLinkExchangeRequest {
            code,
            code_verifier,
            client_id: APP_LINK_CLIENT_ID,
        })
        .send()
        .await?;
    let res = check_status(res)?;
    Ok(res.json::<AppLinkToken>().await?)
}

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

/// Browsing the directory.
///
/// Deliberately outside the `RemoteMods` trait. That trait is the contract the
/// mod manager needs, and the manager is a single-task actor with a depth-one
/// command channel: routing a browse request through it would park it behind
/// whatever install is currently downloading. Browsing is a read-through to the
/// API with no local state, so it skips the actor entirely.
impl HttpApiMods {
    #[instrument(skip(self))]
    pub async fn list_mods(&self, query: &BrowseQuery) -> Result<Page<ModListing>> {
        let mut url = self.url_from_path("/api/mods/")?;
        {
            let mut pairs = url.query_pairs_mut();
            for (key, value) in query.to_pairs() {
                pairs.append_pair(key, &value);
            }
        }
        let res = self.get_authed(url).await?;
        Ok(res.json::<Page<ModListing>>().await?)
    }

    /// The detail endpoint, deserialized into the prose-free shape the app
    /// shows. Same URL `get_manifest` uses; a different view of the response.
    #[instrument(skip(self))]
    pub async fn get_mod_detail(&self, slug: &str) -> Result<ModDetail> {
        let url = self.url_from_path(&format!("/api/mods/{slug}"))?;
        let res = self.get_authed(url).await?;
        Ok(res.json::<ModDetail>().await?)
    }

    #[instrument(skip(self))]
    pub async fn browse_options(&self, game: Option<i32>) -> Result<BrowseOptions> {
        let mut url = self.url_from_path("/api/mods/browse-options/")?;
        if let Some(game) = game {
            url.query_pairs_mut().append_pair("game", &game.to_string());
        }
        let res = self.get_authed(url).await?;
        Ok(res.json::<BrowseOptions>().await?)
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
