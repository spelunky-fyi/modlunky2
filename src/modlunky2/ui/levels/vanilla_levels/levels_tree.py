from dataclasses import dataclass
import logging
import tkinter as tk
from tkinter import ttk
import pyperclip

from modlunky2.config import Config
from modlunky2.ui.widgets import PopupWindow

logger = logging.getLogger(__name__)

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
