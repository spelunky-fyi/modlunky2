from pathlib import Path

from ..base_classes.base_sprite_loader import BaseSpriteLoader


class Mounts(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/mounts.png")
    _chunk_size = 128
    _chunk_map = {
        "turkey": (0, 0, 1, 1),
        "rockdog": (0, 4, 1, 5),
        "axolotl": (0, 8, 1, 9),
        "qilin": (0, 12, 1, 13),
    }
