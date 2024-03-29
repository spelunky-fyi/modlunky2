import logging
import tkinter as tk
from tkinter import ttk, colorchooser, font
from modlunky2.config import Config

from modlunky2.ui.widgets import PopupWindow
from modlunky2.utils import open_directory

from modlunky2.ui.trackers.utils import get_text_color
from modlunky2.ui.trackers.common import TRACKERS_DIR

logger = logging.getLogger(__name__)


COLOR_GREEN = "#00ff00"
COLOR_MAGENTA = "#ff00ff"
COLOR_BLUE = "#0000ff"


class ChooseColor(PopupWindow):
    def __init__(
        self, options_frame: "OptionsFrame", ml_config: Config, *args, **kwargs
    ):
        super().__init__("Choose Color Key", ml_config, *args, **kwargs)
        self.options_frame = options_frame
        self.modlunky_config = ml_config
        self.columnconfigure(0, weight=1)

        color_buttons = ttk.Frame(self)
        color_buttons.grid(row=0, column=0, sticky="nsew")
        color_buttons.columnconfigure(0, weight=1)

        ttk.Button(
            color_buttons,
            text="Magenta",
            command=lambda: self.update_color_label(COLOR_MAGENTA),
        ).grid(row=0, column=0, padx=2, pady=5, sticky="nsew")
        ttk.Button(
            color_buttons,
            text="Green",
            command=lambda: self.update_color_label(COLOR_GREEN),
        ).grid(row=0, column=1, padx=2, pady=5, sticky="nsew")
        ttk.Button(
            color_buttons,
            text="Blue",
            command=lambda: self.update_color_label(COLOR_BLUE),
        ).grid(row=0, column=2, padx=2, pady=5, sticky="nsew")
        ttk.Button(
            color_buttons,
            text="Custom",
            command=self.pick_color,
        ).grid(row=0, column=3, padx=2, pady=5, sticky="nsew")

        ttk.Separator(self).grid(row=1, column=0, pady=5, sticky="nsew")

        self.color_label = tk.Label(
            self,
            font=tk.font.Font(
                family=self.modlunky_config.tracker_font_family, size=16, weight="bold"
            ),
        )
        self.color_label.grid(row=2, column=0, ipadx=5, padx=5, pady=5, sticky="nsew")

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

        color_key = self.modlunky_config.tracker_color_key
        self.update_color_label(color_key)

    def save_choice(self):
        self.modlunky_config.tracker_color_key = self.color_label["text"]
        self.modlunky_config.save()
        self.options_frame.render()
        self.destroy()

    def pick_color(self):
        _, hex_code = colorchooser.askcolor(parent=self, title="Choose color")
        if hex_code is None:
            return
        self.update_color_label(hex_code)

    def update_color_label(self, color_key):
        self.color_label.config(
            text=color_key,
            bg=color_key,
            fg=get_text_color(color_key),
        )


class OptionsFrame(ttk.LabelFrame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, text="Options", *args, **kwargs)
        self.ml_config = ml_config

        self.columnconfigure(0, weight=1)

        self.rowconfigure(0, minsize=60)
        self.rowconfigure(5, minsize=60)

        self.color_button = ttk.Button(
            self, text="Color Key", command=self.choose_color
        )
        self.color_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.color_label = tk.Label(
            self,
            font=tk.font.Font(
                family=self.ml_config.tracker_font_family, size=16, weight="bold"
            ),
        )
        self.color_label.grid(row=0, column=1, ipadx=5, padx=5, pady=5, sticky="nsew")

        self.font_size = tk.IntVar(value=self.ml_config.tracker_font_size)
        self.font_label = ttk.Label(self, text=self.get_font_size_label())
        self.font_label.grid(
            row=1, column=0, columnspan=2, pady=(5, 5), padx=(5, 5), sticky="nswe"
        )
        self.font_slider = ttk.Scale(
            self,
            from_=10,
            to=80,
            orient="horizontal",
            command=parent.register(self.font_changed),
            variable=self.font_size,
        )
        self.font_slider.grid(
            row=2, column=0, columnspan=2, pady=(5, 5), padx=(5, 5), sticky="nswe"
        )

        self.font_family = tk.StringVar(value=self.ml_config.tracker_font_family)
        self.font_family_label = ttk.Label(self, text="Font family:")
        self.font_family_label.grid(
            row=3, column=0, columnspan=2, pady=(5, 5), padx=(5, 5), sticky="nswe"
        )
        self.font_family_input = ttk.Combobox(
            self,
            textvariable=self.font_family,
            validate="all",
            values=list(font.families()),
        )
        self.font_family_input["validatecommand"] = (
            self.font_family_input.register(self.font_family_changed),
            "%P",
        )
        self.font_family_input.bind("<<ComboboxSelected>>", self.font_family_picked)
        self.font_family_input.grid(
            row=4, column=0, columnspan=2, pady=(5, 5), padx=(5, 5), sticky="nswe"
        )

        ttk.Button(
            self, text="Tracker Files", command=lambda: open_directory(TRACKERS_DIR)
        ).grid(row=5, column=0, columnspan=2, pady=(5, 5), padx=(5, 5), sticky="nswe")

    def get_font_size_label(self):
        return f"Font size: {self.font_size.get()}"

    def font_changed(self, _event=None):
        self.font_label.configure(text=self.get_font_size_label())
        self.ml_config.tracker_font_size = int(self.font_size.get())
        self.ml_config.save()
        return True

    def font_family_changed(self, family=None):
        self.ml_config.tracker_font_family = family
        self.ml_config.save()
        self.color_label.config(
            font=tk.font.Font(
                family=self.ml_config.tracker_font_family, size=16, weight="bold"
            ),
        )
        return True

    def font_family_picked(self, _event=None):
        return self.font_family_changed(self.font_family.get())

    def render(self):
        color_key = self.ml_config.tracker_color_key
        self.color_label.config(
            font=tk.font.Font(
                family=self.ml_config.tracker_font_family, size=16, weight="bold"
            ),
            text=color_key,
            bg=color_key,
            fg=get_text_color(color_key),
        )

    def choose_color(self):
        ChooseColor(options_frame=self, ml_config=self.ml_config)
