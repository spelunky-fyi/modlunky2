// Owns the ModManager subsystem tree (local disk cache + manager) and the
// Tauri commands exposed to the frontend for mod management. Wired up in
// `lib.rs::run`, kept in a dedicated module so the surface stays discoverable
// as install, pack, extract, etc. commands land.

use std::collections::HashSet;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use base64::{Engine as _, engine::general_purpose::STANDARD as B64};
use ml2_mods::{
    data::{Change, ManagerError, Manifest, Mod, ModProgress},
    local::{LocalMods, cache::ModCache, disk::DiskMods},
    manager::{DEFAULT_RECEIVING_INTERVAL, ModManager, ModManagerHandle, ModSource},
    spelunkyfyi::http::{DEFAULT_SERVICE_ROOT, HttpApiMods, RemoteMods},
};
use serde::Serialize;
use tauri::{AppHandle, Emitter, Runtime};
use tauri_plugin_opener::OpenerExt;
use tokio::sync::broadcast;
use tokio_graceful_shutdown::{IntoSubsystem, SubsystemBuilder, SubsystemHandle, Toplevel};

use crate::state::AppState;

const MODS_CHANGED_EVENT: &str = "mods-changed";

/// Tells the frontend its mod list is stale so it refetches.
///
/// Exposed because the Mods page renders more than what `ml2_mods` tracks:
/// per-install state like usage history changes from outside that crate
/// entirely (see `launch`), and without a nudge the page keeps showing
/// whatever it fetched last.
pub fn emit_mods_changed<R: Runtime>(app: &AppHandle<R>) {
    let _ = app.emit(MODS_CHANGED_EVENT, ());
}
const FYI_ID_PREFIX: &str = "fyi.";

/// Ceiling on how long `list_mods` blocks waiting for ModCache's first disk
/// scan. Only a pathological install dir (dead network share) should get
/// anywhere near it; the timeout exists so such a case degrades to an empty
/// list the user can Refresh out of, rather than a spinner that never ends.
const CACHE_READY_TIMEOUT: Duration = Duration::from_secs(15);

pub struct ModsSetup {
    pub handle: ModManagerHandle,
    pub cache_handle: ml2_mods::local::cache::ModCacheHandle,
    pub task: tauri::async_runtime::JoinHandle<()>,
}

pub struct SetupOpts {
    pub install_dir: PathBuf,
    pub api_token: Option<String>,
    pub service_root: Option<String>,
}

/// Constructs the spelunky.fyi HTTP client if the user has an API token in
/// Settings. Falls back to DEFAULT_SERVICE_ROOT when the config field is
/// empty. Returns None when there's no token (local-only mode) so remote
/// features silently no-op.
fn build_api_client(api_token: Option<&str>, service_root: Option<&str>) -> Option<HttpApiMods> {
    build_api_client_with(api_token, service_root, reqwest::Client::new())
}

/// As `build_api_client`, but reusing a caller-supplied HTTP client. The browse
/// grid issues many small requests as the user types and pages, so it keeps one
/// client alive rather than discarding a connection pool per call.
pub(crate) fn build_api_client_with(
    api_token: Option<&str>,
    service_root: Option<&str>,
    http: reqwest::Client,
) -> Option<HttpApiMods> {
    let token = api_token?;
    if token.trim().is_empty() {
        return None;
    }
    let root = service_root
        .map(|r| r.trim())
        .filter(|r| !r.is_empty())
        .unwrap_or(DEFAULT_SERVICE_ROOT);
    match HttpApiMods::new(root, token, http) {
        Ok(client) => Some(client),
        Err(e) => {
            tracing::warn!("Failed to build spelunky.fyi API client for root {root}: {e}");
            None
        }
    }
}

