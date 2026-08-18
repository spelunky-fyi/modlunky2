//! Per-install bookkeeping about mods: which ones are favorites, and when
//! each was last actually loaded into the game.
//!
//! Lives in the install directory rather than in `config.json` because every
//! value here is keyed by mod id, and a mod id only means anything relative to
//! one install's `Mods/Packs`. Someone with two installs would otherwise get a
//! union of both their mod sets in one file, each install showing history for
//! mods it doesn't have. It also means copying a `Mods` folder to another
//! machine brings the favorites and usage history along with the mods they
//! describe.
//!
//! How the list is sorted and filtered is the opposite case -- it names no
//! mod, so it means the same thing everywhere -- and lives in `config.json`.
//!
//! Sits next to `pack-metadata/`, the other thing modlunky keeps under `.ml`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::mod_check::ModProblem;

/// Everything this module persists, as one small file. A single document
/// rather than a file per mod because sorting the list needs every mod's
/// timestamp at once, and `list_mods` runs on every `mods-changed` event.
#[derive(Debug, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ModState {
    /// Mod id -> when it was last loaded into a running game, as milliseconds
    /// since the Unix epoch.
    #[serde(default)]
    pub last_used: HashMap<String, u64>,
    /// Mod ids the user starred. A list rather than a set so the JSON reads
    /// naturally; the sizes involved make lookup cost irrelevant.
    #[serde(default)]
    pub favorites: Vec<String>,
    /// Results of the last `mod_check` run per mod. Cached because checking
    /// walks the pack's files, which is far too expensive to repeat for every
    /// mod on every list refresh once someone has a few hundred installed.
    #[serde(default)]
    pub checks: HashMap<String, PackCheck>,
}

/// One pack's check result, stamped with the folder mtime it was computed
/// from.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PackCheck {
    /// `mod_check::CHECK_VERSION` at the time this ran. Missing (and so `0`)
    /// for anything written before versioning existed, which never matches
    /// and is therefore discarded.
    #[serde(default)]
    pub version: u32,
    /// Folder mtime in milliseconds when the check ran. `list_mods` already
    /// stats this for its sort, so validating the cache costs nothing extra.
    ///
    /// Best-effort, and deliberately so. It catches the coarse cases -- the
    /// pack being installed, updated, or replaced -- but not someone fixing
    /// `Data/Textures/char_yellow.json` in a text editor, because editing a
    /// file's contents doesn't touch the mtime of any directory above it.
    /// Making that airtight would mean walking the pack on every list refresh,
    /// which is the exact cost this cache exists to avoid.
    ///
    /// So the cache backs the *badge*, which is advisory and can be re-run on
    /// demand. The check that actually gates enabling is always run fresh
    /// against the files as they are right now.
    pub mtime: u64,
    pub problems: Vec<ModProblem>,
}

fn state_path(install_dir: &Path) -> PathBuf {
    install_dir.join("Mods").join(".ml").join("mod-state.json")
}

/// Reads the state file. A missing or malformed file is not an error: this is
/// convenience data, and refusing to list mods because a preferences blob got
/// corrupted would be a much worse outcome than losing some stars.
pub fn load(install_dir: &Path) -> ModState {
    std::fs::read(state_path(install_dir))
        .ok()
        .and_then(|bytes| serde_json::from_slice(&bytes).ok())
        .unwrap_or_default()
}

pub fn save(install_dir: &Path, state: &ModState) -> Result<(), String> {
    let path = state_path(install_dir);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
    }
    let json = serde_json::to_string_pretty(state).map_err(|e| format!("encode mod state: {e}"))?;
    std::fs::write(&path, json).map_err(|e| format!("write {}: {e}", path.display()))
}

/// Drops entries for mods that are no longer installed, returning whether
/// anything was removed.
///
/// Without this the file grows forever: every mod ever launched or starred
/// keeps its entry after the mod is deleted. Same treatment `list_recent_packs`
/// gives its dead pack names.
pub fn prune(state: &mut ModState, live_ids: &std::collections::HashSet<String>) -> bool {
    let before = (
        state.last_used.len(),
        state.favorites.len(),
        state.checks.len(),
    );
    state.last_used.retain(|id, _| live_ids.contains(id));
    state.favorites.retain(|id| live_ids.contains(id));
    state.checks.retain(|id, _| live_ids.contains(id));
    before
        != (
            state.last_used.len(),
            state.favorites.len(),
            state.checks.len(),
        )
}

/// Stars or unstars one mod.
pub fn set_favorite(install_dir: &Path, id: &str, favorite: bool) -> Result<(), String> {
    let mut state = load(install_dir);
    let already = state.favorites.iter().any(|f| f == id);
    match (favorite, already) {
        (true, false) => state.favorites.push(id.to_string()),
        (false, true) => state.favorites.retain(|f| f != id),
        // Nothing to do, but still write: the caller asked for a specific
        // end state and a no-op write keeps this idempotent.
        _ => {}
    }
    save(install_dir, &state)
}

/// Stamps `ids` as used right now. Called when the game is launched in a mode
/// that actually loads packs.
pub fn mark_used(install_dir: &Path, ids: &[String], now_ms: u64) -> Result<(), String> {
    if ids.is_empty() {
        return Ok(());
    }
    let mut state = load(install_dir);
    for id in ids {
        state.last_used.insert(id.clone(), now_ms);
    }
    save(install_dir, &state)
}

/// Records a fresh check result for one mod.
pub fn set_check(
    install_dir: &Path,
    id: &str,
    mtime: u64,
    problems: Vec<ModProblem>,
) -> Result<(), String> {
    let mut state = load(install_dir);
    state.checks.insert(
        id.to_string(),
        PackCheck {
            version: crate::mod_check::CHECK_VERSION,
            mtime,
            problems,
        },
    );
    save(install_dir, &state)
}

