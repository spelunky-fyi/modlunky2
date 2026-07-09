// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn tilecode_extras() -> LoaderConfig {
    LoaderConfig {
        name: "TilecodeExtras".into(),
        sprite_sheet_path: "static/images/tilecodeextras.png".into(),
        chunk_size: 50,
        chunk_map: chunks(&[
            ("empty", 0.0, 0.0, 1.0, 1.0),
            ("chunk_air", 1.0, 0.0, 2.0, 1.0),
            ("chunk_ground", 2.0, 0.0, 3.0, 1.0),
            ("chunk_door", 3.0, 0.0, 4.0, 1.0),
            ("generic_styled_floor", 4.0, 0.0, 5.0, 1.0),
            ("yellowdoor", 5.0, 0.0, 6.0, 1.0),
            ("entrance", 6.0, 0.0, 7.0, 1.0),
            ("exit", 7.0, 0.0, 8.0, 1.0),
            ("doorred", 8.0, 0.0, 9.0, 1.0),
            ("doorpurple", 9.0, 0.0, 10.0, 1.0),
            ("entrance_shortcut", 10.0, 0.0, 11.0, 1.0),
            ("cookfire", 11.0, 0.0, 12.0, 1.0),
            ("cavemanshopkeeper", 12.0, 0.0, 13.0, 1.0),
            ("ghist_shopkeeper", 13.0, 0.0, 14.0, 1.0),
            ("challenge_waitroom", 14.0, 0.0, 15.0, 1.0),
            ("shop_woodwall", 15.0, 0.0, 16.0, 1.0),
            ("haunted_corpse", 16.0, 0.0, 17.0, 1.0),
            ("pen_floor", 17.0, 0.0, 18.0, 1.0),
            ("pen_locked_door", 18.0, 0.0, 19.0, 1.0),
            ("timed_powder_keg", 19.0, 0.0, 20.0, 1.0),
            ("chain_ceiling", 20.0, 0.0, 21.0, 1.0),
            ("lava", 21.0, 0.0, 22.0, 1.0),
            ("coarse_lava", 22.0, 0.0, 23.0, 1.0),
            ("vault_wall", 23.0, 0.0, 24.0, 1.0),
            ("treasure", 24.0, 0.0, 25.0, 1.0),
            ("water", 25.0, 0.0, 26.0, 1.0),
            ("coarse_water", 26.0, 0.0, 27.0, 1.0),
            ("fountain_drain", 27.0, 0.0, 28.0, 1.0),
            ("timed_forcefield", 28.0, 0.0, 29.0, 1.0),
            ("ushabti", 29.0, 0.0, 30.0, 1.0),
            ("tomb_floor", 30.0, 0.0, 31.0, 1.0),
            ("littorch", 31.0, 0.0, 32.0, 1.0),
            ("litwalltorch", 32.0, 0.0, 33.0, 1.0),
            ("surface_hidden_floor", 33.0, 0.0, 34.0, 1.0),
            ("zoo_exhibit", 34.0, 0.0, 35.0, 1.0),
            ("dm_spawn_point", 35.0, 0.0, 36.0, 1.0),
            ("idol_hold", 36.0, 0.0, 37.0, 1.0),
            ("regenerating_block", 37.0, 0.0, 38.0, 1.0),
            ("sister", 38.0, 0.0, 39.0, 1.0),
            ("unknown", 39.0, 0.0, 40.0, 1.0),
            ("generic_floor", 40.0, 0.0, 41.0, 1.0),
            ("shop_pagodawall", 41.0, 0.0, 42.0, 1.0),
            ("autowalltorch", 42.0, 0.0, 43.0, 1.0),
            ("shop_wall", 43.0, 0.0, 44.0, 1.0),
            ("nonreplaceable_floor", 44.0, 0.0, 45.0, 1.0),
            ("minewood_floor_noreplace", 45.0, 0.0, 46.0, 1.0),
            ("nonreplaceable_babylon_floor", 46.0, 0.0, 47.0, 1.0),
            ("adjacent_floor", 47.0, 0.0, 48.0, 1.0),
            ("floor_hard", 48.0, 0.0, 49.0, 1.0),
            ("thorn_vine", 49.0, 0.0, 50.0, 1.0),
            ("sleeping_hiredhand", 50.0, 0.0, 51.0, 1.0),
            ("woodenlog_trap_ceiling", 51.0, 0.0, 52.0, 1.0),
            ("shop_item", 52.0, 0.0, 53.0, 1.0),
            ("platform", 53.0, 0.0, 54.0, 1.0),
            ("quicksand", 54.0, 0.0, 55.0, 1.0),
            ("pillar", 55.0, 0.0, 56.0, 1.0),
            ("giantclam", 56.0, 0.0, 57.0, 1.0),
            ("pipe", 57.0, 0.0, 58.0, 1.0),
            ("sticky_trap", 58.0, 0.0, 59.0, 1.0),
            ("duat_floor_hard", 59.0, 0.0, 60.0, 1.0),
            ("tiamat", 60.0, 0.0, 61.0, 1.0),
            ("sunken_floor_hard", 61.0, 0.0, 62.0, 1.0),
            ("eggplant_child", 62.0, 0.0, 63.0, 1.0),
            ("dustwall", 63.0, 0.0, 64.0, 1.0),
            ("redskeleton", 64.0, 0.0, 65.0, 1.0),
            ("hundun", 65.0, 0.0, 66.0, 1.0),
            ("leaf", 66.0, 0.0, 67.0, 1.0),
            ("rope", 67.0, 0.0, 68.0, 1.0),
            ("udjat_target", 68.0, 0.0, 69.0, 1.0),
            ("forcefield_horizontal_top", 69.0, 0.0, 70.0, 1.0),
            ("forcefield_horizontal", 70.0, 0.0, 71.0, 1.0),
            ("lua_tile", 71.0, 0.0, 72.0, 1.0),
            ("playerbag", 72.0, 0.0, 73.0, 1.0),
            ("rope_unrolled", 73.0, 0.0, 74.0, 1.0),
            ("bubble_platform", 74.0, 0.0, 75.0, 1.0),
            ("apep", 75.0, 0.0, 76.0, 1.0),
            ("apep_left", 76.0, 0.0, 77.0, 1.0),
            ("apep_right", 77.0, 0.0, 78.0, 1.0),
            ("babylon_floor_hard", 78.0, 0.0, 79.0, 1.0),
        ]),
    }
}

