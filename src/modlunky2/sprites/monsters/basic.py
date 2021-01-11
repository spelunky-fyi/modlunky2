from pathlib import Path

from ..base_classes import BaseSpriteLoader


class Basic1(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic01.png")
    _chunk_size = 128
    _chunk_map = {
        "snake": (0, 0, 1, 1),
        "bat": (6, 0, 7, 1),
        "skeleton": (0, 2, 1, 3),
        "leprechaun": (0, 4, 1, 5),
        "spider": (0, 3, 1, 4),
        "shopkeep": (0, 6, 1, 7),
        "ufo": (0, 8, 1, 9),
        "alien": (0, 9, 1, 10),
        "cobra": (0, 10, 1, 11),
        "scorpion": (0, 12, 1, 13),
        "golden_monkey": (14, 9, 15, 10),
        "bee": (9, 12, 10, 13),
        "magmar": (4, 14, 5, 15),
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
