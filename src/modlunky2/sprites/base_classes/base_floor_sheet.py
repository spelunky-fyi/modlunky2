from abc import abstractmethod
from pathlib import Path

from modlunky2.sprites.base_classes.base_sprite_loader import BaseSpriteLoader


class AbstractFloorSheet(BaseSpriteLoader):
    @property
    @abstractmethod
    def biome_name(self) -> str:
        raise NotImplementedError

    @property
    def _sprite_sheet_path(self) -> Path:
        return Path(f"Data/Textures/floor_{self.biome_name}.png")

    """
    Biome sheets are 12x12 128 pixel squares
    """
    _chunk_size = 128
    _chunk_map = {
        "push_block": (7, 0, 8, 1),
        "entrance": (0.5, 7, 3, 9),
        "entrance_shortcut": (0.5, 7, 3, 9),
        "door": (0.5, 7, 3, 9),
        # Exit is not on even 128 pixel boundaries RIP even numbers
        "exit": (0.5, 9.5, 3, 11.5),
        "door2": (8, 6, 10, 8),
        # door2_secret is the same as door2, but gets dirt/push_block in front
        "door2_secret": (8, 6, 10, 8),
        "spikes": (5, 9, 6, 10),
        "dirt": (0, 0, 4, 7),
        "floor": (0, 0, 1, 1),
    }
    _additional_chunks = {}

    def __init__(self, base_path: Path):
        super().__init__(base_path=base_path)
        # Adding additional chunks that are defined in subclasses to the chunk map
        new_map = self._chunk_map.copy()
        new_map.update(self._additional_chunks)
        self._chunk_map = new_map
