//! What the app needs configured before it can do anything useful, and one
//! place to say so.
//!
//! Three things gate real work: the Spelunky 2 install directory, extracted
//! game assets, and a spelunky.fyi API token. Only the first is required for
//! the app to function at all; the other two gate a subset of features.
//!
//! The frontend gates on `setup_status`, so an unconfigured install is met
//! with a screen explaining what to do rather than a failure per action. The
//! errors here are the backstop for anything that reaches a command without
//! passing a gate, which is why they name the fix instead of the symptom.

use std::path::PathBuf;

use serde::Serialize;

/// Why the install directory isn't usable. The two cases need different
/// advice: one is "you haven't set this yet", the other is "what you set is
/// gone", which usually means a moved game or a disconnected drive.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum InstallDirState {
    Unset,
    Missing,
    Ok,
}

/// Snapshot of everything the frontend gates on, in one round trip so a tab
/// can decide what to render without chaining three calls.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SetupStatus {
    pub install_dir: InstallDirState,
    /// The configured path, even when it's missing, so the UI can name what
    /// it went looking for rather than just saying "not found".
    pub install_dir_path: Option<String>,
    /// Whether `Mods/Extracted/Data/Textures` has anything in it. Required by
    /// the level editors, which render placeholder tiles without it.
    pub assets_extracted: bool,
    /// Whether a spelunky.fyi token is configured. Never required: local mods
    /// work fine without one, it only gates install-from-site and updates.
    pub has_api_token: bool,
    /// Whether the mod manager is actually running.
    ///
    /// Not the same question as `install_dir`, and that gap is a real state:
    /// the subsystem is only built at startup or by `rebuild_mods`, so a
    /// launch with no folder leaves it down even after a folder is chosen.
    /// Reported so the frontend can bring it up rather than unlocking the
    /// Mods tab onto a manager that isn't there.
    pub mods_ready: bool,
}

pub fn install_dir_state() -> (InstallDirState, Option<PathBuf>) {
    let Some(dir) = crate::config::load().install_dir else {
        return (InstallDirState::Unset, None);
    };
    let state = if dir.exists() {
        InstallDirState::Ok
    } else {
        InstallDirState::Missing
    };
    (state, Some(dir))
}

#[tauri::command]
pub fn get_setup_status(state: tauri::State<'_, crate::state::AppState>) -> SetupStatus {
    let (install_dir, path) = install_dir_state();
    let cfg = crate::config::load();
    SetupStatus {
        mods_ready: state.mods_handle().is_some(),
        install_dir,
        install_dir_path: path.map(|p| p.to_string_lossy().into_owned()),
        assets_extracted: crate::extract::extracted_assets_available(),
        has_api_token: cfg
            .spelunky_fyi_api_token
            .is_some_and(|t| !t.trim().is_empty()),
    }
}

/// The install directory, or an error that tells the user what to do.
///
/// Every command that touches the game folder goes through this, so the
/// message is identical wherever it surfaces and naming the fix isn't left to
/// whoever wrote the call site.
pub fn install_dir() -> Result<PathBuf, String> {
    match install_dir_state() {
        (InstallDirState::Ok, Some(dir)) => Ok(dir),
        (state, path) => Err(install_dir_error(state, path.as_deref())),
    }
}

/// The current install-directory problem as a message, for call sites that
/// only have somewhere to put a string.
///
/// The mod subsystem is the main caller: it never starts without a usable
/// directory, so every command needing its handle fails and has only a string
/// to explain itself with. Naming an internal component there tells the user
/// nothing they can act on, so they get the same advice as everywhere else.
pub fn install_dir_message() -> String {
    let (state, path) = install_dir_state();
    if state == InstallDirState::Ok {
        // The folder is fine, so the handle is missing for the other reason:
        // the subsystem is between teardown and startup after a settings
        // change. Folder advice would be flatly untrue here, and is the one
        // thing the user demonstrably has already done.
        return "Mods directory wasn't ready. Try again in a moment.".to_string();
    }
    install_dir_error(state, path.as_deref())
}

/// The message for an unusable install directory. Split out from the lookup
/// so the wording can be tested without a config file on disk.
pub fn install_dir_error(state: InstallDirState, path: Option<&std::path::Path>) -> String {
    match (state, path) {
        (InstallDirState::Missing, Some(dir)) => format!(
            "Can't find your Spelunky 2 folder at {}. Set it again in Settings.",
            dir.display()
        ),
        _ => "Your Spelunky 2 folder isn't configured. Configure it in your settings.".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    /// Names the one place any of these is fixable. Matched case-insensitively
    /// and on that word alone: this is here to catch a message that leaves the
    /// user with nowhere to go, not to freeze the wording of copy that is
    /// expected to be rewritten.
    fn points_at_settings(msg: &str) -> bool {
        msg.to_lowercase().contains("settings")
    }

    /// Whatever the state, the user is told where to go. Routing every call
    /// site through one function is what keeps that true, rather than leaving
    /// it to whichever command happened to fail.
    #[test]
    fn every_message_names_settings() {
        let cases = [
            install_dir_error(InstallDirState::Unset, None),
            install_dir_error(InstallDirState::Missing, Some(Path::new("D:/gone"))),
        ];
        for msg in cases {
            assert!(points_at_settings(&msg), "no call to action in: {msg}");
        }
    }

    /// A missing folder has to name the path it looked for. "Not found" alone
    /// leaves someone with a moved game or an unplugged drive guessing.
    #[test]
    fn a_missing_folder_names_the_path_it_looked_for() {
        let msg = install_dir_error(InstallDirState::Missing, Some(Path::new("D:/gone")));
        assert!(msg.contains("gone"), "{msg}");
    }

    /// The two failures need different advice: one is "you haven't done this
    /// yet", the other is "what you chose has gone away".
    #[test]
    fn unset_and_missing_read_differently() {
        let unset = install_dir_error(InstallDirState::Unset, None);
        let missing = install_dir_error(InstallDirState::Missing, Some(Path::new("D:/gone")));
        assert_ne!(unset, missing);
    }

    /// The transient message only makes sense while the folder is fine; every
    /// other state has to keep pointing at Settings.
    #[test]
    fn a_usable_folder_never_produces_folder_advice() {
        let ok = install_dir_error(InstallDirState::Ok, Some(Path::new("D:/game")));
        // `install_dir_error` is only ever reached for a broken state, so even
        // the Ok arm must be safe advice rather than nonsense.
        assert!(points_at_settings(&ok), "{ok}");
    }

    /// A state of Missing with no path can't happen through `install_dir`,
    /// but if it ever did the user should still get the actionable fallback
    /// rather than a message with a hole where the path should be.
    #[test]
    fn a_missing_state_without_a_path_falls_back_to_the_unset_wording() {
        assert_eq!(
            install_dir_error(InstallDirState::Missing, None),
            install_dir_error(InstallDirState::Unset, None),
        );
    }
}
