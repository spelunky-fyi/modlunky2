//! `dmpreview.tok`: arena preview thumbnail format.
//!
//! The `dmpreview.tok` file is a fixed 18,000-byte blob shipped inside
//! the arena assets that renders 40 small preview thumbnails on the
//! arena-select screen (one per `dm{world}-{level}.lvl` file). Each
//! preview is a `PREVIEW_WIDTH x PREVIEW_HEIGHT` (30 x 15) grid of bytes;
//! each byte maps to a small `PreviewImage` tile drawn by the game.
//!
//! Rebuilding a preview requires:
//!  - The arena's `.lvl` file to derive tile placements from.
//!  - A tile-code lookup that resolves each `%value` back to its base
//!    tilecode name (strip everything at or after the first `%\d+`).
//!  - A per-template `(row, col)` offset table that decides where each
//!    setroom lands in the 30x15 grid, keyed on whether the arena is a
//!    "small" (2x2 rooms) or "large" (3x2 rooms) map.
//!  - A handful of special-case rendering rules for multi-tile
//!    entities (trees, mushrooms, chainandblocks_ceiling, crushtraplarge,
//!    conveyer flip under ONLYFLIP).
//!
//! No wiring on the Rust side today: the arena editor UI hasn't been
//! built yet. The format knowledge lives here so a future editor doesn't
//! have to reverse-engineer any of it again.

use std::collections::HashMap;

use crate::error::{LevelError, Result};
use crate::file::LevelFile;
use crate::settings::LevelSettingValue;
use crate::templates::TemplateSetting;

// ---- Wire-format constants --------------------------------------------

/// Preview grid width in preview cells (bytes).
pub const PREVIEW_WIDTH: usize = 30;
/// Preview grid height in preview cells (bytes).
pub const PREVIEW_HEIGHT: usize = 15;
/// Number of arenas per file.
pub const NUM_ARENAS: usize = 40;
/// Total on-disk size of a `dmpreview.tok` file.
pub const DMPREVIEW_SIZE: usize = 18_000;
/// Bytes per arena preview. `DMPREVIEW_SIZE / NUM_ARENAS`.
pub const ARENA_SIZE: usize = DMPREVIEW_SIZE / NUM_ARENAS;
/// One game-room in tile units. Not currently referenced elsewhere in
/// this file but preserved to document the setroom shape callers expect.
pub const ROOM_WIDTH: usize = 10;
/// Room height in tiles. See [`ROOM_WIDTH`].
pub const ROOM_HEIGHT: usize = 8;

// ---- Arena size ------------------------------------------------------

/// Whether an arena is a "small" (2x2 rooms, half the preview width) or
/// "large" (3x2 rooms, full preview width) layout. Derived from the
/// `\-size` setting in the arena's `.lvl` file: `2 2` -> small, `3 2` ->
/// large.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ArenaSize {
    Small,
    Large,
}

impl ArenaSize {
    /// Recover the arena size from the `\-size` LevelSetting value.
    /// Only `("2","2")` and `("3","2")` are accepted.
    pub fn from_size_setting(value: &LevelSettingValue) -> Option<Self> {
        let LevelSettingValue::Size(w, h) = value else {
            return None;
        };
        match (w.as_str(), h.as_str()) {
            ("2", "2") => Some(Self::Small),
            ("3", "2") => Some(Self::Large),
            _ => None,
        }
    }
}

// ---- PreviewImage enum ----------------------------------------------

/// Byte value at each cell of an arena preview. `Empty` is the special
/// sentinel `0xFF`. Every other variant has an exact byte value the game
/// draws; those values must be preserved because a pixel-diff against
/// the vanilla dmpreview.tok keys off them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum PreviewImage {
    Empty = 0xFF,
    Floor = 0x00,
    PushBlock = 0x01,
    Crate = 0x02,
    Ladder = 0x03,
    Vines = 0x04,
    Chain = 0x05,
    Pole = 0x06,
    Spikes = 0x07,
    CeilingSpikes = 0x08,
    BoneBlocks = 0x09,
    SpearTrap = 0x0A,
    FallingPlatform = 0x0B,
    ConveyerLeft = 0x0C,
    ConveyerRight = 0x0D,
    Tnt = 0x0E,
    Liquid = 0x0F,
    CrushTrap = 0x10,
    QuickSand = 0x11,
    Ice = 0x12,
    Spring = 0x13,
    Elevator = 0x14,
    Lasers = 0x15,
    SparkBalls = 0x16,
    RegenBlocks = 0x17,
    Tubes = 0x18,
    Foliage = 0x19,
}

