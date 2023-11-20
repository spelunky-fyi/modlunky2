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

        self.templates = []

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

        settings_row += 1

        self.room_type_frame = tk.Frame(self)
        self.room_type_frame.grid(row=settings_row, column=1, sticky="news", padx=10, pady=10)

        self.room_view_size = 30
        self.room_view_padding = 5

        for n in range(8):
            # self.room_type_frame.columnconfigure(n * 2 + 2, minsize=10)
            self.room_type_frame.columnconfigure(n * 2, minsize=self.room_view_size)
            if n != 0:
                self.room_type_frame.columnconfigure(n * 2 - 1, minsize=self.room_view_padding)

        self.room_buttons = []
        self.edge_frames = []

        # s1 = tk.Button(self.room_type_frame, bg="#30F030", activebackground="#30F030", relief=tk.GROOVE)
        # s1.grid(row=0, column=0, sticky="news")
        # s2 = tk.Button(self.room_type_frame, bg="#3A403A", activebackground="#3A403A", relief=tk.GROOVE)
        # s2.grid(row=2, column=0, sticky="news")
        # s3 = tk.Button(self.room_type_frame, bg="#30F030", activebackground="#30F030", relief=tk.GROOVE)
        # s3.grid(row=0, column=2, rowspan=3, columnspan=3, sticky="news")
        # s4 = tk.Button(self.room_type_frame, bg="#30F030", activebackground="#30F030", relief=tk.GROOVE)
        # s4.grid(row=0, column=6, rowspan=1, columnspan=3, sticky="news")

    def set_templates(self, templates):
        if self.templates is not None:
            for row_index in range(len(self.templates) + 1):
                self.room_type_frame.rowconfigure(row_index * 2, minsize=0)
                if row_index != 0:
                    self.room_type_frame.rowconfigure(row_index * 2 - 1, minsize=0)

        self.templates = templates

        if templates is not None:
            for row_index in range(len(templates) + 1):
                self.room_type_frame.rowconfigure(row_index * 2, minsize=self.room_view_size)
                if row_index != 0:
                    self.room_type_frame.rowconfigure(row_index * 2 - 1, minsize=self.room_view_padding)

        for button in self.room_buttons:
            button.grid_remove()

        for frame in self.edge_frames:
            frame.grid_remove()

        self.room_buttons = []
        self.edge_frames = []

        for row_index, template_row in enumerate(templates):
            for col_index, template in enumerate(template_row):
                new_button = None
                if template is None:
                    overlapping_template, _, _ = self.template_item_at(templates, row_index, col_index)
                    if overlapping_template is None:
                        new_button = tk.Button(self.room_type_frame, bg="#3A403A", activebackground="#3A403A", relief=tk.GROOVE)
                        new_button.grid(row=row_index * 2, column=col_index * 2, sticky="news")
                else:
                    new_button = tk.Button(self.room_type_frame, bg="#30F030", activebackground="#30F030", relief=tk.GROOVE)
                    new_button.grid(
                        row=row_index * 2,
                        column=col_index * 2,
                        rowspan=template.height_in_rooms * 2 - 1,
                        columnspan=template.width_in_rooms * 2 - 1,
                        sticky="news",
                    )
                if new_button is not None:
                    self.room_buttons.append(new_button)

            if len(template_row) < 10:
                edge_frame = tk.Frame(self.room_type_frame)
                edge_frame.grid(row=row_index * 2, column=len(template_row) * 2, sticky="news")
                edge_frame.columnconfigure(0, weight=1)
                edge_frame.rowconfigure(0, weight=1)

                edge_button = tk.Button(edge_frame, text="+", bg="#A0C0A6", activebackground="#A0C0A6", relief=tk.GROOVE)
                edge_button.grid(row=0, column=0, sticky="news")
                edge_button.grid_remove()


                edge_frame.bind("<Enter>", lambda _, eb=edge_button: eb.grid())
                edge_frame.bind("<Leave>", lambda _, eb=edge_button: eb.grid_remove())
                self.edge_frames.append(edge_frame)

        if len(templates) > 0:
            row = len(templates) * 2
            for col in range(len(templates[0])):
                edge_frame = tk.Frame(self.room_type_frame)
                edge_frame.grid(row=row, column=col * 2, sticky="news")
                edge_frame.columnconfigure(0, weight=1)
                edge_frame.rowconfigure(0, weight=1)

                edge_button = tk.Button(edge_frame, text="+", bg="#A0C0A6", activebackground="#A0C0A6", relief=tk.GROOVE)
                edge_button.grid(row=0, column=0, sticky="news")
                edge_button.grid_remove()


                edge_frame.bind("<Enter>", lambda _, eb=edge_button: eb.grid())
                edge_frame.bind("<Leave>", lambda _, eb=edge_button: eb.grid_remove())
                self.edge_frames.append(edge_frame)




    def update_zoom_level(self, zoom_level):
        self.grid_size_var.set(zoom_level)

    def template_item_at(self, templates, row, col):
        for room_row_index, room_row in enumerate(templates):
            if room_row_index > row:
                return None, None, None
            for room_column_index, template_draw_item in enumerate(room_row):
                if room_column_index > col:
                    break
                if template_draw_item is None:
                    continue
                if room_row_index + template_draw_item.height_in_rooms - 1 >= row and room_column_index + template_draw_item.width_in_rooms - 1 >= col:
                    return template_draw_item, room_row_index, room_column_index

        return None, None, None