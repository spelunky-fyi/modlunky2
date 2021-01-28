from pathlib import Path

from .base_classes import BaseSpriteLoader


class JournalTrapSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/journal_entry_traps.png")
    _chunk_size = 160
    _chunk_map = {
        "journal_arrow_trap": (0, 0, 1, 1),
        "journal_spear_trap": (1, 0, 2, 1),
        "journal_thorny_vine": (2, 0, 3, 1),
        "journal_powder_box": (3, 0, 4, 1),
        "journal_falling_platform": (4, 0, 5, 1),
        "journal_crush_trap": (6, 0, 7, 1),
        "journal_laser_trap": (7, 0, 8, 1),
        "journal_spring_trap": (8, 0, 9, 1),
        "journal_landmine": (9, 0, 10, 1),
        "journal_spikes": (0, 1, 1, 2),
        "journal_spark_trap": (1, 1, 2, 2),
        "journal_egg_sac": (2, 1, 3, 2),
        "journal_bear_trap": (3, 1, 4, 2),
        "journal_totem_trap": (0, 4, 1, 6),
        "journal_lion_trap": (1, 4, 2, 6),
        "journal_log_trap": (2, 4, 3, 6),
        "journal_sticky_trap": (3, 4, 4, 6),
        "journal_sliding_wall": (4, 4, 5, 6),
        "journal_giant_crush_trap": (0, 8, 2, 10),
        "journal_boulder": (2, 8, 4, 10),
        "journal_giant_clam": (4, 8, 6, 10),
        "journal_bone_drop": (8, 8, 10, 10),
        "journal_frog_trap": (6, 9, 8, 10),
    }
