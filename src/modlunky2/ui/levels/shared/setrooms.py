from dataclasses import dataclass
from collections import namedtuple
from enum import Enum
import re

RoomCoords = namedtuple("RoomCoords", ["x", "y"])
MatchedSetroom = namedtuple("MatchedSetroom", ["name", "template", "coords"])


@dataclass
class BaseTemplateData:
    name: str
    template: str


class VANILLA_SETROOM_TYPE(Enum):
    NONE = "none"
    FRONT = "front"
    BACK = "back"
    DUAL = "dual"


class BaseTemplate:
    setroom = BaseTemplateData("setroom", "setroom{y}-{x}")
    challenge = BaseTemplateData("challenge", "challenge_{y}-{x}")
    palace = BaseTemplateData("palace of pleasure", "palaceofpleasure_{y}-{x}")
    # setroom = {"name":"setroom", "template":"setroom{y}-{x}"}
    # challenge = {"name":"challenge", "template":"challenge_{y}-{x}"}
    # palace = {"name":"palace of pleasure", "template":"palaceofpleasure_{y}-{x}"}


class Setroom:
    @staticmethod
    def match_setroom(template, room):
        # Replaces human-friendly {y} and {x} in the level template format with a regex
        # to find the coordinate of each level template.
        template_regex = "^" + template.format(y=r"(?P<y>\d+)", x=r"(?P<x>\d+)") + "$"
        match = re.search(template_regex, room)
        if match is not None:
            # Fill in the room list at the coordinate of this room with the loaded template data.
            x = int(match.group("x"))
            y = int(match.group("y"))
            return RoomCoords(x, y)
        return None

    @staticmethod
    def find_setroom_in_list(template_list, room):
        for setroom in template_list:
            match = Setroom.match_setroom(setroom.template, room)
            if match:
                return MatchedSetroom(setroom.name, setroom.template, match)
        return None

    @staticmethod
    def find_vanilla_setroom(room):
        return Setroom.find_setroom_in_list(
            [BaseTemplate.setroom, BaseTemplate.challenge, BaseTemplate.palace], room
        )
