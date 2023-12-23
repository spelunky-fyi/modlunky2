from dataclasses import dataclass
import logging
from PIL import Image, ImageTk
import pyperclip
import tkinter as tk
from tkinter import ttk
from typing import List

from modlunky2.config import Config
from modlunky2.constants import BASE_DIR
from modlunky2.levels.level_templates import (
    Chunk,
    LevelTemplate,
    LevelTemplates,
    TemplateSetting,
)
from modlunky2.ui.widgets import PopupWindow
from modlunky2.ui.levels.shared.tags import TAGS
from modlunky2.ui.levels.shared.setrooms import Setroom, MatchedSetroom

logger = logging.getLogger(__name__)


class LevelsTree(ttk.Treeview):
    def __init__(
        self,
        parent,
        on_edit,
        reset_canvas,
        on_add_room,
        on_delete_room,
        on_duplicate_room,
        on_copy_room,
        on_paste_room,
        on_rename_room,
        on_select_room,
        on_create_template,
        config: Config,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.config = config
        self.on_edit = on_edit
        self.reset_canvas = reset_canvas
        self.on_add_room = on_add_room
        self.on_delete_room = on_delete_room
        self.on_duplicate_room = on_duplicate_room
        self.on_copy_room = on_copy_room
        self.on_paste_room = on_paste_room
        self.on_rename_room = on_rename_room
        self.on_select_room = on_select_room
        self.on_create_template = on_create_template

        self.rooms = []

        self.icon_add = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/add.png").resize((20, 20))
        )

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
        self.bind("<ButtonRelease-1>", self.click)

    def click(self, event):
        selection = self.selection()
        if len(selection) == 0:
            return
        item_iid = selection[0]
        parent_iid = self.parent(item_iid)
        if parent_iid:
            self.on_select_room()
        elif self.index(item_iid) == len(self.rooms):
            self.create_template_dialog()

    def create_template_dialog(self):
        win = PopupWindow("Create Template", self.config)

        row = 0
        values_frame = tk.Frame(win)
        values_frame.grid(row=row, column=0, sticky="nw")
        row = row + 1

        values_row = 0
        name_lbl = ttk.Label(values_frame, text="Name: ")
        name_ent = ttk.Entry(values_frame)
        # name_ent.insert(0, "New_Pack")  # Default to rooms current name
        name_lbl.grid(row=values_row, column=0, pady=2, sticky="e")
        name_ent.grid(row=values_row, column=1, pady=2, sticky="we")

        values_row += 1

        comment_lbl = ttk.Label(values_frame, text="Comment: ")
        comment_ent = ttk.Entry(values_frame)
        # name_ent.insert(0, "New_Pack")  # Default to rooms current name
        comment_lbl.grid(row=values_row, column=0, pady=2, sticky="e")
        comment_ent.grid(row=values_row, column=1, pady=2, sticky="we")

        values_row += 1

        size_type_label = tk.Label(values_frame, text="Size in: ")
        size_type_label.grid(row=values_row, column=0, sticky="e", pady=2)

        size_type_combobox = ttk.Combobox(values_frame, height=25)
        size_type_combobox.set("Subrooms")
        size_type_combobox.grid(row=values_row, column=1, sticky="we", pady=2)
        size_type_combobox["state"] = "readonly"
        size_type_combobox["values"] = ["Subrooms", "Tiles"]
        size_type_combobox.current(0)

        values_row += 1

        width_label = tk.Label(values_frame, text="Width: ")
        width_label.grid(row=values_row, column=0, sticky="e", pady=2)

        width_ent = ttk.Entry(values_frame)
        width_ent.insert(0, "1")
        width_ent.grid(row=values_row, column=1, sticky="we", pady=2)

        values_row += 1

        height_label = tk.Label(values_frame, text="Height: ")
        height_label.grid(row=values_row, column=0, sticky="e", pady=2)

        height_ent = ttk.Entry(values_frame)
        height_ent.insert(0, "1")
        height_ent.grid(row=values_row, column=1, sticky="we", pady=2)

        values_row += 1

        error_lbl = tk.Label(values_frame, text="", fg="red")
        error_lbl.grid(row=values_row, column=0, columnspan=2)
        error_lbl.grid_remove()

        values_row += 1

        def update_then_destroy_pack():
            template_name = ""
            for char in str(name_ent.get()):
                if str(char) != " ":
                    template_name += str(char)
                else:
                    template_name += "_"

            comment = comment_ent.get()
            if len(comment) == 0:
                comment = None

            width_str = width_ent.get()
            height_str = height_ent.get()
            if not width_str.isdecimal():
                error_lbl.grid()
                error_lbl["text"] = "Invalid width."
                return

            if not height_str.isdecimal():
                error_lbl.grid()
                error_lbl["text"] = "Invalid height."
                return

            width = int(width_str)
            height = int(height_str)
            if size_type_combobox.current() != 1:
                width *= 10
                height *= 8

            error_lbl.grid_remove()
            if width == 0:
                error_lbl.grid()
                error_lbl["text"] = "Invalid width."
                return

            if height == 0:
                error_lbl.grid()
                error_lbl["text"] = "Invalid height."
                return

            if len(template_name) == 0:
                error_lbl.grid()
                error_lbl["text"] = "Name the template."
                return

            success, error_message, new_room = self.on_create_template(
                template_name, comment, width, height
            )
            if success:
                # self.delete(len(self.rooms))

                room_display_name = str(new_room.name)
                if new_room.comment is not None and len(str(new_room.comment)) > 0:
                    room_display_name += "   // " + new_room.comment
                new_template_item = self.insert(
                    "", len(self.rooms), text=room_display_name
                )
                for room in new_room.rooms:
                    child_id = self.insert(
                        new_template_item, "end", text=room.name or "room"
                    )
                    self.focus(child_id)
                    self.selection_set(child_id)

                self.item(new_template_item, open=True)
                self.rooms.append(new_room)
                self.on_select_room()
                win.destroy()
            else:
                error_lbl.grid()
                error_lbl["text"] = error_message or "Error creating template."
                return
            # name_ent.delete(0, "end")
            # name_ent.insert(0, pack_name)
            # if not os.path.isdir(self.packs_path / str(name_ent.get())):
            #     os.mkdir(self.packs_path / str(name_ent.get()))
            #     self.load_packs()
            #     win.destroy()
            # else:
            #     logger.warning("Pack name taken")
            #     name_ent.delete(0, "end")
            #     name_ent.insert(0, "Name Taken")

        separator = ttk.Separator(win)
        separator.grid(row=row, column=0, columnspan=2, pady=5, sticky="news")

        row = row + 1

        buttons = ttk.Frame(win)
        buttons.grid(row=row, column=0, sticky="news")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Create", command=update_then_destroy_pack)
        ok_button.grid(row=0, column=0, pady=5, sticky="news")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="news")

        row = row + 1

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
            item_index = self.index(item_iid)
            parent_index = self.index(parent_iid)
            new_room = self.on_duplicate_room(parent_index, item_index)
            self.insert(parent_iid, "end", text=new_room.name or "room")

    def copy(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            item_index = self.index(item_iid)
            parent_index = self.index(parent_iid)
            self.on_copy_room(parent_index, item_index)

    def paste(self):
        item_iid = self.selection()[0]
        if item_iid:
            item_index = self.index(item_iid)
            parent_iid = self.parent(item_iid)  # gets selected room
            if parent_iid:
                item_index = self.index(parent_iid)
                item_iid = parent_iid
            new_room = self.on_paste_room(item_index)
            self.insert(item_iid, "end", text=new_room.name or "room")

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
                parent_index = self.index(parent_iid)
                item_index = self.index(item_iid)
                self.on_delete_room(parent_index, item_index)
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

        new_room = self.on_add_room(self.index(parent))
        self.insert(parent, "end", text=new_room.name or "room")

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

        name_lbl = ttk.Label(win, text="Name: ")
        name_ent = ttk.Entry(win)
        name_ent.insert(0, item_name)  # Default to rooms current name
        name_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        name_ent.grid(row=0, column=1, padx=2, pady=2, sticky="nswe")

        def update_then_destroy():
            if self.confirm_entry(name_ent.get()):
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
            item_iid = self.selection()[0]
            parent_iid = self.parent(item_iid)  # gets selected room
            if parent_iid:
                item_index = self.index(item_iid)
                parent_index = self.index(parent_iid)
                self.on_rename_room(parent_index, item_index, entry1)
            return True
        else:
            return False

    def reset(self):
        for i in self.get_children():
            self.delete(i)

    def set_rooms(self, rooms):
        self.rooms = [room for room in rooms]
        for room in rooms:
            room_display_name = str(room.name)
            if len(str(room.comment)) > 0:
                room_display_name += "   // " + room.comment
            entry = self.insert("", "end", text=room_display_name)
            for layout in room.rooms:
                self.insert(entry, "end", text=layout.name or "room")

        self.insert("", "end", text="Create new template", image=self.icon_add)

    def get_selected_room(self):
        selection = self.selection()
        if len(selection) == 0:
            return None, None
        item_iid = selection[0]
        parent_iid = self.parent(item_iid)
        if parent_iid:
            return self.index(parent_iid), self.index(item_iid)
        return None, None
