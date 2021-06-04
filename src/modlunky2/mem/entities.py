import json
from enum import Enum
from typing import TYPE_CHECKING

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

    return Enum("EntityType", enum_values)


EntityType = _make_entity_type_enum()


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

    def id(self):  # pylint: disable=invalid-name
        return self._proc.read_u32(self._offset + 0x14)

    def name(self):
        return EntityType(self.id()).name


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

    def type(self):
        result = self._proc.read_void_p(self._offset + 8)
        return EntityDBEntry(self._proc, result)
