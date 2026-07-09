// Character-mod discovery for the managed character chooser.
//
// Spelunky 2 has 20 characters, each backed by a `char_<color>.png` sheet
// (2048x2048) plus an augmented `char_<color>_full.png` variant (2048x2224)
// that our tools dump. Mods ship these under a chosen color slot, which
// causes conflicts (two mods both shipping `char_blue.png`) resolved by
// Playlunky load order, or ship them under arbitrary names with no way to
// know which slot they belong to.
//
// This module crawls every pack, classifies candidate character sheets by a
// filename + dimensions heuristic, pairs the optional `char_<color>.json`
// metadata, and reports it all so the frontend can present a managed chooser.
// This is the read-only discovery half; assign/disable/restore land on top of
// it and persist declarative state under `Mods/.ml/pack-metadata/<id>/`.

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

use base64::{Engine as _, engine::general_purpose::STANDARD};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

/// A vanilla character slot: the `char_<color>` the game ships and the human
/// names we show for it. `color` is the filename token (`char_<color>.png`).
struct VanillaCharacter {
    color: &'static str,
    full_name: &'static str,
    short_name: &'static str,
}

/// The 20 vanilla characters in the game's canonical order.
const VANILLA_CHARACTERS: &[VanillaCharacter] = &[
    VanillaCharacter {
        color: "yellow",
        full_name: "Ana Spelunky",
        short_name: "Ana",
    },
    VanillaCharacter {
        color: "magenta",
        full_name: "Margaret Tunnel",
        short_name: "Margaret",
    },
    VanillaCharacter {
        color: "cyan",
        full_name: "Colin Northward",
        short_name: "Colin",
    },
    VanillaCharacter {
        color: "black",
        full_name: "Roffy",
        short_name: "Roffy",
    },
    VanillaCharacter {
        color: "cinnabar",
        full_name: "Alto Singh",
        short_name: "Alto",
    },
    VanillaCharacter {
        color: "green",
        full_name: "Liz Mutton",
        short_name: "Liz",
    },
    VanillaCharacter {
        color: "olive",
        full_name: "Nekka the Eagle",
        short_name: "Nekka",
    },
    VanillaCharacter {
        color: "white",
        full_name: "LISE Project",
        short_name: "LISE",
    },
    VanillaCharacter {
        color: "cerulean",
        full_name: "Coco Von Diamonds",
        short_name: "Coco",
    },
    VanillaCharacter {
        color: "blue",
        full_name: "Manfred Tunnel",
        short_name: "Manfred",
    },
    VanillaCharacter {
        color: "lime",
        full_name: "Little Jay",
        short_name: "Jay",
    },
    VanillaCharacter {
        color: "lemon",
        full_name: "Tina Flan",
        short_name: "Tina",
    },
    VanillaCharacter {
        color: "iris",
        full_name: "Valerie Crump",
        short_name: "Valerie",
    },
    VanillaCharacter {
        color: "gold",
        full_name: "Au",
        short_name: "Au",
    },
    VanillaCharacter {
        color: "red",
        full_name: "Demi Von Diamonds",
        short_name: "Demi",
    },
    VanillaCharacter {
        color: "pink",
        full_name: "Pilot",
        short_name: "Pilot",
    },
    VanillaCharacter {
        color: "violet",
        full_name: "Princess Airyn",
        short_name: "Airyn",
    },
    VanillaCharacter {
        color: "gray",
        full_name: "Dirk Yamaoka",
        short_name: "Dirk",
    },
    VanillaCharacter {
        color: "khaki",
        full_name: "Guy Spelunky",
        short_name: "Guy",
    },
    VanillaCharacter {
        color: "orange",
        full_name: "Classic Guy",
        short_name: "Classic Guy",
    },
];

fn is_known_color(color: &str) -> bool {
    VANILLA_CHARACTERS.iter().any(|c| c.color == color)
}

/// Canonical vanilla char-sheet dimensions: 2048x2048 for the base sheet,
/// 2048x2224 for the augmented `_full` variant.
fn is_char_dimensions(w: u32, h: u32) -> bool {
    w == 2048 && (h == 2048 || h == 2224)
}

/// How confident we are that a file is a character sheet, and thus how
/// prominently the chooser surfaces it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum Confidence {
    /// Named `char_<knowncolor>[_full].png`: occupies a known slot.
    Definite,
    /// `char_`-prefixed but an unknown color token (e.g. `char_sonic.png`),
    /// with char-sheet dimensions. A character with no assigned slot.
    Likely,
    /// Any PNG with char-sheet dimensions but no `char_` name. Caught by the
    /// dimensions heuristic; shown behind a "show possible" affordance.
    Possible,
}

/// Result of classifying a single file by name + dimensions. `None` means the
/// file isn't a character-sheet candidate at all.
#[derive(Debug, Clone, PartialEq)]
struct Classification {
    /// The file's true `_full` nature, decided by dimensions when known
    /// (2048x2224 = full), falling back to the name. This is what the assign
    /// target path keys off, not the (possibly wrong) filename.
    is_full: bool,
    /// The name's `_full` claim disagrees with the actual dimensions: either
    /// `_full` at 2048x2048 or a plain name at 2048x2224. Such files load
    /// wrong; the chooser flags them and can offer to rename to match.
    name_mismatch: bool,
    /// Known color slot the file currently occupies, if its name is
    /// `char_<knowncolor>`. `None` for likely/possible unassigned candidates.
    color: Option<String>,
    confidence: Confidence,
    /// Whether the pixel dimensions match a real char sheet. A definite file
    /// with the wrong size (`dims_ok = false`) is worth flagging in the UI.
    dims_ok: bool,
}

/// Whether a `char_`-stripped token is a parked marker (`unassigned<N>` /
/// `disabled<N>`) our tool produces when removing a character from a slot.
fn is_parked_suffix(rest: &str) -> bool {
    ["unassigned", "disabled"].iter().any(|prefix| {
        rest.strip_prefix(prefix)
            .map(|n| !n.is_empty() && n.chars().all(|c| c.is_ascii_digit()))
            .unwrap_or(false)
    })
}

