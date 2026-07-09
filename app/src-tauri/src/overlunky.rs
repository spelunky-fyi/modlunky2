// Overlunky launcher. Unlike Playlunky, Overlunky has no version selection or
// release list, just a single rolling "whip" build fetched from GitHub and
// dropped into <install_dir>/Overlunky/. Launch supports three modes:
// inject into a running game, launch vanilla with Overlunky attached, or
// reconfigure Overlunky's own auto-updater.

use std::io::Cursor;
use std::path::PathBuf;
use std::time::{Duration, Instant};

use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Runtime};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const WHIP_ZIP_URL: &str =
    "https://github.com/spelunky-fyi/overlunky/releases/download/whip/Overlunky_WHIP.zip";
const OVERLUNKY_SUBDIR: &str = "Overlunky";
const OVERLUNKY_EXE: &str = "Overlunky.exe";
const USER_AGENT: &str = concat!("modlunky2/", env!("CARGO_PKG_VERSION"));
const DOWNLOAD_PROGRESS_EVENT: &str = "overlunky-download-progress";
/// IPC throttle. Chunks arrive every few ms so an event per chunk would
/// spam the frontend; 100ms is fast enough for a smooth bar without
/// pinning a core on the event bus.
const DOWNLOAD_PROGRESS_MIN_INTERVAL: Duration = Duration::from_millis(100);

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DownloadProgress {
    phase: &'static str,
    /// Bytes received so far. Reset to 0 at the start of each phase.
    done: u64,
    /// None until the `Content-Length` response header lands (some
    /// GitHub CDN edges omit it), then Some for the rest of the run.
    total: Option<u64>,
}

fn emit_download_progress<R: Runtime>(
    app: &AppHandle<R>,
    phase: &'static str,
    done: u64,
    total: Option<u64>,
) {
    let _ = app.emit(
        DOWNLOAD_PROGRESS_EVENT,
        DownloadProgress { phase, done, total },
    );
}

// Windows CreateProcess flag. Overlunky expects a console window when the
// --console arg is used; without this flag stdout ends up detached.
#[cfg(windows)]
const CREATE_NEW_CONSOLE: u32 = 0x00000010;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum LaunchMode {
    /// --console only, attaches to a running Spelunky 2 process.
    Inject,
    /// --console --launch_game <install_dir>, starts vanilla Spel2.exe with
    /// Overlunky already attached so no timing race.
    LaunchGame,
    /// --update, hands off to Overlunky's own auto-updater UI.
    Update,
}

fn install_dir_required() -> Result<PathBuf, String> {
    let dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    if !dir.exists() {
        return Err(format!(
            "install directory does not exist: {}",
            dir.display()
        ));
    }
    Ok(dir)
}

fn overlunky_exe_path(install_dir: &std::path::Path) -> PathBuf {
    install_dir.join(OVERLUNKY_SUBDIR).join(OVERLUNKY_EXE)
}

#[tauri::command]
pub fn is_overlunky_installed() -> bool {
    let Ok(dir) = install_dir_required() else {
        return false;
    };
    overlunky_exe_path(&dir).exists()
}

