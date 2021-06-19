import enum
from typing import List, TYPE_CHECKING
from struct import unpack

from .entities import EntityMap, Player

if TYPE_CHECKING:
    from . import Spel2Process


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


class Screen(enum.IntEnum):
    LOGO = 0
    INTRO = 1
    PROLOGUE = 2
    TITLE = 3
    MAIN_MENU = 4
    OPTIONS = 5
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
    ARENA_INTRO = 25
    ARENA_MATCH = 26
    ARENA_SCORES = 27
    LOADING_ONLINE = 28
    LOBBY = 29


class Theme(enum.IntEnum):
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


class State:
    def __init__(self, proc):
        self._proc: "Spel2Process" = proc
        self._offset = proc.get_feedcode() - 0x5F
        self._uid_to_entity = None

    @property
    def screen_last(self):
        return self._proc.read_i32(self._offset + 0x08)

    @property
    def screen(self):
        return self._proc.read_i32(self._offset + 0x0C)

    @property
    def screen_next(self):
        return self._proc.read_i32(self._offset + 0x10)

    @property
    def world_start(self):
        return self._proc.read_u8(self._offset + 0x5C)

    @property
    def level_start(self):
        return self._proc.read_u8(self._offset + 0x5D)

    @property
    def theme_start(self):
        return Theme(self._proc.read_u8(self._offset + 0x5E))

    @property
    def time_total(self):
        return self._proc.read_u32(self._offset + 0x64)

    @property
    def world(self):
        return self._proc.read_u8(self._offset + 0x68)

    @property
    def world_next(self):
        return self._proc.read_u8(self._offset + 0x69)

    @property
    def level(self):
        return self._proc.read_u8(self._offset + 0x6A)

    @property
    def level_next(self):
        return self._proc.read_u8(self._offset + 0x6B)

    @property
    def theme(self):
        return Theme(self._proc.read_u8(self._offset + 0x74))

    @property
    def theme_next(self):
        return Theme(self._proc.read_u8(self._offset + 0x75))

    @property
    def win_state(self):
        return WinState(self._proc.read_i8(self._offset + 0x76))

    @property
    def run_recap_flags(self):
        offset = self._offset + 0x9F4
        return RunRecapFlags(self._proc.read_u32(offset))

    @property
    def hud_flags(self):
        offset = self._offset + 0xA10
        return HudFlags(self._proc.read_u32(offset))

    @property
    def players(self) -> List[Player]:  # items
        offset = self._offset + 0x12B0
        items_ptr = self._proc.read_void_p(offset) + 8
        player_pointers = self._proc.read_memory(items_ptr, 8 * 4)

        players = []

        for idx in range(0, len(player_pointers), 8):
            player_pointer = player_pointers[idx : idx + 8]
            if player_pointer == b"\x00\x00\x00\x00\x00\x00\x00\x00":
                players.append(None)
                continue

            player_pointer = unpack("P", player_pointer)[0]
            players.append(Player(self._proc, player_pointer))

        return players

    @property
    def uid_to_entity(self):
        if self._uid_to_entity is None:
            offset = self._offset + 0x1308
            self._uid_to_entity = EntityMap(self._proc, offset)
        return self._uid_to_entity