impl PreviewImage {
    /// Byte value the game draws at this cell.
    pub const fn as_byte(self) -> u8 {
        self as u8
    }
}

/// Weird un-used-tile byte the game apparently draws above extended
/// `tree_base` / `mushroom_base` tiles. Named here rather than left as an
/// inline literal so a future audit can find the reference.
pub const WEIRD_UNUSED_TILE: u8 = 0x1A;

// ---- Arena-index tables ----------------------------------------------

/// Ordered list of the 40 arena `.lvl` filenames. Index in this list
/// equals the arena index in `dmpreview.tok`.
pub const ARENA_LEVEL_FILES: &[&str] = &[
    "dm1-1.lvl",
    "dm1-2.lvl",
    "dm1-3.lvl",
    "dm1-4.lvl",
    "dm1-5.lvl",
    "dm2-1.lvl",
    "dm2-2.lvl",
    "dm2-3.lvl",
    "dm2-4.lvl",
    "dm2-5.lvl",
    "dm3-1.lvl",
    "dm3-2.lvl",
    "dm3-3.lvl",
    "dm3-4.lvl",
    "dm3-5.lvl",
    "dm4-1.lvl",
    "dm4-2.lvl",
    "dm4-3.lvl",
    "dm4-4.lvl",
    "dm4-5.lvl",
    "dm5-1.lvl",
    "dm5-2.lvl",
    "dm5-3.lvl",
    "dm5-4.lvl",
    "dm5-5.lvl",
    "dm6-1.lvl",
    "dm6-2.lvl",
    "dm6-3.lvl",
    "dm6-4.lvl",
    "dm6-5.lvl",
    "dm7-1.lvl",
    "dm7-2.lvl",
    "dm7-3.lvl",
    "dm7-4.lvl",
    "dm7-5.lvl",
    "dm8-1.lvl",
    "dm8-2.lvl",
    "dm8-3.lvl",
    "dm8-4.lvl",
    "dm8-5.lvl",
];

/// Return the arena index for a `dm{world}-{level}.lvl` filename, or
/// None if the name isn't a known arena file.
pub fn arena_index_for_file(name: &str) -> Option<usize> {
    ARENA_LEVEL_FILES.iter().position(|&n| n == name)
}

/// Canonical display names for the 40 arenas, in wire order. Intended
/// for a future arena picker UI's section headers.
pub const ARENA_NAMES: &[&str] = &[
    "Dwelling - Boneyard",
    "Dwelling - Ladders",
    "Dwelling - The Boss Room",
    "Dwelling - The Dig",
    "Dwelling - Apartments",
    "Jungle - Vines",
    "Jungle - Ruins",
    "Jungle - No Roots",
    "Jungle - Tower to Heaven",
    "Jungle - Prickly",
    "Volcana - Treadmill",
    "Volcana - Precarious",
    "Volcana - Smelter",
    "Volcana - Scrapyard",
    "Volcana - Chained",
    "Tide Pool - Clam Bake",
    "Tide Pool - Barrier Reef",
    "Tide Pool - Pole Dance",
    "Tide Pool - Two Houses",
    "Tide Pool - Eight Treasures",
    "Temple of Anubis - Roundabout",
    "Temple of Anubis - Pyramid",
    "Temple of Anubis - Burial Chamber",
    "Temple of Anubis - Grinder",
    "Temple of Anubis - Sandpit",
    "Ice Caves - Ice Box",
    "Ice Caves - Bounce House",
    "Ice Caves - Sprung",
    "Ice Caves - The Platform",
    "Ice Caves - Forgotten God",
    "Neo Babylon - Zap Cage",
    "Neo Babylon - Fungal",
    "Neo Babylon - Holy Mountain",
    "Neo Babylon - Neo City",
    "Neo Babylon - Power Plant",
    "Sunken City - Scar Tissue",
    "Sunken City - Indigestion",
    "Sunken City - Temple of Frog",
    "Sunken City - Pipe Dream",
    "Sunken City - Passions",
];