/// Classify a file by its name and (optional) pixel dimensions. Pure so the
/// heuristic can be unit-tested without touching disk. `dims` is `None` only
/// in tests; the crawl always supplies it.
fn classify(file_name: &str, dims: Option<(u32, u32)>) -> Option<Classification> {
    let lower = file_name.to_lowercase();
    let stem = lower.strip_suffix(".png")?;

    let (base, name_is_full) = match stem.strip_suffix("_full") {
        Some(b) => (b, true),
        None => (stem, false),
    };
    let char_dims = dims.map(|(w, h)| is_char_dimensions(w, h)).unwrap_or(false);
    // `_full` is really signalled by the 2224 height. Trust the dimensions for
    // the true nature (so an augmented sheet under a plain name reads as full),
    // and flag when the name's `_full` claim disagrees with the pixels.
    let dims_is_full = dims.map(|(_, h)| h == 2224);
    let is_full = dims_is_full.unwrap_or(name_is_full);
    let name_mismatch = char_dims && dims_is_full.map(|f| f != name_is_full).unwrap_or(false);

    if let Some(rest) = base.strip_prefix("char_") {
        if is_known_color(rest) {
            return Some(Classification {
                is_full,
                name_mismatch,
                color: Some(rest.to_string()),
                confidence: Confidence::Definite,
                dims_ok: char_dims,
            });
        }
        // Files our tool parked out of a slot (`char_unassigned<N>` /
        // `char_disabled<N>`) came from real characters, so they're definite
        // even though they hold no slot right now. Their name intentionally
        // drops `_full`, and they aren't loading, so never flag a mismatch.
        if is_parked_suffix(rest) {
            return Some(Classification {
                is_full,
                name_mismatch: false,
                color: None,
                confidence: Confidence::Definite,
                dims_ok: char_dims,
            });
        }
        // char_-prefixed, unknown color: only a candidate when it's actually
        // char-sized, otherwise it's some other `char_...` texture.
        if char_dims {
            return Some(Classification {
                is_full,
                name_mismatch,
                color: None,
                confidence: Confidence::Likely,
                dims_ok: true,
            });
        }
        return None;
    }

    // Arbitrary name: only a candidate via the dimensions heuristic.
    if char_dims {
        return Some(Classification {
            is_full,
            name_mismatch,
            color: None,
            confidence: Confidence::Possible,
            dims_ok: true,
        });
    }
    None
}

/// The `char_<color>.json` metadata a mod can ship to override display name,
/// color, and gender. All fields optional; we only read it for display.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CharacterMeta {
    #[serde(default)]
    pub full_name: Option<String>,
    #[serde(default)]
    pub short_name: Option<String>,
    #[serde(default)]
    pub color: Option<String>,
    #[serde(default)]
    pub gender: Option<String>,
}

/// One discovered character-sheet file inside a pack.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CharacterCandidate {
    pub pack_id: String,
    /// Forward-slash path of the PNG relative to the pack root.
    pub rel_path: String,
    pub file_name: String,
    /// True `_full` nature by dimensions (2048x2224), not by the filename.
    pub is_full: bool,
    /// The filename's `_full` suffix disagrees with the dimensions, so the
    /// file is misnamed and won't load as intended. Fixable by renaming.
    pub name_mismatch: bool,
    pub width: u32,
    pub height: u32,
    pub dims_ok: bool,
    /// Known slot color the file currently occupies (`char_<color>`), or
    /// `None` for unassigned likely/possible candidates.
    pub detected_color: Option<String>,
    pub confidence: Confidence,
    /// Paired metadata sidecar (`char_<color>.json` or `.name`), if found (not
    /// necessarily a sibling of the PNG).
    pub meta_rel_path: Option<String>,
    pub metadata: Option<CharacterMeta>,
    /// Whether the pack is active in the load order. Only active packs' sheets
    /// actually load in-game.
    pub active: bool,
    /// Position in the load order (lower wins a slot conflict). `None` when the
    /// pack is inactive.
    pub load_rank: Option<usize>,
    /// User flagged this file as "not a character" so it stays hidden. Stored
    /// in the pack's `.ml` metadata; see `set_character_ignored`.
    pub ignored: bool,
    /// User confirmed a "possible" file IS a character (promoted to the pool).
    pub confirmed: bool,
    /// If the chooser renamed this file, the path it was originally shipped
    /// under (so the UI can show it's assigned and offer restore).
    pub original_rel_path: Option<String>,
    /// The chooser disabled this file (renamed it out of its slot). It no
    /// longer loads; restore brings it back.
    pub user_disabled: bool,
    /// The chooser unassigned this file (`char_unassigned<N>`): removed from a
    /// slot but kept available in the pool. Restore brings it back.
    pub user_unassigned: bool,
}

/// A vanilla character slot exposed to the frontend.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CharacterSlot {
    pub color: String,
    pub full_name: String,
    pub short_name: String,
}

/// Full discovery result: the static 20 slots plus every discovered candidate.
/// The frontend groups candidates by `detected_color` for slot occupancy
/// (winner = lowest `load_rank` among active) and buckets the rest as
/// potential characters.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CharactersResponse {
    pub slots: Vec<CharacterSlot>,
    pub candidates: Vec<CharacterCandidate>,
}

fn packs_dir() -> Result<PathBuf, String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    Ok(install_dir.join("Mods").join("Packs"))
}

/// Active pack ids in load order, as recorded in Playlunky's
/// `Mods/Packs/load_order.txt`. Lines prefixed `--` are inactive and skipped.
/// Returns an empty list when the file is absent.
fn active_load_order(packs: &Path) -> Vec<String> {
    let path = packs.join("load_order.txt");
    let Ok(contents) = fs::read_to_string(path) else {
        return Vec::new();
    };
    contents
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with("--"))
        .map(|l| l.to_string())
        .collect()
}

