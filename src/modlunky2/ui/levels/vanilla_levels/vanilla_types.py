from dataclasses import dataclass
from typing import List, Optional

from modlunky2.levels.level_templates import TemplateSetting
from modlunky2.ui.levels.shared.setrooms import MatchedSetroom


@dataclass
class RoomInstance:
    name: Optional[str]
    settings: List[TemplateSetting]
    front: List[List[str]]
    back: List[List[str]]


@dataclass
class RoomTemplate:
    name: str
    comment: Optional[str]
    rooms: List[RoomInstance]


@dataclass
class MatchedSetroomTemplate:
    template: RoomTemplate
    setroom: MatchedSetroom