/// Downloads the whip zip from GitHub and extracts every entry directly into
/// install_dir. The archive is laid out with a top-level Overlunky/ folder
/// that ml2_mods style path traversal protection keeps honest via
/// enclosed_name(). Overlunky's own script bundle rides along. Emits
/// `overlunky-download-progress` events (throttled) while streaming so the
/// UI can show a real progress bar.
#[tauri::command]
pub async fn download_overlunky<R: Runtime>(app: AppHandle<R>) -> Result<(), String> {
    let install_dir = install_dir_required()?;

    let client = reqwest::Client::builder()
        .user_agent(USER_AGENT)
        .connect_timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    emit_download_progress(&app, "downloading", 0, None);
    let resp = client
        .get(WHIP_ZIP_URL)
        .send()
        .await
        .map_err(|e| format!("download: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("download responded {}", resp.status()));
    }

    let total_bytes = resp.content_length();

    // Overlunky's whip zip is under 20 MB, memory-buffer it before extracting.
    let mut buf: Vec<u8> = Vec::with_capacity(
        total_bytes
            .and_then(|n| usize::try_from(n).ok())
            .unwrap_or(0),
    );
    let mut stream = resp.bytes_stream();
    let mut last_emit = Instant::now() - DOWNLOAD_PROGRESS_MIN_INTERVAL;
    while let Some(chunk) = stream.next().await {
        let bytes = chunk.map_err(|e| format!("read stream: {e}"))?;
        buf.extend_from_slice(&bytes);
        if last_emit.elapsed() >= DOWNLOAD_PROGRESS_MIN_INTERVAL {
            emit_download_progress(&app, "downloading", buf.len() as u64, total_bytes);
            last_emit = Instant::now();
        }
    }
    // Final "downloading" tick so the bar always ends at 100% before
    // flipping to the extract phase.
    emit_download_progress(&app, "downloading", buf.len() as u64, total_bytes);

    emit_download_progress(&app, "extracting", 0, None);
    let mut archive =
        zip::ZipArchive::new(Cursor::new(buf)).map_err(|e| format!("open zip: {e}"))?;
    for i in 0..archive.len() {
        let mut file = archive
            .by_index(i)
            .map_err(|e| format!("read entry {i}: {e}"))?;
        let Some(name) = file.enclosed_name() else {
            continue;
        };
        let dest = install_dir.join(&name);
        if file.is_dir() {
            std::fs::create_dir_all(&dest).map_err(|e| format!("mkdir {}: {e}", dest.display()))?;
            continue;
        }
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
        }
        let mut out =
            std::fs::File::create(&dest).map_err(|e| format!("create {}: {e}", dest.display()))?;
        std::io::copy(&mut file, &mut out).map_err(|e| format!("write {}: {e}", dest.display()))?;
    }
    emit_download_progress(&app, "done", 0, None);

    Ok(())
}

/// Spawns Overlunky.exe with the args for the requested mode. Fire and
/// forget: Overlunky owns its own console and its lifetime is independent of
/// the modlunky2 app.
#[tauri::command]
pub fn launch_overlunky<R: Runtime>(
    _app: tauri::AppHandle<R>,
    mode: LaunchMode,
) -> Result<(), String> {
    let install_dir = install_dir_required()?;
    let exe = overlunky_exe_path(&install_dir);
    if !exe.exists() {
        return Err("Overlunky is not installed. Download the WHIP build first.".to_string());
    }

    let mut args: Vec<String> = Vec::new();
    match mode {
        LaunchMode::Inject => {
            args.push("--console".to_string());
        }
        LaunchMode::LaunchGame => {
            args.push("--console".to_string());
            args.push("--launch_game".to_string());
            args.push(install_dir.display().to_string());
        }
        LaunchMode::Update => {
            args.push("--update".to_string());
        }
    }

    // command_prefix wraps the whole invocation, same shape as Playlunky.
    let prefix_tokens: Vec<String> = crate::config::load()
        .command_prefix
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .and_then(|s| shell_words::split(s).ok())
        .unwrap_or_default();

    let cwd = exe
        .parent()
        .ok_or_else(|| "Overlunky exe has no parent dir".to_string())?;

    let spawn = if let Some((head, tail)) = prefix_tokens.split_first() {
        let mut cmd = std::process::Command::new(head);
        cmd.args(tail).arg(&exe).args(&args).current_dir(cwd);
        #[cfg(windows)]
        cmd.creation_flags(CREATE_NEW_CONSOLE);
        cmd.spawn()
    } else {
        let mut cmd = std::process::Command::new(&exe);
        cmd.args(&args).current_dir(cwd);
        #[cfg(windows)]
        cmd.creation_flags(CREATE_NEW_CONSOLE);
        cmd.spawn()
    };
    spawn.map_err(|e| format!("spawn Overlunky.exe: {e}"))?;
    Ok(())
}
