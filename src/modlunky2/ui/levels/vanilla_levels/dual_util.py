from modlunky2.ui.levels.shared.tags import TAGS

def make_dual(rows: List[str]):
    new_room_data = []
    new_room_data.append(r"\!dual")
    for row in rows:
        tag_row = False
        new_row = ""
        for tag in TAGS:
            if row.startswith(tag):
                tag_row = True
        if not tag_row:
            new_row = row + " "
            for _char in row:
                new_row += "0"
            new_room_data.append(str(new_row))
        else:
            new_room_data.append(str(row))
    return new_room_data

def remove_dual(rows: List[str]):
    new_room_data = []
    for row in current_room.rows:
        tag_row = False
        new_row = ""
        for tag in TAGS:
            if str(row).startswith(tag):
                tag_row = True
        if not tag_row:
            new_row = str(row).split(" ", 2)[0]
        else:
            if not row.startswith(r"\!dual"):
                new_row = row
        if new_row != "":
            new_room_data.append(str(new_row))

    return new_room_data