pub fn chain_and_blocks_ceiling_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "ChainAndBlocksCeilingSheet".into(),
        sprite_sheet_path: "static/images/chainandblocks_ceiling.png".into(),
        chunk_size: 50,
        chunk_map: chunks(&[("chainandblocks_ceiling", 0.0, 0.0, 1.0, 1.0)]),
    }
}

pub fn spikeball_trap_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "SpikeballTrapSheet".into(),
        sprite_sheet_path: "static/images/spikeball_trap.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("spikeball_trap", 0.0, 0.0, 1.0, 2.0)]),
    }
}

pub fn sticky_trap_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "StickyTrapSheet".into(),
        sprite_sheet_path: "static/images/sticky_trap.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("sticky_trap", 0.0, 0.0, 1.0, 2.0)]),
    }
}

pub fn treasure_vault_chest_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "TreasureVaultChestSheet".into(),
        sprite_sheet_path: "static/images/treasure_vaultchest.png".into(),
        chunk_size: 50,
        chunk_map: chunks(&[("treasure_vaultchest", 0.0, 0.0, 1.0, 1.0)]),
    }
}

pub fn poison_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "PoisonSheet".into(),
        sprite_sheet_path: "static/images/venom.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("venom", 0.0, 0.0, 1.0, 1.0)]),
    }
}
