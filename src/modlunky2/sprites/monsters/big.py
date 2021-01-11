from pathlib import Path

from ..base_classes.base_sprite_loader import BaseSpriteLoader


class Big1(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig01.png")
    _chunk_size = 128
    _chunk_map = {
        "cavemanboss": (0, 0, 2, 2),
        "giantspider": (0, 10, 2, 12),
        "queenbee": (0, 14, 2, 16),
    }


class Big2(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig02.png")
    _chunk_size = 128
    _chunk_map = {
        "mummy": (0, 0, 2, 2),
        "anubis": (4, 8, 6, 11),
        "anubis2": (2, 8, 4, 10),
    }


class Big3(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig03.png")
    _chunk_size = 128
    _chunk_map = {
        "lamassu": (0, 0, 2, 2),
        "yeti_king": (0, 4, 2, 6),
        "yeti_queen": (0, 10, 2, 12),
    }


class Big4(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig04.png")
    _chunk_size = 128
    _chunk_map = {
        "crabman": (0, 0, 2, 2),
        "lavamander": (10, 4, 12, 6),
        "giantfly": (0, 12, 2, 14),
    }


class Big5(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig05.png")
    _chunk_size = 128
    _chunk_map = {
        "ammit": (0, 4, 2, 5),
        "apep": (8, 0, 10, 2),
        "madametusk": (0, 8, 2, 10),
        "giant_frog": (0, 13, 3, 16),
        "minister": (0, 10, 1, 13),
    }


class Big6(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbig06.png")
    _chunk_size = 128
    _chunk_map = {
        "kingu": (0, 0, 5, 6),
        "waddler": (0, 12, 2, 14),
        "humphead": (0, 14, 4, 16),
    }
