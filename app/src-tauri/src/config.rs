// Reads and writes the shared modlunky2 config.json. The on-disk file uses
// kebab-case keys; the wire format between Rust and the frontend uses
// camelCase. Only the fields the app currently needs are represented, so
// this is a targeted reader not a full mapping. Writes preserve unknown
// JSON fields by round-tripping through serde_json::Value.

use std::path::PathBuf;

use directories::BaseDirs;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

const KEY_INSTALL_DIR: &str = "install-dir";
const KEY_FYI_ROOT: &str = "spelunky-fyi-root";
const KEY_FYI_TOKEN: &str = "spelunky-fyi-api-token";
const KEY_PLAYLUNKY_VERSION: &str = "playlunky-version";
const KEY_PLAYLUNKY_CONSOLE: &str = "playlunky-console";
const KEY_PLAYLUNKY_OVERLUNKY: &str = "playlunky-overlunky";
const KEY_COMMAND_PREFIX: &str = "command-prefix";
const KEY_PLAYLUNKY_SHORTCUT: &str = "playlunky-shortcut";
/// Tab id that was active when the user last closed the app shell.
/// Matches the frontend's Tab string union so it round-trips as-is.
const KEY_LAST_TAB: &str = "last-tab";
/// User-authored setroom template formats.
pub const KEY_CUSTOM_SAVE_FORMATS: &str = "custom-level-editor-custom-save-formats";
/// The single format the editor uses by default for new levels + as the
/// preferred detection hint on load.
pub const KEY_DEFAULT_SAVE_FORMAT: &str = "custom-level-editor-default-save-format";
/// Recent packs opened in the Vanilla editor. Most-recent first, capped at
/// `MAX_RECENT_PACKS` entries. Key kept separate from Custom so a user's
/// history in one mode doesn't crowd out the other.
pub const KEY_RECENT_VANILLA_PACKS: &str = "level-editor-vanilla-recents";
/// Recent packs opened in the Custom editor.
pub const KEY_RECENT_CUSTOM_PACKS: &str = "level-editor-custom-recents";
/// App-wide level-editor UI preferences (default zoom behavior, clamp render
/// toggle, grid visibility). Stored as one JSON object so the settings modal
/// round-trips the whole thing; see `EditorPrefs` in `level_editor.rs`.
pub const KEY_EDITOR_PREFS: &str = "level-editor-prefs";
/// Port the tracker HTTP + WS server binds on. Key name pre-dates the
/// tracker-specific naming and is kept for round-trip compatibility.
const KEY_TRACKER_PORT: &str = "api-port";
/// Whether the tracker server should start automatically when the
/// app launches.
const KEY_TRACKER_AUTO_START: &str = "tracker-server-auto-start";
/// CSS background color the popped-out tracker window + browser
/// source use, so users can chroma-key it out in OBS.
const KEY_TRACKER_COLOR_KEY: &str = "tracker-color-key";
/// Font pixel size for the tracker text.
const KEY_TRACKER_FONT_SIZE: &str = "tracker-font-size";
/// Font family for the tracker text.
const KEY_TRACKER_FONT_FAMILY: &str = "tracker-font-family";
/// Fill color for the tracker text.
const KEY_TRACKER_FONT_COLOR: &str = "tracker-font-color";
/// Outline (text stroke) width in px for the tracker text; 0 = none.
const KEY_TRACKER_STROKE_WIDTH: &str = "tracker-stroke-width";
/// Outline (text stroke) color for the tracker text.
const KEY_TRACKER_STROKE_COLOR: &str = "tracker-stroke-color";
/// Optional override for where tracker text files land. When absent,
/// falls back to `{install-dir}/Mods/Modlunky2/trackers`.
const KEY_TRACKER_OUTPUT_DIR: &str = "tracker-output-dir";
/// Global toggle: when true, opening a tracker window also spawns a
/// file writer that mirrors its current display to
/// `{output_dir}/{slug}.txt` for as long as the window is open. The
/// writer's lifecycle is tied to the window's, so closing the window
/// blanks the file automatically.
const KEY_TRACKER_FILE_ENABLED: &str = "tracker-file-enabled";
/// Whether popped-out tracker windows should stay above other
/// windows. Applied to every new tracker window at open time and to
/// every already-open one when the setting toggles.
const KEY_TRACKER_ALWAYS_ON_TOP: &str = "tracker-always-on-top";
/// UI color theme for the whole app. `"dark"` (default) or `"light"`.
/// The frontend reads this at boot to set `data-theme` on the document.
const KEY_THEME: &str = "theme";
/// Minimum severity that shows a floating toast: `"info" | "success" |
/// "warning" | "error"`. Quieter levels are still recorded to the toast log,
/// just not popped. Defaults to `"warning"` so routine success/info messages
/// stay in the log without covering the UI.
const KEY_TOAST_LEVEL: &str = "toast-level";

