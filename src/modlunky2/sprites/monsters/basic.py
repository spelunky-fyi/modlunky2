from pathlib import Path

from ..base_classes import BaseSpriteLoader
from ..util import chunks_from_animation


class Basic1(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic01.png")
    _chunk_size = 128
    _chunk_map = {
        "snake": (0, 0, 1, 1),
        **chunks_from_animation("snake_row_0_", (0, 0, 1, 1), 6),
        **chunks_from_animation("snake_row_1_", (0, 1, 1, 2), 6),
        "bat": (6, 0, 7, 1),
        **chunks_from_animation("bat_row_0_", (6, 0, 7, 1), 6),
        **chunks_from_animation("bat_row_1_", (6, 1, 7, 2), 6),
        "fly": (12, 0, 13, 1),
        **chunks_from_animation("fly_row_0_", (12, 0, 13, 1), 4),
        "skeleton": (0, 2, 1, 3),
        **chunks_from_animation("skeleton_row_0_", (0, 2, 1, 3), 7),
        **chunks_from_animation("skeleton_row_1_", (7, 2, 8, 3), 7),
        "spider": (0, 3, 1, 4),
        **chunks_from_animation("spider_row_0_", (0, 3, 1, 4), 7),
        **chunks_from_animation("spider_row_1_", (7, 3, 8, 4), 6),
        "ear": (0, 4, 1, 5),
        "ear_hold": (15, 14, 16, 15),
        **chunks_from_animation("ear_walk_0_", (0, 4, 1, 5), 6),
        **chunks_from_animation("ear_walk_1_", (6, 4, 7, 5), 3),
        **chunks_from_animation("ear_climb_0_", (10, 4, 11, 5), 6),
        **chunks_from_animation("ear_climb_1_", (6, 15, 7, 16), 6),
        **chunks_from_animation("ear_climb_2_", (12, 15, 13, 16), 4),
        **chunks_from_animation("ear_throw_0_", (0, 5, 1, 6), 5),
        **chunks_from_animation("ear_stunned_0_", (5, 5, 6, 6), 5),
        "shopkeep": (0, 6, 1, 7),
        "shopkeeper": (0, 6, 1, 7),
        "shopkeeper_hold": (15, 7, 16, 8),
        **chunks_from_animation("shopkeeper_walk_0_", (0, 6, 1, 7), 6),
        **chunks_from_animation("shopkeeper_walk_1_", (6, 6, 7, 7), 3),
        **chunks_from_animation("shopkeeper_climb_0_", (10, 5, 11, 6), 6),
        **chunks_from_animation("shopkeeper_climb_1_", (5, 7, 6, 8), 6),
        **chunks_from_animation("shopkeeper_climb_2_", (11, 7, 12, 8), 4),
        **chunks_from_animation("shopkeeper_throw_0_", (0, 7, 1, 8), 5),
        **chunks_from_animation("shopkeeper_stunned_0_", (9, 6, 10, 7), 5),
        "ufo": (0, 8, 1, 9),
        **chunks_from_animation("ufo_row_0_", (0, 8, 1, 9), 7),
        **chunks_from_animation("ufo_row_1_", (7, 8, 8, 9), 7),
        "alien": (0, 9, 1, 10),
        **chunks_from_animation("alien_row_0_", (0, 9, 1, 10), 7),
        **chunks_from_animation("alien_row_1_", (7, 9, 8, 10), 7),
        "cobra": (0, 10, 1, 11),
        **chunks_from_animation("cobra_row_0_", (0, 10, 1, 11), 6),
        **chunks_from_animation("cobra_row_1_", (0, 11, 1, 12), 6),
        **chunks_from_animation("cobra_row_2_", (6, 11, 7, 12), 6),
        "scorpion": (0, 12, 1, 13),
        "scorpion_stomped": (5, 12, 6, 13),
        "scorpion_stunned": (5, 13, 6, 14),
        **chunks_from_animation("scorpion_row_0_", (0, 12, 1, 13), 5),
        **chunks_from_animation("scorpion_row_1_", (0, 13, 1, 14), 5),
        **chunks_from_animation("scorpion_row_2_", (6, 12, 7, 13), 3),
        "golden_monkey": (14, 9, 15, 10),
        **chunks_from_animation("golden_monkey_row_0_", (14, 9, 15, 10), 2),
        **chunks_from_animation("golden_monkey_row_1_", (6, 10, 7, 11), 4),
        **chunks_from_animation("golden_monkey_row_2_", (10, 10, 11, 11), 6),
        "bee": (9, 12, 10, 13),
        **chunks_from_animation("bee_row_0_", (9, 12, 10, 13), 7),
        **chunks_from_animation("bee_row_1_", (9, 13, 10, 14), 7),
        "magmar": (4, 14, 5, 15),
        "magmar_ball": (0, 14, 1, 15),
        **chunks_from_animation("magmar_row_0_", (1, 14, 2, 15), 6),
        **chunks_from_animation("magmar_row_1_", (7, 14, 8, 15), 6),
        **chunks_from_animation("magmar_row_2_", (0, 15, 1, 16), 6),
    }


class Basic2(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic02.png")
    _chunk_size = 128
    _chunk_map = {
        "vampire": (6, 1, 7, 2),
        "vlad": (6, 3, 7, 4),
        "caveman": (0, 5, 1, 6),
        "caveman_asleep": (8, 6, 9, 7),
        "bodyguard": (0, 8, 1, 9),
        "oldhunter": (0, 11, 1, 12),
        "tun": (0, 14, 1, 15),
        "merchant": (0, 14, 1, 15),
    }


class Basic3(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic03.png")
    _chunk_size = 128
    _chunk_map = {
        "beg": (0, 0, 1, 1),
        "thief": (0, 1, 1, 2),
        "sister": (0, 5, 1, 6),
        "sister1": (0, 11, 1, 12),
        "sister2": (0, 8, 1, 9),
        "sister3": (0, 5, 1, 6),
        "yang": (0, 14, 1, 15),
    }


class Monsters01(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters01.png")
    _chunk_size = 128
    _chunk_map = {
        "robot": (0, 0, 1, 1),
        "imp": (4, 0, 5, 1),
        "witchdoctor": (0, 6, 1, 7),
        "mantrap": (0, 8, 1, 9),
        "tikiman": (0, 9, 1, 10),
        "mosquito": (0, 14, 1, 15),
    }


class Monsters02(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters02.png")
    _chunk_size = 128
    _chunk_map = {
        "jiangshi": (0, 0, 1, 1),
        "octopus": (0, 2, 1, 3),
        # "asfsafd": (0, 6, 1, 7),
        "hermitcrab": (11, 5, 12, 6),
        "crocman": (0, 8, 1, 9),
        "sorceress": (0, 10, 1, 11),
        "catmummy": (0, 11, 1, 12),
        "necromancer": (0, 12, 1, 13),
    }


class Monsters03(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters03.png")
    _chunk_size = 128
    _chunk_map = {
        "yeti": (0, 0, 1, 1),
        "jumpdog": (0, 6, 1, 7),
        "olmite": (0, 7, 1, 8),
    }
