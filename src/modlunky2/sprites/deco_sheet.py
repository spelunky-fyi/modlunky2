from .base_classes.base_deco_sheet import AbstractDecoSheet

__all__ = [
    "CaveDecoSheet",
    "VolcanaDecoSheet",
    "JungleDecoSheet",
    "TidePoolDecoSheet",
    "TempleDecoSheet",
    "IceCavesDecoSheet",
    "BabylonDecoSheet",
    "SunkenCityDecoSheet",
    "EggplantDecoSheet",
    "SurfaceDecoSheet",
]


class CaveDecoSheet(AbstractDecoSheet):
    biome_name = "cave"
    _chunk_size = 128
    _chunk_map = {"kali_bg": (0, 0, 4, 5), "woodenlog_trap": (1, 5, 3, 10)}


class VolcanaDecoSheet(AbstractDecoSheet):
    biome_name = "volcano"
    _chunk_size = 128
    _chunk_map = {
        "kali_bg": (0, 0, 4, 5),
        "drill": (1, 5, 3, 8),
        "vlad_banner": (1, 8, 3, 12),
    }


class JungleDecoSheet(AbstractDecoSheet):
    biome_name = "jungle"
    _chunk_size = 128
    _chunk_map = {"stone_door": (0, 5, 3, 7)}


class TidePoolDecoSheet(AbstractDecoSheet):
    biome_name = "tidepool"
    _chunk_size = 128
    _chunk_map = {}


class TempleDecoSheet(AbstractDecoSheet):
    biome_name = "temple"
    _chunk_size = 128
    _chunk_map = {}


class IceCavesDecoSheet(AbstractDecoSheet):
    biome_name = "ice"
    _chunk_size = 128
    _chunk_map = {
        "moai_statue": (0, 7, 4, 12),
    }


class BabylonDecoSheet(AbstractDecoSheet):
    biome_name = "babylon"
    _chunk_size = 128
    _chunk_map = {}


class SunkenCityDecoSheet(AbstractDecoSheet):
    biome_name = "sunken"
    _chunk_size = 128
    _chunk_map = {
        "mother_statue": (0, 5, 2, 11),
    }


class EggplantDecoSheet(AbstractDecoSheet):
    biome_name = "eggplant"
    _chunk_size = 128
    _chunk_map = {}


class SurfaceDecoSheet(AbstractDecoSheet):
    biome_name = "basecamp"
    _chunk_size = 128
    _chunk_map = {
        "construction_sign": (5, 12, 6, 13),
        "boombox": (5, 14, 6, 15),
        "tutorial_speedrun_sign": (7, 14, 8, 15),
        "tutorial_menu_sign": (7, 14, 8, 15),
        "singlebed": (0, 15, 1, 16),
        "dresser": (2, 14, 3, 15),
        "bunkbed": (0, 13, 2, 15),
        "diningtable": (14, 10, 16, 11),
        "sidetable": (9, 12, 10, 13),
        "chair_looking_left": (3, 15, 4, 16),
        "chair_looking_right": (3, 15, 4, 16),
        "couch": (6, 15, 8, 16),
        "tv": (8, 15, 9, 16),
        "dog_sign": (12, 10, 14, 12),
        "shortcut_station_banner": (10, 8, 12, 12),
        "telescope": (12, 8, 14, 10),
    }
