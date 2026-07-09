// Extract Assets tab backend. Wraps ml2_assets' AssetStore + Soundbank behind
// Tauri commands and emits phase progress events so the frontend can show
// what's happening during the multi-second extraction.

use std::collections::HashMap;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use ml2_assets::{AssetStore, Soundbank, StringHasher};
use ml2_sprites::{SpriteLoader, SpriteMerger, all_loaders, all_mergers};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager, Runtime, State};

use crate::state::AppState;

const PROGRESS_EVENT: &str = "extract-progress";
const MAX_EXE_SCAN_DEPTH: usize = 3;
const IGNORED_EXE_FILENAMES: &[&str] = &["modlunky2.exe"];

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ExtractOptions {
    pub extract_wav: bool,
    pub extract_ogg: bool,
    pub reuse_extracted: bool,
    pub generate_string_hashes: bool,
    pub create_entity_sprites: bool,
}

#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
struct ExtractProgress {
    phase: &'static str,
    detail: Option<String>,
    done: Option<usize>,
    total: Option<usize>,
}

fn emit<R: Runtime>(app: &AppHandle<R>, phase: &'static str, detail: Option<String>) {
    let _ = app.emit(
        PROGRESS_EVENT,
        ExtractProgress {
            phase,
            detail,
            done: None,
            total: None,
        },
    );
    // Mirror to the shared slot so late mounts can catch the current
    // phase without waiting for the next event.
    if let Some(state) = app.try_state::<AppState>() {
        state.extract().set(ExtractStatus {
            phase,
            done: None,
            total: None,
        });
    }
}

fn emit_counted<R: Runtime>(app: &AppHandle<R>, phase: &'static str, done: usize, total: usize) {
    let _ = app.emit(
        PROGRESS_EVENT,
        ExtractProgress {
            phase,
            detail: None,
            done: Some(done),
            total: Some(total),
        },
    );
    if let Some(state) = app.try_state::<AppState>() {
        state.extract().set(ExtractStatus {
            phase,
            done: Some(done),
            total: Some(total),
        });
    }
}

/// Snapshot of what an in-flight extract is doing, mirrored on the Rust
/// side of the AppState so a fresh page mount or app reload can resume
/// showing progress without waiting for the next event.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ExtractStatus {
    pub phase: &'static str,
    pub done: Option<usize>,
    pub total: Option<usize>,
}

/// Shared slot holding the currently-running extract's phase, or None
/// when no extract is in flight. Managed by AppState.
#[derive(Debug, Clone, Default)]
pub struct ExtractStatusSlot(Arc<Mutex<Option<ExtractStatus>>>);

impl ExtractStatusSlot {
    pub fn new() -> Self {
        Self::default()
    }

    fn set(&self, status: ExtractStatus) {
        *self.0.lock().unwrap() = Some(status);
    }

    fn clear(&self) {
        *self.0.lock().unwrap() = None;
    }

    /// Returns true iff nothing is currently running (i.e. a fresh extract
    /// may start). Called before the invoker spawns a task.
    fn try_begin(&self) -> bool {
        let mut guard = self.0.lock().unwrap();
        if guard.is_some() {
            return false;
        }
        *guard = Some(ExtractStatus {
            phase: "preparing",
            done: None,
            total: None,
        });
        true
    }

    pub fn snapshot(&self) -> Option<ExtractStatus> {
        self.0.lock().unwrap().clone()
    }
}

/// Frontend-facing "what's happening?" query. Called on ExtractPage mount
/// so navigation-away-and-back can resume showing progress instead of
/// jumping to the idle hero. None means nothing is running.
#[tauri::command]
pub fn get_extract_status(state: State<AppState>) -> Option<ExtractStatus> {
    state.extract().snapshot()
}

/// True iff the user has run Extract at least once, i.e. there's a
/// non-empty `Mods/Extracted/Data/Textures/` directory. The level editor
/// windows gate their UI on this because sprite lookups without extracted
/// assets return placeholders for every tile.
#[tauri::command]
pub fn extracted_assets_available() -> bool {
    let Some(install_dir) = crate::config::load().install_dir else {
        return false;
    };
    let textures_dir = install_dir
        .join("Mods")
        .join("Extracted")
        .join("Data")
        .join("Textures");
    let Ok(mut iter) = std::fs::read_dir(&textures_dir) else {
        return false;
    };
    iter.next().is_some()
}

