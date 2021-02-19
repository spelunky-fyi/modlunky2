from abc import abstractmethod
from pathlib import Path

from .base_sprite_loader import BaseSpriteLoader


class AbstractFloorStyledSheet(BaseSpriteLoader):
    @property
    @abstractmethod
    def styled_name(self) -> str:
        raise NotImplementedError

    @property
    def _sprite_sheet_path(self) -> Path:
        return Path(f"Data/Textures/floorstyled_{self.styled_name}.png")

    _chunk_size = 128
    _chunk_map = {"styled_floor": (7, 2, 8, 3),
    "duat_floor": (7, 2, 8, 3),
    "palace_floor": (7, 2, 8, 3),
    "temple_floor": (7, 2, 8, 3),
    "guts_floor": (7, 2, 8, 3),
    "sunken_floor": (7, 2, 8, 3),
    "minewood_floor": (7, 2, 8, 3),
    "stone_floor": (7, 2, 8, 3),
    "vlad_floor": (7, 2, 8, 3),
    "pagoda_floor": (7, 2, 8, 3),
    "babylon_floor": (7, 2, 8, 3),
    "beehive_floor": (7, 2, 8, 3),
    "cog_floor": (7, 2, 8, 3),
    "mothership_floor": (7, 2, 8, 3)}
