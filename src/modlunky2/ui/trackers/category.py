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
from modlunky2.ui.trackers.label import Label

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

        # Starting Category Exclusion
        ## This does not have any effect on the actual tracking logic, rather,
        ## like always_show_modifiers, it only has an effect on the actual
        ## text returned.
        self.category_exclude_label = ttk.Label(
            self,
            text="Exclude Starting Categories"
        )
        self.category_exclude_label.grid(row=1, column=0, padx=5, pady=5, sticky="nw")

        self.excludable_dict = {}

        # You can exclude any starting category that is non-terminal, i.e., any of them except Any%
        valid_excludable_categories = [l for l in Label if l.value.start and not l.value.terminus]
        excluded_loaded = modlunky_config.trackers.category.excluded_categories

        # Sort by '%' then by name descending
        valid_excludable_categories.sort(key=lambda l: (l.value.percent_priority is not None, l.name), reverse=True)

        row=2
        for category in valid_excludable_categories:
            variable = tk.BooleanVar()
            checkbox = ttk.Checkbutton(
                self,
                text=f"{category.value.text}{'%' if category.value.percent_priority is not None else ''}",
                variable=variable,
                onvalue=True,
                offvalue=False,
                command=self.toggle_excluded_categories,
            )
            if category.name in excluded_loaded:
                variable.set(True)
            checkbox.grid(row=row, column=0, padx=5, pady=5, sticky="nw")
            row += 1

            self.excludable_dict[category] = (checkbox, variable)

    def toggle_always_show_modifiers(self):
        self.modlunky_config.trackers.category.always_show_modifiers = (
            self.always_show_modifiers.get()
        )
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.category)

    def toggle_excluded_categories(self):
        self.modlunky_config.trackers.category.excluded_categories = [
            c.name for c, v in self.excludable_dict.items() if v[1].get()
        ]
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
            game_state.screen, config.always_show_modifiers, config.excluded_categories
        )
        return WindowData(label)
