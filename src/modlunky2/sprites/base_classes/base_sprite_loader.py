from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, Optional, Union

from PIL import Image

from .types import chunk_map_type

_DEFAULT_BASE_PATH = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted"
)

_CACHED_NONE_SENTINEL = object()


def _cache_img_not_class(f):
    """using this because functools.lrucache will keep the class object from getting
    GCed if you are using it on a method"""

    # noinspection PyProtectedMember
    @wraps(f)
    def cache_img(slf, name: str):
        img = slf._cache_dict.get(name)
        if not img:
            img = f(slf, name) or _CACHED_NONE_SENTINEL
            slf._cache_dict[name] = img
        if img is _CACHED_NONE_SENTINEL:
            return None
        return img

    return cache_img


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

    def __init__(self, base_path: Path = _DEFAULT_BASE_PATH):
        self.base_path = base_path
        self._sprite_sheet = Image.open(self.base_path / self._sprite_sheet_path)
        # This is to support the caching decorator and let it use storage on this class
        # otherwise we get doofy global dicts for caching
        self._cache_dict = {}

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

    @_cache_img_not_class
    def get(self, name: str) -> Optional[Image.Image]:
        coords = self._chunk_map.get(name)
        if coords:
            return self._get_block(*coords)

    def key_map(self) -> Dict[str, Callable]:
        return {k: self.get for k in self._chunk_map}
