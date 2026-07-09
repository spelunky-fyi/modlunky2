use std::io::Write;

use indexmap::IndexMap;
use once_cell::sync::Lazy;
use regex::Regex;

use crate::error::{LevelError, Result};
use crate::utils::{DirectivePrefix, format_comment, split_comment, to_line};

/// The pool of cp1252 characters usable as tile-code values in a `.lvl` file.
/// Includes non-ASCII bytes like `€`, `ç`, `é`, `ÿ` etc., which is why the
/// file must be read as cp1252 not UTF-8.
pub const VALID_SHORT_CODES: &str = concat!(
    "!\"#$%&'()*+,-.0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`",
    "abcdefghijklmnopqrstuvwxyz{|}~€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—™š›œžŸ¡¢£¤¥¦§",
    "¨©ª«¬-®¯°±²³´µ¶·¸¹°»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæç",
    "èéêëìíîïðñòóôõö÷øùúûüýþÿ",
);

pub fn usable_short_codes() -> Vec<char> {
    VALID_SHORT_CODES.chars().collect()
}

pub const VALID_TILE_CODES: &[&str] = &[
    "alien",
    "adjacent_floor",
    "alien_generator",
    "alienqueen",
    "altar",
    "ammit",
    "ankh",
    "anubis",
    "arrow_trap",
    "autowalltorch",
    "babylon_floor",
    "beehive_floor",
    "bigspear_trap",
    "bodyguard",
    "bone_block",
    "bunkbed",
    "bush_block",
    "catmummy",
    "caveman",
    "caveman_asleep",
    "cavemanboss",
    "cavemanshopkeeper",
    "chain_ceiling",
    "chainandblocks_ceiling",
    "chair_looking_left",
    "chair_looking_right",
    "challenge_waitroom",
    "chunk_air",
    "chunk_door",
    "chunk_ground",
    "climbing_pole",
    "clover",
    "coarse_water",
    "cobra",
    "coffin",
    "cog_floor",
    "construction_sign",
    "conveyorbelt_left",
    "conveyorbelt_right",
    "cooked_turkey",
    "cookfire",
    "couch",
    "crate",
    "crate_bombs",
    "crate_parachute",
    "crate_ropes",
    "crocman",
    "crossbow",
    "crown_statue",
    "crushing_elevator",
    "crushtrap",
    "crushtraplarge",
    "cursed_pot",
    "die",
    "diningtable",
    "dm_spawn_point",
    "dog_sign",
    "door",
    "door_drop_held",
    "door2",
    "door2_secret",
    "dresser",
    "drill",
    "duat_floor",
    "eggplant_altar",
    "eggplant_child",
    "eggplant_door",
    "elevator",
    "empress_grave",
    "empty",
    "empty_mech",
    "entrance",
    "entrance_shortcut",
    "excalibur_stone",
    "exit",
    "factory_generator",
    "falling_platform",
    "floor",
    "floor_hard",
    "forcefield",
    "forcefield_top",
    "fountain_drain",
    "fountain_head",
    "ghist_door2",
    "ghist_shopkeeper",
    "giant_frog",
    "giant_spider",
    "giantclam",
    "goldbars",
    "growable_climbing_pole",
    "growable_vine",
    "guts_floor",
    "haunted_corpse",
    "hermitcrab",
    "honey_downwards",
    "honey_upwards",
    "houyibow",
    "icefloor",
    "idol",
    "idol_floor",
    "idol_hold",
    "imp",
    "jiangshi",
    "jumpdog",
    "jungle_floor",
    "jungle_spear_trap",
    "key",
    "kingu",
    "ladder",
    "ladder_plat",
    "lamassu",
    "lamp_hang",
    "landmine",
    "laser_trap",
    "lava",
    "lavamander",
    "leprechaun",
    "lightarrow",
    "littorch",
    "litwalltorch",
    "locked_door",
    "lockedchest",
    "madametusk",
    "mantrap",
    "mattock",
    "merchant",
    "minewood_floor",
    "minewood_floor_hanging_hide",
    "minewood_floor_noreplace",
    "minister",
    "moai_statue",
    "mosquito",
    "mother_statue",
    "mothership_floor",
    "mummy",
    "mushroom_base",
    "necromancer",
    "nonreplaceable_babylon_floor",
    "nonreplaceable_floor",
    "octopus",
    "oldhunter",
    "olmec",
    "olmecship",
    "olmite",
    "pagoda_floor",
    "pagoda_platform",
    "palace_bookcase",
    "palace_candle",
    "palace_chandelier",
    "palace_entrance",
    "palace_floor",
    "palace_table",
    "palace_table_tray",
    "pen_floor",
    "pen_locked_door",
    "pillar",
    "pipe",
    "plasma_cannon",
    "platform",
    "pot",
    "potofgold",
    "powder_keg",
    "push_block",
    "quicksand",
    "regenerating_block",
    "robot",
    "rock",
    "royal_jelly",
    "scorpion",
    "shop_door",
    "shop_item",
    "shop_pagodawall",
    "shop_sign",
    "shop_wall",
    "shop_woodwall",
    "shopkeeper",
    "shopkeeper_vat",
    "shortcut_station_banner",
    "sidetable",
    "singlebed",
    "sister",
    "sleeping_hiredhand",
    "slidingwall_ceiling",
    "slidingwall_switch",
    "snake",
    "snap_trap",
    "sorceress",
    "spark_trap",
    "spikes",
    "spring_trap",
    "coarse_lava",
    "starting_exit",
    "sticky_trap",
    "stone_floor",
    "storage_floor",
    "storage_guy",
    "styled_floor",
    "sunken_floor",
    "surface_floor",
    "surface_hidden_floor",
    "telescope",
    "temple_floor",
    "thief",
    "thinice",
    "thorn_vine",
    "tiamat",
    "tikiman",
    "timed_forcefield",
    "timed_powder_keg",
    "tomb_floor",
    "treasure",
    "treasure_chest",
    "treasure_vaultchest",
    "tree_base",
    "turkey",
    "tv",
    "udjat_socket",
    "ufo",
    "upsidedown_spikes",
    "ushabti",
    "vault_wall",
    "vine",
    "vlad",
    "vlad_flying",
    "vlad_floor",
    "walltorch",
    "wanted_poster",
    "water",
    "witchdoctor",
    "woodenlog_trap",
    "woodenlog_trap_ceiling",
    "yama",
    "yang",
    "yeti",
    "zoo_exhibit",
    // Community tile codes
    "cog_door",
    "totem_trap",
    "dustwall",
    "bat",
    "bat_flying",
    "skeleton",
    "redskeleton",
    "lizard",
    "mole",
    "monkey",
    "firebug",
    "vampire",
    "vampire_flying",
    "osiris",
    "anubis2",
    "assassin",
    "yeti_king",
    "yeti_queen",
    "bee",
    "bee_queen",
    "frog",
    "frog_orange",
    "hundun",
    "scarab",
    "cosmic_jelly",
    "ghost",
    "ghost_med_sad",
    "ghost_med_happy",
    "ghost_small_angry",
    "ghost_small_sad",
    "ghost_small_surprised",
    "ghost_small_happy",
    "leaf",
    "udjat_key",
    "tutorial_speedrun_sign",
    "tutorial_menu_sign",
    "boombox",
    "eggplant",
    "gold_bar",
    "diamond",
    "emerald",
    "sapphire",
    "ruby",
    "rope_pile",
    "rope",
    "bomb_bag",
    "bomb_box",
    "giantfood",
    "elixir",
    "seeded_run_unlocker",
    "specs",
    "climbing_gloves",
    "pitchers_mitt",
    "shoes_spring",
    "shoes_spike",
    "paste",
    "compass",
    "compass_alien",
    "parachute",
    "udjat_eye",
    "kapala",
    "hedjet",
    "crown",
    "eggplant_crown",
    "true_crown",
    "tablet",
    "bone_key",
    "playerbag",
    "cape",
    "vlads_cape",
    "back_jetpack",
    "back_telepack",
    "back_hoverpack",
    "back_powerpack",
    "gun_webgun",
    "gun_shotgun",
    "gun_freezeray",
    "camera",
    "teleporter",
    "boomerang",
    "machete",
    "excalibur",
    "excalibur_broken",
    "scepter",
    "clonegun",
    "shield_wooden",
    "shield_metal",
    "udjat_target",
    "mount_rockdog",
    "mount_axolotl",
    "mount_qilin",
    "humphead",
    "present",
    "forcefield_horizontal",
    "forcefield_horizontal_top",
    "pet_monty",
    "pet_percy",
    "pet_poochi",
    "lion_trap",
    "bomb",
    "rope_unrolled",
    "cosmic_orb",
    "monkey_gold",
    "altar_duat",
    "spikeball",
    "excalibur_stone_empty",
    "cobweb",
    "eggsac",
    "eggsac_left",
    "eggsac_right",
    "eggsac_top",
    "eggsac_bottom",
    "grub",
    "spider",
    "spider_falling",
    "spider_hanging",
    "skull_drop_trap",
    "lava_pot",
    "proto_shopkeeper",
    "shopkeeper_clone",
    "tadpole",
    "ghist_present",
    "palace_sign",
    "critter_dungbeetle",
    "critter_butterfly",
    "critter_snail",
    "critter_fish",
    "critter_crab",
    "critter_locust",
    "critter_penguin",
    "critter_firefly",
    "critter_drone",
    "bubble_platform",
    "punishball",
    "punishball_attach",
    "giant_fly",
    "flying_fish",
    "crabman",
    "spikeball_trap",
    "spikeball_no_bounce",
    "slidingwall",
    "boulder",
    "apep",
    "apep_left",
    "apep_right",
    "olmite_naked",
    "olmite_helmet",
    "olmite_armored",
    "critter_slime",
    "skull",
    "movable_spikes",
    "punishball_attach_bottom",
    "punishball_attach_top",
    "punishball_attach_left",
    "punishball_attach_right",
    "arrow_wooden",
    "arrow_metal",
    "arrow_wooden_poison",
    "arrow_metal_poison",
    "venom",
];

