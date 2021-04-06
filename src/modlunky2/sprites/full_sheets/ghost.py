from pathlib import Path

from ..base_classes.base_json_sprite_merger import BaseJsonSpriteMerger
from ..monsters.ghost import Ghost
from ..journal_people import JournalPeopleSheet
from ..journal_mons_big import JournalBigMonsterSheet


class GhistSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Ghost/ghist.png")
    _grid_hint_size = 8
    _origin_map = {
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
