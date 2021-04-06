from abc import abstractmethod
from typing import List

from .base_sprite_loader import BaseSpriteLoader
from ..util import chunks_from_json


class BaseJsonSpriteLoader(BaseSpriteLoader):
    @property
    @abstractmethod
    def _entity_names(self) -> List[str]:
        """
        Define names of entities that should additionally be added to the _chunk_map
        """
        pass

    def __init__(self, entities_json, textures_json, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for entity_name in self._entity_names:
            self._chunk_map.update(
                chunks_from_json(
                    entities_json, textures_json, entity_name, self._chunk_size
                )
            )
