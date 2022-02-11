from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from colorhash import ColorHash
from PIL import Image, ImageDraw
from ttf_opensans import opensans

from modlunky2.constants import BASE_DIR
from modlunky2.sprites.base_classes import (
    AbstractBiome,
    BaseSpriteLoader,
    BaseJsonSpriteLoader,
    DEFAULT_BASE_PATH,
)
from modlunky2.sprites.tilecode_extras import EXTRA_TILECODE_CLASSES


class SpelunkySpriteFetcher:
    def __init__(self, base_path: Path = DEFAULT_BASE_PATH):
        self.base_path = base_path
        # Setting up universal pieces
        self._non_biome_sheets, self._non_biome_map = self._make_non_biome_map()
        # Now biome specific pieces
        self._biome_dict = self._init_biomes()
        self._biome_map = {k: v.get for k, v in self._biome_dict.items()}
        self._dyn_cache = {}

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

        # These uses the constant BASE_DIR as the base path as this
        # texture is bundled with the source rather than coming
        # from the extracted assets.
        sheets.append(TilecodeExtras(BASE_DIR))
        for class_ in EXTRA_TILECODE_CLASSES:
            sheets.append(class_(BASE_DIR))

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

    def get_dyn(self, name: str) -> Image.Image:
        if name in self._dyn_cache:
            return self._dyn_cache[name]

        color = ColorHash(name)
        text_color = get_text_color(color.rgb)
        imgtxt = "\n".join(name.split("_"))

        w, h = 128, 128
        padding = 5
        img = Image.new("RGB", (w, h))
        imgdraw = ImageDraw.Draw(img)
        imgdraw.rectangle([(0, 0), (w, h)], fill=color.hex, outline=text_color)

        font_size = 1
        font = opensans(font_weight=600).imagefont(size=font_size)
        while True:
            font_size += 1
            new_font = opensans(font_weight=600).imagefont(size=font_size)
            dimensions = imgdraw.textsize(imgtxt, new_font)
            if dimensions[0] > (w - (padding * 2)) or dimensions[1] > (
                h - (padding * 2) - padding
            ):
                break
            font = new_font

        txt_dimensions = imgdraw.textsize(imgtxt, font)
        x_padding = (w - txt_dimensions[0]) / 2
        y_padding = (h - txt_dimensions[1]) / 2

        imgdraw.multiline_text(
            (x_padding, y_padding),
            imgtxt,
            font=font,
            align="center",
            fill=text_color,
        )

        self._dyn_cache[name] = img
        return img


def get_text_color(rgb):
    if (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114) > 160:
        return (0, 0, 0, 255)
    return (255, 255, 255, 255)
