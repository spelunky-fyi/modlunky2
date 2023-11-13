# pylint: disable=too-many-lines

from copy import deepcopy
import dataclasses
from functools import lru_cache
import datetime
import glob
import logging
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
from modlunky2.levels.level_chances import LevelChances
from modlunky2.levels.level_settings import LevelSetting, LevelSettings
from modlunky2.levels.level_templates import (
    Chunk,
    LevelTemplate,
    LevelTemplates,
    TemplateSetting,
)
from modlunky2.levels.monster_chances import MonsterChances
from modlunky2.levels.tile_codes import VALID_TILE_CODES, TileCode, TileCodes, ShortCode
from modlunky2.sprites import SpelunkySpriteFetcher
from modlunky2.ui.levels.custom_levels.options_panel import OptionsPanel
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.ui.levels.shared.biomes import Biomes, BIOME
from modlunky2.ui.levels.shared.level_canvas import LevelCanvas
from modlunky2.ui.levels.shared.multi_canvas_container import MultiCanvasContainer
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import BaseTemplate, Setroom
from modlunky2.ui.levels.shared.textures import TextureUtil
from modlunky2.ui.levels.vanilla_levels.dual_util import make_dual, remove_dual
from modlunky2.ui.levels.vanilla_levels.level_dependencies import LevelDependencies
from modlunky2.ui.levels.vanilla_levels.level_list_panel import LevelListPanel
from modlunky2.ui.levels.vanilla_levels.levels_tree import LevelsTree, LevelsTreeRoom, LevelsTreeTemplate
from modlunky2.ui.levels.vanilla_levels.rules.rules_tab import RulesTab
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
        # TODO: Get actual resolution
        self.screen_width = 1290
        self.screen_height = 720
        self.dual_mode = False
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
        self.cur_lvl_bg_path = None
        self.im_output = None
        self.lvl_bg = None
        self.lvl_bg_path = None
        self.lvl_bgbg = None
        self.lvl_bgbg_path = None
        self.lvl_width = None
        self.lvl_height = None
        self.rows = None
        self.cols = None
        self.tiles = None
        self.tiles_meta = None
        self.im_output_dual = None
        self.palette_panel = None
        self.palette_panel_custom = None
        self.options_panel = None
        self.tile_palette_ref_in_use = None
        self.tile_palette_map = {}
        self.tile_palette_suggestions = None
        self.lvl = None
        self.lvl_biome = None
        self.node = None
        self.sister_locations = None
        self.icon_add = None
        self.icon_folder = None
        self.loaded_pack = None
        self.last_selected_tab = None
        self.list_preview_tiles_ref = None
        self.full_size = None
        self.current_level_custom = None
        self.mag_full = None
        self.grid_lines_foreground = []
        self.grid_lines_background = []
        self.grid_rooms_foreground = []
        self.grid_rooms_background = []
        self.custom_editor_foreground_tile_images = None
        self.custom_editor_background_tile_images = None
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
        self.depend_order_label = None
        self.no_conflicts_label = None
        self.tree_depend = None
        self.vsb_depend = None
        self.button_resolve_variables = None
        self.dependencies = None
        self.mag = None
        self.canvas_grids = None
        self.scrollable_canvas_frame = None
        self.foreground_label = None
        self.background_label = None
        self.vbar = None
        self.hbar = None
        self.canvas = None
        self.canvas_dual = None
        self.button_hide_tree = None
        self.button_replace = None
        self.button_clear = None
        self.var_ignore = None
        self.var_flip = None
        self.var_only_flip = None
        self.var_dual = None
        self.var_rare = None
        self.var_hard = None
        self.var_liquid = None
        self.var_purge = None
        self.checkbox_ignore = None
        self.checkbox_flip = None
        self.checkbox_only_flip = None
        self.checkbox_rare = None
        self.checkbox_hard = None
        self.checkbox_liquid = None
        self.checkbox_purge = None
        self.checkbox_dual = None
        self.texture_images = None
        self.uni_tile_code_list = None
        self.tile_palette_ref = None
        self.draw_mode = None
        self.tile_images = None
        self.current_level_path_custom = None

        self.usable_codes = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        def open_editor():
            if os.path.isdir(self.extracts_path):
                self.lvls_path = self.extracts_path
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
        self.tiles = None
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
            lambda index, row, column, is_primary: self.canvas_click(
                self.custom_editor_canvas,
                index,
                self.custom_editor_zoom_level,
                row,
                column,
                is_primary,
                tile_codes_at(index),
            ),
            lambda index, row, column, is_primary: self.canvas_shiftclick(
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
        self.variables_tab = ttk.Frame(self.tab_control)

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

        # Variables Tab
        self.variables_tab.columnconfigure(0, weight=1)  # Column 1 = Everything Else
        self.variables_tab.rowconfigure(1, weight=1)  # Row 0 = List box / Label
        self.variables_tab.rowconfigure(2, minsize=100)  # Row 0 = List box / Label

        self.depend_order_label = ttk.Label(
            self.variables_tab, text="Conflicts will be shown here", font=("Arial", 15)
        )
        self.depend_order_label.grid(row=0, column=0, sticky="nwse")

        self.no_conflicts_label = ttk.Label(
            self.variables_tab, text="No conflicts detected!", font=("Arial", 15)
        )
        self.no_conflicts_label.grid(row=1, column=0, sticky="nwse")

        self.tree_depend = ttk.Treeview(
            self.variables_tab, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        # self.tree_depend.bind("<Double-1>", lambda e: self.on_double_click(self.tree))
        self.tree_depend.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_depend = ttk.Scrollbar(
            self.variables_tab, orient="vertical", command=self.tree_depend.yview
        )
        self.vsb_depend.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_depend.configure(yscrollcommand=self.vsb_depend.set)
        self.tree_depend["columns"] = ("1", "2", "3")
        self.tree_depend["show"] = "headings"
        self.tree_depend.column("1", width=100, anchor="w")
        self.tree_depend.column("2", width=10, anchor="w")
        self.tree_depend.column("3", width=100, anchor="w")
        self.tree_depend.heading("1", text="Tile Id")
        self.tree_depend.heading("2", text="Tilecode")
        self.tree_depend.heading("3", text="File")
        self.tree_depend.grid(row=1, column=0, sticky="nwse")
        self.vsb_depend.grid(row=1, column=0, sticky="nse")

        self.button_resolve_variables = ttk.Button(
            self.variables_tab, text="Resolve Conflicts", command=self.resolve_conflicts
        )
        self.button_resolve_variables.grid(row=2, column=0, sticky="nswe")

        self.button_resolve_variables.grid_remove()
        self.no_conflicts_label.grid_remove()

        self.dependencies = []
        self.dependencies.append(
            [
                "basecamp.lvl",
                "basecamp_garden.lvl",
                "basecamp_shortcut_discovered.lvl",
                "basecamp_shortcut_undiscovered.lvl",
                "basecamp_shortcut_unlocked.lvl",
                "basecamp_surface.lvl",
                "basecamp_tutorial.lvl",
                "basecamp_tv_room_locked.lvl",
                "basecamp_tv_room_unlocked.lvl",
            ]
        )
        self.dependencies.append(
            ["junglearea.lvl", "blackmarket.lvl", "beehive.lvl", "challenge_moon.lvl"]
        )  # 1
        self.dependencies.append(
            ["volcanoarea.lvl", "vladscastle.lvl", "challenge_moon.lvl"]
        )  # 2
        self.dependencies.append(
            ["tidepoolarea.lvl", "lake.lvl", "lakeoffire.lvl", "challenge_star.lvl"]
        )  # 3
        self.dependencies.append(
            ["templearea.lvl", "beehive.lvl", "challenge_star.lvl"]
        )  # 4
        self.dependencies.append(
            [
                "babylonarea.lvl",
                "babylonarea_1-1.lvl",
                "hallofushabti.lvl",
                "palaceofpleasure.lvl",
            ]
        )  # 5
        self.dependencies.append(["sunkencityarea.lvl", "challenge_sun.lvl"])  # 6
        self.dependencies.append(["ending.lvl", "ending_hard.lvl"])  # 7
        self.dependencies.append(
            ["challenge_moon.lvl", "junglearea.lvl", "volcanoarea.lvl"]
        )  # 8
        self.dependencies.append(
            ["challenge_star.lvl", "tidepoolarea.lvl", "templearea.lvl"]
        )  # 9
        self.dependencies.append(
            [
                "generic.lvl",
                "dwellingarea.lvl",
                "cavebossarea.lvl",
                "junglearea.lvl",
                "blackmarket.lvl",
                "beehive.lvl",
                "challenge_moon.lvl",
                "volcanoarea.lvl",
                "vladscastle.lvl",
                "challenge_moon.lvl",
                "olmecarea.lvl",
                "tidepoolarea.lvl",
                "lake.lvl",
                "lakeoffire.lvl",
                "challenge_star.lvl",
                "abzu.lvl",
                "templearea.lvl",
                "beehive.lvl",
                "challenge_star.lvl",
                "cityofgold.lvl",
                "duat.lvl",
                "icecavesarea.lvl",
                "babylonarea.lvl",
                "babylonarea_1-1.lvl",
                "hallofushabti.lvl",
                "palaceofpleasure.lvl",
                "tiamat.lvl",
                "sunkencityarea.lvl",
                "challenge_sun.lvl",
                "eggplantarea.lvl",
                "hundun.lvl",
                "ending.lvl",
                "ending_hard.lvl",
                "cosmicocean_babylon.lvl",
                "cosmicocean_dwelling.lvl",
                "cosmicocean_icecavesarea.lvl",
                "cosmicocean_jungle.lvl",
                "cosmicocean_sunkencity.lvl",
                "cosmicocean_temple.lvl",
                "cosmicocean_tidepool.lvl",
                "cosmicocean_volcano.lvl",
            ]
        )  # 10

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
        self.rows = (
            15  # default values, could be set to none and still work I think lol
        )
        self.cols = (
            15  # default values, could be set to none and still work I think lol
        )

        self.canvas_grids = tk.Canvas(  # this is the main level editor grid
            self.editor_tab,
            bg="#292929",
        )
        self.canvas_grids.grid(row=0, column=1, rowspan=4, columnspan=8, sticky="nwse")

        self.canvas_grids.columnconfigure(2, weight=1)
        self.canvas_grids.rowconfigure(0, weight=1)

        self.scrollable_canvas_frame = tk.Frame(self.canvas_grids, bg="#343434")

        # offsets the screen so user can freely scroll around work area
        self.scrollable_canvas_frame.columnconfigure(
            0, minsize=int(int(self.screen_width) / 2)
        )
        self.scrollable_canvas_frame.columnconfigure(1, weight=1)
        self.scrollable_canvas_frame.columnconfigure(2, minsize=50)
        self.scrollable_canvas_frame.columnconfigure(
            4, minsize=int(int(self.screen_width) / 2)
        )
        self.scrollable_canvas_frame.rowconfigure(
            0, minsize=int(int(self.screen_height) / 2)
        )
        self.scrollable_canvas_frame.rowconfigure(1, weight=1)
        self.scrollable_canvas_frame.rowconfigure(2, minsize=100)
        self.scrollable_canvas_frame.rowconfigure(2, minsize=100)
        self.scrollable_canvas_frame.rowconfigure(
            4, minsize=int(int(self.screen_height) / 2)
        )

        self.scrollable_canvas_frame.grid(row=0, column=0, sticky="nwes")

        self.foreground_label = tk.Label(
            self.scrollable_canvas_frame,
            text="Foreground Area",
            fg="white",
            bg="#343434",
        )
        self.foreground_label.grid(row=2, column=1, sticky="nwse")
        self.foreground_label.grid_remove()

        self.background_label = tk.Label(
            self.scrollable_canvas_frame,
            text="Background Area",
            fg="white",
            bg="#343434",
        )
        self.background_label.grid(row=2, column=3, sticky="nwse")
        self.background_label.grid_remove()

        self.vbar = ttk.Scrollbar(
            self.editor_tab, orient="vertical", command=self.canvas_grids.yview
        )
        self.vbar.grid(row=0, column=2, rowspan=4, columnspan=7, sticky="nse")
        self.hbar = ttk.Scrollbar(
            self.editor_tab, orient="horizontal", command=self.canvas_grids.xview
        )
        self.hbar.grid(row=0, column=1, rowspan=4, columnspan=8, sticky="wes")

        self.canvas_grids.config(
            xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set
        )
        x_origin = self.canvas_grids.winfo_screenwidth() / 2
        y_origin = self.canvas_grids.winfo_screenheight() / 2
        self.canvas_grids.create_window(
            (x_origin, y_origin), window=self.scrollable_canvas_frame, anchor="center"
        )
        self.canvas_grids.bind(
            "<Enter>",
            lambda event: self._bind_to_mousewheel(
                event, self.hbar, self.vbar, self.canvas_grids
            ),
        )
        self.canvas_grids.bind(
            "<Leave>",
            lambda event: self._unbind_from_mousewheel(event, self.canvas_grids),
        )
        self.scrollable_canvas_frame.bind(
            "<Configure>",
            lambda e: self.canvas_grids.configure(
                scrollregion=self.canvas_grids.bbox("all")
            ),
        )

        self.canvas = tk.Canvas(  # this is the main level editor grid
            self.scrollable_canvas_frame,
            bg="#343434",
        )
        self.canvas.grid(row=1, column=1)
        self.canvas.grid_remove()
        self.canvas_dual = tk.Canvas(  # this is for dual level, it shows the back area
            self.scrollable_canvas_frame,
            width=0,
            bg="yellow",
        )
        self.canvas_dual.grid(row=1, column=3, padx=(0, 50))
        self.canvas_dual.grid_remove()  # hides it for now
        self.dual_mode = False

        self.button_hide_tree = ttk.Button(
            self.canvas_grids, text="<<", command=self.toggle_list_hide
        )
        self.button_hide_tree.grid(row=0, column=0, sticky="nw")

        self.button_replace = ttk.Button(
            self.canvas_grids, text="Replace", command=self.replace_tiles_dia
        )
        self.button_replace.grid(row=0, column=1, sticky="nw")
        self.button_replace["state"] = tk.DISABLED

        self.button_clear = ttk.Button(
            self.canvas_grids, text="Clear Canvas", command=self.clear_canvas
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

        self.var_ignore = tk.IntVar()
        self.var_flip = tk.IntVar()
        self.var_only_flip = tk.IntVar()
        self.var_dual = tk.IntVar()
        self.var_rare = tk.IntVar()
        self.var_hard = tk.IntVar()
        self.var_liquid = tk.IntVar()
        self.var_purge = tk.IntVar()
        self.checkbox_ignore = ttk.Checkbutton(
            self.editor_tab,
            text="Ignore",
            var=self.var_ignore,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_flip = ttk.Checkbutton(
            self.editor_tab,
            text="Flip",
            var=self.var_flip,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_only_flip = ttk.Checkbutton(
            self.editor_tab,
            text="Only Flip",
            var=self.var_only_flip,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_rare = ttk.Checkbutton(
            self.editor_tab,
            text="Rare",
            var=self.var_rare,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_hard = ttk.Checkbutton(
            self.editor_tab,
            text="Hard",
            var=self.var_hard,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_liquid = ttk.Checkbutton(
            self.editor_tab,
            text="Optimize Liquids",
            var=self.var_liquid,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_purge = ttk.Checkbutton(
            self.editor_tab,
            text="Purge",
            var=self.var_purge,
            onvalue=1,
            offvalue=0,
            command=self.remember_changes,
        )
        self.checkbox_dual = ttk.Checkbutton(
            self.editor_tab,
            text="Dual",
            var=self.var_dual,
            onvalue=1,
            offvalue=0,
            command=self.dual_toggle,
        )
        self.checkbox_dual.grid(row=4, column=1, sticky="w")
        self.checkbox_ignore.grid(row=4, column=2, sticky="w")
        self.checkbox_purge.grid(row=4, column=3, sticky="w")
        self.checkbox_rare.grid(row=4, column=4, sticky="w")
        self.checkbox_hard.grid(row=4, column=5, sticky="w")
        self.checkbox_flip.grid(row=4, column=6, sticky="w")
        self.checkbox_only_flip.grid(row=4, column=7, sticky="w")
        self.checkbox_liquid.grid(row=4, column=8, sticky="w")

        # the tilecodes are in the same order as the tiles in the image(50x50, left to right)
        self.texture_images = []

        self.uni_tile_code_list = []
        self.tile_palette_ref = []

        self.draw_mode = []  # slight adjustments of textures for tile preview
        # 1 = lower half tile
        # 2 = draw from bottom left
        # 3 = center
        # 4 = center to the right
        # 5 = draw bottom left + raise 1 tile
        # 6 = position doors
        # 7 = draw bottom left + raise half tile
        # 8 = draw bottom left + lower 1 tile.
        # 9 = draw bottom left + raise 1 tile + move left 1.5 tiles
        # 10 = draw bottom left + raise 2 tiles
        # 11 = move left 1 tile
        # 12 = raise 1 tile
        # 13 = draw from bottom left + move left half tile
        # 14 = precise bottom left for yama
        # 15 = draw bottom left + raise 1 tile + move left 1 tile.
        # 16 = move left half a tile.
        # 17 = center + move down half a tile.
        # 18 = draw bottom left + lower 1.5 tiles + move left 1.5 tiles.
        self.draw_mode.append(["anubis", 7])
        self.draw_mode.append(["olmec", 15])
        self.draw_mode.append(["alienqueen", 7])
        self.draw_mode.append(["kingu", 18])
        self.draw_mode.append(["coffin", 2])
        self.draw_mode.append(["dog_sign", 2])
        self.draw_mode.append(["bunkbed", 2])
        self.draw_mode.append(["telescope", 2])
        self.draw_mode.append(["palace_table", 11])
        self.draw_mode.append(["palace_chandelier", 11])
        self.draw_mode.append(["moai_statue", 9])
        self.draw_mode.append(["mother_statue", 10])
        self.draw_mode.append(["empress_grave", 2])
        self.draw_mode.append(["empty_mech", 2])
        self.draw_mode.append(["olmecship", 7])
        self.draw_mode.append(["lavamander", 2])
        self.draw_mode.append(["mummy", 2])
        self.draw_mode.append(["yama", 2])
        self.draw_mode.append(["crown_statue", 7])
        self.draw_mode.append(["lamassu", 2])
        self.draw_mode.append(["madametusk", 2])
        self.draw_mode.append(["giant_frog", 17])
        self.draw_mode.append(["door", 13])
        self.draw_mode.append(["starting_exit", 13])
        self.draw_mode.append(["eggplant_door", 13])
        self.draw_mode.append(["door2", 6])
        self.draw_mode.append(["door_drop_held", 6])
        self.draw_mode.append(["palace_entrance", 6])
        self.draw_mode.append(["door2_secret", 6])
        self.draw_mode.append(["ghist_door2", 6])
        self.draw_mode.append(["ghist_door", 2])
        self.draw_mode.append(["minister", 2])
        self.draw_mode.append(["storage_guy", 2])
        self.draw_mode.append(["idol", 4])
        self.draw_mode.append(["idol_held", 4])
        self.draw_mode.append(["ankh", 4])
        self.draw_mode.append(["fountain_head", 13])
        self.draw_mode.append(["yama", 14])
        self.draw_mode.append(["plasma_cannon", 4])
        self.draw_mode.append(["lockedchest", 4])
        self.draw_mode.append(["shopkeeper_vat", 12])
        self.draw_mode.append(["totem_trap", 2])
        self.draw_mode.append(["lion_trap", 2])
        self.draw_mode.append(["vlad", 4])
        self.draw_mode.append(["yeti_queen", 2])
        self.draw_mode.append(["yeti_king", 2])
        self.draw_mode.append(["crabman", 2])
        self.draw_mode.append(["giant_fly", 2])
        self.draw_mode.append(["ammit", 16])
        self.draw_mode.append(["humphead", 13])

        def canvas_click(
            event, canvas, is_primary, palette_panel
        ):  # when the level editor grid is clicked
            # Get rectangle diameters
            col_width = self.mag
            row_height = self.mag
            col = 0
            row = 0
            if canvas == self.canvas_dual:
                col = ((event.x + int(self.canvas["width"])) + col_width) // col_width
                row = event.y // row_height

                if (
                    col * self.mag < int(self.canvas["width"]) + self.mag
                    or col * self.mag > int(self.canvas["width"]) * 2 + self.mag
                ):
                    logger.debug("col out of bounds")
                    return

                if row * self.mag < 0 or row * self.mag > int(self.canvas["height"]):
                    logger.debug("row out of bounds")
                    return
            else:
                # Calculate column and row number
                col = event.x // col_width
                row = event.y // row_height

                if col * self.mag < 0 or col * self.mag > int(self.canvas["width"]):
                    logger.debug("col out of bounds")
                    return

                if row * self.mag < 0 or row * self.mag > int(self.canvas["height"]):
                    logger.debug("row out of bounds")
                    return
            # If the tile is not filled, create a rectangle
            if self.dual_mode:
                if int(col) == int((len(self.tiles[0]) - 1) / 2):
                    logger.debug("Middle of dual detected; not tile placed")
                    return

            tile_name, tile_code = palette_panel.selected_tile(is_primary)
            # tile_name = tile_label["text"].split(" ", 4)[2]
            # tile_code = tile_label["text"].split(" ", 4)[3]
            x_coord_offset, y_coord_offset = self.offset_for_tile(
                tile_name, tile_code, self.mag
            )

            canvas.delete(self.tiles[int(row)][int(col)])
            if canvas == self.canvas_dual:
                x2_coord = int(int(col) - ((len(self.tiles[0]) - 1) / 2) - 1)
                self.tiles[int(row)][int(col)] = canvas.create_image(
                    x2_coord * self.mag - x_coord_offset,
                    int(row) * self.mag - y_coord_offset,
                    image=self.tile_palette_map[tile_code][1],
                    anchor="nw",
                )
            else:
                self.tiles[int(row)][int(col)] = canvas.create_image(
                    int(col) * self.mag - x_coord_offset,
                    int(row) * self.mag - y_coord_offset,
                    image=self.tile_palette_map[tile_code][1],
                    anchor="nw",
                )
            self.tiles_meta[row][col] = tile_code
            logger.debug(
                "%s replaced with %s",
                self.tiles_meta[row][col],
                tile_code,
            )
            self.remember_changes()  # remember changes made

        self.canvas.bind(
            "<Button-1>",
            lambda event: canvas_click(event, self.canvas, True, self.palette_panel),
        )
        self.canvas.bind(
            "<B1-Motion>",
            lambda event: canvas_click(event, self.canvas, True, self.palette_panel),
        )  # These second binds are so the user can hold down their mouse button when painting tiles
        self.canvas.bind(
            "<Button-3>",
            lambda event: canvas_click(event, self.canvas, False, self.palette_panel),
        )
        self.canvas.bind(
            "<B3-Motion>",
            lambda event: canvas_click(event, self.canvas, False, self.palette_panel),
        )  # These second binds are so the user can hold down their mouse button when painting tiles
        # self.canvas.bind("<Key>", lambda event: )
        self.canvas_dual.bind(
            "<Button-1>",
            lambda event: canvas_click(event, self.canvas_dual, True, self.palette_panel),
        )
        self.canvas_dual.bind(
            "<B1-Motion>",
            lambda event: canvas_click(event, self.canvas_dual, True, self.palette_panel),
        )
        self.canvas_dual.bind(
            "<Button-3>",
            lambda event: canvas_click(
                event,
                self.canvas_dual,
                False,
                self.palette_panel,
            ),
        )
        self.canvas_dual.bind(
            "<B3-Motion>",
            lambda event: canvas_click(
                event,
                self.canvas_dual,
                False,
                self.palette_panel,
            ),
        )
        self.tree_files.bind(
            "<ButtonRelease-1>",
            lambda event: self.tree_filesitemclick(
                event, self.tree_files, EditorType.VANILLA_ROOMS
            ),
        )

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile_name, tile_code, tile_size):
        for tile_name_ref in self.draw_mode:
            if tile_name != str(tile_name_ref[0]):
                continue
            logger.debug("Applying custom anchor for %s", tile_name)
            tile_ref = self.tile_palette_map[tile_code]
            if tile_ref:
                logger.debug("Found %s", tile_ref[0])
                img = tile_ref[1]
                return TextureUtil.adjust_texture_xy(
                    img.width(), img.height(), int(tile_name_ref[1]), tile_size
                )

        return 0, 0

    # Click event on a canvas for either left or right click to replace the tile at the cursor's position with
    # the selected tile.
    def canvas_click(
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

    def canvas_shiftclick(self, row, column, is_primary, tile_code_matrix):
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
        self.canvas.delete("all")
        self.canvas_dual.delete("all")
        self.canvas.grid_remove()
        self.canvas_dual.grid_remove()

    def reset(self):
        logger.debug("Resetting..")
        self.level_list_panel.reset()
        try:
            for palette_panel in [self.palette_panel, self.palette_panel_custom]:
                palette_panel.reset()
            self.options_panel.disable_controls()
            self.show_intro()
            self.show_intro_full()
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()
            self.tile_palette_map = {}
            self.tile_palette_ref_in_use = None
            self.tile_palette_suggestions = None
            self.lvl = None
            self.lvl_biome = None
            self.custom_editor_foreground_tile_images = None
            self.custom_editor_background_tile_images = None
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
        self.lvls_path = Path(lvl_dir)
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
        self.lvls_path = Path(lvl_dir)
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
        win = PopupWindow("Create Level", self.modlunky_config)

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
        width_combobox["values"] = [1, 2, 3, 4, 5, 6, 7, 8]

        values_row = values_row + 1

        tk.Label(values_frame, text="Height: ").grid(
            row=values_row, column=0, sticky="ne", pady=2
        )

        height_combobox = ttk.Combobox(values_frame, value=4, height=25)
        height_combobox.set(4)
        height_combobox.grid(row=values_row, column=1, sticky="nswe", pady=2)
        height_combobox["state"] = "readonly"
        height_combobox["values"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

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
            self.base_save_formats
            + self.modlunky_config.custom_level_editor_custom_save_formats
        )
        save_format_combobox["values"] = list(
            map(lambda format: format.name, save_formats)
        )
        create_save_format = (
            self.current_save_format
            or self.modlunky_config.custom_level_editor_default_save_format
        )
        if not create_save_format:
            create_save_format = self.base_save_formats[0]
        if create_save_format:
            save_format_combobox.set(create_save_format.name)

        warning_label = tk.Label(
            win, text="", foreground="red", wraplength=200, justify=tk.LEFT
        )
        warning_label.grid(row=row, column=0, sticky="nw", pady=(10, 0))
        warning_label.grid_remove()
        row = row + 1

        def create_level():
            theme = self.theme_for_name(theme_combobox.get())
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
                lvl_path = Path(self.lvls_path) / lvl_file_name
                if lvl_path.exists():
                    warning_label[
                        "text"
                    ] = "Error: Level {level} already exists!".format(
                        level=lvl_file_name
                    )
                    warning_label.grid()
                    return
                tiles = [
                    ["floor 1"],
                    ["empty 0"],
                    ["floor_hard X"],
                ]
                # Fill in the level with empty tiles in the foreground and hard floor in the background.
                foreground = [
                    ["0" for _ in range(width * 10)] for _ in range(height * 8)
                ]
                background = [
                    ["X" for _ in range(width * 10)] for _ in range(height * 8)
                ]
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
                saved = self.save_level(
                    lvl_path,
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
                    # Reload the file list tree so that the new file shows up, and select it.
                    self.load_pack_custom_lvls(tree, self.lvls_path, lvl_file_name)
                    # Load the newly created file into the editor.
                    self.read_custom_lvl_file(lvl_file_name)
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

    def _on_mousewheel(self, event, hbar, vbar, canvas):
        scroll_dir = None
        if event.num == 5 or event.delta == -120:
            scroll_dir = 1
        elif event.num == 4 or event.delta == 120:
            scroll_dir = -1

        if scroll_dir is None:
            return

        if event.state & (1 << 0):  # Shift / Horizontal Scroll
            self._scroll_horizontal(scroll_dir, hbar, canvas)
        else:
            self._scroll_vertical(scroll_dir, vbar, canvas)

    def _scroll_vertical(self, scroll_dir, scrollbar, canvas):
        # If the scrollbar is max size don't bother scrolling
        if scrollbar.get() == (0.0, 1.0):
            return

        canvas.yview_scroll(scroll_dir, "units")

    def _scroll_horizontal(self, scroll_dir, scrollbar, canvas):
        # If the scrollbar is max size don't bother scrolling
        if scrollbar.get() == (0.0, 1.0):
            return

        canvas.xview_scroll(scroll_dir, "units")

    def _bind_to_mousewheel(self, _event, hbar, vbar, canvas):
        if is_windows():
            canvas.bind_all(
                "<MouseWheel>",
                lambda event: self._on_mousewheel(event, hbar, vbar, canvas),
            )
        else:
            canvas.bind_all(
                "<Button-4>",
                lambda event: self._on_mousewheel(event, hbar, vbar, canvas),
            )
            canvas.bind_all(
                "<Button-5>",
                lambda event: self._on_mousewheel(event, hbar, vbar, canvas),
            )

    def _unbind_from_mousewheel(self, _event, canvas):
        if is_windows():
            canvas.unbind_all("<MouseWheel>")
        else:
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

    def log_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        logger.debug("%s codes left (%s)", len(self.usable_codes), codes)

    def dual_toggle(self):
        current_room = self.level_list_panel.get_selected_room()

        if current_room:
            new_room_data = current_room.rows

            if self.var_dual.get() == 1:  # converts room into dual
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

    def make_backup(self, file):
        logger.debug("Making backup..")
        loaded_pack = self.tree_files.heading("#0")["text"].split("/")[0]
        backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
        if os.path.isfile(file):
            lvl_name = (
                os.path.basename(file)
                + "_"
                + ("{date:%Y-%m-%d_%H_%M_%S}").format(date=datetime.datetime.now())
            )
            if not os.path.exists(Path(backup_dir)):
                os.makedirs(Path(backup_dir))
            copyfile(file, backup_dir + "/" + lvl_name)
            logger.debug("Backup made!")

            # Removes oldest backup every 50 backups
            _, _, files = next(os.walk(backup_dir))
            file_count = len(files)
            logger.debug("This mod has %s backups.", file_count)
            list_of_files = os.listdir(backup_dir)
            full_path = [backup_dir + f"/{x}" for x in list_of_files]
            if len(list_of_files) >= 50:
                logger.debug("Deleting oldest backup")
                oldest_file = min(full_path, key=os.path.getctime)
                os.remove(oldest_file)
        else:
            logger.debug("Backup not needed for what was a default file.")

    class VanillaSetroomType(Enum):
        NONE = "none"
        FRONT = "front"
        BACK = "back"
        DUAL = "dual"

    def vanilla_setroom_type_for(self, theme, x, y):
        if theme == "ice":
            if y in [4, 5, 6, 7] and x in [0, 1, 2]:
                return LevelsTab.VanillaSetroomType.DUAL
            elif y in [10, 11, 12, 13] and x in [0, 1, 2]:
                return LevelsTab.VanillaSetroomType.BACK
        elif theme == "tiamat":
            if y == 0 and x in [0, 1, 2]:
                return LevelsTab.VanillaSetroomType.DUAL
            elif y in range(2, 10 + 1) and x in [0, 1, 2]:
                return LevelsTab.VanillaSetroomType.FRONT
        elif theme == "duat":
            if y in [0, 1, 2, 3] and x in [0, 1, 2]:
                return LevelsTab.VanillaSetroomType.FRONT
        elif theme == "eggplant":
            if y in [0, 1] and x in [0, 1, 2, 3]:
                return LevelsTab.VanillaSetroomType.FRONT
        elif theme == "olmec":
            if (y in [0, 1, 6, 7] and x in [0, 1, 2, 3, 4]) or (
                y in [2, 3, 4, 5] and x in [1, 2, 3]
            ):
                return LevelsTab.VanillaSetroomType.DUAL
            elif (y in [2, 3, 4, 5] and x in [0, 4]) or (
                y == 7 and x in [0, 1, 2, 3, 4]
            ):
                return LevelsTab.VanillaSetroomType.FRONT
        elif theme == "hundun":
            if y in [0, 1, 2, 10, 11] and x in [0, 1, 2]:
                return LevelsTab.VanillaSetroomType.FRONT
        elif theme == "abzu":
            if y in [0, 1, 2, 3] and x in [0, 1, 2, 3]:
                return LevelsTab.VanillaSetroomType.DUAL
            elif y in [4, 5, 6, 7, 8] and x in [0, 1, 2, 3]:
                return LevelsTab.VanillaSetroomType.FRONT

        return LevelsTab.VanillaSetroomType.NONE

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
        self.save_level(
            self.current_level_path_custom,
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
        )

    def save_level(
        self,
        level_path,
        width,
        height,
        theme,
        save_format,
        comment,
        level_chances,
        level_settings,
        monster_chances,
        used_tiles,
        foreground_tiles,
        background_tiles,
    ):
        try:
            tile_codes = TileCodes()
            level_templates = LevelTemplates()

            hard_floor_code = None
            air_code = "0"
            for tilecode in used_tiles:
                tile_codes.set_obj(
                    TileCode(
                        name=tilecode[0].split(" ", 1)[0],
                        value=tilecode[0].split(" ", 1)[1],
                        comment="",
                    )
                )
                if tilecode[0].split(" ", 1)[0] == "floor_hard":
                    hard_floor_code = tilecode[0].split(" ", 1)[1]
                elif tilecode[0].split(" ", 1)[0] == "empty":
                    air_code = tilecode[0].split(" ", 1)[1]

            def write_vanilla_room(
                x,
                y,
                foreground,
                background,
                save_format,
                level_templates,
                hard_floor_code,
            ):
                if not save_format.include_vanilla_setrooms:
                    return
                vanilla_setroom_type = self.vanilla_setroom_type_for(theme, x, y)
                if vanilla_setroom_type == LevelsTab.VanillaSetroomType.NONE:
                    return
                vf = []
                vb = []
                vs = []
                vm = ""
                dual = (not hard_floor_code) or background != [
                    hard_floor_code * 10 for _ in range(8)
                ]
                if vanilla_setroom_type == LevelsTab.VanillaSetroomType.FRONT:
                    vf = foreground
                    vm = "the front layer"
                elif vanilla_setroom_type == LevelsTab.VanillaSetroomType.BACK:
                    vf = background
                    vm = "the back layer"
                elif vanilla_setroom_type == LevelsTab.VanillaSetroomType.DUAL:
                    vf = foreground
                    vm = "both layers"
                    if dual:
                        vb = background
                        vs.append(TemplateSetting.DUAL)

                template_chunks = [
                    Chunk(
                        comment=None,
                        settings=vs,
                        foreground=vf,
                        background=vb,
                    )
                ]
                template_name = save_format.room_template_format.format(y=y, x=x)
                comment = f"Auto-generated template to match {vm} of {template_name}."
                level_templates.set_obj(
                    LevelTemplate(
                        name=f"setroom{room_y}-{room_x}",
                        comment=comment,
                        chunks=template_chunks,
                    )
                )

            for room_y in range(height):
                for room_x in range(width):
                    room_foreground = []
                    room_background = []
                    for row in range(8):
                        foreground_row = foreground_tiles[room_y * 8 + row]
                        background_row = background_tiles[room_y * 8 + row]
                        room_foreground.append(
                            "".join(foreground_row[room_x * 10 : room_x * 10 + 10])
                        )
                        room_background.append(
                            "".join(background_row[room_x * 10 : room_x * 10 + 10])
                        )

                    room_settings = []
                    dual = (not hard_floor_code) or room_background != [
                        hard_floor_code * 10 for _ in range(8)
                    ]
                    if dual:
                        room_settings.append(TemplateSetting.DUAL)
                    template_chunks = [
                        Chunk(
                            comment=None,
                            settings=room_settings,
                            foreground=room_foreground,
                            background=room_background if dual else [],
                        )
                    ]
                    template_name = save_format.room_template_format.format(
                        y=room_y, x=room_x
                    )
                    level_templates.set_obj(
                        LevelTemplate(
                            name=template_name,
                            comment=theme,
                            chunks=template_chunks,
                        )
                    )
                    write_vanilla_room(
                        room_x,
                        room_y,
                        room_foreground,
                        room_background,
                        save_format,
                        level_templates,
                        hard_floor_code,
                    )

            # Write vanilla setrooms for any room that the game expects a setroom for, but does not
            # exist in the current size of the level.
            for room_y in range(15):
                for room_x in range(8):
                    # If the room has already been handled, just continue to the next room.
                    if room_y < height and room_x < width:
                        continue
                    room_foreground = [air_code * 10] * 8
                    room_background = [(hard_floor_code or "X") * 10] * 8
                    write_vanilla_room(
                        room_x,
                        room_y,
                        room_foreground,
                        room_background,
                        save_format,
                        level_templates,
                        hard_floor_code,
                    )

            level_settings.set_obj(
                LevelSetting(
                    name="size",
                    value="{width} {height}".format(width=width, height=height),
                    comment=None,
                )
            )
            level_file = LevelFile(
                comment,
                level_settings,
                tile_codes,
                level_chances,
                monster_chances,
                level_templates,
            )

            if not os.path.exists(Path(self.lvls_path)):
                os.makedirs(Path(self.lvls_path))
            save_path = level_path
            self.make_backup(save_path)
            logger.debug("Saving to %s", save_path)

            with Path(save_path).open("w", encoding="cp1252") as handle:
                level_file.write(handle)

            logger.debug("Saved!")

            self.save_needed = False
            self.button_save_custom["state"] = tk.DISABLED
            logger.debug("Saved")
            for item in self.tree_files_custom.selection():
                self.tree_files_custom.item(item, image=self.lvl_icon(LevelType.MODDED))
            return True
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed to save level: %s", tb_info())
            _msg_box = tk.messagebox.showerror(
                "Oops?",
                "Error saving..",
            )
            return False

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
                self.make_backup(save_path)
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
        else:
            logger.debug("No changes to save")

    def resolve_conflicts(self):
        if self.save_needed:
            msg_box = tk.messagebox.askquestion(
                "Save now?",
                "This will save all your current changes. Continue?",
                icon="warning",
            )
            if msg_box == "no":
                return
            else:
                self.save_changes()

        def get_level(file):
            if os.path.exists(Path(self.lvls_path / file)):
                levelp = LevelFile.from_path(Path(self.lvls_path / file))
            else:
                levelp = LevelFile.from_path(Path(self.extracts_path) / file)
            return levelp

        usable_codes = ShortCode.usable_codes()

        # finds tilecodes that are taken in all the dependacy files
        for level in self.sister_locations:
            used_codes = level[1].tile_codes.all()
            for code in used_codes:
                for usable_code in usable_codes:
                    if str(code.value) == str(usable_code):
                        usable_codes.remove(usable_code)
                        # "sister location" = nick name for lvl files in a dependency group
                        logger.debug("removed %s from sister location", code.value)

        for i in self.tree_depend.get_children():  # gets base level conflict to compare
            try:
                item = self.tree_depend.item(
                    i, option="values"
                )  # gets it values ([0] = tile id [1] = tile code [2] = level file name)

                levels = []  # gets list of levels to fix tilecodes among
                # adds item as (level, item values)
                levels.append([get_level(item[2].split(" ")[0]), item])
                # removes item cause its already being worked on so it doesn't
                # get worked on or compared to again
                # self.tree_depend.delete(i)

                for child in self.tree_depend.get_children():
                    item2 = self.tree_depend.item(child, option="values")
                    # finds item with conflicting codes
                    if str(item2[1]) == str(item[1]):
                        levels.append([get_level(item2[2].split(" ")[0]), item2])
                        # removes item cause its already being worked on so it doesn't
                        # get worked on or compared to again
                        # self.tree_depend.delete(child)

                # finds tilecodes that are not available in all the dependacy files
                # (again cause it could have changed since tilecodes are being messed with)
                # might not actually be needed
                for level in levels:
                    used_codes = level[0].tile_codes.all()
                    for code in used_codes:
                        for usable_code in usable_codes:
                            if str(code.value) == str(usable_code):
                                usable_codes.remove(usable_code)
                                logger.debug(
                                    "removed %s cause its already in use", code.value
                                )

                # replaces all the old tile codes with the new ones in the rooms
                for level in levels:
                    # gives tilecodes their own loop
                    tilecode_count = 0
                    tile_codes_new = TileCodes()  # new tilecode database

                    for code in level[0].tile_codes.all():
                        tile_id = str(level[1][0])
                        old_code = str(level[1][1])
                        if str(code.name) == str(
                            tile_id
                        ):  # finds conflicting tilecode by id
                            # makes sure there's even codes left to assing new unique ones
                            if len(usable_codes) > 0:
                                # gets the next available usable code
                                new_code = str(usable_codes[0])
                                tile_codes_new.set_obj(
                                    TileCode(
                                        name=tile_id,
                                        value=new_code,
                                        comment="",
                                    )
                                )  # adds new tilecode to database with new code
                                old_code_found = False
                                for usable_code in usable_codes:
                                    if str(new_code) == str(usable_code):
                                        usable_codes.remove(usable_code)
                                        logger.debug("used and removed %s", new_code)
                                    if str(old_code) == str(usable_code):
                                        old_code_found = True
                                if not old_code_found:
                                    usable_codes.append(
                                        old_code
                                    )  # adds back replaced code since its now free for use again
                            else:
                                logger.warning("Not enough unique tilecodes left")
                                self.tree_filesitemclick(
                                    self, self.tree_files, EditorType.VANILLA_ROOMS
                                )
                                self.check_dependencies()
                                return
                        else:
                            tile_codes_new.set_obj(
                                TileCode(
                                    name=code.name,
                                    value=code.value,
                                    comment="",
                                )  # adds tilecode back to database
                            )
                        tilecode_count = tilecode_count + 1

                    for code in level[0].tile_codes.all():
                        tile_id = str(level[1][0])
                        old_code = str(level[1][1])
                        if str(code.name) == str(tile_id):  # finds conflicting tilecode
                            for new_code in tile_codes_new.all():
                                if new_code.name == code.name:
                                    template_count = 0
                                    for template in level[0].level_templates.all():
                                        new_chunks = []
                                        for room in template.chunks:
                                            row_count = 0
                                            for row in room.foreground:
                                                col_count = 0
                                                for col in row:
                                                    if str(col) == str(old_code):
                                                        room.foreground[row_count][
                                                            col_count
                                                        ] = str(new_code.value)
                                                        logger.debug(
                                                            "replaced %s with %s",
                                                            old_code,
                                                            new_code.value,
                                                        )
                                                    col_count = col_count + 1
                                                row_count = row_count + 1
                                            row_count = 0
                                            for row in room.background:
                                                col_count = 0
                                                for col in row:
                                                    if str(col) == str(old_code):
                                                        room.background[row_count][
                                                            col_count
                                                        ] = str(new_code.value)
                                                        logger.debug(
                                                            "replaced %s with %s",
                                                            old_code,
                                                            new_code.value,
                                                        )
                                                    col_count = col_count + 1
                                                row_count = row_count + 1
                                            new_chunks.append(
                                                Chunk(
                                                    comment=room.comment,
                                                    settings=room.settings,
                                                    foreground=room.foreground,
                                                    background=room.background,
                                                )
                                            )
                                        level[0].level_templates.all()[
                                            template_count
                                        ].chunks = new_chunks
                                        template_count = template_count + 1
                    level[0].tile_codes = tile_codes_new

                    path = Path(self.lvls_path / str(level[1][2].split(" ")[0]))
                    with Path(path).open("w", encoding="cp1252") as handle:
                        level[0].write(handle)
                        logger.debug("Fixed conflicts in %s", level[1][2].split(" ")[0])
            except Exception:  # pylint: disable=broad-except
                logger.critical("Error: %s", tb_info())
        self.tree_filesitemclick(self, self.tree_files, EditorType.VANILLA_ROOMS)
        self.check_dependencies()

    def check_dependencies(self):
        self.depend_order_label["text"] = ""
        for i in self.tree_depend.get_children():  # clears tree
            self.tree_depend.delete(i)
        logger.debug("checking dependencies..")
        levels = []

        def append_level(item):
            self.depend_order_label["text"] += " -> " + item
            if os.path.exists(Path(self.lvls_path / item)):
                levels.append(
                    [
                        item + " custom",
                        LevelFile.from_path(Path(self.lvls_path / item)),
                    ]
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    [
                        item + " extracts",
                        LevelFile.from_path(Path(self.extracts_path) / item),
                    ]
                )

        self.depend_order_label["text"] = ""
        if str(self.tree_files.item(self.last_selected_file, option="text")).startswith(
            "basecamp"
        ):
            for file in self.dependencies[0]:
                append_level(file)
        elif str(
            self.tree_files.item(self.last_selected_file, option="text")
        ).startswith("generic.lvl"):
            # for file in self.dependencies[10]:
            #    append_level(file)
            # removed for now
            self.depend_order_label.grid_remove()
            self.tree_depend.grid_remove()
            self.button_resolve_variables.grid_remove()
            self.no_conflicts_label.grid()
            return
        else:
            append_level("generic.lvl")  # adds generic for all other files
        if str(self.tree_files.item(self.last_selected_file, option="text")).startswith(
            "challenge_moon.lvl"
        ):
            for file in self.dependencies[8]:
                append_level(file)
        elif str(
            self.tree_files.item(self.last_selected_file, option="text")
        ).startswith("challenge_star.lvl"):
            for file in self.dependencies[9]:
                append_level(file)
        elif str(
            self.tree_files.item(self.last_selected_file, option="text")
        ).startswith("junglearea.lvl"):
            for file in self.dependencies[1]:
                append_level(file)
        elif str(
            self.tree_files.item(self.last_selected_file, option="text")
        ).startswith("volcanoarea.lvl"):
            for file in self.dependencies[2]:
                append_level(file)
        elif str(
            self.tree_files.item(self.last_selected_file, option="text")
        ).startswith("tidepoolarea.lvl"):
            for file in self.dependencies[3]:
                append_level(file)
        elif str(
            self.tree_files.item(self.last_selected_file, option="text")
        ).startswith("templearea.lvl"):
            for file in self.dependencies[4]:
                append_level(file)
        else:
            i = 0
            # each 'depend' = list of files that depend on each other
            for depend in self.dependencies:
                if i == 9:
                    break
                for file in depend:
                    # makes sure opened level file match 1 dependency entry
                    if str(
                        self.tree_files.item(self.last_selected_file, option="text")
                    ).startswith(file):
                        # makes sure this level isn't being tracked from the generic file
                        if depend != self.dependencies[10]:
                            logger.debug("checking dependencies of %s", file)
                            for item in depend:
                                append_level(item)
                            break
                i = i + 1
        level = None
        tilecode_compare = []
        for level in levels:
            logger.debug("getting tilecodes from %s", level[0])
            tilecodes = []
            tilecodes.append(str(level[0]) + " file")
            level_tilecodes = level[1].tile_codes.all()

            for tilecode in level_tilecodes:
                tilecodes.append(str(tilecode.name) + " " + str(tilecode.value))
            tilecode_compare.append(tilecodes)

        self.sister_locations = levels

        for lvl_tilecodes in tilecode_compare:  # for list of tilecodes in each lvl
            for tilecode in lvl_tilecodes:  # for each tilecode in the lvl
                # for list of tilecodes in each lvl to compare to
                for lvl_tilecodes_compare in tilecode_compare:
                    # makes sure it doesn't compare to itself
                    if lvl_tilecodes_compare[0] != lvl_tilecodes[0]:
                        # for each tilecode in the lvl being compared to
                        for tilecode_compare_to in lvl_tilecodes_compare:
                            # makes sure its not the header
                            if (
                                len(tilecode.split(" ")) != 3
                                and len(tilecode_compare_to.split(" ")) != 3
                            ):
                                # if tilecodes match
                                if str(tilecode.split(" ")[1]) == str(
                                    tilecode_compare_to.split(" ")[1]
                                ):
                                    # if tilecodes aren't assigned to same thing
                                    if str(tilecode.split(" ")[0]) != str(
                                        tilecode_compare_to.split(" ")[0]
                                    ):
                                        logger.debug(
                                            "tilecode conflict: %s",
                                            tilecode.split(" ")[1],
                                        )
                                        logger.debug(
                                            "in %s and %s",
                                            lvl_tilecodes[0],
                                            lvl_tilecodes_compare[0],
                                        )
                                        logger.debug(
                                            "comparing tileids %s to %s",
                                            tilecode.split(" ")[0],
                                            tilecode_compare_to.split(" ")[0],
                                        )
                                        compare_exists = False
                                        compare_to_exists = False
                                        # makes sure the detected conflicts are already listed
                                        for (
                                            tree_item
                                        ) in self.tree_depend.get_children():
                                            tree_item_check = self.tree_depend.item(
                                                tree_item, option="values"
                                            )
                                            if (
                                                tree_item_check[0]
                                                == str(tilecode.split(" ")[0])
                                                and tree_item_check[1]
                                                == str(tilecode.split(" ")[1])
                                                and tree_item_check[2]
                                                == str(lvl_tilecodes[0])
                                            ):
                                                compare_exists = True
                                            elif (
                                                tree_item_check[0]
                                                == str(
                                                    tilecode_compare_to.split(" ")[0]
                                                )
                                                and tree_item_check[1]
                                                == str(
                                                    tilecode_compare_to.split(" ")[1]
                                                )
                                                and tree_item_check[2]
                                                == str(lvl_tilecodes_compare[0])
                                            ):
                                                compare_to_exists = True
                                        if not compare_exists:
                                            self.tree_depend.insert(
                                                "",
                                                "end",
                                                text="L1",
                                                values=(
                                                    str(tilecode.split(" ")[0]),
                                                    str(tilecode.split(" ")[1]),
                                                    str(lvl_tilecodes[0]),
                                                ),
                                            )
                                        if not compare_to_exists:
                                            self.tree_depend.insert(
                                                "",
                                                "end",
                                                text="L1",
                                                values=(
                                                    str(
                                                        tilecode_compare_to.split(" ")[
                                                            0
                                                        ]
                                                    ),
                                                    str(
                                                        tilecode_compare_to.split(" ")[
                                                            1
                                                        ]
                                                    ),
                                                    str(lvl_tilecodes_compare[0]),
                                                ),
                                            )
        logger.debug("Done.")
        if len(self.tree_depend.get_children()) == 0:
            self.depend_order_label.grid_remove()
            self.tree_depend.grid_remove()
            self.button_resolve_variables.grid_remove()
            self.no_conflicts_label.grid()
        else:
            self.depend_order_label.grid()
            self.tree_depend.grid()
            self.button_resolve_variables.grid()
            self.no_conflicts_label.grid_remove()

    def remember_changes(self):  # remembers changes made to rooms
        current_room = self.level_list_panel.get_selected_room()
        if current_room:
            new_room_data = ""
            if int(self.var_dual.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!dual"
            if int(self.var_purge.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!purge"
            if int(self.var_flip.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!flip"
            if int(self.var_only_flip.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!onlyflip"
            if int(self.var_rare.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!rare"
            if int(self.var_hard.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!hard"
            if int(self.var_liquid.get()) == 1:
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!liquid"
            if int(self.var_ignore.get()) == 1:
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
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()

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
                        # self.canvas.delete(self.tiles[int(row_count)][int(col_count)])
                        # self.canvas_dual.delete(self.tiles[int(row_count)][int(col_count)])
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
                    self.canvas.delete(self.tiles[int(row_count)][int(col_count)])
                    self.canvas_dual.delete(self.tiles[int(row_count)][int(col_count)])
                    col_count = col_count + 1
                row_count = row_count + 1
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
            self.check_dependencies()

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
            self.check_dependencies()
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
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()
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

        self.mag_full = int(self.slider_zoom_full.get() / 2)
        self.full_level_preview_canvas.clear()
        self.full_level_preview_canvas.set_zoom(self.mag_full)

        self.full_size = None
        if len(self.tree_files.selection()) > 0:
            self.full_size = self.rules_tab.get_full_size()
            if self.full_size is not None:
                logger.debug("Size found: %s", self.full_size)
                level_height = int(self.full_size.split(", ")[1])
                level_width = int(self.full_size.split(", ")[0])
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
                                # for _palette_block in self.tile_palette_ref_in_use:
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
                                                (self.mag_full, self.mag_full),
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

                                # x_coord = 0
                                # y_coord = 0
                                # for tile_name_ref in self.draw_mode:
                                #     if tile_name == str(tile_name_ref[0]):
                                #         x_coord, y_coord = TextureUtil.adjust_texture_xy(
                                #             tile_image_full.width(),
                                #             tile_image_full.height(),
                                #             tile_name_ref[1],
                                #             self.mag_full,
                                #         )
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

    def _draw_grid(self, cols, rows, canvas, dual):
        # resizes canvas for grids
        canvas["width"] = (self.mag * cols) - 3
        canvas["height"] = (self.mag * rows) - 3

        if not dual:  # applies normal bg image settings to main grid
            self.cur_lvl_bg_path = (
                self.lvl_bg_path
            )  # store as a temp dif variable so it can switch back to the normal bg when needed

            file_id = self.tree_files.selection()[0]
            # checks which room is being opened to see if a special bg is needed
            selected_room_template_name = self.level_list_panel.get_selected_room_template_name()
            factor = 1.0  # keeps image the same
            if self.lvl_bg_path == self.textures_dir / "bg_ice.png" and str(
                selected_room_template_name
            ).startswith(
                "setroom1"
            ):  # mothership rooms are setroom10-1 to setroom13-2
                self.cur_lvl_bg_path = self.textures_dir / "bg_mothership.png"
            elif str(self.tree_files.item(file_id, option="text")).startswith(
                "blackmark"
            ):
                factor = 2.5  # brightens the image for black market
            elif (
                str(self.tree_files.item(file_id, option="text")).startswith("generic")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "cosmic"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith("duat")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "palace"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "ending_hard"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_m"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_st"
                )
            ):
                factor = 0  # darkens the image for cosmic ocean and duat and others

            image = Image.open(self.cur_lvl_bg_path).convert("RGBA")
            image = image.resize(
                (int(canvas["width"]), int(canvas["height"])), Image.BILINEAR
            )  ## The (250, 250) is (height, width)
            enhancer = ImageEnhance.Brightness(image)

            self.im_output = enhancer.enhance(factor)

            self.lvl_bg = ImageTk.PhotoImage(self.im_output)
            canvas.create_image(0, 0, image=self.lvl_bg, anchor="nw")
        else:  # applies special image settings if working with dual grid
            self.lvl_bgbg_path = (
                self.lvl_bg_path
            )  # Creates seperate image path variable for bgbg image

            file_id = self.tree_files.selection()[0]
            # checks which room is being opened to see if a special bg is needed
            selected_room_template_name = self.level_list_panel.get_selected_room_template_name()
            factor = 0.6  # darkens the image

            if self.lvl_bg_path == self.textures_dir / "bg_ice.png":
                if str(selected_room_template_name).startswith(
                    "mothership"
                ):
                    self.lvl_bgbg_path = self.textures_dir / "bg_mothership.png"
                    factor = 1.0  # keeps image the same
                else:
                    factor = 2.5  # brightens the image for ices caves
            elif str(self.tree_files.item(file_id, option="text")).startswith(
                "blackmark"
            ):
                factor = 2.5  # brightens the image for black market
            elif (
                str(self.tree_files.item(file_id, option="text")).startswith("generic")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "cosmic"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith("duat")
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "palace"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "ending_hard"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_m"
                )
                or str(self.tree_files.item(file_id, option="text")).startswith(
                    "challenge_st"
                )
            ):
                factor = 0  # darkens the image for cosmic ocean and duat and others

            image_dual = Image.open(self.lvl_bgbg_path).convert("RGBA")
            image_dual = image_dual.resize(
                (int(canvas["width"]), int(canvas["height"])), Image.BILINEAR
            )  ## The (250, 250) is (height, width)
            enhancer = ImageEnhance.Brightness(image_dual)

            self.im_output_dual = enhancer.enhance(factor)

            self.lvl_bgbg = ImageTk.PhotoImage(self.im_output_dual)
            canvas.create_image(0, 0, image=self.lvl_bgbg, anchor="nw")

        # finishes by drawing grid on top
        for i in range(0, cols + 2):
            canvas.create_line(
                (i) * self.mag,
                0,
                (i) * self.mag,
                (rows) * self.mag,
                fill="#F0F0F0",
            )
        for i in range(0, rows):
            canvas.create_line(
                0,
                (i) * self.mag,
                self.mag * (cols + 2),
                (i) * self.mag,
                fill="#F0F0F0",
            )

    def room_select(self, _event):  # Loads room when click if not parent node
        self.dual_mode = False
        selected_room = self.level_list_panel.get_selected_room()
        if selected_room:
            self.last_selected_room = selected_room
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
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
                            self.dual_mode = True

            if r"\!dual" in current_settings:
                self.dual_mode = True
                self.var_dual.set(1)
            else:
                self.dual_mode = False
                self.var_dual.set(0)

            if r"\!flip" in current_settings:
                self.var_flip.set(1)
            else:
                self.var_flip.set(0)

            if r"\!purge" in current_settings:
                self.var_purge.set(1)
            else:
                self.var_purge.set(0)

            if r"\!onlyflip" in current_settings:
                self.var_only_flip.set(1)
            else:
                self.var_only_flip.set(0)

            if r"\!ignore" in current_settings:
                self.var_ignore.set(1)
            else:
                self.var_ignore.set(0)

            if r"\!rare" in current_settings:
                self.var_rare.set(1)
            else:
                self.var_rare.set(0)

            if r"\!hard" in current_settings:
                self.var_hard.set(1)
            else:
                self.var_hard.set(0)

            if r"\!liquid" in current_settings:
                self.var_liquid.set(1)
            else:
                self.var_liquid.set(0)

            self.rows = len(current_room_tiles)
            self.cols = len(str(current_room_tiles[0]))

            # self.mag = self.canvas.winfo_height() / self.rows - 30
            if not self.dual_mode:
                self._draw_grid(
                    self.cols, self.rows, self.canvas, False
                )  # cols rows canvas dual(True/False)
                self.canvas_dual["width"] = 0
                self.canvas_dual["height"] = 0
                self.canvas.grid()
                self.canvas_dual.grid_remove()  # hides it for now
                self.foreground_label.grid_remove()
                self.background_label.grid_remove()
            else:
                self.canvas.grid()
                self.canvas_dual.grid()  # brings it back
                self._draw_grid(
                    int((self.cols - 1) / 2), self.rows, self.canvas, False
                )  # cols rows canvas dual(True/False)
                self._draw_grid(
                    int((self.cols - 1) / 2), self.rows, self.canvas_dual, True
                )
                self.foreground_label.grid()
                self.background_label.grid()

            # Create a grid of None to store the references to the tiles
            self.tiles = [
                [None for _ in range(self.cols)] for _ in range(self.rows)
            ]  # tile image displays
            self.tiles_meta = [
                [None for _ in range(self.cols)] for _ in range(self.rows)
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
                        for _palette_block in self.tile_palette_ref_in_use:
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
                        if self.dual_mode and curcol > int((self.cols - 1) / 2):
                            x2_coord = int(curcol - ((self.cols - 1) / 2) - 1)
                            x_coord = 0
                            y_coord = 0
                            for tile_name_ref in self.draw_mode:
                                if tile_name == str(tile_name_ref[0]):
                                    x_coord, y_coord = TextureUtil.adjust_texture_xy(
                                        tile_image.width(),
                                        tile_image.height(),
                                        tile_name_ref[1],
                                    )
                            self.tiles[currow][curcol] = self.canvas_dual.create_image(
                                x2_coord * self.mag - x_coord,
                                currow * self.mag - y_coord,
                                image=tile_image,
                                anchor="nw",
                            )
                            _coords = (
                                x2_coord * self.mag,
                                currow * self.mag,
                                x2_coord * self.mag + 50,
                                currow * self.mag + 50,
                            )
                            self.tiles_meta[currow][curcol] = block
                        else:
                            x_coord = 0
                            y_coord = 0
                            for tile_name_ref in self.draw_mode:
                                if tile_name == str(tile_name_ref[0]):
                                    x_coord, y_coord = TextureUtil.adjust_texture_xy(
                                        tile_image.width(),
                                        tile_image.height(),
                                        tile_name_ref[1],
                                    )
                            self.tiles[currow][curcol] = self.canvas.create_image(
                                curcol * self.mag - x_coord,
                                currow * self.mag - y_coord,
                                image=tile_image,
                                anchor="nw",
                            )
                            _coords = (
                                curcol * self.mag,
                                currow * self.mag,
                                curcol * self.mag + 50,
                                currow * self.mag + 50,
                            )
                            self.tiles_meta[currow][curcol] = block
                    curcol = curcol + 1
        else:
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()
        self.button_clear["state"] = tk.NORMAL

    def read_lvl_file(self, editor_type, lvl):
        if editor_type == EditorType.VANILLA_ROOMS:
            return self.read_vanilla_lvl_file(lvl)
        else:
            return self.read_custom_lvl_file(lvl)

    def read_vanilla_lvl_file(self, lvl):
        self.last_selected_room = None
        self.usable_codes = ShortCode.usable_codes()
        self.check_dependencies()

        self.rules_tab.reset()

        self.level_list_panel.reset()
        self.button_replace["state"] = tk.NORMAL

        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        self.lvl = lvl

        self.lvl_biome = Biomes.get_biome_for_level(lvl)
        self.lvl_bg_path = self.textures_dir / TextureUtil.get_bg_texture_file_name(lvl)

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

        self.full_size = None

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
                    x_offset = 0
                    y_offset = 0
                    for tile_name_ref in self.draw_mode:
                        if tile_name == str(tile_name_ref[0]):
                            x_offset, y_offset = TextureUtil.adjust_texture_xy(
                                tile_image.width(),
                                tile_image.height(),
                                tile_name_ref[1],
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

    # Used only in the combobox for selecting a theme to get the theme code that
    # corresponds to the display-friendly theme name.
    @staticmethod
    def theme_for_name(name):
        if name == "Dwelling":
            return BIOME.DWELLING
        elif name == "Jungle":
            return BIOME.JUNGLE
        elif name == "Volcana":
            return BIOME.VOLCANA
        elif name == "Olmec":
            return BIOME.OLMEC
        elif name == "Tide Pool":
            return BIOME.TIDE_POOL
        elif name == "Temple":
            return BIOME.TEMPLE
        elif name == "Ice Caves":
            return BIOME.ICE_CAVES
        elif name == "Neo Babylon":
            return BIOME.NEO_BABYLON
        elif name == "Sunken City":
            return BIOME.SUNKEN_CITY
        elif name == "City of Gold":
            return BIOME.CITY_OF_GOLD
        elif name == "Duat":
            return BIOME.DUAT
        elif name == "Eggplant World":
            return BIOME.EGGPLANT
        elif name == "Surface":
            return BIOME.SURFACE
        return None

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
