from dataclasses import dataclass
from typing import Optional, Union, Tuple, ClassVar

from .utils import split_comment, parse_chance_values, DirectivePrefixes, to_line


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
        value = parse_chance_values(value)
        name = directive[2:]

        if not name:
            raise ValueError("Directive missing name.")

        if name not in VALID_LEVEL_CHANCES:
            raise ValueError(
                f"Found level chance with name {name!r} which isn't a valid level chance name."
            )

        if len(value) not in (1, 4):
            raise ValueError(
                f"Level chance {name!r} has {len(value)} values when 1 or 4 is expected: {value!r}"
            )

        if len(value) == 1:
            value = value[0]

        return cls(name, value, comment)

    def value_to_str(self) -> str:
        value = self.value
        if isinstance(value, int):
            value = [value]
        return ", ".join(map(str, value))

    def to_line(self) -> str:
        return to_line(
            self.prefix,
            self.name,
            NAME_PADDING,
            self.value_to_str(),
            28,
            self.comment
        )
