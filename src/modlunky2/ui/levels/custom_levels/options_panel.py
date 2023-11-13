import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

from modlunky2.config import Config, CustomLevelSaveFormat
from modlunky2.levels.tile_codes import VALID_TILE_CODES
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.shared.biomes import Biomes, BIOME
from modlunky2.ui.widgets import PopupWindow, Tab

class OptionsPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        zoom_level,
        on_select_theme,
        on_update_level_size,
        on_update_save_format,
        on_update_hide_grid_lines,
        on_update_hide_room_lines,
        on_update_zoom_level,
        modlunky_config,
        *args,
        **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_select_theme = on_select_theme
        self.on_update_level_size = on_update_level_size
        self.on_update_save_format = on_update_save_format
        self.on_update_hide_grid_lines = on_update_hide_grid_lines
        self.on_update_hide_room_lines = on_update_hide_room_lines
        self.on_update_zoom_level = on_update_zoom_level

        self.lvl_width = None
        self.lvl_height = None
        # self.hide_grid_lines = False
        # self.hide_grid_rooms = False

        self.rowconfigure(2, minsize=20)
        self.rowconfigure(4, minsize=20)

        settings_row = 0

        theme_label = tk.Label(self, text="Level Theme:")
        theme_label.grid(row=settings_row, column=0, columnspan=2, sticky="nsw")
        self.theme_label = theme_label

        settings_row += 1

        # Combobox for selecting the level theme. The theme affects the texture used to
        # display many tiles and the level background; the suggested tiles in the tile
        # palette; and the additional vanilla setrooms that are saved into the level
        # file.
        self.theme_combobox = ttk.Combobox(self, height=25)
        self.theme_combobox.grid(row=settings_row, column=0, sticky="nsw")
        self.theme_combobox["state"] = tk.DISABLED
        self.theme_combobox["values"] = [
            "Dwelling",
            "Jungle",
            "Volcana",
            "Olmec",
            "Tide Pool",
            "Temple",
            "Ice Caves",
            "Neo Babylon",
            "Sunken City",
            "City of Gold",
            "Duat",
            "Eggplant World",
            "Surface",
        ]

        def update_theme():
            theme_name = str(self.theme_combobox.get())
            biome = Biomes.biome_for_name(theme_name)
            self.theme_select_button["state"] = tk.DISABLED
            self.theme_label["text"] = "Level Theme: " + Biomes().name_of_biome(biome)
            self.on_select_theme(biome)

        self.theme_select_button = tk.Button(
            self,
            text="Update Theme",
            bg="yellow",
            command=update_theme,
        )
        self.theme_select_button["state"] = tk.DISABLED
        self.theme_select_button.grid(row=settings_row, column=1, sticky="nsw")

        def theme_selected(_):
            self.theme_select_button["state"] = tk.NORMAL

        self.theme_combobox.bind("<<ComboboxSelected>>", theme_selected)

        settings_row += 1
        settings_row += 1
        # Comboboxes to change the size of the level. If the size is decreased, the
        # tiles in the missing space are still cached and restored if the size is
        # increased again. This cache is cleared if another level is loaded or the
        # level editor is closed.
        size_frame = tk.Frame(self)
        size_frame.grid(column=0, row=settings_row, columnspan=2, sticky="w")
        size_frame.columnconfigure(2, minsize=10)
        self.size_label = tk.Label(size_frame, text="Level size:")
        self.size_label.grid(column=0, row=0, columnspan=5, sticky="nsw")

        tk.Label(size_frame, text="Width: ").grid(row=1, column=0, sticky="nsw")

        self.width_combobox = ttk.Combobox(size_frame, height=25)
        self.width_combobox.grid(row=1, column=1, sticky="nswe")
        self.width_combobox["state"] = tk.DISABLED
        self.width_combobox["values"] = [1, 2, 3, 4, 5, 6, 7, 8]

        tk.Label(size_frame, text="Height: ").grid(row=2, column=0, sticky="nsw")

        self.height_combobox = ttk.Combobox(size_frame, height=25)
        self.height_combobox.grid(row=2, column=1, sticky="nswe")
        self.height_combobox["state"] = tk.DISABLED
        self.height_combobox["values"] = [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
        ]

        def update_size():
            width = int(self.width_combobox.get())
            height = int(self.height_combobox.get())
            self.size_select_button["state"] = tk.DISABLED
            self.update_level_size(width, height)
            self.on_update_level_size(width, height)

        self.size_select_button = tk.Button(
            size_frame,
            text="Update Size",
            bg="yellow",
            command=update_size,
        )
        self.size_select_button["state"] = tk.DISABLED
        self.size_select_button.grid(row=1, column=3, rowspan=2, sticky="w")

        def size_selected(_):
            width = int(self.width_combobox.get())
            height = int(self.height_combobox.get())
            self.size_select_button["state"] = (
                tk.DISABLED
                if (width == self.lvl_width and height == self.lvl_height)
                else tk.NORMAL
            )

        self.width_combobox.bind("<<ComboboxSelected>>", size_selected)
        self.height_combobox.bind("<<ComboboxSelected>>", size_selected)

        settings_row += 1
        settings_row += 1

        option_header = tk.Label(self, text="Save format:")
        option_header.grid(column=0, row=settings_row, sticky="nsw")

        settings_row += 1
        save_format_frame = tk.Frame(self)
        save_format_frame.grid(column=0, row=settings_row, columnspan=2, sticky="nwe")

        save_format_variable = tk.IntVar()
        save_format_variable.set(0)
        self.save_format_variable = save_format_variable
        self.save_format_radios = []
        self.save_format_frame = save_format_frame

        for index, save_format in enumerate(
            SaveFormats.base_save_formats()
            + self.modlunky_config.custom_level_editor_custom_save_formats
        ):
            self.add_save_format_radio(index, save_format)

        settings_row += 1
        self.save_format_warning_message = tk.Label(
            self, text="", wraplength=350, justify=tk.LEFT
        )
        self.save_format_warning_message.grid(
            column=0, row=settings_row, columnspan=2, sticky="nw"
        )

        if self.modlunky_config.custom_level_editor_default_save_format:
            self.update_save_format_variable(
                self.modlunky_config.custom_level_editor_default_save_format
            )
            self.update_save_format_warning(
                self.modlunky_config.custom_level_editor_default_save_format
            )

        settings_row += 1

        def create_template():
            SaveFormats.show_setroom_create_dialog(
                self.modlunky_config,
                "Create new room template format",
                "Create a new room template format\n{x} and {y} are the coordinates of the room.",
                "Create",
                self.add_save_format,
            )

        create_template_button = tk.Button(
            self,
            text="New save format",
            bg="red",
            fg="white",
            command=create_template,
        )
        create_template_button.grid(row=settings_row, column=0, sticky="nw")

        # Checkbox to toggle the visibility of the grid lines.
        hide_grid_var = tk.IntVar()
        # hide_grid_var.set(self.hide_grid_lines)
        hide_grid_var.set(False)

        def toggle_hide_grid():
            nonlocal hide_grid_var
            # self.hide_grid_lines = hide_grid_var.get()

            self.on_update_hide_grid_lines(hide_grid_var.get())

            # self.hide_grid(
            #     self.custom_level_canvas_foreground, self.grid_lines_foreground
            # )
            # self.hide_grid(
            #     self.custom_level_canvas_background, self.grid_lines_background
            # )

        settings_row += 1
        tk.Checkbutton(
            self,
            text="Hide grid lines",
            variable=hide_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_grid,
        ).grid(row=settings_row, column=0, sticky="nw", pady=5)

        # Checkbox to toggle the visibility of the grid lines on room boundaries.
        hide_room_grid_var = tk.IntVar()
        # hide_room_grid_var.set(self.hide_grid_rooms)
        hide_room_grid_var.set(False)

        def toggle_hide_room_grid():
            nonlocal hide_room_grid_var
            # self.hide_grid_rooms = hide_room_grid_var.get()
            self.on_update_hide_room_lines(hide_room_grid_var.get())

            # self.hide_room_grid(
            #     self.custom_level_canvas_foreground, self.grid_rooms_foreground
            # )
            # self.hide_room_grid(
            #     self.custom_level_canvas_background, self.grid_rooms_background
            # )

        settings_row += 1
        tk.Checkbutton(
            self,
            text="Hide room lines",
            variable=hide_room_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_room_grid,
        ).grid(row=settings_row, column=0, sticky="nw", pady=5)

        settings_row += 1
        grid_size_frame = tk.Frame(self)
        grid_size_frame.grid(row=settings_row, column=0, sticky="nw", pady=5)
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
            to=100,
            orient=tk.HORIZONTAL,
            variable=grid_size_var,
            length=200,
            showvalue=False,
        )
        grid_size_scale.grid(row=1, column=0, sticky="nwe")

        # grid_size_scale.set(self.custom_editor_zoom_level)
        def update_grid_size(_):
            self.on_update_zoom_level(int(grid_size_var.get()))
            # self.custom_editor_zoom_level = int(grid_size_var.get())
            # self.lvl_bgs = {}
            # if self.lvl:
            #     for tile in self.tile_palette_ref_in_use:
            #         tile_name = tile[0].split(" ", 2)[0]
            #         tile[1] = ImageTk.PhotoImage(
            #             self.texture_fetcher.get_texture(
            #                 tile_name,
            #                 self.lvl_biome,
            #                 self.lvl,
            #                 self.custom_editor_zoom_level,
            #             )
            #         )
            #     self.draw_custom_level_canvases(self.lvl_biome)

        grid_size_scale["command"] = update_grid_size

    def update_level_size(self, width, height):
        self.lvl_width = width
        self.lvl_height = height
        self.width_combobox.set(width)
        self.height_combobox.set(height)
        self.size_label["text"] = "Level size: {width} x {height}".format(
            width=width, height=height
        )

    def update_theme(self, theme):
        theme_name = Biomes.name_of_biome(theme)
        self.theme_combobox.set(theme_name)
        self.theme_label["text"] = "Level Theme: " + theme_name

    def enable_controls(self):
        self.theme_combobox["state"] = "readonly"
        self.width_combobox["state"] = "readonly"
        self.height_combobox["state"] = "readonly"

    def disable_controls(self):
        self.theme_combobox["state"] = tk.DISABLED
        self.theme_select_button["state"] = tk.DISABLED
        self.width_combobox["state"] = tk.DISABLED
        self.height_combobox["state"] = tk.DISABLED
        self.size_select_button["state"] = tk.DISABLED

    # Updates the current radio button in the save format select options menu to the
    # proper save format.
    def update_save_format_variable(self, save_format):
        if save_format in SaveFormats.base_save_formats():
            self.save_format_variable.set(SaveFormats.base_save_formats().index(save_format))
        elif (
            save_format in self.modlunky_config.custom_level_editor_custom_save_formats
        ):
            self.save_format_variable.set(
                len(SaveFormats.base_save_formats())
                + self.modlunky_config.custom_level_editor_custom_save_formats.index(
                    save_format
                )
            )
        self.save_format_radios[self.save_format_variable.get()].select()

    # Adds a warning message below the save format radio list based on the selected
    # save format.
    def update_save_format_warning(self, save_format):
        warning_message = ""
        if save_format == CustomLevelSaveFormat.level_sequence():
            warning_message = (
                "This save format can be used to load saved level files into the "
                "Custom Levels or Level Sequence packages.\n"
                "(https://github.com/jaythebusinessgoose/LevelSequence)"
            )
        elif save_format == CustomLevelSaveFormat.vanilla():
            warning_message = (
                "WARNING: Files saved using vanilla setrooms will only work when loaded "
                "into themes that use them. Otherwise, it will crash the game. Also, themes "
                "that do allow loading vanilla setrooms will only load the required setrooms "
                "for the default size of the level. It is recommended to use another save "
                "format and use scripts to load the proper rooms."
            )
        elif not save_format.include_vanilla_setrooms:
            warning_message = (
                "WARNING: Some themes override the desired level with a vanilla setroom, so it "
                "is recommended to use a save format that includes the correct vanilla setrooms."
            )
        self.save_format_warning_message["text"] = warning_message

    def set_current_save_format(self, save_format):
        self.update_save_format_variable(save_format)
        self.update_save_format_warning(save_format)

    def add_save_format_radio(self, index, save_format):
        radio = tk.Radiobutton(
            self.save_format_frame,
            text=save_format.name,
            variable=self.save_format_variable,
            indicatoron=True,
            value=index,
            command=self.select_save_format_radio,
        )
        radio.grid(column=0, row=index, sticky="nsw")
        self.save_format_radios.append(radio)

        label = tk.Label(self.save_format_frame, text=save_format.room_template_format)
        label.grid(column=1, row=index, sticky="nsw")

    # Called when a save format radio button is selected.
    def select_save_format_radio(self):
        save_format_index = self.save_format_variable.get()
        save_format = None
        if save_format_index < len(SaveFormats.base_save_formats()):
            save_format = SaveFormats.base_save_formats()[save_format_index]
        else:
            save_format = self.modlunky_config.custom_level_editor_custom_save_formats[
                save_format_index - len(SaveFormats.base_save_formats())
            ]
        if not save_format:
            return
        self.set_current_save_format(save_format)
        self.on_update_save_format(save_format)
        self.modlunky_config.custom_level_editor_default_save_format = save_format
        self.modlunky_config.save()

    def add_save_format(self, save_format):
        self.add_save_format_radio(len(self.save_format_radios), save_format)