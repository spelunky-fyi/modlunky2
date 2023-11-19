from modlunky2.ui.levels.shared.setrooms import Setroom, MatchedSetroom
from modlunky2.ui.levels.vanilla_levels.vanilla_types import RoomInstance, RoomTemplate, MatchedSetroomTemplate
from modlunky2.ui.levels.vanilla_levels.multi_room.template_draw_item import TemplateDrawItem

def find_roommap(templates):
    setrooms = {}
    for room_template in templates:
        matched_template = Setroom.find_vanilla_setroom(room_template.name)
        if matched_template:
            if matched_template.name not in setrooms:
                setrooms[matched_template.name] = []
            setrooms[matched_template.name].append(MatchedSetroomTemplate(room_template, matched_template))
        # if not matched_template:
        #     continue

        # setrooms.append(MatchedSetroomTemplate(room_template, matched_template))


    def expand_to_height_if_necessary(room_map, height):
        if len(room_map) < height:
            for _ in range(height - len(room_map)):
                if len(room_map) == 0:
                    room_map.append([None])
                else:
                    room_map.append([None for _ in range(len(room_map[0]))])

    def expand_to_width_if_necessary(room_map, width):
        for row in room_map:
            if len(row) < width:
                for _ in range(width - len(row)):
                    row.append(None)

    room_map = []
    setroom_start = 0

    for _, setroomtype in setrooms.items():
        for matchedtemplate in setroomtype:
            match = matchedtemplate.setroom
            x, y = match.coords.x, match.coords.y

            expand_to_height_if_necessary(room_map, y + setroom_start + 1)
            expand_to_width_if_necessary(room_map, x + 1)

            room_map[setroom_start + y][x] = TemplateDrawItem(matchedtemplate.template, templates.index(matchedtemplate.template), matchedtemplate.template.rooms[0], 0)

        setroom_start = len(room_map)

    return room_map