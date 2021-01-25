from pathlib import Path

from ..base_classes.base_sprite_merger import BaseSpriteMerger
from ..monsters.mounts import Mounts
from ..journal_mons import JournalMonsterSheet
from ..journal_items import JournalItemSheet
from ..items import ItemSheet
from ..util import chunks_from_animation


class TurkeySpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/turkey_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Mounts: {
            **chunks_from_animation("turkey_row_0_", (0, 0, 1, 1), 14),
            **chunks_from_animation("turkey_row_1_", (0, 1, 1, 2), 16),
            **chunks_from_animation("turkey_row_2_", (0, 2, 1, 3), 16),
            **chunks_from_animation("turkey_row_3_", (0, 3, 1, 4), 14),
        },
        JournalMonsterSheet: {"journal_turkey": (0, 0, 1, 1)},
        JournalItemSheet: {"journal_cooked_turkey": (0, 0, 1, 1)},
        ItemSheet: {"cooked_turkey": (0, 0, 1, 1)},
    }


class RockdogSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/rockdog_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Mounts: {
            **chunks_from_animation("rockdog_row_0_", (0, 0, 1, 1), 14),
            **chunks_from_animation("rockdog_row_1_", (0, 1, 1, 2), 12),
            **chunks_from_animation("rockdog_row_2_", (0, 2, 1, 3), 15),
            **chunks_from_animation("rockdog_row_3_", (0, 3, 1, 4), 14),
        },
        JournalMonsterSheet: {"journal_rockdog": (0, 0, 1, 1)},
    }


class AxolotlSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/axolotl_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Mounts: {
            **chunks_from_animation("axolotl_row_0_", (0, 0, 1, 1), 14),
            **chunks_from_animation("axolotl_row_1_", (0, 1, 1, 2), 12),
            **chunks_from_animation("axolotl_row_2_", (0, 2, 1, 3), 15),
            **chunks_from_animation("axolotl_row_3_", (0, 3, 1, 4), 14),
        },
        JournalMonsterSheet: {"journal_axolotl": (0, 0, 1, 1)},
    }


class QilinSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/qilin_full.png")
    _grid_hint_size = 8
    _origin_map = {
        Mounts: {
            **chunks_from_animation("qilin_row_0_", (0, 0, 1, 1), 14),
            **chunks_from_animation("qilin_row_1_", (0, 1, 1, 2), 12),
            **chunks_from_animation("qilin_row_2_", (0, 2, 1, 3), 15),
            **chunks_from_animation("qilin_row_3_", (0, 3, 1, 4), 14),
        },
        JournalMonsterSheet: {"journal_qilin": (0, 0, 1, 1)},
    }
