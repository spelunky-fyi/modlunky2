from dataclasses import dataclass
from functools import lru_cache
import logging
import os
import os.path
from pathlib import Path

from modlunky2.levels import LevelFile

logger = logging.getLogger(__name__)

@dataclass
class SisterLocation:
    level_name: str
    level: LevelFile
    location: str

class LevelDependencies:
    @staticmethod
    def dependencies_for_level(lvl):
        levels = []
        if not lvl.startswith("base"):
            levels.append("generic.lvl")
        if lvl.startswith("base"):
            levels.append("basecamp.lvl")
        elif lvl.startswith("blackmark"):
            levels.append("junglearea.lvl")
        elif lvl.startswith("beehive"):
            levels.append("templearea.lvl")
            levels.append("junglearea.lvl")
        elif lvl.startswith("vlads"):
            levels.append("volcanoarea.lvl")
        elif lvl.startswith("challenge_moon"):
            levels.append("junglearea.lvl")
            levels.append("volcanoarea.lvl")
        elif lvl.startswith("lake"):
            levels.append("tidepoolarea.lvl")
        elif lvl.startswith("challenge_star"):
            levels.append("tidepoolarea.lvl")
            levels.append("templearea.lvl")
        elif (
            lvl.startswith("hallofush")
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
    def loaded_level_file_for_path(lvl, levels_path, extracts_path):
        if Path(levels_path / lvl).exists():
            return LevelFile.from_path(Path(levels_path / lvl))
        else:
            logger.debug(
                "local dependency for lvl %s not found, attempting to load from extracts",
                lvl,
            )
            return LevelFile.from_path(Path(extracts_path) / lvl)

    @staticmethod
    def get_loaded_level(item, lvls_path, extracts_path):
        if os.path.exists(Path(lvls_path / item)):
            return SisterLocation(
                item,
                LevelFile.from_path(Path(lvls_path / item)),
                "custom",
            )

        else:
            logger.debug(
                "local dependency lvl not found, attempting load from extracts"
            )
            return SisterLocation(
                item,
                LevelFile.from_path(Path(extracts_path) / item),
                "extracts",
            )

    @staticmethod
    def sister_locations_for_level(lvl_name, lvls_path, extracts_path):
        levels = []

        if not lvls_path:
            return []

        def get_loaded_level(item):
            return LevelDependencies.get_loaded_level(item, lvls_path, extracts_path)

        for depend in LevelDependencies.dependencies():
            if lvl_name in depend:
                levels.append([get_loaded_level(dep) for dep in depend])

        if len(levels) == 0:
            levels.append([get_loaded_level(lvl_name)])

        if lvl_name.startswith("generic.lvl"):
            return [[get_loaded_level(dep)] for dep in LevelDependencies.generic_dependencies()]
        elif not lvl_name.startswith("basecamp"):
            for dependencies in levels:
                dependencies.append(get_loaded_level("generic.lvl"))

        return levels

    @staticmethod
    @lru_cache
    def generic_dependencies():
         return [
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

    @staticmethod
    @lru_cache
    def dependencies():
        return [
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
            ],
            ["junglearea.lvl", "blackmarket.lvl", "beehive.lvl"],
            ["junglearea.lvl", "challenge_moon.lvl", "beehive.lvl"],
            ["volcanoarea.lvl", "vladscastle.lvl"],
            ["volcanoarea.lvl", "challenge_moon.lvl"],
            ["tidepoolarea.lvl", "challenge_star.lvl", "lake.lvl"],
            ["tidepoolarea.lvl", "lakeoffire.lvl"],
            ["templearea.lvl", "challenge_star.lvl", "beehive.lvl"],
            ["babylonarea.lvl", "babylonarea_1-1.lvl"],
            ["babylonarea.lvl", "hallofushabti.lvl"],
            ["babylonarea.lvl", "palaceofpleasure.lvl"],
            ["sunkencityarea.lvl", "challenge_sun.lvl"],
            ["ending.lvl", "ending_hard.lvl"],
        ]
