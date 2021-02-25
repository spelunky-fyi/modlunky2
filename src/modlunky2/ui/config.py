import logging
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from modlunky2.ui.widgets import Tab, ToolTip
from modlunky2.config import guess_install_dir

logger = logging.getLogger("modlunky2")


class ConfigTab(Tab):
    def __init__(self, tab_control, config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.config = config

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        config_frame = ttk.LabelFrame(self, text="Config")
        config_frame.rowconfigure(0, weight=1)
        config_frame.columnconfigure(0, weight=1)
        config_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        install_dir_frame = ttk.LabelFrame(config_frame, text="Install Directory")
        install_dir_frame.grid(row=0, column=0, pady=5, padx=5, sticky="n")
        ToolTip(install_dir_frame, ("The directory where Spelunky 2 is installed."))

        self.install_dir_var = tk.StringVar(value=self.config.config_file.install_dir)
        install_dir_entry = ttk.Entry(
            install_dir_frame,
            textvariable=self.install_dir_var,
            state=tk.DISABLED,
            width=80,
        )
        install_dir_entry.columnconfigure(0, weight=1)
        install_dir_entry.columnconfigure(1, weight=1)
        install_dir_entry.columnconfigure(2, weight=1)
        install_dir_entry.grid(
            row=0, column=0, padx=10, pady=10, columnspan=3, sticky="n"
        )

        install_dir_browse = ttk.Button(
            install_dir_frame, text="Browse", command=self.browse_install_dir
        )
        install_dir_browse.grid(row=1, column=0, pady=5, padx=5, sticky="nsew")

        install_dir_lucky = ttk.Button(
            install_dir_frame, text="I'm Feeling Lucky", command=self.feeling_lucky
        )
        install_dir_lucky.grid(row=1, column=1, pady=5, padx=5, sticky="nsew")

        install_dir_clear = ttk.Button(
            install_dir_frame, text="Clear", command=self.clear_install_dir
        )
        install_dir_clear.grid(row=1, column=2, pady=5, padx=5, sticky="nsew")

    def browse_install_dir(self):
        install_dir = self.install_dir_var.get()
        directory = tk.filedialog.askdirectory(initialdir=install_dir)
        if directory:
            self.install_dir_var.set(directory)
            self.config.config_file.install_dir = Path(directory)
            self.config.config_file.save()

    def feeling_lucky(self):
        install_dir = guess_install_dir()
        if install_dir:
            self.install_dir_var.set(install_dir)
            self.config.config_file.install_dir = install_dir
            self.config.config_file.save()

    def clear_install_dir(self):
        self.install_dir_var.set("")
        self.config.config_file.install_dir = None
        self.config.config_file.save()
