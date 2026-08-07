//! How to run a Windows executable on whatever platform modlunky2 is on.
//!
//! Everything modlunky2 launches (the game, Playlunky, Overlunky) is a
//! Windows executable. On Windows that's just running it. On Linux it has to
//! go through Proton, in the game's own prefix. Both callers want the same
//! thing, so they build their command through [`command_for_exe`] and only
//! deal with args and working directory themselves.

use std::path::Path;
use std::process::Command;

#[cfg(target_os = "linux")]
pub use crate::proton::PrefixState;

/// Off Linux there is no prefix, but callers still say what they mean so the
/// call sites read the same everywhere.
#[cfg(not(target_os = "linux"))]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PrefixState {
    Fresh,
    Live,
}

/// Builds the command that runs `exe`, with the executable already appended,
/// so callers add their arguments straight on top.
///
/// The working directory defaults to the executable's own directory. That is
/// what all three callers want, and more importantly it means forgetting to
/// set one can't leave the game inheriting modlunky2's cwd: Spelunky 2 writes
/// `savegame.sav`, `settings.cfg`, `input.cfg` and `local.cfg` beside wherever
/// it thinks it is, so an inherited cwd scatters game state into an unrelated
/// directory. Callers that need somewhere else can still override it.
///
/// Resolution order for the command itself:
///
/// 1. `command_prefix`, if the user set one. It's the manual escape hatch and
///    it wins, because someone who configured a wrapper wants that wrapper,
///    not the one we guessed.
/// 2. On Linux, the auto-detected Proton for the game's prefix.
/// 3. Otherwise the executable directly, which is the Windows path.
pub fn command_for_exe(exe: &Path, prefix: PrefixState) -> Result<Command, String> {
    let mut cmd = command_without_cwd(exe, prefix)?;
    if let Some(dir) = exe.parent() {
        cmd.current_dir(dir);
    }
    strip_appimage_env(&mut cmd);
    Ok(cmd)
}

/// Undo the AppImage runtime's environment for a child process.
///
/// When modlunky2 runs as an AppImage, its `AppRun` points a dozen variables
/// at the read-only mount so the bundled copies of GTK, WebKit and friends get
/// used instead of the system ones. Those are right for us and wrong for
/// everything we launch: children inherit them and then load our libraries, or
/// worse, look for their own runtime somewhere it isn't.
///
/// Proton is the case that made this obvious. It's a Python script, so it
/// inherited `PYTHONHOME=$APPDIR/usr/` and died with "Failed to import
/// encodings module" before it got anywhere near starting the game.
/// `GIO_EXTRA_MODULES` produced a second, noisier symptom on the way past.
///
/// Filters rather than clears, because some of these mix our paths with the
/// real ones: `PATH` and `XDG_DATA_DIRS` have the AppDir prepended to the
/// user's actual values, and a child needs what's left. Any variable that ends
/// up empty is removed outright.
///
/// No-op when not running as an AppImage, where `APPDIR` is unset.
pub fn strip_appimage_env(cmd: &mut Command) {
    let Ok(appdir) = std::env::var("APPDIR") else {
        return;
    };
    for (key, replacement) in appimage_env_overrides(&appdir, std::env::vars()) {
        match replacement {
            Some(value) => cmd.env(key, value),
            None => cmd.env_remove(key),
        };
    }
}

/// Which variables [`strip_appimage_env`] changes, and to what. `None` means
/// remove it. Split out from the `Command` so the filtering can be tested
/// against a captured real environment instead of the test process's own.
fn appimage_env_overrides(
    appdir: &str,
    vars: impl Iterator<Item = (String, String)>,
) -> Vec<(String, Option<String>)> {
    if appdir.is_empty() {
        return Vec::new();
    }
    vars.filter(|(_, value)| value.contains(appdir))
        .map(|(key, value)| {
            // Empty components go too. In a search path an empty entry means
            // the current directory, which is not something a child should
            // inherit from us, and the runtime leaves trailing colons behind.
            let kept: Vec<&str> = value
                .split(':')
                .filter(|part| !part.is_empty() && !part.starts_with(appdir))
                .collect();
            let replacement = (!kept.is_empty()).then(|| kept.join(":"));
            (key, replacement)
        })
        .collect()
}

