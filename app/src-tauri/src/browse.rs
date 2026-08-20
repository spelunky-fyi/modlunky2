//! Reading the spelunky.fyi mod directory.
//!
//! Deliberately not routed through `ModManagerHandle`. That manager is a
//! single-task actor behind a depth-one channel, so a browse request sent to it
//! would sit behind whatever install is currently downloading a 90MB pack.
//! Browsing is a read-through to the API with no local state, so it skips the
//! actor and talks to `HttpApiMods` directly, the same way `check_fyi_updates`
//! already does.
//!
//! The client is built per call from current config, so a token pasted or
//! linked a moment ago works without a restart. The underlying
//! `reqwest::Client` is shared and cheap to clone, which keeps the connection
//! pool alive across the many small requests that scrolling a grid produces.

use std::sync::OnceLock;

use ml2_mods::spelunkyfyi::http::{
    BrowseOptions, BrowseQuery, GAME_SPELUNKY_2, INCLUDE_PREVIEW_IMAGES, ModListing, Page,
};
use serde::Deserialize;

use crate::state::AppState;

/// Shared so that paging and filtering reuse connections instead of paying a
/// TLS handshake per keystroke. `reqwest::Client` is internally reference
/// counted, so cloning it is just a refcount bump.
static CLIENT: OnceLock<reqwest::Client> = OnceLock::new();

fn client() -> reqwest::Client {
    CLIENT.get_or_init(reqwest::Client::new).clone()
}

/// Why a browse call failed, in a shape the UI can act on.
///
/// A tagged enum rather than a string because two of these have a fix the user
/// can be handed a button for, and telling them apart by matching on message
/// text is the kind of thing that breaks the next time someone rewords one.
#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "camelCase", tag = "kind", content = "message")]
pub enum BrowseError {
    /// No token configured at all.
    NeedsAccount(String),
    /// A token is configured, and the site refused it. Usually a token that was
    /// reset on the website, which the app has no way to find out about until
    /// it tries to use one.
    Unauthorized(String),
    Failed(String),
}

impl BrowseError {
    fn from_api(err: ml2_mods::spelunkyfyi::Error, context: &str) -> Self {
        if err.is_auth_failure() {
            return BrowseError::Unauthorized(AUTH_FAILED.to_string());
        }
        BrowseError::Failed(format!("{context}: {err}"))
    }
}

const NEEDS_TOKEN: &str = "Connect your spelunky.fyi account in Settings to browse mods.";

/// Deliberately does not guess which of the several causes applies. The site
/// answers 401 for a token that was reset, revoked, never valid, or belongs to
/// a deleted account, and it is the same fix in every case.
const AUTH_FAILED: &str = "spelunky.fyi rejected your account. Your token may have been reset.";

/// What the frontend sends. Mirrors `BrowseQuery` minus `game`, which Modlunky
/// never varies: it is a Spelunky 2 tool, so the filter is pinned rather than
/// exposed as a control nobody would touch.
#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct BrowseArgs {
    pub q: Option<String>,
    pub mod_type: Option<i32>,
    pub favorite: Option<bool>,
    pub rated: Option<String>,
    pub order_by: Option<String>,
    pub limit: Option<u32>,
    pub offset: Option<u32>,
}

impl BrowseArgs {
    fn into_query(self) -> BrowseQuery {
        BrowseQuery {
            q: self.q,
            game: Some(GAME_SPELUNKY_2),
            mod_type: self.mod_type,
            favorite: self.favorite,
            rated: self.rated,
            order_by: self.order_by,
            limit: self.limit,
            offset: self.offset,
            // Always asked for. The detail pane renders screenshots
            // straight from the listing, so selecting a mod costs no second
            // request; drop this and it has nothing to show.
            include: vec![INCLUDE_PREVIEW_IMAGES.to_string()],
        }
    }
}

fn api_client() -> Result<ml2_mods::spelunkyfyi::http::HttpApiMods, BrowseError> {
    let cfg = crate::config::load();
    crate::mods::build_api_client_with(
        cfg.spelunky_fyi_api_token.as_deref(),
        cfg.spelunky_fyi_root.as_deref(),
        client(),
    )
    .ok_or_else(|| BrowseError::NeedsAccount(NEEDS_TOKEN.to_string()))
}

#[tauri::command]
pub async fn browse_mods(args: BrowseArgs) -> Result<Page<ModListing>, BrowseError> {
    let api = api_client()?;
    api.list_mods(&args.into_query())
        .await
        .map_err(|e| BrowseError::from_api(e, "Couldn't load mods"))
}

#[tauri::command]
pub async fn browse_mod_options() -> Result<BrowseOptions, BrowseError> {
    let api = api_client()?;
    api.browse_options(Some(GAME_SPELUNKY_2))
        .await
        .map_err(|e| BrowseError::from_api(e, "Couldn't load browse filters"))
}

/// Ask the site whether the configured token actually works.
///
/// Exists because there is no other way to find out until something fails. A
/// token can be reset on the website at any time and nothing tells the app, so
/// "my install broke" is otherwise the first symptom. `browse-options` is the
/// cheapest authenticated endpoint: a handful of enum labels, no database rows.
#[tauri::command]
pub async fn verify_fyi_account() -> Result<(), BrowseError> {
    let api = api_client()?;
    api.browse_options(Some(GAME_SPELUNKY_2))
        .await
        .map(|_| ())
        .map_err(|e| BrowseError::from_api(e, "Couldn't reach spelunky.fyi"))
}

/// A locally installed mod, keyed the way a browse card can match it.
#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct InstalledFyiMod {
    pub slug: String,
    pub has_update: bool,
}

/// Which spelunky.fyi mods are already installed here, and which of those have
/// a newer file waiting.
///
/// This is the whole reason a browse tab beats the website: the site cannot
/// know what is on your disk. Answered from the local mod list and the update
/// set the mod cache maintains, so it costs no API call.
#[tauri::command]
pub async fn installed_fyi_mods(
    state: tauri::State<'_, AppState>,
) -> Result<Vec<InstalledFyiMod>, String> {
    let Some(handle) = state.mods_handle() else {
        // No install directory configured yet. Nothing is installed, which is
        // a true answer rather than an error the browse grid has to handle.
        return Ok(Vec::new());
    };
    let mods = handle.list().await.map_err(|e| e.to_string())?;

    // Cloned rather than held: the lock must not be alive across the await
    // above or any future one, and the set is small.
    let updates = state.updates_available().lock().unwrap().clone();

    let mut installed: Vec<InstalledFyiMod> = mods
        .into_iter()
        .filter_map(|m| {
            let manifest = m.manifest?;
            let slug = manifest.slug.trim().to_string();
            if slug.is_empty() {
                // A side-loaded local pack, with no directory entry to match.
                return None;
            }
            Some(InstalledFyiMod {
                slug,
                has_update: updates.contains(&m.id),
            })
        })
        .collect();
    installed.sort_by(|a, b| a.slug.cmp(&b.slug));
    installed.dedup_by(|a, b| a.slug == b.slug);
    Ok(installed)
}
