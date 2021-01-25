from pathlib import Path

from ..base_classes.base_sprite_loader import BaseSpriteLoader
from ..util import chunks_from_animation


class Mounts(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/mounts.png")
    _chunk_size = 128
    _chunk_map = {
        "turkey": (0, 0, 1, 1),
        **chunks_from_animation("turkey_row_0_", (0, 0, 1, 1), 14),
        **chunks_from_animation("turkey_row_1_", (0, 1, 1, 2), 16),
        **chunks_from_animation("turkey_row_2_", (0, 2, 1, 3), 16),
        **chunks_from_animation("turkey_row_3_", (0, 3, 1, 4), 14),
        "rockdog": (0, 4, 1, 5),
        **chunks_from_animation("rockdog_row_0_", (0, 4, 1, 5), 14),
        **chunks_from_animation("rockdog_row_1_", (0, 5, 1, 6), 12),
        **chunks_from_animation("rockdog_row_2_", (0, 6, 1, 7), 15),
        **chunks_from_animation("rockdog_row_3_", (0, 7, 1, 8), 14),
        "axolotl": (0, 8, 1, 9),
        **chunks_from_animation("axolotl_row_0_", (0, 8, 1, 9), 14),
        **chunks_from_animation("axolotl_row_1_", (0, 9, 1, 10), 12),
        **chunks_from_animation("axolotl_row_2_", (0, 10, 1, 11), 15),
        **chunks_from_animation("axolotl_row_3_", (0, 11, 1, 12), 14),
        "qilin": (0, 12, 1, 13),
        **chunks_from_animation("qilin_row_0_", (0, 12, 1, 13), 14),
        **chunks_from_animation("qilin_row_1_", (0, 13, 1, 14), 12),
        **chunks_from_animation("qilin_row_2_", (0, 14, 1, 15), 15),
        **chunks_from_animation("qilin_row_3_", (0, 15, 1, 16), 14),
    }
