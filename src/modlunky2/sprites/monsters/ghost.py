from pathlib import Path

from ..base_classes.base_json_sprite_loader import BaseJsonSpriteLoader
from ..util import chunks_from_animation


class Ghost(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_ghost.png")
    _chunk_size = 128
    _chunk_map = {
        "ghist_shopkeeper": (7, 10, 8, 11),
        "ghost": (0, 0, 2, 2),
        **chunks_from_animation("ghist_angry_0", (7, 11, 8, 12), 3),
        **chunks_from_animation("ghist_angry_1", (10, 11, 11, 12), 3),
        **chunks_from_animation("ghist_angry_2", (13, 11, 14, 12), 1),
    }
    _entity_names = [
        "ENT_TYPE_MONS_GHOST",
        "ENT_TYPE_MONS_GHOST_MEDIUM_SAD",
        "ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY",
        "ENT_TYPE_MONS_GHOST_SMALL_SAD",
        "ENT_TYPE_MONS_GHOST_SMALL_HAPPY",
        "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED",
        "ENT_TYPE_MONS_GHOST_SMALL_ANGRY",
        "ENT_TYPE_MONS_GHIST",
        "ENT_TYPE_FX_MEGAJELLYFISH_CROWN",
        "ENT_TYPE_FX_MEGAJELLYFISH_BOTTOM",
        "ENT_TYPE_FX_MEGAJELLYFISH_TAIL",
        "ENT_TYPE_FX_MEGAJELLYFISH_TAIL_BG",
        "ENT_TYPE_FX_MEGAJELLYFISH_FLIPPER",
        "ENT_TYPE_FX_MEGAJELLYFISH_STAR",
        "ENT_TYPE_MONS_MEGAJELLYFISH",
        "ENT_TYPE_MONS_MEGAJELLYFISH_BACKGROUND",
    ]
