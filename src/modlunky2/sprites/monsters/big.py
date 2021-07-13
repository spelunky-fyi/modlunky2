from pathlib import Path

from ..base_classes import BaseSpriteLoader, BaseJsonSpriteLoader
from ..util import chunks_from_animation


class Big1(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig01.png")
    _chunk_size = 128
    _chunk_map = {
        "cavemanboss": (0, 0, 2, 2),
        "giantspider": (0, 10, 2, 12),
        "giant_spider": (0, 10, 2, 12),
        "queenbee": (0, 14, 2, 16),
        "queen_bee": (0, 14, 2, 16),
        "giant_spider_additional": (14, 10, 16, 12),
    }
    _entity_names = [
        "ENT_TYPE_MONS_CAVEMAN_BOSS",
        "ENT_TYPE_MONS_GIANTSPIDER",
        "ENT_TYPE_MONS_QUEENBEE",
    ]


class Big2(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig02.png")
    _chunk_size = 128
    _chunk_map = {
        "mummy": (0, 0, 2, 2),
        "anubis": (4, 8, 6, 11),
        "anubis2": (2, 8, 4, 10),
    }
    _entity_names = [
        "ENT_TYPE_MONS_MUMMY",
        "ENT_TYPE_MONS_ANUBIS",
        "ENT_TYPE_MONS_ANUBIS2",
    ]


class Big3(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig03.png")
    _chunk_size = 128
    _chunk_map = {
        "lamassu": (0, 0, 2, 2),
        "yeti_king": (0, 4, 2, 6),
        "yeti_queen": (0, 10, 2, 12),
    }
    _entity_names = [
        "ENT_TYPE_MONS_LAMASSU",
        "ENT_TYPE_MONS_YETIKING",
        "ENT_TYPE_MONS_YETIQUEEN",
    ]


class Big4(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig04.png")
    _chunk_size = 128
    _chunk_map = {
        "crabman": (0, 0, 2, 2),
        "lavamander": (10, 4, 12, 6),
        "giantfly": (0, 12, 2, 14),
        "giant_fly": (0, 12, 2, 14),
        "crabman_open_claw": (14, 2, 15, 3),
        "crabman_closed_claw": (15, 2, 16, 3),
        "crabman_chain_claw": (14, 3, 15, 4),
        "crabman_additional": (4, 4, 6, 6),
        **chunks_from_animation("lavamander_additional", (10, 10, 12, 12), 3),
    }
    _entity_names = [
        "ENT_TYPE_MONS_CRABMAN",
        "ENT_TYPE_MONS_LAVAMANDER",
        "ENT_TYPE_MONS_GIANTFLY",
        "ENT_TYPE_ITEM_GIANTFLY_HEAD",
        "ENT_TYPE_ITEM_GIANTCLAM_TOP",
        "ENT_TYPE_ACTIVEFLOOR_GIANTCLAM_BASE",
    ]


class Big5(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig05.png")
    _chunk_size = 128
    _chunk_map = {
        "ammit": (0, 4, 2, 5),
        "apep": (8, 0, 10, 2),
        "madametusk": (0, 8, 2, 10),
        "giant_frog": (0, 13, 3, 16),
        "minister": (0, 10, 1, 13.5),
        **chunks_from_animation("minister_small_walk", (9, 7, 10, 8), 7),
    }
    _entity_names = [
        # "ENT_TYPE_MONS_APEP_HEAD",  # ???
        "ENT_TYPE_MONS_APEP_BODY",  # ???
        "ENT_TYPE_MONS_APEP_TAIL",  # ???
        "ENT_TYPE_FX_APEP_MOUTHPIECE",  # ???
        "ENT_TYPE_MONS_AMMIT",
        "ENT_TYPE_MONS_MADAMETUSK",
        "ENT_TYPE_MONS_EGGPLANT_MINISTER",
        "ENT_TYPE_MONS_GIANTFROG",
    ]


class Big6(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig06.png")
    _chunk_size = 128
    _chunk_map = {
        "kingu": (0, 0, 5, 6),
        "waddler": (0, 12, 2, 14),
        "storage_guy": (0, 12, 2, 14),
        "humphead": (0, 14, 4, 16),
    }
    _entity_names = [
        "ENT_TYPE_ACTIVEFLOOR_KINGU_PLATFORM",  # ???
        "ENT_TYPE_FX_KINGU_HEAD",  # ???
        "ENT_TYPE_FX_KINGU_LIMB",  # ???
        "ENT_TYPE_FX_KINGU_PLATFORM",  # ???
        "ENT_TYPE_FX_KINGU_SHADOW",  # ???
        "ENT_TYPE_FX_KINGU_HEAD",  # ???
        "ENT_TYPE_MONS_STORAGEGUY",
        "ENT_TYPE_MONS_GIANTFISH",
    ]


class OsirisAndAlienQueen(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_osiris.png")
    _chunk_size = 128
    _chunk_map = {"osiris": (0, 0, 5, 7), "alienqueen": (0, 13, 3, 16)}
    _entity_names = [
        "ENT_TYPE_MONS_OSIRIS_HEAD",
        "ENT_TYPE_MONS_OSIRIS_HAND",
        "ENT_TYPE_MONS_ALIENQUEEN",
        "ENT_TYPE_FX_ALIENQUEEN_EYE",
        "ENT_TYPE_FX_ALIENQUEEN_EYEBALL",
    ]


class OlmecAndMech(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_olmec.png")
    _chunk_size = 128
    _chunk_map = {
        "olmec": (0, 0, 4, 4),
        "empty_mech": (10, 5, 12, 7),
    }
    _entity_names = [
        "ENT_TYPE_FX_OLMECPART_FLOATER",
        "ENT_TYPE_FX_OLMECPART_LARGE",
        "ENT_TYPE_FX_OLMECPART_MEDIUM",
        "ENT_TYPE_FX_OLMECPART_SMALL",
        "ENT_TYPE_FX_OLMECPART_SMALLEST",
        "ENT_TYPE_MOUNT_MECH",
        "ENT_TYPE_FX_MECH_COLLAR",
    ]


class Yama(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_yama.png")
    _chunk_size = 128
    _chunk_map = {"yama": (0, 0, 8, 10), "empress_grave": (8, 6, 10, 12)}
