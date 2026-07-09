// Playlunky release fetching, version install/uninstall, and launch. UI
// concerns live in React; this module owns the file operations and the
// GitHub API glue.

use std::io::{Cursor, Write};
use std::path::PathBuf;
use std::time::{Duration, SystemTime};

use directories::BaseDirs;
use futures_util::StreamExt;
use ini::Ini;
use serde::{Deserialize, Serialize};

const RELEASES_URL: &str = "https://api.github.com/repos/spelunky-fyi/Playlunky/releases";
const CACHE_TTL: Duration = Duration::from_secs(30 * 60);
const USER_AGENT: &str = concat!("modlunky2/", env!("CARGO_PKG_VERSION"));

const SPEL2_DLL: &str = "spel2.dll";
const PLAYLUNKY_DLL: &str = "playlunky64.dll";
const PLAYLUNKY_EXE: &str = "playlunky_launcher.exe";
const VERSION_FILENAME: &str = "playlunky.version";
const PLAYLUNKY_FILES: &[&str] = &[SPEL2_DLL, PLAYLUNKY_DLL, PLAYLUNKY_EXE];

fn app_base() -> Option<PathBuf> {
    Some(
        BaseDirs::new()?
            .data_local_dir()
            .join("spelunky.fyi")
            .join("modlunky2"),
    )
}

/// Where a given Playlunky version's files live.
fn version_dir(tag: &str) -> Option<PathBuf> {
    Some(app_base()?.join("playlunky").join(tag))
}

fn cache_path() -> Option<PathBuf> {
    Some(app_base()?.join("Cache").join("playlunky-releases.json"))
}

/// Raw GitHub release entry, trimmed to what this module needs.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GhRelease {
    pub tag_name: String,
    #[serde(default)]
    pub prerelease: bool,
    #[serde(default)]
    pub assets: Vec<GhAsset>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GhAsset {
    pub browser_download_url: String,
}

/// Wire-facing release info. Also carries an `installed` flag so the modal
/// doesn't need a second command to figure out whether each tag is on disk.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PlaylunkyReleaseInfo {
    pub tag: String,
    pub prerelease: bool,
    pub download_url: Option<String>,
    pub installed: bool,
}

async fn fetch_releases_from_github() -> Result<Vec<GhRelease>, String> {
    let client = reqwest::Client::builder()
        .user_agent(USER_AGENT)
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let resp = client
        .get(RELEASES_URL)
        .send()
        .await
        .map_err(|e| format!("github request: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("github responded {}", resp.status()));
    }
    resp.json::<Vec<GhRelease>>()
        .await
        .map_err(|e| format!("decode github json: {e}"))
}

/// Returns cached releases if the cache file is fresh (younger than TTL),
/// otherwise fetches from GitHub and writes to cache. `force=true` bypasses
/// the TTL entirely so the "force refresh" button always hits the network.
/// Errors on network failure are non-fatal when any cache is available to
/// fall back on.
async fn load_releases(force: bool) -> Result<Vec<GhRelease>, String> {
    let cache = cache_path();
    if !force
        && let Some(path) = cache.as_ref()
        && let Ok(meta) = std::fs::metadata(path)
        && let Ok(mtime) = meta.modified()
        && let Ok(age) = SystemTime::now().duration_since(mtime)
        && age < CACHE_TTL
        && let Ok(bytes) = std::fs::read(path)
        && let Ok(v) = serde_json::from_slice::<Vec<GhRelease>>(&bytes)
    {
        return Ok(v);
    }

    match fetch_releases_from_github().await {
        Ok(releases) => {
            if let Some(path) = cache.as_ref() {
                if let Some(parent) = path.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                if let Ok(bytes) = serde_json::to_vec(&releases) {
                    let _ = std::fs::write(path, bytes);
                }
            }
            Ok(releases)
        }
        Err(fetch_err) => {
            // Best-effort fallback to any stale cache on disk.
            if let Some(path) = cache.as_ref()
                && let Ok(bytes) = std::fs::read(path)
                && let Ok(v) = serde_json::from_slice::<Vec<GhRelease>>(&bytes)
            {
                tracing::warn!("Using stale releases cache after fetch failure: {fetch_err}");
                return Ok(v);
            }
            Err(fetch_err)
        }
    }
}

/// The synthetic tag for the newest non-prerelease `vX.Y.Z` GitHub release.
/// Playlunky itself never publishes a tag named "stable"; this is a
/// modlunky2-side alias. Every code path that reads `playlunky-version`
/// from config has to run tags through `resolve_release` to turn "stable"
/// into the concrete release before hitting URLs or version markers.
pub const STABLE_TAG: &str = "stable";

/// UI-facing tag -> the GitHub release actually downloaded/compared
/// against. Identity for real tags (`nightly`, `nightly-backup`,
/// `vX.Y.Z`); dereferences the synthetic `stable` to the newest
/// non-prerelease.
fn resolve_release<'a>(releases: &'a [GhRelease], tag: &str) -> Option<&'a GhRelease> {
    if tag == STABLE_TAG {
        releases
            .iter()
            .find(|r| !r.prerelease && r.tag_name != STABLE_TAG)
    } else {
        releases.iter().find(|r| r.tag_name == tag)
    }
}

