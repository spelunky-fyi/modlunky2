from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Type

from PIL import Image

from .deco_sheet import AbstractDecoSheet, CaveDecoSheet
from .floor_sheet import AbstractFloorSheet, CaveFloorSheet

_DEFAULT_BASE_PATH = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted"
)


class AbstractBiome(ABC):
    @property
    @abstractmethod
    def biome_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def _floor_sheet_class(self) -> Type[AbstractFloorSheet]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _deco_sheet_class(self) -> Type[AbstractDecoSheet]:
        raise NotImplementedError

    @property
    def bg(self) -> Image.Image:
        return self._bg

    def __init__(self, base_path: Path = _DEFAULT_BASE_PATH):
        self._floor_sheet = self._floor_sheet_class(base_path)
        self._deco_sheet = self._deco_sheet_class(base_path)
        self._bg = Image.open(base_path / f"Data/Textures/bg_{self.biome_name}.png")

    def get(self, key: str) -> Optional[Image.Image]:
        if key in self._deco_sheet.chunk_map.keys():
            return self._deco_sheet.get(key)
        else:
            return self._floor_sheet.get(key)


class CaveBiome(AbstractBiome):
    biome_name = "cave"
    display_name = "The Dwelling"
    _floor_sheet_class = CaveFloorSheet
    _deco_sheet_class = CaveDecoSheet
