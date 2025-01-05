import tkinter as tk
from tkinter import ttk

from modlunky2.mem.state import Theme

def name_of_theme(theme):
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


class LevelConfigurationPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        on_select_theme,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_select_theme = on_select_theme

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

        def update_theme():
            theme_name = str(self.theme_combobox.get())
            theme = theme_for_name(theme_name)
            self.theme_select_button["state"] = tk.DISABLED
            self.theme_label["text"] = "Level Theme: " + theme_name
            self.on_select_theme(theme)

        self.theme_select_button = tk.Button(
            theme_container,
            text="Update Theme",
            bg="yellow",
            command=update_theme,
        )
        self.theme_select_button["state"] = tk.DISABLED
        self.theme_select_button.grid(row=0, column=2, sticky="nse")

        def theme_selected(_):
            self.theme_select_button["state"] = tk.NORMAL

        self.theme_combobox.bind("<<ComboboxSelected>>", theme_selected)

        settings_row += 1
        self.rowconfigure(settings_row, minsize=20)
        settings_row += 1

    def update_theme(self, theme):
        theme_name = name_of_theme(theme)
        self.theme_combobox.set(theme_name)
        self.theme_label["text"] = "Level Theme: " + theme_name

    def enable_controls(self):
        self.theme_combobox["state"] = "readonly"

    def disable_controls(self):
        self.theme_combobox["state"] = tk.DISABLED
        self.theme_select_button["state"] = tk.DISABLED
