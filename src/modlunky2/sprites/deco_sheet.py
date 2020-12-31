from abc import abstractmethod
from pathlib import Path
from typing import Union

from PIL import Image

from .base_sprite_loader import BaseSpriteLoader

number = Union[float, int]


class AbstractDecoSheet(BaseSpriteLoader):
    _sprite_sheet: Image.Image
    _base_path: Path

    @property
    @abstractmethod
    def biome_name(self) -> str:
        raise NotImplementedError

    @property
    def _sprite_sheet_path(self):
        return Path(f"Data/Textures/deco_{self.biome_name}.png")


class CaveDecoSheet(AbstractDecoSheet):
    biome_name = "cave"
    _chunk_size = 128
    _chunk_map = {"kali_bg": (0, 0, 4, 5), "log_trap": (1, 5, 3, 10)}
