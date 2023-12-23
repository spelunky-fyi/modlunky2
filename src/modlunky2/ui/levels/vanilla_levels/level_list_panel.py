from tkinter import ttk

from modlunky2.ui.levels.vanilla_levels.levels_tree import LevelsTree


class LevelListPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        on_edit,
        on_reset_canvas,
        on_add_room,
        on_delete_room,
        on_duplicate_room,
        on_copy_room,
        on_paste_room,
        on_rename_room,
        on_room_select,
        on_create_template,
        modlunky_config,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.levels_tree = LevelsTree(
            self,
            on_edit,
            on_reset_canvas,
            on_add_room,
            on_delete_room,
            on_duplicate_room,
            on_copy_room,
            on_paste_room,
            on_rename_room,
            on_room_select,
            on_create_template,
            modlunky_config,
            selectmode="browse",
        )
        self.vsb = ttk.Scrollbar(
            self, orient="vertical", command=self.levels_tree.yview
        )
        self.rowconfigure(0, weight=1)
        self.levels_tree.configure(yscrollcommand=self.vsb.set)
        self.levels_tree.grid(row=0, column=0, sticky="nswe")
        self.vsb.grid(row=0, column=0, sticky="nse")

    def reset(self):
        self.levels_tree.reset()

    def add_room(self, new_room):
        self.levels_tree.add_room(new_room)

    def set_rooms(self, new_rooms):
        self.levels_tree.set_rooms(new_rooms)

    def get_selected_room(self):
        return self.levels_tree.get_selected_room()
