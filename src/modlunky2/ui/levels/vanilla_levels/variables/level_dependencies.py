import logging
import os
import os.path
from pathlib import Path

from modlunky2.levels import LevelFile

logger = logging.getLogger(__name__)

class LevelDependencies():
    @staticmethod
    def dependencies_for_level(lvl):
        levels = []
        if not lvl.startswith("base"):
            levels.append("generic.lvl")
        if lvl.startswith("base"):
            levels.append("basecamp.lvl")
        elif lvl.startswith("cave"):
            levels.append("dwellingarea.lvl")
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("beehive")
            or lvl.startswith("challenge_moon")
        ):
            levels.append("junglearea.lvl")
        elif lvl.startswith("vlads"):
            levels.append("volcanoarea.lvl")
        elif lvl.startswith("lake") or lvl.startswith("challenge_star"):
            levels.append("tidepoolarea.lvl")
        elif (
            lvl.startswith("hallofush")
            or lvl.startswith("challenge_star")
            or lvl.startswith("babylonarea_1")
            or lvl.startswith("palace")
        ):
            levels.append("babylonarea.lvl")
        elif lvl.startswith("challenge_sun"):
            levels.append("sunkencityarea.lvl")
        elif lvl.startswith("end"):
            levels.append("ending.lvl")
        return levels

    @staticmethod
    def sister_locations_for_level(lvl_name, lvls_path, extracts_path):
        levels = []

        if not lvls_path:
            return []

        def append_level(item):
            # self.depend_order_label["text"] += " -> " + item
            if os.path.exists(Path(lvls_path / item)):
                levels.append(
                    [
                        item,
                        LevelFile.from_path(Path(lvls_path / item)),
                        "custom",
                    ]
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    [
                        item,
                        LevelFile.from_path(Path(extracts_path) / item),
                        "extracts",
                    ]
                )

        # self.depend_order_label["text"] = ""
        if lvl_name.startswith("basecamp"):
            for file in LevelDependencies.dependencies()[0]:
                append_level(file)
        elif lvl_name.startswith("generic.lvl"):
            # for file in LevelDependencies.dependencies()[10]:
            #    append_level(file)
            # removed for now
            # self.depend_order_label.grid_remove()
            # self.tree_depend.grid_remove()
            # self.button_resolve_variables.grid_remove()
            # self.no_conflicts_label.grid()
            return []
        else:
            append_level("generic.lvl")  # adds generic for all other files
        if lvl_name.startswith("challenge_moon.lvl"):
            for file in LevelDependencies.dependencies()[8]:
                append_level(file)
        elif lvl_name.startswith("challenge_star.lvl"):
            for file in LevelDependencies.dependencies()[9]:
                append_level(file)
        elif lvl_name.startswith("junglearea.lvl"):
            for file in LevelDependencies.dependencies()[1]:
                append_level(file)
        elif lvl_name.startswith("volcanoarea.lvl"):
            for file in LevelDependencies.dependencies()[2]:
                append_level(file)
        elif lvl_name.startswith("tidepoolarea.lvl"):
            for file in LevelDependencies.dependencies()[3]:
                append_level(file)
        elif lvl_name.startswith("templearea.lvl"):
            for file in LevelDependencies.dependencies()[4]:
                append_level(file)
        else:
            i = 0
            # each 'depend' = list of files that depend on each other
            for depend in LevelDependencies.dependencies():
                if i == 9:
                    break
                for file in depend:
                    # makes sure opened level file match 1 dependency entry
                    if lvl_name.startswith(file):
                        # makes sure this level isn't being tracked from the generic file
                        if depend != LevelDependencies.dependencies()[10]:
                            logger.debug("checking dependencies of %s", file)
                            for item in depend:
                                append_level(item)
                            break
                i = i + 1
        level = None
        tilecode_compare = []
        for level in levels:
            logger.debug("getting tilecodes from %s", level[0])
            tilecodes = []
            tilecodes.append(str(level[0]) + " file")
            level_tilecodes = level[1].tile_codes.all()

            for tilecode in level_tilecodes:
                tilecodes.append(str(tilecode.name) + " " + str(tilecode.value))
            tilecode_compare.append(tilecodes)

        return levels

    @staticmethod
    def loaded_level_file_for_path(lvl, levels_path, extracts_path):
        if Path(levels_path / lvl).exists():
            return LevelFile.from_path(Path(levels_path / lvl))
        else:
            logger.debug(
                "local dependency for lvl %s not found, attempting to load from extracts", lvl
            )
            return LevelFile.from_path(Path(extracts_path) / lvl)

    @staticmethod
    def dependencies():
        dependencies = []
        dependencies.append(
            [
                "basecamp.lvl",
                "basecamp_garden.lvl",
                "basecamp_shortcut_discovered.lvl",
                "basecamp_shortcut_undiscovered.lvl",
                "basecamp_shortcut_unlocked.lvl",
                "basecamp_surface.lvl",
                "basecamp_tutorial.lvl",
                "basecamp_tv_room_locked.lvl",
                "basecamp_tv_room_unlocked.lvl",
            ]
        )
        dependencies.append(
            ["junglearea.lvl", "blackmarket.lvl", "beehive.lvl", "challenge_moon.lvl"]
        )  # 1
        dependencies.append(
            ["volcanoarea.lvl", "vladscastle.lvl", "challenge_moon.lvl"]
        )  # 2
        dependencies.append(
            ["tidepoolarea.lvl", "lake.lvl", "lakeoffire.lvl", "challenge_star.lvl"]
        )  # 3
        dependencies.append(
            ["templearea.lvl", "beehive.lvl", "challenge_star.lvl"]
        )  # 4
        dependencies.append(
            [
                "babylonarea.lvl",
                "babylonarea_1-1.lvl",
                "hallofushabti.lvl",
                "palaceofpleasure.lvl",
            ]
        )  # 5
        dependencies.append(["sunkencityarea.lvl", "challenge_sun.lvl"])  # 6
        dependencies.append(["ending.lvl", "ending_hard.lvl"])  # 7
        dependencies.append(
            ["challenge_moon.lvl", "junglearea.lvl", "volcanoarea.lvl"]
        )  # 8
        dependencies.append(
            ["challenge_star.lvl", "tidepoolarea.lvl", "templearea.lvl"]
        )  # 9
        dependencies.append(
            [
                "generic.lvl",
                "dwellingarea.lvl",
                "cavebossarea.lvl",
                "junglearea.lvl",
                "blackmarket.lvl",
                "beehive.lvl",
                "challenge_moon.lvl",
                "volcanoarea.lvl",
                "vladscastle.lvl",
                "challenge_moon.lvl",
                "olmecarea.lvl",
                "tidepoolarea.lvl",
                "lake.lvl",
                "lakeoffire.lvl",
                "challenge_star.lvl",
                "abzu.lvl",
                "templearea.lvl",
                "beehive.lvl",
                "challenge_star.lvl",
                "cityofgold.lvl",
                "duat.lvl",
                "icecavesarea.lvl",
                "babylonarea.lvl",
                "babylonarea_1-1.lvl",
                "hallofushabti.lvl",
                "palaceofpleasure.lvl",
                "tiamat.lvl",
                "sunkencityarea.lvl",
                "challenge_sun.lvl",
                "eggplantarea.lvl",
                "hundun.lvl",
                "ending.lvl",
                "ending_hard.lvl",
                "cosmicocean_babylon.lvl",
                "cosmicocean_dwelling.lvl",
                "cosmicocean_icecavesarea.lvl",
                "cosmicocean_jungle.lvl",
                "cosmicocean_sunkencity.lvl",
                "cosmicocean_temple.lvl",
                "cosmicocean_tidepool.lvl",
                "cosmicocean_volcano.lvl",
            ]
        )  # 10
        return dependencies