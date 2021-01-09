"""
Biomes bring together the floor sheet, deco sheet, and background sprites for each
environment.
"""

from .base_classes import AbstractBiome
from .deco_sheet import *
from .floor_sheet import *

__all__ = [
    "CaveBiome",
    "VolcanaBiome",
    "JungleBiome",
    "TidePoolBiome",
    "TempleBiome",
    "IceCavesBiome",
    "BabylonBiome",
    "SunkenCityBiome",
    "EggplantBiome",
]


class CaveBiome(AbstractBiome):
    biome_name = "cave"
    display_name = "Dwelling"
    _floor_sheet_class = CaveFloorSheet
    _deco_sheet_class = CaveDecoSheet


class VolcanaBiome(AbstractBiome):
    biome_name = "volcano"
    display_name = "Volcana"
    _floor_sheet_class = VolcanaFloorSheet
    _deco_sheet_class = VolcanaDecoSheet


class JungleBiome(AbstractBiome):
    biome_name = "jungle"
    display_name = "Jungle"
    _floor_sheet_class = JungleFloorSheet
    _deco_sheet_class = JungleDecoSheet


class TidePoolBiome(AbstractBiome):
    biome_name = "tidepool"
    display_name = "Tide Pool"
    _floor_sheet_class = TidePoolFloorSheet
    _deco_sheet_class = TidePoolDecoSheet


class TempleBiome(AbstractBiome):
    biome_name = "temple"
    display_name = "Temple of Anubis"
    _floor_sheet_class = TempleFloorSheet
    _deco_sheet_class = TempleDecoSheet


class IceCavesBiome(AbstractBiome):
    biome_name = "ice"
    display_name = "Ice Caves"
    _floor_sheet_class = IceCavesFloorSheet
    _deco_sheet_class = TempleDecoSheet


class BabylonBiome(AbstractBiome):
    biome_name = "babylon"
    display_name = "Neo Babylon"
    _floor_sheet_class = BabylonFloorSheet
    _deco_sheet_class = BabylonDecoSheet


class SunkenCityBiome(AbstractBiome):
    biome_name = "sunken"
    display_name = "Sunken City"
    _floor_sheet_class = SunkenCityFloorSheet
    _deco_sheet_class = SunkenCityDecoSheet


class EggplantBiome(AbstractBiome):
    biome_name = "eggplant"
    display_name = "Eggplant World"
    _floor_sheet_class = EggplantFloorSheet
    _deco_sheet_class = EggplantDecoSheet
