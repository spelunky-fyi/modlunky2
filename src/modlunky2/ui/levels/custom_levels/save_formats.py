import tkinter as tk
from tkinter import ttk
from modlunky2.ui.widgets import PopupWindow

from modlunky2.config import CustomLevelSaveFormat


class SaveFormats:
    @staticmethod
    def base_save_formats():
        return [
            CustomLevelSaveFormat.level_sequence(),
            CustomLevelSaveFormat.vanilla(),
        ]

    # Popup dialog with widgets to create a new room template.
    @staticmethod
    def show_setroom_create_dialog(
        modlunky_config,
        title,
        message,
        button_title,
        button_action,
        suggested_template_name=None,
    ):
        win = PopupWindow(title, modlunky_config)
        message = ttk.Label(win, text=message)
        name_label = ttk.Label(win, text="Name: ")
        name_entry = ttk.Entry(win, foreground="gray")
        format_label = ttk.Label(win, text="Format: ")
        format_entry = ttk.Entry(win, foreground="gray")
        win.columnconfigure(1, weight=1)
        message.grid(row=0, column=0, columnspan=2, sticky="nswe")
        name_label.grid(row=1, column=0, sticky="nse")
        name_entry.grid(row=1, column=1, sticky="nswe")
        format_label.grid(row=2, column=0, sticky="nse")
        format_entry.grid(row=2, column=1, sticky="nswe")
        name_entry.insert(0, "Optional")
        if suggested_template_name:
            format_entry.insert(0, suggested_template_name)
        else:
            format_entry.insert(0, "setroom{y}_{x}")
        name_entry_changed = False
        format_entry_changed = False

        # If displaying a placeholder, delete the placeholder text and update the font color
        # when the field is focused.
        def focus_name(_):
            nonlocal name_entry_changed
            if name_entry_changed:
                return
            name_entry.delete("0", "end")
            name_entry.config(foreground="black")

        def focus_format(_):
            nonlocal format_entry_changed
            if format_entry_changed:
                return
            format_entry.delete("0", "end")
            format_entry.config(foreground="black")

        # When defocusing the field, if the field is empty, replace the text with the
        # placeholder text and change the font color.
        def defocus_name(_):
            nonlocal name_entry_changed
            if str(name_entry.get()) == "":
                name_entry_changed = False
                name_entry.insert(0, "Optional")
                name_entry.config(foreground="gray")
            else:
                name_entry_changed = True

        def defocus_format(_):
            nonlocal format_entry_changed
            if str(format_entry.get()) == "":
                format_entry_changed = False
                if suggested_template_name:
                    format_entry.insert(0, suggested_template_name)
                else:
                    format_entry.insert(0, "setroom{y}_{x}")
                format_entry.config(foreground="gray")
            else:
                format_entry_changed = True

        name_entry.bind("<FocusIn>", focus_name)
        name_entry.bind("<FocusOut>", defocus_name)
        format_entry.bind("<FocusIn>", focus_format)
        format_entry.bind("<FocusOut>", defocus_format)

        # Checkbox to enable or disable vanilla setrooms for themes such as ice caves which
        # crash without them.
        add_vanilla_var = tk.IntVar()
        add_vanilla_var.set(True)
        add_vanilla_label = ttk.Label(win, text="Include vanilla setrooms:")
        add_vanilla_check = ttk.Checkbutton(win, variable=add_vanilla_var)
        add_vanilla_label.grid(row=3, column=0, sticky="nse")
        add_vanilla_check.grid(row=3, column=1, sticky="nsw")

        add_vanilla_tip = ttk.Label(
            win,
            text=(
                "It is recommended to include vanilla setrooms.\n"
                "This setting adds setrooms for some themes which require them.\n"
                "There could be errors if not using this in some themes."
            ),
        )
        add_vanilla_tip.grid(row=4, column=0, columnspan=2, sticky="nswe")

        win.rowconfigure(5, minsize=20)

        buttons = ttk.Frame(win)
        buttons.grid(row=6, column=0, columnspan=2, sticky="nswe")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        def continue_open():
            template_format = str(format_entry.get())
            name = str(name_entry.get()) if name_entry_changed else template_format
            if (
                (
                    not format_entry_changed
                    and suggested_template_name
                    and template_format != suggested_template_name
                )
                or template_format == ""
                or name == ""
                or template_format == "setroom{y}-{x}"
                or template_format == "setroom{x}-{y}"
            ):
                return
            save_format = CustomLevelSaveFormat(
                name, template_format, bool(add_vanilla_var.get())
            )
            win.destroy()
            modlunky_config.custom_level_editor_custom_save_formats.append(save_format)
            modlunky_config.save()
            if button_action:
                button_action(save_format)

        continue_button = ttk.Button(buttons, text=button_title, command=continue_open)
        continue_button.grid(row=0, column=0, sticky="nswe")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, sticky="nswe")
