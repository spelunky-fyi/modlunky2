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
from modlunky2.ui.levels.custom_levels.custom_level_editor import CustomLevelEditor
from modlunky2.ui.levels.custom_levels.options_panel import OptionsPanel
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.custom_levels.save_level import save_level as save_custom_level
from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.ui.levels.shared.biomes import Biomes, BIOME
from modlunky2.ui.levels.shared.files_tree import FilesTree, PACK_LIST_TYPE, LEVEL_TYPE
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
from modlunky2.ui.levels.vanilla_levels.vanilla_level_editor import VanillaLevelEditor
from modlunky2.ui.levels.vanilla_levels.variables.level_dependencies import LevelDependencies
from modlunky2.ui.levels.vanilla_levels.variables.variables_tab import VariablesTab
from modlunky2.ui.levels.warm_welcome import WarmWelcome
from modlunky2.ui.widgets import PopupWindow, ScrollableFrameLegacy, Tab
from modlunky2.utils import is_windows, tb_info

logger = logging.getLogger(__name__)

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

        self.tab_control = tab_control
        self.install_dir = modlunky_config.install_dir
        self.textures_dir = modlunky_config.install_dir / "Mods/Extracted/Data/Textures"
        self.extracts_path = self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        self.packs_path = self.install_dir / "Mods" / "Packs"

        self._sprite_fetcher = None
        self.texture_fetcher = TextureUtil(None)

        self.tile_palette_ref_in_use = None
        self.tile_palette_map = {}
        self.tile_palette_suggestions = None
        self.lvl = None
        self.lvl_biome = None
        self.last_selected_tab = None
        self.list_preview_tiles_ref = None
        self.current_level_custom = None
        self.custom_editor_foreground_tile_codes = None
        self.custom_editor_background_tile_codes = None
        self.editor_tab_control = None
        self.vanilla_level_editor_tab = None
        self.custom_level_editor_tab = None
        self.last_selected_editor_tab = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        def open_editor():
            if os.path.isdir(self.extracts_path):
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

    # Run when start screen option is selected
    def load_editor(self):
        self.show_console = False
        self.modlunky_ui.forget_console()
        self.warm_welcome.grid_remove()

        self.editor_tab_control = ttk.Notebook(self)
        self.editor_tab_control.grid(row=0, column=0, sticky="nw")

        self.editor_tab_control.bind_all(
            "<Control-s>", lambda e: self.save_changes_shortcut()
        )

        self.vanilla_level_editor_tab = VanillaLevelEditor(
            self.editor_tab_control,
            self.modlunky_config,
            self.texture_fetcher,
            self.packs_path,
            self.extracts_path,
            self.textures_dir,
            self.standalone,
            self.go_back,
        )
        self.custom_level_editor_tab = CustomLevelEditor(
            self.editor_tab_control,
            self.modlunky_config,
            self.texture_fetcher,
            self.packs_path,
            self.extracts_path,
            self.textures_dir,
            self.standalone,
            self.go_back,
        )
        self.last_selected_editor_tab = self.vanilla_level_editor_tab

        self.editor_tab_control.add(
            self.vanilla_level_editor_tab, text="Vanilla room editor"
        )
        self.editor_tab_control.add(
            self.custom_level_editor_tab, text="Custom level editor"
        )

        def tab_selected(event):
            if event.widget.select() == self.last_selected_editor_tab:
                return
            if self.last_selected_editor_tab.save_needed:
                msg_box = tk.messagebox.askquestion(
                    "Continue?",
                    "You have unsaved changes.\nContinue without saving?",
                    icon="warning",
                )
                if msg_box == "yes":
                    self.last_selected_editor_tab.reset_save_button()
                    logger.debug("Switched tabs without saving.")
                else:
                    self.editor_tab_control.select(self.last_selected_editor_tab)
                    return
            self.reset()
            # self.load_packs(self.files_tree)
            self.last_selected_editor_tab = event.widget.select()
            tab = event.widget.tab(self.last_selected_editor_tab, "text")
            if tab == "Vanilla room editor":
                self.modlunky_config.level_editor_tab = 0
            else:
                self.modlunky_config.level_editor_tab = 1
            self.modlunky_config.save()

        self.editor_tab_control.bind("<<NotebookTabChanged>>", tab_selected)
        if self.modlunky_config.level_editor_tab == 1:
            self.editor_tab_control.select(self.custom_level_editor_tab)

    def reset(self):
        logger.debug("Resetting..")
        self.vanilla_level_editor_tab.reset()
        self.custom_level_editor_tab.reset()

    # Called whenever CTRL+S is pressed, saves depending on editor tab
    def save_changes_shortcut(self):
        self.last_selected_editor_tab.save_changes()

    def go_back(self):
        msg_box = tk.messagebox.askquestion(
            "Exit Editor?",
            "Exit editor and return to start screen?\n Load data will be lost.",
            icon="warning",
        )
        if msg_box == "yes":
            self.custom_level_editor_tab.reset()
            self.vanilla_level_editor_tab.reset()
            self.editor_tab_control.grid_remove()
            self.warm_welcome.grid()
            self.tab_control.grid_remove()
