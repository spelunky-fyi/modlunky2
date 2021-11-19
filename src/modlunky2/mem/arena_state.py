import enum
from dataclasses import dataclass
from typing import FrozenSet, Tuple

from serde import serialize, deserialize

from modlunky2.mem.memrauder.dsl import (
    array,
    struct_field,
    sc_uint8,
    sc_int8,
    sc_bool,
)


class ArenaFormat(enum.IntEnum):
    DEATHMATCH = 0
    HOLD_THE_IDOL = 1


class ArenaRuleset(enum.IntEnum):
    CASUAL = 0
    TOURNAMENT = 1
    JOUST = 2
    FRANTIC = 3
    CUSTOM = 4
    FAVORITE = 5


class ArenaTimer(enum.IntEnum):
    TIME_00_30 = 0
    TIME_01_00 = 1
    TIME_01_30 = 2
    TIME_02_00 = 3
    TIME_02_30 = 4
    TIME_03_00 = 5
    TIME_03_30 = 6
    TIME_04_00 = 7
    TIME_04_30 = 8
    TIME_05_00 = 9
    TIME_05_30 = 10
    TIME_06_00 = 11
    TIME_06_30 = 12
    TIME_07_00 = 13
    TIME_07_30 = 14
    TIME_08_00 = 15
    TIME_08_30 = 16
    TIME_09_00 = 17
    TIME_09_30 = 18
    TIME_10_00 = 19
    INFINITE = 20


class ArenaTimerEnding(enum.IntEnum):
    ROUND_ENDS = 0
    DEATH_MIST = 1
    ALIEN_BLAST = 2
    LOOSE_BOMBS = 3
    GHOST = 4
    RANDOM = 5


class ArenaTimeToWin(enum.IntEnum):
    SECONDS_10 = 0
    SECONDS_20 = 1
    SECONDS_30 = 2
    SECONDS_40 = 3
    SECONDS_50 = 4
    SECONDS_60 = 5
    SECONDS_70 = 6
    SECONDS_80 = 7
    SECONDS_90 = 8
    SECONDS_99 = 9


class ArenaStunTime(enum.IntEnum):
    X0_00 = 0
    X0_25 = 1
    X0_50 = 2
    X0_75 = 3
    X1_00 = 4
    X1_25 = 5
    X1_50 = 6
    X1_75 = 7
    X2_00 = 8


class ArenaMount(enum.IntEnum):
    NONE = 0
    TURKEY = 1
    ROCKDOG = 2
    AXOLOTL = 3
    RANDOM = 4


class ArenaSelect(enum.IntEnum):
    TAKE_TURNS = 0
    LOSER_PICKS = 1
    RANDOM_LEVEL = 2


class ArenaDarkLevelChance(enum.IntEnum):
    NONE = 0
    PERCENT_10 = 1
    PERCENT_50 = 2
    ALWAYS = 3