pub const DEFAULT_TRACKER_COLOR_KEY: &str = "#00ff00";
pub const DEFAULT_TRACKER_FONT_SIZE: u16 = 24;
pub const DEFAULT_TRACKER_FONT_FAMILY: &str = "Arial";
pub const DEFAULT_TRACKER_FONT_COLOR: &str = "#ffffff";
/// No outline by default, so every tracker looks the same until the user
/// opts into a stroke (which then applies to all of them uniformly).
pub const DEFAULT_TRACKER_STROKE_WIDTH: u16 = 0;
pub const DEFAULT_TRACKER_STROKE_COLOR: &str = "#000000";
/// Defaults to true: matches the pre-setting behavior where every
/// tracker window was hardcoded to always-on-top, so upgrading users
/// don't notice a change on first launch.
pub const DEFAULT_TRACKER_ALWAYS_ON_TOP: bool = true;
/// Dark is the app's original and default look; light is opt-in.
pub const DEFAULT_THEME: &str = "dark";
/// Only warnings and errors pop a toast by default; success/info stay in the
/// log. Keeps the corners clear during routine use.
pub const DEFAULT_TOAST_LEVEL: &str = "warning";

/// Wire-facing snapshot of the config fields the Tauri app cares about.
/// camelCase over the wire; snake_case in Rust.
#[derive(Debug, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SharedConfig {
    pub install_dir: Option<PathBuf>,
    pub spelunky_fyi_root: Option<String>,
    pub spelunky_fyi_api_token: Option<String>,
    pub playlunky_version: Option<String>,
    pub playlunky_console: bool,
    pub playlunky_overlunky: bool,
    pub command_prefix: Option<String>,
    pub playlunky_shortcut: bool,
    pub last_tab: Option<String>,
    pub tracker_server_port: u16,
    pub tracker_server_auto_start: bool,
    pub tracker_color_key: String,
    pub tracker_font_size: u16,
    pub tracker_font_family: String,
    pub tracker_font_color: String,
    pub tracker_stroke_width: u16,
    pub tracker_stroke_color: String,
    pub tracker_output_dir: Option<String>,
    pub tracker_file_enabled: bool,
    pub tracker_always_on_top: bool,
    pub theme: String,
    pub toast_level: String,
}

/// Values the Settings modal can set. `Some("")` clears a string field
/// (removes the key from the JSON); `None` leaves it untouched. Booleans
/// use `Some(true|false)` to set, `None` to leave.
#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConfigPatch {
    pub install_dir: Option<String>,
    pub spelunky_fyi_root: Option<String>,
    pub spelunky_fyi_api_token: Option<String>,
    pub playlunky_version: Option<String>,
    pub playlunky_console: Option<bool>,
    pub playlunky_overlunky: Option<bool>,
    pub command_prefix: Option<String>,
    pub playlunky_shortcut: Option<bool>,
    pub last_tab: Option<String>,
    pub tracker_server_port: Option<u16>,
    pub tracker_server_auto_start: Option<bool>,
    pub tracker_color_key: Option<String>,
    pub tracker_font_size: Option<u16>,
    pub tracker_font_family: Option<String>,
    pub tracker_font_color: Option<String>,
    pub tracker_stroke_width: Option<u16>,
    pub tracker_stroke_color: Option<String>,
    pub tracker_output_dir: Option<String>,
    pub tracker_file_enabled: Option<bool>,
    pub tracker_always_on_top: Option<bool>,
    pub theme: Option<String>,
    pub toast_level: Option<String>,
}