/// Constructs and spawns the ModManager subsystem tree for the given install
/// directory. When an API token is present in Settings, HttpApiMods is wired
/// into ModCache and ModManager so remote install, update, and NewVersion
/// polling all work. Without a token, everything runs in local-only mode and
/// remote calls surface an "API isn't configured" error.
///
/// Returns a task JoinHandle whose lifetime governs the subsystem tree.
/// Aborting the task drops the subsystem futures (which drops the ModManager,
/// closes changes_tx, and terminates the sibling change listener that lives
/// alongside it inside the same spawned future). This is what makes hot
/// reload possible: rebuild_mods aborts the old task and installs a fresh
/// one built from the current config.
pub fn setup<R: Runtime>(
    opts: SetupOpts,
    updates_available: Arc<Mutex<HashSet<String>>>,
    app: AppHandle<R>,
) -> ModsSetup {
    let install_path = opts.install_dir.to_string_lossy().into_owned();
    let (detected_tx, detected_rx) = broadcast::channel(10);
    let api_client = build_api_client(opts.api_token.as_deref(), opts.service_root.as_deref());
    if api_client.is_some() {
        tracing::info!("spelunky.fyi API client configured");
    } else {
        tracing::info!("Local-only mod mode (no API token)");
    }

    let (mod_cache, cache_handle) = ModCache::new(
        api_client.clone(),
        Duration::from_secs(60),
        detected_tx,
        DiskMods::new(&install_path),
        Duration::from_secs(30),
    );

    let (changes_tx, _changes_rx) = broadcast::channel(10);
    let mut change_rx = changes_tx.subscribe();

    let (manager, handle) = ModManager::new(
        api_client,
        mod_cache.clone(),
        changes_tx,
        detected_rx,
        DEFAULT_RECEIVING_INTERVAL,
    );

    let listener_updates = updates_available.clone();
    let listener_app = app.clone();
    let task = tauri::async_runtime::spawn(async move {
        // Change listener: maintains the "mods with updates" set and emits
        // mods-changed events so the frontend refetches reactively.
        let listener = async move {
            loop {
                match change_rx.recv().await {
                    Ok(change) => {
                        {
                            let mut set = listener_updates.lock().unwrap();
                            match &change {
                                Change::NewVersion { id } => {
                                    set.insert(id.clone());
                                }
                                Change::Update {
                                    progress: ModProgress::Finished { r#mod },
                                } => {
                                    set.remove(&r#mod.id);
                                }
                                Change::Remove { id } => {
                                    set.remove(id);
                                }
                                _ => {}
                            }
                        }
                        let _ = listener_app.emit(MODS_CHANGED_EVENT, ());
                    }
                    Err(broadcast::error::RecvError::Lagged(_)) => continue,
                    Err(broadcast::error::RecvError::Closed) => break,
                }
            }
        };
        let toplevel = async move {
            let result = Toplevel::new(async move |s: &mut SubsystemHandle| {
                s.start(SubsystemBuilder::new(
                    "ModCache",
                    mod_cache.into_subsystem(),
                ));
                s.start(SubsystemBuilder::new(
                    "ModManager",
                    manager.into_subsystem(),
                ));
            })
            .handle_shutdown_requests(Duration::from_millis(1000))
            .await;
            if let Err(e) = result {
                tracing::error!("Mod subsystems shut down with error: {e:?}");
            }
        };
        tokio::join!(listener, toplevel);
    });

    ModsSetup {
        handle,
        cache_handle,
        task,
    }
}

fn setup_from_config<R: Runtime>(
    config: &crate::config::SharedConfig,
    updates_available: Arc<Mutex<HashSet<String>>>,
    app: AppHandle<R>,
) -> Option<ModsSetup> {
    let install_dir = config
        .install_dir
        .as_ref()
        .filter(|p| p.exists())
        .cloned()?;
    let opts = SetupOpts {
        install_dir,
        api_token: config.spelunky_fyi_api_token.clone(),
        service_root: config.spelunky_fyi_root.clone(),
    };
    Some(setup(opts, updates_available, app))
}

/// Public startup entry point used by lib.rs. Reads the current config and,
/// if the install directory is present, spawns the mod subsystem tree.
/// Returns the freshly built ModsSlot so lib.rs can hand it to AppState.
pub fn initial_setup<R: Runtime>(
    updates_available: Arc<Mutex<HashSet<String>>>,
    app: AppHandle<R>,
) -> crate::state::ModsSlot {
    let config = crate::config::load();
    match setup_from_config(&config, updates_available, app) {
        Some(s) => crate::state::ModsSlot {
            handle: Some(s.handle),
            cache_handle: Some(s.cache_handle),
            task: Some(s.task),
        },
        None => {
            tracing::warn!(
                "Skipping ModManager setup, install_dir missing or not present in config.json"
            );
            crate::state::ModsSlot::empty()
        }
    }
}

/// Rebuilds the mod subsystem tree from the current config. Called after
/// Settings save when install_dir, api_token, or fyi_root changed. The old
/// task is aborted only after the new one is spawned and swapped in, so the
/// window during which the frontend sees no ModManagerHandle is essentially
/// zero. Not a graceful shutdown of the old subsystems, but they hold no
/// unsaved state so aborting is safe.
#[tauri::command]
pub async fn rebuild_mods<R: Runtime>(
    state: tauri::State<'_, AppState>,
    app: tauri::AppHandle<R>,
) -> Result<(), String> {
    rebuild(&state, &app);
    Ok(())
}

/// Swap the mod subsystem for one built from current config.
///
/// Separate from the command because the credentials it reads can change
/// without anyone visiting Settings: linking an account writes a token from
/// Rust, and the manager captures its API client once at construction. Skipping
/// this leaves a manager holding `api_client: None`, which surfaces much later
/// as "Tried to access remote mod, but API isn't configured" on the next
/// install, long after the step that actually caused it.
pub(crate) fn rebuild<R: Runtime>(state: &AppState, app: &tauri::AppHandle<R>) {
    let updates_arc = state.updates_available().clone();
    let slot_arc = state.mods_slot().clone();

    let config = crate::config::load();
    let new_setup = setup_from_config(&config, updates_arc.clone(), app.clone());

    let old_task = {
        let mut slot = slot_arc.lock().unwrap();
        let old = slot.task.take();
        slot.handle = None;
        slot.cache_handle = None;
        if let Some(s) = new_setup {
            slot.handle = Some(s.handle);
            slot.cache_handle = Some(s.cache_handle);
            slot.task = Some(s.task);
        }
        old
    };

    // The new subsystem starts fresh; drop any stale entries the old poll
    // detected. The new ModCache will repopulate as it discovers versions.
    updates_arc.lock().unwrap().clear();
    if let Some(task) = old_task {
        task.abort();
    }

    let _ = app.emit(MODS_CHANGED_EVENT, ());
}

/// Wire-facing mod DTO. Rust `Mod` doesn't carry an update flag; joins in
/// AppState's updates_available set here so the frontend only makes one call
/// to render each row.
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ModDto {
    id: String,
    manifest: Option<Manifest>,
    has_update: bool,
    /// Folder mtime in milliseconds since the Unix epoch, 0 when unreadable.
    /// Both installing and updating a mod replace its folder, so this doubles
    /// as "when did this mod arrive", which is what the Mods page sorts on.
    modified_at: u64,
    /// When the mod was last loaded into a running game, or None if it hasn't
    /// been since the app started recording. Distinct from `modified_at`:
    /// installing a mod is not using it.
    last_used_at: Option<u64>,
    favorite: bool,
    /// Defects found by the last `check_mod` run, empty when the mod is clean
    /// *or* has never been checked. The two are deliberately not distinguished
    /// on the wire: the UI only ever needs "is there something to warn about",
    /// and checking every pack up front is what this design avoids.
    problems: Vec<crate::mod_check::ModProblem>,
}

/// On-disk record ml2_mods writes at
/// Mods/.ml/pack-metadata/&lt;id&gt;/latest.json after a successful API poll.
/// Held as a nested struct here just to deserialize the file without
/// pulling ml2_mods internals across a module boundary.
#[derive(serde::Deserialize)]
struct LatestFile {
    id: String,
}

/// Reads latest.json for a given mod id and returns its recorded id, or None
/// if the file is missing or unreadable. This is the "newest mod_file id
/// according to spelunky.fyi at last poll" marker.
fn read_latest_id(install_dir: &std::path::Path, mod_id: &str) -> Option<String> {
    let path = install_dir
        .join("Mods")
        .join(".ml")
        .join("pack-metadata")
        .join(mod_id)
        .join("latest.json");
    let bytes = std::fs::read(&path).ok()?;
    let file: LatestFile = serde_json::from_slice(&bytes).ok()?;
    Some(file.id)
}

#[tauri::command]
pub async fn list_mods(state: tauri::State<'_, AppState>) -> Result<Vec<ModDto>, ManagerError> {
    let Some(handle) = state.mods_handle() else {
        return Err(ManagerError::UnknownError(
            crate::setup::install_dir_message(),
        ));
    };
    // The Mods tab is the default tab, so the frontend fires this the
    // instant the webview boots, which routinely beats ModCache's first
    // disk scan (DiskMods::list reads every pack's manifest serially, so
    // it's slower the more mods you have and slower still on a cold FS
    // cache). Listing at that point returned an empty Vec, and since the
    // initial populate deliberately broadcasts no changes, nothing ever
    // emitted mods-changed to correct it: the page stayed empty until the
    // user hit Refresh. Wait for the scan instead, so the caller either
    // sees the real list or keeps showing its spinner.
    if let Some(cache_handle) = state.cache_handle()
        && tokio::time::timeout(CACHE_READY_TIMEOUT, cache_handle.ready())
            .await
            .is_err()
    {
        tracing::warn!("mod cache's first scan is still running; listing without it");
    }
    let mods = handle.list().await.map_err(ManagerError::from)?;
    Ok(build_mod_dtos(mods, state.updates_available()))
}

/// Reads the mods folder DIRECTLY from disk, bypassing the ModCache. Use
/// when the caller knows the mods dir just changed (create/delete a pack
/// outside the cache-managed flow) and needs immediate feedback: the
/// periodic cache poll otherwise takes several seconds to converge.
///
/// Every subsequent `list_mods` call still hits the cache, so the two lists
/// may briefly disagree until the cache's own poll catches up.
#[tauri::command]
pub async fn refresh_mods(state: tauri::State<'_, AppState>) -> Result<Vec<ModDto>, ManagerError> {
    // If the cache is running, ask it to re-scan the disk right now and wait
    // for the scan to finish; that way the fresh state is reflected both in
    // the returned value AND in every subsequent `list_mods` call. Falls
    // back to a direct disk read when the cache isn't wired (e.g. no
    // install_dir yet, or during a rebuild).
    if let Some(cache_handle) = state.cache_handle() {
        let _ = cache_handle.scan_now().await;
        let Some(handle) = state.mods_handle() else {
            return Err(ManagerError::UnknownError(
                crate::setup::install_dir_message(),
            ));
        };
        let mods = handle.list().await.map_err(ManagerError::from)?;
        return Ok(build_mod_dtos(mods, state.updates_available()));
    }

    let install_dir = crate::setup::install_dir().map_err(ManagerError::UnknownError)?;
    let install_str = install_dir.to_string_lossy().into_owned();
    let disk = DiskMods::new(&install_str);
    let mods = disk
        .list()
        .await
        .map_err(|e| ManagerError::UnknownError(e.to_string()))?;
    Ok(build_mod_dtos(mods, state.updates_available()))
}

/// Folder mtime for a mod, in milliseconds since the Unix epoch.
///
/// Both install and update replace the pack folder wholesale, so its mtime is
/// effectively "when this version of the mod landed" -- which is what someone
/// asking to find their newly installed mods actually wants. 0 when the folder
/// can't be stat'd, which sorts such mods to the far end rather than dropping
/// them.
fn read_modified_at(install_dir: &std::path::Path, mod_id: &str) -> u64 {
    install_dir
        .join("Mods")
        .join("Packs")
        .join(mod_id)
        .metadata()
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .and_then(|d| u64::try_from(d.as_millis()).ok())
        .unwrap_or(0)
}

fn build_mod_dtos(mods: Vec<Mod>, updates_available: &Arc<Mutex<HashSet<String>>>) -> Vec<ModDto> {
    let updates = updates_available.lock().unwrap().clone();
    let install_dir = crate::config::load().install_dir;

    // Favorites + usage history are per-install (see `mod_state`). Read once
    // for the whole list rather than per mod, and take the chance to drop
    // entries for mods that have since been deleted so the file stays bounded.
    let mut mod_state = install_dir
        .as_ref()
        .map(|dir| crate::mod_state::load(dir))
        .unwrap_or_default();
    if let Some(dir) = install_dir.as_ref() {
        let live: HashSet<String> = mods.iter().map(|m| m.id.clone()).collect();
        if crate::mod_state::prune(&mut mod_state, &live) {
            // Best-effort: a failed prune write costs nothing this run, and
            // failing the whole listing over it would be absurd.
            let _ = crate::mod_state::save(dir, &mod_state);
        }
    }
    let favorites: HashSet<&str> = mod_state.favorites.iter().map(String::as_str).collect();

    // has_update is the OR of the in-memory set (populated by ModCache's
    // periodic polling and by check_fyi_updates) and a per-mod comparison of
    // latest.json against the installed manifest.mod_file.id. The in-memory
    // set is fast but only picks up transitions of latest.json to a new value
    // and gets cleared on rebuild_mods; the disk comparison is the backstop
    // that surfaces persistently-stale mods.
    mods.into_iter()
        .map(|m| {
            let installed_file_id = m.manifest.as_ref().map(|man| man.mod_file.id.as_str());
            let latest_stale = match (install_dir.as_ref(), installed_file_id) {
                (Some(dir), Some(installed)) => match read_latest_id(dir, &m.id) {
                    Some(latest) => latest != installed,
                    None => false,
                },
                _ => false,
            };
            let modified_at = install_dir
                .as_ref()
                .map(|dir| read_modified_at(dir, &m.id))
                .unwrap_or(0);
            // Only trust a cached check that was taken against the pack as it
            // stands now. Anything older describes files the user may since
            // have fixed, and reporting that would be worse than saying
            // nothing.
            let problems = mod_state
                .checks
                .get(&m.id)
                .filter(|c| crate::mod_state::check_is_current(c, modified_at))
                .map(|c| c.problems.clone())
                .unwrap_or_default();
            ModDto {
                has_update: updates.contains(&m.id) || latest_stale,
                modified_at,
                last_used_at: mod_state.last_used.get(&m.id).copied(),
                favorite: favorites.contains(m.id.as_str()),
                problems,
                id: m.id,
                manifest: m.manifest,
            }
        })
        .collect()
}

/// Inspects one mod's files for defects that would break the game, caching
/// the result against the pack's current mtime.
///
/// Scoped to a single pack and called when the user is about to enable one,
/// rather than swept across the library: the walk is cheap for one mod and
/// prohibitive for the several hundred a heavy user has installed.
#[tauri::command]
pub async fn check_mod(id: String) -> Result<Vec<crate::mod_check::ModProblem>, String> {
    let install_dir = crate::setup::install_dir()?;
    let pack_dir = install_dir.join("Mods").join("Packs").join(&id);
    let problems =
        tauri::async_runtime::spawn_blocking(move || crate::mod_check::check_pack(&pack_dir))
            .await
            .map_err(|e| format!("check_mod: {e}"))?;
    // Best-effort cache: failing to persist costs a rescan, not correctness.
    let _ = crate::mod_state::set_check(
        &install_dir,
        &id,
        read_modified_at(&install_dir, &id),
        problems.clone(),
    );
    Ok(problems)
}

/// Stars or unstars a mod. Persisted per install (see `mod_state`), so it
/// travels with the `Mods` folder rather than with the user's settings.
#[tauri::command]
pub async fn set_mod_favorite(id: String, favorite: bool) -> Result<(), String> {
    let install_dir = crate::setup::install_dir()?;
    crate::mod_state::set_favorite(&install_dir, &id, favorite)
}

fn load_order_path() -> Result<PathBuf, String> {
    let install_dir = crate::setup::install_dir()?;
    Ok(install_dir
        .join("Mods")
        .join("Packs")
        .join("load_order.txt"))
}

/// Reads Playlunky's load_order.txt and returns the active mod ids in load
/// order. Lines prefixed with '--' are treated as inactive and skipped.
/// Returns an empty vec if the file doesn't exist yet (first-run case).
#[tauri::command]
pub async fn get_load_order() -> Result<Vec<String>, String> {
    let path = load_order_path()?;
    if !path.exists() {
        return Ok(vec![]);
    }
    let contents = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut active = Vec::new();
    for raw in contents.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with("--") {
            continue;
        }
        active.push(line.to_string());
    }
    Ok(active)
}

/// Writes Playlunky's load_order.txt. Active ids are written in the supplied
/// order (this is the load order), then any installed packs not in the
/// active list are written with a '--' prefix so Playlunky knows about them
/// as disabled.
#[tauri::command]
pub async fn set_load_order(
    state: tauri::State<'_, AppState>,
    active: Vec<String>,
) -> Result<(), String> {
    let path = load_order_path()?;

    let handle = state
        .mods_handle()
        .ok_or_else(crate::setup::install_dir_message)?;
    let all = handle.list().await.map_err(|e| e.to_string())?;
    let all_ids: HashSet<String> = all.into_iter().map(|m| m.id).collect();
    let active_set: HashSet<String> = active.iter().cloned().collect();

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir: {e}"))?;
    }

    let mut out = String::new();
    for id in &active {
        if all_ids.contains(id) {
            out.push_str(id);
            out.push('\n');
        }
    }
    for id in &all_ids {
        if !active_set.contains(id) {
            out.push_str("--");
            out.push_str(id);
            out.push('\n');
        }
    }

    std::fs::write(&path, out).map_err(|e| format!("write: {e}"))?;
    Ok(())
}

