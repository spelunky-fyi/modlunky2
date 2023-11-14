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

class Biomes:
    @staticmethod
    def get_biome_for_level(lvl): # cave by default, depicts what background and sprites will be loaded
        if (
            lvl.startswith("challenge_sun")
            or lvl.startswith("sunken")
            or lvl.startswith("hundun")
            or lvl.startswith("ending_hard")
            or lvl.endswith("_sunkencity.lvl")
        ):
            return BIOME.SUNKEN_CITY
        elif (
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

    # Used for selecting a theme to get the theme code that
    # corresponds to the display-friendly theme name.
    @staticmethod
    def biome_for_name(name):
        if name == "Dwelling":
            return BIOME.DWELLING
        elif name == "Jungle":
            return BIOME.JUNGLE
        elif name == "Volcana":
            return BIOME.VOLCANA
        elif name == "Olmec":
            return BIOME.OLMEC
        elif name == "Tide Pool":
            return BIOME.TIDE_POOL
        elif name == "Temple":
            return BIOME.TEMPLE
        elif name == "Ice Caves":
            return BIOME.ICE_CAVES
        elif name == "Neo Babylon":
            return BIOME.NEO_BABYLON
        elif name == "Sunken City":
            return BIOME.SUNKEN_CITY
        elif name == "City of Gold":
            return BIOME.CITY_OF_GOLD
        elif name == "Duat":
            return BIOME.DUAT
        elif name == "Eggplant World":
            return BIOME.EGGPLANT_WORLD
        elif name == "Surface":
            return BIOME.SURFACE
        return None

    # Gets a string that can be used to display the name of a biome.
    @staticmethod
    def name_of_biome(theme):
        if theme == BIOME.DWELLING:
            return "Dwelling"
        elif theme == BIOME.TIDE_POOL:
            return "Tide Pool"
        elif theme == BIOME.NEO_BABYLON:
            return "Neo Babylon"
        elif theme == BIOME.JUNGLE:
            return "Jungle"
        elif theme == BIOME.TEMPLE:
            return "Temple"
        elif theme == BIOME.SUNKEN_CITY:
            return "Sunken City"
        elif theme == BIOME.CITY_OF_GOLD:
            return "City of Gold"
        elif theme == BIOME.DUAT:
            return "Duat"
        elif theme == BIOME.EGGPLANT_WORLD:
            return "Eggplant World"
        elif theme == BIOME.ICE_CAVES:
            return "Ice Caves"
        elif theme == BIOME.OLMEC:
            return "Olmec"
        elif theme == BIOME.VOLCANA:
            return "Volcana"
        elif theme == BIOME.SURFACE:
            return "Surface"
        return "Unknown"