from pathlib import Path

from .base_classes import BaseSpriteLoader
from .util import chunks_from_animation


class MenuLeaderSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/menu_leader.png")
    _chunk_size = 64
    _chunk_map = {
        "leader_char_yellow": (0, 7, 2, 8),
        "leader_char_magenta": (2, 7, 4, 8),
        "leader_char_cyan": (4, 7, 6, 8),
        "leader_char_black": (6, 7, 8, 8),
        "leader_char_cinnabar": (8, 7, 10, 8),
        "leader_char_green": (10, 7, 12, 8),
        "leader_char_olive": (12, 7, 14, 8),
        "leader_char_white": (14, 7, 16, 8),
        "leader_char_cerulean": (16, 7, 18, 8),
        "leader_char_blue": (18, 7, 20, 8),
        "leader_char_lime": (0, 9, 2, 10),
        "leader_char_lemon": (2, 9, 4, 10),
        "leader_char_iris": (4, 9, 6, 10),
        "leader_char_gold": (6, 9, 7, 10),
        "leader_char_red": (8, 9, 10, 10),
        "leader_char_pink": (10, 9, 12, 10),
        "leader_char_violet": (12, 9, 14, 10),
        "leader_char_gray": (14, 9, 16, 10),
        "leader_char_khaki": (16, 9, 18, 10),
        "leader_char_orange": (18, 9, 20, 10),
    }
