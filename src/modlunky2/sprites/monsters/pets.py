from pathlib import Path

from ..base_classes.base_sprite_loader import BaseSpriteLoader
from ..util import chunks_from_animation


class Pets(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_pets.png")
    _chunk_size = 128
    _chunk_map = {
        "monty": (0, 0, 1, 1),
        **chunks_from_animation("monty_row_0_", (0, 0, 1, 1), 12),
        **chunks_from_animation("monty_row_1_", (0, 1, 1, 2), 10),
        **chunks_from_animation("monty_row_2_", (0, 2, 1, 3), 12),
        **chunks_from_animation("monty_row_3_", (0, 3, 1, 4), 12),
        "percy": (0, 4, 1, 5),
        **chunks_from_animation("percy_row_0_", (0, 4, 1, 5), 12),
        **chunks_from_animation("percy_row_1_", (0, 5, 1, 6), 10),
        **chunks_from_animation("percy_row_2_", (0, 6, 1, 7), 12),
        **chunks_from_animation("percy_row_3_", (0, 7, 1, 8), 12),
        "poochi": (0, 8, 1, 9),
        **chunks_from_animation("poochi_row_0_", (0, 8, 1, 9), 12),
        **chunks_from_animation("poochi_row_1_", (0, 9, 1, 10), 10),
        **chunks_from_animation("poochi_row_2_", (0, 10, 1, 11), 12),
        **chunks_from_animation("poochi_row_3_", (0, 11, 1, 12), 12),
    }
