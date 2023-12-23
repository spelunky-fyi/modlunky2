import tkinter as tk
from tkinter import ttk

from modlunky2.ui.levels.shared.level_canvas import CANVAS_MODE


class ToolSelect(tk.Frame):
    def __init__(self, parent, on_select_tool, *args, **kwargs):
        super().__init__(parent, bg="#343434", *args, **kwargs)

        self.on_select_tool = on_select_tool

        self.draw_button = tk.Button(self, text="Draw", command=self.select_draw)
        self.draw_button.grid(row=0, column=0, sticky="e")

        self.select_button = tk.Button(self, text="Select", command=self.select_select)
        self.select_button.grid(row=1, column=0, sticky="e")

        self.fill_button = tk.Button(self, text="Fill", command=self.select_fill)
        self.fill_button.grid(row=2, column=0, sticky="e")

    def select_draw(self):
        self.on_select_tool(CANVAS_MODE.DRAW)

    def select_select(self):
        self.on_select_tool(CANVAS_MODE.SELECT)

    def select_fill(self):
        self.on_select_tool(CANVAS_MODE.FILL)