/// Path where the shared config.json lives. On Windows this is
/// `%LOCALAPPDATA%\spelunky.fyi\modlunky2\config.json` (no "config"
/// subfolder). The `directories` crate's `ProjectDirs::config_dir` adds
/// one and uses the roaming dir, so the path is assembled from BaseDirs
/// by hand.
pub fn config_path() -> Option<PathBuf> {
    let base = BaseDirs::new()?;
    Some(
        base.data_local_dir()
            .join("spelunky.fyi")
            .join("modlunky2")
            .join("config.json"),
    )
}

pub fn load_raw() -> Map<String, Value> {
    let Some(path) = config_path() else {
        return Map::new();
    };
    let Ok(contents) = std::fs::read_to_string(&path) else {
        tracing::warn!("Config not found at {}", path.display());
        return Map::new();
    };
    match serde_json::from_str::<Value>(&contents) {
        Ok(v) => v.as_object().cloned().unwrap_or_default(),
        Err(e) => {
            // A subsequent write via `apply_patch` / `set_nested` would happily
            // overwrite the corrupt file with a fresh partial JSON, silently
            // losing every key the user had set. Move the corrupt file aside
            // so the user can recover it manually.
            let backup = backup_corrupt_path(&path);
            tracing::warn!(
                "Failed to parse config at {}: {e}. Moving aside to {}",
                path.display(),
                backup.display()
            );
            if let Err(rename_err) = std::fs::rename(&path, &backup) {
                tracing::warn!(
                    "Could not move corrupt config aside: {rename_err}. \
                     Next write will overwrite it."
                );
            }
            Map::new()
        }
    }
}

/// `config.json` -> `config.corrupt.<unix-secs>.json`. Same-dir rename so
/// the backup lives next to the original for easy discovery.
fn backup_corrupt_path(path: &std::path::Path) -> PathBuf {
    let stem = path
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "config".to_string());
    let ext = path
        .extension()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let filename = if ext.is_empty() {
        format!("{stem}.corrupt.{secs}")
    } else {
        format!("{stem}.corrupt.{secs}.{ext}")
    };
    path.with_file_name(filename)
}

/// Writes `bytes` to `path` via `<path>.tmp` + rename, so a crash mid-write
/// leaves the previous file intact instead of a half-written truncated one.
/// Rename is atomic on Windows (MoveFileEx MOVEFILE_REPLACE_EXISTING) and
/// POSIX (rename(2)).
fn atomic_write(path: &std::path::Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir: {e}"))?;
    }
    let mut tmp_name = path.as_os_str().to_owned();
    tmp_name.push(".tmp");
    let tmp = PathBuf::from(tmp_name);
    std::fs::write(&tmp, bytes).map_err(|e| format!("write tmp: {e}"))?;
    if let Err(e) = std::fs::rename(&tmp, path) {
        let _ = std::fs::remove_file(&tmp);
        return Err(format!("rename tmp: {e}"));
    }
    Ok(())
}

fn get_string(obj: &Map<String, Value>, key: &str) -> Option<String> {
    obj.get(key).and_then(|v| v.as_str().map(String::from))
}

fn get_bool(obj: &Map<String, Value>, key: &str) -> bool {
    obj.get(key).and_then(|v| v.as_bool()).unwrap_or(false)
}

fn get_u16(obj: &Map<String, Value>, key: &str, default: u16) -> u16 {
    obj.get(key)
        .and_then(|v| v.as_u64())
        .and_then(|n| u16::try_from(n).ok())
        .unwrap_or(default)
}

/// Reads command_prefix in either shape the on-disk value may take: a
/// plain string, or a JSON array of tokens (a legacy shape). Both
/// become a single space-joined string on the Rust side.
fn get_command_prefix(obj: &Map<String, Value>) -> Option<String> {
    let v = obj.get(KEY_COMMAND_PREFIX)?;
    if let Some(s) = v.as_str() {
        let trimmed = s.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    } else if let Some(arr) = v.as_array() {
        let parts: Vec<String> = arr
            .iter()
            .filter_map(|x| x.as_str().map(String::from))
            .collect();
        if parts.is_empty() {
            None
        } else {
            Some(parts.join(" "))
        }
    } else {
        None
    }
}

pub fn load() -> SharedConfig {
    from_map(&load_raw())
}

