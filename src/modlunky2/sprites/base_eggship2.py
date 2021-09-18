from pathlib import Path

from modlunky2.sprites.base_classes import BaseSpriteLoader


class EggShip2Sheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/base_eggship2.png")
    _chunk_size = 128
    _chunk_map = {
        "olmecship": (0, 0, 3, 3),
    }