/// Returns the mod's logo as a data URL, or None if the mod has no logo.
/// Base64-encoded so the frontend can drop it straight into an <img src>
/// without needing the Tauri asset protocol configured.
#[tauri::command]
pub async fn get_mod_logo(
    state: tauri::State<'_, AppState>,
    id: String,
) -> Result<Option<String>, String> {
    let handle = state
        .mods_handle()
        .ok_or_else(crate::setup::install_dir_message)?;
    match handle.get_mod_logo(&id).await {
        Ok(logo) => {
            let encoded = B64.encode(&logo.bytes);
            Ok(Some(format!("data:{};base64,{}", logo.mime_type, encoded)))
        }
        // Common case: mod has no manifest or no logo entry. Not an error.
        Err(_) => Ok(None),
    }
}

#[tauri::command]
pub async fn remove_mod(state: tauri::State<'_, AppState>, id: String) -> Result<(), ManagerError> {
    let handle = state
        .mods_handle()
        .ok_or_else(|| ManagerError::UnknownError(crate::setup::install_dir_message()))?;
    handle.remove(&id).await.map_err(ManagerError::from)
}

#[tauri::command]
pub async fn open_mod_folder<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    id: String,
) -> Result<(), String> {
    let install_dir = crate::setup::install_dir()?;
    let target = install_dir.join("Mods").join("Packs").join(&id);
    if !target.exists() {
        return Err(format!("mod folder not found: {}", target.display()));
    }
    app.opener()
        .open_path(target.to_string_lossy(), None::<&str>)
        .map_err(|e| e.to_string())
}

