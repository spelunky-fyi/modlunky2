import tkinter as tk
from tkinter import ttk

from modlunky2.ui.widgets import PopupWindow


def present_create_template_dialog(modlunky_config, callback):
    win = PopupWindow("Create Template", modlunky_config)

    row = 0
    values_frame = tk.Frame(win)
    values_frame.grid(row=row, column=0, sticky="nw")
    row = row + 1

    values_row = 0
    name_lbl = ttk.Label(values_frame, text="Name: ")
    name_ent = ttk.Entry(values_frame)
    name_lbl.grid(row=values_row, column=0, pady=2, sticky="e")
    name_ent.grid(row=values_row, column=1, pady=2, sticky="we")

    values_row += 1

    comment_lbl = ttk.Label(values_frame, text="Comment: ")
    comment_ent = ttk.Entry(values_frame)
    comment_lbl.grid(row=values_row, column=0, pady=2, sticky="e")
    comment_ent.grid(row=values_row, column=1, pady=2, sticky="we")

    values_row += 1

    size_type_label = tk.Label(values_frame, text="Size in: ")
    size_type_label.grid(row=values_row, column=0, sticky="e", pady=2)

    size_type_combobox = ttk.Combobox(values_frame, height=25)
    size_type_combobox.set("Subrooms")
    size_type_combobox.grid(row=values_row, column=1, sticky="we", pady=2)
    size_type_combobox["state"] = "readonly"
    size_type_combobox["values"] = ["Subrooms", "Tiles"]
    size_type_combobox.current(0)

    values_row += 1

    width_label = tk.Label(values_frame, text="Width: ")
    width_label.grid(row=values_row, column=0, sticky="e", pady=2)

    width_ent = ttk.Entry(values_frame)
    width_ent.insert(0, "1")
    width_ent.grid(row=values_row, column=1, sticky="we", pady=2)

    values_row += 1

    height_label = tk.Label(values_frame, text="Height: ")
    height_label.grid(row=values_row, column=0, sticky="e", pady=2)

    height_ent = ttk.Entry(values_frame)
    height_ent.insert(0, "1")
    height_ent.grid(row=values_row, column=1, sticky="we", pady=2)

    values_row += 1

    error_lbl = tk.Label(values_frame, text="", fg="red")
    error_lbl.grid(row=values_row, column=0, columnspan=2)
    error_lbl.grid_remove()

    values_row += 1

    def update_then_destroy_pack():
        template_name = ""
        for char in str(name_ent.get()):
            if str(char) != " ":
                template_name += str(char)
            else:
                template_name += "_"

        comment = comment_ent.get()
        if len(comment) == 0:
            comment = None

        width_str = width_ent.get()
        height_str = height_ent.get()
        if not width_str.isdecimal():
            error_lbl.grid()
            error_lbl["text"] = "Invalid width."
            return

        if not height_str.isdecimal():
            error_lbl.grid()
            error_lbl["text"] = "Invalid height."
            return

        width = int(width_str)
        height = int(height_str)
        if size_type_combobox.current() != 1:
            width *= 10
            height *= 8

        error_lbl.grid_remove()
        if width == 0:
            error_lbl.grid()
            error_lbl["text"] = "Invalid width."
            return

        if height == 0:
            error_lbl.grid()
            error_lbl["text"] = "Invalid height."
            return

        if len(template_name) == 0:
            error_lbl.grid()
            error_lbl["text"] = "Name the template."
            return

        success, error_message = callback(template_name, comment, width, height)

        if success:
            win.destroy()
        else:
            error_lbl.grid()
            error_lbl["text"] = error_message or "Error creating template."
            return

    separator = ttk.Separator(win)
    separator.grid(row=row, column=0, columnspan=2, pady=5, sticky="news")

    row = row + 1

    buttons = ttk.Frame(win)
    buttons.grid(row=row, column=0, sticky="news")
    buttons.columnconfigure(0, weight=1)
    buttons.columnconfigure(1, weight=1)

    ok_button = ttk.Button(buttons, text="Create", command=update_then_destroy_pack)
    ok_button.grid(row=0, column=0, pady=5, sticky="news")

    cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
    cancel_button.grid(row=0, column=1, pady=5, sticky="news")

    row = row + 1
