from .base_classes.base_floorstyled_sheet import AbstractFloorStyledSheet

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


class HiveStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "beehive"


class DuatStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "duat"


class GoldStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "gold"


class GutsStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "guts"


class MothershipStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "mothership"


class PagodaStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "pagoda"


class BabylonStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "babylon"


class SunkenCityStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "sunken"


class PalaceStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "palace"


class StonedStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "stone"


class TempleStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "temple"


class VladStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "vlad"


class WoodStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "wood"
    _additional_chunks = {"wanted_poster": (6, 6, 8, 8),
    "shop_sign": (4, 8, 6, 10),
    "shop_door": (9, 0, 10, 1)}
