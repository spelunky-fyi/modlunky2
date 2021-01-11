from abc import abstractmethod
from pathlib import Path

from PIL import Image

from .base_sprite_loader import BaseSpriteLoader


class AbstractDecoSheet(BaseSpriteLoader):
    _sprite_sheet: Image.Image
    _base_path: Path

    @property
    @abstractmethod
    def biome_name(self) -> str:
        raise NotImplementedError

    @property
    def _sprite_sheet_path(self):
        return Path(f"Data/Textures/deco_{self.biome_name}.png")