// ---- Tilecode -> preview byte mapping --------------------------------

/// Map a base tile-code name (the part before any `%N` percent suffix)
/// to its preview byte. The "Double-check these" block is preserved:
/// those entries all resolve to `Empty` for now, mark them here if a
/// future audit finds a real mapping.
///
/// Returns None for unknown tile codes; callers decide whether that's
/// a legit "renders as nothing" (see `is_empty_tilecode`) or a bug.
pub fn preview_for_tile(name: &str) -> Option<PreviewImage> {
    use PreviewImage::*;
    Some(match name {
        "empty" => Empty,
        "babylon_floor" => Floor,
        "bone_block" => BoneBlocks,
        "climbing_pole" => Pole,
        "conveyorbelt_left" => ConveyerLeft,
        "conveyorbelt_right" => ConveyerRight,
        "crate" => Crate,
        "crushtrap" => CrushTrap,
        "crushtraplarge" => CrushTrap,
        "elevator" => Elevator,
        "falling_platform" => FallingPlatform,
        "floor_hard" => Empty,
        "floor" => Floor,
        "forcefield_top" => Lasers,
        "forcefield" => Lasers,
        "icefloor" => Ice,
        "jungle_spear_trap" => SpearTrap,
        "ladder_plat" => Ladder,
        "ladder" => Ladder,
        "lava" => Liquid,
        "minewood_floor" => Floor,
        "mushroom_base" => Foliage,
        "pagoda_floor" => Floor,
        "pagoda_platform" => Floor,
        "pipe" => Tubes,
        "powder_keg" => Tnt,
        "push_block" => PushBlock,
        "quicksand" => QuickSand,
        "regenerating_block" => RegenBlocks,
        "spark_trap" => SparkBalls,
        "spikes" => Spikes,
        "spring_trap" => Spring,
        "stone_floor" => Floor,
        "sunken_floor" => Floor,
        "temple_floor" => Floor,
        "thinice" => Ice,
        "thorn_vine" => Floor,
        "timed_forcefield" => Lasers,
        "tree_base" => Foliage,
        "upsidedown_spikes" => CeilingSpikes,
        "vine" => Vines,
        "water" => Liquid,
        "chainandblocks_ceiling" => Floor,
        "factory_generator" => Floor,
        "slidingwall_ceiling" => Floor,
        // Double-check these: resolve to Empty for now. A pixel-diff
        // against vanilla previews might reveal the real bytes; leave
        // as Empty until then.
        "bigspear_trap" => Empty,
        "giantclam" => Empty,
        "giant_frog" => Empty,
        "fountain_drain" => Empty,
        "idol_hold" => Empty,
        "landmine" => Empty,
        "laser_trap" => Empty,
        "slidingwall_switch" => Empty,
        _ => return None,
    })
}

/// Tile codes that legitimately render as nothing in a preview. Used by
/// the "unknown tilecode" warning check so it doesn't misfire on these.
pub fn is_empty_tilecode(name: &str) -> bool {
    matches!(name, "cavemanboss" | "cookfire" | "dm_spawn_point")
}

// ---- Setroom geometry ------------------------------------------------

/// Vertical offset (in preview cells) where a template's rooms start.
/// Only the four vanilla arena setroom names are populated; anything
/// else is a level-file authoring error and returns None.
pub fn row_offset_for(template_name: &str) -> Option<usize> {
    Some(match template_name {
        "setroom0-0" | "setroom0-1" | "setroom0-2" => 0,
        "setroom1-0" | "setroom1-1" | "setroom1-2" => 8,
        _ => return None,
    })
}

