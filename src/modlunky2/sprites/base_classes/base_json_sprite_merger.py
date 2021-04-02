from abc import abstractmethod
from typing import List, Dict, Type

from .base_sprite_loader import BaseSpriteLoader
from .base_sprite_merger import BaseSpriteMerger
from ..util import target_chunks_from_json


class BaseJsonSpriteMerger(BaseSpriteMerger):
    @property
    @abstractmethod
    def _entity_origins(self) -> Dict[Type[BaseSpriteLoader], List[str]]:
        """
        Define names of entities that should additionally be added to the _origin_map per loader type
        """
        pass

    def __init__(self, entities_json: dict, textures_json: dict, *args, **kwargs):
        # Extend _origin_map first because BaseSpriteMerger.__init__ needs that information ready
        for loader_type, entity_names in self._entity_origins.items():
            if loader_type not in self._origin_map:
                front_inserted_dict = { loader_type: {} }
                front_inserted_dict.update(self._origin_map)
                self._origin_map = front_inserted_dict
            for entity_name in entity_names:
                self._origin_map[loader_type].update(
                    target_chunks_from_json(entities_json, textures_json, entity_name)
                )

        super().__init__(*args, **kwargs)
