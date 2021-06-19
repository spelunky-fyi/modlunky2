import json
from enum import IntEnum
from typing import Optional, TYPE_CHECKING

from modlunky2.constants import BASE_DIR

from .unordered_map import UnorderedMap

if TYPE_CHECKING:
    from . import Spel2Process


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
    EntityType.ITEM_HOVERPACK,
    EntityType.ITEM_JETPACK,
    EntityType.ITEM_POWERPACK,
    EntityType.ITEM_TELEPORTER_BACKPACK,
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


class EntityMap(UnorderedMap):
    KEY_CHAR = "<L"
    VALUE_CHAR = "P"

    def get(self, key, meta=None):
        result = super().get(key)
        if result is None:
            return None

        return Entity(self._proc, result)


class EntityDBEntry:
    def __init__(self, proc, offset):
        self._proc: "Spel2Process" = proc
        self._offset = offset

    @property
    def id(self):  # pylint: disable=invalid-name
        return self._proc.read_u32(self._offset + 0x14)

    @property
    def entity_type(self):
        return EntityType(self.id)

    @property
    def name(self):
        return self.entity_type.name


class EntityDB:

    ENTITY_DB_SIZE = 256  # Size of EntityDB

    def __init__(self, proc):
        self._proc: "Spel2Process" = proc
        self._offset = proc.get_offset_past_bundle()
        self._entity_db_ptr = self._get_entity_db_ptr()

    def _get_entity_db_ptr(self):
        entity_instr = self._proc.find(
            self._offset, b"\x48\xB8\x02\x55\xA7\x74\x52\x9D\x51\x43"
        )
        return self._proc.read_void_p(
            entity_instr + self._proc.read_u32(entity_instr - 4)
        )

    def get_entity_db_entry_by_id(self, entity_id) -> EntityDBEntry:
        return EntityDBEntry(
            self._proc, self._entity_db_ptr + (self.ENTITY_DB_SIZE * entity_id)
        )


class Entity:
    def __init__(self, proc, offset):
        self._proc: "Spel2Process" = proc
        self._offset = offset

    @property
    def type(self):
        result = self._proc.read_void_p(self._offset + 8)
        return EntityDBEntry(self._proc, result)

    @property
    def overlay(self) -> Optional["Entity"]:
        offset = self._offset + 0x10
        entity_ptr = self._proc.read_void_p(offset)
        if not entity_ptr:
            return None
        return Entity(self._proc, entity_ptr)

    @property
    def items(self):
        offset = self._offset + 0x18
        return self._proc.read_vector(offset, "<L")

    def as_movable(self) -> "Movable":
        return Movable(self._proc, self._offset)

    def as_mount(self) -> "Mount":
        return Mount(self._proc, self._offset)

    def as_player(self) -> "Player":
        return Player(self._proc, self._offset)


class Movable(Entity):
    pass


class Mount(Movable):
    @property
    def is_tamed(self) -> bool:
        offset = self._offset + 0x149
        return self._proc.read_bool(offset)


class Player(Movable):
    def inside(self):
        """std::map. Need to implement red/black tree."""
        # inside = player1_ent_addr + 0x128
        # print("inside", hex(inside))
        # print("")

        # node1_addr = proc.read_void_p(inside)
        # print("node1_addr", hex(node1_addr))
        # print("")

        # x = proc.read_memory(node1_addr, 8 * 3)
        # pointers = unpack(b"PPP", x)
        # print("x", list(map(hex, pointers)))
        # print("x more", proc.read_memory(node1_addr + (8 * 3), 4))
        # print(proc.read_memory(node1_addr + (8 * 3) + 4, 16))
        # print("x more", proc.read_u16(node1_addr + (8 * 3) + 4))

        # print("")
        # p = pointers[0]
        # x = proc.read_memory(p, 8 * 3)
        # pointers = unpack(b"PPP", x)
        # print("x", list(map(hex, pointers)))
        # print("x more", proc.read_memory(p + (8 * 3), 4))
        # print(proc.read_memory(p + (8 * 3) + 4, 16))
        # print("x more", proc.read_u16(p + (8 * 3) + 4))

        # print("")
        # p = pointers[2]
        # x = proc.read_memory(p, 8 * 3)
        # pointers = unpack(b"PPP", x)
        # print("x", list(map(hex, pointers)))
        # print("x more", proc.read_memory(p + (8 * 3), 4))
        # print("x more", hex(proc.read_u16(p + (8 * 3) + 4)))
        # item_count = proc.read_u64(inside + 8)
