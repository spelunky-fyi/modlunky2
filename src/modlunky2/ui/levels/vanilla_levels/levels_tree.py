from dataclasses import dataclass
import logging
import tkinter as tk
from tkinter import ttk
import pyperclip
from typing import List

from modlunky2.config import Config
from modlunky2.levels.level_templates import Chunk, LevelTemplate, LevelTemplates, TemplateSetting
from modlunky2.ui.widgets import PopupWindow
from modlunky2.ui.levels.shared.tags import TAGS

logger = logging.getLogger(__name__)

@dataclass
class LevelsTreeRoom:
    name: str
    rows: List[str]

@dataclass
class LevelsTreeTemplate:
    name: str
    rooms: List[LevelsTreeRoom]

@dataclass
class RoomType:
    name: str
    x_size: int
    y_size: int

ROOM_TYPES = {
    f"{room_type.name}: {room_type.x_size}x{room_type.y_size}": room_type
    for room_type in [
        RoomType("normal", 10, 8),
        RoomType("machine_wideroom", 20, 8),
        RoomType("machine_tallroom", 10, 16),
        RoomType("machine_bigroom", 20, 16),
        RoomType("coffin_frog", 10, 16),
        RoomType("ghistroom", 5, 5),
        RoomType("feeling", 20, 16),
        RoomType("chunk_ground", 5, 3),
        RoomType("chunk_door", 6, 3),
        RoomType("chunk_air", 5, 3),
        RoomType("cache", 5, 5),
    ]
}
DEFAULT_ROOM_TYPE = "normal"