/// Forward-slash path of `path` relative to `root`, or `None` if not nested.
fn rel_forward(root: &Path, path: &Path) -> Option<String> {
    let rel = path.strip_prefix(root).ok()?;
    Some(rel.to_string_lossy().replace('\\', "/"))
}

/// Recursively collect every `.png` and every metadata sidecar (`.json` /
/// `.name`) under `root`, each as a `(forward-slash rel path, absolute path)`
/// pair. Iterative to avoid deep recursion on oddly-nested packs.
fn crawl(root: &Path) -> (Vec<(String, PathBuf)>, Vec<(String, PathBuf)>) {
    let mut pngs = Vec::new();
    let mut sidecars = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let Ok(ft) = entry.file_type() else {
                continue;
            };
            let path = entry.path();
            if ft.is_dir() {
                stack.push(path);
            } else if ft.is_file() {
                let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
                    continue;
                };
                let lower = name.to_lowercase();
                if lower.ends_with(".png") {
                    if let Some(rel) = rel_forward(root, &path) {
                        pngs.push((rel, path));
                    }
                } else if lower.ends_with(".json") || lower.ends_with(".name") {
                    if let Some(rel) = rel_forward(root, &path) {
                        sidecars.push((rel, path));
                    }
                }
            }
        }
    }
    (pngs, sidecars)
}

/// Find the metadata sidecar for a candidate. Pairs by the color token (the
/// metadata travels with the character), preferring one in the same directory
/// as the PNG, then anywhere in the pack. Prefers the newer `char_<color>.json`
/// over the older line-delimited `char_<color>.name`. Unknown-color candidates
/// fall back to a same-stem sibling. Returns the sidecar's rel path + parsed
/// metadata.
fn pair_metadata(
    png_rel: &str,
    color: Option<&str>,
    sidecars: &[(String, PathBuf)],
) -> Option<(String, CharacterMeta)> {
    let png_dir = png_rel.rsplit_once('/').map(|(d, _)| d).unwrap_or("");
    let basename = |rel: &str| {
        rel.rsplit_once('/')
            .map(|(_, n)| n.to_string())
            .unwrap_or_else(|| rel.to_string())
    };
    let dir_of = |rel: &str| {
        rel.rsplit_once('/')
            .map(|(d, _)| d.to_string())
            .unwrap_or_default()
    };

    // Candidate sidecar filenames in preference order.
    let targets: Vec<String> = match color {
        Some(color) => vec![format!("char_{color}.json"), format!("char_{color}.name")],
        None => {
            let stem = png_rel.strip_suffix(".png")?;
            vec![format!("{stem}.json"), format!("{stem}.name")]
                .into_iter()
                .map(|t| basename(&t))
                .collect()
        }
    };

    for target in &targets {
        // Same directory as the png wins; else take any match in the pack.
        let mut same_dir: Option<&(String, PathBuf)> = None;
        let mut anywhere: Option<&(String, PathBuf)> = None;
        for s in sidecars {
            if !basename(&s.0).eq_ignore_ascii_case(target) {
                continue;
            }
            if dir_of(&s.0) == png_dir {
                same_dir = Some(s);
                break;
            }
            anywhere.get_or_insert(s);
        }
        if let Some(hit) = same_dir.or(anywhere) {
            if let Some(meta) = read_meta(&hit.1) {
                return Some((hit.0.clone(), meta));
            }
        }
    }
    None
}

/// Parse a sidecar into metadata. `.json` is the structured schema; `.name` is
/// the older format: the full name on the first line, the short name on the
/// second.
fn read_meta(path: &Path) -> Option<CharacterMeta> {
    let raw = fs::read_to_string(path).ok()?;
    let is_name = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("name"))
        .unwrap_or(false);
    if is_name {
        let mut lines = raw.lines().map(str::trim).filter(|l| !l.is_empty());
        return Some(CharacterMeta {
            full_name: lines.next().map(String::from),
            short_name: lines.next().map(String::from),
            color: None,
            gender: None,
        });
    }
    serde_json::from_str::<CharacterMeta>(&raw).ok()
}

/// Discover character-sheet candidates, tagged with load-order/active state for
/// conflict resolution. By default scans only active mods (the common case,
/// and cheap even with a huge disabled library); `include_inactive` widens it
/// to every pack. `pack_id` scopes the scan to a single pack (for the per-pack
/// variant), scanning it regardless of active state.
#[tauri::command]
pub async fn get_characters(
    include_inactive: bool,
    pack_id: Option<String>,
) -> Result<CharactersResponse, String> {
    tauri::async_runtime::spawn_blocking(move || get_characters_sync(include_inactive, pack_id))
        .await
        .map_err(|e| format!("character scan panicked: {e}"))?
}

