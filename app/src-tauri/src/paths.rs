// Known modlunky2 directories, plus the commands to open them in the OS file
// manager or auto-detect the Spelunky 2 install location.

use std::path::PathBuf;

use directories::BaseDirs;
use serde::{Deserialize, Serialize};
use tauri_plugin_opener::OpenerExt;

const EXE_NAME: &str = "Spel2.exe";
const DEFAULT_INSTALL: &str = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Spelunky 2";

#[derive(Copy, Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum DirectoryKind {
    Install,
    Packs,
    Extracted,
    AppData,
    AppCache,
    Trackers,
}

fn app_base() -> Option<PathBuf> {
    Some(
        BaseDirs::new()?
            .data_local_dir()
            .join("spelunky.fyi")
            .join("modlunky2"),
    )
}

/// Modlunky's app cache directory (`.../modlunky2/Cache`), independent of the
/// game install. `None` when no home directory is resolvable.
pub fn app_cache_dir() -> Option<PathBuf> {
    resolve(DirectoryKind::AppCache, None)
}

fn resolve(kind: DirectoryKind, install_dir: Option<PathBuf>) -> Option<PathBuf> {
    let base = app_base();
    match kind {
        DirectoryKind::Install => install_dir,
        DirectoryKind::Packs => install_dir.map(|p| p.join("Mods").join("Packs")),
        DirectoryKind::Extracted => install_dir.map(|p| p.join("Mods").join("Extracted")),
        DirectoryKind::AppData => base,
        DirectoryKind::AppCache => base.map(|p| p.join("Cache")),
        DirectoryKind::Trackers => base.map(|p| p.join("trackers")),
    }
}

#[cfg(windows)]
fn guess_install_from_registry() -> Option<PathBuf> {
    use winreg::RegKey;
    use winreg::enums::HKEY_LOCAL_MACHINE;

    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
    let uninstall = hklm
        .open_subkey("Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall")
        .ok()?;

    for key_name in uninstall.enum_keys().flatten() {
        let Ok(subkey) = uninstall.open_subkey(&key_name) else {
            continue;
        };
        let display_name: String = match subkey.get_value("DisplayName") {
            Ok(v) => v,
            Err(_) => continue,
        };
        if display_name == "Spelunky 2" {
            let location: String = subkey.get_value("InstallLocation").ok()?;
            return Some(PathBuf::from(location));
        }
    }
    None
}

#[cfg(not(windows))]
fn guess_install_from_registry() -> Option<PathBuf> {
    None
}

#[tauri::command]
pub fn guess_install_dir() -> Option<PathBuf> {
    let default = PathBuf::from(DEFAULT_INSTALL);
    if default.join(EXE_NAME).exists() {
        return Some(default);
    }
    let reg = guess_install_from_registry()?;
    if reg.join(EXE_NAME).exists() {
        Some(reg)
    } else {
        None
    }
}

#[tauri::command]
pub fn open_directory<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    kind: DirectoryKind,
) -> Result<(), String> {
    let install_dir = crate::config::load().install_dir;
    let target = resolve(kind, install_dir)
        .ok_or_else(|| "That directory is not available yet.".to_string())?;
    if !target.exists() {
        std::fs::create_dir_all(&target).map_err(|e| format!("mkdir: {e}"))?;
    }
    app.opener()
        .open_path(target.to_string_lossy(), None::<&str>)
        .map_err(|e| e.to_string())
}
