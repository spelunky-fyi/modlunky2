import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)

class LevelSettingsBar(ttk.Frame):
    def __init__(self, parent, on_flip_setting, on_flip_dual_setting, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)


        self.var_ignore = tk.IntVar()
        self.var_flip = tk.IntVar()
        self.var_only_flip = tk.IntVar()
        self.var_dual = tk.IntVar()
        self.var_rare = tk.IntVar()
        self.var_hard = tk.IntVar()
        self.var_liquid = tk.IntVar()
        self.var_purge = tk.IntVar()
        self.checkbox_ignore = ttk.Checkbutton(
            self,
            text="Ignore",
            var=self.var_ignore,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_flip = ttk.Checkbutton(
            self,
            text="Flip",
            var=self.var_flip,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_only_flip = ttk.Checkbutton(
            self,
            text="Only Flip",
            var=self.var_only_flip,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_rare = ttk.Checkbutton(
            self,
            text="Rare",
            var=self.var_rare,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_hard = ttk.Checkbutton(
            self,
            text="Hard",
            var=self.var_hard,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_liquid = ttk.Checkbutton(
            self,
            text="Optimize Liquids",
            var=self.var_liquid,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_purge = ttk.Checkbutton(
            self,
            text="Purge",
            var=self.var_purge,
            onvalue=1,
            offvalue=0,
            command=on_flip_setting,
        )
        self.checkbox_dual = ttk.Checkbutton(
            self,
            text="Dual",
            var=self.var_dual,
            onvalue=1,
            offvalue=0,
            command=on_flip_dual_setting,
        )
        self.checkbox_dual.grid(row=4, column=0, sticky="w")
        self.checkbox_ignore.grid(row=4, column=2, sticky="w")
        self.checkbox_purge.grid(row=4, column=3, sticky="w")
        self.checkbox_rare.grid(row=4, column=4, sticky="w")
        self.checkbox_hard.grid(row=4, column=5, sticky="w")
        self.checkbox_flip.grid(row=4, column=6, sticky="w")
        self.checkbox_only_flip.grid(row=4, column=7, sticky="w")
        self.checkbox_liquid.grid(row=4, column=8, sticky="w")

        self.columnconfigure(0, weight=1)

    def ignore(self):
        return int(self.var_ignore.get()) == 1

    def liquid(self):
        return int(self.var_liquid.get()) == 1

    def hard(self):
        return int(self.var_hard.get()) == 1

    def rare(self):
        return int(self.var_rare.get()) == 1

    def flip(self):
        return int(self.var_flip.get()) == 1

    def only_flip(self):
        return int(self.var_only_flip.get()) == 1

    def purge(self):
        return int(self.var_purge.get()) == 1

    def dual(self):
        return int(self.var_dual.get()) == 1

    def set_ignore(self, ignore):
        self.var_ignore.set(ignore and 1 or 0)

    def set_liquid(self, liquid):
        self.var_liquid.set(liquid and 1 or 0)

    def set_hard(self, hard):
        self.var_hard.set(hard and 1 or 0)

    def set_rare(self, rare):
        self.var_rare.set(rare and 1 or 0)

    def set_flip(self, flip):
        self.var_flip.set(flip and 1 or 0)

    def set_only_flip(self, only_flip):
        self.var_only_flip.set(only_flip and 1 or 0)

    def set_purge(self, purge):
        self.var_purge.set(purge and 1 or 0)

    def set_dual(self, dual):
        self.var_dual.set(dual and 1 or 0)