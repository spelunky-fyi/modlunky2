//! Steam and Proton discovery on Linux.
//!
//! Spelunky 2 has no native Linux build, so everything modlunky2 launches
//! there (the game, Playlunky, Overlunky) is a Windows executable that has to
//! run inside the game's existing Proton prefix. Using the game's own prefix
//! rather than a fresh one matters: it already has the runtime the game needs,
//! and Overlunky can only inject into the game if both are in the same prefix,
//! which is to say talking to the same wineserver.
//!
//! None of this is configured by hand. Every path is derived from the appid,
//! which we already know, by walking Steam's own on-disk metadata:
//!
//! ```text
//! steam root/steamapps/libraryfolders.vdf   -> every library
//!   library/steamapps/appmanifest_<id>.acf  -> that app's install dir
//!   library/steamapps/compatdata/<id>       -> the game's prefix
//!     config_info                           -> which Proton built it
//!       proton/toolmanifest.vdf             -> the runtime it needs
//! ```
//!
//! The whole module is Linux-only. Windows runs these executables directly.

use std::path::{Path, PathBuf};

/// Spelunky 2. Matches `playlunky::STEAM_APP_ID`, kept as a number here since
/// every path built from it is a directory name.
pub const SPELUNKY2_APPID: &str = "418530";

/// Whether anything of ours is already running in the prefix, which decides
/// which Proton verb to use.
///
/// `proton run` does prefix maintenance before starting the executable, and
/// part of that is replacing the prefix's builtin DLLs. It's guarded by a
/// config signature, so it only actually rewrites them on the first run after
/// something changes, but when it does fire it is rewriting `system32` out
/// from under whatever is already running in there.
///
/// `proton runinprefix` skips that maintenance and runs `wine <exe>` in the
/// prefix as-is, which is what a second process joining a live session wants.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PrefixState {
    /// Nothing of ours is running yet. Let Proton do its full setup, which is
    /// also what creates and upgrades the prefix in the first place.
    Fresh,
    /// The game is already running in this prefix. Touch as little as
    /// possible.
    Live,
}

impl PrefixState {
    fn proton_verb(self) -> &'static str {
        match self {
            Self::Fresh => "run",
            Self::Live => "runinprefix",
        }
    }
}

/// Everything needed to run a Windows executable in the game's prefix.
#[derive(Debug, Clone)]
pub struct ProtonEnv {
    /// Steam root, e.g. `~/.local/share/Steam`.
    pub steam_root: PathBuf,
    /// The game's install directory, the one holding `Spel2.exe`.
    pub install_dir: PathBuf,
    /// `compatdata/<appid>`, the prefix Steam built for the game.
    pub compat_data: PathBuf,
    /// Directory holding the `proton` script.
    pub proton_dir: PathBuf,
    /// The Steam Linux Runtime entry point Proton asks for in its
    /// toolmanifest. `None` for older Proton builds that don't require a
    /// container, in which case the proton script is invoked directly.
    pub runtime_entry_point: Option<PathBuf>,
}

impl ProtonEnv {
    /// Walks Steam's metadata to find the game and the Proton that built its
    /// prefix. `Err` describes which step failed, since each has a different
    /// user-facing fix (install the game, run it once under Proton, ...).
    pub fn detect() -> Result<Self, String> {
        let steam_root = steam_root().ok_or("could not find a Steam installation")?;
        let libraries = library_paths(&steam_root);

        let (library, install_dir) = libraries
            .iter()
            .find_map(|lib| {
                let dir = app_install_dir(lib, SPELUNKY2_APPID)?;
                dir.join(ml2_mem::SPEL2_EXE_NAME)
                    .exists()
                    .then(|| (lib.clone(), dir))
            })
            .ok_or("Spelunky 2 is not installed in any Steam library")?;

        let compat_data = library
            .join("steamapps")
            .join("compatdata")
            .join(SPELUNKY2_APPID);
        if !compat_data.is_dir() {
            return Err(format!(
                "no Proton prefix at {}. Run Spelunky 2 from Steam once so \
                 Steam creates it.",
                compat_data.display()
            ));
        }

        let proton_dir = proton_dir_from_config_info(&compat_data).ok_or_else(|| {
            format!(
                "could not tell which Proton built the prefix at {}",
                compat_data.display()
            )
        })?;

        // Modern Proton runs inside a Steam Linux Runtime container and names
        // the one it wants by appid. Resolve it the same way as the game.
        let runtime_entry_point =
            vdf_lookup(&proton_dir.join("toolmanifest.vdf"), "require_tool_appid")
                .and_then(|appid| {
                    libraries
                        .iter()
                        .find_map(|lib| app_install_dir(lib, &appid))
                        .map(|dir| dir.join("_v2-entry-point"))
                })
                .filter(|p| p.exists());

        Ok(Self {
            steam_root,
            install_dir,
            compat_data,
            proton_dir,
            runtime_entry_point,
        })
    }

