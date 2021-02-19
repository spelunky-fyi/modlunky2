"""
Biomes bring together the floor sheet, deco sheet, and background sprites for each
environment.
"""

from .base_classes import AbstractBiome
from .deco_sheet import *
from .floor_sheet import *
from .floorstyled_sheet import *

__all__ = [
    "CaveBiome",
    "VolcanaBiome",
    "JungleBiome",
    "OlmecBiome",
    "TidePoolBiome",
    "TempleBiome",
    "GoldBiome",
    "IceCavesBiome",
    "BabylonBiome",
    "SunkenCityBiome",
    "EggplantBiome",
]


class CaveBiome(AbstractBiome):
    biome_name = "cave"
    floor_name = "cave"
    display_name = "Dwelling"
    _floor_sheet_class = CaveFloorSheet
    _floorstyled_sheet = WoodStyledFloorSheet
    _deco_sheet_class = CaveDecoSheet


class VolcanaBiome(AbstractBiome):
    biome_name = "volcano"
    floor_name = "volcano"
    display_name = "Volcana"
    _floor_sheet_class = VolcanaFloorSheet
    _floorstyled_sheet = BabylonStyledFloorSheet
    _deco_sheet_class = VolcanaDecoSheet


class JungleBiome(AbstractBiome):
    biome_name = "jungle"
    floor_name = "jungle"
    display_name = "Jungle"
    _floor_sheet_class = JungleFloorSheet
    _floorstyled_sheet = StonedStyledFloorSheet
    _deco_sheet_class = JungleDecoSheet

class OlmecBiome(AbstractBiome):
    biome_name = "jungle"
    floor_name = "jungle"
    display_name = "Stone"
    _floor_sheet_class = VolcanaFloorSheet
    _floorstyled_sheet = WoodStyledFloorSheet
    _deco_sheet_class = VolcanaDecoSheet


class TidePoolBiome(AbstractBiome):
    biome_name = "tidepool"
    floor_name = "tidepool"
    display_name = "Volcana"
    _floor_sheet_class = TidePoolFloorSheet
    _floorstyled_sheet = PagodaStyledFloorSheet
    _deco_sheet_class = TidePoolDecoSheet


class TempleBiome(AbstractBiome):
    biome_name = "temple"
    floor_name = "temple"
    display_name = "Temple of Anubis"
    _floor_sheet_class = TempleFloorSheet
    _floorstyled_sheet = TempleStyledFloorSheet
    _deco_sheet_class = TempleDecoSheet


class GoldBiome(AbstractBiome):
    biome_name = "gold"
    floor_name = "temple"
    display_name = "Temple of Anubis"
    _floor_sheet_class = TempleFloorSheet
    _floorstyled_sheet = GoldStyledFloorSheet
    _deco_sheet_class = TempleDecoSheet


class IceCavesBiome(AbstractBiome):
    biome_name = "ice"
    floor_name = "ice"
    display_name = "Ice Caves"
    _floor_sheet_class = IceCavesFloorSheet
    _floorstyled_sheet = MothershipStyledFloorSheet
    _deco_sheet_class = TempleDecoSheet

class BabylonBiome(AbstractBiome):
    biome_name = "babylon"
    floor_name = "babylon"
    display_name = "Neo Babylon"
    _floor_sheet_class = BabylonFloorSheet
    _floorstyled_sheet = BabylonStyledFloorSheet
    _deco_sheet_class = BabylonDecoSheet

class SunkenCityBiome(AbstractBiome):
    biome_name = "sunken"
    floor_name = "sunken"
    display_name = "Sunken City"
    _floor_sheet_class = SunkenCityFloorSheet
    _floorstyled_sheet = SunkenCityStyledFloorSheet
    _deco_sheet_class = SunkenCityDecoSheet

class EggplantBiome(AbstractBiome):
    biome_name = "eggplant"
    floor_name = "eggplant"
    display_name = "Eggplant World"
    _floor_sheet_class = EggplantFloorSheet
    _floorstyled_sheet = StonedStyledFloorSheet
    _deco_sheet_class = EggplantDecoSheet
