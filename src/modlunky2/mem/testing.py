from dataclasses import dataclass
import dataclasses
from typing import ClassVar, Dict, Iterable, List, Tuple

from modlunky2.mem.entities import Entity, EntityDBEntry, EntityType
from modlunky2.mem.memrauder.model import DictMap, MemContext, PolyPointer


def poly_pointer_no_mem(value):
    return PolyPointer(addr=0xBAD, mem_ctx=MemContext(), value=value)


def trivial_poly_entities(type_ids: Iterable[EntityType]) -> List[PolyPointer[Entity]]:
    return [poly_pointer_no_mem(Entity(type=EntityDBEntry(id=t))) for t in type_ids]


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
        return DictMap(self.entity_map)
