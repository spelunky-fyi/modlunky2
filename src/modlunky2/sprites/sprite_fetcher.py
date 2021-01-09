from itertools import chain
from pathlib import Path
from typing import Callable, Dict, Optional

from PIL import Image

from .base_classes import AbstractBiome, DEFAULT_BASE_PATH
from .floormisc import FloorMiscSheet
from .hud import HudSheet
from .items import ItemSheet


class SpelukySpriteFetcher:
    def __init__(self, base_path: Path = DEFAULT_BASE_PATH):
        self.base_path = base_path
        # Setting up universal pieces
        self._item_sheet = ItemSheet(self.base_path)
        self._hud_sheet = HudSheet(self.base_path)
        self._floor_misc = FloorMiscSheet(self.base_path)
        self._non_biome_map = self._make_non_biome_map()
        # Now biome specific pieces
        self._biome_dict = self._init_biomes()
        self._biome_map = {k: v.get for k, v in self._biome_dict.items()}

    def _init_biomes(self) -> Dict[str, AbstractBiome]:
        from . import biomes

        return {
            getattr(biomes, b).biome_name: getattr(biomes, b)(self.base_path)
            for b in biomes.__all__
        }

    def _make_non_biome_map(self) -> Dict[str, Callable]:
        item_key_map = self._item_sheet.key_map()
        hud_key_map = self._hud_sheet.key_map()
        floor_misc_key_map = self._floor_misc.key_map()
        # checking for key collision between item/hud/floor sheets here
        item_keys = set(item_key_map)
        hud_keys = set(hud_key_map)
        floor_misc_keys = set(floor_misc_key_map)
        if len(item_keys | hud_keys | floor_misc_keys) != len(
            list(chain(item_keys, hud_keys, floor_misc_keys))
        ):
            # TODO: Determine the key collision location
            raise KeyError(
                "Conflicting keys detected between item, hud, floor_misc keys"
            )
        non_biome_map = {}
        non_biome_map.update(item_key_map)
        non_biome_map.update(hud_key_map)
        non_biome_map.update(floor_misc_key_map)
        return non_biome_map

    def get(self, name: str, biome: str = "cave") -> Optional[Image.Image]:
        # we are getting the right sprite sheet with the first `(name)` then getting the
        # image with the second `(name)` maybe using partials here would be more
        # pleasing?
        img = self._non_biome_map.get(name, lambda x: None)(name)
        if not img:
            return self._biome_map.get(biome, lambda x: None)(name)
        else:
            return img
