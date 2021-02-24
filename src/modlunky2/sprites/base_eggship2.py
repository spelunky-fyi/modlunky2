from pathlib import Path

from .base_classes import BaseSpriteLoader
from .util import chunks_from_animation


class EggShip2Sheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/base_eggship2.png")
    _chunk_size = 128
    _chunk_map = {
        "olmecship": (0, 0, 3, 3),
    }
