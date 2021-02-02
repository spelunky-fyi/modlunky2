from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Dict, OrderedDict as OrderedDictType
from pathlib import Path

from .level_chances import LevelChance
from .level_templates import LevelTemplate
from .monster_chances import MonsterChance
from .level_settings import LevelSetting
from .tile_codes import TileCode
from .utils import Peekable, DirectivePrefixes


SECTION_COMMENT = "// ------------------------------"

def parse_section_comment(line, file_handle):
    output = f"{line}\n"

    next_line = file_handle.peek()
    while next_line and next_line.startswith("//"):
        output += next_line

        # Advance the cursor and peek the next line.
        file_handle.advance()
        next_line = file_handle.peek()

    return output


@dataclass
class LevelFile:
    comment: Optional[str]
    level_settings: OrderedDictType[str, LevelSetting]
    tile_codes: OrderedDictType[str, TileCode]
    level_chances: OrderedDictType[str, LevelChance]
    monster_chances: OrderedDictType[str, MonsterChance]
    level_templates: OrderedDictType[str, LevelTemplate]
    section_comments: Dict[str, str]

    @classmethod
    def from_path(cls, level_path: Path) -> "LevelFile":
        level_file = LevelFile(
            comment=None,
            level_settings=OrderedDict(),
            tile_codes=OrderedDict(),
            level_chances=OrderedDict(),
            monster_chances=OrderedDict(),
            level_templates=OrderedDict(),
            section_comments={},
        )

        last_section_comment = None
        last_seen_directive = None

        with level_path.open("r") as level_fh:
            level_fh = Peekable(level_fh)
            for line in level_fh:

                line = line.strip()
                if not line:
                    continue

                if line.startswith(DirectivePrefixes.LEVEL_SETTING.value):
                    level_setting = LevelSetting.parse(line)
                    level_file.level_settings[level_setting.name] = level_setting
                    if last_seen_directive != DirectivePrefixes.LEVEL_SETTING:
                        if last_section_comment:
                            level_file.section_comments[DirectivePrefixes.LEVEL_SETTING] = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.LEVEL_SETTING

                elif line.startswith(DirectivePrefixes.TILE_CODE.value):
                    tile_code = TileCode.parse(line)
                    level_file.tile_codes[tile_code.name] = tile_code
                    if last_seen_directive != DirectivePrefixes.TILE_CODE:
                        if last_section_comment:
                            level_file.section_comments[DirectivePrefixes.TILE_CODE] = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.TILE_CODE

                elif line.startswith(DirectivePrefixes.LEVEL_CHANCE.value):
                    level_chance = LevelChance.parse(line)
                    level_file.level_chances[level_chance.name] = level_chance
                    if last_seen_directive != DirectivePrefixes.LEVEL_CHANCE:
                        if last_section_comment:
                            level_file.section_comments[DirectivePrefixes.LEVEL_CHANCE] = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.LEVEL_CHANCE

                elif line.startswith(DirectivePrefixes.MONSTER_CHANCE.value):
                    monster_chance = MonsterChance.parse(line)
                    level_file.monster_chances[monster_chance.name] = monster_chance
                    if last_seen_directive != DirectivePrefixes.MONSTER_CHANCE:
                        if last_section_comment:
                            level_file.section_comments[DirectivePrefixes.MONSTER_CHANCE] = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.MONSTER_CHANCE

                elif line.startswith(DirectivePrefixes.TEMPLATE.value):
                    template = LevelTemplate.parse(line, level_fh)
                    level_file.level_templates[template.name] = template
                    if last_seen_directive != DirectivePrefixes.TEMPLATE:
                        if last_section_comment:
                            level_file.section_comments[DirectivePrefixes.TEMPLATE] = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.TEMPLATE

                elif line == SECTION_COMMENT:
                    last_section_comment = parse_section_comment(line, level_fh)
                    if not level_file.comment and not last_seen_directive:
                        level_file.comment = last_section_comment
                        last_section_comment = None

        return level_file

    def pprint(self):
        print(self.comment)

        section_comment = self.section_comments.get(DirectivePrefixes.LEVEL_SETTING)
        if section_comment:
            print(section_comment)
        for level_setting in self.level_settings.values():
            print(level_setting.to_line(), end="")
        print("")

        section_comment = self.section_comments.get(DirectivePrefixes.TILE_CODE)
        if section_comment:
            print(section_comment)
        for tile_code in self.tile_codes.values():
            print(tile_code.to_line(), end="")
        print("")

        section_comment = self.section_comments.get(DirectivePrefixes.LEVEL_CHANCE)
        if section_comment:
            print(section_comment)
        for level_chance in self.level_chances.values():
            print(level_chance.to_line(), end="")
        print("")

        section_comment = self.section_comments.get(DirectivePrefixes.MONSTER_CHANCE)
        if section_comment:
            print(section_comment)
        for monster_chance in self.monster_chances.values():
            print(monster_chance.to_line(), end="")
        print("")

        section_comment = self.section_comments.get(DirectivePrefixes.TEMPLATE)
        if section_comment:
            print(section_comment)
        for template in self.level_templates.values():
            template.pprint()
        print("")
