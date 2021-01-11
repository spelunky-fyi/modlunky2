from enum import Enum


class BiomeEnum(Enum):
    dwelling = "cave"
    jungle = "jungle"
    volcana = "volcano"
    tide_pool = "tidepool"
    temple_of_anubis = "temple"
    ice_caves = "ice"
    neo_babylon = "babylon"
    sunken_city = "sunken"
    eggplant_world = "eggplant"
    surface = "surface"


class BossBiomeEnum(Enum):
    olmecs_lair = "????"  # maybe it doesn't count as a biome?
    abzu = "abzu"
    duat = "duat"
    city_of_gold = "?????"
    tiamats_throne = "?????"
    hunduns_hideaway = "????"
    cosmic_ocean = "cosmic"
