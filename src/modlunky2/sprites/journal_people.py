from pathlib import Path

from .base_classes import BaseSpriteLoader


class JournalPeopleSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/journal_entry_people.png")
    _chunk_size = 160
    _chunk_map = {
        "journal_char_yellow": (0, 0, 1, 1),
        "journal_char_magenta": (1, 0, 2, 1),
        "journal_char_cyan": (2, 0, 3, 1),
        "journal_char_black": (3, 0, 4, 1),
        "journal_char_cinnabar": (4, 0, 5, 1),
        "journal_char_green": (5, 0, 6, 1),
        "journal_char_olive": (6, 0, 7, 1),
        "journal_char_white": (7, 0, 8, 1),
        "journal_char_cerulean": (8, 0, 9, 1),
        "journal_char_blue": (9, 0, 10, 1),
        "journal_char_lime": (0, 1, 1, 2),
        "journal_char_lemon": (1, 1, 2, 2),
        "journal_char_iris": (2, 1, 3, 2),
        "journal_char_gold": (3, 1, 4, 2),
        "journal_char_red": (4, 1, 5, 2),
        "journal_char_pink": (5, 1, 6, 2),
        "journal_char_violet": (6, 1, 7, 2),
        "journal_char_gray": (7, 1, 8, 2),
        "journal_char_khaki": (8, 1, 9, 2),
        "journal_char_orange": (9, 1, 10, 2),
        "journal_hired_hand": (0, 2, 1, 3),
        "journal_eggplant_child": (1, 2, 2, 3),
        "journal_shopkeeper": (2, 2, 3, 3),
        "journal_tun": (3, 2, 4, 3),
        "journal_yang": (4, 2, 5, 3),
        "journal_eggplant_king": (4, 2, 6, 4),
        "journal_van_horsing": (5, 2, 6, 3),
        "journal_sparrow": (6, 2, 7, 3),
        "journal_madame_tusk": (6, 2, 8, 4),
        "journal_parsley": (7, 2, 8, 3),
        "journal_parsnip": (8, 2, 9, 3),
        "journal_waddler": (8, 2, 10, 4),
        "journal_parmesan": (9, 2, 10, 3),
        "journal_beg": (0, 3, 1, 4),
        "journal_tusks_bodyguard": (1, 3, 2, 4),
        "journal_cave_man_shopkeeper": (2, 3, 3, 4),
        "journal_ghost_shopkeeper": (3, 3, 4, 4),
        "journal_mama_tunnel": (0, 4, 1, 5),
    }
