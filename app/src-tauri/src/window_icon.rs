//! Set crisp per-size taskbar + titlebar icons on Windows.
//!
//! Tauri's default window-icon path on Windows decodes `icon.ico` via
//! the `image` crate, which picks the largest embedded frame (96x96
//! for this app), then hands the same single-size HICON to Windows as
//! both `ICON_SMALL` and `ICON_BIG`. Windows scales that 96x96 down
//! to 16x16 for the titlebar with its default filter and the result
//! is a soft, blurred glyph. The desktop shortcut looks crisp because
//! it renders from the exe's embedded ICON resource, which Windows
//! shell walks per size and picks the closest hand-tuned frame.
//!
//! This module replicates that behavior at window-creation time:
//! `LoadImageW` with `LR_LOADFROMFILE` at explicit 16x16 and 32x32
//! sizes lets Windows pick the right frame directly out of the ICO,
//! then `WM_SETICON` sets each slot separately.
//!
//! Non-Windows targets get a no-op stub.

#[cfg(windows)]
mod imp {
    use std::path::PathBuf;
    use std::sync::OnceLock;

    use tauri::{Runtime, WebviewWindow};

    /// The multi-frame ICO shipped in `icons/icon.ico`. Embedded at
    /// compile time so `LoadImageW` can point at a real file path without
    /// depending on the exe layout at runtime.
    const ICON_BYTES: &[u8] = include_bytes!("../icons/icon.ico");

    /// Path to the extracted ICO on disk. Written once per process to a
    /// pid-suffixed temp file so parallel dev + release runs on the same
    /// box don't fight over the same handle.
    static ICO_PATH: OnceLock<PathBuf> = OnceLock::new();

    fn ensure_ico_extracted() -> std::io::Result<PathBuf> {
        if let Some(p) = ICO_PATH.get() {
            return Ok(p.clone());
        }
        let path = std::env::temp_dir().join(format!("modlunky2-icon-{}.ico", std::process::id()));
        std::fs::write(&path, ICON_BYTES)?;
        Ok(ICO_PATH.get_or_init(|| path).clone())
    }

    pub fn apply_window_icon<R: Runtime>(window: &WebviewWindow<R>) -> anyhow::Result<()> {
        use windows::Win32::Foundation::{HWND, LPARAM, WPARAM};
        use windows::Win32::UI::WindowsAndMessaging::{
            HICON, ICON_BIG, ICON_SMALL, IMAGE_ICON, LR_DEFAULTCOLOR, LR_LOADFROMFILE, LoadImageW,
            SendMessageW, WM_SETICON,
        };
        use windows::core::PCWSTR;

        let ico_path = ensure_ico_extracted()?;
        let path_wide: Vec<u16> = ico_path
            .as_os_str()
            .to_string_lossy()
            .encode_utf16()
            .chain(std::iter::once(0))
            .collect();

        // Tauri v2's hwnd() returns the raw handle Windows uses. Rewrap
        // into this crate's HWND newtype so the version bump on the
        // `windows` crate stays isolated to this module.
        let raw = window.hwnd()?;
        let hwnd = HWND(raw.0 as *mut _);

        unsafe {
            let small = LoadImageW(
                None,
                PCWSTR(path_wide.as_ptr()),
                IMAGE_ICON,
                16,
                16,
                LR_LOADFROMFILE | LR_DEFAULTCOLOR,
            )?;
            let big = LoadImageW(
                None,
                PCWSTR(path_wide.as_ptr()),
                IMAGE_ICON,
                32,
                32,
                LR_LOADFROMFILE | LR_DEFAULTCOLOR,
            )?;
            // Return value of WM_SETICON is the previous icon handle,
            // which Tauri owns. Dropping it here would double-free; the
            // OS reclaims when the window is destroyed.
            let _ = SendMessageW(
                hwnd,
                WM_SETICON,
                Some(WPARAM(ICON_SMALL as usize)),
                Some(LPARAM(HICON(small.0 as *mut _).0 as isize)),
            );
            let _ = SendMessageW(
                hwnd,
                WM_SETICON,
                Some(WPARAM(ICON_BIG as usize)),
                Some(LPARAM(HICON(big.0 as *mut _).0 as isize)),
            );
        }
        Ok(())
    }
}

#[cfg(not(windows))]
mod imp {
    use tauri::{Runtime, WebviewWindow};

    pub fn apply_window_icon<R: Runtime>(_window: &WebviewWindow<R>) -> anyhow::Result<()> {
        Ok(())
    }
}

pub use imp::apply_window_icon;
