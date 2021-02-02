from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, OrderedDict as OrderedDictType
from pathlib import Path

from .level_chances import LevelChance
from .level_templates import LevelTemplate
from .monster_chances import MonsterChance
from .level_settings import LevelSetting
from .tile_codes import TileCode
from .utils import Peekable, DirectivePrefixes


@dataclass
class LevelFile:
    comment: Optional[str]
    level_settings: OrderedDictType[str, LevelSetting]
    tile_codes: OrderedDictType[str, TileCode]
    level_chances: OrderedDictType[str, LevelChance]
    monster_chances: OrderedDictType[str, MonsterChance]
    level_templates: OrderedDictType[str, LevelTemplate]

    @classmethod
    def from_path(cls, level_path: Path) -> "LevelFile":
        level_file = LevelFile(
            comment=None,
            level_settings=OrderedDict(),
            tile_codes=OrderedDict(),
            level_chances=OrderedDict(),
            monster_chances=OrderedDict(),
            level_templates=OrderedDict(),
        )

        with level_path.open("r") as level_fh:
            level_fh = Peekable(level_fh)
            for line in level_fh:
                line = line.strip()
                if not line:
                    continue

                if line.startswith(DirectivePrefixes.LEVEL_SETTING.value):
                    level_setting = LevelSetting.parse(line)
                    level_file.level_settings[level_setting.name] = level_setting
                elif line.startswith(DirectivePrefixes.TILE_CODE.value):
                    tile_code = TileCode.parse(line)
                    level_file.tile_codes[tile_code.name] = tile_code
                elif line.startswith(DirectivePrefixes.LEVEL_CHANCE.value):
                    level_chance = LevelChance.parse(line)
                    level_file.level_chances[level_chance.name] = level_chance
                elif line.startswith(DirectivePrefixes.MONSTER_CHANCE.value):
                    monster_chance = MonsterChance.parse(line)
                    level_file.monster_chances[monster_chance.name] = monster_chance
                elif line.startswith(DirectivePrefixes.TEMPLATE.value):
                    template = LevelTemplate.parse(line, level_fh)
                    level_file.level_templates[template.name] = template

        return level_file

    def pprint(self):
        print("Level Settings:")
        for level_setting in self.level_settings.values():
            print(level_setting.to_line(), end="")
        print("")

        print("Tile Codes:")
        for tile_code in self.tile_codes.values():
            print(tile_code.to_line(), end="")
        print("")

        print("Level Chances:")
        for level_chance in self.level_chances.values():
            print(level_chance.to_line(), end="")
        print("")

        print("Monster Chances:")
        for monster_chance in self.monster_chances.values():
            print(monster_chance.to_line(), end="")
        print("")

        print("Templates:")
        for template in self.level_templates.values():
            template.pprint()
        print("")
