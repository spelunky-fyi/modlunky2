from abc import abstractmethod
from typing import List, Dict, Type

from modlunky2.sprites.base_classes.base_sprite_loader import BaseSpriteLoader
from modlunky2.sprites.base_classes.base_sprite_merger import BaseSpriteMerger
from modlunky2.sprites.util import target_chunks_from_json


class BaseJsonSpriteMerger(BaseSpriteMerger):
    @property
    @abstractmethod
    def _entity_origins(self) -> Dict[Type[BaseSpriteLoader], List[str]]:
        """
        Define names of entities that should additionally be added to the _origin_map per loader type
        """

    def __init__(self, entities_json: dict, textures_json: dict, *args, **kwargs):
        # Extend _origin_map first because BaseSpriteMerger.__init__ needs that information ready
        for loader_type, entity_names in self._entity_origins.items():
            chunk_size = loader_type._chunk_size
            if loader_type not in self._origin_map:
                front_inserted_dict = {loader_type: []}
                front_inserted_dict.update(self._origin_map)
                self._origin_map = front_inserted_dict
            elif not isinstance(self._origin_map[loader_type], list):
                self._origin_map[loader_type] = [self._origin_map[loader_type]]
            for entity_name in entity_names:
                self._origin_map[loader_type].append(
                    target_chunks_from_json(
                        entities_json, textures_json, entity_name, chunk_size
                    )
                )

        super().__init__(*args, **kwargs)
