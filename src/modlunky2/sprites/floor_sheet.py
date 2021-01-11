from .base_classes import AbstractFloorSheet

__all__ = [
    "CaveFloorSheet",
    "VolcanaFloorSheet",
    "JungleFloorSheet",
    "TidePoolFloorSheet",
    "TempleFloorSheet",
    "IceCavesFloorSheet",
    "SurfaceFloorSheet",
    "SunkenCityFloorSheet",
    "BabylonFloorSheet",
    "EggplantFloorSheet",
]


class CaveFloorSheet(AbstractFloorSheet):
    biome_name = "cave"


class VolcanaFloorSheet(AbstractFloorSheet):
    biome_name = "volcano"


class JungleFloorSheet(AbstractFloorSheet):
    biome_name = "jungle"


class TidePoolFloorSheet(AbstractFloorSheet):
    biome_name = "tidepool"


class TempleFloorSheet(AbstractFloorSheet):
    biome_name = "temple"


class IceCavesFloorSheet(AbstractFloorSheet):
    biome_name = "ice"


class BabylonFloorSheet(AbstractFloorSheet):
    biome_name = "babylon"


class SunkenCityFloorSheet(AbstractFloorSheet):
    biome_name = "sunken"
    _additional_chunks = {"bigspear_trap": (8, 9, 10, 10)}


class EggplantFloorSheet(AbstractFloorSheet):
    biome_name = "eggplant"


class SurfaceFloorSheet(AbstractFloorSheet):
    biome_name = "surface"
