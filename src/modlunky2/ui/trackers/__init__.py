import logging
from tkinter import ttk

from modlunky2.config import Config
from modlunky2.ui.widgets import Tab

from .options import OptionsFrame
from .pacifist import PacifistButtons

logger = logging.getLogger("modlunky2")


class TrackersFrame(ttk.LabelFrame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, text="Trackers", *args, **kwargs)
        self.ml_config = ml_config

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        PacifistButtons(self, ml_config=self.ml_config).grid(
            row=0,
            column=0,
            sticky="nswe",
        )


class TrackersTab(Tab):
    def __init__(self, tab_control, ml_config: Config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.ml_config = ml_config

        self.rowconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)
        self.trackers_frame = TrackersFrame(self, ml_config)
        self.trackers_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.columnconfigure(1, minsize=300)
        self.options_frame = OptionsFrame(self, ml_config)
        self.options_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    def on_load(self):
        self.options_frame.render()
