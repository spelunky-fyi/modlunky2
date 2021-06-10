import logging
import time
import threading
import tkinter as tk
from queue import Queue, Empty
from tkinter import PhotoImage, ttk


from modlunky2.constants import BASE_DIR
from modlunky2.mem.state import RunRecapFlags
from modlunky2.ui.widgets import Tab
from modlunky2.utils import tb_info
from modlunky2.mem import find_spelunky2_pid, Spel2Process

from .pacifist import PacifistWindow

logger = logging.getLogger("modlunky2")


class TrackersTab(Tab):
    def __init__(self, tab_control, modlunky_config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.modlunky_config = modlunky_config

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.trackers_frame = ttk.LabelFrame(self, text="Trackers")
        self.trackers_frame.grid(sticky="nsew")

        self.trackers_frame.rowconfigure(1, minsize=60)
        self.trackers_frame.rowconfigure(2, weight=1)
        self.trackers_frame.columnconfigure(0, weight=1)

        self.button_pacifist = ttk.Button(
            self.trackers_frame,
            text="Pacifist",
            command=self.pacifist,
        )
        self.button_pacifist.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

    def enable_pacifist_button(self):
        self.button_pacifist["state"] = tk.NORMAL

    def disable_pacifist_button(self):
        self.button_pacifist["state"] = tk.DISABLED

    def pacifist(self):
        self.disable_pacifist_button()
        PacifistWindow(
            title="Pacifist Tracker",
            on_close=self.on_pacifist_close,
        )

    def on_pacifist_close(self):
        self.enable_pacifist_button()