fn command_without_cwd(exe: &Path, prefix: PrefixState) -> Result<Command, String> {
    let prefix_tokens: Vec<String> = crate::config::load()
        .command_prefix
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .and_then(|s| shell_words::split(s).ok())
        .unwrap_or_default();

    if let Some((head, tail)) = prefix_tokens.split_first() {
        let mut cmd = Command::new(head);
        cmd.args(tail).arg(exe);
        return Ok(cmd);
    }

    #[cfg(target_os = "linux")]
    {
        let env = crate::proton::ProtonEnv::detect()
            .map_err(|e| format!("could not set up Proton to run {}: {e}", exe.display()))?;
        Ok(env.command(exe, prefix))
    }

    #[cfg(not(target_os = "linux"))]
    {
        let _ = prefix;
        Ok(Command::new(exe))
    }
}

/// Starts the game with the requested combination of tools.
///
/// The four permutations used to be three separate entry points on two
/// different tabs, plus a modal toggle for the fourth, and there was no way to
/// launch the game plain at all. Keeping the mapping here means the UI just
/// says which tools it wants and never has to know that "both" is Playlunky
/// with a flag rather than two launches.
///
/// Writing the flags to config first is necessary, not just so the dock
/// comes back the way it was left: `spawn_playlunky` reads `playlunky-overlunky`
/// back out of config to decide whether to pass `--overlunky`, so skipping the
/// write would silently drop Overlunky from the both-tools case.
///
/// Only the dock calls this. One-off launches elsewhere (the Overlunky tab's
/// card) go straight to their own launcher precisely so they *don't* write
/// here: the dock describes what its own button will do next time, and a
/// transient launch shouldn't leave the user a setting to undo.
#[tauri::command]
pub async fn launch_game(with_playlunky: bool, with_overlunky: bool) -> Result<(), String> {
    crate::config::apply_patch(crate::config::ConfigPatch {
        launch_with_playlunky: Some(with_playlunky),
        playlunky_overlunky: Some(with_overlunky),
        ..Default::default()
    })?;

    match (with_playlunky, with_overlunky) {
        // Playlunky starts the game itself and takes Overlunky along via the
        // `--overlunky` flag it just read back out of the config, so "both" is
        // one launch rather than two.
        (true, _) => crate::playlunky::spawn_playlunky().await,
        // Overlunky's LaunchGame mode starts the game with the DLL already
        // attached, which avoids the race that injecting into a starting game
        // would have.
        (false, true) => {
            crate::overlunky::spawn_overlunky(crate::overlunky::LaunchMode::LaunchGame)
        }
        (false, false) => crate::playlunky::spawn_vanilla(),
    }
}