/// Horizontal offset (in preview cells) where a template's rooms start.
/// Depends on both the arena size and the template name. Small arenas
/// only have `-0` and `-1` columns; large arenas add `-2`.
pub fn column_offset_for(size: ArenaSize, template_name: &str) -> Option<usize> {
    Some(match (size, template_name) {
        (ArenaSize::Small, "setroom0-0") => 5,
        (ArenaSize::Small, "setroom0-1") => 15,
        (ArenaSize::Small, "setroom1-0") => 5,
        (ArenaSize::Small, "setroom1-1") => 15,
        (ArenaSize::Large, "setroom0-0") => 0,
        (ArenaSize::Large, "setroom0-1") => 10,
        (ArenaSize::Large, "setroom0-2") => 20,
        (ArenaSize::Large, "setroom1-0") => 0,
        (ArenaSize::Large, "setroom1-1") => 10,
        (ArenaSize::Large, "setroom1-2") => 20,
        _ => return None,
    })
}

// ---- Arena rendering -------------------------------------------------

/// One arena's preview as a `[u8; ARENA_SIZE]` buffer. Cells outside the
/// active setroom regions default to `Empty` (`0xFF`), which is exactly
/// what a fresh arena preview looks like.
#[derive(Debug, Clone)]
pub struct Arena {
    pub bytes: [u8; ARENA_SIZE],
}

impl Default for Arena {
    fn default() -> Self {
        Self {
            bytes: [PreviewImage::Empty.as_byte(); ARENA_SIZE],
        }
    }
}