class LevelsTree(ttk.Treeview):
    def __init__(self, parent, on_edit, reset_canvas, config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.config = config
        self.on_edit = on_edit
        self.reset_canvas = reset_canvas

        # two different context menus to show depending on what is clicked (room or room list)
        self.popup_menu_child = tk.Menu(self, tearoff=0)
        self.popup_menu_parent = tk.Menu(self, tearoff=0)

        self.popup_menu_child.add_command(label="Rename Room", command=self.rename)
        self.popup_menu_child.add_command(
            label="Duplicate Room", command=self.duplicate
        )
        self.popup_menu_child.add_command(label="Copy Room", command=self.copy)
        self.popup_menu_child.add_command(label="Paste Room", command=self.paste)
        self.popup_menu_child.add_command(
            label="Delete Room", command=self.delete_selected
        )
        self.popup_menu_child.add_command(label="Add Room", command=self.add_room)
        self.popup_menu_parent.add_command(label="Add Room", command=self.add_room)
        self.popup_menu_parent.add_command(label="Paste Room", command=self.paste)

        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            item_iid = self.selection()[0]
            parent_iid = self.parent(item_iid)  # gets selected room
            if parent_iid:  # if actual room is clicked
                self.popup_menu_child.tk_popup(event.x_root, event.y_root, 0)
            else:  # if room list is clicked
                self.popup_menu_parent.tk_popup(event.x_root, event.y_root, 0)

            self.on_edit()
        except Exception:  # pylint: disable=broad-except
            self.popup_menu_child.grab_release()
            self.popup_menu_parent.grab_release()

    def rename(self):
        for _ in self.selection()[::-1]:
            self.rename_dialog()

    def duplicate(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            item_name = self.item(item_iid)["text"]
            room_data = self.item(item_iid, option="values")
            self.insert(parent_iid, "end", text=item_name + " COPY", values=room_data)

    def copy(self):
        item = self.selection()[0]
        copy_text = str(self.item(item, option="text"))
        copy_values_raw = self.item(item, option="values")
        copy_values = ""
        for line in copy_values_raw:
            copy_values += str(line) + "\n"
        logger.debug("copied %s", copy_values)
        pyperclip.copy(copy_text + "\n" + copy_values)

    def paste(self):
        data = pyperclip.paste().encode("utf-8").decode("cp1252")

        paste_text = data.split("\n", 1)[0]
        paste_values_raw = data.split("\n", 1)[1]

        paste_values = []
        paste_values = paste_values_raw.split("\n")

        for item in paste_values:
            if item == "":
                paste_values.remove(item)  # removes empty line
        logger.debug("pasted %s", paste_values)

        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            self.insert(parent_iid, "end", text=paste_text, values=paste_values)
        else:
            self.insert(item_iid, "end", text=paste_text, values=paste_values)

    def delete_selected(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            msg_box = tk.messagebox.askquestion(
                "Delete Room?",
                "Are you sure you want to delete "
                + self.item(item_iid)["text"]
                + "?"
                + "\nThis won't be recoverable.",
                icon="warning",
            )
            if msg_box == "yes":
                self.delete(item_iid)
                self.reset_canvas()

    def add_room(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        parent = None
        if parent_iid:
            parent = parent_iid
        else:
            parent = item_iid

        # First check if a blank space was selected
        entry_index = self.focus()
        if entry_index == "":
            return

        # Set default prompt based on parent name
        roomsize_key = "normal: 10x8"
        parent_room_type = self.item(parent)["text"]
        for room_size_text, room_type in ROOM_TYPES.items():
            if parent_room_type.startswith(room_type.name):
                roomsize_key = room_size_text
                break

        room_type = ROOM_TYPES[roomsize_key]
        new_room_data = ["0" * room_type.x_size] * room_type.y_size
        self.insert(parent, "end", text="new room", values=new_room_data)

    def rename_dialog(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if not parent_iid:
            return

        # First check if a blank space was selected
        entry_index = self.focus()
        if entry_index == "":
            return

        win = PopupWindow("Edit Name", self.config)

        item_name = ""
        item_name = self.item(item_iid)["text"]

        col1_lbl = ttk.Label(win, text="Name: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, item_name)  # Default to rooms current name
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="nswe")

        def update_then_destroy():
            if self.confirm_entry(col1_ent.get()):
                win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=1, column=0, columnspan=2, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=2, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Ok", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

    def confirm_entry(self, entry1):
        if entry1 != "":
            self.item(self.focus(), text=entry1)
            return True
        else:
            return False


    def reset(self):
        for i in self.get_children():
            self.delete(i)

    def get_rooms(self):
        level_templates = []
        for room_parent in self.get_children():
            rooms = []
            for room in self.get_children(room_parent):
                room_name = self.item(room, option="text")
                room_rows = self.item(room, option="values")
                rooms.append(LevelsTreeRoom(room_name, room_rows))
            level_templates.append(LevelsTreeTemplate(self.item(room_parent, option="text"), rooms))
        return level_templates

    def replace_rooms(self, replacements):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)
        selected_parent_index = None
        if parent_iid:
            selected_parent_index = self.index(parent_iid)
        selected_item_index = None
        if item_iid:
            selected_item_index = self.index(item_iid)

        for parent_index, parent in enumerate(self.get_children()):
            for child_index, child in enumerate(self.get_children(parent)):
                self.delete(child)
                if len(replacements) > parent_index and len(replacements[parent_index].rooms) > child_index:
                    room = replacements[parent_index].rooms[child_index]
                    new_child = self.insert(
                        parent,
                        child_index,
                        text=room.name,
                        values=room.rows,
                    )
                    if selected_parent_index == parent_index and selected_item_index == child_index:
                        self.selection_set(new_child)
                        selected_child = new_child

        return selected_child

    def get_selected_room(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)
        if parent_iid:
            room_name = self.item(item_iid, option="text")
            room_rows = self.item(item_iid, option="values")
            return LevelsTreeRoom(room_name, room_rows)
        return None

    def replace_selected_room(self, replacement):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)
        if parent_iid:
            edited = self.insert(
                parent_iid,
                self.index(item_iid),
                text = replacement.name,
                values = replacement.rows,
            )
            self.delete(item_iid)
            self.selection_set(edited)

    def get_level_templates(self):
        level_templates = LevelTemplates()
        for room_parent in self.get_children():
            template_chunks = []
            room_list_name = self.item(room_parent)["text"].split(" ", 1)[0]
            room_list_comment = ""
            if len(self.item(room_parent)["text"].split("//", 1)) > 1:
                room_list_comment = self.item(room_parent)["text"].split("//", 1)[1]
            for room in self.get_children(room_parent):
                room_data = self.item(room, option="values")
                room_name = self.item(room)["text"]
                room_foreground = []
                room_background = []
                room_settings = []

                for line in room_data:
                    row = []
                    back_row = []
                    tag_found = False
                    background_found = False
                    for tag in TAGS:
                        if str(line) == str(tag): # This line is a tag.
                            tag_found = True
                            break
                    if not tag_found:
                        for char in str(line):
                            if not background_found and str(char) != " ":
                                row.append(str(char))
                            elif background_found and str(char) != " ":
                                back_row.append(str(char))
                            elif char == " ":
                                background_found = True
                    else:
                        room_settings.append(
                            TemplateSetting(str(line.split("!", 1)[1]))
                        )
                        logger.debug("FOUND %s", line.split("!", 1)[1])

                    if not tag_found:
                        room_foreground.append(row)
                        if back_row != []:
                            room_background.append(back_row)

                template_chunks.append(
                    Chunk(
                        comment=room_name,
                        settings=room_settings,
                        foreground=room_foreground,
                        background=room_background,
                    )
                )
            level_templates.set_obj(
                LevelTemplate(
                    name=room_list_name,
                    comment=room_list_comment,
                    chunks=template_chunks,
                )
            )

        return level_templates