fn get_characters_sync(
    include_inactive: bool,
    pack_filter: Option<String>,
) -> Result<CharactersResponse, String> {
    let packs = packs_dir()?;
    let slots = VANILLA_CHARACTERS
        .iter()
        .map(|c| CharacterSlot {
            color: c.color.to_string(),
            full_name: c.full_name.to_string(),
            short_name: c.short_name.to_string(),
        })
        .collect();

    if !packs.exists() {
        return Ok(CharactersResponse {
            slots,
            candidates: Vec::new(),
        });
    }

    let order = active_load_order(&packs);
    let rank_of = |id: &str| order.iter().position(|p| p == id);
    let non_char = non_char_texture_names();

    let mut candidates = Vec::new();
    for entry in fs::read_dir(&packs).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        let pack_id = entry.file_name().to_string_lossy().to_string();
        // Skip Playlunky's cache dir and any dot-folders.
        if pack_id.starts_with('.') {
            continue;
        }
        // Single-pack mode scans just that pack (any state); otherwise scope to
        // active mods unless the caller opted into inactive too.
        let load_rank = rank_of(&pack_id);
        let active = load_rank.is_some();
        match &pack_filter {
            Some(filter) => {
                if &pack_id != filter {
                    continue;
                }
            }
            None => {
                if !active && !include_inactive {
                    continue;
                }
            }
        }
        let pack_root = entry.path();
        let (pngs, sidecars) = crawl(&pack_root);
        let state = read_character_state(&pack_id);
        let ignored_set = &state.ignored;

        for (rel, abs) in pngs {
            let dims = image::image_dimensions(&abs).ok();
            let file_name = rel.rsplit_once('/').map(|(_, n)| n).unwrap_or(&rel);
            let Some(cls) = classify(file_name, dims) else {
                continue;
            };
            // Drop known vanilla non-character textures (e.g. monsters_olmec.png
            // that happens to be char-sized) unless the name literally claims a
            // slot. Definite `char_<color>` files are always kept.
            if cls.confidence != Confidence::Definite
                && non_char.contains(&file_name.to_lowercase())
            {
                continue;
            }
            let (width, height) = dims.unwrap_or((0, 0));
            let (meta_rel_path, metadata) =
                match pair_metadata(&rel, cls.color.as_deref(), &sidecars) {
                    Some((rel, meta)) => (Some(rel), Some(meta)),
                    None => (None, None),
                };
            let ignored = ignored_set.iter().any(|p| p == &rel);
            let confirmed = state.confirmed.iter().any(|p| p == &rel);
            let rename = state.renames.iter().find(|r| r.current == rel);
            let original_rel_path = rename.map(|r| r.original.clone());
            let name_lower = file_name.to_lowercase();
            let user_disabled = is_parked_name(&name_lower, "char_disabled");
            let user_unassigned = is_parked_name(&name_lower, "char_unassigned");
            candidates.push(CharacterCandidate {
                pack_id: pack_id.clone(),
                file_name: file_name.to_string(),
                rel_path: rel,
                is_full: cls.is_full,
                name_mismatch: cls.name_mismatch,
                width,
                height,
                dims_ok: cls.dims_ok,
                detected_color: cls.color,
                confidence: cls.confidence,
                meta_rel_path,
                metadata,
                active,
                load_rank,
                ignored,
                confirmed,
                original_rel_path,
                user_disabled,
                user_unassigned,
            });
        }
    }

    Ok(CharactersResponse { slots, candidates })
}

/// Whether a lowercased texture basename is one of the 20 real player character
/// sheets (`char_<knowncolor>[_full].png`). Non-player `char_*` sheets like
/// `char_hired.png` / `char_eggchild.png` return false.
fn is_player_char_texture(name_lower: &str) -> bool {
    let Some(stem) = name_lower.strip_suffix(".png") else {
        return false;
    };
    let base = stem.strip_suffix("_full").unwrap_or(stem);
    base.strip_prefix("char_")
        .map(is_known_color)
        .unwrap_or(false)
}

/// Lowercased basenames of known vanilla `Data/Textures` PNGs that are NOT one
/// of the 20 player characters. Used to drop obvious non-character textures (a
/// mod's `monsters_olmec.png`, `floor_cave.png`, and even non-player
/// `char_hired.png`) from detection while never filtering a real player sheet.
fn non_char_texture_names() -> HashSet<String> {
    ml2_assets::known_texture_png_names()
        .map(|n| n.to_lowercase())
        .filter(|n| !is_player_char_texture(n))
        .collect()
}

// --- Per-pack character state (declarative, under `.ml`) --------------------

/// Modlunky-local per-pack character state, stored at
/// `Mods/.ml/pack-metadata/<id>/character-state.json`. Holds the user's "not a
/// character" suppressions and the record of files we've renamed (so a rename
/// can be undone and, later, re-applied after a mod update re-extracts the
/// originals).
#[derive(Debug, Default, Serialize, Deserialize)]
#[serde(default)]
struct CharacterState {
    /// Rel paths (relative to the pack root) the user flagged as not a
    /// character, so they stop surfacing in the chooser.
    ignored: Vec<String>,
    /// Rel paths the user confirmed ARE characters, promoting a "possible"
    /// (dimensions-only) match out of the review bucket into the usable pool.
    confirmed: Vec<String>,
    /// Files the chooser has renamed within the pack, keyed by their current
    /// path, remembering where they were originally shipped.
    renames: Vec<Rename>,
}

/// One renamed character: where its PNG lives now, where it was shipped, and
/// (if it had one) the paired metadata sidecar's original/current paths, so a
/// character moves and restores as a unit. `disabled` marks a rename that
/// moved the file out of a slot to stop it loading.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Rename {
    /// PNG rel path as originally shipped in the pack.
    original: String,
    /// PNG rel path the file currently lives at.
    current: String,
    #[serde(default)]
    disabled: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    sidecar_original: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    sidecar_current: Option<String>,
}

fn pack_metadata_dir(pack_id: &str) -> Result<PathBuf, String> {
    if pack_id.contains('/') || pack_id.contains('\\') || pack_id.contains("..") {
        return Err(format!("invalid pack: {pack_id:?}"));
    }
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    Ok(install_dir
        .join("Mods")
        .join(".ml")
        .join("pack-metadata")
        .join(pack_id))
}

