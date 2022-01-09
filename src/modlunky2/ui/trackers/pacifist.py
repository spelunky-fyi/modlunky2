import dataclasses
from enum import Enum
import logging
from logging import CRITICAL, WARNING
import tkinter as tk
from tkinter import ttk
from queue import Empty

from modlunky2.config import Config, PacifistTrackerConfig
from modlunky2.mem import Spel2Process
from modlunky2.mem.state import RunRecapFlags

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowKey,
)

logger = logging.getLogger("modlunky2")


class Command(Enum):
    IS_PACIFIST = "is_pacifist"


class PacifistButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.pacifist_button = ttk.Button(
            self,
            text="Pacifist",
            command=self.launch,
        )
        self.pacifist_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.show_kill_count = tk.BooleanVar()
        self.show_kill_count.set(self.modlunky_config.trackers.pacifist.show_kill_count)
        self.show_kill_count_checkbox = ttk.Checkbutton(
            self,
            text="Show Kill Count",
            variable=self.show_kill_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_kill_count,
        )
        self.show_kill_count_checkbox.grid(row=0, column=1, pady=5, padx=5, sticky="nw")

    def toggle_show_kill_count(self):
        self.modlunky_config.trackers.pacifist.show_kill_count = (
            self.show_kill_count.get()
        )
        self.modlunky_config.save()

    def launch(self):
        color_key = self.modlunky_config.tracker_color_key
        self.disable_button()
        self.window = TrackerWindow(
            title="Pacifist Tracker",
            color_key=color_key,
            on_close=self.window_closed,
            file_name="pacifist.txt",
            tracker=PacifistTracker(),
            config=self.modlunky_config.trackers.pacifist.clone(),
        )

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.pacifist_button.winfo_exists():
            self.pacifist_button["state"] = tk.NORMAL

    def disable_button(self):
        self.pacifist_button["state"] = tk.DISABLED


class PacifistTracker(Tracker[PacifistTrackerConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kills_total = 0

    def initialize(self):
        self.kills_total = 0

    def poll(self, proc: Spel2Process, config: PacifistTrackerConfig):
        game_state = proc.get_state()
        if game_state is None:
            return None

        run_recap_flags = game_state.run_recap_flags

        player = None
        if game_state.items is not None:
            player = game_state.items.players[0]
        if player is not None and player.inventory is not None:
            self.kills_total = player.inventory.kills_total

        is_pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)
        label = self.get_text(is_pacifist, config)
        return {WindowKey.DISPLAY_STRING: label}

    def get_text(self, is_pacifist: bool, config: PacifistTrackerConfig):
        if is_pacifist:
            return "Pacifist"

        if config.show_kill_count:
            return f"MURDERED {self.kills_total}!"

        return "MURDERER!"
