from pathlib import Path

from .base_classes import BaseSpriteLoader
from .util import chunks_from_animation


class CoffinSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/coffins.png")
    _chunk_size = 128
    _chunk_map = {
        "coffin": (0, 0, 2, 2),
    }