impl Arena {
    /// Raw byte view. `bytes.len() == ARENA_SIZE`.
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// Rebuild an arena preview from a parsed `.lvl` file. Walks every
    /// template, applies the row/column offset table, then plots each
    /// foreground tile through `preview_for_tile`. Handles the
    /// small-arena vertical-centering hack at the end.
    ///
    /// Rejects levels whose `\-size` isn't one of the two vanilla arena
    /// shapes. Also rejects templates the offset table doesn't know
    /// about.
    pub fn from_level_file(level_file: &LevelFile) -> Result<Self> {
        let size = level_file
            .level_settings
            .get("size")
            .ok_or_else(|| LevelError::BadDmPreview("missing size setting".into()))?;
        let arena_size = ArenaSize::from_size_setting(&size.value).ok_or_else(|| {
            LevelError::BadDmPreview(format!(
                "size {:?} isn't a valid arena size (need 2x2 or 3x2)",
                size.value
            ))
        })?;

        // Build a tilecode value -> base-name map. Strip any `%N`
        // percent-suffix off the name so weighted tile codes (`foo%5`)
        // share a base with their unsuffixed sibling. Value is the
        // single character stored in the tile grid.
        let mut tile_codes: HashMap<char, String> = HashMap::new();
        for tc in level_file.tile_codes.all() {
            let base = tc.name.split('%').next().unwrap_or(&tc.name);
            // TileCode.value is a String (may be a single non-ASCII
            // cp1252 byte); take its first char.
            if let Some(ch) = tc.value.chars().next() {
                tile_codes.insert(ch, base.to_string());
            }
        }

        let mut bytes = [PreviewImage::Empty.as_byte(); ARENA_SIZE];

        for template in level_file.level_templates.all() {
            // Walk past IGNORE-flagged rooms to the first "real" chunk;
            // the arena's actual paint lives in that room.
            let Some(room) = template
                .rooms
                .iter()
                .find(|r| !r.settings.contains(&TemplateSetting::Ignore))
            else {
                continue;
            };

            let Some(row_offset) = row_offset_for(&template.name) else {
                return Err(LevelError::BadDmPreview(format!(
                    "unknown template name {:?}",
                    template.name
                )));
            };
            let Some(column_offset) = column_offset_for(arena_size, &template.name) else {
                return Err(LevelError::BadDmPreview(format!(
                    "template {:?} has no column offset for {:?} arenas",
                    template.name, arena_size
                )));
            };

            let is_setroom1 = template.name.starts_with("setroom1-");
            let is_only_flip = room.settings.contains(&TemplateSetting::OnlyFlip);

            for (row_idx, row_orig) in room.foreground.iter().enumerate() {
                // Skip the last row of any `setroom1-*` room; that row
                // is never used in arena mode.
                if is_setroom1 && row_idx == 7 {
                    continue;
                }

                // Row cloning per ONLYFLIP: reverse a clone to keep the
                // caller's LevelFile data intact.
                let mut row_local: Vec<char>;
                let row: &[char] = if is_only_flip {
                    row_local = row_orig.clone();
                    row_local.reverse();
                    &row_local
                } else {
                    row_orig
                };

                let target_row = row_idx + row_offset;
                let row_start = target_row * PREVIEW_WIDTH;

                for (tile_idx, &tile_ch) in row.iter().enumerate() {
                    let byte_offset = row_start + column_offset + tile_idx;
                    let Some(base_name) = tile_codes.get(&tile_ch) else {
                        // Unknown tile-code value in the grid: leave
                        // that cell empty rather than error out.
                        continue;
                    };
                    // Under ONLYFLIP, conveyors swap direction so the
                    // preview matches the flipped-room's actual visual.
                    let name: &str = if is_only_flip {
                        match base_name.as_str() {
                            "conveyorbelt_left" => "conveyorbelt_right",
                            "conveyorbelt_right" => "conveyorbelt_left",
                            other => other,
                        }
                    } else {
                        base_name
                    };

                    let Some(image) = preview_for_tile(name) else {
                        // Not in the preview table. If it's on the
                        // allowlist of "renders nothing on purpose",
                        // stay silent. Otherwise the tile is unknown;
                        // no logging hookup here, so consumers grep for
                        // unknown tiles by comparing this table's
                        // coverage to their tilecode set.
                        let _ = is_empty_tilecode(name);
                        continue;
                    };
                    let byte_value = image.as_byte();
                    if byte_value == PreviewImage::Empty.as_byte() {
                        continue;
                    }

                    plot(&mut bytes, byte_offset, byte_value);

                    // Multi-tile extensions, including the weird 0x1A
                    // "un-used tile" at the top of a tree/mushroom.
                    match name {
                        "tree_base" | "mushroom_base" => {
                            plot(
                                &mut bytes,
                                byte_offset.wrapping_sub(PREVIEW_WIDTH),
                                byte_value,
                            );
                            plot(
                                &mut bytes,
                                byte_offset.wrapping_sub(PREVIEW_WIDTH * 2),
                                byte_value,
                            );
                            plot(
                                &mut bytes,
                                byte_offset.wrapping_sub(PREVIEW_WIDTH * 3),
                                WEIRD_UNUSED_TILE,
                            );
                        }
                        "chainandblocks_ceiling" => {
                            let chain = PreviewImage::Chain.as_byte();
                            plot(&mut bytes, byte_offset + PREVIEW_WIDTH, chain);
                            plot(&mut bytes, byte_offset + PREVIEW_WIDTH * 2, chain);
                            plot(&mut bytes, byte_offset + PREVIEW_WIDTH * 3, chain);
                            plot(&mut bytes, byte_offset + PREVIEW_WIDTH * 4, chain);
                        }
                        "crushtraplarge" => {
                            let crush = PreviewImage::CrushTrap.as_byte();
                            plot(&mut bytes, byte_offset + 1, crush);
                            plot(&mut bytes, byte_offset + PREVIEW_WIDTH, crush);
                            plot(&mut bytes, byte_offset + PREVIEW_WIDTH + 1, crush);
                        }
                        _ => {}
                    }
                }
            }
        }

        // Small-arena vertical centering hack: if the bottom two rows
        // are entirely empty, shift the whole thing down by two rows.
        // Small arenas are painted at the top of the preview but the
        // vanilla previews are centered.
        if arena_size == ArenaSize::Small {
            let bottom_start = ARENA_SIZE - PREVIEW_WIDTH * 2;
            let bottom = &bytes[bottom_start..];
            let all_empty = bottom.iter().all(|&b| b == PreviewImage::Empty.as_byte());
            if all_empty {
                let mut shifted = [PreviewImage::Empty.as_byte(); ARENA_SIZE];
                shifted[PREVIEW_WIDTH * 2..]
                    .copy_from_slice(&bytes[..ARENA_SIZE - PREVIEW_WIDTH * 2]);
                bytes = shifted;
            }
        }

        Ok(Self { bytes })
    }
}