/// Build a `SharedConfig` from a raw JSON object. Split out of `load()`
/// so tests can drive it without needing a real file on disk. Swallows
/// unknown keys (round-tripped through `apply_patch` on write) and
/// treats `null`-valued string keys the same as missing keys.
pub(crate) fn from_map(obj: &Map<String, Value>) -> SharedConfig {
    SharedConfig {
        install_dir: get_string(obj, KEY_INSTALL_DIR).map(PathBuf::from),
        spelunky_fyi_root: get_string(obj, KEY_FYI_ROOT),
        spelunky_fyi_api_token: get_string(obj, KEY_FYI_TOKEN),
        playlunky_version: get_string(obj, KEY_PLAYLUNKY_VERSION),
        playlunky_console: get_bool(obj, KEY_PLAYLUNKY_CONSOLE),
        playlunky_overlunky: get_bool(obj, KEY_PLAYLUNKY_OVERLUNKY),
        command_prefix: get_command_prefix(obj),
        playlunky_shortcut: get_bool(obj, KEY_PLAYLUNKY_SHORTCUT),
        last_tab: get_string(obj, KEY_LAST_TAB),
        tracker_server_port: get_u16(obj, KEY_TRACKER_PORT, crate::trackers::DEFAULT_TRACKER_PORT),
        tracker_server_auto_start: get_bool(obj, KEY_TRACKER_AUTO_START),
        tracker_color_key: get_string(obj, KEY_TRACKER_COLOR_KEY)
            .unwrap_or_else(|| DEFAULT_TRACKER_COLOR_KEY.to_string()),
        tracker_font_size: get_u16(obj, KEY_TRACKER_FONT_SIZE, DEFAULT_TRACKER_FONT_SIZE),
        tracker_font_family: get_string(obj, KEY_TRACKER_FONT_FAMILY)
            .unwrap_or_else(|| DEFAULT_TRACKER_FONT_FAMILY.to_string()),
        tracker_font_color: get_string(obj, KEY_TRACKER_FONT_COLOR)
            .unwrap_or_else(|| DEFAULT_TRACKER_FONT_COLOR.to_string()),
        tracker_stroke_width: get_u16(obj, KEY_TRACKER_STROKE_WIDTH, DEFAULT_TRACKER_STROKE_WIDTH),
        tracker_stroke_color: get_string(obj, KEY_TRACKER_STROKE_COLOR)
            .unwrap_or_else(|| DEFAULT_TRACKER_STROKE_COLOR.to_string()),
        tracker_output_dir: get_string(obj, KEY_TRACKER_OUTPUT_DIR),
        tracker_file_enabled: get_bool(obj, KEY_TRACKER_FILE_ENABLED),
        // Absent-in-file means "never set", which should behave like
        // the pre-setting default of on. `get_bool` defaults to false,
        // so branch on presence explicitly here.
        tracker_always_on_top: obj
            .get(KEY_TRACKER_ALWAYS_ON_TOP)
            .and_then(|v| v.as_bool())
            .unwrap_or(DEFAULT_TRACKER_ALWAYS_ON_TOP),
        theme: get_string(obj, KEY_THEME).unwrap_or_else(|| DEFAULT_THEME.to_string()),
        toast_level: get_string(obj, KEY_TOAST_LEVEL)
            .unwrap_or_else(|| DEFAULT_TOAST_LEVEL.to_string()),
    }
}

fn apply_field(obj: &mut Map<String, Value>, key: &str, value: Option<String>) {
    let Some(value) = value else { return };
    if value.trim().is_empty() {
        obj.remove(key);
    } else {
        obj.insert(key.to_string(), Value::String(value));
    }
}

fn apply_bool(obj: &mut Map<String, Value>, key: &str, value: Option<bool>) {
    let Some(value) = value else { return };
    obj.insert(key.to_string(), Value::Bool(value));
}

fn apply_u16(obj: &mut Map<String, Value>, key: &str, value: Option<u16>) {
    let Some(value) = value else { return };
    obj.insert(key.to_string(), Value::from(value));
}

