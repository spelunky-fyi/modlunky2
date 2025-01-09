import tkinter as tk
from tkinter import ttk

from modlunky2.mem.state import Theme


def name_of_theme(theme):
    if theme is None:
        return "Default"
    if theme == Theme.DWELLING:
        return "Dwelling"
    elif theme == Theme.TIDE_POOL:
        return "Tide Pool"
    elif theme == Theme.NEO_BABYLON:
        return "Neo Babylon"
    elif theme == Theme.JUNGLE:
        return "Jungle"
    elif theme == Theme.TEMPLE:
        return "Temple"
    elif theme == Theme.SUNKEN_CITY:
        return "Sunken City"
    elif theme == Theme.COSMIC_OCEAN:
        return "Cosmic Ocean"
    elif theme == Theme.CITY_OF_GOLD:
        return "City of Gold"
    elif theme == Theme.DUAT:
        return "Duat"
    elif theme == Theme.ABZU:
        return "Abzu"
    elif theme == Theme.EGGPLANT_WORLD:
        return "Eggplant World"
    elif theme == Theme.ICE_CAVES:
        return "Ice Caves"
    elif theme == Theme.OLMEC:
        return "Olmec"
    elif theme == Theme.VOLCANA:
        return "Volcana"
    elif theme == Theme.TIAMAT:
        return "Tiamat"
    elif theme == Theme.HUNDUN:
        return "Hundun"
    elif theme == Theme.BASE_CAMP:
        return "Surface"
    return "Unknown"


def theme_for_name(name):
    if name == "Dwelling":
        return Theme.DWELLING
    elif name == "Jungle":
        return Theme.JUNGLE
    elif name == "Volcana":
        return Theme.VOLCANA
    elif name == "Olmec":
        return Theme.OLMEC
    elif name == "Tide Pool":
        return Theme.TIDE_POOL
    elif name == "Temple":
        return Theme.TEMPLE
    elif name == "Ice Caves":
        return Theme.ICE_CAVES
    elif name == "Neo Babylon":
        return Theme.NEO_BABYLON
    elif name == "Sunken City":
        return Theme.SUNKEN_CITY
    elif name == "Cosmic Ocean":
        return Theme.COSMIC_OCEAN
    elif name == "City of Gold":
        return Theme.CITY_OF_GOLD
    elif name == "Duat":
        return Theme.DUAT
    elif name == "Abzu":
        return Theme.ABZU
    elif name == "Tiamat":
        return Theme.TIAMAT
    elif name == "Eggplant World":
        return Theme.EGGPLANT_WORLD
    elif name == "Hundun":
        return Theme.HUNDUN
    elif name == "Surface":
        return Theme.BASE_CAMP
    return None


def name_of_border_entity_theme(theme):
    if (
        theme == Theme.DWELLING
        or theme == Theme.TIDE_POOL
        or theme == Theme.JUNGLE
        or theme == Theme.TEMPLE
        or theme == Theme.COSMIC_OCEAN
        or theme == Theme.CITY_OF_GOLD
        or theme == Theme.DUAT
        or theme == Theme.ABZU
        or theme == Theme.EGGPLANT_WORLD
        or theme == Theme.ICE_CAVES
        or theme == Theme.OLMEC
        or theme == Theme.VOLCANA
        or theme == Theme.TIAMAT
        or theme == Theme.HUNDUN
        or theme == Theme.BASE_CAMP
    ):
        return "Hard"
    elif theme == Theme.NEO_BABYLON:
        return "Metal"
    elif theme == Theme.SUNKEN_CITY:
        return "Guts"
    elif theme == Theme.DUAT:
        return "Dust"
    return "Default"


def border_entity_theme_for_name(name):
    if name == "Hard":
        return Theme.DWELLING
    elif name == "Metal":
        return Theme.NEO_BABYLON
    elif name == "Guts":
        return Theme.SUNKEN_CITY
    elif name == "Dust":
        return Theme.DUAT
    return None


