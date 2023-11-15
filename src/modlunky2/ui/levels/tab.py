# pylint: disable=too-many-lines

from copy import deepcopy
import dataclasses
from functools import lru_cache
import datetime
import glob
import logging
import math
import os
import os.path
import re
import shutil
import tkinter as tk
import tkinter.messagebox as tkMessageBox
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from shutil import copyfile
from tkinter import ttk
from typing import Optional
from typing_extensions import Self

import pyperclip
from PIL import Image, ImageDraw, ImageEnhance, ImageTk
from serde.de import deserialize
import serde.json
from serde.se import serialize

from modlunky2.config import Config, CustomLevelSaveFormat
from modlunky2.constants import BASE_DIR
from modlunky2.levels import LevelFile
from modlunky2.levels.level_templates import (
    Chunk,
    LevelTemplate,
    LevelTemplates,
    TemplateSetting,
)
from modlunky2.levels.tile_codes import VALID_TILE_CODES, TileCode, TileCodes, ShortCode
from modlunky2.sprites import SpelunkySpriteFetcher
from modlunky2.ui.levels.custom_levels.create_level_dialog import present_create_level_dialog
from modlunky2.ui.levels.custom_levels.options_panel import OptionsPanel
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.custom_levels.save_level import save_level as save_custom_level
from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.ui.levels.shared.biomes import Biomes, BIOME
from modlunky2.ui.levels.shared.level_canvas import LevelCanvas
from modlunky2.ui.levels.shared.make_backup import make_backup
from modlunky2.ui.levels.shared.multi_canvas_container import MultiCanvasContainer
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import BaseTemplate, Setroom
from modlunky2.ui.levels.shared.textures import TextureUtil
from modlunky2.ui.levels.vanilla_levels.dual_util import make_dual, remove_dual
from modlunky2.ui.levels.vanilla_levels.level_list_panel import LevelListPanel
from modlunky2.ui.levels.vanilla_levels.level_settings_bar import LevelSettingsBar
from modlunky2.ui.levels.vanilla_levels.levels_tree import LevelsTree, LevelsTreeRoom, LevelsTreeTemplate
from modlunky2.ui.levels.vanilla_levels.rules.rules_tab import RulesTab
from modlunky2.ui.levels.vanilla_levels.variables.level_dependencies import LevelDependencies
from modlunky2.ui.levels.vanilla_levels.variables.variables_tab import VariablesTab
from modlunky2.ui.levels.warm_welcome import WarmWelcome
from modlunky2.ui.widgets import PopupWindow, ScrollableFrameLegacy, Tab
from modlunky2.utils import is_windows, tb_info

logger = logging.getLogger(__name__)


class LevelType(Enum):
    VANILLA = 1
    MODDED = 2
    CUSTOM = 3


class EditorType(Enum):
    VANILLA_ROOMS = "single_room"
    CUSTOM_LEVELS = "custom_levels"


