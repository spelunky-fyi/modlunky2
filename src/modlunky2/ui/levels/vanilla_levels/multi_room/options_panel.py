import tkinter as tk
from tkinter import ttk

from modlunky2.config import Config, CustomRoomMap, CustomRoomMapSegment
from modlunky2.levels.level_templates import TemplateSetting
from modlunky2.ui.levels.vanilla_levels.multi_room.reversed_rooms import REVERSED_ROOMS
from modlunky2.ui.widgets import PopupWindow, ScrollableFrameLegacy


class RoomOptions(ttk.Frame):
    def __init__(
        self,
        parent,
        on_select_template,
        on_clear_template,
        on_select_room,
        on_flip_setting,
        on_duplicate_room,
        on_rename_room,
        on_delete_room,
        on_update_reverse_layers,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)

        setting_row = 0

        self.on_select_template = on_select_template
        self.on_clear_template = on_clear_template
        self.on_select_room = on_select_room
        self.on_flip_setting = on_flip_setting
        self.on_duplicate_room = on_duplicate_room
        self.on_rename_room = on_rename_room
        self.on_delete_room = on_delete_room
        self.on_update_reverse_layers = on_update_reverse_layers

        self.current_template_map_index = None
        self.current_template_row = None
        self.current_template_column = None
        self.current_template_item = None

        self.columnconfigure(0, weight=1)

        template_label = tk.Label(self, text="Room Type:")
        template_label.grid(row=setting_row, column=0, sticky="w")

        setting_row += 1

        self.template_combobox = ttk.Combobox(self, height=25)
        self.template_combobox.grid(row=setting_row, column=0, sticky="nsw")
        self.template_combobox["values"] = ["None"]
        self.template_combobox.set("None")
        self.template_combobox["state"] = "readonly"
        self.template_combobox.bind(
            "<<ComboboxSelected>>", lambda _: self.select_template()
        )

        setting_row += 1

        self.template_container = tk.Frame(self)
        self.template_container.grid(row=setting_row, column=0, sticky="news")

        template_setting_row = 0

        self.reverse_layers_container = tk.Frame(self.template_container)
        self.reverse_layers_container.grid(
            row=template_setting_row, column=0, sticky="news"
        )

        self.var_reverse_layers = tk.IntVar()
        self.var_reverse_layers.set(True)
        self.checkbox_reverse_layers = ttk.Checkbutton(
            self.reverse_layers_container,
            text="Reverse Layers",
            var=self.var_reverse_layers,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_reverse_layers,
        )

        self.checkbox_reverse_layers.grid(row=0, column=0, sticky="news")

        wrap = 350
        self.reverse_layers_description_on = tk.Label(
            self.reverse_layers_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="The layers of this room are being reversed to match with the setrooms connected to it. Turn this off to disable this behavior.",
        )
        self.reverse_layers_description_off = tk.Label(
            self.reverse_layers_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="The layers of this room can be reversed to match with the setrooms connected to it. Turn this on to enable this behavior.",
        )
        self.reverse_layers_description_on.grid(row=1, column=0, sticky="nws")
        self.reverse_layers_description_off.grid(row=2, column=0, sticky="nws")

        template_setting_row += 1

        room_label = tk.Label(self.template_container, text="Room:")
        room_label.grid(row=template_setting_row, column=0, sticky="w")

        template_setting_row += 1

        self.room_combobox = ttk.Combobox(self.template_container, height=25)
        self.room_combobox.grid(row=template_setting_row, column=0, sticky="nsw")
        self.room_combobox["values"] = []
        self.room_combobox.set("")
        self.room_combobox["state"] = "readonly"
        self.room_combobox.bind("<<ComboboxSelected>>", lambda _: self.select_room())

        template_setting_row += 1

        buttons_container = tk.Frame(self.template_container)
        buttons_container.grid(row=template_setting_row, column=0, sticky="news")

        self.configure_reverse_rooms_description()

        template_setting_row += 1

        duplicate_button = ttk.Button(
            buttons_container, text="Duplicate", command=self.duplicate_room
        )
        duplicate_button.grid(row=0, column=1, pady=5, sticky="news")

        rename_button = ttk.Button(
            buttons_container, text="Rename", command=self.rename_room
        )
        rename_button.grid(row=0, column=0, pady=5, sticky="news")

        delete_button = ttk.Button(
            buttons_container, text="Delete", command=self.delete_room
        )
        delete_button.grid(row=0, column=2, pady=5, sticky="news")

        self.room_settings_container = tk.Frame(self.template_container)
        self.room_settings_container.grid(
            row=template_setting_row, column=0, sticky="news"
        )

        template_setting_row += 1

        self.var_ignore = tk.IntVar()
        self.var_flip = tk.IntVar()
        self.var_only_flip = tk.IntVar()
        self.var_dual = tk.IntVar()
        self.var_rare = tk.IntVar()
        self.var_hard = tk.IntVar()
        self.var_liquid = tk.IntVar()
        self.var_purge = tk.IntVar()
        self.checkbox_ignore = ttk.Checkbutton(
            self.room_settings_container,
            text="Ignore",
            var=self.var_ignore,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_ignore,
        )
        self.checkbox_flip = ttk.Checkbutton(
            self.room_settings_container,
            text="Flip",
            var=self.var_flip,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_flip,
        )
        self.checkbox_only_flip = ttk.Checkbutton(
            self.room_settings_container,
            text="Only Flip",
            var=self.var_only_flip,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_only_flip,
        )
        self.checkbox_rare = ttk.Checkbutton(
            self.room_settings_container,
            text="Rare",
            var=self.var_rare,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_rare,
        )
        self.checkbox_hard = ttk.Checkbutton(
            self.room_settings_container,
            text="Hard",
            var=self.var_hard,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_hard,
        )
        self.checkbox_liquid = ttk.Checkbutton(
            self.room_settings_container,
            text="Optimize Liquids",
            var=self.var_liquid,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_liquid,
        )
        self.checkbox_purge = ttk.Checkbutton(
            self.room_settings_container,
            text="Purge",
            var=self.var_purge,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_purge,
        )
        self.checkbox_dual = ttk.Checkbutton(
            self.room_settings_container,
            text="Dual",
            var=self.var_dual,
            onvalue=1,
            offvalue=0,
            command=self.on_flip_dual,
        )

        label_dual = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="Whether this room has a backlayer.",
        )
        label_ignore = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="If checked, this room will never appear in-game.",
        )
        label_purge = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="If checked, other rooms of this same template which were already loaded (eg, loaded from another file or appear first in this file) will not appear in-game when this room's file is loaded.",
        )
        label_rare = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="If checked, this room has a 5% chance of being used.",
        )
        label_hard = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="If checked, this room only appears in X-3 and X-4.",
        )
        label_liquid = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="Mark this room as containing liquid to optimize the liquid engine.",
        )
        label_flip = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="Creates two rooms, one which is horizontally flipped from the original.",
        )
        label_only_flip = tk.Label(
            self.room_settings_container,
            wraplength=wrap,
            justify=tk.LEFT,
            text="Like flip, but the original room is ignored.",
        )

        self.checkbox_dual.grid(row=0, column=0, sticky="w")
        label_dual.grid(row=1, column=0, sticky="nws")
        self.checkbox_ignore.grid(row=2, column=0, sticky="w")
        label_ignore.grid(row=3, column=0, sticky="nws")
        self.checkbox_purge.grid(row=4, column=0, sticky="w")
        label_purge.grid(row=5, column=0, sticky="nws")
        self.checkbox_rare.grid(row=6, column=0, sticky="w")
        label_rare.grid(row=7, column=0, sticky="nws")
        self.checkbox_hard.grid(row=8, column=0, sticky="w")
        label_hard.grid(row=9, column=0, sticky="nws")
        self.checkbox_liquid.grid(row=10, column=0, sticky="w")
        label_liquid.grid(row=11, column=0, sticky="nws")
        self.checkbox_flip.grid(row=12, column=0, sticky="w")
        label_flip.grid(row=13, column=0, sticky="nws")
        self.checkbox_only_flip.grid(row=14, column=0, sticky="w")
        label_only_flip.grid(row=15, column=0, sticky="nws")

        self.columnconfigure(0, weight=1)

    def reset(self):
        self.current_template_map_index = None
        self.current_template_row = None
        self.current_template_column = None
        self.current_template_item = None
        self.template_container.grid_remove()
        self.clear_templates()

    def configure_reverse_rooms_container(self):
        if self.current_template_item is None:
            return
        if self.current_template_item.template.name in REVERSED_ROOMS:
            self.reverse_layers_container.grid()
        else:
            self.reverse_layers_container.grid_remove()

    def configure_reverse_rooms_description(self):
        if self.reverse_layers():
            self.reverse_layers_description_on.grid()
            self.reverse_layers_description_off.grid_remove()
        else:
            self.reverse_layers_description_on.grid_remove()
            self.reverse_layers_description_off.grid()

    def on_flip_reverse_layers(self):
        self.configure_reverse_rooms_description()
        self.on_update_reverse_layers(self.reverse_layers())

    def select_template(self):
        template_index = self.template_combobox.current()

        if template_index == 0:
            self.clear_templates()
            self.on_clear_template(
                self.current_template_map_index,
                self.current_template_row,
                self.current_template_column,
            )
        else:
            self.on_select_template(
                template_index - 1,
                self.current_template_map_index,
                self.current_template_row,
                self.current_template_column,
            )

    def select_room(self):
        room_index = self.room_combobox.current()
        self.on_select_room(
            room_index,
            self.current_template_map_index,
            self.current_template_row,
            self.current_template_column,
        )

    def duplicate_room(self):
        self.on_duplicate_room(
            self.current_template_map_index,
            self.current_template_row,
            self.current_template_column,
        )

    def rename_room(self):
        self.on_rename_room(
            self.current_template_map_index,
            self.current_template_row,
            self.current_template_column,
        )

    def delete_room(self):
        self.on_delete_room(
            self.current_template_map_index,
            self.current_template_row,
            self.current_template_column,
        )

    def clear_templates(self):
        self.template_combobox["values"] = ["None"]
        self.template_combobox.set("None")
        self.room_combobox["values"] = []
        self.room_combobox.set("")

    def set_templates(self, templates):
        self.template_combobox["values"] = ["None"] + [
            template.name for template in templates
        ]
        self.current_template_item = None
        self.configure_reverse_rooms_container()

    def set_current_template(self, template, map_index, row, column):
        self.current_template_map_index = map_index
        self.current_template_item = template
        self.current_template_row = row
        self.current_template_column = column
        if template:
            self.configure_reverse_rooms_container()
            self.template_combobox.set(template.template.name)
            self.room_combobox["values"] = [
                room.name or "room " + str(index + 1)
                for index, room in enumerate(template.template.rooms)
            ] + ["Create New"]
            self.room_combobox.set(
                template.room_chunk.name or "room " + str(template.room_index + 1)
            )
            self.room_combobox.current(template.room_index)
            self.template_container.grid()

            current_settings = template.room_chunk.settings
            self.set_dual(TemplateSetting.DUAL in current_settings)
            self.set_flip(TemplateSetting.FLIP in current_settings)
            self.set_purge(TemplateSetting.PURGE in current_settings)
            self.set_only_flip(TemplateSetting.ONLYFLIP in current_settings)
            self.set_ignore(TemplateSetting.IGNORE in current_settings)
            self.set_rare(TemplateSetting.RARE in current_settings)
            self.set_hard(TemplateSetting.HARD in current_settings)
            self.set_liquid(TemplateSetting.LIQUID in current_settings)
        else:
            self.set_empty_cell(map_index, row, column)

    def set_empty_cell(self, map_index, row, column):
        self.current_template_map_index = map_index
        self.current_template_row = row
        self.current_template_column = column
        self.template_combobox.set("None")
        self.template_container.grid_remove()

    def flip_setting(self, setting, value):
        self.on_flip_setting(
            setting,
            value,
            self.current_template_map_index,
            self.current_template_row,
            self.current_template_column,
        )

    def on_flip_ignore(self):
        self.flip_setting(TemplateSetting.IGNORE, self.ignore())

    def on_flip_liquid(self):
        self.flip_setting(TemplateSetting.LIQUID, self.liquid())

    def on_flip_hard(self):
        self.flip_setting(TemplateSetting.HARD, self.hard())

    def on_flip_rare(self):
        self.flip_setting(TemplateSetting.RARE, self.rare())

    def on_flip_flip(self):
        self.flip_setting(TemplateSetting.FLIP, self.flip())

    def on_flip_only_flip(self):
        self.flip_setting(TemplateSetting.ONLYFLIP, self.only_flip())

    def on_flip_purge(self):
        self.flip_setting(TemplateSetting.PURGE, self.purge())

    def on_flip_dual(self):
        self.flip_setting(TemplateSetting.DUAL, self.dual())

    def reverse_layers(self):
        return int(self.var_reverse_layers.get()) == 1

    def ignore(self):
        return int(self.var_ignore.get()) == 1

    def liquid(self):
        return int(self.var_liquid.get()) == 1

    def hard(self):
        return int(self.var_hard.get()) == 1

    def rare(self):
        return int(self.var_rare.get()) == 1

    def flip(self):
        return int(self.var_flip.get()) == 1

    def only_flip(self):
        return int(self.var_only_flip.get()) == 1

    def purge(self):
        return int(self.var_purge.get()) == 1

    def dual(self):
        return int(self.var_dual.get()) == 1

    def set_ignore(self, ignore):
        self.var_ignore.set(ignore and 1 or 0)

    def set_liquid(self, liquid):
        self.var_liquid.set(liquid and 1 or 0)

    def set_hard(self, hard):
        self.var_hard.set(hard and 1 or 0)

    def set_rare(self, rare):
        self.var_rare.set(rare and 1 or 0)

    def set_flip(self, flip):
        self.var_flip.set(flip and 1 or 0)

    def set_only_flip(self, only_flip):
        self.var_only_flip.set(only_flip and 1 or 0)

    def set_purge(self, purge):
        self.var_purge.set(purge and 1 or 0)

    def set_dual(self, dual):
        self.var_dual.set(dual and 1 or 0)


class OptionsPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config: Config,
        zoom_level,
        on_update_hide_grid_lines,
        on_update_hide_room_lines,
        on_update_zoom_level,
        on_select_layout,
        on_change_template_at,
        on_clear_template,
        on_select_room,
        on_flip_setting,
        on_duplicate_room,
        on_rename_room,
        on_delete_room,
        on_update_reverse_layers,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_update_hide_grid_lines = on_update_hide_grid_lines
        self.on_update_hide_room_lines = on_update_hide_room_lines
        self.on_update_zoom_level = on_update_zoom_level
        self.on_select_layout = on_select_layout
        self.on_change_template_at = on_change_template_at
        self.on_clear_template = on_clear_template
        self.on_select_room = on_select_room
        self.on_flip_setting = on_flip_setting
        self.on_duplicate_room = on_duplicate_room
        self.on_rename_room = on_rename_room
        self.on_delete_room = on_delete_room
        self.on_update_reverse_layers = on_update_reverse_layers

        self.columnconfigure(0, minsize=10)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, minsize=10)
        self.rowconfigure(0, weight=1)

        self.room_map = []
        self.templates = []
        self.lvl = None

        self.button_for_selected_room = None
        self.button_for_selected_empty_room = None

        # The tile palettes are loaded into here as buttons with their image
        # as a tile and text as their value to grab when needed.
        self.scrollview = ScrollableFrameLegacy(self, text="", width=50)
        self.scrollview.scrollable_frame["width"] = 50
        self.scrollview.grid(row=0, column=1, sticky="news")

        settings_row = 0

        # Checkbox to toggle the visibility of the grid lines.
        hide_grid_var = tk.IntVar()
        hide_grid_var.set(False)

        def toggle_hide_grid():
            nonlocal hide_grid_var

            self.on_update_hide_grid_lines(hide_grid_var.get())

        settings_row += 1
        tk.Checkbutton(
            self.scrollview.scrollable_frame,
            text="Hide grid lines",
            variable=hide_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_grid,
        ).grid(row=settings_row, column=0, sticky="nw", pady=5)

        # Checkbox to toggle the visibility of the grid lines on room boundaries.
        hide_room_grid_var = tk.IntVar()
        hide_room_grid_var.set(False)

        def toggle_hide_room_grid():
            nonlocal hide_room_grid_var
            self.on_update_hide_room_lines(hide_room_grid_var.get())

        settings_row += 1
        tk.Checkbutton(
            self.scrollview.scrollable_frame,
            text="Hide room lines",
            variable=hide_room_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_room_grid,
        ).grid(row=settings_row, column=0, sticky="nw", pady=5)

        settings_row += 1
        grid_size_frame = tk.Frame(self.scrollview.scrollable_frame)
        grid_size_frame.grid(row=settings_row, column=0, sticky="nw", pady=5)
        grid_size_frame.columnconfigure(0, weight=1)
        grid_size_var = tk.StringVar()
        grid_size_var.set(str(zoom_level))
        grid_size_label_frame = tk.Frame(grid_size_frame)
        grid_size_label_frame.grid(row=0, column=0, sticky="nw")

        grid_size_header_label = tk.Label(grid_size_label_frame, text="Zoom:")
        grid_size_header_label.grid(row=0, column=0, sticky="nwe")
        grid_size_label = tk.Label(grid_size_label_frame, textvariable=grid_size_var)
        grid_size_label.grid(row=0, column=1, sticky="nw")

        grid_size_scale = tk.Scale(
            grid_size_frame,
            from_=10,
            to=200,
            orient=tk.HORIZONTAL,
            variable=grid_size_var,
            length=370,
            showvalue=False,
        )
        grid_size_scale.grid(row=1, column=0, sticky="nwe")

        def update_grid_size(_):
            self.on_update_zoom_level(int(grid_size_var.get()))

        grid_size_scale["command"] = update_grid_size
        self.grid_size_var = grid_size_var

        settings_row += 1

        self.layout_frame = tk.Frame(self.scrollview.scrollable_frame)
        self.layout_frame.grid(row=settings_row, column=0, sticky="news", padx=10, pady=10)

        self.layout_label = tk.Label(self.layout_frame, text="Layout:")
        self.layout_label.grid(row=0, column=0, sticky="w")


        self.layout_combobox = ttk.Combobox(self.layout_frame, height=25)
        self.layout_combobox.grid(row=0, column=1, sticky="nsw", padx=(0, 10))
        self.layout_combobox["values"] = ["Default"]
        self.layout_combobox.set("Default")
        self.layout_combobox["state"] = "readonly"
        self.layout_combobox.bind(
            "<<ComboboxSelected>>", lambda _: self.select_layout()
        )

        self.layout_combobox.grid_remove()
        self.layout_label.grid_remove()

        self.save_layout_button = tk.Button(self.layout_frame, text="Save layout", command=self.save_room_map)
        self.save_layout_button.grid(row=0, column=2, sticky="w")
        self.save_layout_button.grid_remove()
        self.layout_frame.grid_remove()

        settings_row += 1

        self.room_type_frame = tk.Frame(self.scrollview.scrollable_frame)
        self.room_type_frame.grid(
            row=settings_row, column=0, sticky="news", padx=10, pady=10
        )

        self.room_view_size = 30
        self.room_view_padding = 5

        for n in range(10):
            self.room_type_frame.columnconfigure(n * 2, minsize=self.room_view_size)
            if n != 0:
                self.room_type_frame.columnconfigure(
                    n * 2 - 1, minsize=self.room_view_padding
                )

        self.room_buttons = []
        self.edge_frames = []

        settings_row += 1

        self.room_options = RoomOptions(
            self.scrollview.scrollable_frame,
            self.update_room_map_template,
            self.clear_template,
            self.on_select_room,
            self.on_flip_setting,
            self.on_duplicate_room,
            self.on_rename_room,
            self.on_delete_room,
            self.on_update_reverse_layers,
        )
        self.room_options.grid(row=settings_row, column=0, sticky="news")
        self.room_options.grid_remove()


    def save_room_map(self):
        win = PopupWindow("Save Layout", self.modlunky_config)

        item_name = ""

        col1_lbl = ttk.Label(win, text="Name: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, item_name)  # Default to rooms current name
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="news")

        def save_and_destroy():
            if col1_ent.get() == "":
                return
            segments = []
            for template_map in self.room_map:
                segment = CustomRoomMapSegment(
                    template_map.name,
                    [[room.template.name if room else "" for room in row] for row in template_map.rooms]
                )
                segments.append(segment)
            room_map = CustomRoomMap(col1_ent.get(), segments)
            level_room_maps = self.modlunky_config.custom_room_maps.get(self.lvl)
            if level_room_maps is None:
                level_room_maps = []
            level_room_maps.append(room_map)
            self.modlunky_config.custom_room_maps[self.lvl] = level_room_maps
            self.modlunky_config.default_custom_room_maps[self.lvl] = len(level_room_maps) - 1
            self.modlunky_config.save()
            self.update_layouts()

            win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=1, column=0, columnspan=2, pady=5, sticky="news")

        buttons = ttk.Frame(win)
        buttons.grid(row=2, column=0, columnspan=2, sticky="news")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Save", command=save_and_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="news")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="news")

    def update_room_map_template(self, template_index, map_index, row, column):
        template = self.templates[template_index]
        self.on_change_template_at(map_index, row, column, template, template_index)
        self.layout_frame.grid()
        self.save_layout_button.grid()

    def clear_template(self, map_index, row, column):
        self.on_clear_template(map_index, row, column)
        self.layout_frame.grid()
        self.save_layout_button.grid()

    def reset(self):
        self.button_for_selected_room = None
        self.button_for_selected_empty_room = None
        self.room_options.grid_remove()
        self.room_options.reset()
        self.layout_frame.grid_remove()
        self.save_layout_button.grid_remove()

    def select_layout(self):
        selected_layout = self.layout_combobox.current()
        if selected_layout is None:
            selected_layout = 0

        self.modlunky_config.default_custom_room_maps[self.lvl] = selected_layout - 1
        self.on_select_layout(selected_layout - 1)
        self.modlunky_config.save()

    def update_layouts(self):
        level_room_maps = self.modlunky_config.custom_room_maps.get(self.lvl)
        if level_room_maps is not None and len(level_room_maps) > 0:
            self.layout_combobox.grid()
            self.layout_label.grid()
            self.layout_frame.grid()
            self.layout_combobox["values"] = ["Default"] + [map.name for map in level_room_maps]
            default_layout = self.modlunky_config.default_custom_room_maps.get(self.lvl)
            layout_index = default_layout + 1 if default_layout is not None else 0
            self.layout_combobox.current(layout_index)
            self.layout_combobox.set(self.layout_combobox["values"][layout_index])
        else:
            self.layout_combobox.grid_remove()
            self.layout_label.grid_remove()

    def set_lvl(self, lvl):
        self.lvl = lvl
        self.layout_frame.grid_remove()
        self.save_layout_button.grid_remove()
        self.layout_combobox.grid_remove()
        self.layout_label.grid_remove()

        self.update_layouts()

    def set_templates(self, room_map, templates):
        self.button_for_selected_room = None
        self.button_for_selected_empty_room = None
        self.room_options.grid_remove()
        # self.room_options.grid_remove()
        room_row_start = 0
        if self.room_map is not None:
            for template_map in self.room_map:
                for row_index in range(len(template_map.rooms) + 1):
                    self.room_type_frame.rowconfigure(
                        room_row_start + row_index * 2, minsize=0
                    )
                    if row_index + room_row_start != 0:
                        self.room_type_frame.rowconfigure(
                            room_row_start + row_index * 2 - 1, minsize=0
                        )

                room_row_start += (len(template_map.rooms) + 1) * 2

        self.room_map = room_map
        self.templates = templates

        self.room_options.set_templates(templates)

        room_row_start = 0
        if room_map is not None:
            for template_map in room_map:
                for row_index in range(len(template_map.rooms) + 1):
                    self.room_type_frame.rowconfigure(
                        room_row_start + row_index * 2, minsize=self.room_view_size
                    )
                    if row_index != 0:
                        self.room_type_frame.rowconfigure(
                            room_row_start + row_index * 2 - 1,
                            minsize=self.room_view_padding,
                        )
                    elif room_row_start != 0:
                        self.room_type_frame.rowconfigure(
                            room_row_start + row_index * 2 - 1,
                            minsize=self.room_view_size,
                        )
                room_row_start += (len(template_map.rooms) + 1) * 2

        for button in self.room_buttons:
            button.grid_remove()

        for frame in self.edge_frames:
            frame.grid_remove()

        self.room_buttons = []
        self.edge_frames = []

        room_row_start = 0
        for map_index, template_map in enumerate(room_map):
            for row_index, template_row in enumerate(template_map.rooms):
                for col_index, template in enumerate(template_row):
                    new_button = None
                    if template is None:
                        overlapping_template, _, _ = self.template_item_at(
                            template_map.rooms, row_index, col_index
                        )
                        if overlapping_template is None:
                            new_button = tk.Button(
                                self.room_type_frame,
                                bg="#5A605A",
                                activebackground="#5A605A",
                                relief=tk.GROOVE,
                            )
                            new_button.configure(
                                command=lambda nb=new_button, m=map_index, r=row_index, c=col_index: self.select_empty_cell(
                                    nb, m, r, c
                                )
                            )
                            new_button.grid(
                                row=room_row_start + row_index * 2,
                                column=col_index * 2,
                                sticky="news",
                            )
                            if (
                                map_index
                                == self.room_options.current_template_map_index
                                and row_index == self.room_options.current_template_row
                                and col_index
                                == self.room_options.current_template_column
                            ):
                                self.button_for_selected_empty_room = new_button
                                self.room_options.set_empty_cell(
                                    map_index, row_index, col_index
                                )
                    else:
                        new_button = tk.Button(
                            self.room_type_frame,
                            bg="#30F030",
                            activebackground="#30F030",
                            relief=tk.GROOVE,
                        )
                        new_button.configure(
                            command=lambda t=template, nb=new_button, m=map_index, r=row_index, c=col_index: self.select_template_item(
                                t, nb, m, r, c
                            )
                        )
                        new_button.grid(
                            row=room_row_start + row_index * 2,
                            column=col_index * 2,
                            rowspan=template.height_in_rooms * 2 - 1,
                            columnspan=template.width_in_rooms * 2 - 1,
                            sticky="news",
                        )
                        if (
                            map_index == self.room_options.current_template_map_index
                            and row_index == self.room_options.current_template_row
                            and col_index == self.room_options.current_template_column
                        ):
                            self.button_for_selected_room = new_button
                            self.room_options.set_current_template(
                                template, map_index, row_index, col_index
                            )
                    if new_button is not None:
                        self.room_buttons.append(new_button)

                if len(template_row) < 10:
                    edge_frame = tk.Frame(self.room_type_frame)
                    edge_frame.grid(
                        row=room_row_start + row_index * 2,
                        column=len(template_row) * 2,
                        sticky="news",
                    )
                    edge_frame.columnconfigure(0, weight=1)
                    edge_frame.rowconfigure(0, weight=1)

                    edge_button = tk.Button(
                        edge_frame,
                        text="+",
                        bg="#A0C0A6",
                        activebackground="#A0C0A6",
                        relief=tk.GROOVE,
                    )
                    edge_button.grid(row=0, column=0, sticky="news")
                    edge_button.grid_remove()
                    edge_button.configure(
                        command=lambda m=map_index, r=row_index, c=len(
                            template_row
                        ): self.show_create_new_dialog(m, r, c)
                    )

                    edge_frame.bind("<Enter>", lambda _, eb=edge_button: eb.grid())
                    edge_frame.bind(
                        "<Leave>", lambda _, eb=edge_button: eb.grid_remove()
                    )
                    self.edge_frames.append(edge_frame)

            rooms = template_map.rooms
            if len(rooms) > 0:
                row = room_row_start + len(rooms) * 2
                for col in range(len(rooms[0])):
                    edge_frame = tk.Frame(self.room_type_frame)
                    edge_frame.grid(row=row, column=col * 2, sticky="news")
                    edge_frame.columnconfigure(0, weight=1)
                    edge_frame.rowconfigure(0, weight=1)

                    edge_button = tk.Button(
                        edge_frame,
                        text="+",
                        bg="#A0C0A6",
                        activebackground="#A0C0A6",
                        relief=tk.GROOVE,
                    )
                    edge_button.grid(row=0, column=0, sticky="news")
                    edge_button.grid_remove()
                    edge_button.configure(
                        command=lambda r=len(
                            rooms
                        ), c=col, m=map_index: self.show_create_new_dialog(m, r, c)
                    )

                    edge_frame.bind("<Enter>", lambda _, eb=edge_button: eb.grid())
                    edge_frame.bind(
                        "<Leave>", lambda _, eb=edge_button: eb.grid_remove()
                    )
                    self.edge_frames.append(edge_frame)
            room_row_start += (len(template_map.rooms) + 1) * 2
        self.highlight_selected_button()

    def reset_selected_button(self):
        if self.button_for_selected_room is not None:
            self.button_for_selected_room.configure(
                bg="#30F030", activebackground="#30F030"
            )
            self.button_for_selected_room = None
        if self.button_for_selected_empty_room is not None:
            self.button_for_selected_empty_room.configure(
                bg="#5A605A", activebackground="#5A605A"
            )
            self.button_for_selected_empty_room = None

    def highlight_selected_button(self):
        if self.button_for_selected_room is not None:
            self.button_for_selected_room.configure(
                bg="#228B22", activebackground="#228B22"
            )
            self.room_options.grid()
        if self.button_for_selected_empty_room is not None:
            self.button_for_selected_empty_room.configure(
                bg="#1A201A", activebackground="#1A201A"
            )
            self.room_options.grid()

    def select_template_item(self, template_item, button, map_index, row, column):
        self.reset_selected_button()
        self.button_for_selected_room = button
        self.highlight_selected_button()
        self.room_options.set_current_template(template_item, map_index, row, column)
        self.room_options.grid()

    def select_empty_cell(self, button, map_index, row, column):
        self.reset_selected_button()
        self.button_for_selected_empty_room = button
        self.highlight_selected_button()
        self.room_options.set_empty_cell(map_index, row, column)
        self.room_options.grid()

    def show_create_new_dialog(self, map_index, row, column):
        win = PopupWindow("Add room", self.modlunky_config)

        lbl = ttk.Label(win, text="Select a template to add.")
        lbl.grid(row=0, column=0)

        warning_label = tk.Label(
            win, text="", foreground="red", wraplength=200, justify=tk.LEFT
        )
        warning_label.grid(row=2, column=0, sticky="nw", pady=(10, 0))
        warning_label.grid_remove()

        separator = ttk.Separator(win)
        separator.grid(row=3, column=0, columnspan=3, pady=5, sticky="news")

        buttons = ttk.Frame(win)
        buttons.grid(row=4, column=0, columnspan=2, sticky="news")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        template_combobox = ttk.Combobox(win, height=25)
        template_combobox.grid(row=1, column=0, sticky="nsw")
        template_combobox["values"] = [template.name for template in self.templates]
        template_combobox["state"] = "readonly"

        def add_then_destroy():
            template_index = template_combobox.current()
            if template_index is None or template_index == -1:
                warning_label["text"] = "Select a room template"
                warning_label.grid()
                return

            self.room_options.set_empty_cell(map_index, row, column)
            self.update_room_map_template(template_index, map_index, row, column)
            win.destroy()

        ok_button = ttk.Button(buttons, text="Add", command=add_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="news")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="news")

    def update_zoom_level(self, zoom_level):
        self.grid_size_var.set(zoom_level)

    def template_item_at(self, room_map, row, col):
        for room_row_index, room_row in enumerate(room_map):
            if room_row_index > row:
                return None, None, None
            for room_column_index, template_draw_item in enumerate(room_row):
                if room_column_index > col:
                    break
                if template_draw_item is None:
                    continue
                if (
                    room_row_index + template_draw_item.height_in_rooms - 1 >= row
                    and room_column_index + template_draw_item.width_in_rooms - 1 >= col
                ):
                    return template_draw_item, room_row_index, room_column_index

        return None, None, None
