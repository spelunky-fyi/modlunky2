from tkinter import ttk

from modlunky2.ui.levels.vanilla_levels.levels_tree import LevelsTree


class LevelListPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        on_edit,
        on_reset_canvas,
        on_room_select,
        modlunky_config,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.levels_tree = LevelsTree(
            self, on_edit, on_reset_canvas, modlunky_config, selectmode="browse"
        )
        self.vsb = ttk.Scrollbar(
            self, orient="vertical", command=self.levels_tree.yview
        )
        self.rowconfigure(0, weight=1)
        self.levels_tree.configure(yscrollcommand=self.vsb.set)
        self.levels_tree.grid(row=0, column=0, sticky="nswe")
        self.vsb.grid(row=0, column=0, sticky="nse")

        self.levels_tree.bind("<ButtonRelease-1>", on_room_select)

    def reset(self):
        self.levels_tree.reset()

    def get_rooms(self):
        return self.levels_tree.get_rooms()

    def set_rooms(self, new_rooms):
        self.levels_tree.set_rooms(new_rooms)

    def get_selected_room(self):
        return self.levels_tree.get_selected_room()

    def replace_selected_room(self, new_room):
        self.levels_tree.replace_selected_room(new_room)

    def get_level_templates(self):
        return self.levels_tree.get_level_templates()

    def get_selected_room_template_name(self):
        return self.levels_tree.get_selected_room_template_name()

    def replace_rooms(self, replacements):
        return self.levels_tree.replace_rooms(replacements)

    def get_setrooms(self):
        return self.levels_tree.get_setrooms()
