from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, Optional, Union, List, Type, Tuple
from random import uniform

from PIL import Image, ImageDraw, ImageFont

from .types import image_crop_tuple_whole_number
from .base_sprite_loader import BaseSpriteLoader

_DEFAULT_BASE_PATH = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted"
)


class BaseSpriteMerger(ABC):
    @property
    @abstractmethod
    def _target_sprite_sheet_path(self) -> Path:
        """
        Define the path from a "base path" to the specific png file this is for writing,
        for example for the cape it should return Path('Data/Textures/Merged/cape.png')
        """
        pass

    @property
    @abstractmethod
    def _grid_hint_size(self) -> int:
        """
        define how many pixels thick the grid hint is
        """
        pass

    @property
    @abstractmethod
    def _origin_map(self) -> Dict[Type[BaseSpriteLoader], Dict]:
        """
        Define a mapping from types that are implementations of BaseSpriteLoader
        to a dictionary that contain a chunk_size and a chunk_map
        """
        pass

    def __init__(self, base_path: Path = _DEFAULT_BASE_PATH):
        self.base_path = base_path
        self._full_path = self.base_path / self._target_sprite_sheet_path

        max_image_width = 0
        total_image_height = 0
        for origin_def in self._origin_map.values():
            origin_chunk_size = (0, 0)
            for name, coords in origin_def["chunk_map"].items():
                origin_chunk_size = (
                    max(origin_chunk_size[0], coords[2]),
                    max(origin_chunk_size[1], coords[3]),
                )
            extended_chunk_size = origin_def["chunk_size"] + 2 * self._grid_hint_size
            origin_def["image_size"] = tuple(
                image_size * extended_chunk_size for image_size in origin_chunk_size
            )
            max_image_width = max(max_image_width, origin_def["image_size"][0])
            total_image_height = total_image_height + origin_def["image_size"][1]

        image_size = (int(max_image_width), int(total_image_height))
        self._sprite_sheet = Image.new(mode="RGBA", size=image_size, color=(0, 0, 0, 0))

        image_draw = ImageDraw.Draw(self._sprite_sheet)
        guide_text = "Stay within the guides! Do not overlap the guides! "
        default_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=25)
        text_width, text_height = default_font.getsize(guide_text)
        text_height_coord = 0
        text_height_coord_start = 0
        while text_height_coord < total_image_height:
            text_width_coord = text_height_coord_start
            while text_width_coord < max_image_width:
                image_draw.text(
                    (text_width_coord, text_height_coord), guide_text, font=default_font
                )
                text_width_coord += text_width
            text_height_coord += text_height
            text_height_coord_start -= text_width / 2 + uniform(
                -text_width / 2, text_width / 2
            )

    def _get_image_coords(
        self,
        left: int,
        upper: int,
        right: int,
        lower: int,
        chunk_size: int,
        height_offset: int,
    ) -> Tuple[image_crop_tuple_whole_number, image_crop_tuple_whole_number]:

        extended_chunk_size = chunk_size + 2 * self._grid_hint_size
        bg_bbox = [left, upper, right, lower]
        bg_bbox = [coord * extended_chunk_size for coord in bg_bbox]
        bg_bbox[1] = bg_bbox[1] + height_offset
        bg_bbox[3] = bg_bbox[3] + height_offset
        bg_bbox = tuple(bg_bbox)

        chunk_dimensions = (right - left, lower - upper)
        grid_extensions_for_internal_offset = [
            chunk_dimension * self._grid_hint_size
            for chunk_dimension in chunk_dimensions
        ]
        chunk_bbox = (
            bg_bbox[0] + grid_extensions_for_internal_offset[0],
            bg_bbox[1] + grid_extensions_for_internal_offset[1],
            bg_bbox[2] - grid_extensions_for_internal_offset[0],
            bg_bbox[3] - grid_extensions_for_internal_offset[1],
        )

        return (bg_bbox, chunk_bbox)

    def _put_background(self, left: int, upper: int, right: int, lower: int):
        bg_bbox = (left, upper, right, lower)
        bg_size = (right - left, lower - upper)
        bg_color = (255, 0, 0, 255)
        bg_image = Image.new(mode="RGBA", size=bg_size, color=bg_color)
        self._sprite_sheet.paste(bg_image, bg_bbox)

    def _put_chunk(self, left: int, upper: int, right: int, lower: int, image: Image):
        bbox = (left, upper, right, lower)
        self._sprite_sheet.paste(image, bbox)

    def do_merge(self, sprite_loaders: List[BaseSpriteLoader]) -> Image:
        height_offset = 0
        for sprite_loader in sprite_loaders:
            sprite_loader_type = type(sprite_loader)
            if sprite_loader_type in self._origin_map:
                origin_def = self._origin_map[sprite_loader_type]
                chunk_size = origin_def["chunk_size"]
                for name, coords in origin_def["chunk_map"].items():
                    source_image = sprite_loader.get(name)
                    if source_image:
                        bg_coords, chunk_coords = self._get_image_coords(
                            *coords, chunk_size, height_offset
                        )
                        self._put_background(*bg_coords)
                        self._put_chunk(*chunk_coords, source_image)
                height_offset = height_offset + origin_def["image_size"][1]
        return self._sprite_sheet.copy()
