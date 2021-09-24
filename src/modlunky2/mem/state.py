from dataclasses import dataclass
import enum
from typing import FrozenSet, Optional, Tuple

from modlunky2.mem.entities import EntityType, Player

from modlunky2.mem.memrauder.dsl import (
    array,
    pointer,
    struct_field,
    dc_struct,
    sc_int32,
    sc_uint32,
    sc_int8,
    sc_uint8,
)
from modlunky2.mem.memrauder.model import DictMap
from modlunky2.mem.memrauder.spelunky2 import UidEntityMap, uid_entity_map


class RunRecapFlags(enum.IntFlag):
    PACIFIST = 1 << 1 - 1
    VEGAN = 1 << 2 - 1
    VEGETARIAN = 1 << 3 - 1
    PETTY_CRIMINAL = 1 << 4 - 1
    WANTED_CRIMINAL = 1 << 5 - 1
    CRIME_LORD = 1 << 6 - 1
    KING = 1 << 7 - 1
    QUEEN = 1 << 8 - 1
    FOOL = 1 << 9 - 1
    EGGPLANT = 1 << 10 - 1
    NO_GOLD = 1 << 11 - 1
    LIKED_PETS = 1 << 12 - 1
    LOVED_PETS = 1 << 13 - 1
    TOOK_DAMAGE = 1 << 14 - 1
    USED_ANKH = 1 << 15 - 1
    KILLED_KINGU = 1 << 16 - 1
    KILLED_OSIRIS = 1 << 17 - 1
    NORMAL_ENDING = 1 << 18 - 1
    HARD_ENDING = 1 << 19 - 1
    SPECIAL_ENDING = 1 << 20 - 1
    DIED = 1 << 21 - 1


class HudFlags(enum.IntFlag):
    UPBEAT_DWELLING_MUSIC = 1 << 1 - 1
    RUNNING_TUTORIAL_SPEEDRUN = 1 << 3 - 1
    ALLOW_PAUSE = 1 << 20 - 1
    HAVE_CLOVER = 1 << 23 - 1


class QuestFlags(enum.IntFlag):
    MOON_CHALLENGE = 1 << 25 - 1
    STAR_CHALLENGE = 1 << 26 - 1
    SUN_CHALLENGE = 1 << 27 - 1


class PresenceFlags(enum.IntFlag):
    MOON_CHALLENGE = 1 << 9 - 1
    STAR_CHALLENGE = 1 << 10 - 1
    SUN_CHALLENGE = 1 << 11 - 1


class LoadingState(enum.IntEnum):
    NOT_LOADING = 0
    START = 1
    LOADING = 2
    END = 3


class Screen(enum.IntEnum):
    UNKNOWN = -1
    LOGO = 0
    INTRO = 1
    PROLOGUE = 2
    TITLE = 3
    MAIN_MENU = 4
    OPTIONS = 5
    UNKNOWN_1 = 6
    LEADERBOARDS = 7
    SEED_INPUT = 8
    CHARACTER_SELECT = 9
    TEAM_SELECT = 10
    CAMP = 11
    LEVEL = 12
    LEVEL_TRANSITION = 13
    DEATH = 14
    SPACESHIP = 15
    ENDING = 16
    CREDITS = 17
    SCORES = 18
    CONSTELLATION = 19
    RECAP = 20
    ARENA_MENU = 21
    UNKNOWN_2 = 22
    UNKNOWN_3 = 23
    UNKNOWN_4 = 24
    ARENA_INTRO = 25
    ARENA_MATCH = 26
    ARENA_SCORES = 27
    LOADING_ONLINE = 28
    LOBBY = 29


class Theme(enum.IntEnum):
    BEFORE_FIRST_RUN = 0
    DWELLING = 1
    JUNGLE = 2
    VOLCANA = 3
    OLMEC = 4
    TIDE_POOL = 5
    TEMPLE = 6
    ICE_CAVES = 7
    NEO_BABYLON = 8
    SUNKEN_CITY = 9
    COSMIC_OCEAN = 10
    CITY_OF_GOLD = 11
    DUAT = 12
    ABZU = 13
    TIAMAT = 14
    EGGPLANT_WORLD = 15
    HUNDUN = 16
    BASE_CAMP = 17
    ARENA = 18


class WinState(enum.IntEnum):
    UNKNOWN = -1
    NO_WIN = 0
    TIAMAT = 1
    HUNDUN = 2
    COSMIC_OCEAN = 3


class FeedcodeNotFound(Exception):
    """Failed to find feedcode within Spelunky2 memory."""


@dataclass(frozen=True)
class Items:
    players: Tuple[Optional[Player], ...] = struct_field(
        0x08, array(pointer(dc_struct), 4)
    )


@dataclass(frozen=True)
class State:
    screen_last: Screen = struct_field(0x08, sc_int32, default=Screen.LEVEL_TRANSITION)
    screen: Screen = struct_field(0x0C, sc_int32, default=Screen.LEVEL)
    screen_next: Screen = struct_field(0x10, sc_int32, default=Screen.LEVEL_TRANSITION)
    loading: LoadingState = struct_field(
        0x14, sc_int32, default=LoadingState.NOT_LOADING
    )
    quest_flags: QuestFlags = struct_field(0x38, sc_uint32, default=0)
    # The total amount spent at shops and stolen by leprechauns. This is non-positive during the run.
    # If the run ends in a victory, the bonus will be added to this during the score screen.
    money_shop_total: int = struct_field(0x58, sc_int32, default=0)
    world_start: int = struct_field(0x5C, sc_uint8, default=1)
    level_start: int = struct_field(0x5D, sc_uint8, default=1)
    theme_start: Theme = struct_field(0x5E, sc_uint8, default=Theme.DWELLING)
    time_total: int = struct_field(0x64, sc_uint32, default=1)
    world: int = struct_field(0x68, sc_uint8, default=1)
    world_next: int = struct_field(0x69, sc_uint8, default=1)
    level: int = struct_field(0x6A, sc_uint8, default=1)
    level_next: int = struct_field(0x6B, sc_uint8, default=2)
    theme: Theme = struct_field(0x74, sc_uint8, default=Theme.DWELLING)
    theme_next: Theme = struct_field(0x75, sc_uint8, default=Theme.DWELLING)
    win_state: WinState = struct_field(0x76, sc_int8, default=WinState.NO_WIN)
    waddler_storage: FrozenSet[EntityType] = struct_field(
        0x8C, array(sc_uint32, 99), default=frozenset()
    )
    run_recap_flags: RunRecapFlags = struct_field(0xA34, sc_uint32, default=0)
    hud_flags: HudFlags = struct_field(0xA50, sc_uint32, default=0)
    time_level: int = struct_field(0xA44, sc_uint32, default=0)
    presence_flags: PresenceFlags = struct_field(0xA54, sc_uint32, default=0)
    next_entity_uid: int = struct_field(0x12E0, sc_uint32, default=0)
    items: Optional[Items] = struct_field(0x12F0, pointer(dc_struct), default=None)
    instance_id_to_pointer: UidEntityMap = struct_field(
        0x1348, uid_entity_map, default_factory=DictMap
    )
