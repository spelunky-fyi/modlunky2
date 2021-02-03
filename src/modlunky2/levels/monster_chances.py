from dataclasses import dataclass
from collections import OrderedDict
from typing import ClassVar, Optional, TextIO, Tuple, Union

from .utils import DirectivePrefixes, parse_chance_values, split_comment, to_line

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


class MonsterChances:
    def __init__(self):
        self._inner = OrderedDict()
        self.comment = None

    def get(self, name):
        MonsterChance.validate_name(name)
        return self._inner.get(name)

    def set_obj(self, obj: "MonsterChance"):
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
class MonsterChance:
    prefix: ClassVar[str] = DirectivePrefixes.MONSTER_CHANCE.value
    name: str
    value: Union[int, Tuple[int, int, int, int]]
    comment: Optional[str]

    @classmethod
    def parse(cls, line: str) -> "MonsterChance":
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
        if name not in VALID_MONSTER_CHANCES:
            raise ValueError(f"Invalid name provided for MonsterChance: {name!r}")

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
                f"MonsterChance {self.name!r} has {len(value)} values when 1 or 4 is expected: {value!r}"
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
