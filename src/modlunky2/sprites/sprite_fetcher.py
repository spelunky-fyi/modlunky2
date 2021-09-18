from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from modlunky2.constants import BASE_DIR

from PIL import Image

from modlunky2.sprites.base_classes import (
    AbstractBiome,
    BaseSpriteLoader,
    BaseJsonSpriteLoader,
    DEFAULT_BASE_PATH,
)


class SpelunkySpriteFetcher:
    def __init__(self, base_path: Path = DEFAULT_BASE_PATH):
        self.base_path = base_path
        # Setting up universal pieces
        self._non_biome_sheets, self._non_biome_map = self._make_non_biome_map()
        # Now biome specific pieces
        self._biome_dict = self._init_biomes()
        self._biome_map = {k: v.get for k, v in self._biome_dict.items()}

    def _init_biomes(self) -> Dict[str, AbstractBiome]:
        from modlunky2.sprites import biomes

        return {
            getattr(biomes, b).biome_name: getattr(biomes, b)(self.base_path)
            for b in biomes.__all__
        }

    def _make_non_biome_map(self) -> Tuple[List[BaseSpriteLoader], Dict[str, Callable]]:
        from modlunky2.sprites import monsters
        from modlunky2.sprites.items import ItemSheet
        from modlunky2.sprites.coffins import CoffinSheet
        from modlunky2.sprites.deco_extra import DecoExtraSheet
        from modlunky2.sprites.base_eggship2 import EggShip2Sheet
        from modlunky2.sprites.hud import HudSheet
        from modlunky2.sprites.floormisc import FloorMiscSheet
        from modlunky2.sprites.tilecode_extras import TilecodeExtras

        # Gather all of the sheets in a list, these are the classes, not instances yet
        _sheets = [getattr(monsters, m) for m in monsters.__all__]
        _sheets.extend(
            [
                CoffinSheet,
                EggShip2Sheet,
                ItemSheet,
                HudSheet,
                FloorMiscSheet,
                DecoExtraSheet,
            ]
        )

        # Now making them instances
        sheets = []
        for sheet in _sheets:
            if issubclass(sheet, BaseJsonSpriteLoader):
                sheets.append(sheet(None, None, self.base_path))
            else:
                sheets.append(sheet(self.base_path))

        # This uses the constant BASE_DIR as the base path as this
        # texture is bundled with the source rather than coming
        # from the extracted assets.
        sheets.append(TilecodeExtras(BASE_DIR))

        key_map = {}
        for sheet in sheets:
            for k in sheet.key_map():
                key_map[k] = sheet.get
        return sheets, key_map

    # noinspection PyNoneFunctionAssignment
    def get(self, name: str, biome: str = "cave") -> Optional[Image.Image]:
        # we are getting the right sprite sheet with the first `(name)` then getting the
        # image with the second `(name)` maybe using partials here would be more
        # pleasing?
        img = self._non_biome_map.get(name, lambda x: None)(name)
        if not img:
            img = self._biome_map.get(biome, lambda x: None)(name)
        if not img:
            for bname, b_class in self._biome_dict.items():
                if bname != biome:
                    img = b_class.get(name)
                if img:
                    break
        return img
