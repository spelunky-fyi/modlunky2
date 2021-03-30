from pathlib import Path

from modlunky2.sprites.base_classes.base_sprite_merger import BaseSpriteMerger
from modlunky2.sprites.monsters.basic import Basic1
from modlunky2.sprites.journal_mons import JournalMonsterSheet
from modlunky2.sprites.journal_people import JournalPeopleSheet
from modlunky2.sprites.util import chunks_from_animation


class SnakeSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/snake_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("snake_row_0_", (0, 0, 1, 1), 6),
            **chunks_from_animation("snake_row_1_", (0, 1, 1, 2), 6),
        },
        JournalMonsterSheet: {"journal_snake": (0, 0, 1, 1)},
    }


class BatSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/bat_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("bat_row_0_", (0, 0, 1, 1), 6),
            **chunks_from_animation("bat_row_1_", (0, 1, 1, 2), 6),
        },
        JournalMonsterSheet: {"journal_bat": (0, 0, 1, 1)},
    }


class FlySpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/fly_full.png")
    _grid_hint_size = 8
    _origin_map = {Basic1: {**chunks_from_animation("fly_row_0_", (0, 0, 1, 1), 4)}}


class SkeletonSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/monsters/skeleton_full.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("skeleton_row_0_", (0, 0, 1, 1), 7),
            **chunks_from_animation("skeleton_row_1_", (0, 1, 1, 2), 7),
        },
        JournalMonsterSheet: {"journal_skeleton": (0, 0, 1, 1)},
    }


class SpiderSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/spider_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("spider_row_0_", (0, 0, 1, 1), 7),
            **chunks_from_animation("spider_row_1_", (0, 1, 1, 2), 6),
        },
        JournalMonsterSheet: {"journal_spider": (0, 0, 1, 1)},
    }


class EarSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/ear_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("ear_walk_0_", (0, 0, 1, 1), 6),
            "ear_walk_1_1": (5, 1, 6, 2),
            "ear_walk_1_2": (4, 2, 5, 3),
            "ear_walk_1_3": (5, 2, 6, 3),
            **chunks_from_animation("ear_throw_0_", (0, 1, 1, 2), 5),
            **chunks_from_animation("ear_climb_2_", (0, 2, 1, 3), 4),
            **chunks_from_animation("ear_climb_1_", (0, 3, 1, 4), 6),
            **chunks_from_animation("ear_climb_0_", (0, 4, 1, 5), 6),
            **chunks_from_animation("ear_stunned_0_", (0, 5, 1, 6), 5),
            "ear_hold": (5, 5, 6, 6),
        }
    }


class ShopkeeperSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/monsters/shopkeeper_full.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("shopkeeper_walk_0_", (0, 0, 1, 1), 6),
            "shopkeeper_walk_1_1": (5, 1, 6, 2),
            "shopkeeper_walk_1_2": (4, 2, 5, 3),
            "shopkeeper_walk_1_3": (5, 2, 6, 3),
            **chunks_from_animation("shopkeeper_throw_0_", (0, 1, 1, 2), 5),
            **chunks_from_animation("shopkeeper_climb_2_", (0, 2, 1, 3), 4),
            **chunks_from_animation("shopkeeper_climb_1_", (0, 3, 1, 4), 6),
            **chunks_from_animation("shopkeeper_climb_0_", (0, 4, 1, 5), 6),
            **chunks_from_animation("shopkeeper_stunned_0_", (0, 5, 1, 6), 5),
            "shopkeeper_hold": (5, 5, 6, 6),
        },
        JournalPeopleSheet: {"journal_shopkeeper": (0, 0, 1, 1)},
    }


class UfoSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/ufo_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("ufo_row_0_", (0, 0, 1, 1), 7),
            **chunks_from_animation("ufo_row_1_", (0, 1, 1, 2), 7),
        },
        JournalMonsterSheet: {"journal_ufo": (0, 0, 1, 1)},
    }


class AlienSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/alien_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("alien_row_0_", (0, 0, 1, 1), 7),
            **chunks_from_animation("alien_row_1_", (0, 1, 1, 2), 7),
        },
        JournalMonsterSheet: {"journal_alien": (0, 0, 1, 1)},
    }


class CobraSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/cobra_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("cobra_row_0_", (0, 0, 1, 1), 6),
            **chunks_from_animation("cobra_row_1_", (0, 1, 1, 2), 6),
            **chunks_from_animation("cobra_row_2_", (0, 2, 1, 3), 6),
        },
        JournalMonsterSheet: {"journal_cobra": (0, 0, 1, 1)},
    }


class ScorpionSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/monsters/scorpion_full.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("scorpion_row_0_", (0, 0, 1, 1), 5),
            **chunks_from_animation("scorpion_row_1_", (0, 1, 1, 2), 5),
            **chunks_from_animation("scorpion_row_2_", (0, 2, 1, 3), 3),
            "scorpion_stomped": (3, 2, 4, 3),
            "scorpion_stunned": (4, 2, 5, 3),
        },
        JournalMonsterSheet: {"journal_scorpion": (0, 0, 1, 1)},
    }


class GoldenMonkeySpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/monsters/golden_monkey_full.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("golden_monkey_row_0_", (0, 0, 1, 1), 2),
            **chunks_from_animation("golden_monkey_row_1_", (2, 0, 3, 1), 4),
            **chunks_from_animation("golden_monkey_row_2_", (0, 1, 1, 2), 6),
        },
        JournalMonsterSheet: {"journal_golden_monkey": (0, 0, 1, 1)},
    }


class BeeSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/bee_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("bee_row_0_", (0, 0, 1, 1), 7),
            **chunks_from_animation("bee_row_1_", (0, 1, 1, 2), 7),
        },
        JournalMonsterSheet: {"journal_bee": (0, 0, 1, 1)},
    }


class MagmarSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monsters/magmar_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Basic1: {
            **chunks_from_animation("magmar_row_0_", (0, 0, 1, 1), 6),
            **chunks_from_animation("magmar_row_1_", (0, 1, 1, 2), 6),
            **chunks_from_animation("magmar_row_2_", (0, 2, 1, 3), 6),
            "magmar_ball": (0, 3, 1, 4),
        },
        JournalMonsterSheet: {"journal_magmar": (0, 0, 1, 1)},
    }
