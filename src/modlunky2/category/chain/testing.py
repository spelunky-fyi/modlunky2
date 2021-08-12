from dataclasses import dataclass
from typing import Iterable
from modlunky2.category.chain.common import ChainStatus

from modlunky2.mem.entities import EntityDBEntry, EntityType, Player
from modlunky2.mem.testing import EntityMapBuilder


@dataclass(frozen=True)
class FakeStepper:
    last_status: ChainStatus


def make_player_with_hh_items(
    entity_map: EntityMapBuilder, hh_item_types: Iterable[EntityType]
):
    hh_item_ids = entity_map.add_trivial_entities(hh_item_types)
    hh_id = entity_map.add_entity(Player(items=hh_item_ids))

    return Player(linked_companion_child=hh_id)


def make_player_with_hh_type(entity_map: EntityMapBuilder, hh_type: EntityType):
    hh_entity_db = EntityDBEntry(id=hh_type)
    hh_entity = Player(type=hh_entity_db)
    hh_id = entity_map.add_entity(hh_entity)

    return Player(linked_companion_child=hh_id)
