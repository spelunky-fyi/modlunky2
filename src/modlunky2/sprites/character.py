from pathlib import Path

from .base_classes import BaseSpriteLoader
from .util import chunks_from_animation


class CharacterSheet(BaseSpriteLoader):
    _chunk_size = 128
    _chunk_map = {
        "portrait": (12, 1, 16, 7),
        "standing": (0, 0, 1, 1),
        **chunks_from_animation("walking", (1, 0, 2, 1), 8),
        "stunned": (9, 0, 10, 1),
        **chunks_from_animation("swimming", (10, 0, 11, 1), 6),
        **chunks_from_animation("crouching", (0, 1, 1, 2), 5),
        **chunks_from_animation("crawling", (5, 1, 6, 2), 7),
        **chunks_from_animation("stun", (0, 2, 1, 3), 4),
        **chunks_from_animation("flip", (4, 2, 5, 3), 7),
        "holding": (11, 2, 12, 3),
        **chunks_from_animation("teetering", (0, 3, 1, 4), 8),
        **chunks_from_animation("ledge_grab", (8, 3, 9, 4), 4),
        **chunks_from_animation("whipping", (0, 4, 1, 5), 6),
        **chunks_from_animation("throwing", (6, 4, 7, 5), 5),
        **chunks_from_animation("enter", (0, 5, 1, 6), 6),
        **chunks_from_animation("exit", (6, 5, 7, 6), 6),
        **chunks_from_animation("climbing_ladder", (0, 6, 1, 7), 6),
        **chunks_from_animation("pushing", (6, 6, 7, 7), 6),
        **chunks_from_animation("climbing_rope", (0, 7, 1, 8), 10),
        **chunks_from_animation("crouching_mount", (10, 7, 11, 8), 5),
        **chunks_from_animation("looking_up", (0, 8, 1, 9), 7),
        "sitting": (7, 8, 8, 9),
        **chunks_from_animation("looking_up_sitting", (8, 8, 9, 9), 7),
        **chunks_from_animation("jumping", (0, 9, 1, 10), 12),
        "rope_coiled": (12, 9, 13, 10),
        "rope_top": (13, 9, 14, 10),
        "rope_short": (14, 9, 15, 10),
        "rope_burned": (15, 9, 16, 10),
        **chunks_from_animation("ghosting", (0, 10, 1, 11), 16),
        "icon": (0, 11, 1, 12),
        "bag": (1, 11, 2, 12),
        "wanted": (2, 11, 3, 12),
        "pointer": (3, 11, 4, 12),
        **chunks_from_animation("taming", (4, 11, 5, 12), 6),
        "ghost_stun": (10, 11, 11, 12),
        "rope_segment": (0, 12, 1, 13),
        **chunks_from_animation("rope_uncoiling", (1, 12, 2, 13), 4),
        "rope_end": (5, 12, 6, 13),
        **chunks_from_animation("rope_burning", (6, 12, 7, 13), 4),
        **chunks_from_animation("whip", (10, 12, 11, 13), 6),
        **chunks_from_animation("stun_effect", (0, 13, 1, 14), 12),
        **chunks_from_animation("petting", (0, 14, 1, 15), 8),
    }


class CharacterBlackSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_black.png")


class CharacterLimeSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_lime.png")


class CharacterMagentaSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_magenta.png")


class CharacterOliveSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_olive.png")


class CharacterOrangeSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_orange.png")


class CharacterPinkSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_pink.png")


class CharacterRedSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_red.png")


class CharacterVioletSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_violet.png")


class CharacterWhiteSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_white.png")


class CharacterYellowSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_yellow.png")


class CharacterBlueSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_blue.png")


class CharacterCeruleanSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_cerulean.png")


class CharacterCinnabarSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_cinnabar.png")


class CharacterCyanSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_cyan.png")


class CharacterEggChildSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_eggchild.png")


class CharacterGoldSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_gold.png")


class CharacterGraySheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_gray.png")


class CharacterGreenSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_green.png")


class CharacterHiredHandSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_hired.png")


class CharacterIrisSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_iris.png")


class CharacterKhakiSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_khaki.png")


class CharacterLemonSheet(CharacterSheet):
    _sprite_sheet_path = Path("Data/Textures/char_lemon.png")
