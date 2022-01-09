import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.config import CategoryTrackerConfig, Config
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowData,
)
from modlunky2.ui.trackers.runstate import RunState

logger = logging.getLogger("modlunky2")


ICON_PATH = BASE_DIR / "static/images"


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.cat_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "cat2.png").resize((24, 24), Image.ANTIALIAS)
        )

        self.category_button = ttk.Button(
            self,
            image=self.cat_icon,
            text="Category",
            compound="left",
            command=self.launch,
        )
        self.category_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.always_show_modifiers = tk.BooleanVar()
        self.always_show_modifiers.set(
            modlunky_config.trackers.category.always_show_modifiers
        )
        self.always_show_modifiers_checkbox = ttk.Checkbutton(
            self,
            text="Always Show Modifiers",
            variable=self.always_show_modifiers,
            onvalue=True,
            offvalue=False,
            command=self.toggle_always_show_modifiers,
        )
        self.always_show_modifiers_checkbox.grid(
            row=0, column=1, pady=5, padx=5, sticky="nw"
        )

    def toggle_always_show_modifiers(self):
        self.modlunky_config.trackers.category.always_show_modifiers = (
            self.always_show_modifiers.get()
        )
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.category)

    def launch(self):
        color_key = self.modlunky_config.tracker_color_key
        self.disable_button()
        self.window = TrackerWindow(
            title="Category Tracker",
            color_key=color_key,
            on_close=self.window_closed,
            file_name="category.txt",
            tracker=CategoryTracker(),
            config=self.modlunky_config.trackers.category,
        )

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.category_button.winfo_exists():
            self.category_button["state"] = tk.NORMAL

    def disable_button(self):
        self.category_button["state"] = tk.DISABLED


class CategoryTracker(Tracker[CategoryTrackerConfig, WindowData]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proc = None
        self.time_total = None
        self.run_state = None

    def initialize(self):
        self.time_total = 0
        self.run_state = RunState()

    def poll(self, proc: Spel2Process, config: CategoryTrackerConfig) -> WindowData:
        game_state = proc.get_state()
        if game_state is None:
            return None

        # Check if we've reset, if so, reinitialize
        new_time_total = game_state.time_total
        if new_time_total < self.time_total:
            self.initialize()
        self.time_total = new_time_total

        self.run_state.update(game_state)
        label = self.run_state.get_display(
            game_state.screen, config.always_show_modifiers
        )
        return WindowData(label)
