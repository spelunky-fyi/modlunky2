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
/// Name of the release asset we install. We resolve its versioned
/// `browser_download_url` from the API response rather than hitting the
/// `latest/download/<name>` web redirect, whose CDN cache can lag the API and
/// hand back the previous release's exe.
const EXE_ASSET_NAME: &str = "modlunky2.exe";

// ---------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------

/// What the frontend needs to render the update state. A missing
/// `latest` means the GitHub request failed (offline, rate-limited);
/// `check_error` then carries the reason so the UI can say "couldn't
/// check" instead of silently looking identical to "up to date".
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ModlunkyVersionInfo {
    pub current: String,
    pub latest: Option<String>,
    pub update_available: bool,
    /// GitHub releases page for the manual-download fallback if the
    /// in-place swap fails (locked file, weird permissions).
    pub release_page_url: &'static str,
    /// Why the latest-release lookup failed, when it did. `None` on success.
    pub check_error: Option<String>,
}

#[tauri::command]
pub async fn get_modlunky_version() -> Result<ModlunkyVersionInfo, String> {
    let current = env!("CARGO_PKG_VERSION").to_string();
    let (latest, check_error) = match fetch_latest_release().await {
        Ok(release) => (Some(release.tag), None),
        Err(e) => {
            // Log so a user who never sees the update pill has something to
            // find; the check is otherwise invisible when it fails.
            tracing::warn!("update check failed: {e}");
            (None, Some(e))
        }
    };
    let update_available = latest
        .as_ref()
        .map(|l| version_is_newer(l, &current))
        .unwrap_or(false);
    tracing::debug!(
        "update check: current={current} latest={latest:?} update_available={update_available}"
    );
    Ok(ModlunkyVersionInfo {
        current,
        latest,
        update_available,
        release_page_url: GITHUB_LATEST_URL,
        check_error,
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
    // Resolve the exact release we're about to install and pin the download to
    // that release's asset, so the bytes we write match the version we
    // advertised. The old code read the version from the API but downloaded
    // from the `latest/download` web redirect, and the two are cached
    // independently: the redirect could serve the previous release's exe while
    // the API already reported the new tag. That left the app "updating" to the
    // same old build on a loop.
    let release = fetch_latest_release()
        .await
        .map_err(|e| format!("couldn't reach GitHub to resolve the latest release: {e}"))?;

    // Only install when GitHub's latest is genuinely newer than what's running.
    // Guards against the loop above: even if a stale response points at an old
    // release, we refuse rather than reinstall it.
    let current = env!("CARGO_PKG_VERSION");
    if !version_is_newer(&release.tag, current) {
        return Err(format!(
            "already up to date (latest is {}, running {current})",
            release.tag
        ));
    }

    let exe_url = release
        .exe_url
        .ok_or_else(|| format!("release {} has no {EXE_ASSET_NAME} asset", release.tag))?;

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

    // 2. Stream the pinned asset to the original path.
    if let Err(e) = download_to(&exe_url, &self_exe).await {
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

/// The one release we resolve up front, so the version we show and the bytes
/// we download come from the same object.
struct LatestRelease {
    /// `tag_name`, e.g. `"v2.0.14"` or `"2.0.14"`.
    tag: String,
    /// Pinned, versioned download URL for [`EXE_ASSET_NAME`] (e.g.
    /// `.../releases/download/v2.0.14/modlunky2.exe`). `None` if that release
    /// has no such asset.
    exe_url: Option<String>,
}

async fn fetch_latest_release() -> Result<LatestRelease, String> {
    let client = reqwest::Client::builder()
        .user_agent(user_agent())
        .build()
        .map_err(|e| format!("build http client: {e}"))?;
    let resp = client
        .get(GITHUB_LATEST_API_URL)
        .send()
        .await
        .map_err(|e| format!("request to GitHub failed: {e}"))?;
    let status = resp.status();
    if !status.is_success() {
        // Rate limiting is the most common silent failure: GitHub's
        // unauthenticated API allows only 60 requests/hour per IP, which a
        // shared/corporate NAT can exhaust. Call it out explicitly.
        let hint = if status.as_u16() == 403 || status.as_u16() == 429 {
            " (GitHub API rate limit or blocked; the unauthenticated limit is 60 requests/hour per IP)"
        } else {
            ""
        };
        return Err(format!("GitHub API returned HTTP {status}{hint}"));
    }
    let json: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("parse GitHub response: {e}"))?;
    let tag = json
        .get("tag_name")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "GitHub response had no tag_name".to_string())?
        .to_string();
    let exe_url = exe_asset_url(&json, EXE_ASSET_NAME);
    Ok(LatestRelease { tag, exe_url })
}

/// Pull the `browser_download_url` of the named asset out of a release JSON
/// object. Matching is case-insensitive so `Modlunky2.exe` still resolves.
fn exe_asset_url(release: &serde_json::Value, asset_name: &str) -> Option<String> {
    release.get("assets")?.as_array()?.iter().find_map(|asset| {
        let name = asset.get("name")?.as_str()?;
        if name.eq_ignore_ascii_case(asset_name) {
            asset
                .get("browser_download_url")?
                .as_str()
                .map(String::from)
        } else {
            None
        }
    })
}

async fn download_to(url: &str, dest: &std::path::Path) -> Result<(), String> {
    let client = reqwest::Client::builder()
        .user_agent(user_agent())
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let resp = client
        .get(url)
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

    #[test]
    fn exe_asset_url_pins_to_the_versioned_asset() {
        // Shape mirrors the GitHub "get latest release" payload. The pinned
        // url must be the versioned one, not the `latest/download` redirect.
        let release = serde_json::json!({
            "tag_name": "v2.0.14",
            "assets": [
                { "name": "some-other.zip", "browser_download_url": "https://example/other.zip" },
                {
                    "name": "modlunky2.exe",
                    "browser_download_url":
                        "https://github.com/spelunky-fyi/modlunky2/releases/download/v2.0.14/modlunky2.exe"
                }
            ]
        });
        assert_eq!(
            exe_asset_url(&release, EXE_ASSET_NAME).as_deref(),
            Some(
                "https://github.com/spelunky-fyi/modlunky2/releases/download/v2.0.14/modlunky2.exe"
            )
        );
    }

    #[test]
    fn exe_asset_url_is_case_insensitive() {
        let release = serde_json::json!({
            "assets": [
                { "name": "Modlunky2.EXE", "browser_download_url": "https://example/m.exe" }
            ]
        });
        assert_eq!(
            exe_asset_url(&release, EXE_ASSET_NAME).as_deref(),
            Some("https://example/m.exe")
        );
    }

    #[test]
    fn exe_asset_url_none_when_asset_missing() {
        let release = serde_json::json!({
            "assets": [
                { "name": "checksums.txt", "browser_download_url": "https://example/c.txt" }
            ]
        });
        assert_eq!(exe_asset_url(&release, EXE_ASSET_NAME), None);

        // Also None when there's no assets array at all.
        let empty = serde_json::json!({ "tag_name": "v2.0.14" });
        assert_eq!(exe_asset_url(&empty, EXE_ASSET_NAME), None);
    }
}
