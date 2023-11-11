class BIOME():
    DWELLING = "cave"
    JUNGLE = "jungle"
    VOLCANA = "volcano"
    OLMEC = "olmec"
    TEMPLE = "temple"
    TIDE_POOL = "tidepool"
    ICE_CAVES = "ice"
    NEO_BABYLON = "babylon"
    SUNKEN_CITY = "sunken"
    BEEHIVE = "beehive"
    CITY_OF_GOLD = "gold"
    DUAT = "duat"
    EGGPLANT_WORLD = "eggplant"
    SURFACE = "surface"

class Biomes():
    @staticmethod
    def get_biome_for_level(lvl): # cave by default, depicts what background and sprites will be loaded
        if (
            lvl.startswith("abzu.lvl")
            or lvl.startswith("lake")
            or lvl.startswith("tide")
            or lvl.startswith("end")
            or lvl.endswith("_tidepool.lvl")
        ):
            return BIOME.TIDE_POOL
        elif (
            lvl.startswith("babylon")
            or lvl.startswith("hallofu")
            or lvl.endswith("_babylon.lvl")
            or lvl.startswith("palace")
            or lvl.startswith("tiamat")
        ):
            return BIOME.NEO_BABYLON
        elif lvl.startswith("basecamp"):
            return BIOME.DWELLING
        elif lvl.startswith("beehive"):
            return BIOME.BEEHIVE
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("jungle")
            or lvl.startswith("challenge_moon")
            or lvl.endswith("_jungle.lvl")
        ):
            return BIOME.JUNGLE
        elif (
            lvl.startswith("challenge_star")
            or lvl.startswith("temple")
            or lvl.endswith("_temple.lvl")
        ):
            return BIOME.TEMPLE
        elif (
            lvl.startswith("challenge_sun")
            or lvl.startswith("sunken")
            or lvl.startswith("hundun")
            or lvl.startswith("ending_hard")
            or lvl.endswith("_sunkencity.lvl")
        ):
            return BIOME.SUNKEN_CITY
        elif lvl.startswith("city"):
            return BIOME.CITY_OF_GOLD
        elif lvl.startswith("duat"):
            return BIOME.DUAT
        elif lvl.startswith("egg"):
            return BIOME.EGGPLANT_WORLD
        elif lvl.startswith("ice") or lvl.endswith("_icecavesarea.lvl"):
            return BIOME.ICE_CAVES
        elif lvl.startswith("olmec"):
            return BIOME.JUNGLE
        elif lvl.startswith("vlad"):
            return BIOME.VOLCANA
        elif lvl.startswith("volcano") or lvl.endswith("_volcano.lvl"):
            return BIOME.VOLCANA
        return BIOME.DWELLING
