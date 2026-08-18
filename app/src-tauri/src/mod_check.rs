//! Pre-flight checks for a mod's files.
//!
//! Playlunky crashes on some malformed pack files rather than skipping them,
//! which leaves the user with a game that won't start and no clue which of
//! their mods did it. Fixing that properly is Playlunky's job; this is a guard
//! rail so the crash is at least predictable and attributable.
//!
//! Deliberately narrow. Everything here has to be a *fact about the file*, not
//! a guess: a check that fires on a working mod is worse than no check, since
//! it teaches people to click through the warning. What that buys is the right
//! to say "this one is definitely broken" -- but never the reverse. Playlunky
//! parses these files more strictly than we do, so a clean result means "we
//! found nothing", not "this mod is safe".

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::characters::CharacterMeta;

/// Bump whenever the set of checks changes -- a new check, a widened one, or
/// a fixed false negative.
///
/// Cached results record the version that produced them, so a bump discards
/// every stored result. Without it, adding a check would leave every pack
/// that had already been scanned reporting "clean" from the old, smaller set
/// of checks, and the new one would only ever fire for packs that happened to
/// change afterwards. Unversioned caches (`0`) never match, so results written
/// before this existed are discarded too.
pub const CHECK_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum ModProblemKind {
    /// A `char_<color>.json` that isn't parseable at all.
    CharacterJson,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ModProblem {
    pub kind: ModProblemKind,
    /// Forward-slash path of the offending file, relative to the pack root, so
    /// the user can go straight to it.
    pub file: String,
    /// The parser's own message, which carries the line and column. Far more
    /// use than a generic "invalid file" when someone is trying to fix it.
    pub detail: String,
}

/// Whether a file name is character metadata, i.e. `char_<something>.json`.
///
/// Scoped to that shape on purpose. A pack's other JSON (`mod_info.json` and
/// friends) answers to a completely different schema, and validating it
/// against `CharacterMeta` would flag perfectly good mods.
fn is_character_json(file_name: &str) -> bool {
    let lower = file_name.to_ascii_lowercase();
    lower.starts_with("char_") && lower.ends_with(".json")
}

/// Every `char_*.json` under `root`, as (forward-slash rel path, full path).
///
/// Iterative rather than recursive, matching the character scanner, so an
/// oddly-nested pack can't blow the stack.
fn character_jsons(root: &Path) -> Vec<(String, PathBuf)> {
    let mut found = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let Ok(ft) = entry.file_type() else { continue };
            let path = entry.path();
            if ft.is_dir() {
                stack.push(path);
                continue;
            }
            let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
                continue;
            };
            if !is_character_json(name) {
                continue;
            }
            if let Ok(rel) = path.strip_prefix(root) {
                found.push((rel.to_string_lossy().replace('\\', "/"), path.clone()));
            }
        }
    }
    found.sort_by(|a, b| a.0.cmp(&b.0));
    found
}

/// Checks one pack, returning every problem found. An empty result means
/// nothing was detected, which is not the same as "safe" (see module docs).
pub fn check_pack(pack_dir: &Path) -> Vec<ModProblem> {
    let mut problems = Vec::new();
    for (rel, path) in character_jsons(pack_dir) {
        // An unreadable file is a filesystem problem, not a bad mod: a
        // permissions blip or a file being written right now would otherwise
        // brand the mod broken forever in the cache.
        let Ok(raw) = std::fs::read_to_string(&path) else {
            continue;
        };
        // The exact parse `characters::read_meta` performs, so the check can't
        // drift away from what the app actually does with the file. Every
        // field is optional and unknown keys are ignored, so a rejection here
        // means the file isn't structurally valid JSON at all.
        if let Err(e) = serde_json::from_str::<CharacterMeta>(&raw) {
            problems.push(ModProblem {
                kind: ModProblemKind::CharacterJson,
                file: rel,
                detail: e.to_string(),
            });
        }
    }
    problems
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pack(files: &[(&str, &str)]) -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        for (rel, body) in files {
            let path = dir.path().join(rel);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, body).unwrap();
        }
        dir
    }

    #[test]
    fn a_valid_character_json_is_not_a_problem() {
        let dir = pack(&[(
            "Data/Textures/char_yellow.json",
            r#"{"fullName":"Ana","shortName":"Ana"}"#,
        )]);
        assert!(check_pack(dir.path()).is_empty());
    }

    #[test]
    fn a_truncated_character_json_is_reported_with_its_path() {
        let dir = pack(&[("Data/Textures/char_yellow.json", r#"{"fullName":"Ana""#)]);

        let problems = check_pack(dir.path());

        assert_eq!(problems.len(), 1);
        assert_eq!(problems[0].file, "Data/Textures/char_yellow.json");
        assert_eq!(problems[0].kind, ModProblemKind::CharacterJson);
        assert!(!problems[0].detail.is_empty());
    }

    #[test]
    fn a_trailing_comma_is_reported() {
        let dir = pack(&[("char_blue.json", r#"{"fullName":"Ana",}"#)]);
        assert_eq!(check_pack(dir.path()).len(), 1);
    }

    /// The parse has to stay as permissive as the one the app really uses, or
    /// the check starts condemning mods that work fine.
    #[test]
    fn an_empty_object_and_unknown_keys_are_both_fine() {
        let dir = pack(&[
            ("char_red.json", "{}"),
            ("char_blue.json", r#"{"somethingWeDoNotKnow": 5}"#),
        ]);
        assert!(check_pack(dir.path()).is_empty());
    }

    /// Other JSON in a pack answers to a different schema entirely. Running it
    /// through `CharacterMeta` would condemn working mods wholesale.
    #[test]
    fn non_character_json_is_left_alone() {
        let dir = pack(&[
            ("mod_info.json", r#"{"name":"x","description":[1,2,3]}"#),
            ("data/other.json", "not json at all"),
        ]);
        assert!(check_pack(dir.path()).is_empty());
    }

    #[test]
    fn character_json_is_matched_case_insensitively() {
        let dir = pack(&[("CHAR_Yellow.JSON", "{oops")]);
        assert_eq!(check_pack(dir.path()).len(), 1);
    }

    #[test]
    fn every_bad_file_in_a_pack_is_reported() {
        let dir = pack(&[
            ("char_yellow.json", "{oops"),
            ("nested/char_blue.json", "["),
            ("char_red.json", "{}"),
        ]);
        assert_eq!(check_pack(dir.path()).len(), 2);
    }

    #[test]
    fn a_pack_with_no_character_json_is_clean() {
        let dir = pack(&[("main.lua", "-- hi")]);
        assert!(check_pack(dir.path()).is_empty());
    }

    #[test]
    fn a_missing_pack_directory_is_not_a_problem() {
        let dir = tempfile::tempdir().unwrap();
        assert!(check_pack(&dir.path().join("nope")).is_empty());
    }
}
