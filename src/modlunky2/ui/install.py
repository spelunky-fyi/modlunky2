import logging
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from modlunky2.ui.widgets import Tab

logger = logging.getLogger("modlunky2")


class FileChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config

        file_chooser_label = ttk.Label(self, text="Choose the file you want to install")
        file_chooser_label.grid(
            row=0, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.file_chooser_var = tk.StringVar()

        file_chooser_entry = ttk.Entry(
            self,
            textvariable=self.file_chooser_var,
            state=tk.DISABLED,
            width=80,
        )
        file_chooser_entry.columnconfigure(0, weight=1)
        file_chooser_entry.columnconfigure(1, weight=1)
        file_chooser_entry.columnconfigure(2, weight=1)
        file_chooser_entry.grid(
            row=1, column=0, padx=10, pady=10, columnspan=3, sticky="n"
        )

        file_chooser_browse = ttk.Button(self, text="Browse", command=self.browse)
        file_chooser_browse.grid(row=2, column=0, pady=5, padx=5, sticky="nsew")

    def browse(self):
        initial_dir = Path(self.modlunky_config.config_file.last_install_browse)
        if not initial_dir.exists():
            initial_dir = Path("/")

        filename = tk.filedialog.askopenfilenames(parent=self, initialdir=initial_dir)
        if not filename:
            return

        filename = filename[0]
        self.file_chooser_var.set(filename)
        parent = Path(filename).parent

        self.modlunky_config.config_file.last_install_browse = str(parent.as_posix())
        self.modlunky_config.config_file.save()


class InstallTab(Tab):
    def __init__(self, tab_control, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        source_frame = ttk.LabelFrame(self, text="Source")
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)
        source_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        file_chooser_frame = FileChooser(source_frame, modlunky_config)
        file_chooser_frame.grid(row=0, column=0, pady=5, padx=5, sticky="new")

        dest_frame = ttk.LabelFrame(self, text="Destination")
        dest_frame.rowconfigure(0, weight=1)
        dest_frame.columnconfigure(0, weight=1)
        dest_frame.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        file_chooser_frame2 = FileChooser(dest_frame, modlunky_config)
        file_chooser_frame2.grid(row=0, column=0, pady=5, padx=5, sticky="new")
