import logging
from pathlib import Path
from PIL import Image, ImageTk
import re
import tkinter as tk
from tkinter import ttk

from modlunky2.constants import BASE_DIR
from modlunky2.levels.level_chances import LevelChances
from modlunky2.levels.level_settings import LevelSetting, LevelSettings
from modlunky2.levels.monster_chances import MonsterChances
from modlunky2.ui.levels.custom_levels.save_level import save_level
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.shared.biomes import Biomes
from modlunky2.ui.levels.shared.tile import Tile
from modlunky2.ui.widgets import PopupWindow

logger = logging.getLogger(__name__)


def present_create_level_dialog(
    modlunky_config, backup_dir, lvls_path, current_save_format, has_sequence, on_level_created
):
    win = PopupWindow("Create Level", modlunky_config)

    row = 0
    values_frame = tk.Frame(win)
    values_frame.grid(row=row, column=0, sticky="nw")
    row = row + 1

    values_row = 0
    name_label = tk.Label(values_frame, text="Name: ")
    name_label.grid(row=values_row, column=0, sticky="ne", pady=2)

    name_entry = tk.Entry(values_frame)
    name_entry.grid(row=values_row, column=1, sticky="nwe", pady=2)

    values_row = values_row + 1

    width_label = tk.Label(values_frame, text="Width: ")
    width_label.grid(row=values_row, column=0, sticky="ne", pady=2)

    width_combobox = ttk.Combobox(values_frame, value=4, height=25)
    width_combobox.set(4)
    width_combobox.grid(row=values_row, column=1, sticky="nswe", pady=2)
    width_combobox["state"] = "readonly"
    width_combobox["values"] = list(range(1, 19))

    values_row = values_row + 1

    tk.Label(values_frame, text="Height: ").grid(
        row=values_row, column=0, sticky="ne", pady=2
    )

    height_combobox = ttk.Combobox(values_frame, value=4, height=25)
    height_combobox.set(4)
    height_combobox.grid(row=values_row, column=1, sticky="nswe", pady=2)
    height_combobox["state"] = "readonly"
    height_combobox["values"] = list(range(1, 16))

    values_row = values_row + 1

    theme_label = tk.Label(values_frame, text="Theme: ")
    theme_label.grid(row=values_row, column=0, sticky="nse", pady=2)

    theme_combobox = ttk.Combobox(values_frame, height=25)
    theme_combobox.grid(row=values_row, column=1, sticky="nswe", pady=2)
    theme_combobox["state"] = "readonly"
    theme_combobox["values"] = [
        "Dwelling",
        "Jungle",
        "Volcana",
        "Olmec",
        "Tide Pool",
        "Temple",
        "Ice Caves",
        "Neo Babylon",
        "Sunken City",
        "City of Gold",
        "Duat",
        "Eggplant World",
        "Surface",
    ]

    values_row = values_row + 1

    save_format_label = tk.Label(values_frame, text="Save format: ")
    save_format_label.grid(row=values_row, column=0, sticky="nse", pady=2)

    save_format_combobox = ttk.Combobox(values_frame, height=25)
    save_format_combobox.grid(row=values_row, column=1, sticky="nswe", pady=2)
    save_format_combobox["state"] = "readonly"
    save_formats = (
        SaveFormats.base_save_formats()
        + modlunky_config.custom_level_editor_custom_save_formats
    )
    save_format_combobox["values"] = list(map(lambda format: format.name, save_formats))
    create_save_format = (
        current_save_format or modlunky_config.custom_level_editor_default_save_format
    )
    if not create_save_format:
        create_save_format = SaveFormats.base_save_formats()[0]
    if create_save_format:
        save_format_combobox.set(create_save_format.name)

    values_row = values_row + 1

    add_to_sequence_var = tk.IntVar()
    add_to_sequence_var.set(has_sequence)

    add_to_sequence_label = tk.Label(values_frame, text="Add to Sequence: ")
    add_to_sequence_label.grid(row=values_row, column=0, sticky="nes", pady=2)

    tk.Checkbutton(
        values_frame,
        text="",
        variable=add_to_sequence_var,
        onvalue=True,
        offvalue=False,
    ).grid(row=values_row, column=1, sticky="nws", pady=2)

    warning_label = tk.Label(
        win, text="", foreground="red", wraplength=200, justify=tk.LEFT
    )
    warning_label.grid(row=row, column=0, sticky="nw", pady=(10, 0))
    warning_label.grid_remove()
    row = row + 1

    def create_level():
        theme = Biomes.biome_for_name(theme_combobox.get())
        name = name_entry.get()
        width = int(width_combobox.get())
        height = int(height_combobox.get())
        save_format_index = save_format_combobox.current()
        save_format = None
        if save_format_index is not None:
            if save_format_index >= 0 and save_format_index < len(save_formats):
                save_format = save_formats[save_format_index]

        if not name or name == "":
            warning_label["text"] = "Enter a valid level file name."
            warning_label.grid()
            return
        elif re.search(r".*\..*", name) and not name.endswith(".lvl"):
            warning_label[
                "text"
            ] = "File name must not end with an extension other than .lvl"
            warning_label.grid()
            return
        elif not theme or theme == "":
            warning_label["text"] = "Select a theme."
            warning_label.grid()
            return
        elif not save_format:
            warning_label["text"] = "Select a save format."
            warning_label.grid()
            return
        else:
            warning_label["text"] = ""
            warning_label.grid_remove()
            lvl_file_name = name if name.endswith(".lvl") else name + ".lvl"
            lvl_path = Path(lvls_path) / lvl_file_name
            if lvl_path.exists():
                warning_label["text"] = "Error: Level {level} already exists!".format(
                    level=lvl_file_name
                )
                warning_label.grid()
                return
            img = ImageTk.PhotoImage(
                Image.open(BASE_DIR / "static/images/help.png").resize((20, 20))
            )
            tiles = [
                Tile("floor", "1", "", img, img),
                Tile("empty", "0", "", img, img),
                Tile("floor_hard", "X", "", img, img),
            ]
            # Fill in the level with empty tiles in the foreground and hard floor in the background.
            foreground = [["0" for _ in range(width * 10)] for _ in range(height * 8)]
            background = [["X" for _ in range(width * 10)] for _ in range(height * 8)]
            level_settings = LevelSettings()
            for level_setting in [
                "altar_room_chance",
                "back_room_chance",
                "back_room_hidden_door_cache_chance",
                "back_room_hidden_door_chance",
                "back_room_interconnection_chance",
                "background_chance",
                "flagged_liquid_rooms",
                "floor_bottom_spread_chance",
                "floor_side_spread_chance",
                "ground_background_chance",
                "idol_room_chance",
                "machine_bigroom_chance",
                "machine_rewardroom_chance",
                "machine_tallroom_chance",
                "machine_wideroom_chance",
                "max_liquid_particles",
                "mount_chance",
            ]:
                # Set all of the settings to 0 by default to turn off spawning of things like back
                # layer areas and special rooms.
                level_settings.set_obj(
                    LevelSetting(
                        name=level_setting,
                        value=0,
                        comment=None,
                    )
                )
            saved = save_level(
                lvls_path,
                lvl_path,
                backup_dir,
                width,
                height,
                theme,
                save_format,
                "",
                LevelChances(),
                level_settings,
                MonsterChances(),
                tiles,
                foreground,
                background,
            )
            if saved:
                on_level_created(lvl_file_name, add_to_sequence_var.get())
            else:
                logger.debug("error saving lvl file.")
            win.destroy()

    buttons = tk.Frame(win)
    buttons.grid(row=row, column=0, pady=(10, 0), sticky="nswe")
    row = row + 1
    buttons.columnconfigure(0, weight=1)
    buttons.columnconfigure(1, weight=1)

    create_button = tk.Button(buttons, text="Create", command=create_level)
    create_button.grid(row=0, column=0, sticky="nswe", padx=(0, 5))

    cancel_button = tk.Button(buttons, text="Cancel", command=win.destroy)
    cancel_button.grid(row=0, column=1, sticky="nswe", padx=(5, 0))