static NAME_PADDING: Lazy<usize> =
    Lazy::new(|| VALID_TILE_CODES.iter().map(|s| s.len()).max().unwrap_or(0) + 4);

/// Regex for splitting a tile-code name on its optional `%N` or `%N%` chance
/// suffix, e.g. `floor%50` -> `["floor", ""]`, `floor_hard%50%floor` ->
/// `["floor_hard", "floor"]`.
pub fn percent_delim() -> &'static Regex {
    static RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"%\d{1,2}%?").unwrap());
    &RE
}

const VALUE_PADDING: usize = 4;

#[derive(Debug, Clone)]
pub struct TileCode {
    pub name: String,
    /// A single cp1252 character. Held as a `String` because non-ASCII bytes
    /// like `€` decode to multi-byte UTF-8; storing as `char` also works but
    /// `String` keeps the field cheap to serialize back to bytes.
    pub value: String,
    pub comment: Option<String>,
}

impl TileCode {
    pub const PREFIX: &'static str = DirectivePrefix::TileCode.as_str();

    pub fn parse(line: &str) -> Result<Self> {
        let (rest, comment) = split_comment(line);
        let mut split = rest.splitn(2, char::is_whitespace);
        let directive = split
            .next()
            .ok_or_else(|| LevelError::MissingName(line.to_string()))?;
        let value_str = split
            .next()
            .ok_or_else(|| LevelError::MissingValue(rest.clone()))?
            .trim();

        let name = directive
            .strip_prefix(Self::PREFIX)
            .ok_or_else(|| LevelError::MissingName(line.to_string()))?;
        if name.is_empty() {
            return Err(LevelError::MissingName(line.to_string()));
        }

        // Tile-code value must be exactly one cp1252 character (i.e. one
        // Unicode scalar value after decode).
        if value_str.chars().count() != 1 {
            return Err(LevelError::BadTileCodeLen {
                name: name.to_string(),
                value: value_str.to_string(),
            });
        }

        Ok(Self {
            name: name.to_string(),
            value: value_str.to_string(),
            comment,
        })
    }