/// Write `byte_value` at `offset` iff it's inside the arena buffer.
/// The renderer sometimes uses wrapping subtraction to reach "above"
/// the placement cell; silently clipping out-of-bounds writes here lets
/// a `tree_base` at the top of a room do the sane thing.
fn plot(bytes: &mut [u8; ARENA_SIZE], offset: usize, byte_value: u8) {
    if offset < ARENA_SIZE {
        bytes[offset] = byte_value;
    }
}

// ---- DmPreviewTok ---------------------------------------------------

/// The whole 18,000-byte file: 40 arena previews back-to-back.
#[derive(Debug, Clone)]
pub struct DmPreviewTok {
    pub arenas: Vec<Arena>,
}

impl DmPreviewTok {
    /// Parse the fixed-size blob into 40 arenas. Rejects any length
    /// other than `DMPREVIEW_SIZE`.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.len() != DMPREVIEW_SIZE {
            return Err(LevelError::BadDmPreview(format!(
                "expected {DMPREVIEW_SIZE} bytes, got {}",
                bytes.len()
            )));
        }
        let arenas: Vec<Arena> = bytes
            .chunks_exact(ARENA_SIZE)
            .map(|chunk| {
                let mut buf = [0u8; ARENA_SIZE];
                buf.copy_from_slice(chunk);
                Arena { bytes: buf }
            })
            .collect();
        // chunks_exact leaves no remainder because DMPREVIEW_SIZE %
        // ARENA_SIZE == 0. The count must be NUM_ARENAS.
        debug_assert_eq!(arenas.len(), NUM_ARENAS);
        Ok(Self { arenas })
    }

    /// Serialize back to the fixed 18,000-byte layout.
    pub fn to_bytes(&self) -> Result<Vec<u8>> {
        if self.arenas.len() != NUM_ARENAS {
            return Err(LevelError::BadDmPreview(format!(
                "expected {NUM_ARENAS} arenas, got {}",
                self.arenas.len()
            )));
        }
        let mut out = Vec::with_capacity(DMPREVIEW_SIZE);
        for arena in &self.arenas {
            out.extend_from_slice(&arena.bytes);
        }
        Ok(out)
    }

    /// Replace the arena at `arena_index` with `arena`. Convenience over
    /// direct `arenas[i] = ...` assignment; returns Err on out-of-range.
    pub fn set_arena(&mut self, arena_index: usize, arena: Arena) -> Result<()> {
        if arena_index >= NUM_ARENAS {
            return Err(LevelError::BadDmPreview(format!(
                "arena index {arena_index} out of range (0..{NUM_ARENAS})"
            )));
        }
        self.arenas[arena_index] = arena;
        Ok(())
    }
}