/// Write an arbitrary JSON value under `key` in the shared config.json.
/// Passing `None` removes the key. Preserves every other field the file
/// carries, matching the round-trip guarantee of `apply_patch`. Used by
/// callers that own their own schema (e.g. the custom save format list
/// lives with the level editor, not in `SharedConfig`).
pub fn apply_json_field(key: &str, value: Option<Value>) -> Result<(), String> {
    let path = config_path().ok_or_else(|| "no config directory".to_string())?;
    let mut obj = load_raw();
    match value {
        Some(v) => {
            obj.insert(key.to_string(), v);
        }
        None => {
            obj.remove(key);
        }
    }
    let serialized =
        serde_json::to_string_pretty(&Value::Object(obj)).map_err(|e| format!("encode: {e}"))?;
    atomic_write(&path, serialized.as_bytes())?;
    Ok(())
}

/// Reads a nested value at `path` from config.json (dot-separated,
/// e.g. `"trackers.category"`). Returns None if any segment is
/// missing or the leaf isn't an object where the caller expected
/// one. Used to round-trip nested `trackers.<name>` blocks without
/// duplicating each field as a top-level key.
pub fn get_nested(path: &[&str]) -> Option<Value> {
    let mut current = Value::Object(load_raw());
    for segment in path {
        current = current.as_object()?.get(*segment).cloned()?;
    }
    Some(current)
}

/// Writes a nested value at `path`, creating intermediate objects
/// as needed. Passing `None` removes the leaf; empty intermediate
/// objects are left in place so unrelated siblings aren't disturbed.
pub fn set_nested(path: &[&str], value: Option<Value>) -> Result<(), String> {
    if path.is_empty() {
        return Err("empty path".to_string());
    }
    let cfg_path = config_path().ok_or_else(|| "no config directory".to_string())?;
    let mut root = load_raw();

    // Walk down, creating objects along the way. Uses split_last so
    // the terminal segment is the write target.
    let (leaf, ancestors) = path.split_last().unwrap();
    let mut cursor = &mut root;
    for segment in ancestors {
        let entry = cursor
            .entry((*segment).to_string())
            .or_insert_with(|| Value::Object(Map::new()));
        if !entry.is_object() {
            *entry = Value::Object(Map::new());
        }
        cursor = entry.as_object_mut().unwrap();
    }
    match value {
        Some(v) => {
            cursor.insert(leaf.to_string(), v);
        }
        None => {
            cursor.remove(*leaf);
        }
    }

    let serialized =
        serde_json::to_string_pretty(&Value::Object(root)).map_err(|e| format!("encode: {e}"))?;
    atomic_write(&cfg_path, serialized.as_bytes())?;
    Ok(())
}

pub fn apply_patch(patch: ConfigPatch) -> Result<(), String> {
    let path = config_path().ok_or_else(|| "no config directory".to_string())?;
    let mut obj = load_raw();
    apply_field(&mut obj, KEY_INSTALL_DIR, patch.install_dir);
    apply_field(&mut obj, KEY_FYI_ROOT, patch.spelunky_fyi_root);
    apply_field(&mut obj, KEY_FYI_TOKEN, patch.spelunky_fyi_api_token);
    apply_field(&mut obj, KEY_PLAYLUNKY_VERSION, patch.playlunky_version);
    apply_bool(&mut obj, KEY_PLAYLUNKY_CONSOLE, patch.playlunky_console);
    apply_bool(&mut obj, KEY_PLAYLUNKY_OVERLUNKY, patch.playlunky_overlunky);
    apply_field(&mut obj, KEY_COMMAND_PREFIX, patch.command_prefix);
    apply_bool(&mut obj, KEY_PLAYLUNKY_SHORTCUT, patch.playlunky_shortcut);
    apply_field(&mut obj, KEY_LAST_TAB, patch.last_tab);
    apply_u16(&mut obj, KEY_TRACKER_PORT, patch.tracker_server_port);
    apply_bool(
        &mut obj,
        KEY_TRACKER_AUTO_START,
        patch.tracker_server_auto_start,
    );
    apply_field(&mut obj, KEY_TRACKER_COLOR_KEY, patch.tracker_color_key);
    apply_u16(&mut obj, KEY_TRACKER_FONT_SIZE, patch.tracker_font_size);
    apply_field(&mut obj, KEY_TRACKER_FONT_FAMILY, patch.tracker_font_family);
    apply_field(&mut obj, KEY_TRACKER_FONT_COLOR, patch.tracker_font_color);
    apply_u16(
        &mut obj,
        KEY_TRACKER_STROKE_WIDTH,
        patch.tracker_stroke_width,
    );
    apply_field(
        &mut obj,
        KEY_TRACKER_STROKE_COLOR,
        patch.tracker_stroke_color,
    );
    apply_field(&mut obj, KEY_TRACKER_OUTPUT_DIR, patch.tracker_output_dir);
    apply_bool(
        &mut obj,
        KEY_TRACKER_FILE_ENABLED,
        patch.tracker_file_enabled,
    );
    apply_bool(
        &mut obj,
        KEY_TRACKER_ALWAYS_ON_TOP,
        patch.tracker_always_on_top,
    );
    apply_field(&mut obj, KEY_THEME, patch.theme);
    apply_field(&mut obj, KEY_TOAST_LEVEL, patch.toast_level);

    let serialized =
        serde_json::to_string_pretty(&Value::Object(obj)).map_err(|e| format!("encode: {e}"))?;
    atomic_write(&path, serialized.as_bytes())?;
    Ok(())
}

