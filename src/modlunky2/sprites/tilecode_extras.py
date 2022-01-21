from pathlib import Path

from modlunky2.sprites.base_classes import BaseSpriteLoader


TILENAMES = [
    "empty",
    "chunk_air",
    "chunk_ground",
    "chunk_door",
    "generic_styled_floor",
    "yellowdoor",
    "entrance",
    "exit",
    "doorred",
    "doorpurple",
    "entrance_shortcut",
    "cookfire",
    "cavemanshopkeeper",
    "ghist_shopkeeper",
    "challenge_waitroom",
    "shop_woodwall",
    "haunted_corpse",
    "pen_floor",
    "pen_locked_door",
    "timed_powder_keg",
    "chain_ceiling",
    "lava",
    "coarse_lava",
    "vault_wall",
    "treasure",
    "water",
    "coarse_water",
    "fountain_drain",
    "timed_forcefield",
    "ushabti",
    "tomb_floor",
    "littorch",
    "litwalltorch",
    "surface_hidden_floor",
    "zoo_exhibit",
    "dm_spawn_point",
    "idol_hold",
    "regenerating_block",
    "sister",
    "unknown",
    "generic_floor",
    "shop_pagodawall",
    "autowalltorch",
    "shop_wall",
    "nonreplaceable_floor",
    "minewood_floor_noreplace",
    "nonreplaceable_babylon_floor",
    "adjacent_floor",
    "floor_hard",
    "thorn_vine",
    "sleeping_hiredhand",
    "woodenlog_trap_ceiling",
    "shop_item",
    "platform",
    "quicksand",
    "pillar",
    "giantclam",
    "pipe",
    "sticky_trap",
    "duat_floor_hard",
    "tiamat",
    "sunken_floor_hard",
    "eggplant_child",
    "dustwall",
    "redskeleton",
    "hundun",
    "leaf",
    "rope",
    "udjat_target",
    "forcefield_horizontal_top",
    "forcefield_horizontal",
    "lua_tile",
    "playerbag",
    "rope_unrolled",
    "bubble_platform",
    "apep",
    "apep_left",
    "apep_right",
]


class TilecodeExtras(BaseSpriteLoader):
    """Extra tiles used for the level editor."""

    _sprite_sheet_path = Path("static/images/tilecodeextras.png")
    _chunk_size = 50
    _chunk_map = {
        tilename: (idx, 0, idx + 1, 1) for idx, tilename in enumerate(TILENAMES)
    }


class TreasureVaultChestSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("static/images/treasure_vaultchest.png")
    _chunk_size = 50
    _chunk_map = {
        "treasure_vaultchest": (0, 0, 1, 1),
    }


class ChainAndBlocksCeilingSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("static/images/chainandblocks_ceiling.png")
    _chunk_size = 50
    _chunk_map = {
        "chainandblocks_ceiling": (0, 0, 1, 1),
    }


class StickyTrapSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("static/images/sticky_trap.png")
    _chunk_size = 128
    _chunk_map = {
        "sticky_trap": (0, 0, 1, 2),
    }


EXTRA_TILECODE_CLASSES = [
    ChainAndBlocksCeilingSheet,
    StickyTrapSheet,
    TreasureVaultChestSheet,
]
