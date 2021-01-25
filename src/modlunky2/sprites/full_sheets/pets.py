from pathlib import Path

from ..base_classes.base_sprite_merger import BaseSpriteMerger
from ..monsters.pets import Pets
from ..journal_mons import JournalMonsterSheet
from ..util import chunks_from_animation


class MontySpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/monty_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Pets: {
            **chunks_from_animation("monty_row_0_", (0, 0, 1, 1), 12),
            **chunks_from_animation("monty_row_1_", (0, 1, 1, 2), 10),
            **chunks_from_animation("monty_row_2_", (0, 2, 1, 3), 12),
            **chunks_from_animation("monty_row_3_", (0, 3, 1, 4), 12),
        },
        JournalMonsterSheet: {"journal_monty": (0, 0, 1, 1)},
    }


class PercySpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/percy_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Pets: {
            **chunks_from_animation("percy_row_0_", (0, 0, 1, 1), 12),
            **chunks_from_animation("percy_row_1_", (0, 1, 1, 2), 10),
            **chunks_from_animation("percy_row_2_", (0, 2, 1, 3), 12),
            **chunks_from_animation("percy_row_3_", (0, 3, 1, 4), 12),
        },
        JournalMonsterSheet: {"journal_percy": (0, 0, 1, 1)},
    }


class PoochiSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/poochi_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Pets: {
            **chunks_from_animation("poochi_row_0_", (0, 0, 1, 1), 12),
            **chunks_from_animation("poochi_row_1_", (0, 1, 1, 2), 10),
            **chunks_from_animation("poochi_row_2_", (0, 2, 1, 3), 12),
            **chunks_from_animation("poochi_row_3_", (0, 3, 1, 4), 12),
        },
        JournalMonsterSheet: {"journal_poochi": (0, 0, 1, 1)},
    }