#[tauri::command]
pub fn get_config() -> SharedConfig {
    load()
}

#[tauri::command]
pub fn set_config(patch: ConfigPatch) -> Result<(), String> {
    apply_patch(patch)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backup_corrupt_path_shape() {
        let p = std::path::Path::new(r"C:\Users\me\config.json");
        let b = backup_corrupt_path(p);
        let name = b.file_name().unwrap().to_string_lossy();
        assert!(name.starts_with("config.corrupt."));
        assert!(name.ends_with(".json"));
        // "config" + ".corrupt." + digits + ".json" -> 3+ dots.
        assert_eq!(name.matches('.').count(), 3);
    }

    // Round-trip parsing tests for the shared config.json. Tests drive
    // the map-taking `from_map` seam instead of a real file through
    // `load()`, which avoids filesystem contention.
    fn parse(json: &str) -> SharedConfig {
        let obj = serde_json::from_str::<Value>(json)
            .unwrap()
            .as_object()
            .cloned()
            .unwrap_or_default();
        from_map(&obj)
    }

    #[test]
    fn from_empty_object_yields_defaults() {
        // A missing file is parsed as no keys set. Rust defaults are
        // the map-missing fallbacks; assert the shape rather than
        // every field.
        let cfg = from_map(&Map::new());
        assert!(cfg.install_dir.is_none());
        assert!(cfg.playlunky_version.is_none());
        assert!(cfg.last_tab.is_none());
        assert!(!cfg.playlunky_console);
        // tracker_always_on_top must default to `true` so users who
        // upgrade past the setting land on the pre-setting behavior.
        assert!(cfg.tracker_always_on_top);
    }

    #[test]
    fn playlunky_version_present_is_read() {
        let cfg = parse(r#"{"playlunky-version": "latest"}"#);
        assert_eq!(cfg.playlunky_version.as_deref(), Some("latest"));
    }

    #[test]
    fn install_dir_null_is_none_not_error() {
        // Legacy writers store null when the user hasn't picked an
        // install dir yet. Reading that back must produce None, not
        // an error or a `Some("")`.
        let cfg = parse(r#"{"install-dir": null}"#);
        assert!(cfg.install_dir.is_none());
    }

    #[test]
    fn last_tab_null_is_none_not_error() {
        let cfg = parse(r#"{"last-tab": null}"#);
        assert!(cfg.last_tab.is_none());
    }

    #[test]
    fn atomic_write_replaces_existing_file() {
        let dir = std::env::temp_dir().join(format!(
            "modlunky2-config-test-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let target = dir.join("config.json");
        std::fs::write(&target, b"original").unwrap();

        atomic_write(&target, b"replacement").unwrap();

        assert_eq!(std::fs::read(&target).unwrap(), b"replacement");
        // Tmp sidecar must not linger.
        let tmp = {
            let mut s = target.as_os_str().to_owned();
            s.push(".tmp");
            PathBuf::from(s)
        };
        assert!(!tmp.exists(), "tmp file should be renamed away");

        let _ = std::fs::remove_dir_all(&dir);
    }
}
