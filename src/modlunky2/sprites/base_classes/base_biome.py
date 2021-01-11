from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Type

from PIL import Image

from .base_deco_sheet import AbstractDecoSheet
from .base_floor_sheet import AbstractFloorSheet

DEFAULT_BASE_PATH = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted"
)


class AbstractBiome(ABC):
    """Brings together the decoration sheet, floor sheet, and background for a _biome.
    Subclassed by overriding the abstracted methods with static class variables.

    Main apis are the `bg` method which returns the background image, and `get` which
    searches the two subclasses to see if it exists."""

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

    def __init__(self, base_path: Path = DEFAULT_BASE_PATH):
        self.base_path = base_path
        self._floor_sheet = self._floor_sheet_class(base_path)
        self._deco_sheet = self._deco_sheet_class(base_path)
        self._bg = Image.open(base_path / f"Data/Textures/bg_{self.biome_name}.png")
        self._image_cache = {}
        self._sheet_map = self._make_sheet_map()

    # noinspection PyProtectedMember
    def _make_sheet_map(self) -> Dict:
        """
        Ensures the two subclasses don't overlap their key names, and builds a mapping
        so we know already where each key is and which class to ask for a key
        :return:
        """
        floor_keys = set(self._floor_sheet._chunk_map.keys())
        deco_keys = set(self._deco_sheet._chunk_map.keys())
        same_keys = floor_keys & deco_keys
        # Evals to false if nothing in the set
        if same_keys:
            raise KeyError(
                f"floor sheet and decoration sheet have colliding names: {same_keys}"
            )
        sheet_map = {
            k: self._floor_sheet.get for k in self._floor_sheet._chunk_map.keys()
        }
        for k in self._deco_sheet._chunk_map.keys():
            sheet_map[k] = self._deco_sheet.get
        return sheet_map

    def get(self, name: str) -> Optional[Image.Image]:
        # shortcut to check if we actually have this key available to us and bail out
        # early if we don't
        get_func = self._sheet_map.get(name)
        if get_func is None:
            return
        # this will either be the `get` method of the floor or deco sheet object
        return get_func(name)
