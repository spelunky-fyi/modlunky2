from pathlib import Path

from .base_classes import BaseSpriteLoader


TILENAMES = [
    "blank",
    "chunk1",
    "chunk2",
    "chunk3",
    "styled",
    "yellowdoor",
    "enter",
    "exit",
]

class TilecodeExtras(BaseSpriteLoader):
    """ Extra tiles used for the level editor. """
    _sprite_sheet_path = Path("static/images/tilecodeextras.png")
    _chunk_size = 50
    _chunk_map = {
        tilename: (idx, 0, idx + 1, 1)
        for idx, tilename in enumerate(TILENAMES)
    }
