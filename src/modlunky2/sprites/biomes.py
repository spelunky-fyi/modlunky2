from .base_classes import AbstractBiome
from .deco_sheet import CaveDecoSheet
from .floor_sheet import CaveFloorSheet


class CaveBiome(AbstractBiome):
    biome_name = "cave"
    display_name = "The Dwelling"
    _floor_sheet_class = CaveFloorSheet
    _deco_sheet_class = CaveDecoSheet
