import logging

from tkinter import ttk

from modlunky2.ui.widgets import Tab

logger = logging.getLogger("modlunky2")


class ErrorTab(Tab):
    def __init__(self, tab_control, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.label = ttk.Label(
            self, text="Failed to load this tab... See console for more details."
        )
        self.label.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")
