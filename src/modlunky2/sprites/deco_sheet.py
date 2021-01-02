from pathlib import Path

from .base_classes.base_deco_sheet import AbstractDecoSheet


class CaveDecoSheet(AbstractDecoSheet):
    biome_name = "cave"
    _chunk_size = 128
    _chunk_map = {"kali_bg": (0, 0, 4, 5), "log_trap": (1, 5, 3, 10)}


class VolcanaDecoSheet(AbstractDecoSheet):
    biome_name = "volcano"
    _chunk_size = 128
    _chunk_map = {
        "kali_bg": (0, 0, 4, 5),
        "drill": (1, 5, 3, 8),
        "vlad_banner": (1, 8, 3, 12),
    }