fn read_character_state(pack_id: &str) -> CharacterState {
    pack_metadata_dir(pack_id)
        .ok()
        .map(|d| d.join("character-state.json"))
        .and_then(|p| fs::read_to_string(p).ok())
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn write_character_state(pack_id: &str, state: &CharacterState) -> Result<(), String> {
    let dir = pack_metadata_dir(pack_id)?;
    fs::create_dir_all(&dir).map_err(|e| format!("mkdir {}: {e}", dir.display()))?;
    let path = dir.join("character-state.json");
    let body = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
    fs::write(&path, body).map_err(|e| format!("write {}: {e}", path.display()))
}

/// Flag (or un-flag) a pack file as "not a character" so the chooser stops
/// showing it. Persisted in the pack's `.ml` state; idempotent.
#[tauri::command]
pub fn set_character_ignored(
    pack_id: String,
    rel_path: String,
    ignored: bool,
) -> Result<(), String> {
    if rel_path.contains("..") {
        return Err(format!("invalid path: {rel_path:?}"));
    }
    let mut state = read_character_state(&pack_id);
    let present = state.ignored.iter().any(|p| p == &rel_path);
    if ignored {
        // Ignoring and confirming are mutually exclusive.
        state.confirmed.retain(|p| p != &rel_path);
        if present {
            return Ok(());
        }
        state.ignored.push(rel_path);
    } else {
        if !present {
            return Ok(());
        }
        state.ignored.retain(|p| p != &rel_path);
    }
    write_character_state(&pack_id, &state)
}

/// Confirm (or un-confirm) that a "possible" file really is a character,
/// promoting it out of the review bucket into the usable pool. Confirming
/// clears any "not a character" flag; the two are mutually exclusive.
#[tauri::command]
pub fn set_character_confirmed(
    pack_id: String,
    rel_path: String,
    confirmed: bool,
) -> Result<(), String> {
    if rel_path.contains("..") {
        return Err(format!("invalid path: {rel_path:?}"));
    }
    let mut state = read_character_state(&pack_id);
    let present = state.confirmed.iter().any(|p| p == &rel_path);
    if confirmed {
        state.ignored.retain(|p| p != &rel_path);
        if present {
            return Ok(());
        }
        state.confirmed.push(rel_path);
    } else {
        if !present {
            return Ok(());
        }
        state.confirmed.retain(|p| p != &rel_path);
    }
    write_character_state(&pack_id, &state)
}

// --- Assign / disable / restore ---------------------------------------------

/// Basename a sheet takes for a slot: `char_<color>.png`, or
/// `char_<color>_full.png` for an augmented sheet. Assign renames a file in
/// place (keeping its directory) rather than relocating it, so mods keep their
/// own layout.
fn char_basename(color: &str, full: bool) -> String {
    if full {
        format!("char_{color}_full.png")
    } else {
        format!("char_{color}.png")
    }
}

/// Directory portion of a forward-slash rel path (empty for a root file).
fn dir_of(rel: &str) -> &str {
    rel.rsplit_once('/').map(|(d, _)| d).unwrap_or("")
}

/// A rel path for `new_basename` in the same directory as `rel`.
fn sibling_rel(rel: &str, new_basename: &str) -> String {
    let dir = dir_of(rel);
    if dir.is_empty() {
        new_basename.to_string()
    } else {
        format!("{dir}/{new_basename}")
    }
}

/// Join a forward-slash pack-relative path onto the pack root, component by
/// component (so it works on Windows and can't contain a raw separator).
fn pack_join(pack_root: &Path, rel: &str) -> PathBuf {
    let mut p = pack_root.to_path_buf();
    for comp in rel.split('/') {
        if comp.is_empty() || comp == "." {
            continue;
        }
        p.push(comp);
    }
    p
}

fn validate_pack(pack_id: &str) -> Result<(), String> {
    if pack_id.is_empty()
        || pack_id.starts_with('.')
        || pack_id.contains('/')
        || pack_id.contains('\\')
        || pack_id.contains("..")
    {
        return Err(format!("invalid pack: {pack_id:?}"));
    }
    Ok(())
}

fn validate_rel(rel: &str) -> Result<(), String> {
    if rel.is_empty() || rel.contains("..") || rel.starts_with('/') || rel.starts_with('\\') {
        return Err(format!("invalid path: {rel:?}"));
    }
    Ok(())
}

/// Rename a file within a pack. No-op when source and target are the same.
/// Refuses to clobber a different existing file at the target.
fn move_file_in_pack(pack_root: &Path, from_rel: &str, to_rel: &str) -> Result<(), String> {
    if from_rel == to_rel {
        return Ok(());
    }
    let from = pack_join(pack_root, from_rel);
    let to = pack_join(pack_root, to_rel);
    if !from.exists() {
        return Err(format!("file not found: {from_rel}"));
    }
    if to.exists() {
        return Err(format!("target already exists: {to_rel}"));
    }
    if let Some(parent) = to.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
    }
    fs::rename(&from, &to).map_err(|e| format!("rename {from_rel} -> {to_rel}: {e}"))
}

/// Next free `<prefix><N>.png` name in the same directory as `from_rel`.
/// `prefix` is `char_disabled` or `char_unassigned`.
fn next_parked_rel(pack_root: &Path, from_rel: &str, prefix: &str) -> String {
    let dir = from_rel.rsplit_once('/').map(|(d, _)| d).unwrap_or("");
    let mut n = 0;
    loop {
        let name = format!("{prefix}{n}.png");
        let rel = if dir.is_empty() {
            name
        } else {
            format!("{dir}/{name}")
        };
        if !pack_join(pack_root, &rel).exists() {
            return rel;
        }
        n += 1;
    }
}

/// True when a basename is a parked `<prefix><N>.png` (e.g. `char_unassigned3`).
fn is_parked_name(name_lower: &str, prefix: &str) -> bool {
    name_lower
        .strip_suffix(".png")
        .and_then(|s| s.strip_prefix(prefix))
        .map(|n| !n.is_empty() && n.chars().all(|c| c.is_ascii_digit()))
        .unwrap_or(false)
}

fn pack_root_for(pack_id: &str) -> Result<PathBuf, String> {
    validate_pack(pack_id)?;
    Ok(packs_dir()?.join(pack_id))
}

