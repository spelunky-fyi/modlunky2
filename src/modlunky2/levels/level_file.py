import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import TextIO

from .level_chances import LevelChances, LevelChance
from .level_settings import LevelSettings, LevelSetting
from .level_templates import LevelTemplates, LevelTemplate
from .monster_chances import MonsterChances, MonsterChance
from .tile_codes import TileCodes, TileCode
from .utils import DirectivePrefixes, Peekable

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
    level_settings: LevelSettings
    tile_codes: TileCodes
    level_chances: LevelChances
    monster_chances: MonsterChances
    level_templates: LevelTemplates

    @classmethod
    def from_path(cls, level_path: Path) -> "LevelFile":
        level_file = LevelFile(
            comment=None,
            level_settings=LevelSettings(),
            tile_codes=TileCodes(),
            level_chances=LevelChances(),
            monster_chances=MonsterChances(),
            level_templates=LevelTemplates(),
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
                    level_file.level_settings.set_obj(level_setting)
                    if last_seen_directive != DirectivePrefixes.LEVEL_SETTING:
                        if last_section_comment:
                            level_file.level_settings.comment = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.LEVEL_SETTING

                elif line.startswith(DirectivePrefixes.TILE_CODE.value):
                    tile_code = TileCode.parse(line)
                    level_file.tile_codes.set_obj(tile_code)
                    if last_seen_directive != DirectivePrefixes.TILE_CODE:
                        if last_section_comment:
                            level_file.tile_codes.comment = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.TILE_CODE

                elif line.startswith(DirectivePrefixes.LEVEL_CHANCE.value):
                    level_chance = LevelChance.parse(line)
                    level_file.level_chances.set_obj(level_chance)
                    if last_seen_directive != DirectivePrefixes.LEVEL_CHANCE:
                        if last_section_comment:
                            level_file.level_chances.comment = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.LEVEL_CHANCE

                elif line.startswith(DirectivePrefixes.MONSTER_CHANCE.value):
                    monster_chance = MonsterChance.parse(line)
                    level_file.monster_chances.set_obj(monster_chance)
                    if last_seen_directive != DirectivePrefixes.MONSTER_CHANCE:
                        if last_section_comment:
                            level_file.monster_chances.comment = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.MONSTER_CHANCE

                elif line.startswith(DirectivePrefixes.TEMPLATE.value):
                    template = LevelTemplate.parse(line, level_fh)
                    level_file.level_templates.set_obj(template)
                    if last_seen_directive != DirectivePrefixes.TEMPLATE:
                        if last_section_comment:
                            level_file.level_templates.comment = last_section_comment
                            last_section_comment = None
                        last_seen_directive = DirectivePrefixes.TEMPLATE

                elif line == SECTION_COMMENT:
                    last_section_comment = parse_section_comment(line, level_fh)
                    if not level_file.comment and not last_seen_directive:
                        level_file.comment = last_section_comment
                        last_section_comment = None

        return level_file

    def write(self, handle: TextIO):
        handle.write(f"{self.comment}\n")
        self.level_settings.write(handle)
        self.tile_codes.write(handle)
        self.level_chances.write(handle)
        self.monster_chances.write(handle)
        self.level_templates.write(handle)

    def write_path(self, level_path: Path):
        with level_path.open("w") as level_fh:
            self.write(level_fh)

    def print(self):
        self.write(sys.stdout)
