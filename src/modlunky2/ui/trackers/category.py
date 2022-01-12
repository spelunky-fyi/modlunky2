import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.config import CategoryTrackerConfig, Config, SaveableCategory
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


class CategoryModifiers(ttk.LabelFrame):
    def __init__(
        self, parent, category_tracker_config: CategoryTrackerConfig, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.category_tracker_config = category_tracker_config

        self.always_show_modifiers = tk.BooleanVar()
        self.always_show_modifiers.set(
            self.category_tracker_config.always_show_modifiers
        )

        widgets = []
        widgets.append(
            ttk.Checkbutton(
                self,
                text="Show all modifiers before 1-3",
                variable=self.always_show_modifiers,
                onvalue=True,
                offvalue=False,
                command=self.toggle_always_show_modifiers,
            )
        )
        widgets.append(ttk.Separator(self))

        # Starting Category Exclusion

        ## This does not have any effect on the actual tracking logic, rather,
        ## like always_show_modifiers, it only has an effect on the actual
        ## text returned.

        ## The checkboxes imply *inclusion*, not exclusion, so the
        ## boolean logic here is inverted.
        loaded_config = frozenset(self.category_tracker_config.excluded_categories)

        if loaded_config is None:
            loaded_config = frozenset()

        self.variables_by_category = {}
        for category in SaveableCategory:
            variable = tk.BooleanVar()
            checkbox = ttk.Checkbutton(
                self,
                text=category.value,
                variable=variable,
                onvalue=True,
                offvalue=False,
                command=self.toggle_excluded_categories,
            )
            if category not in loaded_config:
                variable.set(True)

            self.variables_by_category[category] = variable
            widgets.append(checkbox)

        for column, widget in enumerate(widgets):
            widget.grid(row=0, column=column, pady=5, padx=5, sticky="nw")

    def toggle_always_show_modifiers(self):
        self.category_tracker_config.always_show_modifiers = (
            self.always_show_modifiers.get()
        )
        self.parent.config_update_callback()

    def toggle_excluded_categories(self):
        self.category_tracker_config.excluded_categories = set(
            [c for c, v in self.variables_by_category.items() if not v.get()]
        )
        self.parent.config_update_callback()


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
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

        self.modifiers = CategoryModifiers(
            self, self.modlunky_config.trackers.category, text="Modifiers"
        )
        self.modifiers.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

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

    def config_update_callback(self):
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.category)

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
        label = self.run_state.get_display(game_state.screen, config)
        return WindowData(label)