class LevelsTab(Tab):
    def __init__(
        self,
        tab_control,
        modlunky_ui,
        modlunky_config: Config,
        *args,
        standalone=False,
        **kwargs,
    ):  # Loads editor start screen
        super().__init__(tab_control, *args, **kwargs)
        if not modlunky_config.install_dir:
            return
        self.modlunky_config = modlunky_config

        self.modlunky_ui = modlunky_ui
        self.level_list_panel = LevelListPanel(self, self.changes_made, self.reset_canvas, self.room_select, self.modlunky_config)

        self.last_selected_room = None
        self.tab_control = tab_control
        self.install_dir = modlunky_config.install_dir
        self.textures_dir = modlunky_config.install_dir / "Mods/Extracted/Data/Textures"
        self.extracts_path = self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        self.packs_path = self.install_dir / "Mods" / "Packs"

        self._sprite_fetcher = None
        self.texture_fetcher = TextureUtil(None)

        self.custom_editor_zoom_level = 30

        # Init Attributes
        self.lvls_path = None
        self.save_needed = False
        self.last_selected_file = None
        self.lvl_width = None
        self.lvl_height = None
        self.tiles_meta = None

        self.palette_panel = None
        self.palette_panel_custom = None
        self.options_panel = None

        self.tile_palette_ref_in_use = None
        self.tile_palette_map = {}
        self.tile_palette_suggestions = None
        self.lvl = None
        self.lvl_biome = None
        self.icon_add = None
        self.icon_folder = None
        self.loaded_pack = None
        self.last_selected_tab = None
        self.list_preview_tiles_ref = None
        self.current_level_custom = None
        self.custom_editor_foreground_tile_codes = None
        self.custom_editor_background_tile_codes = None
        self.editor_tab_control = None
        self.single_room_editor_tab = None
        self.full_level_editor_tab = None
        self.last_selected_editor_tab = None

        self.tree_files_custom = None
        self.button_back_custom = None
        self.button_save_custom = None
        self.custom_editor_container = None
        self.custom_editor_canvas = None
        self.custom_editor_side_panel = None
        self.tree_files = None
        self.vsb_tree_files = None
        self.rules_tab = None
        self.editor_tab = None
        self.preview_tab = None
        self.variables_tab = None
        self.button_back = None
        self.button_save = None
        self.current_value_full = None
        self.slider_zoom_full = None
        self.full_level_preview_canvas = None
        self.mag = None
        self.vanilla_editor_canvas = None
        self.button_hide_tree = None
        self.button_replace = None
        self.button_clear = None
        self.level_settings_bar = None
        self.current_level_path_custom = None

        self.usable_codes = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        def open_editor():
            if os.path.isdir(self.extracts_path):
                self.update_lvls_path(self.extracts_path)
                self.load_editor()
            else:
                tk.messagebox.showerror(
                    "Oops?",
                    "Please extract your game before using the level editor.",
                )

        self.warm_welcome = WarmWelcome(
            self,
            open_editor
        )
        self.warm_welcome.grid(row=0, column=0, columnspan=2, sticky="nswe")

        self.base_save_formats = [
            CustomLevelSaveFormat.level_sequence(),
            CustomLevelSaveFormat.vanilla(),
        ]
        # Set the format that will be used for saving new level files.
        if not self.modlunky_config.custom_level_editor_default_save_format:
            self.modlunky_config.custom_level_editor_default_save_format = (
                self.base_save_formats[0]
            )
        # Save format used in the currently loaded level file.
        self.current_save_format = None

        self.standalone = standalone
        if standalone:
            self.on_load()
            self.load_editor()

    def on_load(self):
        if not hasattr(self, "install_dir"):
            return
        self._sprite_fetcher = SpelunkySpriteFetcher(
            self.install_dir / "Mods/Extracted"
        )
        self.texture_fetcher = TextureUtil(self._sprite_fetcher)

    @lru_cache
    def lvl_icon(self, level_type):
        if level_type == LevelType.CUSTOM:
            image_path = BASE_DIR / "static/images/lvl_custom.png"
        elif level_type == LevelType.MODDED:
            image_path = BASE_DIR / "static/images/lvl_modded.png"
        else:
            image_path = BASE_DIR / "static/images/lvl.png"

        return ImageTk.PhotoImage(Image.open(image_path).resize((20, 20)))

    # Run when start screen option is selected
    def load_editor(self):
        self.show_console = False
        self.modlunky_ui.forget_console()
        self.save_needed = False
        self.last_selected_file = None
        self.tiles_meta = None
        self.warm_welcome.grid_remove()

        self.icon_add = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/add.png").resize((20, 20))
        )
        self.icon_folder = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/folder.png").resize((20, 20))
        )

        self.editor_tab_control = ttk.Notebook(self)
        self.editor_tab_control.grid(row=0, column=0, sticky="nw")

        self.editor_tab_control.bind_all(
            "<Control-s>", lambda e: self.save_changes_shortcut()
        )

        self.single_room_editor_tab = ttk.Frame(self.editor_tab_control)
        self.full_level_editor_tab = ttk.Frame(self.editor_tab_control)
        self.last_selected_editor_tab = self.single_room_editor_tab

        self.editor_tab_control.add(
            self.single_room_editor_tab, text="Vanilla room editor"
        )
        self.editor_tab_control.add(
            self.full_level_editor_tab, text="Custom level editor"
        )

        self.load_single_room_editor(self.single_room_editor_tab)
        self.load_full_level_editor(self.full_level_editor_tab)

        def tab_selected(event):
            if event.widget.select() == self.last_selected_editor_tab:
                return
            if self.save_needed and self.last_selected_file is not None:
                msg_box = tk.messagebox.askquestion(
                    "Continue?",
                    "You have unsaved changes.\nContinue without saving?",
                    icon="warning",
                )
                if msg_box == "yes":
                    self.save_needed = False
                    self.button_save["state"] = tk.DISABLED
                    self.button_save_custom["state"] = tk.DISABLED
                    logger.debug("Switched tabs without saving.")
                else:
                    self.editor_tab_control.select(self.last_selected_editor_tab)
                    return
            self.reset()
            self.load_packs(self.tree_files)
            self.load_packs(self.tree_files_custom)
            self.last_selected_editor_tab = event.widget.select()
            tab = event.widget.tab(self.last_selected_editor_tab, "text")
            if tab == "Vanilla room editor":
                self.modlunky_config.level_editor_tab = 0
            else:
                self.modlunky_config.level_editor_tab = 1
            self.modlunky_config.save()

        self.editor_tab_control.bind("<<NotebookTabChanged>>", tab_selected)
        if self.modlunky_config.level_editor_tab == 1:
            self.editor_tab_control.select(self.full_level_editor_tab)

    def load_full_level_editor(self, tab):
        tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
        tab.columnconfigure(0, weight=0)
        tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        tab.rowconfigure(0, weight=1)

        # Loads lvl files
        tree_files = ttk.Treeview(
            tab, selectmode="browse", padding=[-15, 0, 0, 0]
        )  # This tree shows the lvl files loaded from the chosen dir, excluding vanilla lvl files.
        tree_files.place(x=30, y=95)
        vsb_tree_files = ttk.Scrollbar(tab, orient="vertical", command=tree_files.yview)
        vsb_tree_files.place(x=30 + 200 + 2, y=95, height=200 + 20)
        tree_files.configure(yscrollcommand=vsb_tree_files.set)
        tree_files.grid(row=0, column=0, rowspan=1, sticky="nswe")
        vsb_tree_files.grid(row=0, column=0, sticky="nse")

        self.load_packs(tree_files)

        tree_files.bind(
            "<ButtonRelease-1>",
            lambda event: self.tree_filesitemclick(
                event, tree_files, EditorType.CUSTOM_LEVELS
            ),
        )
        self.tree_files_custom = tree_files

        # Button below the file list to exit the editor.
        self.button_back_custom = tk.Button(
            tab, text="Exit Editor", bg="black", fg="white", command=self.go_back
        )
        if not self.standalone:
            self.button_back_custom.grid(row=1, column=0, sticky="nswe")

        # Button below the file list to save changes to the current file.
        self.button_save_custom = tk.Button(
            tab, text="Save", bg="Blue", fg="white", command=self.save_changes_full
        )
        self.button_save_custom.grid(row=2, column=0, sticky="nswe")
        self.button_save_custom["state"] = tk.DISABLED

        # View that contains the canvases to edit the level along with some controls.
        editor_view = tk.Frame(tab)
        editor_view.grid(row=0, column=1, rowspan=3, sticky="nswe")
        self.custom_editor_container = editor_view

        editor_view.columnconfigure(0, weight=1)
        editor_view.columnconfigure(2, minsize=0)
        editor_view.columnconfigure(1, minsize=50)
        editor_view.rowconfigure(1, weight=1)

        def tile_codes_at(index):
            if index == 0:
                return self.custom_editor_foreground_tile_codes
            else:
                return self.custom_editor_background_tile_codes

        self.custom_editor_canvas = MultiCanvasContainer(
            editor_view,
            self.textures_dir,
            ["Foreground", "Background"],
            self.custom_editor_zoom_level,
            lambda index, row, column, is_primary: self.canvas_click_custom(
                self.custom_editor_canvas,
                index,
                self.custom_editor_zoom_level,
                row,
                column,
                is_primary,
                tile_codes_at(index),
            ),
            lambda index, row, column, is_primary: self.canvas_shiftclick_custom(
                row,
                column,
                is_primary,
                tile_codes_at(index),
            ),
            "Select a level file to begin editing",
        )
        self.custom_editor_canvas.grid(row=0, column=0, columnspan=3, rowspan=2, sticky="news")

        # Side panel with the tile palette and level settings.
        self.custom_editor_side_panel = tk.Frame(tab)
        self.custom_editor_side_panel.grid(column=2, row=0, rowspan=3, sticky="nswe")
        self.custom_editor_side_panel.rowconfigure(0, weight=1)
        self.custom_editor_side_panel.columnconfigure(0, weight=1)

        # Allow hiding the side panel so more level can be seen.
        side_panel_hidden = False
        side_panel_hide_button = tk.Button(editor_view, text=">>")

        def toggle_panel_hidden():
            nonlocal side_panel_hidden
            side_panel_hidden = not side_panel_hidden
            if side_panel_hidden:
                self.custom_editor_side_panel.grid_remove()
                side_panel_hide_button.configure(text="<<")
            else:
                self.custom_editor_side_panel.grid()
                side_panel_hide_button.configure(text=">>")

        side_panel_hide_button.configure(
            command=toggle_panel_hidden,
        )
        side_panel_hide_button.grid(column=1, row=0, sticky="nwe")

        side_panel_tab_control = ttk.Notebook(self.custom_editor_side_panel)
        side_panel_tab_control.grid(row=0, column=0, sticky="nswe")

        self.palette_panel_custom = PalettePanel(
            side_panel_tab_control,
            self.delete_tilecode_custom,
            lambda tile, percent, alt_tile: self.add_tilecode(
                tile,
                percent,
                alt_tile,
                self.palette_panel_custom,
                self.custom_editor_zoom_level
            ),
            self.texture_fetcher,
            self._sprite_fetcher,
        )
        self.options_panel = OptionsPanel(
            side_panel_tab_control,
            self.custom_editor_zoom_level,
            self.select_theme,
            self.update_custom_level_size,
            self.set_current_save_format,
            self.update_hide_grid,
            self.update_hide_room_grid,
            self.update_custom_editor_zoom,
            self.modlunky_config
        )
        side_panel_tab_control.add(self.palette_panel_custom, text="Tiles")
        side_panel_tab_control.add(self.options_panel, text="Settings")

    def load_single_room_editor(self, editor_tab):
        editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
        editor_tab.columnconfigure(0, weight=0)
        editor_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        editor_tab.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        # Loads lvl Files
        self.tree_files = ttk.Treeview(
            editor_tab, selectmode="browse", padding=[-15, 0, 0, 0]
        )  # This tree shows all the lvl files loaded from the chosen dir
        self.tree_files.place(x=30, y=95)
        self.vsb_tree_files = ttk.Scrollbar(
            editor_tab, orient="vertical", command=self.tree_files.yview
        )
        self.vsb_tree_files.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_files.configure(yscrollcommand=self.vsb_tree_files.set)
        self.tree_files.heading("#0", text="Select Pack", anchor="center")
        self.tree_files.grid(row=0, column=0, rowspan=1, sticky="nswe")
        self.vsb_tree_files.grid(row=0, column=0, sticky="nse")

        # Loads list of all the lvl files in the left farthest treeview
        # paths = Path(self.packs_path).glob('*/') #.glob('**/*.png')
        self.load_packs(self.tree_files)

        # Seperates Level Rules and Level Editor into two tabs
        self.tab_control = ttk.Notebook(editor_tab)
        self.tab_control.grid(row=0, column=1, rowspan=3, sticky="nwse")

        self.last_selected_tab = None

        def tab_selected(event):
            selection = event.widget.select()
            tab = event.widget.tab(selection, "text")
            self.last_selected_tab = str(tab)
            if str(tab) == "Full Level View":
                self.load_full_preview()

        self.tab_control.bind("<<NotebookTabChanged>>", tab_selected)

        self.rules_tab = RulesTab(self.tab_control, self.modlunky_config, self.changes_made)
        self.editor_tab = ttk.Frame(
            self.tab_control
        )  # Tab 2 is the actual level editor
        self.preview_tab = ttk.Frame(self.tab_control)
        self.variables_tab = VariablesTab(
            self.tab_control,
            self.modlunky_config,
            self.lvls_path,
            self.extracts_path,
            self.save_requested,
            self.on_resolve_conflicts
        )

        self.button_back = tk.Button(
            editor_tab, text="Exit Editor", bg="black", fg="white", command=self.go_back
        )
        if not self.standalone:
            self.button_back.grid(row=1, column=0, sticky="nswe")

        self.button_save = tk.Button(
            editor_tab,
            text="Save",
            bg="purple",
            fg="white",
            command=self.save_changes,
        )
        self.button_save.grid(row=2, column=0, sticky="nswe")
        self.button_save["state"] = tk.DISABLED

        #  View Tab

        self.current_value_full = tk.DoubleVar()

        def slider_changed(_event):
            self.load_full_preview()

        config_container = tk.Frame(self.preview_tab)
        config_container.grid(row=0, column=0, columnspan=2, sticky="nw")

        self.slider_zoom_full = tk.Scale(
            config_container,
            from_=2,
            to=100,
            length=300,
            orient="horizontal",
            variable=self.current_value_full,
            command=slider_changed,
        )
        self.slider_zoom_full.set(50)
        self.slider_zoom_full.grid(row=0, column=0, sticky="nw")

        # Checkbox to toggle the visibility of the grid lines.
        hide_grid_var = tk.IntVar()
        hide_grid_var.set(False)

        def toggle_hide_grid():
            nonlocal hide_grid_var

            self.full_level_preview_canvas.hide_grid_lines(hide_grid_var.get())

        tk.Checkbutton(
            config_container,
            text="Hide grid lines",
            variable=hide_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_grid,
        ).grid(row=0, column=1, sticky="sw", pady=5)

        self.preview_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.preview_tab.rowconfigure(1, weight=1)  # Row 0 = List box / Label

        self.full_level_preview_canvas = MultiCanvasContainer(
            self.preview_tab,
            self.textures_dir,
            ["Foreground", "Background"],
            50,
            intro_text="Select a level file to begin viewing",
        )
        self.full_level_preview_canvas.grid(row=1, column=0, columnspan=2, rowspan=2, sticky="nw")

        # Level Editor Tab
        self.tab_control.add(self.editor_tab, text="Level Editor")
        self.tab_control.add(self.rules_tab, text="Rules")
        self.tab_control.add(self.preview_tab, text="Full Level View")
        self.tab_control.add(self.variables_tab, text="Variables (Experimental)")

        self.editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.editor_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.editor_tab.rowconfigure(2, weight=1)  # Row 0 = List box / Label

        self.level_list_panel = LevelListPanel(self.editor_tab, self.changes_made, self.reset_canvas, self.room_select, self.modlunky_config)
        self.level_list_panel.grid(row=0, column=0, rowspan=5, sticky="nswe")

        self.mag = 50  # the size of each tiles in the grid; 50 is optimal

        vanilla_editor_container = tk.Frame(
            self.editor_tab,
            bg="#292929",
        )
        vanilla_editor_container.grid(row=0, column=1, rowspan=4, columnspan=8, sticky="news")

        self.vanilla_editor_canvas = MultiCanvasContainer(
            vanilla_editor_container,
            self.textures_dir,
            ["Foreground Area", "Background Area"],
            self.mag,
            lambda index, row, column, is_primary: self.canvas_click_vanilla(
                self.vanilla_editor_canvas,
                index,
                self.mag,
                row,
                column,
                is_primary,
            ),
            self.canvas_shiftclick_vanilla,
            "Select a room to begin editing",
            side_by_side=True,
        )
        self.vanilla_editor_canvas.grid(row=0, column=0, rowspan=4, columnspan=8, sticky="news")

        vanilla_editor_container.columnconfigure(3, weight=1)
        vanilla_editor_container.rowconfigure(0, weight=1)

        self.button_hide_tree = ttk.Button(
            vanilla_editor_container, text="<<", command=self.toggle_list_hide
        )
        self.button_hide_tree.grid(row=0, column=0, sticky="nw")

        self.button_replace = ttk.Button(
            vanilla_editor_container, text="Replace", command=self.replace_tiles_dia
        )
        self.button_replace.grid(row=0, column=1, sticky="nw")
        self.button_replace["state"] = tk.DISABLED

        self.button_clear = ttk.Button(
            vanilla_editor_container, text="Clear Canvas", command=self.clear_canvas
        )
        self.button_clear.grid(row=0, column=2, sticky="nw")
        self.button_clear["state"] = tk.DISABLED

        self.palette_panel = PalettePanel(
            self.editor_tab,
            self.delete_tilecode_vanilla,
            lambda tile, percent, alt_tile: self.add_tilecode(
                tile,
                percent,
                alt_tile,
                self.palette_panel,
                self.mag
            ),
            self.texture_fetcher,
            self._sprite_fetcher,
        )
        self.palette_panel.grid(row=0, column=9, rowspan=5, columnspan=4, sticky="nwse")

        self.level_settings_bar = LevelSettingsBar(self.editor_tab, self.remember_changes, self.dual_toggle)
        self.level_settings_bar.grid(row=4, column=1, columnspan=8, sticky="news")

        self.tree_files.bind(
            "<ButtonRelease-1>",
            lambda event: self.tree_filesitemclick(
                event, self.tree_files, EditorType.VANILLA_ROOMS
            ),
        )

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile_name, tile_code, tile_size):
        logger.debug("Applying custom anchor for %s", tile_name)
        tile_ref = self.tile_palette_map[tile_code]
        if tile_ref:
            logger.debug("Found %s", tile_ref[0])
            img = tile_ref[1]
            return self.texture_fetcher.adjust_texture_xy(
                img.width(), img.height(), tile_name, tile_size
            )

        return 0, 0

    def canvas_click_vanilla(
        self,
        canvas_container,
        canvas_index,
        tile_size,
        row,
        column,
        is_primary,
    ):
        tile_name, tile_code = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, tile_size)

        canvas_container.replace_tile_at(canvas_index, row, column, self.tile_palette_map[tile_code][1], x_offset, y_offset)

        col = column
        if canvas_index == 1:
            col = col + (len(self.tiles_meta[row]) + 1) // 2

        self.tiles_meta[row][col] = tile_code
        self.remember_changes()

    def canvas_shiftclick_vanilla(self, canvas_index, row, column, is_primary):
        col = column
        if canvas_index == 1:
            col = col + (len(self.tiles_meta[row]) + 1) // 2

        tile_code = self.tiles_meta[row][col]
        tile = self.tile_palette_map[tile_code]

        self.palette_panel.select_tile(tile[0], tile[2], is_primary)

    # Click event on a canvas for either left or right click to replace the tile at the cursor's position with
    # the selected tile.
    def canvas_click_custom(
        self,
        canvas_container,
        canvas_index,
        tile_size,
        row,
        column,
        is_primary,
        tile_code_matrix,
    ):

        tile_name, tile_code = self.palette_panel_custom.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, tile_size)

        canvas_container.replace_tile_at(canvas_index, row, column, self.tile_palette_map[tile_code][1], x_offset, y_offset)
        # canvas.replace_tile_at(row, column, self.tile_palette_map[tile_code][1], x_offset, y_offset)
        tile_code_matrix[row][column] = tile_code
        self.changes_made()

    def canvas_shiftclick_custom(self, row, column, is_primary, tile_code_matrix):
        tile_code = tile_code_matrix[row][column]
        tile = self.tile_palette_map[tile_code]

        self.palette_panel_custom.select_tile(tile[0], tile[2], is_primary)

    def changes_made(self):
        self.save_needed = True
        self.button_save_custom["state"] = tk.NORMAL
        self.button_save["state"] = tk.NORMAL

    def show_intro(self):
        self.custom_editor_canvas.show_intro()
        self.custom_editor_container.columnconfigure(2, minsize=0)

    def hide_intro(self):
        self.custom_editor_canvas.hide_intro()
        self.custom_editor_container.columnconfigure(2, minsize=17)

    def show_intro_full(self):
        self.full_level_preview_canvas.show_intro()

    def hide_intro_full(self):
        self.full_level_preview_canvas.hide_intro()

    def reset_canvas(self):
        self.vanilla_editor_canvas.clear()

    def reset(self):
        logger.debug("Resetting..")
        self.level_list_panel.reset()
        try:
            for palette_panel in [self.palette_panel, self.palette_panel_custom]:
                palette_panel.reset()
            self.options_panel.disable_controls()
            self.show_intro()
            self.show_intro_full()
            self.vanilla_editor_canvas.show_intro()
            self.vanilla_editor_canvas.clear()
            self.tile_palette_map = {}
            self.tile_palette_ref_in_use = None
            self.tile_palette_suggestions = None
            self.lvl = None
            self.lvl_biome = None
            self.custom_editor_foreground_tile_codes = None
            self.custom_editor_background_tile_codes = None
            self.custom_editor_canvas.clear()
            self.full_level_preview_canvas.clear()
            self.button_save_custom["state"] = tk.DISABLED
            self.button_save["state"] = tk.DISABLED
        except Exception:  # pylint: disable=broad-except
            logger.debug("canvas does not exist yet")

    def load_packs(self, tree):
        self.reset()
        logger.debug("loading packs")

        for i in tree.get_children():
            tree.delete(i)
        tree.heading("#0", text="Select Pack")
        i = 0
        for filepath in glob.iglob(str(self.packs_path) + "/*/"):
            # Convert the filepath to a string.
            path_in_str = str(filepath)
            pack_name = os.path.basename(os.path.normpath(path_in_str))
            # Add the file to the tree with the folder icon.
            tree.insert("", "end", text=str(pack_name), image=self.icon_folder)
            i = i + 1
        tree.insert("", "end", text=str("[Create_New_Pack]"), image=self.icon_add)

    def load_pack_lvls(self, tree, editor_type, lvl_dir):
        if editor_type == EditorType.VANILLA_ROOMS:
            self.load_pack_vanilla_lvls(tree, lvl_dir)
        else:
            self.load_pack_custom_lvls(tree, lvl_dir)

    def load_pack_vanilla_lvls(self, tree, lvl_dir):
        self.reset()
        self.update_lvls_path(Path(lvl_dir))
        self.organize_pack()
        logger.debug("lvls_path = %s", lvl_dir)
        for i in tree.get_children():
            tree.delete(i)

        tree.insert("", "end", values=str("<<BACK"), text=str("<<BACK"))

        in_arena_folder = str(lvl_dir).endswith("Arena")
        if not in_arena_folder:
            defaults_path = self.extracts_path
            tree.insert("", "end", text=str("ARENA"), image=self.icon_folder)
        else:
            defaults_path = self.extracts_path / "Arena"

        loaded_pack = tree.heading("#0")["text"].split("/")[0]
        root = Path(self.packs_path / loaded_pack)

        def get_levels_in_dir(dir_path):
            levels = glob.iglob(str(dir_path))
            levels = [str(file_path) for file_path in levels]
            levels = [
                os.path.basename(os.path.normpath(file_path)) for file_path in levels
            ]
            return levels

        # Load all .lvl files from extracts so we know which are modded and which are not
        # Treat all that don't exist in extracts as a custom level file
        custom_levels = get_levels_in_dir(root / "Data/Levels/***.lvl")
        vanilla_levels = get_levels_in_dir(defaults_path / "***.lvl")

        modded_levels = [
            lvl_name for lvl_name in custom_levels if lvl_name in vanilla_levels
        ]
        custom_levels = [
            lvl_name for lvl_name in custom_levels if lvl_name not in modded_levels
        ]

        if not in_arena_folder:
            for lvl_name in custom_levels:
                tree.insert(
                    "", "end", text=lvl_name, image=self.lvl_icon(LevelType.CUSTOM)
                )
        for lvl_name in vanilla_levels:
            if lvl_name in modded_levels:
                tree.insert(
                    "", "end", text=lvl_name, image=self.lvl_icon(LevelType.MODDED)
                )
            else:
                tree.insert(
                    "", "end", text=lvl_name, image=self.lvl_icon(LevelType.VANILLA)
                )

    def load_pack_custom_lvls(self, tree, lvl_dir, selected_lvl=None):
        self.reset()
        self.update_lvls_path(Path(lvl_dir))
        logger.debug("lvls_path = %s", lvl_dir)
        defaults_path = self.extracts_path
        for i in tree.get_children():
            tree.delete(i)

        tree.insert("", "end", values=str("<<BACK"), text=str("<<BACK"))

        level_files = [
            os.path.basename(os.path.normpath(i))
            for i in glob.iglob(str(lvl_dir) + "/***.lvl")
        ]
        mod_files = level_files
        is_arenas = False
        if not str(lvl_dir).endswith("Arena"):
            tree.insert("", "end", text=str("ARENA"), image=self.icon_folder)
        else:
            defaults_path = self.extracts_path / "Arena"
            extracts_files = [
                os.path.basename(os.path.normpath(i))
                for i in glob.iglob(str(defaults_path) + "/***.lvl")
            ]
            level_files = sorted(list(set(level_files).union(set(extracts_files))))
            is_arenas = True

        for lvl_name in level_files:
            if is_arenas or not (defaults_path / lvl_name).exists():
                item = None
                lvl_in_use = False
                for name in mod_files:
                    if name == lvl_name:
                        lvl_in_use = True
                        item = tree.insert(
                            "",
                            "end",
                            text=str(lvl_name),
                            image=self.lvl_icon(LevelType.MODDED),
                        )
                if not lvl_in_use:
                    item = tree.insert(
                        "",
                        "end",
                        text=str(lvl_name),
                        image=self.lvl_icon(LevelType.VANILLA),
                    )
                if item != None and lvl_name == selected_lvl:
                    tree.selection_set(item)
                    self.last_selected_file = item

        tree.insert("", "end", text=str("[Create_New_Level]"), image=self.icon_add)

    def create_level_dialog(self, tree):
        def on_created(lvl_file_name):
            # Reload the file list tree so that the new file shows up, and select it.
            self.load_pack_custom_lvls(tree, self.lvls_path, lvl_file_name)
            # Load the newly created file into the editor.
            self.read_custom_lvl_file(lvl_file_name)

        loaded_pack = self.tree_files.heading("#0")["text"].split("/")[0]
        backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
        present_create_level_dialog(self.modlunky_config, backup_dir, self.lvls_path, self.current_save_format, on_created)

    def create_pack_dialog(self, tree):
        win = PopupWindow("Create Pack", self.modlunky_config)

        col1_lbl = ttk.Label(win, text="Name: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, "New_Pack")  # Default to rooms current name
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="nswe")

        def update_then_destroy_pack():
            pack_name = ""
            for char in str(col1_ent.get()):
                if str(char) != " ":
                    pack_name += str(char)
                else:
                    pack_name += "_"
            col1_ent.delete(0, "end")
            col1_ent.insert(0, pack_name)
            if not os.path.isdir(self.packs_path / str(col1_ent.get())):
                os.mkdir(self.packs_path / str(col1_ent.get()))
                self.load_packs(tree)
                win.destroy()
            else:
                logger.warning("Pack name taken")
                col1_ent.delete(0, "end")
                col1_ent.insert(0, "Name Taken")

        separator = ttk.Separator(win)
        separator.grid(row=1, column=0, columnspan=2, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=2, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Ok", command=update_then_destroy_pack)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

    def organize_pack(self):
        loaded_pack = self.tree_files.heading("#0")["text"].split("/")[0]
        root = Path(self.packs_path / loaded_pack)
        pattern = "*.lvl"

        # gets rid of copies of the file in the wrong place
        for path, _, files in os.walk(Path(root)):
            for name in files:
                if fnmatch(name, pattern):
                    found_lvl_path = str(os.path.join(path, name))
                    found_lvl_dir = os.path.dirname(found_lvl_path)
                    found_lvl = os.path.basename(found_lvl_path)
                    if found_lvl.startswith("dm"):
                        if Path(found_lvl_dir) != Path(
                            self.packs_path / loaded_pack / "Data" / "Levels" / "Arena"
                        ):
                            logger.debug(
                                "%s found arena lvl in wrong location. Fixing that.",
                                found_lvl,
                            )
                            if not os.path.exists(
                                Path(
                                    self.packs_path
                                    / loaded_pack
                                    / "Data"
                                    / "Levels"
                                    / "Arena"
                                )
                            ):
                                os.makedirs(
                                    Path(
                                        self.packs_path
                                        / loaded_pack
                                        / "Data"
                                        / "Levels"
                                        / "Arena"
                                    )
                                )
                            shutil.move(
                                Path(found_lvl_path),
                                Path(
                                    self.packs_path
                                    / loaded_pack
                                    / "Data"
                                    / "Levels"
                                    / "Arena"
                                    / found_lvl
                                ),
                            )
                    else:
                        if Path(found_lvl_dir) != Path(
                            self.packs_path / loaded_pack / "Data" / "Levels"
                        ):
                            logger.debug(
                                "%s found lvl in wrong location. Fixing that.",
                                found_lvl,
                            )
                            if not os.path.exists(
                                Path(self.packs_path / loaded_pack / "Data" / "Levels")
                            ):
                                os.makedirs(
                                    Path(
                                        self.packs_path
                                        / loaded_pack
                                        / "Data"
                                        / "Levels"
                                    )
                                )
                            shutil.move(
                                Path(found_lvl_path),
                                Path(
                                    self.packs_path
                                    / loaded_pack
                                    / "Data"
                                    / "Levels"
                                    / found_lvl
                                ),
                            )

    def tree_filesitemclick(self, _event, tree, editor_type):
        if (
            self.save_needed
            and self.last_selected_file is not None
            and tree.heading("#0")["text"] != "Select Pack"
        ):
            msg_box = tk.messagebox.askquestion(
                "Continue?",
                "You have unsaved changes to "
                + str(tree.item(self.last_selected_file, option="text"))
                + "\nContinue without saving?",
                icon="warning",
            )
            if msg_box == "yes":
                self.save_needed = False
                self.button_save["state"] = tk.DISABLED
                logger.debug("Entered new files witout saving")
            else:
                tree.selection_set(self.last_selected_file)
                return

        item_text = ""
        for item in tree.selection():
            item_text = tree.item(item, "text")
        if item_text == "<<BACK":
            if tree.heading("#0")["text"].endswith("Arena"):
                tree.heading("#0", text=tree.heading("#0")["text"].split("/")[0])
                self.loaded_pack = tree.heading("#0")["text"].split("/")[0]
                self.load_pack_lvls(
                    tree,
                    editor_type,
                    Path(self.packs_path / self.loaded_pack / "Data" / "Levels"),
                )
            else:
                self.load_packs(tree)
        elif item_text == "ARENA" and tree.heading("#0")["text"] != "Select Pack":
            tree.heading("#0", text=tree.heading("#0")["text"] + "/Arena")
            self.loaded_pack = tree.heading("#0")["text"].split("/")[0]
            self.load_pack_lvls(
                tree,
                editor_type,
                Path(self.packs_path / self.loaded_pack / "Data" / "Levels" / "Arena"),
            )
        elif item_text == "[Create_New_Pack]":
            logger.debug("Creating new pack")
            self.create_pack_dialog(tree)
            # self.tree_files.heading('#0', text='Select Pack', anchor='center')
        elif item_text == "[Create_New_Level]":
            logger.debug("Creating new level")
            self.create_level_dialog(tree)
        elif tree.heading("#0")["text"] == "Select Pack":
            for item in tree.selection():
                self.last_selected_file = item
                item_text = tree.item(item, "text")
                tree.heading("#0", text=item_text)
                self.loaded_pack = tree.heading("#0")["text"].split("/")[0]
                self.load_pack_lvls(
                    tree,
                    editor_type,
                    Path(self.packs_path / self.loaded_pack) / "Data" / "Levels",
                )
        else:
            self.reset()
            for item in tree.selection():
                self.last_selected_file = item
                item_text = tree.item(item, "text")
                self.read_lvl_file(editor_type, item_text)

        if self.last_selected_tab == "Full Level View":
            self.load_full_preview()


    def log_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        logger.debug("%s codes left (%s)", len(self.usable_codes), codes)

    def dual_toggle(self):
        current_room = self.level_list_panel.get_selected_room()

        if current_room:
            new_room_data = current_room.rows

            if self.level_settings_bar.dual():  # converts room into dual
                new_room_data = make_dual(current_room.rows)
            else:  # converts room into non-dual
                msg_box = tk.messagebox.askquestion(
                    "Delete Dual Room?",
                    "Un-dualing this room will delete your background layer. This is not recoverable.\nContinue?",
                    icon="warning",
                )
                if msg_box == "yes":
                    new_room_data = remove_dual(current_room.rows)
                else:
                    return

            self.level_list_panel.replace_selected_room(LevelsTreeRoom(current_room.name, new_room_data))
            self.room_select(None)
            self.remember_changes()

    # Called whenever CTRL+S is pressed, saves depending on editor tab
    def save_changes_shortcut(self):
        if self.editor_tab_control.index(self.editor_tab_control.select()) == 0:
            # Vanilla room editor
            self.save_changes()
        elif self.editor_tab_control.index(self.editor_tab_control.select()) == 1:
            # Custom level editor
            self.save_changes_full()

    def save_changes_full(self):
        if not self.save_needed:
            logger.debug("No changes to save.")
            return
        old_level_file = self.current_level_custom

        loaded_pack = self.tree_files.heading("#0")["text"].split("/")[0]
        backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
        if save_custom_level(
            self.lvls_path,
            self.current_level_path_custom,
            backup_dir,
            self.lvl_width,
            self.lvl_height,
            self.lvl_biome,
            self.current_save_format,
            old_level_file.comment,
            old_level_file.level_chances,
            old_level_file.level_settings,
            old_level_file.monster_chances,
            self.tile_palette_ref_in_use,
            self.custom_editor_foreground_tile_codes,
            self.custom_editor_background_tile_codes,
        ):
            self.save_needed = False
            self.button_save_custom["state"] = tk.DISABLED
            logger.debug("Saved")
            for item in self.tree_files_custom.selection():
                self.tree_files_custom.item(item, image=self.lvl_icon(LevelType.MODDED))
        else:
            _msg_box = tk.messagebox.showerror(
                "Oops?",
                "Error saving..",
            )

    def save_changes(self):
        if self.save_needed:
            try:
                level_chances = self.rules_tab.get_level_chances()
                level_settings = self.rules_tab.get_level_settings()
                monster_chances = self.rules_tab.get_monster_chances()
                level_templates = self.level_list_panel.get_level_templates()

                tile_codes = TileCodes()
                for tilecode in self.tile_palette_ref_in_use:
                    tile_codes.set_obj(
                        TileCode(
                            name=tilecode[0].split(" ", 1)[0],
                            value=tilecode[0].split(" ", 1)[1],
                            comment="",
                        )
                    )

                level_file = LevelFile(
                    "",
                    level_settings,
                    tile_codes,
                    level_chances,
                    monster_chances,
                    level_templates,
                )
                save_path = None
                if not os.path.exists(Path(self.lvls_path)):
                    os.makedirs(Path(self.lvls_path))
                save_path = Path(
                    self.lvls_path
                    / str(self.tree_files.item(self.last_selected_file, option="text"))
                )
                loaded_pack = self.tree_files.heading("#0")["text"].split("/")[0]
                backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
                make_backup(save_path, backup_dir)
                logger.debug("Saving to %s", save_path)

                with Path(save_path).open("w", encoding="cp1252") as handle:
                    level_file.write(handle)

                logger.debug("Saved!")
                for item in self.tree_files.selection():
                    self.tree_files.item(item, image=self.lvl_icon(LevelType.MODDED))
                self.save_needed = False
                self.button_save["state"] = tk.DISABLED
                logger.debug("Saved")
            except Exception:  # pylint: disable=broad-except
                logger.critical("Failed to save level: %s", tb_info())
                _msg_box = tk.messagebox.showerror(
                    "Oops?",
                    "Error saving..",
                )
                return False
        else:
            logger.debug("No changes to save")
        return True

    def save_requested(self):
        if self.save_needed:
            msg_box = tk.messagebox.askquestion(
                "Save now?",
                "This will save all your current changes. Continue?",
                icon="warning",
            )
            if msg_box == "no":
                return False
            else:
                return self.save_changes()
        return True

    def on_resolve_conflicts(self):
        self.tree_filesitemclick(self, self.tree_files, EditorType.VANILLA_ROOMS)

    def remember_changes(self):  # remembers changes made to rooms
        current_room = self.level_list_panel.get_selected_room()
        if current_room:
            new_room_data = ""
            if self.level_settings_bar.dual():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!dual"
            if self.level_settings_bar.purge():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!purge"
            if self.level_settings_bar.flip():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!flip"
            if self.level_settings_bar.only_flip():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!onlyflip"
            if self.level_settings_bar.rare():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!rare"
            if self.level_settings_bar.hard():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!hard"
            if self.level_settings_bar.liquid():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!liquid"
            if self.level_settings_bar.ignore():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!ignore"

            for row in self.tiles_meta:
                if new_room_data != "":
                    new_room_data += "\n"
                for block in row:
                    if str(block) == "None":
                        new_room_data += str(" ")
                    else:
                        new_room_data += str(block)
            room_save = []
            for line in new_room_data.split("\n", 100):
                room_save.append(line)
            # Put it back in with the upated values
            self.level_list_panel.replace_selected_room(LevelsTreeRoom(current_room.name, room_save))

            logger.debug("temp saved: \n%s", new_room_data)
            logger.debug("Changes remembered!")
            self.changes_made()
        else:
            self.vanilla_editor_canvas.clear()
            self.vanilla_editor_canvas.show_intro()

    def toggle_list_hide(self):
        if self.button_hide_tree["text"] == "<<":
            self.level_list_panel.grid_remove()
            self.editor_tab.columnconfigure(0, minsize=0)  # Column 0 = Level List
            self.button_hide_tree["text"] = ">>"
        else:
            self.level_list_panel.grid()
            self.editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
            self.button_hide_tree["text"] = "<<"

    def replace_tiles_dia(self):
        # Set up window
        win = PopupWindow("Replace Tiles", self.modlunky_config)

        replacees = []
        for tile in self.tile_palette_ref_in_use:
            replacees.append(str(tile[0]))

        col1_lbl = ttk.Label(win, text="Replace all ")
        col1_lbl.grid(row=0, column=0)
        combo_replace = ttk.Combobox(win, height=20)
        combo_replace["values"] = replacees
        combo_replace.grid(row=0, column=1)

        col2_lbl = ttk.Label(win, text="with ")
        col2_lbl.grid(row=1, column=0)
        combo_replacer = ttk.Combobox(win, height=20)
        combo_replacer["values"] = replacees
        combo_replacer.grid(row=1, column=1)

        col3_lbl = ttk.Label(win, text="in ")
        col3_lbl.grid(row=2, column=0)
        combo_where = ttk.Combobox(win, height=20)
        combo_where["values"] = ["all rooms", "current room"]
        combo_where.set("current room")
        combo_where.grid(row=2, column=1)

        error_lbl = tk.Label(win, text="", fg="red")
        error_lbl.grid(row=3, column=0, columnspan=2)
        error_lbl.grid_remove()

        def update_then_destroy():
            if (
                str(combo_replace.get().split(" ", 1)[0]) != "empty"
                and combo_replace.get() != ""
                and combo_replacer.get() != ""
            ):
                if str(combo_where.get()) not in ["all rooms", "current room"]:
                    error_lbl["text"] = "Invalid parameter"
                    error_lbl.grid()
                    return
                valid_1 = False
                valid_2 = False
                for valid_tile in replacees:
                    if str(combo_replace.get()) == valid_tile:
                        valid_1 = True
                    if str(combo_replacer.get()) == valid_tile:
                        valid_2 = True
                if valid_1 is False or valid_2 is False:
                    error_lbl["text"] = "Invalid parameter"
                    error_lbl.grid()
                    return
                if (
                    str(combo_where.get()) == "current room"
                    and self.last_selected_room is None
                ):
                    error_lbl["text"] = "No current room selected.."
                    error_lbl.grid()
                    return
                self.replace_tiles(
                    str(combo_replace.get().split(" ", 1)[1]),
                    str(combo_replacer.get().split(" ", 1)[1]),
                    str(combo_where.get()),
                )
                win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=4, column=0, columnspan=3, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=5, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Replace", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

    def replace_rooms(self, replacement_rooms):
        new_selected_room = self.level_list_panel.replace_rooms(replacement_rooms)
        if new_selected_room:
            self.last_selected_room = new_selected_room
            self.room_select(None)

    def replace_tiles(self, tile, new_tile, replace_where):
        if replace_where == "all rooms":
            existing_templates = self.level_list_panel.get_rooms()
            new_templates = []
            for existing_template in existing_templates:
                new_rooms = []
                for existing_room in existing_template.rooms:
                    room_data = []
                    room_name = existing_room.name
                    room_rows = existing_room.rows
                    for row in room_rows:
                        new_row = ""
                        if not str(row).startswith(r"\!"):
                            for replace_code in row:
                                if replace_code == str(tile):
                                    replace_code = str(new_tile)
                                    new_row += str(new_tile)
                                else:
                                    new_row += str(replace_code)
                        else:
                            new_row = str(row)
                        room_data.append(new_row)
                    new_rooms.append(LevelsTreeRoom(room_name, room_data))
                new_templates.append(LevelsTreeTemplate(existing_template.name, new_rooms))
            self.replace_rooms(new_templates)
            self.changes_made()
        else:
            row_count = 0
            for row in self.tiles_meta:
                col_count = 0
                for _ in row:
                    if self.tiles_meta[int(row_count)][int(col_count)] == tile:
                        self.tiles_meta[int(row_count)][int(col_count)] = new_tile
                    col_count = col_count + 1
                row_count = row_count + 1
            self.remember_changes()  # remember changes made
            self.room_select(None)

    def clear_canvas(self):
        msg_box = tk.messagebox.askquestion(
            "Clear Canvases?",
            "Completely clear your canvas? This isn't recoverable.",
            icon="warning",
        )
        if msg_box == "yes":
            row_count = 0
            for row in self.tiles_meta:
                col_count = 0
                for _ in row:
                    self.tiles_meta[int(row_count)][int(col_count)] = "0"
                    col_count = col_count + 1
                row_count = row_count + 1
            self.vanilla_editor_canvas.clear()
            self.vanilla_editor_canvas.draw_background(self.lvl_biome)
            self.vanilla_editor_canvas.draw_grid()
            self.remember_changes()  # remember changes made

    def delete_tilecode_vanilla(self, tile_name, tile_code):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air.",
            icon="warning",
        )
        if msg_box == "yes":
            if tile_name == r"empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            self.replace_tiles(tile_code, "0", "all rooms")
            logger.debug("Replaced %s in all rooms with air/empty", tile_name)

            self.usable_codes.append(str(tile_code))
            logger.debug("%s is now available for use.", tile_code)

            # Adds tilecode back to list to be reused.
            for id_ in self.tile_palette_ref_in_use:
                if str(tile_code) == str(id_[0].split(" ", 2)[1]):
                    self.tile_palette_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile_name)

            self.populate_tilecode_palette(self.palette_panel)

            self.log_codes_left()
            self.changes_made()
            self.variables_tab.check_dependencies()

    def delete_tilecode_custom(self, tile_name, tile_code):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air.",
            icon="warning",
        )
        if msg_box == "yes":
            if tile_name == r"empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            tile_code_matrices = [
                self.custom_editor_foreground_tile_codes,
                self.custom_editor_background_tile_codes,
            ]
            new_tile = self.tile_palette_map["0"]
            for matrix_index in range(len(tile_code_matrices)):
                tile_code_matrix = tile_code_matrices[matrix_index]
                for row in range(len(tile_code_matrix)):
                    for column in range(len(tile_code_matrix[row])):
                        if str(tile_code_matrix[row][column]) == str(tile_code):
                            self.custom_editor_canvas.replace_tile_at(matrix_index, row, column, new_tile[1])
                            tile_code_matrix[row][column] = "0"
            self.usable_codes.append(str(tile_code))
            logger.debug("%s is now available for use.", tile_code)

            # Adds tilecode back to list to be reused.
            for id_ in self.tile_palette_ref_in_use:
                if str(tile_code) == str(id_[0].split(" ", 2)[1]):
                    self.tile_palette_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile_name)

            self.populate_tilecode_palette(self.palette_panel_custom)

            self.log_codes_left()
            self.changes_made()

    def add_tilecode(
        self,
        tile,
        percent,
        alt_tile,
        palette_panel,
        scale,
    ):
        usable_code = None

        invalid_tilecodes = []
        if tile not in VALID_TILE_CODES:
            invalid_tilecodes.append(tile)

        if alt_tile not in VALID_TILE_CODES:
            invalid_tilecodes.append(alt_tile)

        i = 0
        for invalid_tile in invalid_tilecodes:
            lua_tile = tkMessageBox.askquestion(
                "Uh Oh!",
                str(invalid_tile) + " isn't a valid tile id. Add as a custom lua tile?",
            )
            if lua_tile != "yes":
                return
            i = i + 1

        new_tile_code = tile
        if int(percent) < 100:
            new_tile_code += "%" + percent
            # Have to use a temporary directory due to TCL/Tkinter is trying to write
            # to a file name, not a file handle, and windows doesn't support sharing the
            # file between processes
            if alt_tile != "empty":
                new_tile_code += "%" + alt_tile

        tile_image = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(new_tile_code, self.lvl_biome, self.lvl, scale)
        )
        tile_image_picker = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(new_tile_code, self.lvl_biome, self.lvl, 40)
        )

        # compares tile id to tile ids in palette list
        for palette_tile in self.tile_palette_ref_in_use:
            palette_tile = palette_tile[0].split()[0].strip()
            if new_tile_code == palette_tile:
                tkMessageBox.showinfo("Uh Oh!", "You already have that!")
                return

        if len(self.usable_codes) > 0:
            usable_code = self.usable_codes[0]
            for code in self.usable_codes:
                if code == usable_code:
                    self.usable_codes.remove(code)
        else:
            tkMessageBox.showinfo(
                "Uh Oh!", "You've reached the tilecode limit; delete some to add more"
            )
            return

        ref_tile = []
        ref_tile.append(new_tile_code + " " + str(usable_code))
        ref_tile.append(tile_image)
        ref_tile.append(tile_image_picker)
        self.tile_palette_ref_in_use.append(ref_tile)
        self.tile_palette_map[usable_code] = ref_tile

        self.populate_tilecode_palette(palette_panel)
        self.log_codes_left()
        self.changes_made()
        if palette_panel == self.palette_panel:
            self.variables_tab.check_dependencies()
        return ref_tile



    def populate_tilecode_palette(self, palette_panel):
        palette_panel.update_with_palette(self.tile_palette_ref_in_use, self.tile_palette_suggestions, self.lvl_biome, self.lvl)

    def go_back(self):
        msg_box = tk.messagebox.askquestion(
            "Exit Editor?",
            "Exit editor and return to start screen?\n Load data will be lost.",
            icon="warning",
        )
        if msg_box == "yes":
            self.editor_tab_control.grid_remove()
            self.warm_welcome.grid()
            self.tab_control.grid_remove()
            self.tree_files.grid_remove()
            # Resets widgets
            self.button_replace["state"] = tk.DISABLED
            self.button_clear["state"] = tk.DISABLED
            self.vanilla_editor_canvas.clear()
            self.vanilla_editor_canvas.show_intro()
            self.button_back.grid_remove()
            self.button_save.grid_remove()
            self.vsb_tree_files.grid_remove()
            # Removes any old tiles that might be there from the last file.
            for palette_panel in [self.palette_panel, self.palette_panel_custom]:
                palette_panel.reset()

    def load_full_preview(self):
        self.list_preview_tiles_ref = []
        # sets default level size for levels that might not have a size variable like the challenge levels.
        # 8x8 is what I went with
        level_height = 8
        level_width = 8

        mag_full = int(self.slider_zoom_full.get() / 2)
        self.full_level_preview_canvas.clear()
        self.full_level_preview_canvas.set_zoom(mag_full)

        full_size = None
        if len(self.tree_files.selection()) > 0:
            full_size = self.rules_tab.get_full_size()
            if full_size is not None:
                logger.debug("Size found: %s", full_size)
                level_height = int(full_size.split(", ")[1])
                level_width = int(full_size.split(", ")[0])
            self.full_level_preview_canvas.configure_size(level_width, level_height)
            self.full_level_preview_canvas.draw_background(self.lvl_biome)
            self.full_level_preview_canvas.draw_grid()
        else:
            self.show_intro_full()
            return

        self.hide_intro_full()

        def flip_text(x_coord):
            return x_coord[::-1]

        for setroom_template in self.level_list_panel.get_setrooms():
            room_x = setroom_template.setroom.coords.x
            room_y = setroom_template.setroom.coords.y

            logger.debug("%s", setroom_template.template.name)
            logger.debug("Room pos: %sx%s", room_x, room_y)
            current_room_tiles = []
            current_room_tiles_dual = []
            layers = []

            tree_rooms = setroom_template.template.rooms
            flip_room = False
            if len(tree_rooms) != 0:
                tree_room = tree_rooms[0]
                for cr_line in tree_room.rows:
                    if str(cr_line).startswith(r"\!"):
                        logger.debug("found tag %s", cr_line)
                        if str(cr_line) == r"\!onlyflip":
                            flip_room = True
                        elif str(cr_line) == r"\!ignore":
                            continue
                    else:
                        logger.debug("appending %s", cr_line)
                        load_line = ""
                        load_line_dual = ""
                        dual_mode = False
                        for char in str(cr_line):
                            if str(char) == " ":
                                dual_mode = True
                                logger.debug("dual room found")

                                if flip_room:
                                    current_room_tiles.append(flip_text(str(load_line)))
                                else:
                                    current_room_tiles.append(str(load_line))
                            else:
                                if dual_mode:
                                    load_line_dual += str(char)
                                else:
                                    load_line += str(char)
                        if dual_mode:
                            if flip_room:
                                current_room_tiles_dual.append(
                                    flip_text(str(load_line_dual))
                                )
                            else:
                                current_room_tiles_dual.append(str(load_line_dual))
                        else:
                            if flip_room:
                                current_room_tiles.append(flip_text(str(load_line)))
                            else:
                                current_room_tiles.append(str(load_line))

                curcol = 0

                layers.append(current_room_tiles)
                layers.append(current_room_tiles_dual)

                for layer_index, layer in enumerate(layers):
                    for currow, room_row in enumerate(layer):
                        curcol = 0
                        tile_image_full = None
                        logger.debug("Room row: %s", room_row)
                        for block in str(room_row):
                            if str(block) != " ":
                                tile_name = ""
                                tiles = [
                                    c
                                    for c in self.tile_palette_ref_in_use
                                    if str(" " + block) in str(c[0])
                                ]
                                if tiles:
                                    tile_name = str(tiles[-1][0]).split(" ", 1)[0]
                                    new_ref = True
                                    for (
                                        preview_tile_ref
                                    ) in self.list_preview_tiles_ref:
                                        if tile_name == str(preview_tile_ref[0]):
                                            new_ref = False
                                            tile_image_full = preview_tile_ref[1]

                                    if new_ref:
                                        tile_ref = []
                                        tile_image = ImageTk.PhotoImage(
                                            ImageTk.getimage(tiles[-1][1])
                                            .resize(
                                                (mag_full, mag_full),
                                                Image.Resampling.LANCZOS,
                                            )
                                            .convert("RGBA")
                                        )
                                        tile_ref.append(tile_name)
                                        tile_ref.append(tile_image)
                                        self.list_preview_tiles_ref.append(tile_ref)
                                        tile_image_full = (
                                            self.list_preview_tiles_ref[
                                                len(self.list_preview_tiles_ref) - 1
                                            ][1]
                                        )
                                else:
                                    # There's a missing tile id somehow
                                    logger.debug("%s Not Found", block)

                                self.full_level_preview_canvas.replace_tile_at(
                                    layer_index,
                                    room_y * 8 + currow,
                                    room_x * 10 + curcol,
                                    tile_image_full,
                                    0,
                                    0,
                                )
                            curcol = curcol + 1

    def update_custom_editor_zoom(self, zoom):
        self.custom_editor_zoom_level = zoom
        if self.lvl:
            for tile in self.tile_palette_ref_in_use:
                tile_name = tile[0].split(" ", 2)[0]
                tile[1] = ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        tile_name,
                        self.lvl_biome,
                        self.lvl,
                        self.custom_editor_zoom_level,
                    )
                )
            self.custom_editor_canvas.set_zoom(zoom)
            self.draw_custom_level_canvases(self.lvl_biome)

    def update_hide_grid(self, hide_grid):
        self.custom_editor_canvas.hide_grid_lines(hide_grid)

    def update_hide_room_grid(self, hide_grid):
        self.custom_editor_canvas.hide_room_lines(hide_grid)

    def room_select(self, _event):  # Loads room when click if not parent node
        dual_mode = False
        selected_room = self.level_list_panel.get_selected_room()
        if selected_room:
            self.vanilla_editor_canvas.clear()
            self.vanilla_editor_canvas.hide_intro()

            self.last_selected_room = selected_room
            current_settings = []
            current_room_tiles = []
            current_settings = []

            for cr_line in selected_room.rows:
                if str(cr_line).startswith(r"\!"):
                    logger.debug("found tag %s", cr_line)
                    current_settings.append(cr_line)
                else:
                    logger.debug("appending %s", cr_line)
                    current_room_tiles.append(str(cr_line))
                    for char in str(cr_line):
                        if str(char) == " ":
                            dual_mode = True


            dual_mode = r"\!dual" in current_settings
            self.level_settings_bar.set_dual(dual_mode)
            self.level_settings_bar.set_flip(r"\!flip" in current_settings)
            self.level_settings_bar.set_purge(r"\!purge" in current_settings)
            self.level_settings_bar.set_only_flip(r"\!onlyflip" in current_settings)
            self.level_settings_bar.set_ignore(r"\!ignore" in current_settings)
            self.level_settings_bar.set_rare(r"\!rare" in current_settings)
            self.level_settings_bar.set_hard(r"\!hard" in current_settings)
            self.level_settings_bar.set_liquid(r"\!liquid" in current_settings)

            rows = len(current_room_tiles)
            cols = len(str(current_room_tiles[0]))

            roomwidth = int(math.ceil(cols / 10))
            if dual_mode:
                roomwidth = int(math.ceil(((cols - 1) / 2) / 10))
            self.vanilla_editor_canvas.configure_size(roomwidth, int(math.ceil(rows / 8)))

            # Draw lines to fill the size of the level.
            self.vanilla_editor_canvas.draw_background(self.lvl_biome)
            self.vanilla_editor_canvas.draw_grid()

            self.vanilla_editor_canvas.hide_canvas(1, not dual_mode)

            # Create a grid of None to store the references to the tiles
            self.tiles_meta = [
                [None for _ in range(cols)] for _ in range(rows)
            ]  # meta for tile

            currow = -1
            curcol = 0
            for room_row in current_room_tiles:
                curcol = 0
                currow = currow + 1
                tile_image = None
                logger.debug("Room row: %s", room_row)
                for block in str(room_row):
                    if str(block) != " ":
                        tile_name = ""
                        # for _palette_block in self.tile_palette_ref_in_use:
                        tiles = [
                            c
                            for c in self.tile_palette_ref_in_use
                            if str(" " + block) in str(c[0])
                        ]
                        if tiles:
                            tile_image = tiles[-1][1]
                            tile_name = str(tiles[-1][0]).split(" ", 1)[0]
                        else:
                            # There's a missing tile id somehow
                            logger.debug("%s Not Found", block)
                        if dual_mode and curcol > int((cols - 1) / 2):
                            x2_coord = int(curcol - ((cols - 1) / 2) - 1)
                            x_coord, y_coord = self.texture_fetcher.adjust_texture_xy(
                                tile_image.width(),
                                tile_image.height(),
                                tile_name,
                            )
                            self.vanilla_editor_canvas.replace_tile_at(
                                1,
                                currow,
                                x2_coord,
                                tile_image,
                                x_coord,
                                y_coord,
                            )
                            self.tiles_meta[currow][curcol] = block
                        else:
                            x_coord, y_coord = self.texture_fetcher.adjust_texture_xy(
                                tile_image.width(),
                                tile_image.height(),
                                tile_name,
                            )
                            self.vanilla_editor_canvas.replace_tile_at(
                                0,
                                currow,
                                curcol,
                                tile_image,
                                x_coord,
                                y_coord,
                            )
                            self.tiles_meta[currow][curcol] = block
                    curcol = curcol + 1
        else:
            self.vanilla_editor_canvas.clear()
            self.vanilla_editor_canvas.hide_canvas(1, True)
            self.vanilla_editor_canvas.show_intro()
        self.button_clear["state"] = tk.NORMAL

    def read_lvl_file(self, editor_type, lvl):
        if editor_type == EditorType.VANILLA_ROOMS:
            return self.read_vanilla_lvl_file(lvl)
        else:
            return self.read_custom_lvl_file(lvl)

    def read_vanilla_lvl_file(self, lvl):
        self.last_selected_room = None
        self.usable_codes = ShortCode.usable_codes()
        self.variables_tab.update_current_level_name(lvl)
        self.variables_tab.check_dependencies()

        self.rules_tab.reset()

        self.level_list_panel.reset()
        self.button_replace["state"] = tk.NORMAL

        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        self.lvl = lvl

        self.lvl_biome = Biomes.get_biome_for_level(lvl)

        logger.debug("searching %s", self.lvls_path / lvl)
        if Path(self.lvls_path / lvl).exists():
            logger.debug("Found this lvl in pack; loading it instead")
            lvl_path = Path(self.lvls_path) / lvl
        else:
            logger.debug(
                "Did not find this lvl in pack; loading it from extracts instead"
            )
            if self.tree_files.heading("#0")["text"].endswith("Arena"):
                lvl_path = self.extracts_path / "Arena" / lvl
            else:
                lvl_path = self.extracts_path / lvl

        # Levels to load dependency tilecodes from
        level_dependencies = LevelDependencies.dependencies_for_level(lvl)
        levels = []
        for dependency in level_dependencies:
            levels.append(LevelDependencies.loaded_level_file_for_path(dependency, self.lvls_path, self.extracts_path))
        levels.append(LevelFile.from_path(Path(lvl_path)))

        level = None
        for level in levels:
            logger.debug("%s loaded.", level.comment)
            level_tilecodes = level.tile_codes.all()

            for tilecode in level_tilecodes:
                tilecode_item = []
                tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

                img = self.texture_fetcher.get_texture(tilecode.name, self.lvl_biome, lvl, self.mag)
                selection_img = self.texture_fetcher.get_texture(tilecode.name, self.lvl_biome, lvl, 40)

                tilecode_item.append(ImageTk.PhotoImage(img))
                tilecode_item.append(ImageTk.PhotoImage(selection_img))

                self.palette_panel.select_tile(tilecode_item[0], tilecode_item[2], True)
                self.palette_panel.select_tile(tilecode_item[0], tilecode_item[2], False)

                for i in self.tile_palette_ref_in_use:
                    if str(i[0]).split(" ", 1)[1] == str(tilecode.value):
                        self.tile_palette_ref_in_use.remove(i)

                for i in self.usable_codes:
                    if str(i) == str(tilecode.value):
                        self.usable_codes.remove(i)

                self.tile_palette_ref_in_use.append(tilecode_item)
                self.tile_palette_map[tilecode.value] = tilecode_item

        if level is None:
            return

        if lvl.startswith(
            "generic"
        ):  # adds tilecodes to generic that it relies on yet doesn't provide
            generic_needs = [
                ["4", "push_block"],
                ["t", "treasure"],
                ["1", "floor"],
                ["6", "chunk_air"],
                ["=", "minewood_floor"],
            ]
            for need in generic_needs:
                for code in self.usable_codes:
                    if str(code) == need[0] and not any(
                        need[0] in str(code_in_use[0].split(" ", 3)[1])
                        for code_in_use in self.tile_palette_ref_in_use
                    ):
                        for i in self.usable_codes:
                            if str(i) == str(need[0]):
                                self.usable_codes.remove(i)
                        tilecode_item = []
                        tilecode_item.append(str(need[1]) + " " + str(need[0]))

                        img = self.texture_fetcher.get_texture(
                            str(need[1]), self.lvl_biome, lvl, self.mag
                        )
                        img_select = self.texture_fetcher.get_texture(
                            str(need[1]), self.lvl_biome, lvl, 40
                        )

                        tilecode_item.append(ImageTk.PhotoImage(img))
                        tilecode_item.append(ImageTk.PhotoImage(img_select))
                        self.tile_palette_ref_in_use.append(tilecode_item)
                        self.tile_palette_map[need[0]] = tilecode_item
        self.populate_tilecode_palette(self.palette_panel)

        self.rules_tab.load_level_settings(level.level_settings)
        self.rules_tab.load_monster_chances(level.monster_chances)
        self.rules_tab.load_level_chances(level.level_chances)

        level_templates = level.level_templates.all()

        tree_templates = []
        for template in level_templates:
            template_comment = ""
            if str(template.comment) != "":
                template_comment = "// " + str(template.comment)
            rooms = []
            for room in template.chunks:
                room_string = []  # makes room data into string for storing

                for setting in room.settings:
                    room_string.append(r"\!" + str(setting).split(".", 1)[1].lower())

                i = 0
                for line in room.foreground:
                    foreground = ""
                    background = ""
                    for code in line:
                        foreground += str(code)
                    if len(room.background) > 0:
                        background += " "
                        for code in room.background[i]:
                            background += str(code)
                    room_string.append(foreground + background)
                    i = i + 1

                room_name = "room"
                comment = str(room.comment).lstrip("/ ").strip()
                if comment:
                    room_name = comment

                rooms.append(LevelsTreeRoom(str(room_name), room_string))
            tree_templates.append(LevelsTreeTemplate(str(template.name) + "   " + template_comment, rooms))
        self.level_list_panel.set_rooms(tree_templates)

    def read_custom_lvl_file(self, lvl, theme=None):
        if Path(self.lvls_path / lvl).exists():
            logger.debug("Found this lvl in pack; loading it")
            lvl_path = Path(self.lvls_path) / lvl
        else:
            logger.debug(
                "Did not find this lvl in pack; loading it from extracts instead"
            )
            if self.tree_files_custom.heading("#0")["text"].endswith("Arena"):
                lvl_path = self.extracts_path / "Arena" / lvl
            else:
                lvl_path = self.extracts_path / lvl
        level = LevelFile.from_path(lvl_path)

        # Try to detect what save format the file uses by attempting to read the room
        # at (0, 0) which should always exist in a valid lvl file.
        save_format = self.read_save_format(level)
        if not save_format:
            # If the room couldn't be found, pop up a dialog asking the user to create
            # a new save format to load the file with. If a new format is created,
            # we can then attempt to load the file again.
            self.show_format_error_dialog(lvl, level)
            return

        # Refresh the list of usable tile codes to contain all of the tile codes
        # that are supported by the level editor.
        self.usable_codes = ShortCode.usable_codes()

        self.lvl = lvl
        self.current_level_custom = level
        self.current_level_path_custom = Path(self.lvls_path) / lvl
        self.hide_intro()

        self.set_current_save_format(save_format)

        # Attempt to read the theme from the level file. The theme will be saved in
        # a comment in each room.
        theme = self.read_theme(level, self.current_save_format)
        if not theme and self.tree_files_custom.heading("#0")["text"].endswith("Arena"):
            themes = [
                BIOME.DWELLING,
                BIOME.JUNGLE,
                BIOME.VOLCANA,
                BIOME.TIDE_POOL,
                BIOME.TEMPLE,
                BIOME.ICE_CAVES,
                BIOME.NEO_BABYLON,
                BIOME.SUNKEN_CITY,
            ]
            for x, themeselect in enumerate(themes):
                if lvl.startswith("dm" + str(x + 1)):
                    theme = themeselect
        self.lvl_biome = theme or BIOME.DWELLING

        self.options_panel.update_theme(theme)
        self.options_panel.enable_controls()

        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        hard_floor_code = None
        # Populate the tile palette from the tile codes listed in the level file.
        for tilecode in level.tile_codes.all():
            tilecode_item = []
            tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

            img = self.texture_fetcher.get_texture(
                tilecode.name, theme, lvl, self.custom_editor_zoom_level
            )
            img_select = self.texture_fetcher.get_texture(
                tilecode.name, theme, lvl, 40
            )

            tilecode_item.append(ImageTk.PhotoImage(img))
            tilecode_item.append(ImageTk.PhotoImage(img_select))

            self.usable_codes.remove(tilecode.value)
            self.tile_palette_ref_in_use.append(tilecode_item)
            self.tile_palette_map[tilecode.value] = tilecode_item
            if str(tilecode.name) == "floor_hard":
                # Keep track of the tile code used for hard floors since this will be
                # used to populate the back layer tiles for rooms that are not dual.
                hard_floor_code = tilecode.value

        # If a tile for hard floor was not found, create one since it is needed for the
        # empty back layer rooms.
        if hard_floor_code is None:
            # The preferred tile code for hard floor is X, so use that if it is available.
            # Otherwise, just use the first available code.
            if self.usable_codes.count("X") > 0:
                hard_floor_code = "X"
            else:
                hard_floor_code = self.usable_codes[0]
            self.usable_codes.remove(hard_floor_code)
            tilecode_item = [
                "floor_hard " + str(hard_floor_code),
                ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        "floor_hard", theme, lvl, self.custom_editor_zoom_level
                    )
                ),
                ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        "floor_hard", theme, lvl, 40
                    )
                ),
            ]
            self.tile_palette_ref_in_use.append(tilecode_item)
            self.tile_palette_map[hard_floor_code] = tilecode_item

        secondary_backup_index = 0

        # Populate the default tile code for left clicks.
        if "1" in self.tile_palette_map:
            # If there is a "1" tile code, guess it is a good default tile since it is often the floor.
            tile = self.tile_palette_map["1"]
            self.palette_panel_custom.select_tile(tile[0], tile[2], True)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there is no "1" tile, just populate with the first tile.
            tile = self.tile_palette_ref_in_use[0]
            self.palette_panel_custom.select_tile(tile[0], tile[2], True)
            secondary_backup_index = 1

        # Populate the default tile code for right clicks.
        if "0" in self.tile_palette_map:
            # If there is a "0" tile code, guess it is a good default secondary tile since it is often the empty tile.
            tile = self.tile_palette_map["0"]
            self.palette_panel_custom.select_tile(tile[0], tile[2], False)
        elif len(self.tile_palette_ref_in_use) > secondary_backup_index:
            # If there is not a "0" tile code, populate with the second tile code if the
            # primary tile code was populated from the first one.
            tile = self.tile_palette_ref_in_use[secondary_backup_index]
            self.palette_panel_custom.select_tile(tile[0], tile[2], False)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there are only one tile code available, populate both right and
            # left click with it.
            tile = self.tile_palette_ref_in_use[0]
            self.palette_panel_custom.select_tile(tile[0], tile[2], False)

        # Populate the list of suggested tiles based on the current theme.
        self.tile_palette_suggestions = suggested_tiles_for_theme(theme)
        # Load images and create buttons for all of the tile codes and suggestions that
        # we populated.
        self.populate_tilecode_palette(self.palette_panel_custom)

        # Creates a matrix of empty elements that rooms from the level file will load into.
        rooms = [[None for _ in range(8)] for _ in range(15)]

        for template in level.level_templates.all():
            match = Setroom.match_setroom(self.current_save_format.room_template_format, template.name)
            if match is not None:
                # Fill in the room list at the coordinate of this room with the loaded template data.
                rooms[match.y][match.x] = template

        # Filtered room matrix which will be populated with the rooms that were not empty.
        # Essentially, we are going to be removing all of the 'None' from the rooms matrix
        # which weren't replaced with an actual room.
        filtered_rooms = []
        for row in rooms:
            # Filter out all of the None from each row in the matrix.
            newrow = list(filter(lambda room: room is not None, row))
            if len(newrow) > 0:
                filtered_rooms.append(newrow)
            else:
                # If the row was empty, do not include it at all and also break out
                # of the loop to not include any future rows.
                break

        height = len(filtered_rooms)
        width = len(filtered_rooms[0])
        self.lvl_width = width
        self.lvl_height = height

        self.options_panel.update_level_size(width, height)

        foreground_tiles = ["" for _ in range(height * 8)]
        background_tiles = ["" for _ in range(height * 8)]

        # Takes the matrix of rooms and creates an array of strings out of it, where each
        # element in the array is a full row of tiles across the entire level, combining
        # all rooms in the row.
        for i, row in enumerate(filtered_rooms):
            for template in row:
                room = template.chunks[0]
                for line_index, line in enumerate(room.foreground):
                    index = i * 8 + line_index
                    foreground_tiles[index] = foreground_tiles[index] + "".join(line)
                    if (
                        room.background is not None
                        and len(room.background) > line_index
                    ):
                        background_tiles[index] = background_tiles[index] + "".join(
                            room.background[line_index]
                        )
                    else:
                        # If there is no back layer for this room, populate the back layer tile codes
                        # with hard floor tile codes.
                        background_tiles[index] = (
                            background_tiles[index] + hard_floor_code * 10
                        )

        # Map each long string that contains the entire row of tile codes into an
        # array where each element of the array is a single tile code.
        def map_rooms(layer):
            return list(
                map(lambda room_row: list(map(lambda tile: tile, str(room_row))), layer)
            )

        self.custom_editor_foreground_tile_codes = map_rooms(foreground_tiles)
        self.custom_editor_background_tile_codes = map_rooms(background_tiles)

        # Fetch the images for each tile and draw them in the canvases.
        self.draw_custom_level_canvases(theme)

    def draw_custom_level_canvases(self, theme):
        width = self.lvl_width
        height = self.lvl_height

        # Clear all existing images from the canvas before drawing the new images.
        self.custom_editor_canvas.clear()
        self.custom_editor_canvas.configure_size(width, height)

        # Draw lines to fill the size of the level.
        self.custom_editor_canvas.draw_background(theme)
        self.custom_editor_canvas.draw_grid()
        self.custom_editor_canvas.draw_room_grid()

        # Draws all of the images of a layer on its canvas, and stores the images in
        # the proper index of tile_images so they can be removed from the grid when
        # replaced with another tile.
        def draw_layer(canvas_index, tile_codes):
            for row_index, room_row in enumerate(tile_codes):
                if row_index >= self.lvl_height * 8:
                    continue
                for tile_index, tile in enumerate(room_row):
                    if tile_index >= self.lvl_width * 10:
                        continue
                    tilecode = self.tile_palette_map[tile]
                    tile_name = tilecode[0].split(" ", 1)[0]
                    tile_image = tilecode[1]
                    x_offset, y_offset = self.texture_fetcher.adjust_texture_xy(
                        tile_image.width(),
                        tile_image.height(),
                        tile_name,
                        self.custom_editor_zoom_level,
                    )
                    self.custom_editor_canvas.replace_tile_at(
                        canvas_index,
                        row_index,
                        tile_index,
                        tile_image,
                        x_offset,
                        y_offset,
                    )

        for index, tileset in enumerate([
            self.custom_editor_foreground_tile_codes,
            self.custom_editor_background_tile_codes,
        ]):
            draw_layer(index, tileset)

    def set_current_save_format(self, save_format):
        self.current_save_format = save_format

    # Look through the level templates and try to find one that matches an existing save
    # format.
    def read_save_format(self, level):
        if self.modlunky_config.custom_level_editor_default_save_format is None:
            raise TypeError("custom_level_editor_default_save_format shouldn't be None")

        valid_save_formats = (
            [self.modlunky_config.custom_level_editor_default_save_format]
            + self.modlunky_config.custom_level_editor_custom_save_formats
            + self.base_save_formats
        )
        for save_format in valid_save_formats:
            for template in level.level_templates.all():
                if template.name == save_format.room_template_format.format(y=0, x=0):
                    return save_format

    # Read the comment of the template at room (0, 0) to extract the theme, defaulting to dwelling.
    def read_theme(self, level, save_format):
        for template in level.level_templates.all():
            if template.name == save_format.room_template_format.format(y=0, x=0):
                return template.comment
        return None

    # Selects a new theme, updating the grid to theme tiles and backgrounds for the
    # new theme.
    def select_theme(self, theme):
        if theme == self.lvl_biome:
            return
        self.lvl_biome = theme

        # Retexture all of the tiles in use
        for tilecode_item in self.tile_palette_ref_in_use:
            tile_name = tilecode_item[0].split(" ", 2)[0]
            img = self.texture_fetcher.get_texture(
                tile_name, theme, self.lvl, self.custom_editor_zoom_level
            )
            tilecode_item[1] = ImageTk.PhotoImage(img)

        # Load suggested tiles for the new theme.
        self.tile_palette_suggestions = suggested_tiles_for_theme(theme)
        # Redraw the tilecode palette with the new textures of tiles and the new suggestions.
        self.populate_tilecode_palette(self.palette_panel_custom)
        # Draw the grid now that we have the newly textured tiles.
        self.draw_custom_level_canvases(theme)

        self.changes_made()

    # Shows an error dialog when attempting to open a level using an unrecognized template format.
    def show_format_error_dialog(self, lvl, level_info):
        def on_create(save_format):
            self.options_panel.add_save_format(save_format)

            # When a new format is created, try reading the level file again.
            self.read_custom_lvl_file(lvl)

        SaveFormats.show_setroom_create_dialog(
            self.modlunky_config,
            "Couldn't find room templates",
            "Create a new room template format to load this level file?\n{x} and {y} are the coordinates of the room.\n",
            "Continue",
            on_create,
            self.get_suggested_saveroom_format(level_info),
        )

    def get_suggested_saveroom_format(self, level_info):
        template_regex = (
            "^"
            + r"(?P<begin>[^0-9]*)" + r"(?P<y>\d+)" + r"(?P<mid>[^0-9]*)" + r"(?P<x>\d+)" + r"(?P<end>[^0-9]*)"
            + "$"
        )
        logger.info(template_regex)
        for template in level_info.level_templates.all():
            match = re.search(template_regex, template.name)
            logger.info(template.name)
            if match is not None:
                logger.info("MATCHED")
                begin = match.group("begin")
                mid = match.group("mid")
                ending = match.group("end")
                return begin + "{y}" + mid + "{x}" + ending

    # Updates the level size from the options menu.
    def update_custom_level_size(self, width, height):
        if width == self.lvl_width and height == self.lvl_height:
            return

        # If the new level size is creater than the current level size, fill in
        # the level tile matrix with default tiles to fill the new size.
        def fill_to_size_with_tile(tile_matrix, tile, width, height):
            fill_rows = list(
                map(
                    lambda row: row
                    + (
                        []
                        if (width * 10 <= len(row))
                        else [tile for _ in range(width * 10 - len(row))]
                    ),
                    tile_matrix,
                )
            )
            return fill_rows + (
                []
                if (height * 8 <= len(fill_rows))
                else [
                    [tile for _ in range(width * 10)]
                    for _ in range(height * 8 - len(fill_rows))
                ]
            )

        empty = None
        hard_floor = None
        # Try to find a tile code for the empty tile and the hard floor to use as the
        # default tile codes of the front and back layers, respectively.
        for tile_ref in self.tile_palette_ref_in_use:
            tile_name = str(tile_ref[0].split(" ", 2)[0])
            tile_code = str(tile_ref[0].split(" ", 2)[1])
            if tile_name == "empty":
                empty = tile_code
            elif tile_name == "floor_hard":
                hard_floor = tile_code

        # If we didn't find an "empty" tile code, create one and use it.
        if not empty:
            empty = self.add_tilecode(
                "empty",
                "100",
                "empty",
                self.palette_panel_custom,
                self.custom_editor_zoom_level,
            )[0].split(" ", 2)[1]
        # If we did not find a "hard_floor" tile code, create one and use it.
        if not hard_floor:
            hard_floor = self.add_tilecode(
                "hard_floor",
                "100",
                "empty",
                self.palette_panel_custom,
                self.custom_editor_zoom_level,
            )[0].split(" ", 2)[1]

        self.custom_editor_foreground_tile_codes = fill_to_size_with_tile(
            self.custom_editor_foreground_tile_codes, empty, width, height
        )
        self.custom_editor_background_tile_codes = fill_to_size_with_tile(
            self.custom_editor_background_tile_codes, hard_floor, width, height
        )
        self.lvl_width = width
        self.lvl_height = height
        self.changes_made()
        self.draw_custom_level_canvases(self.lvl_biome)

    def update_lvls_path(self, new_path):
        self.lvls_path = new_path
        if self.variables_tab:
            self.variables_tab.update_lvls_path(new_path)