// ---- Tests ----------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constants_match_wire_format() {
        assert_eq!(PREVIEW_WIDTH, 30);
        assert_eq!(PREVIEW_HEIGHT, 15);
        assert_eq!(NUM_ARENAS, 40);
        assert_eq!(DMPREVIEW_SIZE, 18_000);
        assert_eq!(ARENA_SIZE, 450);
        assert_eq!(ARENA_LEVEL_FILES.len(), NUM_ARENAS);
        assert_eq!(ARENA_NAMES.len(), NUM_ARENAS);
    }

    #[test]
    fn arena_index_lookup_covers_boundaries() {
        assert_eq!(arena_index_for_file("dm1-1.lvl"), Some(0));
        assert_eq!(arena_index_for_file("dm8-5.lvl"), Some(NUM_ARENAS - 1));
        assert_eq!(arena_index_for_file("dm4-3.lvl"), Some(17));
        assert_eq!(arena_index_for_file("dm9-9.lvl"), None);
        assert_eq!(arena_index_for_file("dm1-1"), None);
    }

    #[test]
    fn preview_for_tile_spot_checks() {
        assert_eq!(preview_for_tile("floor"), Some(PreviewImage::Floor));
        assert_eq!(preview_for_tile("water"), Some(PreviewImage::Liquid));
        assert_eq!(preview_for_tile("lava"), Some(PreviewImage::Liquid));
        assert_eq!(
            preview_for_tile("crushtraplarge"),
            Some(PreviewImage::CrushTrap)
        );
        assert_eq!(preview_for_tile("tree_base"), Some(PreviewImage::Foliage));
        assert_eq!(
            preview_for_tile("mushroom_base"),
            Some(PreviewImage::Foliage)
        );
        assert_eq!(
            preview_for_tile("chainandblocks_ceiling"),
            Some(PreviewImage::Floor)
        );
        assert_eq!(preview_for_tile("floor_hard"), Some(PreviewImage::Empty));
        assert_eq!(preview_for_tile("empty"), Some(PreviewImage::Empty));
        assert_eq!(preview_for_tile("unknown_tile_xyz"), None);
    }

    #[test]
    fn is_empty_tilecode_allowlist() {
        assert!(is_empty_tilecode("cavemanboss"));
        assert!(is_empty_tilecode("cookfire"));
        assert!(is_empty_tilecode("dm_spawn_point"));
        assert!(!is_empty_tilecode("floor"));
    }

    #[test]
    fn row_and_column_offset_tables() {
        assert_eq!(row_offset_for("setroom0-0"), Some(0));
        assert_eq!(row_offset_for("setroom1-2"), Some(8));
        assert_eq!(row_offset_for("setroomX"), None);

        assert_eq!(column_offset_for(ArenaSize::Small, "setroom0-0"), Some(5));
        assert_eq!(column_offset_for(ArenaSize::Small, "setroom0-1"), Some(15));
        assert_eq!(column_offset_for(ArenaSize::Small, "setroom0-2"), None);
        assert_eq!(column_offset_for(ArenaSize::Large, "setroom0-0"), Some(0));
        assert_eq!(column_offset_for(ArenaSize::Large, "setroom0-2"), Some(20));
        assert_eq!(column_offset_for(ArenaSize::Large, "setroom1-2"), Some(20));
    }

    #[test]
    fn from_bytes_rejects_wrong_size() {
        assert!(DmPreviewTok::from_bytes(&[0u8; 100]).is_err());
        assert!(DmPreviewTok::from_bytes(&[0u8; DMPREVIEW_SIZE + 1]).is_err());
    }

    #[test]
    fn round_trip_preserves_bytes() {
        // Distinct byte per arena so a shuffled read would show.
        let mut input = vec![0u8; DMPREVIEW_SIZE];
        for (i, byte) in input.iter_mut().enumerate() {
            *byte = (i % 256) as u8;
        }
        let tok = DmPreviewTok::from_bytes(&input).unwrap();
        assert_eq!(tok.arenas.len(), NUM_ARENAS);
        assert_eq!(tok.arenas[0].bytes[0], 0);
        assert_eq!(tok.arenas[1].bytes[0], (ARENA_SIZE % 256) as u8);

        let out = tok.to_bytes().unwrap();
        assert_eq!(out, input);
    }

    #[test]
    fn default_arena_is_all_empty() {
        let arena = Arena::default();
        assert!(
            arena
                .bytes
                .iter()
                .all(|&b| b == PreviewImage::Empty.as_byte())
        );
    }

    #[test]
    fn set_arena_out_of_range_errors() {
        let mut tok = DmPreviewTok::from_bytes(&vec![0xFFu8; DMPREVIEW_SIZE]).unwrap();
        assert!(tok.set_arena(0, Arena::default()).is_ok());
        assert!(tok.set_arena(NUM_ARENAS, Arena::default()).is_err());
    }

    #[test]
    fn arena_size_recovery() {
        assert_eq!(
            ArenaSize::from_size_setting(&LevelSettingValue::Size("2".into(), "2".into())),
            Some(ArenaSize::Small)
        );
        assert_eq!(
            ArenaSize::from_size_setting(&LevelSettingValue::Size("3".into(), "2".into())),
            Some(ArenaSize::Large)
        );
        assert_eq!(
            ArenaSize::from_size_setting(&LevelSettingValue::Size("1".into(), "1".into())),
            None
        );
        assert_eq!(
            ArenaSize::from_size_setting(&LevelSettingValue::Int(2)),
            None
        );
    }

    // End-to-end: parse a minimal arena .lvl through LevelFile, render an
    // Arena, and check the resulting bytes at the coordinates a single
    // painted floor tile should land at. Also exercises the tile-code
    // deref and the row/column offset lookup.
    //
    // Paint a floor tile in the bottom row of setroom1-0 (which the
    // renderer skips) AND a floor tile in the top row of setroom0-0.
    // The setroom1-0 bottom-row skip means that row stays empty in the
    // preview, so a tile in setroom1-2's bottom row would trigger the
    // small-arena vertical-centering shift on its own. Deliberately
    // paint into row 7 of setroom0-0 (which lands at preview row 7)
    // so the bottom two rows AREN'T all empty and the shift doesn't
    // fire. That keeps the assertion talking about the painted tile's
    // actual placement, not the shift's placement.
    #[test]
    fn from_level_file_plots_a_single_tile() {
        let lvl = "\
\\-size          2 2

\\?floor        f

\\.setroom0-0

f000000000
0000000000
0000000000
0000000000
0000000000
0000000000
0000000000
0000000000

\\.setroom1-0

0000000000
0000000000
0000000000
0000000000
0000000000
0000000000
f000000000
0000000000
";
        let file = LevelFile::from_str(lvl).unwrap();
        let arena = Arena::from_level_file(&file).unwrap();
        // Small arena, setroom0-0 -> column offset 5, row offset 0.
        // The 'f' at row 0 col 0 lands at preview_row 0, preview_col 5.
        let byte_offset = 5;
        assert_eq!(arena.bytes[byte_offset], PreviewImage::Floor.as_byte());
        // Column 1 got '0' -> not in the tilecode map -> stays empty.
        assert_eq!(arena.bytes[byte_offset + 1], PreviewImage::Empty.as_byte());
        // The setroom1-0 tile lands at (row 8+6=14, col 5+0=5): the
        // last painted row of the whole preview. Its presence keeps
        // the bottom two rows from being all-empty, so the shift
        // doesn't fire.
        let bottom_row_offset = (8 + 6) * PREVIEW_WIDTH + 5;
        assert_eq!(
            arena.bytes[bottom_row_offset],
            PreviewImage::Floor.as_byte()
        );
    }

    // Guard the small-arena vertical-centering shift path. Paint a
    // single tile at the top of setroom0-0. The bottom two preview
    // rows stay empty, so the shift fires and the tile moves down by
    // PREVIEW_WIDTH * 2 bytes.
    #[test]
    fn small_arena_shifts_down_when_bottom_rows_empty() {
        let lvl = "\
\\-size          2 2

\\?floor        f

\\.setroom0-0

f000000000
0000000000
0000000000
0000000000
0000000000
0000000000
0000000000
0000000000
";
        let file = LevelFile::from_str(lvl).unwrap();
        let arena = Arena::from_level_file(&file).unwrap();
        // Painted at preview cell (0, 5) originally, shifts to (2, 5).
        let shifted = 2 * PREVIEW_WIDTH + 5;
        assert_eq!(arena.bytes[shifted], PreviewImage::Floor.as_byte());
        // The original slot is empty after the shift.
        assert_eq!(arena.bytes[5], PreviewImage::Empty.as_byte());
    }
}
