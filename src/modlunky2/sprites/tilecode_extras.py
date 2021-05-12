from pathlib import Path

from .base_classes import BaseSpriteLoader


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
    "stagnant_lava",
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
]


class TilecodeExtras(BaseSpriteLoader):
    """Extra tiles used for the level editor."""

    _sprite_sheet_path = Path("static/images/tilecodeextras.png")
    _chunk_size = 50
    _chunk_map = {
        tilename: (idx, 0, idx + 1, 1) for idx, tilename in enumerate(TILENAMES)
    }
