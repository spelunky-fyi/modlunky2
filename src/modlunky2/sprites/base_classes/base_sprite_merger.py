from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, Optional, Union, List, Type, Tuple
from random import uniform
from os import makedirs

from PIL import Image, ImageDraw, ImageFont

from .types import image_crop_tuple_whole_number
from .base_sprite_loader import BaseSpriteLoader

_DEFAULT_BASE_PATH = Path(
    r"D:\Program Files (x86)\SteamLibrary\steamapps\common\Spelunky 2\Mods\Extracted"
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

    def __init__(
        self, base_path: Path = _DEFAULT_BASE_PATH, separate_grid_file: bool = True
    ):
        self.base_path = base_path
        self._full_path = self.base_path / self._target_sprite_sheet_path
        self._separate_grid_file = separate_grid_file
        self._grid_colors = [(255, 0, 0, 255), (0, 0, 255, 255)]
        self._grid_colors_idx = 0

        max_image_width = 0
        total_image_height = 0
        for origin_def in self._origin_map.values():
            origin_chunk_size = (0, 0)
            for _, coords in origin_def["chunk_map"].items():
                origin_chunk_size = (
                    max(origin_chunk_size[0], coords[2]),
                    max(origin_chunk_size[1], coords[3]),
                )
            real_chunk_size = self._get_real_chunk_size(origin_def["chunk_size"])
            origin_def["image_size"] = tuple(
                image_size * real_chunk_size for image_size in origin_chunk_size
            )
            max_image_width = max(max_image_width, origin_def["image_size"][0])
            total_image_height = total_image_height + origin_def["image_size"][1]

        image_size = (int(max_image_width), int(total_image_height))
        self._sprite_sheet = Image.new(mode="RGBA", size=image_size, color=(0, 0, 0, 0))

        if self._separate_grid_file:
            self._grid_image = Image.new(
                mode="RGBA", size=image_size, color=(0, 0, 0, 0)
            )
        else:
            self._grid_image = self._sprite_sheet
        self._grid_image_draw = ImageDraw.Draw(self._grid_image)

        def draw_text_hint(text_hint: str):
            default_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=25)
            lines = text_hint.splitlines()
            current_height = 0
            for line in lines:
                line_width, line_height = default_font.getsize(line)
                current_height = current_height + line_height
                self._grid_image_draw.text(
                    (image_size[0] - line_width, image_size[1] - current_height),
                    line,
                    font=default_font,
                )

        if self._separate_grid_file:
            draw_text_hint("Stay within the guides!")
        else:
            draw_text_hint("Stay within the guides!\nDo not overlap the guides!")

    def _get_real_chunk_size(self, chunk_size: int) -> int:
        if self._separate_grid_file:
            return chunk_size
        return chunk_size + 2 * self._grid_hint_size

    def _get_image_coords(
        self,
        left: int,
        upper: int,
        right: int,
        lower: int,
        chunk_size: int,
        height_offset: int,
    ) -> Tuple[image_crop_tuple_whole_number, image_crop_tuple_whole_number]:
        if self._separate_grid_file:
            bbox = (left, upper, right, lower)
            bbox = tuple(x * self._get_real_chunk_size(chunk_size) for x in bbox)
            bbox = (bbox[0], bbox[1] + height_offset, bbox[2], bbox[3] + height_offset)
            return bbox, bbox

        real_chunk_size = self._get_real_chunk_size(chunk_size)
        grid_bbox = [left, upper, right, lower]
        grid_bbox = [coord * real_chunk_size for coord in grid_bbox]
        grid_bbox[1] = grid_bbox[1] + height_offset
        grid_bbox[3] = grid_bbox[3] + height_offset
        grid_bbox = tuple(grid_bbox)

        chunk_dimensions = (right - left, lower - upper)
        grid_extensions_for_internal_offset = [
            chunk_dimension * self._grid_hint_size
            for chunk_dimension in chunk_dimensions
        ]
        chunk_bbox = (
            grid_bbox[0] + grid_extensions_for_internal_offset[0],
            grid_bbox[1] + grid_extensions_for_internal_offset[1],
            grid_bbox[2] - grid_extensions_for_internal_offset[0],
            grid_bbox[3] - grid_extensions_for_internal_offset[1],
        )

        return (grid_bbox, chunk_bbox)

    def _put_grid(self, left: int, upper: int, right: int, lower: int):
        grid_bbox = (left, upper, right, lower)
        grid_color = self._grid_colors[self._grid_colors_idx]
        self._grid_colors_idx = 1 if self._grid_colors_idx == 0 else 0
        self._grid_image_draw.rectangle(
            grid_bbox, outline=grid_color, width=self._grid_hint_size
        )

    def _put_chunk(self, left: int, upper: int, right: int, lower: int, image: Image):
        bbox = (left, upper, right, lower)
        self._sprite_sheet.paste(image, bbox)

    def do_merge(self, sprite_loaders: List[BaseSpriteLoader]) -> Image:
        height_offset = 0
        for sprite_loader_type, origin_def in self._origin_map.items():
            matching_sprite_loaders = [
                x for x in sprite_loaders if isinstance(x, sprite_loader_type)
            ]
            if matching_sprite_loaders:
                sprite_loader = matching_sprite_loaders[0]
                chunk_size = origin_def["chunk_size"]
                for name, coords in origin_def["chunk_map"].items():
                    source_image = sprite_loader.get(name)
                    if source_image:
                        grid_coords, chunk_coords = self._get_image_coords(
                            *coords, chunk_size, height_offset
                        )
                        self._put_grid(*grid_coords)
                        self._put_chunk(*chunk_coords, source_image)
            height_offset = height_offset + origin_def["image_size"][1]
        return self._sprite_sheet

    def save(self):
        if not self._target_sprite_sheet_path.parent.exists():
            makedirs(self._target_sprite_sheet_path.parent)
        self._sprite_sheet.save(self._target_sprite_sheet_path)
        if self._separate_grid_file:
            grid_file_path = f"{self._target_sprite_sheet_path.with_suffix('')}_grid{self._target_sprite_sheet_path.suffix}"
            self._grid_image.save(grid_file_path)
