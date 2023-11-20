import tkinter as tk
from tkinter import ttk

class OptionsPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        zoom_level,
        on_update_hide_grid_lines,
        on_update_hide_room_lines,
        on_update_zoom_level,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_update_hide_grid_lines = on_update_hide_grid_lines
        self.on_update_hide_room_lines = on_update_hide_room_lines
        self.on_update_zoom_level = on_update_zoom_level

        self.columnconfigure(0, minsize=10)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, minsize=10)

        settings_row = 0


        # Checkbox to toggle the visibility of the grid lines.
        hide_grid_var = tk.IntVar()
        hide_grid_var.set(False)

        def toggle_hide_grid():
            nonlocal hide_grid_var

            self.on_update_hide_grid_lines(hide_grid_var.get())

        settings_row += 1
        tk.Checkbutton(
            self,
            text="Hide grid lines",
            variable=hide_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_grid,
        ).grid(row=settings_row, column=1, sticky="nw", pady=5)

        # Checkbox to toggle the visibility of the grid lines on room boundaries.
        hide_room_grid_var = tk.IntVar()
        hide_room_grid_var.set(False)

        def toggle_hide_room_grid():
            nonlocal hide_room_grid_var
            self.on_update_hide_room_lines(hide_room_grid_var.get())

        settings_row += 1
        tk.Checkbutton(
            self,
            text="Hide room lines",
            variable=hide_room_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_room_grid,
        ).grid(row=settings_row, column=1, sticky="nw", pady=5)

        settings_row += 1
        grid_size_frame = tk.Frame(self)
        grid_size_frame.grid(row=settings_row, column=1, sticky="nw", pady=5)
        grid_size_frame.columnconfigure(0, weight=1)
        grid_size_var = tk.StringVar()
        grid_size_var.set(str(zoom_level))
        grid_size_label_frame = tk.Frame(grid_size_frame)
        grid_size_label_frame.grid(row=0, column=0, sticky="nw")

        grid_size_header_label = tk.Label(grid_size_label_frame, text="Zoom:")
        grid_size_header_label.grid(row=0, column=0, sticky="nwe")
        grid_size_label = tk.Label(grid_size_label_frame, textvariable=grid_size_var)
        grid_size_label.grid(row=0, column=1, sticky="nw")

        grid_size_scale = tk.Scale(
            grid_size_frame,
            from_=10,
            to=200,
            orient=tk.HORIZONTAL,
            variable=grid_size_var,
            length=390,
            showvalue=False,
        )
        grid_size_scale.grid(row=1, column=0, sticky="nwe")

        def update_grid_size(_):
            self.on_update_zoom_level(int(grid_size_var.get()))

        grid_size_scale["command"] = update_grid_size
        self.grid_size_var = grid_size_var

    def update_zoom_level(self, zoom_level):
        self.grid_size_var.set(zoom_level)