// Emit a per-asset progress event no more than this often. Prevents IPC
// spam during the ~1000-asset AssetStore::extract loop while still keeping
// the bar visibly moving; every 5 assets is roughly a 4Hz update in release
// mode and slower but still active in debug.
const PROGRESS_TICK_EVERY: usize = 5;

/// Returns .exe file paths (relative to install_dir) up to three directory
/// levels deep. Excludes modlunky2.exe so users don't accidentally pick the
/// app's own binary out of the game folder.
#[tauri::command]
pub fn list_extractable_exes() -> Result<Vec<String>, String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    if !install_dir.exists() {
        return Ok(Vec::new());
    }
    let mut exes = Vec::new();
    walk_for_exes(&install_dir, &install_dir, 0, &mut exes);
    exes.sort();
    Ok(exes)
}

fn walk_for_exes(base: &Path, dir: &Path, depth: usize, out: &mut Vec<String>) {
    if depth > MAX_EXE_SCAN_DEPTH {
        return;
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name();
        let name_str = name.to_string_lossy().into_owned();
        if path.is_dir() {
            if name_str.starts_with('.') {
                continue;
            }
            walk_for_exes(base, &path, depth + 1, out);
        } else if name_str.to_ascii_lowercase().ends_with(".exe")
            && !IGNORED_EXE_FILENAMES.contains(&name_str.as_str())
            && let Ok(rel) = path.strip_prefix(base)
        {
            out.push(rel.to_string_lossy().into_owned());
        }
    }
}

/// Runs an extraction pass. Long-running work is dispatched to a blocking
/// thread so the tokio runtime stays responsive; phase events fire at
/// each stage boundary so the UI can render progress.
///
/// Concurrent starts are rejected: if an extract is already in flight
/// (from any window / any prior click that hasn't finished yet), the
/// second invoke returns an error immediately instead of racing a
/// second spawn_blocking task. The frontend can also read the current
/// phase via `get_extract_status`.
#[tauri::command]
pub async fn extract_assets<R: Runtime>(
    app: AppHandle<R>,
    state: State<'_, AppState>,
    exe_relative: String,
    options: ExtractOptions,
) -> Result<(), String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    let exe_path = install_dir.join(&exe_relative);
    if !exe_path.exists() {
        return Err(format!("exe not found: {}", exe_path.display()));
    }
    let extracted_dir = install_dir.join("Mods").join("Extracted");
    let packs_dir = install_dir.join("Mods").join("Packs");

    // Reserve the status slot before spawning so a fast second click gets a
    // clean error instead of starting a parallel extract.
    let slot = state.extract().clone();
    if !slot.try_begin() {
        return Err("another extraction is already in progress; wait for it to finish".into());
    }

    let app_for_task = app.clone();
    let slot_for_task = slot.clone();
    let result = tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        run_extract(
            &app_for_task,
            &exe_path,
            &extracted_dir,
            &packs_dir,
            &options,
        )
    })
    .await;

    // Always clear the slot; the frontend polls `get_extract_status` and
    // uses "None" to know it's safe to allow a new click.
    slot_for_task.clear();

    result.map_err(|e| format!("extract task join: {e}"))?
}

