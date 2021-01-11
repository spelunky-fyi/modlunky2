from pathlib import Path

from ..base_classes.base_sprite_loader import BaseSpriteLoader


class Ghost(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_ghost.png")
    _chunk_size = 128
    _chunk_map = {"ghist_shopkeeper": (7, 10, 8, 11), "ghost": (0, 0, 2, 2)}