/// Refetch the Playlunky releases cache every CACHE_TTL, forever. Started
/// at boot and lives for the lifetime of the app so long-running sessions
/// see fresh releases without the user opening the version modal to
/// trigger a fetch. Errors are logged and swallowed; failing once doesn't
/// stop the loop from trying again in 30 min.
pub async fn background_release_refresh_loop() {
    loop {
        tokio::time::sleep(CACHE_TTL).await;
        if let Err(e) = load_releases(true).await {
            tracing::debug!("background Playlunky release refresh failed: {e}");
        }
    }
}

fn installed_tags() -> Vec<String> {
    let Some(base) = app_base() else {
        return Vec::new();
    };
    let dir = base.join("playlunky");
    let Ok(entries) = std::fs::read_dir(&dir) else {
        return Vec::new();
    };
    let mut tags = Vec::new();
    for entry in entries.flatten() {
        if entry.file_type().map(|t| t.is_dir()).unwrap_or(false)
            && let Some(name) = entry.file_name().to_str()
        {
            tags.push(name.to_string());
        }
    }
    tags.sort();
    tags
}

#[tauri::command]
pub fn list_installed_playlunky() -> Vec<String> {
    installed_tags()
}

#[tauri::command]
pub async fn list_playlunky_releases(
    force: Option<bool>,
) -> Result<Vec<PlaylunkyReleaseInfo>, String> {
    let releases = load_releases(force.unwrap_or(false)).await?;
    let installed: std::collections::HashSet<String> = installed_tags().into_iter().collect();

    let to_info = |r: &GhRelease, tag: String, installed_key: &str| PlaylunkyReleaseInfo {
        installed: installed.contains(installed_key),
        download_url: r.assets.first().map(|a| a.browser_download_url.clone()),
        tag,
        prerelease: r.prerelease,
    };

    let stable_release = resolve_release(&releases, STABLE_TAG).cloned();

    // Pin nightly + synthetic stable to the top of the list; drop
    // any real "stable" tag first so the synthetic wins if Playlunky
    // ever publishes one.
    let mut nightly = None;
    let mut rest: Vec<GhRelease> = Vec::with_capacity(releases.len());
    for r in releases {
        if r.tag_name.eq_ignore_ascii_case(STABLE_TAG) {
            continue;
        }
        if r.tag_name == "nightly" {
            nightly = Some(r);
        } else {
            rest.push(r);
        }
    }

    let mut out = Vec::with_capacity(rest.len() + 2);
    if let Some(r) = nightly.as_ref() {
        out.push(to_info(r, r.tag_name.clone(), &r.tag_name));
    }
    if let Some(r) = stable_release.as_ref() {
        out.push(to_info(r, STABLE_TAG.to_string(), STABLE_TAG));
    }
    for r in &rest {
        out.push(to_info(r, r.tag_name.clone(), &r.tag_name));
    }
    Ok(out)
}

