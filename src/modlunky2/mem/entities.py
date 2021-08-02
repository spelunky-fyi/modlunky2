from __future__ import annotations  # PEP 563
from dataclasses import dataclass
import json
from enum import IntEnum
from typing import ClassVar, Optional, Tuple

from modlunky2.constants import BASE_DIR
from modlunky2.mem.memrauder.dsl import (
    poly_pointer,
    struct_field,
    dc_struct,
    pointer,
    sc_uint8,
    sc_uint32,
    sc_int8,
    sc_int16,
    sc_int32,
    sc_bool,
)
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.memrauder.msvc import vector


def _make_entity_type_enum():
    with open(BASE_DIR / "static/game_data/entities.json") as entities_file:
        entities_json = json.load(entities_file)

        enum_values = {
            name[len("ENT_TYPE_") :]: obj["id"] for name, obj in entities_json.items()
        }

    return IntEnum("EntityType", enum_values)


EntityType = _make_entity_type_enum()


MOUNTS = {
    EntityType.MOUNT_TURKEY,
    EntityType.MOUNT_ROCKDOG,
    EntityType.MOUNT_AXOLOTL,
    EntityType.MOUNT_MECH,
    EntityType.MOUNT_QILIN,
}

BACKPACKS = {
    EntityType.ITEM_CAPE,
    EntityType.ITEM_VLADS_CAPE,
    EntityType.ITEM_HOVERPACK,
    EntityType.ITEM_JETPACK,
    EntityType.ITEM_POWERPACK,
    EntityType.ITEM_TELEPORTER_BACKPACK,
}

LOW_BANNED_ATTACKABLES = {
    EntityType.ITEM_WEBGUN,
    EntityType.ITEM_SHOTGUN,
    EntityType.ITEM_FREEZERAY,
    EntityType.ITEM_CLONEGUN,
    EntityType.ITEM_CAMERA,
    EntityType.ITEM_TELEPORTER,
    EntityType.ITEM_BOOMERANG,
    EntityType.ITEM_MACHETE,
    EntityType.ITEM_BROKENEXCALIBUR,
    EntityType.ITEM_PLASMACANNON,
    EntityType.ITEM_LIGHT_ARROW,
    EntityType.ITEM_CROSSBOW,
    # Allowed in moon challenge, sun challenge, waddlers lair,
    # once on hundun w/ arrow of light
    EntityType.ITEM_HOUYIBOW,
    # Allowed in Abzu
    EntityType.ITEM_EXCALIBUR,
    # Allowed to be used in moon challenge
    EntityType.ITEM_MATTOCK,
}

LOW_BANNED_THROWABLES = {
    EntityType.ITEM_LIGHT_ARROW,
}

SHIELDS = {
    EntityType.ITEM_METAL_SHIELD,
    EntityType.ITEM_WOODEN_SHIELD,
}

TELEPORT_ENTITIES = {
    EntityType.ITEM_TELEPORTER,
    EntityType.ITEM_TELEPORTER_BACKPACK,
    EntityType.ITEM_POWERUP_TRUECROWN,
}

CHAIN_POWERUP_ENTITIES = {
    EntityType.ITEM_POWERUP_UDJATEYE,
    EntityType.ITEM_POWERUP_CROWN,
    EntityType.ITEM_POWERUP_HEDJET,
    EntityType.ITEM_POWERUP_ANKH,
    EntityType.ITEM_POWERUP_TABLETOFDESTINY,
}

NON_CHAIN_POWERUP_ENTITIES = {
    EntityType.ITEM_POWERUP_CLIMBING_GLOVES,
    EntityType.ITEM_POWERUP_COMPASS,
    # Explicitly excluded as having the crown is a valid modifier to every
    # category.
    # EntityType.ITEM_POWERUP_EGGPLANTCROWN,
    EntityType.ITEM_POWERUP_KAPALA,
    EntityType.ITEM_POWERUP_PARACHUTE,
    EntityType.ITEM_POWERUP_PASTE,
    EntityType.ITEM_POWERUP_PITCHERSMITT,
    EntityType.ITEM_POWERUP_SKELETON_KEY,
    EntityType.ITEM_POWERUP_SPECIALCOMPASS,
    EntityType.ITEM_POWERUP_SPECTACLES,
    EntityType.ITEM_POWERUP_SPIKE_SHOES,
    EntityType.ITEM_POWERUP_SPRING_SHOES,
    EntityType.ITEM_POWERUP_TRUECROWN,
}


class Layer(IntEnum):
    FRONT = 0
    BACK = 1


class CharState(IntEnum):
    FLAILING = 0
    STANDING = 1
    SITTING = 2
    UNKNOWN_1 = 3
    HANGING = 4
    DUCKING = 5
    CLIMBING = 6
    PUSHING = 7
    JUMPING = 8
    FALLING = 9
    DROPPING = 10
    UNKNOWN_2 = 11
    ATTACKING = 12
    UNKNOWN_3 = 13
    UNKNOWN_4 = 14
    UNKNOWN_5 = 15
    UNKNOWN_6 = 16
    THROWING = 17
    STUNNED = 18
    ENTERING = 19
    LOADING = 20
    EXITING = 21
    DYING = 22
    UNKNOWN_7 = 23
    UNKNOWN_8 = 24
    UNKNOWN_9 = 25
    UNKNOWN_10 = 26
    UNKNOWN_11 = 27
    UNKNOWN_12 = 28
    UNKNOWN_13 = 29
    UNKNOWN_14 = 30


@dataclass(frozen=True)
class EntityDBEntry:
    _size_as_element_: ClassVar[int] = 256  # Size of EntityDB struct

    id: int = struct_field(0x14, sc_uint32)  # pylint: disable=invalid-name

    # TODO try constructing eagerly
    @property
    def entity_type(self) -> EntityType:
        return EntityType(self.id)

    @property
    def name(self):
        return self.entity_type.name


# EntityReduced exists only to break the circular dependency via 'overlay'
@dataclass(frozen=True)
class EntityReduced:
    type: Optional[EntityDBEntry] = struct_field(0x08, pointer(dc_struct))
    items: Optional[Tuple[int, ...]] = struct_field(0x18, vector(sc_uint32))
    layer: int = struct_field(0x98, sc_uint8)


@dataclass(frozen=True)
class Entity(EntityReduced):
    overlay: PolyPointer[EntityReduced] = struct_field(0x10, poly_pointer(dc_struct))


@dataclass(frozen=True)
class Movable(Entity):
    holding_uid: int = struct_field(0x108, sc_int32)
    state: CharState = struct_field(0x10C, sc_uint8)
    last_state: CharState = struct_field(0x10D, sc_uint8)
    health: int = struct_field(0x10F, sc_int8)


@dataclass(frozen=True)
class Mount(Movable):
    is_tamed: bool = struct_field(0x149, sc_bool)


@dataclass(frozen=True)
class Inventory:
    # Amount of money collected in the current level
    money: int = struct_field(0x00, sc_uint32)
    bombs: int = struct_field(0x04, sc_uint8)
    ropes: int = struct_field(0x05, sc_uint8)
    poison_tick_timer: int = struct_field(0x06, sc_int16)
    cursed: bool = struct_field(0x08, sc_bool)
    kills_level: int = struct_field(0x1424, sc_uint32)
    kills_total: int = struct_field(0x1428, sc_uint32)
    collected_money_total: int = struct_field(0x1520, sc_uint32)


@dataclass(frozen=True)
class Player(Movable):
    inventory: Optional[Inventory] = struct_field(0x138, pointer(dc_struct))