/// Assigns a character sheet to a slot: renames the PNG to the canonical
/// `char_<color>` path (base or `_full` per its dimensions) and moves the
/// paired metadata sidecar to `char_<color>.json`/`.name`. Also serves as
/// "fix misnamed" (assign a file to its own color to correct the `_full`
/// naming). Records the shipped originals so it can be undone.
#[tauri::command]
pub fn assign_character(pack_id: String, rel_path: String, color: String) -> Result<(), String> {
    validate_rel(&rel_path)?;
    if !is_known_color(&color) {
        return Err(format!("unknown character color: {color}"));
    }
    let pack_root = pack_root_for(&pack_id)?;
    let src = pack_join(&pack_root, &rel_path);
    if !src.exists() {
        return Err(format!("file not found: {rel_path}"));
    }
    let full = image::image_dimensions(&src)
        .map(|(_, h)| h == 2224)
        .unwrap_or(false);
    // Rename in place: keep the file's directory, just change its basename.
    let target_rel = sibling_rel(&rel_path, &char_basename(&color, full));

    // Find the paired sidecar (by the source's own color token, else sibling).
    let src_color = classify(basename(&rel_path), None).and_then(|c| c.color);
    let (_, sidecars) = crawl(&pack_root);
    let sidecar = pair_metadata(&rel_path, src_color.as_deref(), &sidecars);

    let mut state = read_character_state(&pack_id);
    let existing = state
        .renames
        .iter()
        .find(|r| r.current == rel_path)
        .cloned();
    let png_original = existing
        .as_ref()
        .map(|r| r.original.clone())
        .unwrap_or_else(|| rel_path.clone());
    let mut sidecar_original = existing.as_ref().and_then(|r| r.sidecar_original.clone());
    state.renames.retain(|r| r.current != rel_path);

    // PNG move is the critical step; a sidecar hiccup shouldn't lose it.
    move_file_in_pack(&pack_root, &rel_path, &target_rel)?;

    let mut sidecar_current = None;
    if let Some((sc_rel, _)) = &sidecar {
        let ext = if sc_rel.to_lowercase().ends_with(".name") {
            "name"
        } else {
            "json"
        };
        // Rename the sidecar in place too.
        let sc_target = sibling_rel(sc_rel, &format!("char_{color}.{ext}"));
        if sc_target == *sc_rel || move_file_in_pack(&pack_root, sc_rel, &sc_target).is_ok() {
            sidecar_current = Some(sc_target);
            sidecar_original.get_or_insert_with(|| sc_rel.clone());
        }
    }

    let back_to_shipped =
        target_rel == png_original && sidecar_current.as_deref() == sidecar_original.as_deref();
    if !back_to_shipped {
        state.renames.push(Rename {
            original: png_original,
            current: target_rel,
            disabled: false,
            sidecar_original,
            sidecar_current,
        });
    }
    write_character_state(&pack_id, &state)
}

/// Removes a sheet from its slot by renaming it to `<prefix><N>.png` so it
/// stops occupying the slot. `char_unassigned*` keeps it as an available
/// character in the pool; `char_disabled*` marks it explicitly off. The
/// sidecar is left in place but remembered so restore brings the pair back.
fn park_character(
    pack_id: &str,
    rel_path: &str,
    prefix: &str,
    disabled: bool,
) -> Result<(), String> {
    validate_rel(rel_path)?;
    let pack_root = pack_root_for(pack_id)?;
    let target_rel = next_parked_rel(&pack_root, rel_path, prefix);

    let mut state = read_character_state(pack_id);
    let existing = state
        .renames
        .iter()
        .find(|r| r.current == rel_path)
        .cloned();
    let png_original = existing
        .as_ref()
        .map(|r| r.original.clone())
        .unwrap_or_else(|| rel_path.to_string());
    let sidecar_original = existing.as_ref().and_then(|r| r.sidecar_original.clone());
    let sidecar_current = existing.as_ref().and_then(|r| r.sidecar_current.clone());
    state.renames.retain(|r| r.current != rel_path);

    move_file_in_pack(&pack_root, rel_path, &target_rel)?;
    state.renames.push(Rename {
        original: png_original,
        current: target_rel,
        disabled,
        sidecar_original,
        sidecar_current,
    });
    write_character_state(pack_id, &state)
}

/// Unassign a sheet: remove it from its slot but keep it available in the pool
/// (renamed to `char_unassigned<N>.png`).
#[tauri::command]
pub fn unassign_character(pack_id: String, rel_path: String) -> Result<(), String> {
    park_character(&pack_id, &rel_path, "char_unassigned", false)
}

/// Disable a sheet: remove it from its slot and mark it explicitly off
/// (renamed to `char_disabled<N>.png`).
#[tauri::command]
pub fn disable_character(pack_id: String, rel_path: String) -> Result<(), String> {
    park_character(&pack_id, &rel_path, "char_disabled", true)
}

/// Restores a renamed character (and its sidecar) to the paths it shipped
/// under, and drops the record.
#[tauri::command]
pub fn restore_character(pack_id: String, rel_path: String) -> Result<(), String> {
    validate_rel(&rel_path)?;
    let pack_root = pack_root_for(&pack_id)?;
    let mut state = read_character_state(&pack_id);
    let Some(rec) = state
        .renames
        .iter()
        .find(|r| r.current == rel_path)
        .cloned()
    else {
        return Err(format!("no rename to restore for {rel_path}"));
    };
    move_file_in_pack(&pack_root, &rel_path, &rec.original)?;
    if let (Some(cur), Some(orig)) = (&rec.sidecar_current, &rec.sidecar_original) {
        // Best-effort: a missing/renamed sidecar shouldn't block the PNG restore.
        let _ = move_file_in_pack(&pack_root, cur, orig);
    }
    state.renames.retain(|r| r.current != rel_path);
    write_character_state(&pack_id, &state)
}

fn basename(rel: &str) -> &str {
    rel.rsplit_once('/').map(|(_, n)| n).unwrap_or(rel)
}

// Preview crop: the standing/idle frame, i.e. the top-left 128x128 chunk of a
// char sheet (the `standing` chunk in ml2_sprites' character map). It stays
// crisp scaled down to a thumbnail, where the larger portrait crop looked
// muddy, and lives in the top grid shared by both the base and `_full` sheets.
const PREVIEW_X: u32 = 0;
const PREVIEW_Y: u32 = 0;
const PREVIEW_W: u32 = 128;
const PREVIEW_H: u32 = 128;

