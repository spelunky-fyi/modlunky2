//! Self-update: rename the running EXE aside, download the new EXE
//! over the old path, spawn it, exit. Works because Windows lets a
//! running EXE be renamed even though it can't be overwritten.
//!
//! No signature check because the binary isn't signed. SmartScreen
//! click-through is expected on the first run of every version.

use std::path::PathBuf;

use serde::Serialize;

const GITHUB_LATEST_URL: &str = "https://github.com/spelunky-fyi/modlunky2/releases/latest";
const GITHUB_LATEST_API_URL: &str =
    "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest";
const LATEST_EXE_URL: &str =
    "https://github.com/spelunky-fyi/modlunky2/releases/latest/download/modlunky2.exe";

// ---------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------

/// What the frontend needs to render the update state. A missing
/// `latest` means the GitHub request failed (offline, rate-limited);
/// UI silently hides the pill in that case.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ModlunkyVersionInfo {
    pub current: String,
    pub latest: Option<String>,
    pub update_available: bool,
    /// GitHub releases page for the manual-download fallback if the
    /// in-place swap fails (locked file, weird permissions).
    pub release_page_url: &'static str,
}

#[tauri::command]
pub async fn get_modlunky_version() -> Result<ModlunkyVersionInfo, String> {
    let current = env!("CARGO_PKG_VERSION").to_string();
    let latest = fetch_latest_version().await;
    let update_available = latest
        .as_ref()
        .map(|l| version_is_newer(l, &current))
        .unwrap_or(false);
    Ok(ModlunkyVersionInfo {
        current,
        latest,
        update_available,
        release_page_url: GITHUB_LATEST_URL,
    })
}

/// Renames the current exe aside, downloads the latest release into
/// the original path, spawns the new one, asks Tauri to exit.
///
/// Rollback: if the download fails after the rename, moves the
/// backup back so the user isn't stranded without an exe. If the
/// rename itself fails, nothing else happens.
#[tauri::command]
pub async fn install_update(app: tauri::AppHandle) -> Result<(), String> {
    let self_exe = std::env::current_exe().map_err(|e| format!("resolve current exe: {e}"))?;

    // 1. Move the current exe aside. Renaming an in-use exe is legal
    // on Windows even though overwriting one isn't.
    let backup = backup_path_for(&self_exe);
    if backup.exists() {
        // A previous update crashed after the rename; clear it. If it
        // can't be cleared (locked handle, permissions), the rename
        // below fails and surfaces the underlying error.
        let _ = std::fs::remove_file(&backup);
    }
    std::fs::rename(&self_exe, &backup)
        .map_err(|e| format!("rename current exe to backup: {e}"))?;

    // 2. Stream the download to the original path.
    if let Err(e) = download_latest(&self_exe).await {
        // Roll back so the user isn't stranded.
        let _ = std::fs::rename(&backup, &self_exe);
        return Err(format!("download update: {e}"));
    }

    // 3. Spawn the new exe, then exit.
    if let Err(e) = std::process::Command::new(&self_exe).spawn() {
        return Err(format!("spawn new exe: {e}"));
    }
    app.exit(0);
    Ok(())
}

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

fn user_agent() -> String {
    format!("modlunky2/{}", env!("CARGO_PKG_VERSION"))
}

async fn fetch_latest_version() -> Option<String> {
    let client = reqwest::Client::builder()
        .user_agent(user_agent())
        .build()
        .ok()?;
    let resp = client.get(GITHUB_LATEST_API_URL).send().await.ok()?;
    if !resp.status().is_success() {
        return None;
    }
    let json: serde_json::Value = resp.json().await.ok()?;
    json.get("tag_name")?.as_str().map(String::from)
}

async fn download_latest(dest: &std::path::Path) -> Result<(), String> {
    let client = reqwest::Client::builder()
        .user_agent(user_agent())
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let resp = client
        .get(LATEST_EXE_URL)
        .send()
        .await
        .map_err(|e| format!("send: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("http status {}", resp.status()));
    }
    let bytes = resp.bytes().await.map_err(|e| format!("body: {e}"))?;
    std::fs::write(dest, &bytes).map_err(|e| format!("write: {e}"))?;
    Ok(())
}

/// `foo.exe` -> `foo.backup.exe`; anything without an extension
/// gets `<name>.backup`.
fn backup_path_for(exe: &std::path::Path) -> PathBuf {
    let stem = exe
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "modlunky2".to_string());
    let ext = exe
        .extension()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let filename = if ext.is_empty() {
        format!("{stem}.backup")
    } else {
        format!("{stem}.backup.{ext}")
    };
    exe.with_file_name(filename)
}

/// Compare tag_name against the compiled-in version. Strips a
/// leading `v`, splits on `.`, compares numeric components. Non-
/// numeric suffixes sort after their numeric prefix.
fn version_is_newer(candidate: &str, current: &str) -> bool {
    let cand = strip_v(candidate);
    let cur = strip_v(current);
    let mut a = version_parts(cand);
    let mut b = version_parts(cur);
    while a.len() < b.len() {
        a.push(0);
    }
    while b.len() < a.len() {
        b.push(0);
    }
    a > b
}

fn strip_v(s: &str) -> &str {
    s.strip_prefix('v').unwrap_or(s)
}

fn version_parts(s: &str) -> Vec<u64> {
    s.split(|c: char| !c.is_ascii_digit() && c != '.')
        .next()
        .unwrap_or("")
        .split('.')
        .filter_map(|p| p.parse::<u64>().ok())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_is_newer_semver() {
        assert!(version_is_newer("0.10.5", "0.10.4"));
        assert!(version_is_newer("1.0.0", "0.99.99"));
        assert!(!version_is_newer("0.10.4", "0.10.5"));
        assert!(!version_is_newer("0.10.5", "0.10.5"));
        assert!(!version_is_newer("1.2", "1.2.0"));
        assert!(version_is_newer("v1.2.3", "1.2.2"));
    }

    #[test]
    fn backup_path_ends_in_dot_backup() {
        let p = PathBuf::from(r"C:\Users\me\modlunky2.exe");
        assert_eq!(
            backup_path_for(&p),
            PathBuf::from(r"C:\Users\me\modlunky2.backup.exe")
        );
    }
}
