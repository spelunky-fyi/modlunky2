from typing import Tuple, List
from enum import Enum


def split_comment(line: str) -> Tuple[str, str]:
    rest, _, comment = line.partition("//")
    comment = comment.strip().strip("/")
    return (rest.strip(), comment)


def parse_chance_values(values: str) -> List[int]:
    return [int(value.strip()) for value in values.split(",")]


def to_line(prefix, name, name_padding, value, value_padding, comment) -> str:
    line = f"{prefix}{name:<{name_padding}}"
    if comment:
        line = f"{line}{value:<{value_padding}} // {comment}"
    else:
        line = f"{line}{value}"
    return f"{line}\n"


class Peekable:
    def __init__(self, iterable):
        self._buffer = []
        self._iterator = iter(iterable)

    def __iter__(self):
        return self

    def __next__(self):
        if not self._buffer:
            return next(self._iterator)
        return self._buffer.pop(0)

    def peek(self):
        try:
            val = next(self._iterator)
        except StopIteration:
            return None
        self._buffer.append(val)
        return val

    def advance(self):
        try:
            val = next(self)
        except StopIteration:
            return None
        return val


class DirectivePrefixes(Enum):
    LEVEL_SETTING = r"\-"
    TILE_CODE = r"\?"
    LEVEL_CHANCE = r"\%"
    MONSTER_CHANCE = r"\+"
    TEMPLATE = r"\."
    TEMPLATE_SETTING = r"\!"