/// Returns a portrait preview of a candidate sheet as a base64 PNG data URL.
/// Fetched on demand (per visible candidate) so `get_characters` stays a cheap
/// header-only scan.
#[tauri::command]
pub async fn get_character_preview(pack_id: String, rel_path: String) -> Result<String, String> {
    if rel_path.contains("..") || rel_path.starts_with('/') || rel_path.starts_with('\\') {
        return Err(format!("invalid path: {rel_path:?}"));
    }
    if pack_id.contains('/') || pack_id.contains('\\') || pack_id.contains("..") {
        return Err(format!("invalid pack: {pack_id:?}"));
    }
    let path = packs_dir()?.join(&pack_id).join(&rel_path);
    if !path.exists() {
        return Err(format!("not found: {}", path.display()));
    }
    tauri::async_runtime::spawn_blocking(move || -> Result<String, String> {
        let img = image::open(&path).map_err(|e| e.to_string())?;
        use image::GenericImageView;
        let (w, h) = img.dimensions();
        // Clamp the crop to the image bounds so non-standard-sized candidates
        // still yield a best-effort preview instead of erroring.
        let cw = PREVIEW_W.min(w.saturating_sub(PREVIEW_X.min(w)));
        let ch = PREVIEW_H.min(h.saturating_sub(PREVIEW_Y.min(h)));
        let (x, y, cw, ch) = if cw == 0 || ch == 0 {
            (0, 0, w, h)
        } else {
            (PREVIEW_X.min(w), PREVIEW_Y.min(h), cw, ch)
        };
        let crop = image::imageops::crop_imm(&img, x, y, cw, ch).to_image();
        let mut buf: Vec<u8> = Vec::new();
        image::DynamicImage::ImageRgba8(crop)
            .write_to(&mut std::io::Cursor::new(&mut buf), image::ImageFormat::Png)
            .map_err(|e| e.to_string())?;
        let mut out = String::from("data:image/png;base64,");
        STANDARD.encode_string(&buf, &mut out);
        Ok(out)
    })
    .await
    .map_err(|e| format!("preview task panicked: {e}"))?
}

fn png_data_url(bytes: &[u8]) -> String {
    let mut out = String::from("data:image/png;base64,");
    STANDARD.encode_string(bytes, &mut out);
    out
}

/// Cache subdir under the app cache dir for cropped vanilla previews. The
/// suffix tracks the crop region so changing it (e.g. portrait -> standing
/// frame) sidesteps stale caches from an earlier crop instead of serving them.
const PORTRAIT_CACHE_SUBDIR: &str = "character-standing";

/// Portrait of a vanilla character (the one a mod slot replaces). Cropped from
/// the user's own extracted `char_<color>.png` the first time it's requested,
/// then cached in app data so later opens don't need the Extracted dir at all.
/// Returns `None` (not an error) when the user has never extracted assets, so
/// the frontend can fall back to a name + color chip.
#[tauri::command]
pub async fn get_vanilla_character_preview(color: String) -> Result<Option<String>, String> {
    if !is_known_color(&color) {
        return Err(format!("unknown character color: {color}"));
    }
    tauri::async_runtime::spawn_blocking(move || vanilla_preview_sync(&color))
        .await
        .map_err(|e| format!("vanilla preview task panicked: {e}"))?
}

fn vanilla_preview_sync(color: &str) -> Result<Option<String>, String> {
    let cached = crate::paths::app_cache_dir()
        .map(|d| d.join(PORTRAIT_CACHE_SUBDIR).join(format!("{color}.png")));

    // Serve from cache when we've already cropped this portrait.
    if let Some(cached) = &cached {
        if let Ok(bytes) = fs::read(cached) {
            return Ok(Some(png_data_url(&bytes)));
        }
    }

    // Otherwise crop from the user's extracted char sheet, cache, and serve.
    let Some(install_dir) = crate::config::load().install_dir else {
        return Ok(None);
    };
    let sheet = install_dir
        .join("Mods")
        .join("Extracted")
        .join("Data")
        .join("Textures")
        .join(format!("char_{color}.png"));
    if !sheet.exists() {
        return Ok(None);
    }
    let img = image::open(&sheet).map_err(|e| e.to_string())?;
    let crop =
        image::imageops::crop_imm(&img, PREVIEW_X, PREVIEW_Y, PREVIEW_W, PREVIEW_H).to_image();
    let mut buf: Vec<u8> = Vec::new();
    image::DynamicImage::ImageRgba8(crop)
        .write_to(&mut std::io::Cursor::new(&mut buf), image::ImageFormat::Png)
        .map_err(|e| e.to_string())?;

    // Best-effort cache write; a failure just means we recrop next time.
    if let Some(cached) = &cached {
        if let Some(parent) = cached.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::write(cached, &buf);
    }
    Ok(Some(png_data_url(&buf)))
}

