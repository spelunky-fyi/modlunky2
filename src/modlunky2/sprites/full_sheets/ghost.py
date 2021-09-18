from pathlib import Path

from modlunky2.sprites.base_classes.base_json_sprite_merger import BaseJsonSpriteMerger
from modlunky2.sprites.util import chunks_from_animation
from modlunky2.sprites.monsters.ghost import Ghost
from modlunky2.sprites.journal_people import JournalPeopleSheet
from modlunky2.sprites.journal_mons_big import JournalBigMonsterSheet


class GhistSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/ghist.png")
    _grid_hint_size = 8
    _origin_map = {
        Ghost: {
            **chunks_from_animation("ghist_angry_0", (0, 0, 1, 1), 3),
            **chunks_from_animation("ghist_angry_1", (0, 1, 1, 2), 3),
            **chunks_from_animation("ghist_angry_2", (0, 2, 1, 3), 1),
        },
        JournalPeopleSheet: {"journal_ghost_shopkeeper": (0, 0, 1, 1)},
    }
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHIST"]}


class GhostSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/ghost.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalBigMonsterSheet: {"journal_ghost": (0, 0, 1, 1)},
    }
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST"]}


class GhostMediumSadSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/ghost_sad.png")
    _grid_hint_size = 8
    _origin_map = {}
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST_MEDIUM_SAD"]}


class GhostMediumHappySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/ghost_happy.png")
    _grid_hint_size = 8
    _origin_map = {}
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY"]}


class GhostSmallSadSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/ghost_small_sad.png")
    _grid_hint_size = 8
    _origin_map = {}
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST_SMALL_SAD"]}


class GhostSmallHappySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Ghost/ghost_small_happy.png"
    )
    _grid_hint_size = 8
    _origin_map = {}
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST_SMALL_HAPPY"]}


class GhostSmallSurprisedSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Ghost/ghost_small_surprised.png"
    )
    _grid_hint_size = 8
    _origin_map = {}
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST_SMALL_SURPRISED"]}


class GhostSmallAngrySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Ghost/ghost_small_angry.png"
    )
    _grid_hint_size = 8
    _origin_map = {}
    _entity_origins = {Ghost: ["ENT_TYPE_MONS_GHOST_SMALL_ANGRY"]}


class MegaJellySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/mega_jelly.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalBigMonsterSheet: {"journal_celestial_jellyfish": (0, 0, 1, 1)},
    }
    _entity_origins = {
        Ghost: [
            "ENT_TYPE_FX_MEGAJELLYFISH_CROWN",
            "ENT_TYPE_FX_MEGAJELLYFISH_BOTTOM",
            "ENT_TYPE_FX_MEGAJELLYFISH_TAIL",
            "ENT_TYPE_FX_MEGAJELLYFISH_FLIPPER",
            "ENT_TYPE_FX_MEGAJELLYFISH_STAR",
            "ENT_TYPE_MONS_MEGAJELLYFISH",
        ]
    }
