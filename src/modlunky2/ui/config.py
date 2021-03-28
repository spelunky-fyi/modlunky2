import logging
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from modlunky2.ui.widgets import Tab, ToolTip
from modlunky2.config import guess_install_dir

logger = logging.getLogger("modlunky2")


class InstallDir(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent, text="Install Directory")
        self.modlunky_config = modlunky_config

        install_dir_label = ttk.Label(
            self, text="The directory where Spelunky 2 is installed"
        )
        install_dir_label.grid(
            row=0, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.install_dir_var = tk.StringVar(
            value=self.modlunky_config.config_file.install_dir
        )
        install_dir_entry = ttk.Entry(
            self,
            textvariable=self.install_dir_var,
            state=tk.DISABLED,
            width=80,
        )
        install_dir_entry.columnconfigure(0, weight=1)
        install_dir_entry.columnconfigure(1, weight=1)
        install_dir_entry.columnconfigure(2, weight=1)
        install_dir_entry.grid(
            row=1, column=0, padx=10, pady=10, columnspan=3, sticky="n"
        )

        install_dir_browse = ttk.Button(
            self, text="Browse", command=self.browse_install_dir
        )
        install_dir_browse.grid(row=2, column=0, pady=5, padx=5, sticky="nsew")

        install_dir_lucky = ttk.Button(
            self, text="I'm Feeling Lucky", command=self.feeling_lucky
        )
        install_dir_lucky.grid(row=2, column=1, pady=5, padx=5, sticky="nsew")

        install_dir_clear = ttk.Button(
            self, text="Clear", command=self.clear_install_dir
        )
        install_dir_clear.grid(row=2, column=2, pady=5, padx=5, sticky="nsew")

    def browse_install_dir(self):
        install_dir = self.install_dir_var.get()
        directory = tk.filedialog.askdirectory(initialdir=install_dir)
        if directory:
            self.install_dir_var.set(directory)
            self.modlunky_config.config_file.install_dir = Path(directory)
            self.modlunky_config.config_file.save()

    def feeling_lucky(self):
        install_dir = guess_install_dir()
        if install_dir:
            self.install_dir_var.set(install_dir)
            self.modlunky_config.config_file.install_dir = install_dir
            self.modlunky_config.config_file.save()

    def clear_install_dir(self):
        self.install_dir_var.set("")
        self.modlunky_config.config_file.install_dir = None
        self.modlunky_config.config_file.save()


class ConfigTab(Tab):
    def __init__(self, tab_control, modlunky_config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        config_frame = ttk.LabelFrame(self, text="Config")
        config_frame.rowconfigure(0, weight=1)
        config_frame.columnconfigure(0, weight=1)
        config_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        install_dir_frame = InstallDir(config_frame, modlunky_config)
        install_dir_frame.grid(row=0, column=0, pady=5, padx=5, sticky="n")
