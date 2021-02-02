from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, ClassVar

from .utils import split_comment, DirectivePrefixes


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

        if name not in VALID_LEVEL_SETTINGS:
            raise ValueError(
                f"Found level setting with name {name!r} which isn't a valid level setting name."
            )

        if name == "size":
            value = tuple(value.split())
            if len(value) != 2:
                raise ValueError("Directive `size` expects 2 values.")
        elif name == "liquid_gravity":
            value = float(value)
        else:
            value = int(value)

        return cls(name, value, comment)

    def value_to_str(self) -> str:
        if isinstance(self.value, (int, float)):
            return f"{self.value}"
        return " ".join(self.value)

    def to_line(self) -> str:
        line = f"{self.prefix}{self.name}\t\t{self.value_to_str()}"
        if self.comment is not None:
            line = f"{line} // {self.comment}"
        return f"{line}\n"
