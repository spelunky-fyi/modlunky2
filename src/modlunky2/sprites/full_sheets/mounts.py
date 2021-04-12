from pathlib import Path

from ..base_classes.base_json_sprite_merger import BaseJsonSpriteMerger
from ..monsters.mounts import Mounts
from ..journal_mons import JournalMonsterSheet
from ..journal_items import JournalItemSheet
from ..items import ItemSheet
from ..util import chunks_from_animation


class TurkeySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Mounts/turkey.png")
    _grid_hint_size = 8
    _origin_map = {
        Mounts: { **chunks_from_animation("turkey_neck", (0, 0, 1, 1), 4), },
        JournalMonsterSheet: {"journal_turkey": (0, 0, 1, 1)},
        JournalItemSheet: {"journal_cooked_turkey": (0, 0, 1, 1)},
        ItemSheet: {"cooked_turkey": (0, 0, 1, 1)},
    }
    _entity_origins = {Mounts: ["ENT_TYPE_MOUNT_TURKEY"]}


class RockdogSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Mounts/rockdog.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_rockdog": (0, 0, 1, 1)},
    }
    _entity_origins = {Mounts: ["ENT_TYPE_MOUNT_ROCKDOG"]}


class AxolotlSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Mounts/axolotl.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_axolotl": (0, 0, 1, 1)},
    }
    _entity_origins = {Mounts: ["ENT_TYPE_MOUNT_AXOLOTL", "ENT_TYPE_FX_AXOLOTL_HEAD_ENTERING_DOOR"]}


class QilinSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Mounts/qilin.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_qilin": (0, 0, 1, 1)},
    }
    _entity_origins = {Mounts: ["ENT_TYPE_MOUNT_QILIN"]}