class ArenaCrateFrequency(enum.IntEnum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class ArenaWhipDamage(enum.IntEnum):
    HP_0 = 0
    HP_1 = 1
    HP_2 = 2
    HP_3 = 3
    HP_4 = 4
    HP_5 = 5
    HP_10 = 6
    HP_99 = 7


class ArenaBreathCooldown(enum.IntEnum):
    NONE = 0
    X0_25 = 1
    X0_50 = 2
    X0_75 = 3
    X1_00 = 4
    X1_25 = 5
    X1_50 = 6
    X1_75 = 7
    X2_00 = 8
    BREATH_OFF = 9


class ArenaItem(enum.IntEnum):
    NOTHING = -1
    ROCK = 0
    POT = enum.auto()
    BOMBBAG = enum.auto()
    BOMBBOX = enum.auto()
    ROPEPILE = enum.auto()
    PICKUP_12BAG = enum.auto()
    PICKUP_24BAG = enum.auto()
    COOKED_TURKEY = enum.auto()
    ROYAL_JELLY = enum.auto()
    TORCH = enum.auto()
    BOOMERANG = enum.auto()
    MACHETE = enum.auto()
    MATTOCK = enum.auto()
    CROSSBOW = enum.auto()
    WEBGUN = enum.auto()
    FREEZERAY = enum.auto()
    SHOTGUN = enum.auto()
    CAMERA = enum.auto()
    PLASMA_CANNON = enum.auto()
    WOODEN_SHIELD = enum.auto()
    METAL_SHIELD = enum.auto()
    TELEPORTER = enum.auto()
    MINE = enum.auto()
    SNAPTRAP = enum.auto()
    PASTE = enum.auto()
    CLIMBING_GLOVES = enum.auto()
    PITCHERS_MITT = enum.auto()
    SPIKE_SHOES = enum.auto()
    SPRING_SHOES = enum.auto()
    PARACHUTE = enum.auto()
    CAPE = enum.auto()
    VLADS_CAPE = enum.auto()
    JETPACK = enum.auto()
    HOVERPACK = enum.auto()
    TELEPACK = enum.auto()
    POWERPACK = enum.auto()
    EXCALIBUR = enum.auto()
    SCEPTER = enum.auto()
    KAPALA = enum.auto()
    TRUE_CROWN = enum.auto()


class ArenaLevel(enum.IntEnum):
    DWELLING_1 = 0
    DWELLING_2 = enum.auto()
    DWELLING_3 = enum.auto()
    DWELLING_4 = enum.auto()
    DWELLING_5 = enum.auto()
    JUNGLE_1 = enum.auto()
    JUNGLE_2 = enum.auto()
    JUNGLE_3 = enum.auto()
    JUNGLE_4 = enum.auto()
    JUNGLE_5 = enum.auto()
    VOLCANA_1 = enum.auto()
    VOLCANA_2 = enum.auto()
    VOLCANA_3 = enum.auto()
    VOLCANA_4 = enum.auto()
    VOLCANA_5 = enum.auto()
    TIDEPOOL_1 = enum.auto()
    TIDEPOOL_2 = enum.auto()
    TIDEPOOL_3 = enum.auto()
    TIDEPOOL_4 = enum.auto()
    TIDEPOOL_5 = enum.auto()
    TEMPLE_1 = enum.auto()
    TEMPLE_2 = enum.auto()
    TEMPLE_3 = enum.auto()
    TEMPLE_4 = enum.auto()
    TEMPLE_5 = enum.auto()
    ICECAVES_1 = enum.auto()
    ICECAVES_2 = enum.auto()
    ICECAVES_3 = enum.auto()
    ICECAVES_4 = enum.auto()
    ICECAVES_5 = enum.auto()
    NEOBABYLON_1 = enum.auto()
    NEOBABYLON_2 = enum.auto()
    NEOBABYLON_3 = enum.auto()
    NEOBABYLON_4 = enum.auto()
    NEOBABYLON_5 = enum.auto()
    SUNKENCITY_1 = enum.auto()
    SUNKENCITY_2 = enum.auto()
    SUNKENCITY_3 = enum.auto()
    SUNKENCITY_4 = enum.auto()
    SUNKENCITY_5 = enum.auto()


ARENA_STATE_BASE = 0x95C
ArenaItemsTuple = Tuple[
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
    bool,
]


@serialize(rename_all="spinalcase")
@deserialize(rename_all="spinalcase")
@dataclass(frozen=True)
class ArenaState:
    format: ArenaFormat = struct_field(
        0x964 - ARENA_STATE_BASE, sc_int8, default=ArenaFormat.DEATHMATCH
    )
    ruleset: ArenaRuleset = struct_field(
        0x965 - ARENA_STATE_BASE, sc_int8, default=ArenaRuleset.CUSTOM
    )
    timer: ArenaTimer = struct_field(
        0x978 - ARENA_STATE_BASE, sc_int8, default=ArenaTimer.TIME_02_00
    )
    timer_ending: ArenaTimerEnding = struct_field(
        0x979 - ARENA_STATE_BASE, sc_int8, default=ArenaTimerEnding.ROUND_ENDS
    )
    wins: int = struct_field(0x97A - ARENA_STATE_BASE, sc_uint8, default=5)
    lives: int = struct_field(0x97B - ARENA_STATE_BASE, sc_uint8, default=2)
    time_to_win: ArenaTimeToWin = struct_field(
        0x97C - ARENA_STATE_BASE, sc_int8, default=ArenaTimeToWin.SECONDS_30
    )
    health: int = struct_field(0x986 - ARENA_STATE_BASE, sc_uint8, default=4)
    bombs: int = struct_field(0x987 - ARENA_STATE_BASE, sc_uint8, default=4)
    ropes: int = struct_field(0x988 - ARENA_STATE_BASE, sc_uint8, default=4)
    stun_time: ArenaStunTime = struct_field(
        0x989 - ARENA_STATE_BASE, sc_int8, default=ArenaStunTime.X0_50
    )
    mount: ArenaMount = struct_field(
        0x98A - ARENA_STATE_BASE, sc_int8, default=ArenaMount.NONE
    )
    arena_select: ArenaSelect = struct_field(
        0x98B - ARENA_STATE_BASE, sc_int8, default=ArenaSelect.RANDOM_LEVEL
    )
    arenas: ArenaItemsTuple = struct_field(
        0x98C - ARENA_STATE_BASE,
        array(sc_bool, 40),
        default_factory=lambda: tuple([False] * 40),
    )
    dark_level_chance: ArenaDarkLevelChance = struct_field(
        0x9B4 - ARENA_STATE_BASE, sc_int8, default=ArenaDarkLevelChance.PERCENT_10
    )
    crate_frequency: ArenaCrateFrequency = struct_field(
        0x9B5 - ARENA_STATE_BASE, sc_int8, default=ArenaCrateFrequency.MEDIUM
    )
    items_enabled: ArenaItemsTuple = struct_field(
        0x9B6 - ARENA_STATE_BASE,
        array(sc_bool, 40),
        default_factory=lambda: tuple([False] * 40),
    )
    items_in_crate: ArenaItemsTuple = struct_field(
        0x9DE - ARENA_STATE_BASE,
        array(sc_bool, 40),
        default_factory=lambda: tuple([False] * 40),
    )
    held_item: ArenaItem = struct_field(
        0xA06 - ARENA_STATE_BASE, sc_int8, default=ArenaItem.NOTHING
    )
    equipped_backitem: ArenaItem = struct_field(
        0xA07 - ARENA_STATE_BASE, sc_int8, default=ArenaItem.NOTHING
    )
    equipped_items: ArenaItemsTuple = struct_field(
        0xA08 - ARENA_STATE_BASE,
        array(sc_bool, 40),
        default_factory=lambda: tuple([False] * 40),
    )
    whip_damage: ArenaWhipDamage = struct_field(
        0xA30 - ARENA_STATE_BASE, sc_int8, default=ArenaWhipDamage.HP_1
    )
    final_ghost: bool = struct_field(0xA31 - ARENA_STATE_BASE, sc_bool, default=True)
    breath_cooldown: ArenaBreathCooldown = struct_field(
        0xA32 - ARENA_STATE_BASE, sc_int8, default=ArenaBreathCooldown.X0_50
    )
    punish_ball: bool = struct_field(0xA33 - ARENA_STATE_BASE, sc_bool, default=False)

    @staticmethod
    def get_enabled_items(items: Tuple[bool, ...]) -> FrozenSet[ArenaItem]:
        return frozenset(ArenaItem(idx) for idx, item in enumerate(items) if item)

    def get_enabled_levels(self) -> FrozenSet[ArenaLevel]:
        return frozenset(
            ArenaLevel(idx) for idx, level in enumerate(self.arenas) if level
        )
