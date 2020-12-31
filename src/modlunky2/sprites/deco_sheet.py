from .base_classes.base_deco_sheet import AbstractDecoSheet


class CaveDecoSheet(AbstractDecoSheet):
    biome_name = "cave"
    _chunk_size = 128
    _chunk_map = {"kali_bg": (0, 0, 4, 5), "log_trap": (1, 5, 3, 10)}