/// Whether a cached result still describes the pack as it is now, under the
/// checks we run today.
pub fn check_is_current(check: &PackCheck, pack_mtime: u64) -> bool {
    check.version == crate::mod_check::CHECK_VERSION && check.mtime == pack_mtime
}

/// Milliseconds since the Unix epoch, or 0 if the clock is before it.
pub fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .ok()
        .and_then(|d| u64::try_from(d.as_millis()).ok())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ids(list: &[&str]) -> std::collections::HashSet<String> {
        list.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn a_missing_file_reads_as_empty_rather_than_failing() {
        let dir = tempfile::tempdir().unwrap();
        let state = load(dir.path());
        assert!(state.last_used.is_empty());
        assert!(state.favorites.is_empty());
    }

    /// Losing a star is an acceptable outcome for a corrupted preferences
    /// blob; refusing to show the user's mods is not.
    #[test]
    fn a_corrupt_file_reads_as_empty_rather_than_failing() {
        let dir = tempfile::tempdir().unwrap();
        let path = state_path(dir.path());
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, "{not json at all").unwrap();
        assert!(load(dir.path()).favorites.is_empty());
    }

    #[test]
    fn favorites_round_trip() {
        let dir = tempfile::tempdir().unwrap();
        set_favorite(dir.path(), "fyi.a-mod", true).unwrap();
        assert_eq!(load(dir.path()).favorites, vec!["fyi.a-mod".to_string()]);
        set_favorite(dir.path(), "fyi.a-mod", false).unwrap();
        assert!(load(dir.path()).favorites.is_empty());
    }

    #[test]
    fn favoriting_twice_does_not_duplicate() {
        let dir = tempfile::tempdir().unwrap();
        set_favorite(dir.path(), "fyi.a-mod", true).unwrap();
        set_favorite(dir.path(), "fyi.a-mod", true).unwrap();
        assert_eq!(load(dir.path()).favorites.len(), 1);
    }

    #[test]
    fn mark_used_stamps_every_id_and_overwrites_older_stamps() {
        let dir = tempfile::tempdir().unwrap();
        mark_used(dir.path(), &["a".into(), "b".into()], 1_000).unwrap();
        mark_used(dir.path(), &["a".into()], 2_000).unwrap();
        let state = load(dir.path());
        assert_eq!(state.last_used.get("a"), Some(&2_000));
        assert_eq!(state.last_used.get("b"), Some(&1_000));
    }

    /// Favorites and usage must survive each other's writes: they share one
    /// file, so a careless save would drop whichever wasn't being edited.
    #[test]
    fn writing_one_field_preserves_the_other() {
        let dir = tempfile::tempdir().unwrap();
        set_favorite(dir.path(), "a", true).unwrap();
        mark_used(dir.path(), &["a".into()], 1_000).unwrap();
        set_favorite(dir.path(), "b", true).unwrap();

        let state = load(dir.path());
        assert_eq!(state.last_used.get("a"), Some(&1_000));
        assert_eq!(state.favorites, vec!["a".to_string(), "b".to_string()]);
    }

    #[test]
    fn a_fresh_check_is_current() {
        let dir = tempfile::tempdir().unwrap();
        set_check(dir.path(), "a-mod", 500, Vec::new()).unwrap();
        let state = load(dir.path());
        assert!(check_is_current(&state.checks["a-mod"], 500));
    }

    /// A pack that's been reinstalled or updated has a different folder mtime,
    /// so its old findings describe files that may no longer exist.
    #[test]
    fn a_check_taken_against_a_different_pack_state_is_stale() {
        let dir = tempfile::tempdir().unwrap();
        set_check(dir.path(), "a-mod", 500, Vec::new()).unwrap();
        let state = load(dir.path());
        assert!(!check_is_current(&state.checks["a-mod"], 900));
    }

    /// Adding a check must not leave every already-scanned pack reporting
    /// clean forever under the old, smaller set of checks.
    #[test]
    fn a_check_from_an_older_check_set_is_stale() {
        let stale = PackCheck {
            version: crate::mod_check::CHECK_VERSION - 1,
            mtime: 500,
            problems: Vec::new(),
        };
        assert!(!check_is_current(&stale, 500));
    }

    /// Results written before versioning existed deserialize with version 0.
    #[test]
    fn an_unversioned_check_is_stale() {
        let unversioned: PackCheck =
            serde_json::from_str(r#"{"mtime":500,"problems":[]}"#).unwrap();
        assert_eq!(unversioned.version, 0);
        assert!(!check_is_current(&unversioned, 500));
    }

    #[test]
    fn prune_drops_entries_for_uninstalled_mods() {
        let mut state = ModState {
            last_used: [("gone".to_string(), 1u64), ("kept".to_string(), 2)].into(),
            favorites: vec!["gone".into(), "kept".into()],
            ..Default::default()
        };

        assert!(prune(&mut state, &ids(&["kept"])));

        assert_eq!(state.favorites, vec!["kept".to_string()]);
        assert_eq!(state.last_used.keys().collect::<Vec<_>>(), vec!["kept"]);
    }

    #[test]
    fn prune_reports_no_change_when_everything_is_still_installed() {
        let mut state = ModState {
            last_used: [("kept".to_string(), 2u64)].into(),
            favorites: vec!["kept".into()],
            ..Default::default()
        };
        assert!(!prune(&mut state, &ids(&["kept", "other"])));
    }
}
