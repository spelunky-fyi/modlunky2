from dataclasses import dataclass
from collections import OrderedDict
from typing import ClassVar, Generic, Optional, TextIO, TypeVar

from .utils import DirectivePrefixes, split_comment, to_line

T = TypeVar("T")  # pylint: disable=invalid-name

VALID_LEVEL_SETTINGS = set(
    [
        "altar_room_chance",
        "back_room_chance",
        "back_room_hidden_door_cache_chance",
        "back_room_hidden_door_chance",
        "back_room_interconnection_chance",
        "background_chance",
        "flagged_liquid_rooms",
        "floor_bottom_spread_chance",
        "floor_side_spread_chance",
        "ground_background_chance",
        "idol_room_chance",
        "liquid_gravity",
        "machine_bigroom_chance",
        "machine_rewardroom_chance",
        "machine_tallroom_chance",
        "machine_wideroom_chance",
        "max_liquid_particles",
        "mount_chance",
        "size",
    ]
)

NAME_PADDING = max(map(len, VALID_LEVEL_SETTINGS)) + 4


class LevelSettings:
    def __init__(self):
        self._inner = OrderedDict()
        self.comment = None

    def get(self, name):
        LevelSetting.validate_name(name)
        return self._inner.get(name)

    def set_obj(self, obj: "LevelSetting"):
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
class LevelSetting(Generic[T]):
    prefix: ClassVar[str] = DirectivePrefixes.LEVEL_SETTING.value
    name: str
    value: T
    comment: Optional[str]

    @classmethod
    def parse(cls, line: str) -> "LevelSetting":
        rest, comment = split_comment(line)
        directive, value = rest.split(None, 1)
        name = directive[2:]

        if not name:
            raise ValueError("Directive missing name.")

        level_setting = cls(name, value, comment)
        level_setting.clean()
        level_setting.validate()

        return level_setting

    @staticmethod
    def validate_name(name: str):
        if name not in VALID_LEVEL_SETTINGS:
            raise ValueError(f"Invalid name provided for LevelSetting: {name!r}")

    def validate_value(self):
        if self.name == "size":
            if not isinstance(self.value, tuple) or len(self.value) != 2:
                raise ValueError(
                    f"LevelSetting with name {self.name} expected a tuple of length 2: {self.value!r}"
                )
        elif self.name == "liquid_gravity":
            if not isinstance(self.value, float):
                raise ValueError(
                    f"LevelSetting with name {self.name} expected to be a float: {self.value!r}"
                )
        else:
            if not isinstance(self.value, int):
                raise ValueError(
                    f"LevelSetting with name {self.name} expected to be an int: {self.value!r}"
                )

    def validate(self):
        self.validate_name(self.name)
        self.validate_value()

    def clean_value(self):
        if not isinstance(self.value, str):
            return

        if self.name == "size":
            value = tuple(self.value.split())
            if len(value) != 2:
                raise ValueError("Directive `size` expects 2 values.")
        elif self.name == "liquid_gravity":
            value = float(self.value)
        else:
            value = int(self.value)

        self.value = value

    def clean(self):
        self.clean_value()

    def value_to_str(self) -> str:
        if isinstance(self.value, (int, float)):
            return f"{self.value}"
        return " ".join(self.value)

    def to_line(self) -> str:
        return to_line(
            self.prefix, self.name, NAME_PADDING, self.value_to_str(), 10, self.comment
        )

    def write(self, handle: TextIO):
        handle.write(self.to_line())