/// Runs an update for a mod that was originally installed from spelunky.fyi.
/// Local mods aren't updateable this way (reinstall from a new file instead),
/// so ids without the fyi prefix early-out. Will fail with "API isn't
/// configured" if the API token isn't set in Settings.
#[tauri::command]
pub async fn update_mod(
    state: tauri::State<'_, AppState>,
    id: String,
) -> Result<Mod, ManagerError> {
    let handle = state
        .mods_handle()
        .ok_or_else(|| ManagerError::UnknownError(crate::setup::install_dir_message()))?;
    let code = id
        .strip_prefix(FYI_ID_PREFIX)
        .ok_or_else(|| {
            ManagerError::SourceError(
                "Only mods installed from spelunky.fyi can be updated automatically.".to_string(),
            )
        })?
        .to_string();
    handle
        .update(&ModSource::Remote { code })
        .await
        .map_err(ManagerError::from)
}

/// Installs a mod from spelunky.fyi by its slug. When overwrite is true the
/// existing mod is updated in place (calls update instead of install), which
/// is what the frontend does after confirming the ModExistsError from a
/// prior install call.
#[tauri::command]
pub async fn install_from_fyi(
    state: tauri::State<'_, AppState>,
    code: String,
    overwrite: bool,
) -> Result<Mod, ManagerError> {
    let handle = state
        .mods_handle()
        .ok_or_else(|| ManagerError::UnknownError(crate::setup::install_dir_message()))?;

    // Checked here rather than left to the manager, which answers with "Tried
    // to access remote mod, but API isn't configured": true, but it names an
    // internal condition instead of the thing the user can do about it.
    let config = crate::config::load();
    if build_api_client(
        config.spelunky_fyi_api_token.as_deref(),
        config.spelunky_fyi_root.as_deref(),
    )
    .is_none()
    {
        return Err(ManagerError::UnknownError(
            "Connect your spelunky.fyi account in Settings to install mods.".to_string(),
        ));
    }

    let package = ModSource::Remote { code };
    if overwrite {
        handle.update(&package).await.map_err(ManagerError::from)
    } else {
        handle.install(&package).await.map_err(ManagerError::from)
    }
}

