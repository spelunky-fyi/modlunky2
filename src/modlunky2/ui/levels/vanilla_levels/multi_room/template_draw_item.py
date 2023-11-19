from dataclasses import dataclass

from modlunky2.ui.levels.vanilla_levels.vanilla_types import (
    RoomInstance,
    RoomTemplate,
    MatchedSetroomTemplate,
)


@dataclass
class TemplateDrawItem:
    template: RoomTemplate
    template_index: int
    room_chunk: RoomInstance
    room_index: int
    width_in_rooms: int = 1
    height_in_rooms: int = 1
