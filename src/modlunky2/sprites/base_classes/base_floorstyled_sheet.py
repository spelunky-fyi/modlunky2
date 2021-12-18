from abc import abstractmethod
from pathlib import Path

from modlunky2.sprites.base_classes.base_sprite_loader import BaseSpriteLoader


class AbstractFloorStyledSheet(BaseSpriteLoader):
    @property
    @abstractmethod
    def styled_name(self) -> str:
        raise NotImplementedError

    @property
    def _sprite_sheet_path(self) -> Path:
        return Path(f"Data/Textures/floorstyled_{self.styled_name}.png")

    _chunk_size = 128
    _chunk_map = {
        "styled_floor": (7, 2, 8, 3),
    }
    _additional_chunks = {}

    def __init__(self, base_path: Path):
        super().__init__(base_path=base_path)
        # Adding additional chunks that are defined in subclasses to the chunk map
        new_map = self._chunk_map.copy()
        new_map.update(self._additional_chunks)
        self._chunk_map = new_map
