import tkinter as tk
from tkinter import ttk

from modlunky2.config import CustomLevelSaveFormat
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats

class OptionsPanel(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        zoom_level,
        on_update_save_format,
        on_update_hide_grid_lines,
        on_update_hide_room_lines,
        on_update_zoom_level,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.on_update_save_format = on_update_save_format
        self.on_update_hide_grid_lines = on_update_hide_grid_lines
        self.on_update_hide_room_lines = on_update_hide_room_lines
        self.on_update_zoom_level = on_update_zoom_level

        self.columnconfigure(0, weight=1)

        settings_row = 0

        option_header = tk.Label(self, text="Save format:")
        option_header.grid(column=0, row=settings_row, sticky="nsw")

        settings_row += 1
        save_format_frame = tk.Frame(self)
        save_format_frame.grid(column=0, row=settings_row, sticky="nwe")

        save_format_variable = tk.IntVar()
        save_format_variable.set(0)
        self.save_format_variable = save_format_variable
        self.save_format_radios = []
        self.save_format_frame = save_format_frame

        for index, save_format in enumerate(
            SaveFormats.base_save_formats()
            + self.modlunky_config.custom_level_editor_custom_save_formats
        ):
            self.add_save_format_radio(index, save_format)

        settings_row += 1
        self.save_format_warning_message = tk.Label(
            self, text="", wraplength=350, justify=tk.LEFT
        )
        self.save_format_warning_message.grid(column=0, row=settings_row, sticky="nw")

        if self.modlunky_config.custom_level_editor_default_save_format:
            self.update_save_format_variable(
                self.modlunky_config.custom_level_editor_default_save_format
            )
            self.update_save_format_warning(
                self.modlunky_config.custom_level_editor_default_save_format
            )

        settings_row += 1

        def create_template():
            SaveFormats.show_setroom_create_dialog(
                self.modlunky_config,
                "Create new room template format",
                "Create a new room template format\n{x} and {y} are the coordinates of the room.",
                "Create",
                self.add_save_format,
            )

        create_template_button = tk.Button(
            self,
            text="New save format",
            bg="red",
            fg="white",
            command=create_template,
        )
        create_template_button.grid(row=settings_row, column=0, sticky="nw")

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
        ).grid(row=settings_row, column=0, sticky="nw", pady=5)

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
        ).grid(row=settings_row, column=0, sticky="nw", pady=5)

        settings_row += 1
        grid_size_frame = tk.Frame(self)
        grid_size_frame.grid(row=settings_row, column=0, sticky="nw", pady=5)
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

    def enable_controls(self):
        return

    def disable_controls(self):
        return

    # Updates the current radio button in the save format select options menu to the
    # proper save format.
    def update_save_format_variable(self, save_format):
        if save_format in SaveFormats.base_save_formats():
            self.save_format_variable.set(
                SaveFormats.base_save_formats().index(save_format)
            )
        elif (
            save_format in self.modlunky_config.custom_level_editor_custom_save_formats
        ):
            self.save_format_variable.set(
                len(SaveFormats.base_save_formats())
                + self.modlunky_config.custom_level_editor_custom_save_formats.index(
                    save_format
                )
            )
        self.save_format_radios[self.save_format_variable.get()].select()

    # Adds a warning message below the save format radio list based on the selected
    # save format.
    def update_save_format_warning(self, save_format):
        warning_message = ""
        if save_format == CustomLevelSaveFormat.level_sequence():
            warning_message = (
                "This save format can be used to load saved level files into the "
                "Custom Levels or Level Sequence packages.\n"
                "(https://github.com/jaythebusinessgoose/LevelSequence)"
            )
        elif save_format == CustomLevelSaveFormat.vanilla():
            warning_message = (
                "WARNING: Files saved using vanilla setrooms will only work when loaded "
                "into themes that use them. Otherwise, it will crash the game. Also, themes "
                "that do allow loading vanilla setrooms will only load the required setrooms "
                "for the default size of the level. It is recommended to use another save "
                "format and use scripts to load the proper rooms."
            )
        elif not save_format.include_vanilla_setrooms:
            warning_message = (
                "WARNING: Some themes override the desired level with a vanilla setroom, so it "
                "is recommended to use a save format that includes the correct vanilla setrooms."
            )
        self.save_format_warning_message["text"] = warning_message

    def set_current_save_format(self, save_format):
        self.update_save_format_variable(save_format)
        self.update_save_format_warning(save_format)

    def add_save_format_radio(self, index, save_format):
        radio = tk.Radiobutton(
            self.save_format_frame,
            text=save_format.name,
            variable=self.save_format_variable,
            indicatoron=True,
            value=index,
            command=self.select_save_format_radio,
        )
        radio.grid(column=0, row=index, sticky="nsw")
        self.save_format_radios.append(radio)

        label = tk.Label(self.save_format_frame, text=save_format.room_template_format)
        label.grid(column=1, row=index, sticky="nsw")

    # Called when a save format radio button is selected.
    def select_save_format_radio(self):
        save_format_index = self.save_format_variable.get()
        save_format = None
        if save_format_index < len(SaveFormats.base_save_formats()):
            save_format = SaveFormats.base_save_formats()[save_format_index]
        else:
            save_format = self.modlunky_config.custom_level_editor_custom_save_formats[
                save_format_index - len(SaveFormats.base_save_formats())
            ]
        if not save_format:
            return
        self.set_current_save_format(save_format)
        self.on_update_save_format(save_format)
        self.modlunky_config.custom_level_editor_default_save_format = save_format
        self.modlunky_config.save()

    def add_save_format(self, save_format):
        self.add_save_format_radio(len(self.save_format_radios), save_format)
