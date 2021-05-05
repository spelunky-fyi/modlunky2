import logging
import tkinter as tk
from tkinter import ttk

from modlunky2.ui.widgets import DebounceEntry


logger = logging.getLogger("modlunky2")


class FiltersFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Filters")
        self.parent = parent

        self.name_label = ttk.Label(self, text="Name:")
        self.name_label.grid(row=0, column=0, pady=(5, 5), padx=(5, 0), sticky="w")
        self.name = DebounceEntry(self, width="30")
        self.name_last_seen = ""
        self.name.bind_on_key(self.on_name_key)
        self.name.grid(row=0, column=1, pady=(5, 5), padx=(5, 0), sticky="w")

        self.selected_label = ttk.Label(self, text="Show:")
        self.selected_label.grid(row=0, column=2, pady=(5, 5), padx=(5, 0), sticky="w")
        self.selected_var = tk.StringVar(value="Both")
        self.selected_dropdown = ttk.OptionMenu(
            self,
            self.selected_var,
            self.selected_var.get(),
            "Both",
            "Selected",
            "Unselected",
            command=self.selected_command,
        )
        self.selected_dropdown.grid(
            row=0, column=3, pady=(5, 5), padx=(5, 0), sticky="w"
        )

    def selected_command(self, _event=None):
        self.parent.master.render_packs()

    def on_name_key(self, _event=None):
        name = self.name.get().strip()
        if name != self.name_last_seen:
            self.name_last_seen = name
            self.parent.master.render_packs()