    /// Builds the command that runs `exe` inside the game's prefix.
    ///
    /// Shape is `[<runtime> --verb=run --] <proton> <verb> <exe>`, with the
    /// compat variables Proton reads for the prefix and Steam root. The
    /// `SteamAppId` group is what `steam_appid.txt` does on Windows: launching
    /// this way bypasses the Steam client's own path, so without it the
    /// Steamworks init in the executable has no app identity. Steam still has
    /// to be running.
    ///
    /// See [`PrefixState`] for why the verb depends on what's already running.
    pub fn command(&self, exe: &Path, prefix: PrefixState) -> std::process::Command {
        let mut cmd = match &self.runtime_entry_point {
            Some(entry) => {
                let mut c = std::process::Command::new(entry);
                c.arg("--verb=run").arg("--").arg(self.proton_script());
                c
            }
            None => std::process::Command::new(self.proton_script()),
        };
        cmd.arg(prefix.proton_verb())
            .arg(exe)
            .env("STEAM_COMPAT_DATA_PATH", &self.compat_data)
            .env("STEAM_COMPAT_CLIENT_INSTALL_PATH", &self.steam_root)
            .env("SteamAppId", SPELUNKY2_APPID)
            .env("SteamGameId", SPELUNKY2_APPID)
            .env("STEAM_COMPAT_APP_ID", SPELUNKY2_APPID);
        cmd
    }

    pub fn proton_script(&self) -> PathBuf {
        self.proton_dir.join("proton")
    }
}

/// Steam's root, wherever this distro or install method put it.
fn steam_root() -> Option<PathBuf> {
    let home = PathBuf::from(std::env::var_os("HOME")?);
    [
        home.join(".local/share/Steam"),
        home.join(".steam/steam"),
        home.join(".steam/root"),
        home.join(".var/app/com.valvesoftware.Steam/data/Steam"),
    ]
    .into_iter()
    .find(|p| p.join("steamapps").is_dir())
}

/// Every library root Steam knows about, starting with the root install.
/// `libraryfolders.vdf` is a nested blob and only its `path` keys matter, so
/// this scrapes them rather than pulling in a VDF parser.
fn library_paths(steam_root: &Path) -> Vec<PathBuf> {
    let mut out = vec![steam_root.to_path_buf()];
    let Ok(text) = std::fs::read_to_string(steam_root.join("steamapps/libraryfolders.vdf")) else {
        return out;
    };
    for line in text.lines() {
        if let Some(path) = vdf_value(line, "path") {
            let path = PathBuf::from(path);
            if !out.contains(&path) {
                out.push(path);
            }
        }
    }
    out
}

/// `<library>/steamapps/common/<installdir>` for an installed appid, read from
/// that app's manifest. `None` when the app isn't in this library.
fn app_install_dir(library: &Path, appid: &str) -> Option<PathBuf> {
    let manifest = library
        .join("steamapps")
        .join(format!("appmanifest_{appid}.acf"));
    let installdir = vdf_lookup(&manifest, "installdir")?;
    let dir = library.join("steamapps").join("common").join(installdir);
    dir.is_dir().then_some(dir)
}

/// The prefix's `config_info` lists paths inside the Proton that built it (its
/// fonts dir, its lib dir). The Proton root is whichever ancestor of one of
/// those holds a `proton` script.
fn proton_dir_from_config_info(compat_data: &Path) -> Option<PathBuf> {
    let text = std::fs::read_to_string(compat_data.join("config_info")).ok()?;
    text.lines().find_map(|line| {
        let mut candidate = Path::new(line.trim());
        while let Some(parent) = candidate.parent() {
            if parent.join("proton").is_file() {
                return Some(parent.to_path_buf());
            }
            candidate = parent;
        }
        None
    })
}

fn vdf_lookup(file: &Path, key: &str) -> Option<String> {
    let text = std::fs::read_to_string(file).ok()?;
    text.lines().find_map(|line| vdf_value(line, key))
}

