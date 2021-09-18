from pathlib import Path

from modlunky2.sprites.base_classes.base_json_sprite_merger import BaseJsonSpriteMerger
from modlunky2.sprites.monsters.pets import Pets
from modlunky2.sprites.journal_mons import JournalMonsterSheet
from modlunky2.sprites.menu_basic import MenuBasicSheet, PetHeadsSheet


class MontySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Pets/monty_v2.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_monty": (0, 0, 1, 1)},
        MenuBasicSheet: {"basic_monty": (0, 0, 1, 1)},
        PetHeadsSheet: {"pet_head_monty": (0, 0, 1, 1)},
    }
    _entity_origins = {Pets: ["ENT_TYPE_MONS_PET_DOG"]}


class PercySpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Pets/percy_v2.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_percy": (0, 0, 1, 1)},
        MenuBasicSheet: {"basic_percy": (0, 0, 1, 1)},
        PetHeadsSheet: {"pet_head_percy": (0, 0, 1, 1)},
    }
    _entity_origins = {Pets: ["ENT_TYPE_MONS_PET_CAT"]}


class PoochiSpriteMerger(BaseJsonSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/Pets/poochi_v2.png")
    _grid_hint_size = 8
    _origin_map = {
        JournalMonsterSheet: {"journal_poochi": (0, 0, 1, 1)},
        MenuBasicSheet: {"basic_poochi": (0, 0, 1, 1)},
        PetHeadsSheet: {"pet_head_poochi": (0, 0, 1, 1)},
    }
    _entity_origins = {Pets: ["ENT_TYPE_MONS_PET_HAMSTER"]}
