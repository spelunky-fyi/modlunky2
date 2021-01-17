from pathlib import Path

from .base_classes import BaseSpriteLoader


class JournalBigMonsterSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/journal_entry_mons_big.png")
    _chunk_size = 320
    _chunk_map = {
        "journal_quill_back": (0, 0, 1, 1),
        "journal_olmec": (1, 0, 2, 1),
        "journal_mummy": (2, 0, 3, 1),
        "journal_anubis": (3, 0, 4, 1),
        "journal_lamassu": (4, 0, 5, 1),
        "journal_queen_bee": (0, 1, 1, 2),
        "journal_ghost": (1, 1, 2, 2),
        "journal_yeti_king": (3, 1, 4, 2),
        "journal_yeti_queen": (4, 1, 5, 2),
        "journal_goliath_frog": (0, 2, 1, 3),
        "journal_giant_spider": (1, 2, 2, 3),
        "journal_lavamander": (2, 2, 3, 3),
        "journal_panxie": (3, 2, 4, 3),
        "journal_celestial_jellyfish": (4, 2, 5, 3),
        "journal_eggplant_minister": (0, 3, 1, 4),
        "journal_mech_rider": (1, 3, 2, 4),
        "journal_great_humphead": (2, 3, 3, 4),
        "journal_lahamu": (3, 3, 4, 4),
        "journal_ammit": (4, 3, 5, 4),
        "journal_anubis_2": (0, 4, 1, 5),
        "journal_hundun": (1, 4, 2, 5),
        "journal_kingu": (2, 4, 3, 5),
        "journal_osiris": (3, 4, 4, 5),
        "journal_tiamat": (4, 4, 5, 5),
        "journal_giant_fly": (0, 5, 1, 6),
    }