    pub fn to_line(&self) -> String {
        to_line(
            Self::PREFIX,
            &self.name,
            *NAME_PADDING,
            &self.value,
            VALUE_PADDING,
            self.comment.as_deref(),
        )
    }
}

#[derive(Debug, Default, Clone)]
pub struct TileCodes {
    inner: IndexMap<String, TileCode>,
    pub comment: Option<String>,
}

impl TileCodes {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn all(&self) -> impl Iterator<Item = &TileCode> {
        self.inner.values()
    }

    pub fn get(&self, name: &str) -> Option<&TileCode> {
        self.inner.get(name)
    }

    pub fn set(&mut self, obj: TileCode) {
        self.inner.insert(obj.name.clone(), obj);
    }

    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    pub fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
        writer.write_all(format_comment(self.comment.as_deref()).as_bytes())?;
        for obj in self.inner.values() {
            writer.write_all(obj.to_line().as_bytes())?;
        }
        writer.write_all(b"\n")?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_basic() {
        let t = TileCode::parse("\\?empty                     0").unwrap();
        assert_eq!(t.name, "empty");
        assert_eq!(t.value, "0");
    }

    #[test]
    fn parse_with_percent_suffix() {
        let t = TileCode::parse("\\?floor%50                  2   // 50% chance").unwrap();
        assert_eq!(t.name, "floor%50");
        assert_eq!(t.value, "2");
        assert_eq!(t.comment.as_deref(), Some("50% chance"));
    }