/// Opens the managed character chooser in its own window. Single-instance per
/// scope: focuses an existing window instead of opening a second. When `pack`
/// is set the window is scoped to that one pack (the per-pack variant);
/// otherwise it's the global (active-mods) view. Mirrors
/// `open_level_editor_window`; must be async so Tauri v2's `build()` can round
/// trip to the main runtime thread.
#[tauri::command]
pub async fn open_character_chooser_window(
    app: AppHandle,
    pack: Option<String>,
) -> Result<(), String> {
    let label = match &pack {
        Some(p) => {
            let slug: String = p
                .to_lowercase()
                .chars()
                .map(|c| {
                    if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                        c
                    } else {
                        '_'
                    }
                })
                .collect();
            format!("character-chooser-{slug}")
        }
        None => "character-chooser".to_string(),
    };
    if let Some(existing) = app.get_webview_window(&label) {
        let _ = existing.set_focus();
        return Ok(());
    }
    // The init script runs before any app JS, so App.tsx reads this
    // synchronously on first render to pick the chooser shell.
    let context = match &pack {
        Some(p) => format!(
            "window.__charChooserContext = {{ kind: \"characters\", pack: {} }};",
            serde_json::to_string(p).map_err(|e| e.to_string())?
        ),
        None => "window.__charChooserContext = { kind: \"characters\" };".to_string(),
    };
    let title = match &pack {
        Some(p) => format!("Characters: {p} - Modlunky2"),
        None => "Character Chooser - Modlunky2".to_string(),
    };
    let window = WebviewWindowBuilder::new(&app, &label, WebviewUrl::App("/".into()))
        .title(&title)
        .inner_size(1200.0, 900.0)
        .min_inner_size(900.0, 640.0)
        .resizable(true)
        .initialization_script(&context)
        .build()
        .map_err(|e| format!("open window: {e}"))?;
    if let Err(e) = crate::window_icon::apply_window_icon(&window) {
        tracing::warn!("failed to set window icon on character chooser: {e}");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dims() -> Option<(u32, u32)> {
        Some((2048, 2048))
    }

    #[test]
    fn definite_known_color() {
        let c = classify("char_blue.png", dims()).unwrap();
        assert_eq!(c.confidence, Confidence::Definite);
        assert_eq!(c.color.as_deref(), Some("blue"));
        assert!(!c.is_full);
        assert!(c.dims_ok);
    }

    #[test]
    fn definite_full_variant_by_name_and_by_dims() {
        let by_name = classify("char_red_full.png", Some((2048, 2224))).unwrap();
        assert_eq!(by_name.color.as_deref(), Some("red"));
        assert!(by_name.is_full);
        // Augmented sheet shipped under a plain name is still full via its height.
        let by_dims = classify("char_red.png", Some((2048, 2224))).unwrap();
        assert!(by_dims.is_full);
    }

    #[test]
    fn misnamed_full_at_base_dimensions() {
        // Name claims _full but it's really a 2048x2048 base sheet.
        let c = classify("char_blue_full.png", Some((2048, 2048))).unwrap();
        assert!(c.name_mismatch);
        assert!(!c.is_full, "true nature is base by dimensions");
        assert_eq!(c.color.as_deref(), Some("blue"));
    }

    #[test]
    fn misnamed_base_at_full_dimensions() {
        // Plain name but it's really a 2048x2224 full sheet.
        let c = classify("char_blue.png", Some((2048, 2224))).unwrap();
        assert!(c.name_mismatch);
        assert!(c.is_full, "true nature is full by dimensions");
    }

    #[test]
    fn correctly_named_variants_have_no_mismatch() {
        assert!(
            !classify("char_blue.png", Some((2048, 2048)))
                .unwrap()
                .name_mismatch
        );
        assert!(
            !classify("char_blue_full.png", Some((2048, 2224)))
                .unwrap()
                .name_mismatch
        );
    }

    #[test]
    fn definite_flags_wrong_dimensions() {
        let c = classify("char_blue.png", Some((512, 512))).unwrap();
        assert_eq!(c.confidence, Confidence::Definite);
        assert!(
            !c.dims_ok,
            "wrong-sized char_blue should flag dims_ok=false"
        );
    }

    #[test]
    fn likely_unknown_color_with_char_dims() {
        let c = classify("char_sonic.png", dims()).unwrap();
        assert_eq!(c.confidence, Confidence::Likely);
        assert!(c.color.is_none());
    }

    #[test]
    fn char_prefixed_wrong_dims_is_not_a_candidate() {
        assert!(classify("char_sonic.png", Some((256, 256))).is_none());
    }

    #[test]
    fn parked_files_are_definite_characters() {
        // Parked by our own tool from a real character -> high confidence.
        for name in ["char_unassigned0.png", "char_disabled3.png"] {
            let c = classify(name, dims()).unwrap();
            assert_eq!(c.confidence, Confidence::Definite, "{name}");
            assert!(c.color.is_none(), "{name} holds no slot");
        }
        // But a bare `char_unassigned` (no index) is just an unknown char_ file.
        assert_eq!(
            classify("char_unassigned.png", dims()).unwrap().confidence,
            Confidence::Likely,
        );
    }

    #[test]
    fn parked_full_sheet_is_not_flagged_misnamed() {
        // Parking a full sheet drops `_full`; that's intentional, not a mismatch.
        let c = classify("char_disabled0.png", Some((2048, 2224))).unwrap();
        assert!(c.is_full);
        assert!(!c.name_mismatch);
    }

    #[test]
    fn possible_arbitrary_name_char_dims() {
        let c = classify("asfeafasf.png", dims()).unwrap();
        assert_eq!(c.confidence, Confidence::Possible);
        assert!(c.color.is_none());
    }

    #[test]
    fn non_char_sized_arbitrary_png_ignored() {
        assert!(classify("logo.png", Some((256, 256))).is_none());
    }

    #[test]
    fn non_png_ignored() {
        assert!(classify("char_blue.dds", dims()).is_none());
    }

    #[test]
    fn case_insensitive_name() {
        let c = classify("Char_Blue.PNG", dims()).unwrap();
        assert_eq!(c.color.as_deref(), Some("blue"));
    }

    #[test]
    fn char_basename_and_in_place_rename() {
        assert_eq!(char_basename("blue", false), "char_blue.png");
        assert_eq!(char_basename("blue", true), "char_blue_full.png");
        // Renames keep the source directory.
        assert_eq!(
            sibling_rel(
                "Data/Textures/Entities/char_sonic_full.png",
                "char_blue_full.png"
            ),
            "Data/Textures/Entities/char_blue_full.png"
        );
        assert_eq!(sibling_rel("weird.png", "char_blue.png"), "char_blue.png");
    }

    #[test]
    fn classify_detects_color_without_dimensions() {
        // assign_character resolves the source's slot by name only.
        assert_eq!(
            classify("char_blue.png", None)
                .and_then(|c| c.color)
                .as_deref(),
            Some("blue")
        );
        assert!(classify("asfeafasf.png", None).is_none());
    }

    #[test]
    fn all_twenty_colors_are_definite() {
        for vc in VANILLA_CHARACTERS {
            let name = format!("char_{}.png", vc.color);
            let c = classify(&name, dims()).unwrap();
            assert_eq!(c.confidence, Confidence::Definite, "{name}");
            assert_eq!(c.color.as_deref(), Some(vc.color));
        }
    }
}