fn run_extract<R: Runtime>(
    app: &AppHandle<R>,
    exe_path: &Path,
    extracted_dir: &Path,
    packs_dir: &Path,
    options: &ExtractOptions,
) -> Result<(), String> {
    emit(app, "preparing", None);
    std::fs::create_dir_all(extracted_dir).map_err(|e| format!("mkdir Extracted: {e}"))?;
    std::fs::create_dir_all(packs_dir).map_err(|e| format!("mkdir Packs: {e}"))?;

    if !options.reuse_extracted {
        emit(
            app,
            "extracting-assets",
            Some(exe_path.display().to_string()),
        );
        {
            let file = std::fs::File::open(exe_path)
                .map_err(|e| format!("open {}: {e}", exe_path.display()))?;
            let mut reader = BufReader::new(file);
            let mut store = AssetStore::from_handle(&mut reader)
                .map_err(|e| format!("parse asset store: {e}"))?;
            store
                .extract_with_progress(extracted_dir, |done, total| {
                    // Throttle: emit every N assets plus the final tick.
                    if done == total || done % PROGRESS_TICK_EVERY == 0 {
                        emit_counted(app, "extracting-assets", done, total);
                    }
                })
                .map_err(|e| format!("extract assets: {e}"))?;
            // Drop store (and its file handle) here so the subsequent exe
            // backup copy doesn't hit a Windows sharing-violation error.
        }

        emit(app, "backing-up-exe", None);
        let backup = extracted_dir.join("Spel2.exe");
        if !paths_match(&backup, exe_path) {
            std::fs::copy(exe_path, &backup).map_err(|e| format!("backup exe: {e}"))?;
        }
    }

    if options.extract_wav || options.extract_ogg {
        emit(app, "extracting-audio", None);
        extract_soundbank(extracted_dir, options.extract_wav, options.extract_ogg)?;
    }

    if options.generate_string_hashes {
        emit(app, "hashing-strings", None);
        generate_string_hashes(extracted_dir)?;
    }

    if options.create_entity_sprites {
        generate_entity_sprites(app, extracted_dir)?;
    }

    emit(app, "done", None);
    Ok(())
}

/// Composes per-entity sprite sheets under Data/Textures/Entities/ using the
/// bundled loader and merger configs from ml2_sprites. Loaders whose source
/// PNG is absent (DLC-only textures on a base install, or a partial extract)
/// are skipped so mergers referencing them silently drop those origin
/// entries. Emits progress per merger so the frontend bar advances through
/// the ~128 sheets.
fn generate_entity_sprites<R: Runtime>(
    app: &AppHandle<R>,
    extracted_dir: &Path,
) -> Result<(), String> {
    let loader_configs = all_loaders();
    let merger_configs = all_mergers();

    let total_loaders = loader_configs.len();
    emit_counted(app, "loading-sprite-sheets", 0, total_loaders);

    // Load every loader that has a matching PNG on disk. Skip missing ones
    // rather than error since a base install won't have DLC textures.
    let mut loaders: HashMap<String, SpriteLoader> = HashMap::new();
    for (idx, cfg) in loader_configs.into_iter().enumerate() {
        let name = cfg.name.clone();
        match SpriteLoader::open_if_present(extracted_dir, cfg) {
            Ok(Some(loader)) => {
                loaders.insert(name, loader);
            }
            Ok(None) => {
                tracing::debug!("Skipping sprite loader {name}, source PNG not present");
            }
            Err(e) => {
                tracing::warn!("Failed to load sprite sheet {name}: {e}");
            }
        }
        emit_counted(app, "loading-sprite-sheets", idx + 1, total_loaders);
    }

    let total_mergers = merger_configs.len();
    emit_counted(app, "generating-entity-sheets", 0, total_mergers);

    for (idx, cfg) in merger_configs.into_iter().enumerate() {
        let merger = SpriteMerger::new(cfg);
        let loader_refs: HashMap<String, &SpriteLoader> =
            loaders.iter().map(|(k, v)| (k.clone(), v)).collect();
        match merger.merge(&loader_refs, false) {
            Ok(result) => {
                if let Err(e) = result.save(extracted_dir) {
                    tracing::warn!(
                        "Failed to save merger {}: {e}",
                        merger.config.target_sprite_sheet_path.display()
                    );
                }
            }
            Err(e) => {
                tracing::warn!(
                    "Failed to merge {}: {e}",
                    merger.config.target_sprite_sheet_path.display()
                );
            }
        }
        // Emit every merger; 128 events over ~10s is fine for the UI to keep
        // up and users get a granular percentage.
        emit_counted(app, "generating-entity-sheets", idx + 1, total_mergers);
    }

    Ok(())
}

