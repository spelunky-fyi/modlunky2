import logging
import tkinter as tk
from tkinter import ttk, colorchooser
from modlunky2.config import Config


from modlunky2.ui.widgets import PopupWindow, Tab

from .pacifist import PacifistButtons, PacifistWindow

logger = logging.getLogger("modlunky2")


CHROMA_GREEN = "#00ff00"
CHROMA_MAGENTA = "#ff00ff"
CHROMA_BLUE = "#0000ff"


def hex_to_rgb(hex_value):
    return tuple(int(hex_value[idx : idx + 2], 16) for idx in (0, 2, 4))


def get_text_color(bg_color):
    rgb = hex_to_rgb(bg_color.lstrip("#"))
    if (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114) > 160:
        return "#000000"
    return "#ffffff"


class ChooseChroma(PopupWindow):
    def __init__(
        self, options_frame: "OptionsFrame", ml_config: Config, *args, **kwargs
    ):
        super().__init__("Choose Chroma Key", ml_config, *args, **kwargs)
        self.options_frame = options_frame
        self.ml_config = ml_config
        self.columnconfigure(0, weight=1)

        color_buttons = ttk.Frame(self)
        color_buttons.grid(row=0, column=0, sticky="nsew")
        color_buttons.columnconfigure(0, weight=1)

        ttk.Button(
            color_buttons,
            text="Magenta",
            command=lambda: self.update_chroma_label(CHROMA_MAGENTA),
        ).grid(row=0, column=0, padx=2, pady=5, sticky="nsew")
        ttk.Button(
            color_buttons,
            text="Green",
            command=lambda: self.update_chroma_label(CHROMA_GREEN),
        ).grid(row=0, column=1, padx=2, pady=5, sticky="nsew")
        ttk.Button(
            color_buttons,
            text="Blue",
            command=lambda: self.update_chroma_label(CHROMA_BLUE),
        ).grid(row=0, column=2, padx=2, pady=5, sticky="nsew")
        ttk.Button(
            color_buttons,
            text="Custom",
            command=self.pick_color,
        ).grid(row=0, column=3, padx=2, pady=5, sticky="nsew")

        ttk.Separator(self).grid(row=1, column=0, pady=5, sticky="nsew")

        self.chroma_label = tk.Label(
            self, font=tk.font.Font(family="Helvitica", size=16, weight="bold")
        )
        self.chroma_label.grid(row=2, column=0, ipadx=5, padx=5, pady=5, sticky="nsew")

        ttk.Separator(self).grid(row=3, column=0, pady=5, sticky="nsew")

        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ttk.Button(
            buttons,
            text="Ok",
            command=self.save_choice,
        ).grid(row=0, column=0, padx=1, pady=5, sticky="nsew")
        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).grid(row=0, column=1, padx=1, pady=5, sticky="nsew")

        chroma_key = self.ml_config.config_file.tracker_chroma_key
        self.update_chroma_label(chroma_key)

    def save_choice(self):
        self.ml_config.config_file.tracker_chroma_key = self.chroma_label["text"]
        self.ml_config.config_file.save()
        self.options_frame.render()
        self.destroy()

    def pick_color(self):
        _, hex_code = colorchooser.askcolor(parent=self, title="Choose color")
        if hex_code is None:
            return
        self.update_chroma_label(hex_code)

    def update_chroma_label(self, chroma_key):
        self.chroma_label.config(
            text=chroma_key,
            bg=chroma_key,
            fg=get_text_color(chroma_key),
        )


class OptionsFrame(ttk.LabelFrame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, text="Options", *args, **kwargs)
        self.ml_config = ml_config

        self.columnconfigure(0, weight=1)

        self.rowconfigure(0, minsize=60)
        self.chroma_button = ttk.Button(
            self, text="Chroma Key", command=self.choose_chroma
        )
        self.chroma_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.chroma_label = tk.Label(
            self, font=tk.font.Font(family="Helvitica", size=16, weight="bold")
        )
        self.chroma_label.grid(row=0, column=1, ipadx=5, padx=5, pady=5, sticky="nsew")

    def render(self):
        chroma_key = self.ml_config.config_file.tracker_chroma_key
        self.chroma_label.config(
            text=chroma_key,
            bg=chroma_key,
            fg=get_text_color(chroma_key),
        )

    def choose_chroma(self):
        ChooseChroma(options_frame=self, ml_config=self.ml_config)


class TrackersTab(Tab):
    def __init__(self, tab_control, ml_config: Config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.ml_config = ml_config

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=300)
        self.trackers_frame = ttk.LabelFrame(self, text="Trackers")
        self.trackers_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.trackers_frame.rowconfigure(1, weight=1)
        self.trackers_frame.columnconfigure(0, weight=1)

        PacifistButtons(self.trackers_frame, ml_config=self.ml_config).grid(
            row=0, column=0, sticky="nswe"
        )

        self.options_frame = OptionsFrame(self, ml_config)
        self.options_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    def on_load(self):
        self.options_frame.render()
