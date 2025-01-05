from modlunky2.mem.state import Theme

class BIOME:
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
    def get_biome_for_level(
        lvl,
    ):  # cave by default, depicts what background and sprites will be loaded
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
            return BIOME.OLMEC
        elif lvl.startswith("vlad"):
            return BIOME.VOLCANA
        elif lvl.startswith("volcano") or lvl.endswith("_volcano.lvl"):
            return BIOME.VOLCANA

        dm_themes = [
            BIOME.DWELLING,
            BIOME.JUNGLE,
            BIOME.VOLCANA,
            BIOME.TIDE_POOL,
            BIOME.TEMPLE,
            BIOME.ICE_CAVES,
            BIOME.NEO_BABYLON,
            BIOME.SUNKEN_CITY,
        ]
        for x, themeselect in enumerate(dm_themes):
            if lvl.startswith("dm" + str(x + 1)):
                return themeselect
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

    @staticmethod
    def theme_for_biome(biome):
        if biome == BIOME.DWELLING:
            return Theme.DWELLING
        elif biome == BIOME.JUNGLE:
            return Theme.JUNGLE
        elif biome == BIOME.VOLCANA:
            return Theme.VOLCANA
        elif biome == BIOME.OLMEC:
            return Theme.OLMEC
        elif biome == BIOME.TIDE_POOL:
            return Theme.TIDE_POOL
        elif biome == BIOME.TEMPLE:
            return Theme.TEMPLE
        elif biome == BIOME.ICE_CAVES:
            return Theme.ICE_CAVES
        elif biome == BIOME.NEO_BABYLON:
            return Theme.NEO_BABYLON
        elif biome == BIOME.SUNKEN_CITY:
            return Theme.SUNKEN_CITY
        elif biome == BIOME.CITY_OF_GOLD:
            return Theme.CITY_OF_GOLD
        elif biome == BIOME.DUAT:
            return Theme.DUAT
        elif biome == BIOME.EGGPLANT_WORLD:
            return Theme.EGGPLANT_WORLD
        elif biome == BIOME.SURFACE:
            return Theme.BASE_CAMP
        return Theme.DWELLING

    @staticmethod
    def biome_for_theme(theme, subtheme):
        if theme == Theme.DWELLING:
            return BIOME.DWELLING
        elif theme == Theme.JUNGLE:
            return BIOME.JUNGLE
        elif theme == Theme.VOLCANA:
            return BIOME.VOLCANA
        elif theme == Theme.OLMEC:
            return BIOME.OLMEC
        elif theme == Theme.TIDE_POOL or theme == Theme.ABZU:
            return BIOME.TIDE_POOL
        elif theme == Theme.TEMPLE:
            return BIOME.TEMPLE
        elif theme == Theme.ICE_CAVES:
            return BIOME.ICE_CAVES
        elif theme == Theme.NEO_BABYLON or theme == Theme.TIAMAT:
            return BIOME.NEO_BABYLON
        elif theme == Theme.SUNKEN_CITY or theme == Theme.HUNDUN:
            return BIOME.SUNKEN_CITY
        elif theme == Theme.CITY_OF_GOLD:
            return BIOME.CITY_OF_GOLD
        elif theme == Theme.DUAT:
            return BIOME.DUAT
        elif theme == Theme.EGGPLANT_WORLD:
            return BIOME.EGGPLANT_WORLD
        elif theme == Theme.BASE_CAMP:
            return BIOME.SURFACE
        elif theme == Theme.ARENA or theme == Theme.COSMIC_OCEAN:
            if subtheme is not None:
                return Biomes.biome_for_theme(subtheme, None)
        return BIOME.DWELLING