/// Produces strings*_hashed.str for every strings*.str file in the extract
/// dir. Uses strings00.str (English) as the hash source and applies the
/// same table to every language file. Files with a different line count
/// than English are skipped rather than aborted so a stray malformed
/// localization doesn't sink the whole pass.
fn generate_string_hashes(extracted_dir: &Path) -> Result<(), String> {
    let english_path = extracted_dir.join("strings00.str");
    if !english_path.exists() {
        return Err(format!(
            "strings00.str not found at {}; run without \"Reuse extracted\" first.",
            english_path.display()
        ));
    }

    let hasher = {
        let file =
            std::fs::File::open(&english_path).map_err(|e| format!("open strings00.str: {e}"))?;
        StringHasher::from_reader(BufReader::new(file))
    };

    let entries =
        std::fs::read_dir(extracted_dir).map_err(|e| format!("read extracted dir: {e}"))?;
    for entry in entries {
        let entry = entry.map_err(|e| format!("dir entry: {e}"))?;
        let path = entry.path();
        let Some(file_name) = path.file_name().and_then(|s| s.to_str()) else {
            continue;
        };
        if !file_name.starts_with("strings")
            || !file_name.ends_with(".str")
            || file_name.contains("_hashed")
        {
            continue;
        }

        let file = std::fs::File::open(&path).map_err(|e| format!("open {file_name}: {e}"))?;
        let lines: Vec<String> = BufReader::new(file)
            .lines()
            .collect::<Result<_, _>>()
            .map_err(|e| format!("read {file_name}: {e}"))?;
        if lines.len() != hasher.hashes.len() {
            tracing::warn!(
                "Skipping {file_name}: line count {} does not match strings00.str ({})",
                lines.len(),
                hasher.hashes.len()
            );
            continue;
        }

        // strings00.str -> strings00_hashed.str
        let stem = file_name.trim_end_matches(".str");
        let out_path = path
            .parent()
            .ok_or_else(|| "extract dir has no parent".to_string())?
            .join(format!("{stem}_hashed.str"));
        let mut out = std::fs::File::create(&out_path)
            .map_err(|e| format!("create {}: {e}", out_path.display()))?;
        hasher
            .merge_hashes(&lines, &mut out)
            .map_err(|e| format!("merge hashes for {file_name}: {e}"))?;
    }
    Ok(())
}

fn paths_match(a: &Path, b: &Path) -> bool {
    match (std::fs::canonicalize(a), std::fs::canonicalize(b)) {
        (Ok(a), Ok(b)) => a == b,
        _ => a == b,
    }
}

fn extract_soundbank(extracted_dir: &Path, want_wav: bool, want_ogg: bool) -> Result<(), String> {
    let soundbank_path = extracted_dir.join("soundbank.bank");
    if !soundbank_path.exists() {
        return Err(format!(
            "soundbank.bank not found at {}. Run without \"Reuse extracted\" first.",
            soundbank_path.display()
        ));
    }
    let path_str = soundbank_path
        .to_str()
        .ok_or_else(|| "soundbank path is not valid unicode".to_string())?;
    let soundbank = Soundbank::from_path(path_str).map_err(|e| format!("open soundbank: {e}"))?;

    for fsb in soundbank.fsbs {
        let ext = fsb.header.mode.file_extension();
        let matches = match ext.as_str() {
            "wav" => want_wav,
            "ogg" => want_ogg,
            _ => false,
        };
        if !matches {
            continue;
        }
        let out_dir = extracted_dir.join("soundbank").join(&ext);
        std::fs::create_dir_all(&out_dir).map_err(|e| format!("mkdir soundbank dir: {e}"))?;
        for track in fsb.tracks {
            let out_path = out_dir.join(format!("{}.{}", track.name, ext));
            let bytes = track
                .rebuild_as(&fsb.header.mode)
                .map_err(|e| format!("rebuild track {}: {e}", track.name))?;
            std::fs::write(&out_path, bytes)
                .map_err(|e| format!("write {}: {e}", out_path.display()))?;
        }
    }
    Ok(())
}

// Suppress a warning if the future turns out unused in other contexts.
#[allow(dead_code)]
fn _keep_pathbuf_import(_: PathBuf) {}