/// Returns the folder names directly under install_dir/Mods/Packs so the
/// Install modal can offer them as autocomplete for "install into an
/// existing pack." Hidden folders (.ml, .git, etc) are skipped since they
/// aren't user-facing pack destinations.
#[tauri::command]
pub fn list_pack_ids() -> Result<Vec<String>, String> {
    let install_dir = crate::setup::install_dir()?;
    let packs_dir = install_dir.join("Mods").join("Packs");
    if !packs_dir.exists() {
        return Ok(Vec::new());
    }
    let mut ids = Vec::new();
    for entry in std::fs::read_dir(&packs_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        if let Some(name) = entry.file_name().to_str()
            && !name.starts_with('.')
        {
            ids.push(name.to_string());
        }
    }
    ids.sort();
    Ok(ids)
}

/// Force-polls spelunky.fyi for updates to every installed fyi mod. Unlike
/// ModCache's periodic poll, this happens on demand from the "check for
/// updates" button in the Mods header. Builds a fresh HttpApiMods from the
/// current config each call so it works even before restart after the user
/// pastes their token. Returns the number of mods found with a new version.
/// Emits mods-changed at the end so the row Update buttons appear without
/// waiting for the next scheduled poll.
///
/// One batched `check_updates` call (implicitly chunked to 200 slugs
/// per HTTP request on the client) replaces the previous per-mod
/// get_manifest loop, which was N round trips against the server.
#[tauri::command]
pub async fn check_fyi_updates<R: Runtime>(
    state: tauri::State<'_, AppState>,
    app: AppHandle<R>,
) -> Result<usize, String> {
    let cfg = crate::config::load();
    let handle = state
        .mods_handle()
        .ok_or_else(crate::setup::install_dir_message)?;
    let api_client = build_api_client(
        cfg.spelunky_fyi_api_token.as_deref(),
        cfg.spelunky_fyi_root.as_deref(),
    )
    .ok_or_else(|| "Add a spelunky.fyi API token in Settings to check for updates.".to_string())?;

    let mods = handle.list().await.map_err(|e| e.to_string())?;

    // Map slug -> (mod id, currently installed mod_file id). Skip mods
    // without a manifest or with a blank slug (side-loaded local packs).
    let mut wanted: std::collections::HashMap<String, (String, String)> =
        std::collections::HashMap::new();
    for m in mods {
        let Some(manifest) = m.manifest.as_ref() else {
            continue;
        };
        let slug = manifest.slug.trim();
        if slug.is_empty() {
            continue;
        }
        wanted.insert(
            slug.to_string(),
            (m.id.clone(), manifest.mod_file.id.clone()),
        );
    }

    if wanted.is_empty() {
        let _ = app.emit(MODS_CHANGED_EVENT, ());
        return Ok(0);
    }

    let slug_refs: Vec<&str> = wanted.keys().map(String::as_str).collect();
    let response = api_client
        .check_updates(&slug_refs)
        .await
        .map_err(|e| format!("check_fyi_updates: {e}"))?;

    // not_found means the mod was deleted / unlisted / never had a file:
    // treat as "no update", not an error, matching the per-mod 404 path.
    let mut found = 0usize;
    for (slug, (mod_id, installed_file_id)) in wanted {
        let Some(latest) = response.mods.get(&slug) else {
            continue;
        };
        if latest.id != installed_file_id {
            state.updates_available().lock().unwrap().insert(mod_id);
            found += 1;
        }
    }

    let _ = app.emit(MODS_CHANGED_EVENT, ());
    Ok(found)
}

