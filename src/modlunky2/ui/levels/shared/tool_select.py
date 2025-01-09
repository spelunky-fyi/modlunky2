import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from modlunky2.constants import BASE_DIR
from modlunky2.ui.levels.shared.level_canvas import CANVAS_MODE


class ToolSelect(tk.Frame):
    def __init__(self, parent, on_select_tool, *args, **kwargs):
        super().__init__(parent, bg="#343434", *args, **kwargs)

        self.on_select_tool = on_select_tool

        self.icon_draw = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/brush.png").resize((20, 20))
        )

        self.icon_select = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/select.png").resize((20, 20))
        )

        self.icon_fill = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/bucket.png").resize((20, 20))
        )

        self.icon_move = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/move.png").resize((20, 20))
        )

        self.draw_button = tk.Button(
            self, image=self.icon_draw, command=self.select_draw
        )
        self.draw_button.grid(row=0, column=0, sticky="e")

        self.select_button = tk.Button(
            self, image=self.icon_select, command=self.select_select
        )
        self.select_button.grid(row=1, column=0, sticky="e")

        self.fill_button = tk.Button(
            self, image=self.icon_fill, command=self.select_fill
        )
        self.fill_button.grid(row=2, column=0, sticky="e")

        self.move_button = tk.Button(
            self, image=self.icon_move, command=self.select_move
        )
        self.move_button.grid(row=3, column=0, sticky="e")

        self.bind_all("d", self.select_draw_binding)
        self.bind_all("s", self.select_select_binding)
        self.bind_all("f", self.select_fill_binding)
        self.bind_all("m", self.select_move_binding)

        self.select_draw()

    def reset_button_colors(self):
        self.draw_button.configure(bg="SystemButtonFace")
        self.select_button.configure(bg="SystemButtonFace")
        self.fill_button.configure(bg="SystemButtonFace")
        self.move_button.configure(bg="SystemButtonFace")
        self.draw_button.configure(relief=tk.RAISED)
        self.select_button.configure(relief=tk.RAISED)
        self.fill_button.configure(relief=tk.RAISED)
        self.move_button.configure(relief=tk.RAISED)

    def select_draw(self, _=None):
        self.on_select_tool(CANVAS_MODE.DRAW)
        self.reset_button_colors()
        self.draw_button.configure(bg="white")
        self.draw_button.configure(relief=tk.SUNKEN)

    def select_select(self, _=None):
        self.on_select_tool(CANVAS_MODE.SELECT)
        self.reset_button_colors()
        self.select_button.configure(bg="white")
        self.select_button.configure(relief=tk.SUNKEN)

    def select_fill(self, _=None):
        self.on_select_tool(CANVAS_MODE.FILL)
        self.reset_button_colors()
        self.fill_button.configure(bg="white")
        self.fill_button.configure(relief=tk.SUNKEN)

    def select_move(self, _=None):
        self.on_select_tool(CANVAS_MODE.MOVE)
        self.reset_button_colors()
        self.move_button.configure(bg="white")
        self.move_button.configure(relief=tk.SUNKEN)

    def select_draw_binding(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        if not self.winfo_ismapped():
            return
        self.select_draw()

    def select_select_binding(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        if not self.winfo_ismapped():
            return
        self.select_select()

    def select_fill_binding(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        if not self.winfo_ismapped():
            return
        self.select_fill()

    def select_move_binding(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        if not self.winfo_ismapped():
            return
        self.select_move()
