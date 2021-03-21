from pathlib import Path

from .base_classes import BaseSpriteLoader


class DecoExtraSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/deco_extra.png")
    _chunk_size = 128
    _chunk_map = {
        "shopkeeper_vat": (4, 5, 8, 11),
    }