/// Pull the value out of a `"<key>"    "<value>"` VDF line.
fn vdf_value(line: &str, key: &str) -> Option<String> {
    let mut parts = line.split('"').filter(|s| !s.trim().is_empty());
    if parts.next()? != key {
        return None;
    }
    parts.next().map(String::from)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn vdf_value_reads_tab_separated_pairs() {
        assert_eq!(
            vdf_value("\t\t\"installdir\"\t\t\"Spelunky 2\"", "installdir").as_deref(),
            Some("Spelunky 2")
        );
        assert_eq!(
            vdf_value("\t\"path\"\t\t\"/mnt/games/SteamLibrary\"", "path").as_deref(),
            Some("/mnt/games/SteamLibrary")
        );
    }

    /// End-to-end check of the launch path, from Steam discovery through to a
    /// tracker attaching to what we started. Ignored by default because it
    /// needs Spelunky 2 installed, Steam running, and it opens a game window
    /// for about a minute:
    ///
    /// ```console
    /// cargo test -p modlunky2-app --lib -- --ignored --nocapture proton
    /// ```
    ///
    /// Also the only automated cover for the subreaper behaviour: if the game
    /// leaves our process subtree, `from_pid` comes back `AccessDenied` on any
    /// machine with the usual `ptrace_scope=1`.
    #[test]
    #[ignore = "needs Spelunky 2 installed and Steam running; launches the game"]
    fn launches_the_game_and_can_read_it() {
        use std::time::{Duration, Instant};

        crate::launch::become_child_subreaper();
        let env = ProtonEnv::detect().expect("detect Proton");
        println!("install dir {}", env.install_dir.display());
        println!("proton      {}", env.proton_script().display());

        // Through `command_for_exe`, not `env.command`, so the game gets a
        // working directory. Spawning it bare once left a savegame and three
        // config files in whatever directory the test ran from.
        let exe = env.install_dir.join(ml2_mem::SPEL2_EXE_NAME);
        let mut child = crate::launch::command_for_exe(&exe, PrefixState::Fresh)
            .expect("build launch command")
            .spawn()
            .expect("spawn the game");

        // The game appears well after the spawn returns: Proton forks through
        // the runtime container and the wine loader first.
        let deadline = Instant::now() + Duration::from_secs(120);
        let pid = loop {
            if let Some(pid) = ml2_mem::find_spelunky2_pid() {
                break pid;
            }
            assert!(Instant::now() < deadline, "game never started");
            std::thread::sleep(Duration::from_millis(250));
        };
        println!("Spel2.exe pid {pid}");

        let result = (|| {
            let process = ml2_mem::Spel2Process::from_pid(pid)?;
            // The marker isn't written for the first few seconds of startup,
            // so a miss here is expected until the game finishes loading.
            loop {
                match process.get_feedcode() {
                    Ok(addr) => return Ok(addr),
                    Err(e) if Instant::now() < deadline => {
                        println!("  waiting for feedcode: {e}");
                        std::thread::sleep(Duration::from_secs(2));
                    }
                    Err(e) => return Err(e),
                }
            }
        })();

        let _ = child.kill();
        let _ = child.wait();
        println!("feedcode at {:#x}", result.expect("read the game's memory"));
    }

    /// Overlunky's inject mode, which is the one path that runs a second
    /// executable into a prefix that already has the game live in it. Same
    /// requirements as the test above, plus Overlunky installed:
    ///
    /// ```console
    /// cargo test -p modlunky2-app --lib -- --ignored --nocapture inject
    /// ```
    #[test]
    #[ignore = "needs Spelunky 2 and Overlunky installed, and Steam running"]
    fn overlunky_injects_into_a_running_game() {
        use std::time::{Duration, Instant};

        crate::launch::become_child_subreaper();
        let env = ProtonEnv::detect().expect("detect Proton");
        let overlunky = env.install_dir.join("Overlunky").join("Overlunky.exe");
        assert!(
            overlunky.exists(),
            "Overlunky not installed at {}",
            overlunky.display()
        );

        let game_exe = env.install_dir.join(ml2_mem::SPEL2_EXE_NAME);
        let mut game = crate::launch::command_for_exe(&game_exe, PrefixState::Fresh)
            .expect("build game command")
            .spawn()
            .expect("spawn the game");

        // Wait until the game is genuinely up, not just present in the process
        // table, so the inject isn't racing startup.
        let deadline = Instant::now() + Duration::from_secs(120);
        let game_pid = loop {
            if let Some(pid) = ml2_mem::find_spelunky2_pid()
                && let Ok(p) = ml2_mem::Spel2Process::from_pid(pid)
                && p.get_feedcode().is_ok()
            {
                break pid;
            }
            assert!(Instant::now() < deadline, "game never became readable");
            std::thread::sleep(Duration::from_millis(500));
        };
        println!("game up, pid {game_pid}");

        let mut ol = crate::launch::command_for_exe(&overlunky, PrefixState::Live)
            .expect("build Overlunky command")
            .arg("--console")
            .spawn()
            .expect("spawn Overlunky");
        println!("Overlunky spawned, pid {}", ol.id());

        // Give the injection time to land, checking as we go that the game is
        // still alive rather than only looking at the end.
        let mut still_running = true;
        for _ in 0..30 {
            std::thread::sleep(Duration::from_secs(1));
            if ml2_mem::find_spelunky2_pid() != Some(game_pid) {
                still_running = false;
                break;
            }
        }

        let _ = ol.kill();
        let _ = ol.wait();
        let _ = game.kill();
        let _ = game.wait();

        assert!(
            still_running,
            "the game died after Overlunky injected into it"
        );
        println!("game survived the inject");
    }

    #[test]
    fn vdf_value_ignores_other_keys_and_structure() {
        assert_eq!(
            vdf_value("\t\"name\"\t\t\"Spelunky 2\"", "installdir"),
            None
        );
        assert_eq!(vdf_value("{", "installdir"), None);
        assert_eq!(vdf_value("", "installdir"), None);
        // A key with no value shouldn't come back as a match.
        assert_eq!(vdf_value("\t\"installdir\"", "installdir"), None);
    }
}
