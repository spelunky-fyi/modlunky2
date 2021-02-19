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
    _additional_chunks = {"bush_block": (10, 2, 11, 3),
    "ladder": (4, 1, 5, 2),
    "ladder_plat": (4, 2, 5, 3),
    "bone_block": (10, 2, 11, 3),
    "idol_floor": (10, 0, 11, 1)}


class VolcanaFloorSheet(AbstractFloorSheet):
    biome_name = "volcano"
    _additional_chunks = {"icefloor": (7, 1, 8, 2),
    "conveyorbelt_right": (8, 10, 9, 11),
    "conveyorbelt_left": (8, 11, 9, 12),
    "falling_platform": (4, 5, 5, 6)}


class JungleFloorSheet(AbstractFloorSheet):
    biome_name = "jungle"
    _additional_chunks = {"vine": (4, 1, 5, 2),
    "growable_vine": (4, 2, 5, 3),
    "tree_base": (3, 11, 4, 12)}


class TidePoolFloorSheet(AbstractFloorSheet):
    biome_name = "tidepool"
    _additional_chunks = {"climbing_pole": (4, 1, 5, 2),
    "growable_climbing_pole": (4, 0, 5, 1)}


class TempleFloorSheet(AbstractFloorSheet):
    biome_name = "temple"


class IceCavesFloorSheet(AbstractFloorSheet):
    biome_name = "ice"
    _additional_chunks = {"icefloor": (7, 1, 8, 2),
    "thinice": (3, 11, 4, 12),
    "upsidedown_spikes": (8, 9, 9, 10),
    "falling_platform": (4, 5, 5, 6),
    "eggplant_altar": (10, 2, 11, 3)}


class BabylonFloorSheet(AbstractFloorSheet):
    biome_name = "babylon"


class SunkenCityFloorSheet(AbstractFloorSheet):
    biome_name = "sunken"
    _additional_chunks = {"bigspear_trap": (8, 9, 10, 10)}


class EggplantFloorSheet(AbstractFloorSheet):
    biome_name = "eggplant"


class SurfaceFloorSheet(AbstractFloorSheet):
    biome_name = "surface"
