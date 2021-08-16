from dataclasses import dataclass
import dataclasses
from typing import ClassVar, Dict, Iterable, Tuple

from modlunky2.mem.entities import Entity, EntityDBEntry, EntityType
from modlunky2.mem.memrauder.model import MemContext, PolyPointer
from modlunky2.mem.memrauder.msvc import DictUnorderedMap


@dataclass
class EntityMapBuilder:
    next_uid: int = 1
    entity_map: Dict[int, PolyPointer[Entity]] = dataclasses.field(default_factory=dict)
    mem_ctx: MemContext = dataclasses.field(default_factory=MemContext)

    FAKE_ADDR: ClassVar[int] = 1234567

    # Adds an entity with only its type field set.
    # Returns the UID
    def add_trivial_entity(self, entity_type: EntityType) -> int:
        entity = Entity(type=EntityDBEntry(entity_type))
        return self.add_entity(entity)

    # Adds entities with only their type field set.
    # Returns the UIDs
    def add_trivial_entities(self, entity_types: Iterable[EntityType]) -> Tuple[int]:
        id_list = [self.add_trivial_entity(item_type) for item_type in entity_types]
        return tuple(id_list)

    # Adds an entity and returns the UID
    def add_entity(self, entity: Entity) -> int:
        poly_entity = PolyPointer(
            addr=self.FAKE_ADDR, value=entity, mem_ctx=self.mem_ctx
        )

        item_uid = self.next_uid
        self.next_uid += 1
        self.entity_map[item_uid] = poly_entity
        return item_uid

    def build(self):
        return DictUnorderedMap(self.entity_map)
