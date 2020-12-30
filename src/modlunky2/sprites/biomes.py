from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Type

from PIL import Image

from .deco_sheet import AbstractDecoSheet, CaveDecoSheet
from .floor_sheet import AbstractFloorSheet, CaveFloorSheet

_DEFAULT_BASE_PATH = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted"
)


class AbstractBiome(ABC):
    _image_cache: Dict[str, Image.Image]

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
        self.base_path = base_path
        self._floor_sheet = self._floor_sheet_class(base_path)
        self._deco_sheet = self._deco_sheet_class(base_path)
        self._bg = Image.open(base_path / f"Data/Textures/bg_{self.biome_name}.png")
        self._image_cache = {}

    def get(self, name: str) -> Optional[Image.Image]:
        # Basically implementing my own doofy caching so that we don't have possible
        # memory leaks with functools.lru_cache decorator
        if self._image_cache.get(name):
            return self._image_cache.get(name)
        # Try deco_sheet
        img = self._deco_sheet.get(name)
        if img:
            self._image_cache[name] = img
            return img
        # If we are still here, check the floor_sheet
        img = self._floor_sheet.get(name)
        if img:
            self._image_cache[name] = img
            return img
        # If we still haven't found anything, we got an invalid string or something went
        # wrong, we are returning none


class CaveBiome(AbstractBiome):
    biome_name = "cave"
    display_name = "The Dwelling"
    _floor_sheet_class = CaveFloorSheet
    _deco_sheet_class = CaveDecoSheet
