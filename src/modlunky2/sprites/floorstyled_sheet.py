from modlunky2.sprites.base_classes.base_floorstyled_sheet import (
    AbstractFloorStyledSheet,
)

__all__ = [
    "HiveStyledFloorSheet",
    "DuatStyledFloorSheet",
    "GoldStyledFloorSheet",
    "GutsStyledFloorSheet",
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
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "beehive_floor": (7, 2, 8, 3),
    }


class DuatStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "duat"
    _additional_chunks = {
        "duat_floor": (1, 3, 2, 4),
        "altar_duat": (8, 1, 10, 2),
        "push_block": (7, 2, 8, 3),
    }


class GoldStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "gold"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "cog_floor": (1, 3, 2, 4),
        "slidingwall_ceiling": (5, 8, 6, 10),
        "slidingwall_switch": (6, 8, 7, 9),
        "gold_crushtraplarge": (6, 0, 8, 2),
        "push_block": (7, 2, 8, 3),
    }


class GutsStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "guts"
    _additional_chunks = {
        "guts_floor": (7, 2, 8, 3),
    }


class MothershipStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "mothership"
    _additional_chunks = {
        "mothership_floor": (7, 2, 8, 3),
    }


class PagodaStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "pagoda"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "pagoda_floor": (7, 2, 8, 3),
        "slidingwall_ceiling": (5, 8, 6, 10),
        "slidingwall": (5, 8, 6, 10),
        "slidingwall_switch": (6, 8, 7, 9),
    }


class BabylonStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "babylon"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "babylon_floor": (7, 2, 8, 3),
    }


class SunkenCityStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "sunken"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "sunken_floor": (7, 2, 8, 3),
    }


class PalaceStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "palace"
    _additional_chunks = {
        "palace_floor": (7, 2, 8, 3),
        "palace_entrance": (8, 6, 10, 8),
        "palace_table": (7, 1, 10, 2),
        "palace_table_tray": (8, 0, 9, 1),
        "palace_chandelier": (4, 8, 7, 10),
        "palace_candle": (7, 0, 8, 1),
        "palace_bookcase": (8, 2, 9, 3),
    }


class StonedStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "stone"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "stone_floor": (7, 2, 8, 3),
    }


class TempleStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "temple"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "temple_floor": (1, 3, 2, 4),
        "push_block": (7, 2, 8, 3),
    }


class VladStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "vlad"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "crown_statue": (8, 0, 10, 3),
        "vlad_floor": (7, 2, 8, 3),
    }


class WoodStyledFloorSheet(AbstractFloorStyledSheet):
    styled_name = "wood"
    _additional_chunks = {
        "door2": (8, 6, 10, 8),
        "door_drop_held": (8, 6, 10, 8),
        "minewood_floor": (7, 2, 8, 3),
        "wanted_poster": (6, 6, 8, 8),
        "shop_sign": (4, 8, 6, 10),
        "shop_door": (9, 0, 10, 1),
    }
