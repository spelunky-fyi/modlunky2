"""
Biomes bring together the floor sheet, deco sheet, and background sprites for each
environment.
"""

from .base_classes import AbstractBiome
from .deco_sheet import *
from .floor_sheet import *
from .floorstyled_sheet import *

__all__ = [
    "SurfaceBiome",
    "CaveBiome",
    "VolcanaBiome",
    "JungleBiome",
    "OlmecBiome",
    "TidePoolBiome",
    "TempleBiome",
    "DuatBiome",
    "GoldBiome",
    "BeeBiome",
    "IceCavesBiome",
    "BabylonBiome",
    "PalaceBiome",
    "SunkenCityBiome",
    "GutsBiome",
    "EggplantBiome",
]

class SurfaceBiome(AbstractBiome):
    biome_name = "surface"
    floor_name = "surface"
    display_name = "Surface"
    _floor_sheet_class = SurfaceFloorSheet
    _floorstyled_sheet_class = WoodStyledFloorSheet
    _deco_sheet_class = SurfaceDecoSheet

class CaveBiome(AbstractBiome):
    biome_name = "cave"
    floor_name = "cave"
    display_name = "Dwelling"
    _floor_sheet_class = CaveFloorSheet
    _floorstyled_sheet_class = WoodStyledFloorSheet
    _deco_sheet_class = CaveDecoSheet

class VolcanaBiome(AbstractBiome):
    biome_name = "volcano"
    floor_name = "volcano"
    display_name = "Volcana"
    _floor_sheet_class = VolcanaFloorSheet
    _floorstyled_sheet_class = VladStyledFloorSheet
    _deco_sheet_class = VolcanaDecoSheet

class JungleBiome(AbstractBiome):
    biome_name = "jungle"
    floor_name = "jungle"
    display_name = "Jungle"
    _floor_sheet_class = JungleFloorSheet
    _floorstyled_sheet_class = StonedStyledFloorSheet
    _deco_sheet_class = JungleDecoSheet

class OlmecBiome(AbstractBiome):
    biome_name = "olmec"
    floor_name = "jungle"
    display_name = "Stone"
    _floor_sheet_class = JungleFloorSheet
    _floorstyled_sheet_class = StonedStyledFloorSheet
    _deco_sheet_class = JungleDecoSheet

class TidePoolBiome(AbstractBiome):
    biome_name = "tidepool"
    floor_name = "tidepool"
    display_name = "Volcana"
    _floor_sheet_class = TidePoolFloorSheet
    _floorstyled_sheet_class = PagodaStyledFloorSheet
    _deco_sheet_class = TidePoolDecoSheet

class TempleBiome(AbstractBiome):
    biome_name = "temple"
    floor_name = "temple"
    display_name = "Temple of Anubis"
    _floor_sheet_class = TempleFloorSheet
    _floorstyled_sheet_class = TempleStyledFloorSheet
    _deco_sheet_class = TempleDecoSheet

class DuatBiome(AbstractBiome):
    biome_name = "duat"
    floor_name = "duat"
    display_name = "Duat"
    _floor_sheet_class = TempleFloorSheet
    _floorstyled_sheet_class = DuatStyledFloorSheet
    _deco_sheet_class = TempleDecoSheet

class GoldBiome(AbstractBiome):
    biome_name = "gold"
    floor_name = "temple"
    display_name = "Temple of Anubis"
    _floor_sheet_class = TempleFloorSheet
    _floorstyled_sheet_class = GoldStyledFloorSheet
    _deco_sheet_class = TempleDecoSheet

class BeeBiome(AbstractBiome):
    biome_name = "beehive"
    floor_name = "beehive"
    display_name = "Bee Hive"
    _floor_sheet_class = JungleFloorSheet
    _floorstyled_sheet_class = HiveStyledFloorSheet
    _deco_sheet_class = JungleDecoSheet

class IceCavesBiome(AbstractBiome):
    biome_name = "ice"
    floor_name = "ice"
    display_name = "Ice Caves"
    _floor_sheet_class = IceCavesFloorSheet
    _floorstyled_sheet_class = MothershipStyledFloorSheet
    _deco_sheet_class = IceCavesDecoSheet

class BabylonBiome(AbstractBiome):
    biome_name = "babylon"
    floor_name = "babylon"
    display_name = "Neo Babylon"
    _floor_sheet_class = BabylonFloorSheet
    _floorstyled_sheet_class = BabylonStyledFloorSheet
    _deco_sheet_class = BabylonDecoSheet

class PalaceBiome(AbstractBiome):
    biome_name = "palace"
    floor_name = "palace"
    display_name = "Palace"
    _floor_sheet_class = BabylonFloorSheet
    _floorstyled_sheet_class = PalaceStyledFloorSheet
    _deco_sheet_class = BabylonDecoSheet

class SunkenCityBiome(AbstractBiome):
    biome_name = "sunken"
    floor_name = "sunken"
    display_name = "Sunken City"
    _floor_sheet_class = SunkenCityFloorSheet
    _floorstyled_sheet_class = SunkenCityStyledFloorSheet
    _deco_sheet_class = SunkenCityDecoSheet

class GutsBiome(AbstractBiome):
    biome_name = "guts"
    floor_name = "guts"
    display_name = "Guts"
    _floor_sheet_class = SunkenCityFloorSheet
    _floorstyled_sheet_class = GutsStyledFloorSheet
    _deco_sheet_class = SunkenCityDecoSheet

class EggplantBiome(AbstractBiome):
    biome_name = "eggplant"
    floor_name = "eggplant"
    display_name = "Eggplant World"
    _floor_sheet_class = EggplantFloorSheet
    _floorstyled_sheet_class = StonedStyledFloorSheet
    _deco_sheet_class = EggplantDecoSheet
