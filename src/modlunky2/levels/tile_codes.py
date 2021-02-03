import re
from dataclasses import dataclass
from collections import OrderedDict
from typing import ClassVar, Optional, TextIO

from .utils import DirectivePrefixes, split_comment, to_line

VALID_TILE_CODES = set(
    [
        "alien",
        "adjacent_floor",
        "alien_generator",
        "alienqueen",
        "altar",
        "ammit",
        "ankh",
        "anubis",
        "arrow_trap",
        "autowalltorch",
        "babylon_floor",
        "beehive_floor",
        "bigspear_trap",
        "bodyguard",
        "bone_block",
        "bunkbed",
        "bush_block",
        "catmummy",
        "caveman",
        "caveman_asleep",
        "cavemanboss",
        "cavemanshopkeeper",
        "chain_ceiling",
        "chainandblocks_ceiling",
        "chair_looking_left",
        "chair_looking_right",
        "challenge_waitroom",
        "chunk_air",
        "chunk_door",
        "chunk_ground",
        "climbing_pole",
        "clover",
        "coarse_water",
        "cobra",
        "coffin",
        "cog_floor",
        "construction_sign",
        "conveyorbelt_left",
        "conveyorbelt_right",
        "cooked_turkey",
        "cookfire",
        "couch",
        "crate",
        "crate_bombs",
        "crate_parachute",
        "crate_ropes",
        "crocman",
        "crossbow",
        "crown_statue",
        "crushing_elevator",
        "crushtrap",
        "crushtraplarge",
        "cursed_pot",
        "die",
        "diningtable",
        "dm_spawn_point",
        "dog_sign",
        "door",
        "door_drop_held",
        "door2",
        "door2_secret",
        "dresser",
        "drill",
        "duat_floor",
        "eggplant_altar",
        "eggplant_child",
        "eggplant_door",
        "elevator",
        "empress_grave",
        "empty",
        "empty_mech",
        "entrance",
        "entrance_shortcut",
        "excalibur_stone",
        "exit",
        "factory_generator",
        "falling_platform",
        "floor",
        "floor_hard",
        "forcefield",
        "forcefield_top",
        "fountain_drain",
        "fountain_head",
        "ghist_door2",
        "ghist_shopkeeper",
        "giant_frog",
        "giant_spider",
        "giantclam",
        "goldbars",
        "growable_climbing_pole",
        "growable_vine",
        "guts_floor",
        "haunted_corpse",
        "hermitcrab",
        "honey_downwards",
        "honey_upwards",
        "houyibow",
        "icefloor",
        "idol",
        "idol_floor",
        "idol_hold",
        "imp",
        "jiangshi",
        "jumpdog",
        "jungle_floor",
        "jungle_spear_trap",
        "key",
        "kingu",
        "ladder",
        "ladder_plat",
        "lamassu",
        "lamp_hang",
        "landmine",
        "laser_trap",
        "lava",
        "lavamander",
        "leprechaun",
        "lightarrow",
        "littorch",
        "litwalltorch",
        "locked_door",
        "lockedchest",
        "madametusk",
        "mantrap",
        "mattock",
        "merchant",
        "minewood_floor",
        "minewood_floor_hanging_hide",
        "minewood_floor_noreplace",
        "minister",
        "moai_statue",
        "mosquito",
        "mother_statue",
        "mothership_floor",
        "mummy",
        "mushroom_base",
        "necromancer",
        "nonreplaceable_babylon_floor",
        "nonreplaceable_floor",
        "octopus",
        "oldhunter",
        "olmec",
        "olmecship",
        "olmite",
        "pagoda_floor",
        "pagoda_platform",
        "palace_bookcase",
        "palace_candle",
        "palace_chandelier",
        "palace_entrance",
        "palace_floor",
        "palace_table",
        "palace_table_tray",
        "pen_floor",
        "pen_locked_door",
        "pillar",
        "pipe",
        "plasma_cannon",
        "platform",
        "pot",
        "potofgold",
        "powder_keg",
        "push_block",
        "quicksand",
        "regenerating_block",
        "robot",
        "rock",
        "royal_jelly",
        "scorpion",
        "shop_door",
        "shop_item",
        "shop_pagodawall",
        "shop_sign",
        "shop_wall",
        "shop_woodwall",
        "shopkeeper",
        "shopkeeper_vat",
        "shortcut_station_banner",
        "sidetable",
        "singlebed",
        "sister",
        "sleeping_hiredhand",
        "slidingwall_ceiling",
        "slidingwall_switch",
        "snake",
        "snap_trap",
        "sorceress",
        "spark_trap",
        "spikes",
        "spring_trap",
        "stagnant_lava",
        "starting_exit",
        "sticky_trap",
        "stone_floor",
        "storage_floor",
        "storage_guy",
        "styled_floor",
        "sunken_floor",
        "surface_floor",
        "surface_hidden_floor",
        "telescope",
        "temple_floor",
        "thief",
        "thinice",
        "thorn_vine",
        "tiamat",
        "tikiman",
        "timed_forcefield",
        "timed_powder_keg",
        "tomb_floor",
        "treasure",
        "treasure_chest",
        "treasure_vaultchest",
        "tree_base",
        "turkey",
        "tv",
        "udjat_socket",
        "ufo",
        "upsidedown_spikes",
        "ushabti",
        "vault_wall",
        "vine",
        "vlad",
        "vlad_floor",
        "walltorch",
        "wanted_poster",
        "water",
        "witchdoctor",
        "woodenlog_trap",
        "woodenlog_trap_ceiling",
        "yama",
        "yang",
        "yeti",
        "zoo_exhibit",
    ]
)

NAME_PADDING = max(map(len, VALID_TILE_CODES)) + 4
PERCENT_DELIM = re.compile(r"%\d{1,2}%?")


class TileCodes:
    def __init__(self):
        self._inner = OrderedDict()
        self.comment = None

    def get(self, name):
        TileCode.validate_name(name)
        return self._inner.get(name)

    def set_obj(self, obj: "TileCode"):
        obj.validate()
        self._inner[obj.name] = obj

    def write(self, handle: TextIO):
        if self.comment:
            handle.write(f"{self.comment}\n")
        for obj in self._inner.values():
            handle.write(obj.to_line())
        handle.write("\n")


@dataclass
class TileCode:
    prefix: ClassVar[str] = DirectivePrefixes.TILE_CODE.value
    name: str
    value: str
    comment: Optional[str]

    @classmethod
    def parse(cls, line: str) -> "TileCode":
        rest, comment = split_comment(line)
        directive, value = rest.split(None, 1)
        name = directive[2:]

        if not name:
            raise ValueError("Directive missing name.")

        obj = cls(name, value, comment)
        obj.validate()

        return obj

    @staticmethod
    def validate_name(name: str):
        for part in PERCENT_DELIM.split(name):
            # names can have foo%50 where an empty rightside is valid.
            if not part:
                continue

            if part not in VALID_TILE_CODES:
                raise ValueError(f"Name {name!r} isn't a valid tile code.")

    def validate_value(self):
        if len(self.value) != 1:
            raise ValueError(
                f"Tilecode {self.name!r} has value {self.value!r} that's more than one character."
            )

    def validate(self):
        self.validate_name(self.name)
        self.validate_value()

    def to_line(self) -> str:
        return to_line(
            self.prefix, self.name, NAME_PADDING, self.value, 4, self.comment
        )

    def write(self, handle: TextIO):
        handle.write(self.to_line())
