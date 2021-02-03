from dataclasses import dataclass
from collections import OrderedDict
from typing import ClassVar, Optional, TextIO, Tuple, Union

from .utils import DirectivePrefixes, parse_chance_values, split_comment, to_line

VALID_LEVEL_CHANCES = set(
    [
        "arrowtrap_chance",
        "beehive_chance",
        "bigspeartrap_chance",
        "chain_blocks_chance",
        "crusher_trap_chance",
        "eggsac_chance",
        "jungle_spear_trap_chance",
        "lasertrap_chance",
        "leprechaun_chance",
        "liontrap_chance",
        "minister_chance",
        "pushblock_chance",
        "skulldrop_chance",
        "snap_trap_chance",
        "sparktrap_chance",
        "spike_ball_chance",
        "stickytrap_chance",
        "totemtrap_chance",
    ]
)

NAME_PADDING = max(map(len, VALID_LEVEL_CHANCES)) + 4


class LevelChances:
    def __init__(self):
        self._inner = OrderedDict()
        self.comment = None

    def get(self, name):
        LevelChance.validate_name(name)
        return self._inner.get(name)

    def set_obj(self, obj: "LevelChance"):
        obj.clean()
        obj.validate()
        self._inner[obj.name] = obj

    def write(self, handle: TextIO):
        if self.comment:
            handle.write(f"{self.comment}\n")
        for obj in self._inner.values():
            handle.write(obj.to_line())
        handle.write("\n")


@dataclass
class LevelChance:
    prefix: ClassVar[str] = DirectivePrefixes.LEVEL_CHANCE.value
    name: str
    value: Union[int, Tuple[int, int, int, int]]
    comment: Optional[str]

    @classmethod
    def parse(cls, line: str) -> "LevelChance":
        rest, comment = split_comment(line)
        directive, value = rest.split(None, 1)
        name = directive[2:]

        if not name:
            raise ValueError("Directive missing name.")

        obj = cls(name, value, comment)
        obj.clean()
        obj.validate()

        return obj

    @staticmethod
    def validate_name(name: str):
        if name not in VALID_LEVEL_CHANCES:
            raise ValueError(f"Invalid name provided for LevelChance: {name!r}")

    def validate_value(self):
        if isinstance(self.value, list) and len(self.value) != 4:
            raise ValueError(
                f"Expected 4 values but got {len(self.value)} for {self.name}"
            )
        elif not isinstance(self.value, (list, int)):
            raise ValueError(f"Got unexpected type for {self.name}: {self.value!r}")

    def validate(self):
        self.validate_name(self.name)
        self.validate_value()

    def clean_value(self):
        if not isinstance(self.value, str):
            return

        value = parse_chance_values(self.value)

        if len(value) not in (1, 4):
            raise ValueError(
                f"Level chance {self.name!r} has {len(value)} values when 1 or 4 is expected: {value!r}"
            )

        if len(value) == 1:
            value = value[0]

        self.value = value

    def clean(self):
        self.clean_value()

    def value_to_str(self) -> str:
        value = self.value
        if isinstance(value, int):
            value = [value]
        return ", ".join(map(str, value))

    def to_line(self) -> str:
        return to_line(
            self.prefix, self.name, NAME_PADDING, self.value_to_str(), 28, self.comment
        )

    def write(self, handle: TextIO):
        handle.write(self.to_line())
