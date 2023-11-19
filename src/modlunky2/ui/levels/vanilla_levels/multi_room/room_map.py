import math

from modlunky2.ui.levels.shared.setrooms import Setroom, MatchedSetroom
from modlunky2.ui.levels.vanilla_levels.vanilla_types import (
    RoomInstance,
    RoomTemplate,
    MatchedSetroomTemplate,
)
from modlunky2.ui.levels.vanilla_levels.multi_room.template_draw_item import (
    TemplateDrawItem,
)

def find_roommap(templates):
    setrooms = {}
    for room_template in templates:
        matched_template = Setroom.find_vanilla_setroom(room_template.name)
        if matched_template:
            if matched_template.name not in setrooms:
                setrooms[matched_template.name] = []
            setrooms[matched_template.name].append(
                MatchedSetroomTemplate(room_template, matched_template)
            )

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

    def set_room(room_map, x, y, room):
        expand_to_height_if_necessary(room_map, y + room.height_in_rooms)
        expand_to_width_if_necessary(room_map, x + room.width_in_rooms)
        room_map[y][x] = room

    room_map = []
    setroom_start = 0

    def get_template_draw_item(room_template, index):
        chunk_index = 0
        if len(room_template.rooms) == 0:
            return None
        chunk = room_template.rooms[chunk_index]
        if chunk is None or len(chunk.front) == 0:
            return None
        return TemplateDrawItem(
            room_template,
            index,
            chunk,
            chunk_index,
            int(math.ceil(len(chunk.front[0]) / 10)),
            int(math.ceil(len(chunk.front) / 8)),
        )


    for _, setroomtype in setrooms.items():
        for matchedtemplate in setroomtype:
            match = matchedtemplate.setroom
            x, y = match.coords.x, match.coords.y

            template_item = get_template_draw_item(matchedtemplate.template, templates.index(matchedtemplate.template))
            if template_item:
                set_room(room_map, x, setroom_start + y, template_item)

        setroom_start = len(room_map)

    template_map = {}
    for index, room_template in enumerate(templates):
        template_item = get_template_draw_item(room_template, index)
        if template_item:
            template_map[room_template.name] = template_item

    path_start = setroom_start
    entrance = template_map.get("entrance")
    entrance_drop = template_map.get("entrance_drop")
    path = template_map.get("path_normal")
    path_drop = template_map.get("path_drop")
    path_notop = template_map.get("path_notop")
    path_drop_notop = template_map.get("path_drop_notop")
    path_exit = template_map.get("exit")
    path_exit_notop = template_map.get("exit_notop")
    path_wide = template_map.get("machine_wideroom_path")
    path_tall = template_map.get("machine_tallroom_path")
    path_big = template_map.get("machine_bigroom_path")

    more_rooms_start = path_start

    if entrance:
        set_room(room_map, 0, path_start, entrance)
        more_rooms_start = path_start + 1
    if path is None:
        if entrance_drop:
            set_room(room_map, 1, path_start, entrance_drop)
            more_rooms_start = path_start + 1
        if path_exit:
            set_room(room_map, 2, path_start, path_exit)
            more_rooms_start = path_start + 1
        if path_exit_notop:
            set_room(room_map, 3, path_start, path_exit_notop)
            more_rooms_start = path_start + 1
    else:
        cw = 1
        set_room(room_map, 1, path_start, path)
        if path_drop:
            cw = 2
            set_room(room_map, 2, path_start, path_drop)
        if entrance_drop:
            set_room(room_map, cw + 1, path_start, entrance_drop)
        big_top = 1
        if path_wide:
            big_top = 2
            set_room(room_map, 0, path_start + 1, path_wide)
        has_big = False
        if path_big:
            has_big = True
            set_room(room_map, 0, path_start + big_top, path_big)
        if path_drop_notop:
            set_room(room_map, 2, path_start + 1, path_drop_notop)
        if path_notop:
            set_room(room_map, 2, path_start + 2, path_notop)
        if path_tall:
            set_room(room_map, 3, path_start + 1, path_tall)
        er, ec = 3, 2
        if not has_big:
            er, ec = 2, 0
        if path_exit:
            set_room(room_map, ec, path_start + er, path_exit)
            ec += 1
        if path_exit_notop:
            set_room(room_map, ec, path_start + er, path_exit_notop)
        more_rooms_start = path_start + er + 1

    olmecship_room = template_map.get("olmecship_room")
    if olmecship_room:
        for i, room in enumerate(room_map[more_rooms_start - 1]):
            if room is None:
                set_room(room_map, i, more_rooms_start - 1, olmecship_room)
                break

    challenge_entrance = template_map.get("challenge_entrance")
    challenge_special = template_map.get("challenge_special")
    challenge_bottom = template_map.get("challenge_bottom")
    entrancer, entrancec = None, None
    if challenge_entrance:
        for i, room in enumerate(room_map[more_rooms_start - 1]):
            if room is None:
                entrancer, entrancec = more_rooms_start - 1, i
                set_room(room_map, i, more_rooms_start - 1, challenge_entrance)
                break
        if entrancer is None:
            entrancer, entrancec = more_rooms_start, 0
            set_room(room_map, 0, more_rooms_start, challenge_entrance)
            more_rooms_start += 1

    bottomr, bottomc = None, None
    if challenge_bottom:
        if entrancer is not None and entrancec is not None:
            set_room(room_map, entrancec, entrancer + 1, challenge_bottom)
            bottomr, bottomc = entrancer + 1, entrancec
            more_rooms_start += 1
        else:
            set_room(room_map, 0, more_rooms_start, challenge_bottom)
            bottomr, bottomc = more_rooms_start, 0
            more_rooms_start += 1

    if challenge_special:
        if bottomc is not None and bottomr is not None:
            set_room(room_map, bottomc < len(room_map[0]) and bottomc + 1 or bottomc - 1, bottomr, challenge_special)
        elif entrancer is not None and entrancec is not None:
            cr, cc = entrancer + 1, entrancec
            if entrancec < len(room_map[entrancer]) and room_map[entrancer][entrancec + 1] is None:
                cr, cc = entrancer, entrancec + 1
            elif entrancec > 0 and room_map[entrancer][entrancec - 1] is None:
                cr, cc = entrancer, entrancec - 1
            set_room(room_map, cc, cr, challenge_special)
            more_rooms_start = cr + 1
        else:
            set_room(room_map, 0, more_rooms_start, challenge_special)
            more_rooms_start += 1

    bigroom_side = template_map.get("machine_bigroom_side")
    wideroom_side = template_map.get("machine_wideroom_side")
    tallroom_side = template_map.get("machine_tallroom_side")
    side = template_map.get("side")

    sideroomsc, sideroomsr = 0, 0
    sider, sidec = 0, 0
    highest_room = 0
    if bigroom_side:
        set_room(room_map, 0, more_rooms_start, bigroom_side)
        sideroomsc = 2
        sideroomsr = 2
        sider, sidec = 0, 2
        highest_room = 2
    if tallroom_side:
        set_room(room_map, sideroomsc, more_rooms_start, tallroom_side)
        sideroomsr = 2
        sideroomsc += 1
        sider, sidec = 0, sideroomsc
        highest_room = 2
    if wideroom_side:
        wider, widec = sideroomsr, 0
        sider, sidec = wider, widec + 2
        if sideroomsc <= 2:
            wider, widec = 0, sideroomsc
            sider, sidec = wider + 1, widec
        if wider + 1 > highest_room:
            highest_room = wider + 1
        set_room(room_map, widec, more_rooms_start + wider, wideroom_side)
    if side:
        set_room(room_map, sidec, more_rooms_start + sider, side)
        if sider + 1 > highest_room:
            highest_room = sider + 1

    more_rooms_start += highest_room

    other_vertical_paired_rooms_to_add = [
        ["idol_top", "idol"],
        ["udjattop", "udjatentrance"],
        ["machine_keyroom", "machine_rewardroom"],
        ["cog_altar_top", "altar"],
        ["oldhunter_keyroom", "oldhunter_rewardroom"],
    ]

    vertical_room_column = 0
    vertical_max_height = 0
    for room_pair in other_vertical_paired_rooms_to_add:
        top_room = template_map.get(room_pair[0])
        r = 0
        if top_room:
            set_room(room_map, vertical_room_column, more_rooms_start, top_room)
            r = 1
            if vertical_max_height == 0:
                vertical_max_height = 1
        bottom_room = template_map.get(room_pair[1])
        if bottom_room:
            if vertical_max_height < r + 1:
                vertical_max_height = r + 1
            set_room(room_map, vertical_room_column, more_rooms_start + r, bottom_room)
        if top_room is not None or bottom_room is not None:
            vertical_room_column += 1

    more_rooms_bottom = more_rooms_start + vertical_max_height - 1

    other_rooms_to_add = [
        "abzu_backdoor",
        "lake_normal",
        "lake_notop",
        "lake_exit",
        "lakeoffire_back_entrance",
        "lakeoffire_back_exit",
        "mothership_entrance",
        "mothership_exit",
        "mothership_coffin",
        "storage_room",
        "moai",
        "coffin_unlockable",
        "coffin_player",
        "coffin_player_vertical",
        "quest_thief2",
        "beehive",
        "beehive_entrance",
        "blackmarket_entrance",
        "blackmarket_exit",
        "blackmarket_coffin",
        "apep",
        "pen_room",
        "ghistshop",
        "empress_grave",
        "vault",
        "shop_entrance_up",
        "shop_entrance_down",
        "diceshop",
        "curioshop",
        "cavemanshop",
        "posse",
        "quest_thief1",
        "room2",
        "passage_horz",
        "passage_vert",
        "passage_turn",
        "ushabti_entrance",
        "ushabti_room",
        "sisters_room",
        "motherstatue_room",
        "crashedship_entrance",
        "crashedship_entrance_notop",
        "anubis_room",
        "oldhunter_cursedroom",
    ]

    for room_name in other_rooms_to_add:
        room = template_map.get(room_name)
        added_room = False
        if room:
            for row in range(more_rooms_start, more_rooms_bottom+1):
                if added_room:
                    break
                if len(room_map) <= row:
                    break
                for col, template_item in enumerate(room_map[row]):
                    if template_item is None:
                        set_room(room_map, col, row, room)
                        added_room = True
                        break

            if not added_room:
                if len(room_map) > 0 and len(room_map[0]) < 3:
                    set_room(room_map, len(room_map[0]), more_rooms_start, room)
                else:
                    more_rooms_start = more_rooms_bottom + 1
                    more_rooms_bottom = more_rooms_start
                    set_room(room_map, 0, more_rooms_start, room)

    return room_map
