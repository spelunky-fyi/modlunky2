from enum import Enum


class LevelPrefixes(Enum):
    setting = "\\-"
    tile_code = "\\?"
    level_chances = "\\%"
    monster_chances = "\\+"
    template_directive = "\\!"
    room_start = "\\."
