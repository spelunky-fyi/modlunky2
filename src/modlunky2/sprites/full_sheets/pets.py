from pathlib import Path

from ..base_classes.base_json_sprite_merger import BaseJsonSpriteMerger
from ..monsters.pets import Pets
from ..journal_mons import JournalMonsterSheet


class MontySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/pets/monty.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_monty": (0, 0, 1, 1)},
    }
    _entity_origins = {Pets: ["ENT_TYPE_MONS_PET_DOG"]}


class PercySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/pets/percy.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_percy": (0, 0, 1, 1)},
    }
    _entity_origins = {Pets: ["ENT_TYPE_MONS_PET_CAT"]}


class PoochiSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/pets/poochi.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_poochi": (0, 0, 1, 1)},
    }
    _entity_origins = {Pets: ["ENT_TYPE_MONS_PET_HAMSTER"]}
