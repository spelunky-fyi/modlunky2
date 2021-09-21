import logging

import tkinter as tk
from tkinter import ttk

logger = logging.getLogger("modlunky2")


class LoadOrderFrame(ttk.LabelFrame):
    def __init__(self, play_tab, *args, **kwargs):
        logger.debug("Initializing Playlunky LoadOrderFrame")
        super().__init__(play_tab, text="Load Order", *args, **kwargs)
        self.play_tab = play_tab
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE)
        self.listbox.grid(
            row=0, column=0, columnspan=3, pady=5, padx=(5, 0), sticky="nsew"
        )

        self.scrollbar = ttk.Scrollbar(self)
        self.scrollbar.grid(row=0, column=1, columnspan=3, pady=5, sticky="nse")

        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.render_buttons)

        self.up_button = ttk.Button(
            self, text="Up", state=tk.DISABLED, command=self.move_up
        )
        self.up_button.grid(row=1, column=0, pady=5, padx=2, sticky="nswe")

        self.down_button = ttk.Button(
            self, text="Down", state=tk.DISABLED, command=self.move_down
        )
        self.down_button.grid(row=1, column=1, pady=5, padx=2, sticky="nswe")

        self.remove_button = ttk.Button(
            self, text="Remove", state=tk.DISABLED, command=self.remove
        )
        self.remove_button.grid(row=1, column=2, pady=5, padx=2, sticky="nswe")

    def current_selection(self):
        cur = self.listbox.curselection()
        if not cur:
            return None
        return cur[0]

    def render_buttons(self, _event=None):
        size = self.listbox.size()
        selection = self.current_selection()
        if selection is None:
            self.remove_button["state"] = tk.DISABLED
        else:
            self.remove_button["state"] = tk.NORMAL

        # Too few items or none selected
        if size < 2 or selection is None:
            up_state = tk.DISABLED
            down_state = tk.DISABLED
        # First item selected
        elif selection == 0:
            up_state = tk.DISABLED
            down_state = tk.NORMAL
        # Last item selected
        elif selection == size - 1:
            up_state = tk.NORMAL
            down_state = tk.DISABLED
        else:
            up_state = tk.NORMAL
            down_state = tk.NORMAL

        self.up_button["state"] = up_state
        self.down_button["state"] = down_state

    def remove(self):
        selection = self.current_selection()

        if selection is None:
            return

        label = self.listbox.get(selection)
        self.delete(label)
        pack_obj = self.play_tab.packs_frame.pack_objs.get(label)
        if pack_obj is None:
            return
        pack_obj.var.set(False)

    def move_up(self):
        selection = self.current_selection()

        if selection is None:
            return

        if selection == 0:
            return

        label = self.listbox.get(selection)
        self.listbox.delete(selection)
        self.listbox.insert(selection - 1, label)
        self.listbox.selection_set(selection - 1)

        self.play_tab.write_load_order()
        self.render_buttons()

    def move_down(self):
        size = self.listbox.size()
        selection = self.current_selection()

        if selection is None:
            return

        if selection == size - 1:
            return

        label = self.listbox.get(selection)
        self.listbox.delete(selection)
        self.listbox.insert(selection + 1, label)
        self.listbox.selection_set(selection + 1)

        self.play_tab.write_load_order()
        self.render_buttons()

    def insert(self, label):
        self.listbox.insert(tk.END, label)
        self.play_tab.write_load_order()
        self.render_buttons()

    def all(self):
        return self.listbox.get(0, tk.END)

    def delete(self, label):
        try:
            idx = self.listbox.get(0, tk.END).index(label)
        except ValueError:
            return
        self.listbox.delete(idx)
        self.play_tab.write_load_order()
        self.render_buttons()