def name_of_border_theme(theme):
    if (
        theme == Theme.DWELLING
        or theme == Theme.NEO_BABYLON
        or theme == Theme.SUNKEN_CITY
        or theme == Theme.TIDE_POOL
        or theme == Theme.JUNGLE
        or theme == Theme.TEMPLE
        or theme == Theme.CITY_OF_GOLD
        or theme == Theme.ABZU
        or theme == Theme.EGGPLANT_WORLD
        or theme == Theme.OLMEC
        or theme == Theme.VOLCANA
        or theme == Theme.HUNDUN
        or theme == Theme.BASE_CAMP
    ):
        return "Normal"
    elif theme == Theme.ICE_CAVES:
        return "Ice Caves"
    elif theme == Theme.TIAMAT:
        return "Tiamat"
    elif theme == Theme.DUAT:
        return "Duat"
    elif theme == Theme.COSMIC_OCEAN:
        return "Cosmic Ocean"
    return "Default"


def border_theme_for_name(name):
    if name == "Normal":
        return Theme.DWELLING
    elif name == "Ice Caves":
        return Theme.ICE_CAVES
    elif name == "Tiamat":
        return Theme.TIAMAT
    elif name == "Duat":
        return Theme.DUAT
    elif name == "Cosmic Ocean":
        return Theme.COSMIC_OCEAN
    return None


class LevelConfigurationPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        on_update_level_size,
        on_update_level_name,
        on_select_theme,
        on_select_border_theme,
        on_select_border_entity_theme,
        on_select_background_theme,
        on_select_floor_theme,
        on_select_music_theme,
        on_update_co_fix,
        on_update_spawn_jelly,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_update_level_size = on_update_level_size
        self.on_update_level_name = on_update_level_name
        self.on_select_theme = on_select_theme
        self.on_select_border_theme = on_select_border_theme
        self.on_select_border_entity_theme = on_select_border_entity_theme
        self.on_select_background_theme = on_select_background_theme
        self.on_select_floor_theme = on_select_floor_theme
        self.on_select_music_theme = on_select_music_theme
        self.on_update_co_fix = on_update_co_fix
        self.on_update_spawn_jelly = on_update_spawn_jelly

        self.lvl_width = None
        self.lvl_height = None

        self.sequence_exists = True
        self.level_in_sequence = True

        self.columnconfigure(0, weight=1)
        right_padding = 10
        self.columnconfigure(1, minsize=right_padding)

        settings_row = 0

        self.rowconfigure(settings_row, minsize=10)
        settings_row += 1

        name_frame = tk.Frame(self)
        name_frame.grid(column=0, row=settings_row, sticky="news")
        name_frame.columnconfigure(1, weight=1)

        tk.Label(name_frame, text="Display Name: ").grid(row=0, column=0, sticky="nsw")

        self.setting_name = False

        def update_name():
            if self.setting_name:
                return
            self.on_update_level_name(self.name_var.get())

        self.name_var = tk.StringVar()
        self.name_var.trace_add(
            "write",
            lambda *args: update_name(),
        )
        self.name_entry = tk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="news")

        settings_row += 1
        self.rowconfigure(settings_row, minsize=10)
        settings_row += 1

        theme_label = tk.Label(self, text="Level Theme:")
        theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.theme_label = theme_label

        settings_row += 1

        theme_container = ttk.Frame(self)
        theme_container.grid(row=settings_row, column=0, sticky="nwse")
        theme_container.columnconfigure(1, weight=1)

        # Combobox for selecting the level theme. The theme affects the texture used to
        # display many tiles and the level background; the suggested tiles in the tile
        # palette; and the additional vanilla setrooms that are saved into the level
        # file.
        self.theme_combobox = ttk.Combobox(theme_container, height=25)
        self.theme_combobox.grid(row=0, column=0, sticky="nsw")
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
            "Cosmic Ocean",
            "City of Gold",
            "Duat",
            "Abzu",
            "Tiamat",
            "Eggplant World",
            "Hundun",
            "Surface",
        ]

        self.subtheme_combobox = ttk.Combobox(theme_container, height=25)
        self.subtheme_combobox.grid(row=1, column=0, sticky="nsw")
        self.subtheme_combobox["state"] = tk.DISABLED
        self.subtheme_combobox.grid_remove()
        self.subtheme_combobox["values"] = [
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
            "Abzu",
            "Tiamat",
            "Eggplant World",
            "Hundun",
            "Surface",
        ]

        def update_theme():
            theme_name = str(self.theme_combobox.get())
            theme = theme_for_name(theme_name)
            if theme == Theme.COSMIC_OCEAN:
                subtheme_name = str(self.subtheme_combobox.get())
                subtheme = theme_for_name(subtheme_name)
            else:
                subtheme = None
            self.theme_select_button["state"] = tk.DISABLED
            self.update_theme_label()
            self.on_select_theme(theme, subtheme)

        self.theme_select_button = tk.Button(
            theme_container,
            text="Update Theme",
            bg="yellow",
            command=update_theme,
        )
        self.theme_select_button["state"] = tk.DISABLED
        self.theme_select_button.grid(row=0, column=2, sticky="nse")

        self.selected_theme = None
        self.selected_subtheme = None

        def theme_selected(_):
            theme_name = str(self.theme_combobox.get())
            theme = theme_for_name(theme_name)

            if theme == Theme.COSMIC_OCEAN:
                if self.selected_subtheme is None and self.selected_theme is not None:
                    self.subtheme_combobox.set(name_of_theme(self.selected_theme))

            self.selected_theme = theme

            self.theme_select_button["state"] = tk.NORMAL
            self.update_theme_controls()

        def subtheme_selected(_):
            subtheme_name = str(self.subtheme_combobox.get())
            subtheme = theme_for_name(subtheme_name)
            self.selected_subtheme = subtheme
            self.theme_select_button["state"] = tk.NORMAL

        self.theme_combobox.bind("<<ComboboxSelected>>", theme_selected)
        self.subtheme_combobox.bind("<<ComboboxSelected>>", subtheme_selected)

        settings_row += 1
        self.rowconfigure(settings_row, minsize=20)
        settings_row += 1

        # Comboboxes to change the size of the level. If the size is decreased, the
        # tiles in the missing space are still cached and restored if the size is
        # increased again. This cache is cleared if another level is loaded or the
        # level editor is closed.
        size_frame = tk.Frame(self)
        size_frame.grid(column=0, row=settings_row, sticky="news")
        size_frame.columnconfigure(2, weight=1)
        self.size_label = tk.Label(size_frame, text="Level size:")
        self.size_label.grid(column=0, row=0, columnspan=4, sticky="nsw")

        tk.Label(size_frame, text="Width: ").grid(row=1, column=0, sticky="nsw")

        self.width_combobox = ttk.Combobox(size_frame, height=25)
        self.width_combobox.grid(row=1, column=1, sticky="nswe")
        self.width_combobox["state"] = tk.DISABLED
        self.width_combobox["values"] = list(range(1, 9))

        tk.Label(size_frame, text="Height: ").grid(row=2, column=0, sticky="nsw")

        self.height_combobox = ttk.Combobox(size_frame, height=25)
        self.height_combobox.grid(row=2, column=1, sticky="nswe")
        self.height_combobox["state"] = tk.DISABLED
        self.height_combobox["values"] = list(range(1, 16))

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
        self.rowconfigure(settings_row, minsize=20)
        settings_row += 1

        advanced_settings_label = tk.Label(
            self, text="Advanced Configuration:", font=("TkDefaultFont", 17)
        )
        advanced_settings_label.grid(row=settings_row, column=0, sticky="nsw")

        settings_row += 1
        self.rowconfigure(settings_row, minsize=20)

        self.sequence_warning_container = ttk.Frame(self)
        self.sequence_warning_container.grid(row=settings_row, column=0, sticky="news")
        self.sequence_warning_container.rowconfigure(0, minsize=10)
        self.sequence_warning_container.rowconfigure(2, minsize=10)

        self.sequence_warning_label = tk.Label(
            self.sequence_warning_container,
            text="",
            foreground="red",
            wraplength=400,
            justify="left",
        )
        self.sequence_warning_label.grid(row=1, column=0, sticky="nsw")

        self.update_sequence_warning_message()

        settings_row += 1

        border_theme_label = tk.Label(self, text="Border Type:")
        border_theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.border_theme_label = border_theme_label

        settings_row += 1

        border_theme_container = ttk.Frame(self)
        border_theme_container.grid(row=settings_row, column=0, sticky="nwse")
        border_theme_container.columnconfigure(1, weight=1)

        self.border_theme_combobox = ttk.Combobox(border_theme_container, height=25)
        self.border_theme_combobox.grid(row=0, column=0, sticky="nsw")
        self.border_theme_combobox["state"] = tk.DISABLED
        self.border_theme_combobox["values"] = [
            "Default",
            "Normal",
            "Ice Caves",
            "Cosmic Ocean",
            "Duat",
            "Tiamat",
        ]

        def update_border_theme():
            border_theme_name = str(self.border_theme_combobox.get())
            theme = border_theme_for_name(border_theme_name)
            self.border_theme_select_button["state"] = tk.DISABLED
            self.update_border_theme_label()
            loop = None
            if self.loop_manually_toggled:
                loop = self.loop_var.get()
            self.on_select_border_theme(theme, loop)

        self.border_theme_select_button = tk.Button(
            border_theme_container,
            text="Update Border",
            bg="yellow",
            command=update_border_theme,
        )
        self.border_theme_select_button["state"] = tk.DISABLED
        self.border_theme_select_button.grid(row=0, column=2, sticky="nse")

        def border_theme_selected(_):
            self.border_theme_select_button["state"] = tk.NORMAL

        self.border_theme_combobox.bind("<<ComboboxSelected>>", border_theme_selected)

        self.loop_manually_toggled = False
        self.loop_var = tk.IntVar()
        self.loop_var.set(False)

        def toggle_loop():
            self.loop_manually_toggled = True
            self.border_theme_select_button["state"] = tk.NORMAL

        self.border_loops_checkbox = tk.Checkbutton(
            border_theme_container,
            text="Loop",
            variable=self.loop_var,
            onvalue=True,
            offvalue=False,
            command=toggle_loop,
        ).grid(row=0, column=1, sticky="nws")

        settings_row += 1

        border_entity_theme_label = tk.Label(self, text="Border Entity:")
        border_entity_theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.border_entity_theme_label = border_entity_theme_label

        settings_row += 1

        border_entity_theme_container = ttk.Frame(self)
        border_entity_theme_container.grid(row=settings_row, column=0, sticky="news")
        border_entity_theme_container.columnconfigure(1, weight=1)

        self.border_entity_theme_combobox = ttk.Combobox(
            border_entity_theme_container, height=25
        )
        self.border_entity_theme_combobox.grid(row=0, column=0, sticky="nsw")
        self.border_entity_theme_combobox["state"] = tk.DISABLED
        self.border_entity_theme_combobox["values"] = [
            "Default",
            "Hard",
            "Metal",
            "Dust",
            "Guts",
        ]

        def update_border_entity_theme():
            border_entity_theme_name = str(self.border_entity_theme_combobox.get())
            theme = border_entity_theme_for_name(border_entity_theme_name)
            self.border_entity_theme_select_button["state"] = tk.DISABLED
            self.update_border_entity_theme_label()
            self.on_select_border_entity_theme(theme)

        self.border_entity_theme_select_button = tk.Button(
            border_entity_theme_container,
            text="Update Border",
            bg="yellow",
            command=update_border_entity_theme,
        )
        self.border_entity_theme_select_button["state"] = tk.DISABLED
        self.border_entity_theme_select_button.grid(row=0, column=2, sticky="nse")

        def border_entity_theme_selected(_):
            self.border_entity_theme_select_button["state"] = tk.NORMAL

        self.border_entity_theme_combobox.bind(
            "<<ComboboxSelected>>", border_entity_theme_selected
        )

        settings_row += 1

        background_theme_label = tk.Label(self, text="Background Theme:")
        background_theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.background_theme_label = background_theme_label

        settings_row += 1

        background_theme_container = ttk.Frame(self)
        background_theme_container.grid(row=settings_row, column=0, sticky="nwse")
        background_theme_container.columnconfigure(1, weight=1)

        # Combobox for selecting the background theme. The theme affects the texture
        # used to display only the level background.
        self.background_theme_combobox = ttk.Combobox(
            background_theme_container, height=25
        )
        self.background_theme_combobox.grid(row=0, column=0, sticky="nsw")
        self.background_theme_combobox["state"] = tk.DISABLED
        self.background_theme_combobox["values"] = [
            "Default",
            "Dwelling",
            "Jungle",
            "Volcana",
            "Olmec",
            "Tide Pool",
            "Temple",
            "Ice Caves",
            "Neo Babylon",
            "Sunken City",
            "Cosmic Ocean",
            "City of Gold",
            "Duat",
            "Abzu",
            "Tiamat",
            "Eggplant World",
            "Hundun",
            "Surface",
        ]

        self.background_subtheme_combobox = ttk.Combobox(
            background_theme_container, height=25
        )
        self.background_subtheme_combobox.grid(row=1, column=0, sticky="nsw")
        self.background_subtheme_combobox["state"] = tk.DISABLED
        self.background_subtheme_combobox.grid_remove()
        self.background_subtheme_combobox["values"] = [
            "Default",
            "Dwelling",
            "Jungle",
            "Volcana",
            "Tide Pool",
            "Temple",
            "Ice Caves",
            "Neo Babylon",
            "Sunken City",
        ]

        def update_background_theme():
            theme_name = str(self.background_theme_combobox.get())
            theme = theme_for_name(theme_name)
            if theme == Theme.COSMIC_OCEAN:
                subtheme_name = str(self.background_subtheme_combobox.get())
                subtheme = theme_for_name(subtheme_name)
            else:
                subtheme = None
            self.background_theme_select_button["state"] = tk.DISABLED
            self.update_background_theme_label()
            self.on_select_background_theme(theme, subtheme)

        self.background_theme_select_button = tk.Button(
            background_theme_container,
            text="Update Background",
            bg="yellow",
            command=update_background_theme,
        )
        self.background_theme_select_button["state"] = tk.DISABLED
        self.background_theme_select_button.grid(row=0, column=2, sticky="nse")

        def background_theme_selected(_):
            self.background_theme_select_button["state"] = tk.NORMAL
            self.update_background_theme_controls()

        def background_subtheme_selected(_):
            self.background_theme_select_button["state"] = tk.NORMAL

        self.background_theme_combobox.bind(
            "<<ComboboxSelected>>", background_theme_selected
        )
        self.background_subtheme_combobox.bind(
            "<<ComboboxSelected>>", background_subtheme_selected
        )

        settings_row += 1

        floor_theme_label = tk.Label(self, text="Floor Theme:")
        floor_theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.floor_theme_label = floor_theme_label

        settings_row += 1

        floor_theme_container = ttk.Frame(self)
        floor_theme_container.grid(row=settings_row, column=0, sticky="nwse")
        floor_theme_container.columnconfigure(1, weight=1)

        self.floor_theme_combobox = ttk.Combobox(floor_theme_container, height=25)
        self.floor_theme_combobox.grid(row=0, column=0, sticky="nsw")
        self.floor_theme_combobox["state"] = tk.DISABLED
        self.floor_theme_combobox["values"] = [
            "Default",
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
            "Abzu",
            "Tiamat",
            "Eggplant World",
            "Hundun",
            "Surface",
        ]

        def update_floor_theme():
            theme_name = str(self.floor_theme_combobox.get())
            theme = theme_for_name(theme_name)
            self.floor_theme_select_button["state"] = tk.DISABLED
            self.update_floor_theme_label()
            self.on_select_floor_theme(theme)

        self.floor_theme_select_button = tk.Button(
            floor_theme_container,
            text="Update Floor",
            bg="yellow",
            command=update_floor_theme,
        )
        self.floor_theme_select_button["state"] = tk.DISABLED
        self.floor_theme_select_button.grid(row=0, column=2, sticky="nse")

        def floor_theme_selected(_):
            self.floor_theme_select_button["state"] = tk.NORMAL

        self.floor_theme_combobox.bind("<<ComboboxSelected>>", floor_theme_selected)

        settings_row += 1

        music_theme_label = tk.Label(self, text="Level Music:")
        music_theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.music_theme_label = music_theme_label

        settings_row += 1

        music_theme_container = ttk.Frame(self)
        music_theme_container.grid(row=settings_row, column=0, sticky="nwse")
        music_theme_container.columnconfigure(1, weight=1)

        self.music_theme_combobox = ttk.Combobox(music_theme_container, height=25)
        self.music_theme_combobox.grid(row=0, column=0, sticky="nsw")
        self.music_theme_combobox["state"] = tk.DISABLED
        self.music_theme_combobox["values"] = [
            "Default",
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
            "Abzu",
            "Tiamat",
            "Eggplant World",
            "Hundun",
            "Surface",
        ]

        def update_music_theme():
            theme_name = str(self.music_theme_combobox.get())
            theme = theme_for_name(theme_name)
            self.music_theme_select_button["state"] = tk.DISABLED
            self.update_music_theme_label()
            self.on_select_music_theme(theme)

        self.music_theme_select_button = tk.Button(
            music_theme_container,
            text="Update Music",
            bg="yellow",
            command=update_music_theme,
        )
        self.music_theme_select_button["state"] = tk.DISABLED
        self.music_theme_select_button.grid(row=0, column=2, sticky="nse")

        def music_theme_selected(_):
            self.music_theme_select_button["state"] = tk.NORMAL

        self.music_theme_combobox.bind("<<ComboboxSelected>>", music_theme_selected)

        settings_row += 1
        self.rowconfigure(settings_row, minsize=20)
        settings_row += 1

        self.co_fix_var = tk.IntVar()
        self.co_fix_var.set(False)

        def toggle_co_fix():
            self.on_update_co_fix(self.co_fix_var.get())

        self.co_fix_checkbox = tk.Checkbutton(
            self,
            text="Disable Jellyfish/Orb fixes",
            variable=self.co_fix_var,
            onvalue=True,
            offvalue=False,
            command=toggle_co_fix,
        ).grid(row=settings_row, column=0, sticky="nws")

        settings_row += 1

        self.jelly_var = tk.IntVar()
        self.jelly_var.set(False)

        def toggle_jelly():
            self.on_update_spawn_jelly(self.jelly_var.get())

        self.jelly_checkbox = tk.Checkbutton(
            self,
            text="Spawn door Jellyfish",
            variable=self.jelly_var,
            onvalue=True,
            offvalue=False,
            command=toggle_jelly,
        ).grid(row=settings_row, column=0, sticky="nws")

        settings_row += 1
        self.rowconfigure(settings_row, minsize=20)
        settings_row += 1

    def update_level_name(self, level_name):
        self.setting_name = True
        self.name_var.set(level_name)
        self.setting_name = False

    def update_theme(self, theme, subtheme):
        self.selected_theme = theme
        self.selected_subtheme = subtheme
        theme_name = name_of_theme(theme)
        self.theme_combobox.set(theme_name)
        if subtheme is not None:
            subtheme_name = name_of_theme(subtheme)
            self.subtheme_combobox.set(subtheme_name)
        self.update_theme_controls()
        self.update_theme_label()

    def update_theme_label(self):
        theme_name = str(self.theme_combobox.get())
        theme = theme_for_name(theme_name)
        subtheme_name = str(self.subtheme_combobox.get())
        if (
            theme == Theme.COSMIC_OCEAN
            and subtheme_name is not None
            and subtheme_name != ""
        ):
            theme_description = theme_name + " (" + subtheme_name + ")"
        else:
            theme_description = theme_name
        self.theme_label["text"] = "Level Theme: " + theme_description

    def update_theme_controls(self):
        theme_name = str(self.theme_combobox.get())
        theme = theme_for_name(theme_name)
        if theme == Theme.COSMIC_OCEAN:
            self.subtheme_combobox.grid()
            self.theme_select_button.grid(row=1)
        else:
            self.subtheme_combobox.grid_remove()
            self.theme_select_button.grid(row=0)

    def update_background_theme(self, theme, subtheme):
        theme_name = name_of_theme(theme)
        self.background_theme_combobox.set(theme_name)
        if subtheme is not None:
            subtheme_name = name_of_theme(subtheme)
            self.background_subtheme_combobox.set(subtheme_name)
        self.update_background_theme_controls()
        self.update_background_theme_label()

    def update_background_theme_label(self):
        theme_name = str(self.background_theme_combobox.get())
        theme = theme_for_name(theme_name)
        subtheme_name = str(self.background_subtheme_combobox.get())
        if (
            theme == Theme.COSMIC_OCEAN
            and subtheme_name is not None
            and subtheme_name != ""
            and subtheme_name != "Default"
        ):
            theme_description = theme_name + " (" + subtheme_name + ")"
        else:
            theme_description = theme_name
        self.background_theme_label["text"] = "Background Theme: " + theme_description

    def update_background_theme_controls(self):
        theme_name = str(self.background_theme_combobox.get())
        theme = theme_for_name(theme_name)
        if theme == Theme.COSMIC_OCEAN:
            self.background_subtheme_combobox.grid()
            self.background_theme_select_button.grid(row=1)
        else:
            self.background_subtheme_combobox.grid_remove()
            self.background_theme_select_button.grid(row=0)

    def update_level_size(self, width, height):
        self.lvl_width = width
        self.lvl_height = height
        self.width_combobox.set(width)
        self.height_combobox.set(height)
        self.size_label["text"] = "Level size: {width} x {height}".format(
            width=width, height=height
        )

    def update_border_theme(self, theme, loop):
        theme_name = name_of_border_theme(theme)
        self.border_theme_combobox.set(theme_name)
        self.loop_manually_toggled = False
        self.loop_var.set(False)
        if loop is not None:
            self.loop_manually_toggled = True
            self.loop_var.set(loop)
        self.update_border_theme_label()

    def update_border_entity_theme(self, theme):
        theme_name = name_of_border_entity_theme(theme)
        self.border_entity_theme_combobox.set(theme_name)
        self.update_border_entity_theme_label()

    def update_floor_theme(self, theme):
        theme_name = name_of_theme(theme)
        self.floor_theme_combobox.set(theme_name)
        self.update_floor_theme_label()

    def update_music_theme(self, theme):
        theme_name = name_of_theme(theme)
        self.music_theme_combobox.set(theme_name)
        self.update_music_theme_label()

    def update_border_theme_label(self):
        theme_name = str(self.border_theme_combobox.get())
        if self.loop_manually_toggled:
            loops = self.loop_var.get()
            if loops:
                theme_description = theme_name + " (Loops)"
            else:
                theme_description = theme_name + " (Doesn't Loop)"
        else:
            theme_description = theme_name
        self.border_theme_label["text"] = "Border Type: " + theme_description

    def update_border_entity_theme_label(self):
        theme_name = str(self.border_entity_theme_combobox.get())
        self.border_entity_theme_label["text"] = "Border Entity: " + theme_name

    def update_floor_theme_label(self):
        theme_name = str(self.floor_theme_combobox.get())
        self.floor_theme_label["text"] = "Floor Theme: " + theme_name

    def update_music_theme_label(self):
        theme_name = str(self.music_theme_combobox.get())
        self.music_theme_label["text"] = "Music Theme: " + theme_name

    def update_skip_co_fix(self, skip_co_fix):
        self.co_fix_var.set(skip_co_fix)

    def update_spawn_jelly(self, spawn_jelly):
        self.jelly_var.set(spawn_jelly)

    def set_sequence_exists(self, sequence_exists):
        self.sequence_exists = sequence_exists
        self.update_sequence_warning_message()

    def set_level_in_sequence(self, level_in_sequence):
        self.level_in_sequence = level_in_sequence
        self.update_sequence_warning_message()

    def update_sequence_warning_message(self):
        self.sequence_warning_container.grid()
        if not self.sequence_exists:
            self.sequence_warning_label[
                "text"
            ] = "Warning: This mod is not configured to save a level sequence. Advanced level configuration will be lost."
        elif not self.level_in_sequence:
            self.sequence_warning_label[
                "text"
            ] = "Warning: This level is not in the level sequence. Advanced level configuration will be saved but not used."
        else:
            self.sequence_warning_container.grid_remove()

    def enable_controls(self):
        self.theme_combobox["state"] = "readonly"
        self.subtheme_combobox["state"] = "readonly"
        self.border_theme_combobox["state"] = "readonly"
        self.border_entity_theme_combobox["state"] = "readonly"
        self.width_combobox["state"] = "readonly"
        self.height_combobox["state"] = "readonly"
        self.background_theme_combobox["state"] = "readonly"
        self.background_subtheme_combobox["state"] = "readonly"
        self.floor_theme_combobox["state"] = "readonly"
        self.music_theme_combobox["state"] = "readonly"
        self.name_entry["state"] = tk.NORMAL

    def disable_controls(self):
        self.theme_combobox["state"] = tk.DISABLED
        self.subtheme_combobox["state"] = tk.DISABLED
        self.theme_select_button["state"] = tk.DISABLED
        self.border_theme_combobox["state"] = tk.DISABLED
        self.border_theme_select_button["state"] = tk.DISABLED
        self.border_entity_theme_combobox["state"] = tk.DISABLED
        self.border_entity_theme_select_button["state"] = tk.DISABLED
        self.width_combobox["state"] = tk.DISABLED
        self.height_combobox["state"] = tk.DISABLED
        self.size_select_button["state"] = tk.DISABLED
        self.background_theme_combobox["state"] = tk.DISABLED
        self.background_subtheme_combobox["state"] = tk.DISABLED
        self.background_theme_select_button["state"] = tk.DISABLED
        self.floor_theme_combobox["state"] == tk.DISABLED
        self.floor_theme_select_button["state"] = tk.DISABLED
        self.music_theme_combobox["state"] = tk.DISABLED
        self.music_theme_select_button["state"] = tk.DISABLED
        self.name_entry["state"] = tk.DISABLED
