import re
from dataclasses import dataclass
from enum import Enum
from collections import OrderedDict
from itertools import zip_longest
from typing import ClassVar, List, Optional, TextIO, Tuple

from modlunky2.levels.utils import split_comment

from .utils import DirectivePrefixes

VALID_LEVEL_TEMPLATES = set(
    [
        "abzu_backdoor",
        "altar",
        "anubis_room",
        "apep",
        "beehive",
        "beehive_entrance",
        "blackmarket_coffin",
        "blackmarket_entrance",
        "blackmarket_exit",
        "cache",
        "cavemanshop",
        "challenge_0-0",
        "challenge_0-1",
        "challenge_0-2",
        "challenge_0-3",
        "challenge_1-0",
        "challenge_1-1",
        "challenge_1-2",
        "challenge_1-3",
        "challenge_bottom",
        "challenge_entrance",
        "challenge_special",
        "chunk_air",
        "chunk_door",
        "chunk_ground",
        "coffin_player",
        "coffin_player_vertical",
        "coffin_unlockable",
        "cog_altar_top",
        "crashedship_entrance",
        "crashedship_entrance_notop",
        "curioshop",
        "diceshop",
        "empress_grave",
        "entrance",
        "entrance_drop",
        "exit",
        "exit_notop",
        "feeling_factory",
        "feeling_prison",
        "feeling_tomb",
        "ghistroom",
        "ghistshop",
        "idol",
        "idol_top",
        "lake_exit",
        "lake_normal",
        "lake_notop",
        "lakeoffire_back_entrance",
        "lakeoffire_back_exit",
        "machine_bigroom_path",
        "machine_bigroom_side",
        "machine_keyroom",
        "machine_rewardroom",
        "machine_tallroom_path",
        "machine_tallroom_side",
        "machine_wideroom_path",
        "machine_wideroom_side",
        "moai",
        "mothership_coffin",
        "mothership_entrance",
        "mothership_exit",
        "motherstatue_room",
        "oldhunter_cursedroom",
        "oldhunter_keyroom",
        "oldhunter_rewardroom",
        "olmecship_room",
        "palaceofpleasure_0-0",
        "palaceofpleasure_0-1",
        "palaceofpleasure_0-2",
        "palaceofpleasure_1-0",
        "palaceofpleasure_1-1",
        "palaceofpleasure_1-2",
        "palaceofpleasure_2-0",
        "palaceofpleasure_2-1",
        "palaceofpleasure_2-2",
        "palaceofpleasure_3-0",
        "palaceofpleasure_3-1",
        "palaceofpleasure_3-2",
        "passage_horz",
        "passage_turn",
        "passage_vert",
        "path_drop",
        "path_drop_notop",
        "path_normal",
        "path_notop",
        "pen_room",
        "posse",
        "quest_thief1",
        "quest_thief2",
        "room2",
        "shop",
        "shop_attic",
        "shop_basement",
        "shop_entrance_down",
        "shop_entrance_up",
        "side",
        "sisters_room",
        "storage_room",
        "tuskdiceshop",
        "tuskfrontdiceshop",
        "udjatentrance",
        "udjattop",
        "ushabti_entrance",
        "ushabti_room",
        "vault",
        "vlad_bottom_exit",
        "vlad_bottom_tunnel",
        "vlad_drill",
        "vlad_entrance",
        "vlad_tunnel",
    ]
)

SETROOM_RE = re.compile(r"^setroom\d{1,2}-\d{1,2}")

TEMPLATE_COMMENT = "/" * 80


class TemplateSetting(Enum):
    IGNORE = "ignore"
    FLIP = "flip"
    ONLYFLIP = "onlyflip"
    DUAL = "dual"
    RARE = "rare"
    HARD = "hard"
    LIQUID = "liquid"
    PURGE = "purge"

    def to_line(self):
        prefix = DirectivePrefixes.TEMPLATE_SETTING.value
        return f"{prefix}{self.value}\n"


VALID_TEMPLATE_SETTINGS = set(rf"\!{setting.value}" for setting in TemplateSetting)


class LevelTemplates:
    def __init__(self):
        self._inner = OrderedDict()
        self.comment = None

    def get(self, name):
        LevelTemplate.validate_name(name)
        return self._inner.get(name)

    def set_obj(self, obj: "LevelTemplate"):
        obj.validate()
        self._inner[obj.name] = obj

    def write(self, handle: TextIO):
        if self.comment:
            handle.write(f"{self.comment}\n")
        for idx, template in enumerate(self._inner.values()):
            template.write(handle)
            if idx < len(self._inner) - 1:
                handle.write("\n")


@dataclass
class Chunk:
    comment: Optional[str]
    settings: List[TemplateSetting]
    foreground: List[List[str]]
    background: List[List[str]]

    @staticmethod
    def partition_line(line: str) -> Tuple[str, str]:
        foreground, _, background = line.partition(" ")
        return foreground.strip(), background.strip()

    @classmethod
    def parse(cls, file_handle: TextIO) -> "Chunk":
        chunk = cls(comment="", settings=[], foreground=[], background=[])

        for line in file_handle:
            line = line.strip()

            if not line:
                # Reached the end of the file chunk or file.
                return chunk

            if line.startswith("//"):
                chunk.comment += f"{line}\n"
            elif line in VALID_TEMPLATE_SETTINGS:
                chunk.settings.append(TemplateSetting(line[2:]))
            else:
                foreground, background = cls.partition_line(line)
                if background:
                    chunk.background.append(list(background))
                chunk.foreground.append(list(foreground))

        return chunk

    def write(self, handle: TextIO):
        if self.comment:
            handle.write(self.comment)

        for setting in self.settings:
            handle.write(setting.to_line())

        for fg_line, bg_line in zip_longest(self.foreground, self.background):
            line = "".join(fg_line)
            if bg_line:
                line = f"{line} {''.join(bg_line)}"
            handle.write(f"{line}\n")


@dataclass
class LevelTemplate:
    prefix: ClassVar[str] = DirectivePrefixes.TEMPLATE.value

    name: str
    comment: Optional[str]
    chunks: List[Chunk]

    @classmethod
    def parse(cls, line: str, file_handle: TextIO) -> "LevelTemplate":
        directive, comment = split_comment(line)
        name = directive[2:]

        if not name:
            raise ValueError("Directive missing name.")

        chunks = []
        level_template = cls(name, comment, chunks)

        next_line = file_handle.peek()
        while next_line:
            next_line, comment = split_comment(next_line)

            # We've reached the next Template, return
            if next_line.startswith(DirectivePrefixes.TEMPLATE.value):
                return level_template

            if next_line or comment:
                chunk = Chunk.parse(file_handle)
                chunks.append(chunk)
            else:
                # Advance the cursor and peek the next line.
                file_handle.advance()

            next_line = file_handle.peek()

        return level_template

    @staticmethod
    def validate_name(name: str):
        if name not in VALID_LEVEL_TEMPLATES and not SETROOM_RE.match(name):
            raise ValueError(f"Name {name!r} isn't a valid level template")

    def validate(self):
        self.validate_name(self.name)

    def write(self, handle: TextIO):
        handle.write(f"{TEMPLATE_COMMENT}\n")
        name_line = f"{self.prefix}{self.name}"
        if self.comment:
            name_line += f"   // {self.comment}"
        handle.write(f"{name_line}\n")
        handle.write(f"{TEMPLATE_COMMENT}\n\n")

        for idx, chunk in enumerate(self.chunks):
            chunk.write(handle)
            if idx < len(self.chunks) - 1:
                handle.write("\n")
