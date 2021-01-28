from pathlib import Path

from .base_classes import BaseSpriteLoader


class JournalPlaceSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/journal_entry_place.png")
    _chunk_size = 320
    _chunk_map = {
        "journal_dwelling": (0, 0, 2, 1),
        "journal_jungle": (2, 0, 4, 1),
        "journal_volcana": (4, 0, 6, 1),
        "journal_olmecs_lair": (6, 0, 8, 1),
        "journal_tide_pool": (0, 1, 2, 2),
        "journal_temple_of_anubis": (2, 1, 4, 2),
        "journal_ice_caves": (4, 1, 6, 2),
        "journal_neo_babylon": (6, 1, 8, 2),
        "journal_sunken_city": (0, 2, 2, 3),
        "journal_cosmic_ocean": (2, 2, 4, 3),
        "journal_city_of_gold": (4, 2, 6, 3),
        "journal_duat": (6, 2, 8, 3),
        "journal_abzu": (0, 3, 2, 4),
        "journal_tiamats_throne": (2, 3, 4, 4),
        "journal_eggplant_world": (4, 3, 6, 4),
        "journal_hunduns_hideaway": (6, 3, 8, 4),
    }
