import tkinter as tk
from tkinter import ttk

class RoomOptions(ttk.Frame):
    def __init__(
        self,
        parent,
        on_select_template,
        on_clear_template,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)

        setting_row = 0

        self.on_select_template = on_select_template
        self.on_clear_template = on_clear_template

        self.current_template_row = None
        self.current_template_column = None
        self.current_template_item = None

        self.columnconfigure(0, weight=1)

        template_label = tk.Label(self, text="Room Type:")
        template_label.grid(row=setting_row, column=0, sticky="w")

        setting_row += 1

        self.template_combobox = ttk.Combobox(self, height=25)
        self.template_combobox.grid(row=setting_row, column=0, sticky="nsw")
        self.template_combobox["values"] = ["None"]
        self.template_combobox.set("None")
        self.template_combobox["state"] = "readonly"
        self.template_combobox.bind("<<ComboboxSelected>>", lambda _: self.select_template())

    def select_template(self):
        template_index = self.template_combobox.current()

        if template_index == 0:
            self.clear_templates()
            self.on_clear_template(self.current_template_row, self.current_template_column)
        else:
            self.on_select_template(template_index - 1, self.current_template_row, self.current_template_column)

    def clear_templates(self):
        self.template_combobox["values"] = ["None"]
        self.template_combobox.set("None")

    def set_templates(self, templates):
        self.template_combobox["values"] = ["None"] + [template.name for template in templates]
        self.current_template_item = None

    def set_current_template(self, template, row, column):
        self.current_template_item = template
        self.current_template_row = row
        self.current_template_column = column
        if template:
            self.template_combobox.set(template.template.name)

class OptionsPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        zoom_level,
        on_update_hide_grid_lines,
        on_update_hide_room_lines,
        on_update_zoom_level,
        on_change_template_at,
        on_clear_template,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_update_hide_grid_lines = on_update_hide_grid_lines
        self.on_update_hide_room_lines = on_update_hide_room_lines
        self.on_update_zoom_level = on_update_zoom_level
        self.on_change_template_at = on_change_template_at
        self.on_clear_template = on_clear_template

        self.columnconfigure(0, minsize=10)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, minsize=10)

        self.room_map = []
        self.templates = []

        self.button_for_selected_room = None

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
            self.room_type_frame.columnconfigure(n * 2, minsize=self.room_view_size)
            if n != 0:
                self.room_type_frame.columnconfigure(n * 2 - 1, minsize=self.room_view_padding)

        self.room_buttons = []
        self.edge_frames = []

        settings_row += 1

        self.room_options = RoomOptions(self, self.update_room_map_template, self.clear_template)
        self.room_options.grid(row=settings_row, column=1, sticky="news")

    def update_room_map_template(self, template_index, row, column):
        template = self.templates[template_index]
        self.on_change_template_at(row, column, template, template_index)

    def clear_template(self, row, column):
        self.on_clear_template(row, column)

    def set_templates(self, room_map, templates):
        # self.room_options.grid_remove()
        if self.room_map is not None:
            for row_index in range(len(self.room_map) + 1):
                self.room_type_frame.rowconfigure(row_index * 2, minsize=0)
                if row_index != 0:
                    self.room_type_frame.rowconfigure(row_index * 2 - 1, minsize=0)

        self.room_map = room_map
        self.templates = templates

        self.room_options.set_templates(templates)

        if room_map is not None:
            for row_index in range(len(room_map) + 1):
                self.room_type_frame.rowconfigure(row_index * 2, minsize=self.room_view_size)
                if row_index != 0:
                    self.room_type_frame.rowconfigure(row_index * 2 - 1, minsize=self.room_view_padding)

        for button in self.room_buttons:
            button.grid_remove()

        for frame in self.edge_frames:
            frame.grid_remove()

        self.room_buttons = []
        self.edge_frames = []

        for row_index, template_row in enumerate(room_map):
            for col_index, template in enumerate(template_row):
                new_button = None
                if template is None:
                    overlapping_template, _, _ = self.template_item_at(room_map, row_index, col_index)
                    if overlapping_template is None:
                        new_button = tk.Button(self.room_type_frame, bg="#3A403A", activebackground="#3A403A", relief=tk.GROOVE)
                        new_button.grid(row=row_index * 2, column=col_index * 2, sticky="news")
                else:
                    new_button = tk.Button(
                        self.room_type_frame,
                        bg="#30F030",
                        activebackground="#30F030",
                        relief=tk.GROOVE,
                    )
                    new_button.configure(
                        command=lambda t=template, nb=new_button, r=row_index, c=col_index: self.select_template_item(t, nb, r, c)
                    )
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

        if len(room_map) > 0:
            row = len(room_map) * 2
            for col in range(len(room_map[0])):
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

    def reset_selected_button(self):
        if self.button_for_selected_room is not None:
            self.button_for_selected_room.configure(bg="#30F030", activebackground="#30F030")
            self.button_for_selected_room = None

    def select_template_item(self, template_item, button, row, column):
        self.reset_selected_button()
        self.button_for_selected_room = button
        button.configure(bg="#228B22", activebackground="#228B22")
        self.room_options.set_current_template(template_item, row, column)

    def update_zoom_level(self, zoom_level):
        self.grid_size_var.set(zoom_level)

    def template_item_at(self, room_map, row, col):
        for room_row_index, room_row in enumerate(room_map):
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