    #[test]
    fn parse_non_ascii_value() {
        // These cp1252-only chars round-trip through UTF-8 str just fine.
        let t = TileCode::parse("\\?sunken_floor              =").unwrap();
        assert_eq!(t.value, "=");
    }

    #[test]
    fn parse_rejects_multi_char_value() {
        let err = TileCode::parse("\\?empty 00");
        assert!(matches!(err, Err(LevelError::BadTileCodeLen { .. })));
    }

    #[test]
    fn parse_rejects_missing_value() {
        // Directive with no value token at all -> MissingValue.
        let err = TileCode::parse("\\?empty");
        assert!(
            matches!(err, Err(LevelError::MissingValue(_))),
            "got {err:?}"
        );
    }

    #[test]
    fn parse_accepts_euro_value() {
        // `€` is one cp1252 character; must decode as one Unicode scalar
        // and pass the len==1 check. This is what the existing
        // `parse_non_ascii_value` test claimed to cover but actually
        // used `=`.
        let t = TileCode::parse("\\?styled_floor              €").unwrap();
        assert_eq!(t.name, "styled_floor");
        assert_eq!(t.value, "€");
    }

    #[test]
    fn parse_accepts_c_cedilla_value() {
        let t = TileCode::parse("\\?styled_floor              ç").unwrap();
        assert_eq!(t.value, "ç");
    }

    #[test]
    fn parse_accepts_y_diaeresis_value() {
        let t = TileCode::parse("\\?styled_floor              ÿ").unwrap();
        assert_eq!(t.value, "ÿ");
    }

    #[test]
    fn percent_delim_splits_name() {
        let re = percent_delim();
        let parts: Vec<&str> = re.split("floor_hard%50%floor").collect();
        assert_eq!(parts, vec!["floor_hard", "floor"]);
    }
}
