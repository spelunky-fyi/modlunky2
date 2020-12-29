from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image


class AbstractDecoSheet(ABC):
    _sprite_sheet: Image.Image
    _base_path: Path

    def __init__(self, base_path: Path):
        self._base_path = base_path
        self._sprite_sheet = Image.open(self._base_path / self._sheet_path)

    @property
    @abstractmethod
    def biome_name(self) -> str:
        raise NotImplementedError

    @property
    def _sheet_path(self):
        return Path(f"Data/Textures/floor_{self.biome_name}.png")


class CaveDecoSheet(AbstractDecoSheet):
    biome_name = "cave"