/// Downloads and extracts a Playlunky release. Only the three files listed
/// in PLAYLUNKY_FILES are pulled out of the zip; readmes and other extras
/// are discarded. Writes playlunky.version alongside so nightly and stable
/// can detect a stale install and refresh.
#[tauri::command]
pub async fn download_playlunky_version(tag: String) -> Result<(), String> {
    let releases = load_releases(false).await?;
    let release = resolve_release(&releases, &tag)
        .cloned()
        .ok_or_else(|| format!("no release with tag {tag}"))?;
    let download_url = release
        .assets
        .into_iter()
        .next()
        .map(|a| a.browser_download_url)
        .ok_or_else(|| format!("release {tag} has no download asset"))?;

    let target = version_dir(&tag).ok_or_else(|| "no data directory".to_string())?;
    std::fs::create_dir_all(&target).map_err(|e| format!("mkdir: {e}"))?;

    let client = reqwest::Client::builder()
        .user_agent(USER_AGENT)
        .timeout(Duration::from_secs(600))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let resp = client
        .get(&download_url)
        .send()
        .await
        .map_err(|e| format!("download: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("download responded {}", resp.status()));
    }

    // Collect the zip into memory. Playlunky releases are ~5 MB so this is
    // fine; streaming to disk would only matter if this ever grew.
    let mut buf: Vec<u8> = Vec::new();
    let mut stream = resp.bytes_stream();
    while let Some(chunk) = stream.next().await {
        let bytes = chunk.map_err(|e| format!("read stream: {e}"))?;
        buf.extend_from_slice(&bytes);
    }

    let mut archive =
        zip::ZipArchive::new(Cursor::new(buf)).map_err(|e| format!("open zip: {e}"))?;
    for i in 0..archive.len() {
        let mut file = archive
            .by_index(i)
            .map_err(|e| format!("read entry {i}: {e}"))?;
        let Some(name) = file.enclosed_name() else {
            continue;
        };
        let file_name = name
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or_default();
        if !PLAYLUNKY_FILES.contains(&file_name) {
            continue;
        }
        let dest = target.join(file_name);
        let mut out =
            std::fs::File::create(&dest).map_err(|e| format!("write {}: {e}", dest.display()))?;
        std::io::copy(&mut file, &mut out).map_err(|e| format!("copy {}: {e}", dest.display()))?;
    }

    // Write a version marker: last '_' delimited segment of the download
    // URL stem.
    let version = parse_version_from_url(&download_url).unwrap_or_else(|| tag.clone());
    let mut vf = std::fs::File::create(target.join(VERSION_FILENAME))
        .map_err(|e| format!("write version: {e}"))?;
    vf.write_all(version.as_bytes())
        .map_err(|e| format!("write version: {e}"))?;

    Ok(())
}

fn parse_version_from_url(url: &str) -> Option<String> {
    let last = url.rsplit('/').next()?;
    let stem = last.strip_suffix(".zip").unwrap_or(last);
    let (_, tail) = stem.rsplit_once('_')?;
    Some(tail.to_string())
}

/// Removes an installed Playlunky version. Non-recursive: only the files
/// this app writes get deleted, plus the directory. Extra files a user
/// dropped in there are left alone.
#[tauri::command]
pub fn remove_playlunky_version(tag: String) -> Result<(), String> {
    let dir = version_dir(&tag).ok_or_else(|| "no data directory".to_string())?;
    if !dir.exists() {
        return Ok(());
    }
    for name in PLAYLUNKY_FILES {
        let _ = std::fs::remove_file(dir.join(name));
    }
    let _ = std::fs::remove_file(dir.join(VERSION_FILENAME));
    let _ = std::fs::remove_dir(&dir);
    Ok(())
}

fn launcher_exe_path(tag: &str) -> Option<PathBuf> {
    Some(version_dir(tag)?.join(PLAYLUNKY_EXE))
}

const STEAM_APP_ID: &str = "418530";
const STEAM_APPID_FILENAME: &str = "steam_appid.txt";

/// Prefix on `launch_playlunky` errors telling the frontend that the pinned
/// version's launcher exe isn't on disk. The frontend matches this prefix,
/// offers to redownload, then relaunches. Format: `<sentinel>:<tag>`.
const NOT_INSTALLED_SENTINEL: &str = "PLAYLUNKY_NOT_INSTALLED";

/// Rolling-release tags ("nightly" and the synthetic "stable") get an
/// auto-update check before launch: if the installed playlunky.version
/// doesn't match the current release's URL-derived version, redownload
/// before spawning. Failure to reach GitHub is not fatal, the on-disk
/// build launches anyway.
async fn refresh_rolling_release_if_stale(tag: &str) -> Result<(), String> {
    if tag != "nightly" && tag != STABLE_TAG {
        return Ok(());
    }
    let releases = match load_releases(false).await {
        Ok(r) => r,
        Err(_) => return Ok(()),
    };
    let Some(release) = resolve_release(&releases, tag) else {
        return Ok(());
    };
    let Some(url) = release
        .assets
        .first()
        .map(|a| a.browser_download_url.as_str())
    else {
        return Ok(());
    };
    let Some(latest_version) = parse_version_from_url(url) else {
        return Ok(());
    };

    let installed_version = version_dir(tag)
        .map(|d| d.join(VERSION_FILENAME))
        .and_then(|p| std::fs::read_to_string(&p).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_default();

    if installed_version == latest_version {
        return Ok(());
    }

    tracing::info!("Refreshing Playlunky {tag} from {installed_version} to {latest_version}");
    download_playlunky_version(tag.to_string()).await
}

/// Launches Playlunky for the currently selected version. For nightly and
/// synthetic stable, check for a newer build and download it before
/// proceeding; write steam_appid.txt to the install directory; spawn
/// playlunky_launcher.exe with --exe_dir pointing at the install dir, cwd
/// set to the version's data dir. Fire and forget on the subprocess side so
/// the app stays responsive.
///
/// load_order.txt is already kept up to date by set_load_order which the
/// Mods page calls on every activate, deactivate, and drag reorder, and
/// playlunky.ini is written by the Options modal, so this command only
/// handles the launch itself.
#[tauri::command]
pub async fn launch_playlunky() -> Result<(), String> {
    let cfg = crate::config::load();
    let install_dir = cfg
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    if !install_dir.exists() {
        return Err(format!(
            "install directory does not exist: {}",
            install_dir.display()
        ));
    }

    let tag = cfg
        .playlunky_version
        .filter(|t| !t.trim().is_empty())
        .ok_or_else(|| "no Playlunky version selected".to_string())?;

    // Auto-update rolling releases (nightly) before spawn.
    refresh_rolling_release_if_stale(&tag).await?;

    let launcher =
        launcher_exe_path(&tag).ok_or_else(|| "no data directory for Playlunky".to_string())?;
    if !launcher.exists() {
        // Sentinel the frontend catches to offer a one-click reinstall
        // (common cause: antivirus quarantines playlunky_launcher.exe
        // after it's dropped on disk).
        return Err(format!("{NOT_INSTALLED_SENTINEL}:{tag}"));
    }

    // Write steam_appid.txt every launch. Playlunky uses this to attach
    // to the running Steam client.
    let appid_path = install_dir.join(STEAM_APPID_FILENAME);
    std::fs::write(&appid_path, STEAM_APP_ID).map_err(|e| format!("write steam_appid.txt: {e}"))?;

    let cwd = launcher
        .parent()
        .ok_or_else(|| "playlunky launcher has no parent dir".to_string())?;
    let exe_dir_arg = format!("--exe_dir={}", install_dir.display());

    // Assemble args after the launcher path. --exe_dir first, then flags
    // for --console and --overlunky when the user has them on.
    let mut launcher_args: Vec<String> = vec![exe_dir_arg];
    if cfg.playlunky_console {
        launcher_args.push("--console".to_string());
    }
    if cfg.playlunky_overlunky {
        launcher_args.push("--overlunky".to_string());
    }

    // command_prefix wraps the whole invocation. First token becomes the
    // executable and the rest become leading args, so a prefix of "wine"
    // produces `wine playlunky_launcher.exe --exe_dir=...`.
    let prefix_tokens: Vec<String> = cfg
        .command_prefix
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .and_then(|s| shell_words::split(s).ok())
        .unwrap_or_default();

    let spawn_result = if let Some((head, tail)) = prefix_tokens.split_first() {
        std::process::Command::new(head)
            .args(tail)
            .arg(&launcher)
            .args(&launcher_args)
            .current_dir(cwd)
            .spawn()
    } else {
        std::process::Command::new(&launcher)
            .args(&launcher_args)
            .current_dir(cwd)
            .spawn()
    };
    spawn_result.map_err(|e| format!("spawn playlunky_launcher.exe: {e}"))?;

    Ok(())
}

// ── Desktop shortcut ─────────────────────────────────────────────────────

const SHORTCUT_FILENAME: &str = "Playlunky.lnk";

fn desktop_shortcut_path() -> Option<PathBuf> {
    Some(
        BaseDirs::new()?
            .home_dir()
            .join("Desktop")
            .join(SHORTCUT_FILENAME),
    )
}

/// Reconciles the desktop shortcut with the current config. When
/// playlunky_shortcut is true and enough is configured to actually launch,
/// writes (or overwrites) `Playlunky.lnk` on the user's Desktop pointing
/// directly at playlunky_launcher.exe with only `--exe_dir=<install>`.
/// Console/overlunky flags are read live from config at launch time (via
/// launch_playlunky), NOT baked into the shortcut, so toggling those
/// doesn't require re-syncing the shortcut. Fire-and-forget from the
/// frontend; missing prerequisites are silently ignored so the modal
/// Save flow doesn't error over a not-quite-configured state.
#[tauri::command]
pub fn sync_desktop_shortcut() -> Result<(), String> {
    let cfg = crate::config::load();
    let Some(path) = desktop_shortcut_path() else {
        return Ok(());
    };

    if !cfg.playlunky_shortcut {
        if path.exists() {
            let _ = std::fs::remove_file(&path);
        }
        return Ok(());
    }

    let Some(install_dir) = cfg.install_dir.filter(|p| p.exists()) else {
        return Ok(());
    };
    let Some(tag) = cfg
        .playlunky_version
        .as_deref()
        .filter(|t| !t.trim().is_empty())
    else {
        return Ok(());
    };
    let Some(launcher) = launcher_exe_path(tag) else {
        return Ok(());
    };
    if !launcher.exists() {
        return Ok(());
    }

    let args = [format!("--exe_dir={}", install_dir.display())];

    let launcher_str = launcher
        .to_str()
        .ok_or_else(|| "launcher path is not valid unicode".to_string())?;
    let mut lnk =
        mslnk::ShellLink::new(launcher_str).map_err(|e| format!("create shortcut: {e}"))?;
    lnk.set_arguments(Some(args.join(" ")));
    if let Some(cwd) = launcher.parent().and_then(|p| p.to_str()) {
        lnk.set_working_dir(Some(cwd.to_string()));
    }

    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let path_str = path
        .to_str()
        .ok_or_else(|| "shortcut path is not valid unicode".to_string())?;
    lnk.create_lnk(path_str)
        .map_err(|e| format!("write shortcut: {e}"))?;
    Ok(())
}

// ── Playlunky options / playlunky.ini ───────────────────────────────────

const INI_FILENAME: &str = "playlunky.ini";
const SEC_GENERAL: &str = "general_settings";
const SEC_SCRIPT: &str = "script_settings";
const SEC_AUDIO: &str = "audio_settings";
const SEC_SPRITE: &str = "sprite_settings";
// Older Playlunky stored every option under a single flat [settings]
// section. On read, values there back-fill any key missing from the
// modern per-domain section; on write, known keys get swept out of it
// so migrated files converge on the modern layout.
const SEC_LEGACY: &str = "settings";

/// Every key this module owns across the four modern sections. Used on
/// save to evict duplicates from the legacy [settings] section so it
/// either disappears or ends up holding only foreign keys.
const OWNED_KEYS: &[&str] = &[
    "enable_loose_file_warning",
    "disable_asset_caching",
    "speedrun_mode",
    "block_save_game",
    "allow_save_game_mods",
    "disable_steam_achievements",
    "use_playlunky_save",
    "enable_developer_mode",
    "enable_developer_console",
    "console_history_size",
    "enable_loose_audio_files",
    "cache_decoded_audio_files",
    "synchronous_update",
    "random_character_select",
    "link_related_files",
    "generate_character_journal_stickers",
    "generate_character_journal_entries",
    "generate_sticker_pixel_art",
    "enable_sprite_hot_loading",
    "sprite_hot_load_delay",
    "enable_customizable_sheets",
    "enable_luminance_scaling",
];

/// Options exposed by the Playlunky Options modal. Defaults match
/// Playlunky's own defaults so the written file ends up identical to
/// what the user would get from a fresh Playlunky install after a save.
/// camelCase over the wire; snake_case in Rust.
#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PlaylunkyOptions {
    pub general: GeneralSettings,
    pub script: ScriptSettings,
    pub audio: AudioSettings,
    pub sprite: SpriteSettings,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GeneralSettings {
    pub enable_loose_file_warning: bool,
    pub disable_asset_caching: bool,
    pub speedrun_mode: bool,
    pub block_save_game: bool,
    pub allow_save_game_mods: bool,
    pub disable_steam_achievements: bool,
    pub use_playlunky_save: bool,
}

impl Default for GeneralSettings {
    fn default() -> Self {
        Self {
            enable_loose_file_warning: true,
            disable_asset_caching: false,
            speedrun_mode: false,
            block_save_game: false,
            allow_save_game_mods: true,
            disable_steam_achievements: false,
            use_playlunky_save: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ScriptSettings {
    pub enable_developer_mode: bool,
    pub enable_developer_console: bool,
    pub console_history_size: u32,
}

impl Default for ScriptSettings {
    fn default() -> Self {
        Self {
            enable_developer_mode: false,
            enable_developer_console: false,
            console_history_size: 20,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AudioSettings {
    pub enable_loose_audio_files: bool,
    pub cache_decoded_audio_files: bool,
    pub synchronous_update: bool,
}

impl Default for AudioSettings {
    fn default() -> Self {
        Self {
            enable_loose_audio_files: true,
            cache_decoded_audio_files: false,
            synchronous_update: true,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SpriteSettings {
    pub random_character_select: bool,
    pub link_related_files: bool,
    pub generate_character_journal_stickers: bool,
    pub generate_character_journal_entries: bool,
    pub generate_sticker_pixel_art: bool,
    pub enable_sprite_hot_loading: bool,
    pub sprite_hot_load_delay: u32,
    pub enable_customizable_sheets: bool,
    pub enable_luminance_scaling: bool,
}

impl Default for SpriteSettings {
    fn default() -> Self {
        Self {
            random_character_select: false,
            link_related_files: true,
            generate_character_journal_stickers: true,
            generate_character_journal_entries: true,
            generate_sticker_pixel_art: true,
            enable_sprite_hot_loading: false,
            sprite_hot_load_delay: 400,
            enable_customizable_sheets: true,
            enable_luminance_scaling: true,
        }
    }
}

fn playlunky_ini_path() -> Result<PathBuf, String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    Ok(install_dir.join(INI_FILENAME))
}

fn load_playlunky_ini() -> Result<Ini, String> {
    let path = playlunky_ini_path()?;
    if !path.exists() {
        return Ok(Ini::new());
    }
    Ini::load_from_file(&path).map_err(|e| format!("read {INI_FILENAME}: {e}"))
}

/// Fetches a raw value, falling back to the legacy [settings] section
/// when the key is missing from its modern section. This makes get flows
/// transparent for users whose ini pre-dates Playlunky's section reorg.
fn get_value_with_legacy<'a>(ini: &'a Ini, section: &str, key: &str) -> Option<&'a str> {
    ini.get_from(Some(section), key)
        .or_else(|| ini.get_from(Some(SEC_LEGACY), key))
}

fn read_bool(ini: &Ini, section: &str, key: &str, default: bool) -> bool {
    get_value_with_legacy(ini, section, key)
        .map(|v| v.trim().eq_ignore_ascii_case("true"))
        .unwrap_or(default)
}

fn read_u32(ini: &Ini, section: &str, key: &str, default: u32) -> u32 {
    get_value_with_legacy(ini, section, key)
        .and_then(|v| v.trim().parse::<u32>().ok())
        .unwrap_or(default)
}

fn write_bool(ini: &mut Ini, section: &str, key: &str, value: bool) {
    ini.with_section(Some(section))
        .set(key, if value { "true" } else { "false" });
}

fn write_u32(ini: &mut Ini, section: &str, key: &str, value: u32) {
    ini.with_section(Some(section)).set(key, value.to_string());
}

#[tauri::command]
pub fn get_playlunky_options() -> Result<PlaylunkyOptions, String> {
    let ini = load_playlunky_ini()?;
    Ok(options_from_ini(&ini))
}

/// Pure `Ini -> PlaylunkyOptions` conversion. Section reads fall
/// through `get_value_with_legacy`, so pre-migration files that stored
/// everything under `[settings]` still yield the right values. Missing
/// keys resolve to Playlunky's own defaults.
pub(crate) fn options_from_ini(ini: &Ini) -> PlaylunkyOptions {
    let defaults = PlaylunkyOptions::default();
    PlaylunkyOptions {
        general: GeneralSettings {
            enable_loose_file_warning: read_bool(
                ini,
                SEC_GENERAL,
                "enable_loose_file_warning",
                defaults.general.enable_loose_file_warning,
            ),
            disable_asset_caching: read_bool(
                ini,
                SEC_GENERAL,
                "disable_asset_caching",
                defaults.general.disable_asset_caching,
            ),
            speedrun_mode: read_bool(
                ini,
                SEC_GENERAL,
                "speedrun_mode",
                defaults.general.speedrun_mode,
            ),
            block_save_game: read_bool(
                ini,
                SEC_GENERAL,
                "block_save_game",
                defaults.general.block_save_game,
            ),
            allow_save_game_mods: read_bool(
                ini,
                SEC_GENERAL,
                "allow_save_game_mods",
                defaults.general.allow_save_game_mods,
            ),
            disable_steam_achievements: read_bool(
                ini,
                SEC_GENERAL,
                "disable_steam_achievements",
                defaults.general.disable_steam_achievements,
            ),
            use_playlunky_save: read_bool(
                ini,
                SEC_GENERAL,
                "use_playlunky_save",
                defaults.general.use_playlunky_save,
            ),
        },
        script: ScriptSettings {
            enable_developer_mode: read_bool(
                ini,
                SEC_SCRIPT,
                "enable_developer_mode",
                defaults.script.enable_developer_mode,
            ),
            enable_developer_console: read_bool(
                ini,
                SEC_SCRIPT,
                "enable_developer_console",
                defaults.script.enable_developer_console,
            ),
            console_history_size: read_u32(
                ini,
                SEC_SCRIPT,
                "console_history_size",
                defaults.script.console_history_size,
            ),
        },
        audio: AudioSettings {
            enable_loose_audio_files: read_bool(
                ini,
                SEC_AUDIO,
                "enable_loose_audio_files",
                defaults.audio.enable_loose_audio_files,
            ),
            cache_decoded_audio_files: read_bool(
                ini,
                SEC_AUDIO,
                "cache_decoded_audio_files",
                defaults.audio.cache_decoded_audio_files,
            ),
            synchronous_update: read_bool(
                ini,
                SEC_AUDIO,
                "synchronous_update",
                defaults.audio.synchronous_update,
            ),
        },
        sprite: SpriteSettings {
            random_character_select: read_bool(
                ini,
                SEC_SPRITE,
                "random_character_select",
                defaults.sprite.random_character_select,
            ),
            link_related_files: read_bool(
                ini,
                SEC_SPRITE,
                "link_related_files",
                defaults.sprite.link_related_files,
            ),
            generate_character_journal_stickers: read_bool(
                ini,
                SEC_SPRITE,
                "generate_character_journal_stickers",
                defaults.sprite.generate_character_journal_stickers,
            ),
            generate_character_journal_entries: read_bool(
                ini,
                SEC_SPRITE,
                "generate_character_journal_entries",
                defaults.sprite.generate_character_journal_entries,
            ),
            generate_sticker_pixel_art: read_bool(
                ini,
                SEC_SPRITE,
                "generate_sticker_pixel_art",
                defaults.sprite.generate_sticker_pixel_art,
            ),
            enable_sprite_hot_loading: read_bool(
                ini,
                SEC_SPRITE,
                "enable_sprite_hot_loading",
                defaults.sprite.enable_sprite_hot_loading,
            ),
            sprite_hot_load_delay: read_u32(
                ini,
                SEC_SPRITE,
                "sprite_hot_load_delay",
                defaults.sprite.sprite_hot_load_delay,
            ),
            enable_customizable_sheets: read_bool(
                ini,
                SEC_SPRITE,
                "enable_customizable_sheets",
                defaults.sprite.enable_customizable_sheets,
            ),
            enable_luminance_scaling: read_bool(
                ini,
                SEC_SPRITE,
                "enable_luminance_scaling",
                defaults.sprite.enable_luminance_scaling,
            ),
        },
    }
}

#[tauri::command]
pub fn set_playlunky_options(options: PlaylunkyOptions) -> Result<(), String> {
    // Load first so any unknown sections or keys already in the file survive
    // the round trip.
    let mut ini = load_playlunky_ini()?;
    apply_options_to_ini(&mut ini, &options);
    let path = playlunky_ini_path()?;
    // Playlunky's ini parser accepts key=value without spaces around the
    // delimiter, which is rust-ini's default writer output.
    ini.write_to_file(&path)
        .map_err(|e| format!("write {INI_FILENAME}: {e}"))?;
    Ok(())
}

/// Pure `PlaylunkyOptions -> Ini` write. Populates the four modern
/// sections then evicts owned keys from the legacy `[settings]` block,
/// dropping the block entirely when empty. Preserves any unknown
/// sections or keys the caller had already loaded into `ini` (that's
/// how per-user tweaks Playlunky adds survive the round trip).
pub(crate) fn apply_options_to_ini(ini: &mut Ini, options: &PlaylunkyOptions) {
    write_bool(
        ini,
        SEC_GENERAL,
        "enable_loose_file_warning",
        options.general.enable_loose_file_warning,
    );
    write_bool(
        ini,
        SEC_GENERAL,
        "disable_asset_caching",
        options.general.disable_asset_caching,
    );
    write_bool(
        ini,
        SEC_GENERAL,
        "speedrun_mode",
        options.general.speedrun_mode,
    );
    write_bool(
        ini,
        SEC_GENERAL,
        "block_save_game",
        options.general.block_save_game,
    );
    write_bool(
        ini,
        SEC_GENERAL,
        "allow_save_game_mods",
        options.general.allow_save_game_mods,
    );
    write_bool(
        ini,
        SEC_GENERAL,
        "disable_steam_achievements",
        options.general.disable_steam_achievements,
    );
    write_bool(
        ini,
        SEC_GENERAL,
        "use_playlunky_save",
        options.general.use_playlunky_save,
    );

    write_bool(
        ini,
        SEC_SCRIPT,
        "enable_developer_mode",
        options.script.enable_developer_mode,
    );
    write_bool(
        ini,
        SEC_SCRIPT,
        "enable_developer_console",
        options.script.enable_developer_console,
    );
    write_u32(
        ini,
        SEC_SCRIPT,
        "console_history_size",
        options.script.console_history_size,
    );

    write_bool(
        ini,
        SEC_AUDIO,
        "enable_loose_audio_files",
        options.audio.enable_loose_audio_files,
    );
    write_bool(
        ini,
        SEC_AUDIO,
        "cache_decoded_audio_files",
        options.audio.cache_decoded_audio_files,
    );
    write_bool(
        ini,
        SEC_AUDIO,
        "synchronous_update",
        options.audio.synchronous_update,
    );

    write_bool(
        ini,
        SEC_SPRITE,
        "random_character_select",
        options.sprite.random_character_select,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "link_related_files",
        options.sprite.link_related_files,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "generate_character_journal_stickers",
        options.sprite.generate_character_journal_stickers,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "generate_character_journal_entries",
        options.sprite.generate_character_journal_entries,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "generate_sticker_pixel_art",
        options.sprite.generate_sticker_pixel_art,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "enable_sprite_hot_loading",
        options.sprite.enable_sprite_hot_loading,
    );
    write_u32(
        ini,
        SEC_SPRITE,
        "sprite_hot_load_delay",
        options.sprite.sprite_hot_load_delay,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "enable_customizable_sheets",
        options.sprite.enable_customizable_sheets,
    );
    write_bool(
        ini,
        SEC_SPRITE,
        "enable_luminance_scaling",
        options.sprite.enable_luminance_scaling,
    );

    // Legacy [settings] migration: sweep any owned keys out of the
    // flat section so duplicates can't drift apart. Drop the whole
    // section if it's now empty.
    for key in OWNED_KEYS {
        ini.delete_from(Some(SEC_LEGACY), key);
    }
    let legacy_empty = ini
        .section(Some(SEC_LEGACY))
        .map(|s| s.is_empty())
        .unwrap_or(true);
    if legacy_empty {
        ini.delete(Some(SEC_LEGACY));
    }
}

#[cfg(test)]
mod tests {
    // Semantic-outcome tests for the ini round-trip: legacy `[settings]`
    // migration to the modern per-domain sections, unknown-key
    // preservation, and empty-section drop. Inline-comment stripping is
    // out of scope: `rust-ini` keeps `key=false  # comment` as the
    // literal value unless the `inline-comment` feature is enabled.
    use super::{
        PlaylunkyOptions, SEC_AUDIO, SEC_GENERAL, SEC_LEGACY, SEC_SPRITE, apply_options_to_ini,
        options_from_ini,
    };
    use ini::Ini;

    fn parse(input: &str) -> Ini {
        Ini::load_from_str(input).expect("valid ini")
    }

    // Empty ini yields default option values.
    #[test]
    fn playlunky_ini_empty_uses_defaults() {
        let ini = Ini::new();
        let opts = options_from_ini(&ini);
        let d = PlaylunkyOptions::default();
        assert_eq!(
            opts.sprite.random_character_select,
            d.sprite.random_character_select
        );
        assert!(opts.audio.enable_loose_audio_files);
        assert!(!opts.audio.cache_decoded_audio_files);
    }

    // Values under the legacy `[settings]` section must feed the
    // modern-section fields via `get_value_with_legacy`.
    #[test]
    fn playlunky_ini_legacy_settings_flow_into_modern_sections() {
        let ini = parse(
            "\
[settings]
random_character_select=false
enable_loose_audio_files=true
cache_decoded_audio_files=false
enable_developer_mode=false
",
        );
        let opts = options_from_ini(&ini);
        assert!(!opts.sprite.random_character_select);
        assert!(opts.audio.enable_loose_audio_files);
        assert!(!opts.audio.cache_decoded_audio_files);
        assert!(!opts.script.enable_developer_mode);
    }

    // One key set; every other field falls through to Playlunky's
    // default.
    #[test]
    fn playlunky_ini_partial_config_falls_through_to_defaults() {
        let ini = parse(
            "\
[settings]
random_character_select=false
",
        );
        let opts = options_from_ini(&ini);
        assert!(!opts.sprite.random_character_select);
        // Default enable_loose_audio_files is true; defaulted.
        assert!(opts.audio.enable_loose_audio_files);
        // Default cache_decoded_audio_files is false; defaulted.
        assert!(!opts.audio.cache_decoded_audio_files);
    }

    // Write, re-parse, options must compare equal.
    #[test]
    fn playlunky_ini_round_trip_preserves_options() {
        let mut src = PlaylunkyOptions::default();
        src.sprite.random_character_select = true;
        let mut ini = Ini::new();
        apply_options_to_ini(&mut ini, &src);

        let mut serialized = Vec::new();
        ini.write_to(&mut serialized).unwrap();
        let text = String::from_utf8(serialized).unwrap();

        let round_trip = options_from_ini(&parse(&text));
        assert_eq!(round_trip, src);
    }

    // Legacy `[settings]` contains only owned keys -> after apply,
    // section is gone entirely.
    #[test]
    fn playlunky_ini_legacy_settings_disappears_when_all_owned() {
        let mut ini = parse(
            "\
[settings]
random_character_select=false
enable_loose_audio_files=true
cache_decoded_audio_files=false
enable_developer_mode=false

[script_settings]
enable_developer_console=true
console_history_size=50
",
        );
        let mut opts = options_from_ini(&ini);
        opts.sprite.random_character_select = true;
        apply_options_to_ini(&mut ini, &opts);
        assert!(
            ini.section(Some(SEC_LEGACY)).is_none(),
            "legacy [settings] should be dropped"
        );
        // Modern sections all present with the applied values.
        assert_eq!(
            ini.get_from(Some(SEC_SPRITE), "random_character_select"),
            Some("true")
        );
        assert_eq!(
            ini.get_from(Some(SEC_AUDIO), "enable_loose_audio_files"),
            Some("true")
        );
    }

    // Same migration but `some_unknown_field` survives inside
    // `[settings]`.
    #[test]
    fn playlunky_ini_legacy_settings_kept_when_unknown_key_present() {
        let mut ini = parse(
            "\
[settings]
random_character_select=false
enable_loose_audio_files=true
some_unknown_field=ABACAB00
cache_decoded_audio_files=false
enable_developer_mode=false

[script_settings]
enable_developer_console=true
console_history_size=50
",
        );
        let mut opts = options_from_ini(&ini);
        opts.sprite.random_character_select = true;
        apply_options_to_ini(&mut ini, &opts);
        assert_eq!(
            ini.get_from(Some(SEC_LEGACY), "some_unknown_field"),
            Some("ABACAB00"),
            "unknown key must survive the migration"
        );
        // Owned keys must have been swept out.
        assert_eq!(
            ini.get_from(Some(SEC_LEGACY), "random_character_select"),
            None
        );
        assert_eq!(
            ini.get_from(Some(SEC_LEGACY), "enable_loose_audio_files"),
            None
        );
        // And re-parented onto the modern sections.
        assert_eq!(
            ini.get_from(Some(SEC_SPRITE), "random_character_select"),
            Some("true")
        );
        assert_eq!(
            ini.get_from(Some(SEC_GENERAL), "enable_loose_file_warning"),
            Some("true")
        );
    }
}
