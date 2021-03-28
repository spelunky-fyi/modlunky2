import logging
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from modlunky2.ui.widgets import Tab

logger = logging.getLogger("modlunky2")


class InstallTab(Tab):
    def __init__(self, tab_control, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        install_frame = ttk.LabelFrame(self, text="Install")
        install_frame.rowconfigure(0, weight=1)
        install_frame.columnconfigure(0, weight=1)
        install_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")