/// Removes Playlunky's own cache directory at Mods/Packs/.db. Playlunky
/// rebuilds this on the next launch.
#[tauri::command]
pub fn clear_playlunky_cache() -> Result<(), String> {
    let install_dir = crate::setup::install_dir()?;
    let cache_dir = install_dir.join("Mods").join("Packs").join(".db");
    if cache_dir.exists() {
        std::fs::remove_dir_all(&cache_dir).map_err(|e| format!("clear cache: {e}"))?;
    }
    Ok(())
}

/// Installs a mod from a local .zip archive. dest_id is the folder name it
/// gets under Mods/Packs; the frontend derives it from the file stem. When
/// overwrite is true, an existing mod at dest_id is replaced.
#[tauri::command]
pub async fn install_from_local(
    state: tauri::State<'_, AppState>,
    source_path: String,
    dest_id: String,
    overwrite: bool,
) -> Result<Mod, ManagerError> {
    let handle = state
        .mods_handle()
        .ok_or_else(|| ManagerError::UnknownError(crate::setup::install_dir_message()))?;
    let package = ModSource::Local {
        source_path,
        dest_id,
    };
    if overwrite {
        handle.update(&package).await.map_err(ManagerError::from)
    } else {
        handle.install(&package).await.map_err(ManagerError::from)
    }
}
