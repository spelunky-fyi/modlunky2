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
    _chunk_map = {}


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
    _chunk_map = {}


class BabylonDecoSheet(AbstractDecoSheet):
    biome_name = "babylon"
    _chunk_size = 128
    _chunk_map = {}


class SunkenCityDecoSheet(AbstractDecoSheet):
    biome_name = "sunken"
    _chunk_size = 128
    _chunk_map = {}


class EggplantDecoSheet(AbstractDecoSheet):
    biome_name = "eggplant"
    _chunk_size = 128
    _chunk_map = {}


class SurfaceDecoSheet(AbstractDecoSheet):
    biome_name = "surface"
    _chunk_size = 128
    _chunk_map = {}
