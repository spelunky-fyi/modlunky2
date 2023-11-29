import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.config import Config, PacifistTrackerConfig
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process
from modlunky2.mem.state import RunRecapFlags

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowData,
)

logger = logging.getLogger(__name__)


ICON_PATH = BASE_DIR / "static/images"


class PacifistModifiers(ttk.LabelFrame):
    def __init__(
        self, parent, pacifist_tracker_config: PacifistTrackerConfig, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.pacifist_tracker_config = pacifist_tracker_config

        self.show_kill_count = tk.BooleanVar()
        self.show_kill_count.set(self.pacifist_tracker_config.show_kill_count)
        self.show_kill_count_checkbox = ttk.Checkbutton(
            self,
            text="Show Kill Count",
            variable=self.show_kill_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_kill_count,
        )
        self.show_kill_count_checkbox.grid(row=0, column=1, pady=5, padx=5, sticky="w")

    def toggle_show_kill_count(self):
        self.pacifist_tracker_config.show_kill_count = self.show_kill_count.get()
        self.parent.config_update_callback()


class PacifistButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1, minsize=200)
        self.columnconfigure(1, weight=10000)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.pacifist_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "pacifist.png").resize(
                (24, 24), Image.Resampling.LANCZOS
            )
        )

        self.pacifist_button = ttk.Button(
            self,
            text="Pacifist",
            image=self.pacifist_icon,
            compound="left",
            command=self.launch,
            width=1,
        )
        self.pacifist_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.modifiers = PacifistModifiers(
            self, self.modlunky_config.trackers.pacifist, text="Options"
        )
        self.modifiers.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

    def launch(self):
        self.disable_button()
        self.window = TrackerWindow(
            title="Pacifist Tracker",
            color_key=self.modlunky_config.tracker_color_key,
            font_size=self.modlunky_config.tracker_font_size,
            font_family=self.modlunky_config.tracker_font_family,
            on_close=self.window_closed,
            file_name="pacifist.txt",
            tracker=PacifistTracker(),
            config=self.modlunky_config.trackers.pacifist,
        )

    def config_update_callback(self):
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.pacifist)

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.pacifist_button.winfo_exists():
            self.pacifist_button["state"] = tk.NORMAL

    def disable_button(self):
        self.pacifist_button["state"] = tk.DISABLED


class PacifistTracker(Tracker[PacifistTrackerConfig, WindowData]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kills_total = 0

    def initialize(self):
        self.kills_total = 0

    def poll(self, proc: Spel2Process, config: PacifistTrackerConfig) -> WindowData:
        game_state = proc.get_state()
        if game_state is None:
            return None

        run_recap_flags = game_state.run_recap_flags

        if game_state.items is not None:
            total_kills = 0
            for inventory in game_state.items.player_inventory:
                if inventory is not None:
                    total_kills += inventory.kills_total
            self.kills_total = total_kills

        is_pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)
        label = self.get_text(is_pacifist, config)
        return WindowData(label)

    def get_text(self, is_pacifist: bool, config: PacifistTrackerConfig):
        if is_pacifist:
            return "Pacifist"

        if config.show_kill_count:
            return f"MURDERED {self.kills_total}!"

        return "MURDERER!"