/// Makes orphaned descendants reparent to us instead of to init.
///
/// The trackers read the game's memory, which on Linux requires passing the
/// ptrace access check. Under the common `kernel.yama.ptrace_scope=1` a
/// descendant is always readable, and the check runs at read time rather than
/// launch time, so the game has to still be in our subtree when a tracker
/// attaches, not merely have been started by us.
///
/// That isn't automatic. Launching goes through several layers (the Steam
/// runtime container, the Proton script, wine, and for Playlunky its own
/// launcher), and if an intermediate exits, everything below it reparents to
/// the nearest subreaper. Becoming that subreaper keeps the chain intact.
///
/// This is a fallback rather than the main mechanism: a Proton-launched game
/// is readable regardless of ancestry, because pressure-vessel puts it in a
/// user namespace we own (see `ml2_mem::process::linux`). It matters for the
/// setups that don't get that, such as a bare wine via `command_prefix`.
///
/// Best-effort: failure only costs the trackers on an already-restricted
/// system, so it's logged rather than surfaced.
pub fn become_child_subreaper() {
    #[cfg(target_os = "linux")]
    {
        // SAFETY: prctl with PR_SET_CHILD_SUBREAPER takes an int by value and
        // touches no memory we own. It cannot fail for a valid option, but
        // the result is checked anyway.
        let rc = unsafe { libc::prctl(libc::PR_SET_CHILD_SUBREAPER, 1) };
        if rc != 0 {
            tracing::warn!(
                "could not become a child subreaper: {}. Trackers may not be \
                 able to attach to a game launched from here.",
                std::io::Error::last_os_error()
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const APPDIR: &str = "/tmp/.mount_modlunAbc123";

    /// Lifted from a running AppImage build of this app, trimmed to the
    /// variables its runtime actually rewrites. Real values rather than
    /// invented ones, including the doubled slashes and trailing colons the
    /// runtime emits, since those are what the filter has to cope with.
    fn captured_appimage_env() -> Vec<(String, String)> {
        [
            ("PYTHONHOME", "/tmp/.mount_modlunAbc123/usr/"),
            (
                "PYTHONPATH",
                "/tmp/.mount_modlunAbc123/usr/share/pyshared/:",
            ),
            (
                "GIO_EXTRA_MODULES",
                "/tmp/.mount_modlunAbc123/usr/lib/x86_64-linux-gnu/gio/modules",
            ),
            (
                "LD_LIBRARY_PATH",
                "/tmp/.mount_modlunAbc123/usr/lib/:/tmp/.mount_modlunAbc123/lib64/:",
            ),
            ("APPDIR", "/tmp/.mount_modlunAbc123"),
            (
                "GTK_PATH",
                "/tmp/.mount_modlunAbc123//usr/lib/x86_64-linux-gnu/gtk-3.0:/usr/lib64/gtk-3.0",
            ),
            (
                "XDG_DATA_DIRS",
                "/tmp/.mount_modlunAbc123/usr/share/:/usr/share:/usr/local/share/",
            ),
            (
                "PATH",
                "/tmp/.mount_modlunAbc123/usr/bin/:/usr/local/bin:/usr/bin:/bin",
            ),
            // Untouched: no AppDir anywhere in it.
            ("HOME", "/home/gary"),
            (
                "STEAM_COMPAT_DATA_PATH",
                "/home/gary/.steam/compatdata/418530",
            ),
        ]
        .into_iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect()
    }

    fn overrides() -> std::collections::HashMap<String, Option<String>> {
        appimage_env_overrides(APPDIR, captured_appimage_env().into_iter())
            .into_iter()
            .collect()
    }

    /// The bug this all exists for. Proton is a Python script, and an
    /// inherited PYTHONHOME pointing into our mount kills it before it starts
    /// with "Failed to import encodings module".
    #[test]
    fn removes_the_python_vars_that_break_proton() {
        let o = overrides();
        assert_eq!(o.get("PYTHONHOME"), Some(&None));
        assert_eq!(o.get("PYTHONPATH"), Some(&None));
    }

    #[test]
    fn removes_vars_that_point_only_into_the_appdir() {
        let o = overrides();
        for key in ["GIO_EXTRA_MODULES", "LD_LIBRARY_PATH", "APPDIR"] {
            assert_eq!(o.get(key), Some(&None), "{key} should have been removed");
        }
    }

    /// The reason this filters instead of clearing. A child still needs to
    /// find its own executables and data; only our entries should go.
    #[test]
    fn keeps_the_real_entries_in_mixed_search_paths() {
        let o = overrides();
        assert_eq!(
            o.get("PATH"),
            Some(&Some("/usr/local/bin:/usr/bin:/bin".to_string()))
        );
        assert_eq!(
            o.get("XDG_DATA_DIRS"),
            Some(&Some("/usr/share:/usr/local/share/".to_string()))
        );
        assert_eq!(
            o.get("GTK_PATH"),
            Some(&Some("/usr/lib64/gtk-3.0".to_string()))
        );
    }

    #[test]
    fn leaves_unrelated_vars_alone() {
        let o = overrides();
        assert!(!o.contains_key("HOME"));
        assert!(!o.contains_key("STEAM_COMPAT_DATA_PATH"));
    }

    /// Not running as an AppImage: nothing to undo, and we must not start
    /// deleting a normal environment on the strength of an empty prefix.
    #[test]
    fn does_nothing_without_an_appdir() {
        let o = appimage_env_overrides("", captured_appimage_env().into_iter());
        assert!(o.is_empty());
    }
}
