import logging
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
    def loaded_level_file_for_path(lvl, levels_path, extracts_path):
        if Path(levels_path / lvl).exists():
            return LevelFile.from_path(Path(levels_path / lvl))
        else:
            logger.info(
                "local dependency for lvl %s not found, attempting to load from extracts", lvl
            )
            return LevelFile.from_path(Path(extracts_path) / lvl)