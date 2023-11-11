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
            return "tidepool"
        elif (
            lvl.startswith("babylon")
            or lvl.startswith("hallofu")
            or lvl.endswith("_babylon.lvl")
            or lvl.startswith("palace")
            or lvl.startswith("tiamat")
        ):
            return "babylon"
        elif lvl.startswith("basecamp"):
            return "cave"
        elif lvl.startswith("beehive"):
            return "beehive"
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("jungle")
            or lvl.startswith("challenge_moon")
            or lvl.endswith("_jungle.lvl")
        ):
            return "jungle"
        elif (
            lvl.startswith("challenge_star")
            or lvl.startswith("temple")
            or lvl.endswith("_temple.lvl")
        ):
            return "temple"
        elif (
            lvl.startswith("challenge_sun")
            or lvl.startswith("sunken")
            or lvl.startswith("hundun")
            or lvl.startswith("ending_hard")
            or lvl.endswith("_sunkencity.lvl")
        ):
            return "sunken"
        elif lvl.startswith("city"):
            return "gold"
        elif lvl.startswith("duat"):
            return "duat"
        elif lvl.startswith("egg"):
            return "eggplant"
        elif lvl.startswith("ice") or lvl.endswith("_icecavesarea.lvl"):
            return "ice"
        elif lvl.startswith("olmec"):
            return "jungle"
        elif lvl.startswith("vlad"):
            return "volcano"
        elif lvl.startswith("volcano") or lvl.endswith("_volcano.lvl"):
            return "volcano"
        return "cave"
