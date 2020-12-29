from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from .types import chunk_map_type

number = Union[float, int]


class AbstractDecoSheet(ABC):
    _sprite_sheet: Image.Image
    _base_path: Path

    @property
    @abstractmethod
    def chunk_map(self) -> chunk_map_type:
        raise NotImplementedError

    def __init__(self, base_path: Path):
        self._base_path = base_path
        self._sprite_sheet = Image.open(self._base_path / self._sheet_path)

    @property
    @abstractmethod
    def biome_name(self) -> str:
        raise NotImplementedError

    @property
    def _sheet_path(self):
        return Path(f"Data/Textures/deco_{self.biome_name}.png")

    def _get_block(
        self,
        left: Union[int, float],
        upper: Union[int, float],
        right: Union[int, float],
        lower: Union[int, float],
    ) -> Image.Image:
        """Used to get chunks of the sprite sheet."""
        bbox = tuple(map(lambda x: x * 128, (upper, left, lower, right)))
        return self._sprite_sheet.crop(bbox)

    def get(self, name: str) -> Optional[Image.Image]:
        coords = self.chunk_map.get(name)
        if coords:
            return self._get_block(*coords)


class CaveDecoSheet(AbstractDecoSheet):
    biome_name = "cave"
    chunk_map = {"kali_bg": (0, 0, 5, 4), "log_trap": (5, 1, 10, 3)}
