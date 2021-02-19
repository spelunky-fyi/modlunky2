from .base_classes import AbstractFloorSheet

__all__ = [
    "HiveStyledFloorSheet",
    "DuatStyledFloorSheet",
    "GoldStyledFloorSheet",
    "PagodaStyledFloorSheet",
    "TempleStyledFloorSheet",
    "MothershipStyledFloorSheet",
    "BabylonStyledFloorSheet",
    "SunkenCityStyledFloorSheet",
    "PalaceStyledFloorSheet",
    "StonedStyledFloorSheet",
    "WoodStyledFloorSheet",
    "VladStyledFloorSheet",
]


class HiveStyledFloorSheet(AbstractFloorSheet):
    styled_name = "beehive"


class DuatStyledFloorSheet(AbstractFloorSheet):
    styled_name = "duat"


class GoldStyledFloorSheet(AbstractFloorSheet):
    styled_name = "gold"


class GutsStyledFloorSheet(AbstractFloorSheet):
    styled_name = "guts"


class MothershipStyledFloorSheet(AbstractFloorSheet):
    styled_name = "mothership"


class PagodaStyledFloorSheet(AbstractFloorSheet):
    styled_name = "pagoda"


class BabylonStyledFloorSheet(AbstractFloorSheet):
    styled_name = "babylon"


class SunkenCityStyledFloorSheet(AbstractFloorSheet):
    styled_name = "sunken"


class PalaceStyledFloorSheet(AbstractFloorSheet):
    styled_name = "palace"


class StonedStyledFloorSheet(AbstractFloorSheet):
    styled_name = "stone"


class TempleStyledFloorSheet(AbstractFloorSheet):
    styled_name = "temple"


class VladStyledFloorSheet(AbstractFloorSheet):
    styled_name = "vlad"


class WoodStyledFloorSheet(AbstractFloorSheet):
    styled_name = "wood"
