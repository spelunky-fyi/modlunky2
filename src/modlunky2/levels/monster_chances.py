from dataclasses import dataclass
from typing import Optional, Union, Tuple, ClassVar

from .utils import split_comment, parse_chance_values, DirectivePrefixes, to_line


VALID_MONSTER_CHANCES = set(
    [
        "bat",
        "bee",
        "cat",
        "caveman",
        "cobra",
        "crabman",
        "critteranchovy",
        "critterbutterfly",
        "crittercrab",
        "critterdrone",
        "critterdungbeetle",
        "critterfirefly",
        "critterfish",
        "critterlocust",
        "critterpenguin",
        "critterslime",
        "crittersnail",
        "crocman",
        "female_jiangshi",
        "firebug",
        "firefrog",
        "fish",
        "frog",
        "giantfly",
        "giantspider",
        "hangspider",
        "hermitcrab",
        "hornedlizard",
        "imp",
        "jiangshi",
        "landmine",
        "lavamander",
        "leprechaun",
        "mantrap",
        "mole",
        "monkey",
        "mosquito",
        "necromancer",
        "octopus",
        "olmite",
        "robot",
        "snake",
        "sorceress",
        "spider",
        "springtrap",
        "tadpole",
        "tikiman",
        "ufo",
        "vampire",
        "witchdoctor",
        "yeti",
    ]
)

NAME_PADDING = max(map(len, VALID_MONSTER_CHANCES)) + 4


@dataclass
class MonsterChance:
    prefix: ClassVar[str] = DirectivePrefixes.MONSTER_CHANCE.value
    name: str
    value: Union[int, Tuple[int, int, int, int]]
    comment: Optional[str]

    @classmethod
    def parse(cls, line: str) -> "MonsterChance":
        rest, comment = split_comment(line)
        directive, value = rest.split(None, 1)
        value = parse_chance_values(value)
        name = directive[2:]

        if not name:
            raise ValueError("Directive missing name.")

        if name not in VALID_MONSTER_CHANCES:
            raise ValueError(
                f"Found monster chance with name {name!r} which isn't a valid monster chance name."
            )

        if len(value) not in (1, 4):
            raise ValueError(
                f"Monster chance {name!r} has {len(value)} values when 1 or 4 is expected: {value!r}"
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
