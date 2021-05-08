from pathlib import Path

from .base_classes import BaseSpriteLoader


class MenuBasicSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/menu_basic.png")
    _chunk_size = 64
    _chunk_map = {
        "basic_monty": (16, 7, 17, 8),
        "basic_percy": (17, 7, 18, 8),
        "basic_poochi": (18, 7, 19, 8),
    }

class PetHeadsSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("images/pet_heads.png")
    _chunk_size = 128
    _chunk_map = {
        "pet_head_monty": (0, 0, 1, 1),
        "pet_head_percy": (1, 0, 2, 1),
        "pet_head_poochi": (2, 0, 3, 1),
    }
