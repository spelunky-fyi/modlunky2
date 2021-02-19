from abc import abstractmethod
from pathlib import Path

from .base_sprite_loader import BaseSpriteLoader


class AbstractFloorStyledSheet(BaseSpriteLoader):
    @property
    @abstractmethod
    def floor_style(self) -> str:
        raise NotImplementedError

    @property
    def _sprite_sheet_path(self) -> Path:
        return Path(f"Data/Textures/floorstyled_{self.styled_name}.png")

    _chunk_size = 128
    _chunk_map = {"styled_floor": (7, 2, 8, 3)}
