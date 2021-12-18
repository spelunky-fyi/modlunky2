from pathlib import Path

from modlunky2.sprites.base_classes import BaseSpriteLoader


class CoffinSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/coffins.png")
    _chunk_size = 128
    _chunk_map = {
        "coffin": (0, 0, 2, 2),
    }
