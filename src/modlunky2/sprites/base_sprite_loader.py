from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from .types import chunk_map_type


class BaseSpriteLoader(ABC):
    @property
    @abstractmethod
    def _sprite_sheet_path(self) -> Path:
        """
        Define the path from a "base path" to the specific png file this is for reading,
        for example for `items.png` it should return Path('Data/Textures/items.png')
        """
        pass

    @property
    @abstractmethod
    def _chunk_size(self) -> int:
        """
        define how many pixels wide/tall each piece is expected to be
        """
        pass

    @property
    @abstractmethod
    def _chunk_map(self) -> chunk_map_type:
        """
        Define the mapping of name, coordinates in a dictionary in the form of:
        `"thing_name": (1, 0, 2, 2)`
        The digits will be multiplied by the _chunk_size when the piece is accessed.
        """
        pass

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self._sprite_sheet = Image.open(self.base_path / self._sprite_sheet_path)

    def _get_block(
        self,
        left: Union[int, float],
        upper: Union[int, float],
        right: Union[int, float],
        lower: Union[int, float],
    ) -> Image.Image:
        """Used to get chunks of the sprite sheet."""
        bbox = tuple(map(lambda x: x * self._chunk_size, (left, upper, right, lower)))
        return self._sprite_sheet.crop(bbox)

    def get(self, name: str) -> Optional[Image.Image]:
        coords = self._chunk_map.get(name)
        if coords:
            return self._get_block(*coords)
