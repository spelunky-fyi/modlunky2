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
    if theme == Theme.DWELLING or theme == Theme.TIDE_POOL or theme == Theme.JUNGLE or theme == Theme.TEMPLE or theme == Theme.COSMIC_OCEAN or theme == Theme.CITY_OF_GOLD or theme == Theme.DUAT or theme == Theme.ABZU or theme == Theme.EGGPLANT_WORLD or theme == Theme.ICE_CAVES or theme == Theme.OLMEC or theme == Theme.VOLCANA or theme == Theme.TIAMAT or theme == Theme.HUNDUN or theme == Theme.BASE_CAMP:
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
    if theme == Theme.DWELLING or theme == Theme.NEO_BABYLON or theme == Theme.SUNKEN_CITY or theme == Theme.TIDE_POOL or theme == Theme.JUNGLE or theme == Theme.TEMPLE or theme == Theme.CITY_OF_GOLD or theme == Theme.ABZU or theme == Theme.EGGPLANT_WORLD or theme == Theme.OLMEC or theme == Theme.VOLCANA or theme == Theme.HUNDUN or theme == Theme.BASE_CAMP:
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
        on_select_theme,
        on_select_border_theme,
        on_select_border_entity_theme,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_select_theme = on_select_theme
        self.on_select_border_theme = on_select_border_theme
        self.on_select_border_entity_theme = on_select_border_entity_theme

        self.columnconfigure(0, weight=1)
        right_padding = 10
        self.columnconfigure(1, minsize=right_padding)

        settings_row = 0

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
            self.on_select_border_theme(theme)

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

        settings_row += 1

        border_entity_theme_label = tk.Label(self, text="Border Entity:")
        border_entity_theme_label.grid(row=settings_row, column=0, sticky="nsw")
        self.border_entity_theme_label = border_entity_theme_label

        settings_row += 1

        border_entity_theme_container = ttk.Frame(self)
        border_entity_theme_container.grid(row=settings_row, column=0, sticky="news")
        border_entity_theme_container.columnconfigure(1, weight=1)

        self.border_entity_theme_combobox = ttk.Combobox(border_entity_theme_container, height=25)
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

        self.border_entity_theme_combobox.bind("<<ComboboxSelected>>", border_entity_theme_selected)

        settings_row += 1


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
        if theme == Theme.COSMIC_OCEAN and subtheme_name is not None and subtheme_name is not "":
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


    def update_border_theme(self, theme):
        theme_name = name_of_border_theme(theme)
        self.border_theme_combobox.set(theme_name)
        self.update_border_theme_label()

    def update_border_entity_theme(self, theme):
        theme_name = name_of_border_entity_theme(theme)
        self.border_entity_theme_combobox.set(theme_name)
        self.update_border_entity_theme_label()

    def update_border_theme_label(self):
        theme_name = str(self.border_theme_combobox.get())
        self.border_theme_label["text"] = "Border Type: " + theme_name

    def update_border_entity_theme_label(self):
        theme_name = str(self.border_theme_combobox.get())
        self.border_entity_theme_label["text"] = "Border Entity: " + theme_name

    def enable_controls(self):
        self.theme_combobox["state"] = "readonly"
        self.subtheme_combobox["state"] = "readonly"
        self.border_theme_combobox["state"] = "readonly"
        self.border_entity_theme_combobox["state"] = "readonly"

    def disable_controls(self):
        self.theme_combobox["state"] = tk.DISABLED
        self.subtheme_combobox["state"] = tk.DISABLED
        self.theme_select_button["state"] = tk.DISABLED
        self.border_theme_combobox["state"] = tk.DISABLED
        self.border_theme_select_button["state"] = tk.DISABLED
        self.border_entity_theme_combobox["state"] = tk.DISABLED
        self.border_entity_theme_select_button["state"] = tk.DISABLED
