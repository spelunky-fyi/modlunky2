# pylint: disable=too-many-lines

import datetime
import glob
import logging
import os
import os.path
import re
import shutil
import tempfile
import tkinter as tk
import tkinter.messagebox as tkMessageBox
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from shutil import copyfile
from tkinter import ttk

import pyperclip
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

from modlunky2.config import Config
from modlunky2.constants import BASE_DIR
from modlunky2.levels import LevelFile
from modlunky2.levels.level_chances import LevelChance, LevelChances
from modlunky2.levels.level_settings import LevelSetting, LevelSettings
from modlunky2.levels.level_templates import (
    Chunk,
    LevelTemplate,
    LevelTemplates,
    TemplateSetting,
)
from modlunky2.levels.monster_chances import MonsterChance, MonsterChances
from modlunky2.levels.tile_codes import VALID_TILE_CODES, TileCode, TileCodes
from modlunky2.sprites import SpelunkySpriteFetcher
from modlunky2.sprites.tilecode_extras import TILENAMES
from modlunky2.ui.widgets import PopupWindow, ScrollableFrameLegacy, Tab
from modlunky2.utils import is_windows, tb_info

logger = logging.getLogger("modlunky2")

class EditorType(Enum):
    VANILLA_ROOMS = "single_room"
    CUSTOM_LEVELS = "custom_levels"

class CustomLevelSaveFormat:
    def __init__(self, name, room_template_format, include_vanilla_setrooms):
        self.name = name or room_template_format
        self.room_template_format = room_template_format
        self.include_vanilla_setrooms = include_vanilla_setrooms

    @classmethod
    def LevelSequence(cls):
        return cls("LevelSequence", "setroom{y}_{x}", True)
    
    @classmethod
    def Vanilla(cls):
        return cls("Vanilla setroom [warning]", "setroom{y}-{x}", False)

    def toJSON(self):
        return {"name": self.name, "room_template_format": self.room_template_format, "include_vanilla_setrooms": self.include_vanilla_setrooms}

    @classmethod
    def fromJSON(cls, json):
        return cls(json["name"], json["room_template_format"], json["include_vanilla_setrooms"])
    

class LevelsTab(Tab):
    def __init__(
        self, tab_control, modlunky_ui, modlunky_config: Config, *args, **kwargs
    ):  # Loads editor start screen
        super().__init__(tab_control, *args, **kwargs)
        self.modlunky_config = modlunky_config

        self.modlunky_ui = modlunky_ui
        self.tree_levels = LevelsTree(
            self, self, self.modlunky_config, selectmode="browse"
        )
        self.last_selected_room = None
        # TODO: Get actual resolution
        self.screen_width = 1290
        self.screen_height = 720
        self.dual_mode = False
        self.tab_control = tab_control
        self.install_dir = modlunky_config.install_dir
        self.textures_dir = modlunky_config.install_dir / "Mods/Extracted/Data/Textures"
        self._sprite_fetcher = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.custom_editor_zoom_level = 30

        self.lvl_editor_start_frame = tk.Frame(
            self,
            bg="black",
        )
        self.lvl_editor_start_frame.grid(row=0, column=0, columnspan=2, sticky="nswe")
        self.lvl_editor_start_frame.columnconfigure(0, weight=1)
        self.lvl_editor_start_frame.rowconfigure(1, weight=1)

        self.extracts_path = self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        self.packs_path = self.install_dir / "Mods" / "Packs"

        self.welcome_label_title = tk.Label(
            self.lvl_editor_start_frame,
            text=("Spelunky 2 Level Editor"),
            anchor="center",
            bg="black",
            fg="white",
            font=("Arial", 45),
        )
        self.welcome_label_title.grid(
            row=0, column=0, sticky="nwe", ipady=30, padx=(10, 10)
        )

        self.welcome_label = tk.Label(
            self.lvl_editor_start_frame,
            text=(
                "Welcome to the Spelunky 2 Level Editor!\n"
                "Created by JackHasWifi with lots of help from "
                "Garebear, Fingerspit, Wolfo, and the community.\n\n "
                "NOTICE: Saving will save "
                "changes to a file in your selected pack and never overwrite its extracts counterpart.\n"
                "BIGGER NOTICE: Please make backups of your files. This is still in beta stages.."
            ),
            anchor="center",
            bg="black",
            fg="white",
            font=("Arial", 12),
        )
        self.welcome_label.grid(row=1, column=0, sticky="nwe", ipady=30, padx=(10, 10))

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
        self.lvl_bgs = {}
        self.rows = None
        self.cols = None
        self.tiles = None
        self.tiles_meta = None
        self.im_output_dual = None
        self.tile_pallete_ref_in_use = None
        self.tile_pallete_map = {}
        self.tile_pallete_suggestions = None
        self.lvl = None
        self.lvl_biome = None
        self.node = None
        self.sister_locations = None
        self.icon_add = None
        self.icon_folder = None
        self.icon_lvl_vanilla = None
        self.icon_lvl_modded = None
        self.loaded_pack = None
        self.last_selected_tab = None
        self.list_preview_tiles_ref = None
        self.full_size = None
        self.tiles_full = None
        self.tiles_full_dual = None
        self.current_level_full = None
        self.mag_full = None
        self.custom_editor_foreground_tile_images = None
        self.custom_editor_background_tile_images = None
        self.custom_editor_foreground_tile_codes = None
        self.custom_editor_background_tile_codes = None
        self.editor_tab_control = None
        self.single_room_editor_tab = None
        self.full_level_editor_tab = None
        self.last_selected_editor_tab = None
        self.current_editor_type = EditorType.VANILLA_ROOMS
        self.usable_codes = None
        self.usable_codes_string = (
            r"""!"#$%&'()*+,-.0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`"""
            r"""abcdefghijklmnopqrstuvwxyz{|}~€‚ƒ„…†‡ˆ‰Š‹Œ Ž‘’“”•–—™š›œžŸ¡¢£¤¥¦§"""
            r"""¨©ª«¬-®¯°±²³´µ¶·¸¹°»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæç"""
            r"""èéêëìíîïðñòóôõö÷øùúûüýþÿ"""
        )

        self.base_save_formats = [CustomLevelSaveFormat.LevelSequence(), CustomLevelSaveFormat.Vanilla()]
        custom_save_formats = self.modlunky_config.config_file.custom_level_editor_custom_save_formats
        if custom_save_formats:
            self.custom_save_formats = list(map(lambda json: CustomLevelSaveFormat.fromJSON(json), custom_save_formats))
        else:
            self.custom_save_formats = []

        default_save_format = self.modlunky_config.config_file.custom_level_editor_default_save_format
        # Set the format that will be used for saving new level files.
        if default_save_format:
            self.default_save_format = CustomLevelSaveFormat.fromJSON(default_save_format)
        else:
            self.default_save_format = self.base_save_formats[0]
        # Save format used in the currently loaded level file.
        self.current_save_format = None

        def load_extracts_lvls():
            if os.path.isdir(self.extracts_path):
                self.lvls_path = self.extracts_path
                self.load_editor()
            else:
                tk.messagebox.showerror(
                    "Oops?",
                    "Please extract your game before using the level editor",
                )

        self.btn_lvl_extracts = ttk.Button(
            self.lvl_editor_start_frame,
            text="Open Editor",
            command=load_extracts_lvls,
        )
        self.btn_lvl_extracts.grid(
            row=2, column=0, sticky="nswe", ipady=30, padx=(20, 20), pady=(20, 20)
        )

    def on_load(self):
        self._sprite_fetcher = SpelunkySpriteFetcher(
            self.install_dir / "Mods/Extracted"
        )

    def lvl_icon(self, modded):
        if modded:
            if self.icon_lvl_modded == None:
                self.icon_lvl_modded = ImageTk.PhotoImage(
                    Image.open(
                        BASE_DIR / "static/images/lvl_modded.png"
                    ).resize((20, 20))
                )
            return self.icon_lvl_modded
        else:
            if self.icon_lvl_vanilla == None:
                self.icon_lvl_vanilla = ImageTk.PhotoImage(
                    Image.open(BASE_DIR / "static/images/lvl.png").resize((20, 20))
                )
            return self.icon_lvl_vanilla

    # Run when start screen option is selected
    def load_editor(self):
        self.show_console = False
        self.modlunky_ui.forget_console()
        self.save_needed = False
        self.last_selected_file = None
        self.tiles = None
        self.tiles_meta = None
        self.custom_editor_foreground_tile_images = None
        self.custom_editor_background_tile_images = None
        self.custom_editor_foreground_tile_codes = None
        self.custom_editor_background_tile_codes = None
        self.lvl_editor_start_frame.grid_remove()

        self.icon_add = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/add.png").resize((20, 20))
        )
        self.icon_folder = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/folder.png").resize((20, 20))
        )

        self.editor_tab_control = ttk.Notebook(self)
        self.editor_tab_control.grid(row=0, column=0, sticky="nw")
        

        self.single_room_editor_tab = ttk.Frame(self.editor_tab_control)
        self.full_level_editor_tab = ttk.Frame(self.editor_tab_control)
        self.last_selected_editor_tab = self.single_room_editor_tab

        self.editor_tab_control.add(self.single_room_editor_tab, text = "Vanilla room editor")
        self.editor_tab_control.add(self.full_level_editor_tab, text = "Custom level editor")

        self.load_single_room_editor(self.single_room_editor_tab)
        self.load_full_level_editor(self.full_level_editor_tab)

        def tab_selected(event):
            if event.widget.select() == self.last_selected_editor_tab:
                return
            if (
                self.save_needed
                and self.last_selected_file is not None
            ):
                msg_box = tk.messagebox.askquestion(
                    "Continue?",
                    "You have unsaved changes.\nContinue without saving?",
                    icon="warning",
                )
                if msg_box == "yes":
                    self.save_needed = False
                    self.button_save["state"] = tk.DISABLED
                    self.button_save_full["state"] = tk.DISABLED
                    logger.debug("Switched tabs without saving.")
                else:
                    self.editor_tab_control.select(self.last_selected_editor_tab)
                    return
            self.reset()
            self.last_selected_editor_tab = event.widget.select()
            tab = event.widget.tab(self.last_selected_editor_tab, "text")
            if tab == "Vanilla room editor":
                self.modlunky_config.config_file.level_editor_tab = 0
                self.current_editor_type = EditorType.VANILLA_ROOMS
            else:
                self.modlunky_config.config_file.level_editor_tab = 1
                self.current_editor_type = EditorType.CUSTOM_LEVELS
            self.modlunky_config.config_file.save()


        self.editor_tab_control.bind("<<NotebookTabChanged>>", tab_selected)
        if self.modlunky_config.config_file.level_editor_tab == 1:
            self.editor_tab_control.select(self.full_level_editor_tab)

    def load_full_level_editor(self, tab):
        tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
        tab.columnconfigure(0, weight=0)
        tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        tab.rowconfigure(0, weight=1)

        # Loads lvl files
        tree_files = ttk.Treeview(
            tab, selectmode="browse", padding=[-15, 0, 0, 0]
        ) # This tree shows the lvl files loaded from the chosen dir, excluding vanilla lvl files.
        tree_files.place(x=30, y=95)
        vsb_tree_files = ttk.Scrollbar(
            tab, orient="vertical", command=tree_files.yview
        )
        vsb_tree_files.place(x=30 + 200 + 2, y=95, height=200 + 20)
        tree_files.configure(yscrollcommand=vsb_tree_files.set)
        tree_files.grid(row=0, column=0, rowspan=1, sticky="nswe")
        vsb_tree_files.grid(row=0, column=0, sticky="nse")

        self.load_packs(tree_files)

        tree_files.bind("<ButtonRelease-1>", lambda event: self.tree_filesitemclick(event, tree_files, EditorType.CUSTOM_LEVELS))

        self.button_back_full = tk.Button(tab, text="Exit Editor", bg="black", fg="white", command=self.go_back)
        self.button_back_full.grid(row=1, column=0, sticky="nswe")

        self.button_save_full = tk.Button(tab, text="Save", bg="Blue", fg="white", command=self.save_changes_full)
        self.button_save_full.grid(row=2, column=0, sticky="nswe")
        self.button_save_full["state"] = tk.DISABLED

        editor_view = tk.Frame(tab)
        # editor_view.configure(background='red')
        editor_view.grid(row=0, column=1, rowspan=3, sticky="nswe")
        
        editor_view.columnconfigure(3, weight=1)
        editor_view.columnconfigure(7, minsize=17)
        editor_view.columnconfigure(6, minsize=50)
        editor_view.rowconfigure(1, weight=1)

        scrollable_canvas = tk.Canvas(editor_view, bg="#292929")
        scrollable_canvas.grid(row=0, column=0, columnspan=8, rowspan=2, sticky="nswe")
        scrollable_canvas.columnconfigure(0, weight=1)
        scrollable_canvas.rowconfigure(0, weight=1)

        scrollable_frame = tk.Frame(scrollable_canvas, bg="#343434")

        scrollable_frame.columnconfigure(
            0, minsize=int(int(self.screen_width) / 2)
        )
        scrollable_frame.columnconfigure(1, weight=1)
        scrollable_frame.columnconfigure(2, minsize=50)
        scrollable_frame.columnconfigure(
            4, minsize=int(int(self.screen_width) / 2)
        )
        scrollable_frame.rowconfigure(
            0, minsize=int(int(self.screen_height) / 2)
        )
        scrollable_frame.rowconfigure(1, weight=1)
        scrollable_frame.rowconfigure(2, minsize=100)
        scrollable_frame.rowconfigure(
            4, minsize=int(int(self.screen_height) / 2)
        )
        # scrollable_frame.columnconfigure(0, weight=1)
        # scrollable_frame.rowconfigure(0, weight=1)
        scrollable_frame.grid(row=0, column=0, sticky="nswe")

        width = scrollable_canvas.winfo_screenwidth()
        height = scrollable_canvas.winfo_screenheight()
        scrollable_canvas.create_window(
            (width, height),
            window=scrollable_frame,
            anchor="center",
        )
        scrollable_canvas["width"] = width
        scrollable_canvas["height"] = height

        hbar = ttk.Scrollbar(editor_view, orient="horizontal", command=scrollable_canvas.xview)
        hbar.grid(row=0, column=0, columnspan=7, rowspan=2, sticky="swe")
        vbar = ttk.Scrollbar(editor_view, orient="vertical", command=scrollable_canvas.yview)
        vbar.grid(row=0, column=0, columnspan=8, rowspan=2, sticky="nse")

        scrollable_canvas.bind("<Enter>", lambda event: self._bind_to_mousewheel(event, hbar, vbar, scrollable_canvas))
        scrollable_canvas.bind("<Leave>", lambda event: self._unbind_from_mousewheel(event, scrollable_canvas))
        scrollable_frame.bind(
            "<Configure>",
            lambda e: scrollable_canvas.configure(
                scrollregion=scrollable_canvas.bbox("all")
            ),
        )

        scrollable_canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        canvas_foreground = tk.Canvas(scrollable_frame, bg="#343434")
        canvas_foreground.grid(row=1, column=1)
        canvas_background = tk.Canvas(scrollable_frame, bg="#343434")
        canvas_background.grid(row=1, column=1)
        canvas_background.grid_remove()
        self.custom_level_canvas = scrollable_canvas
        self.custom_level_frame = scrollable_frame
        self.custom_level_canvas_foreground = canvas_foreground
        self.custom_level_canvas_background = canvas_background


        switch_variable = tk.StringVar()
        def toggle_layer():
            nonlocal switch_variable
            x_coord = switch_variable.get()
            if x_coord == "0":
                canvas_foreground.grid()
                canvas_background.grid_remove()
            else:
                canvas_foreground.grid_remove()
                canvas_background.grid()

        front_view = tk.Radiobutton(
            editor_view,
            text="Foreground",
            variable=switch_variable,
            indicatoron=False,
            value="0",
            width=10,
            command=toggle_layer,
        )
        switch_variable.set("0")
        front_view.grid(column=0, row=0, sticky="ne")
        back_view = tk.Radiobutton(
            editor_view,
            text="Background",
            variable=switch_variable,
            indicatoron=False,
            value="1",
            width=10,
            command=toggle_layer,
        )
        back_view.grid(column=1, row=0, sticky="nw")

        self.custom_editor_side_panel = tk.Frame(tab)
        self.custom_editor_side_panel.grid(column=2, row=0, rowspan=3, sticky="nswe")
        self.custom_editor_side_panel.rowconfigure(0, weight=1)
        self.custom_editor_side_panel.columnconfigure(0, weight=1)

        side_panel_hidden = False
        side_panel_hide_button = tk.Button(
            editor_view,
            text=">>"
        )
        def toggle_panel_hidden():
            nonlocal side_panel_hidden
            side_panel_hidden = not side_panel_hidden
            if side_panel_hidden:
                self.custom_editor_side_panel.grid_remove()
                side_panel_hide_button.configure(text="<<")
            else:
                self.custom_editor_side_panel.grid()
                side_panel_hide_button.configure(text=">>")
            # variable=side_panel_hidden,
            # indicatoron=False,
            # value=False,
            # width=10,
        side_panel_hide_button.configure(
            command=toggle_panel_hidden,
        )
        side_panel_hide_button.grid(column=6, row=0, sticky="nwe")

        tiles_panel = tk.Frame(self.custom_editor_side_panel)
        tiles_panel.grid(row=0, column=0, sticky="nswe")
        
        tiles_panel.rowconfigure(2, weight=1)
        tiles_panel.rowconfigure(3, minsize=50)

        self.tile_pallete_custom = ScrollableFrameLegacy(
            tiles_panel, text="Tile Palette", width=50
        )
        self.tile_pallete_custom.grid(row=2, column=0, columnspan=4, sticky="nswe")
        self.tile_pallete_custom.scrollable_frame["width"] = 50

        self.tile_label_custom = ttk.Label(
            tiles_panel,
            text="Primary Tile: empty 0",
        )
        self.tile_label_custom.grid(row=0, column=1, sticky="we")

        self.tile_label_secondary_custom = ttk.Label(
            tiles_panel,
            text="Secondary Tile: empty 0",
        )
        self.tile_label_secondary_custom.grid(row=1, column=1, sticky="we")

        self.img_sel_custom = ImageTk.PhotoImage(self._sprite_fetcher.get("empty"))

        self.panel_sel_custom = ttk.Label(
            tiles_panel,
            image=ImageTk.PhotoImage(self._sprite_fetcher.get("empty")),
            width=50
        )
        self.panel_sel_custom.grid(row=0, column=2)

        self.panel_sel_secondary_custom = ttk.Label(
            tiles_panel,
            image=ImageTk.PhotoImage(self._sprite_fetcher.get("empty")),
            width=50
        )
        self.panel_sel_secondary_custom.grid(row=1, column=2)
        
        self.button_tilecode_del_custom = tk.Button(
            tiles_panel,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=lambda: self.del_tilecode_custom(
                self.tile_label_custom,
                [canvas_foreground, canvas_background],
                [self.custom_editor_foreground_tile_images, self.custom_editor_background_tile_images],
                [self.custom_editor_foreground_tile_codes, self.custom_editor_background_tile_codes],
            ),
        )        
        self.button_tilecode_del_custom.grid(row=0, column=0, sticky="e")
        self.button_tilecode_del_custom["state"] = tk.DISABLED
        
        self.button_tilecode_del_secondary_custom = tk.Button(
            tiles_panel,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=lambda: self.del_tilecode_custom(
                self.tile_label_secondary_custom,
                [self.custom_editor_foreground_tile_images, self.custom_editor_background_tile_images],
                [self.custom_editor_foreground_tile_codes, custom_editor_background_tile_codes],
            ),
        )        
        self.button_tilecode_del_secondary_custom.grid(row=1, column=0, sticky="e")
        self.button_tilecode_del_secondary_custom["state"] = tk.DISABLED

        self.combobox_custom = ttk.Combobox(tiles_panel, height=20)
        self.combobox_custom.grid(row=3, column=0, columnspan=2, sticky="swe")
        self.combobox_custom["state"] = tk.DISABLED
        tile_codes = sorted(VALID_TILE_CODES, key=str.lower)
        self.combobox_custom["values"] = tile_codes

        self.button_tilecode_add_custom = tk.Button(
            tiles_panel,
            text="Add TileCode",
            bg="yellow",
            command=lambda: self.add_tilecode(
                str(self.combobox_custom.get()),
                "100",
                "empty",
                self.tile_pallete_custom,
                self.tile_label_custom,
                self.tile_label_secondary_custom,
                self.panel_sel_custom,
                self.panel_sel_secondary_custom,
                self.custom_editor_zoom_level
            ),
        )
        self.button_tilecode_add_custom.grid(
            row=3, column=2, sticky="nswe"
        )
        canvas_foreground.bind(
            "<Button-1>",
            lambda event: self.canvas_click(
                event,
                canvas_foreground,
                self.custom_editor_zoom_level,
                self.tile_label_custom,
                self.panel_sel_custom,
                self.custom_editor_foreground_tile_images,
                self.custom_editor_foreground_tile_codes))
        canvas_foreground.bind(
            "<B1-Motion>",
            lambda event: self.canvas_click(
                event,
                canvas_foreground,
                self.custom_editor_zoom_level,
                self.tile_label_custom,
                self.panel_sel_custom,
                self.custom_editor_foreground_tile_images,
                self.custom_editor_foreground_tile_codes))
        canvas_foreground.bind(
            "<Button-3>",
            lambda event: self.canvas_click(
                event,
                canvas_foreground,
                self.custom_editor_zoom_level,
                self.tile_label_secondary_custom,
                self.panel_sel_secondary_custom,
                self.custom_editor_foreground_tile_images,
                self.custom_editor_foreground_tile_codes))
        canvas_foreground.bind(
            "<B3-Motion>",
            lambda event: self.canvas_click(
                event,
                canvas_foreground,
                self.custom_editor_zoom_level,
                self.tile_label_secondary_custom,
                self.panel_sel_secondary_custom,
                self.custom_editor_foreground_tile_images,
                self.custom_editor_foreground_tile_codes))

        canvas_background.bind(
            "<Button-1>",
            lambda event: self.canvas_click(
                event,
                canvas_background,
                self.custom_editor_zoom_level,
                self.tile_label_custom,
                self.panel_sel_custom,
                self.custom_editor_background_tile_images,
                self.custom_editor_background_tile_codes))
        canvas_background.bind(
            "<B1-Motion>",
            lambda event: self.canvas_click(
                event,
                canvas_background,
                self.custom_editor_zoom_level,
                self.tile_label_custom,
                self.panel_sel_custom,
                self.custom_editor_background_tile_images,
                self.custom_editor_background_tile_codes))
        canvas_background.bind(
            "<Button-3>",
            lambda event: self.canvas_click(
                event,
                canvas_background,
                self.custom_editor_zoom_level,
                self.tile_label_secondary_custom,
                self.panel_sel_secondary_custom,
                self.custom_editor_background_tile_images,
                self.custom_editor_background_tile_codes))
        canvas_background.bind(
            "<B3-Motion>",
            lambda event: self.canvas_click(
                event,
                canvas_background,
                self.custom_editor_zoom_level,
                self.tile_label_secondary_custom,
                self.panel_sel_secondary_custom,
                self.custom_editor_background_tile_images,
                self.custom_editor_background_tile_codes))

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

        self.rules_tab = ttk.Frame(self.tab_control)
        self.editor_tab = ttk.Frame(
            self.tab_control
        )  # Tab 2 is the actual level editor
        self.preview_tab = ttk.Frame(self.tab_control)
        self.variables_tab = ttk.Frame(self.tab_control)

        self.button_back = tk.Button(
            editor_tab, text="Exit Editor", bg="black", fg="white", command=self.go_back
        )
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

        # Rules Tab
        self.rules_tab.columnconfigure(0, weight=1)  # Column 1 = Everything Else
        self.rules_tab.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        self.tree = RulesTree(
            self.rules_tab, self, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        self.tree.bind("<Double-1>", lambda e: self.on_double_click(self.tree))
        self.tree.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb = ttk.Scrollbar(
            self.rules_tab, orient="vertical", command=self.tree.yview
        )
        self.vsb.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree.configure(yscrollcommand=self.vsb.set)
        self.tree["columns"] = ("1", "2", "3")
        self.tree["show"] = "headings"
        self.tree.column("1", width=100, anchor="w")
        self.tree.column("2", width=10, anchor="w")
        self.tree.column("3", width=100, anchor="w")
        self.tree.heading("1", text="Level Settings")
        self.tree.heading("2", text="Value")
        self.tree.heading("3", text="Notes")
        self.tree.grid(row=0, column=0, sticky="nwse")
        self.vsb.grid(row=0, column=1, sticky="nse")

        self.tree_chances_levels = RulesTree(
            self.rules_tab, self, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        self.tree_chances_levels.bind(
            "<Double-1>", lambda e: self.on_double_click(self.tree_chances_levels)
        )
        self.tree_chances_levels.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_chances_levels = ttk.Scrollbar(
            self.rules_tab, orient="vertical", command=self.tree_chances_levels.yview
        )
        self.vsb_chances_levels.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_chances_levels.configure(yscrollcommand=self.vsb_chances_levels.set)
        self.tree_chances_levels["columns"] = ("1", "2", "3")
        self.tree_chances_levels["show"] = "headings"
        self.tree_chances_levels.column("1", width=100, anchor="w")
        self.tree_chances_levels.column("2", width=10, anchor="w")
        self.tree_chances_levels.column("3", width=100, anchor="w")
        self.tree_chances_levels.heading("1", text="Level Chances")
        self.tree_chances_levels.heading("2", text="Value")
        self.tree_chances_levels.heading("3", text="Notes")
        self.tree_chances_levels.grid(row=1, column=0, sticky="nwse")
        self.vsb_chances_levels.grid(row=1, column=1, sticky="nse")

        self.tree_chances_monsters = RulesTree(
            self.rules_tab, self, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        self.tree_chances_monsters.bind(
            "<Double-1>", lambda e: self.on_double_click(self.tree_chances_monsters)
        )
        self.tree_chances_monsters.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_chances_monsters = ttk.Scrollbar(
            self.rules_tab, orient="vertical", command=self.tree_chances_monsters.yview
        )
        self.vsb_chances_monsters.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree.configure(yscrollcommand=self.vsb_chances_monsters.set)
        self.tree_chances_monsters["columns"] = ("1", "2", "3")
        self.tree_chances_monsters["show"] = "headings"
        self.tree_chances_monsters.column("1", width=100, anchor="w")
        self.tree_chances_monsters.column("2", width=10, anchor="w")
        self.tree_chances_monsters.column("3", width=100, anchor="w")
        self.tree_chances_monsters.heading("1", text="Monster Chances")
        self.tree_chances_monsters.heading("2", text="Value")
        self.tree_chances_monsters.heading("3", text="Notes")
        self.tree_chances_monsters.grid(row=2, column=0, sticky="nwse")
        self.vsb_chances_monsters.grid(row=2, column=1, sticky="nse")

        #  View Tab

        self.current_value_full = tk.DoubleVar()

        def slider_changed(_event):
            self.load_full_preview()

        self.slider_zoom_full = tk.Scale(
            self.preview_tab,
            from_=2,
            to=100,
            orient="horizontal",
            variable=self.current_value_full,
        )  # command=slider_changed,
        self.slider_zoom_full.set(50)
        self.slider_zoom_full.bind("<ButtonRelease-1>", slider_changed)
        self.slider_zoom_full.grid(row=0, column=0, columnspan=2, sticky="nw")

        self.preview_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.preview_tab.rowconfigure(1, weight=1)  # Row 0 = List box / Label

        self.canvas_grids_full = tk.Canvas(  # this is the main level editor grid
            self.preview_tab,
            bg="#292929",
        )
        self.canvas_grids_full.grid(row=1, column=0, columnspan=2, sticky="nw")

        self.canvas_grids_full.columnconfigure(2, weight=1)
        self.canvas_grids_full.rowconfigure(0, weight=1)

        self.scrollable_canvas_frame_full = tk.Frame(
            self.canvas_grids_full, bg="#343434"
        )

        # offsets the screen so user can freely scroll around work area
        self.scrollable_canvas_frame_full.columnconfigure(
            0, minsize=int(int(self.screen_width) / 2)
        )
        self.scrollable_canvas_frame_full.columnconfigure(1, weight=1)
        self.scrollable_canvas_frame_full.columnconfigure(2, minsize=50)
        self.scrollable_canvas_frame_full.columnconfigure(
            4, minsize=int(int(self.screen_width) / 2)
        )
        self.scrollable_canvas_frame_full.rowconfigure(
            0, minsize=int(int(self.screen_height) / 2)
        )
        self.scrollable_canvas_frame_full.rowconfigure(1, weight=1)
        self.scrollable_canvas_frame_full.rowconfigure(2, minsize=100)
        self.scrollable_canvas_frame_full.rowconfigure(2, minsize=100)
        self.scrollable_canvas_frame_full.rowconfigure(
            4, minsize=int(int(self.screen_height) / 2)
        )

        self.scrollable_canvas_frame_full.grid(row=0, column=0, sticky="nwes")
        self.vbar_full = ttk.Scrollbar(
            self.preview_tab, orient="vertical", command=self.canvas_grids_full.yview
        )
        self.vbar_full.grid(row=0, column=0, rowspan=4, columnspan=7, sticky="nse")
        self.hbar_full = ttk.Scrollbar(
            self.preview_tab, orient="horizontal", command=self.canvas_grids_full.xview
        )
        self.hbar_full.grid(row=0, column=0, rowspan=4, columnspan=8, sticky="wes")

        self.canvas_grids_full.config(
            xscrollcommand=self.hbar_full.set, yscrollcommand=self.vbar_full.set
        )
        x_origin = self.canvas_grids_full.winfo_screenwidth()
        y_origin = self.canvas_grids_full.winfo_screenheight()
        self.canvas_grids_full.create_window(
            (x_origin, y_origin),
            window=self.scrollable_canvas_frame_full,
            anchor="center",
        )
        self.canvas_grids_full["width"] = x_origin
        self.canvas_grids_full["height"] = y_origin
        self.canvas_grids_full.bind("<Enter>", lambda event: self._bind_to_mousewheel(event, self.hbar_full, self.vbar_full, self.canvas_grids_full))
        self.canvas_grids_full.bind("<Leave>", lambda event: self._unbind_from_mousewheel(event, self.canvas_grids_full))
        self.scrollable_canvas_frame_full.bind(
            "<Configure>",
            lambda e: self.canvas_grids_full.configure(
                scrollregion=self.canvas_grids_full.bbox("all")
            ),
        )

        self.canvas_full = tk.Canvas(  # this is the main level editor grid
            self.scrollable_canvas_frame_full,
            bg="#343434",
        )
        self.canvas_full.grid(row=1, column=1)
        # self.canvas_full.grid_remove()

        self.canvas_full_dual = tk.Canvas(  # this is the main level editor grid
            self.scrollable_canvas_frame_full,
            bg="#343434",
        )
        self.canvas_full_dual.grid(row=1, column=1)
        self.canvas_full_dual.grid_remove()

        def toggle_layer():
            x_coord = self.switch_variable_full.get()
            if x_coord == "0":
                self.canvas_full.grid()
                self.canvas_full_dual.grid_remove()
            else:
                self.canvas_full.grid_remove()
                self.canvas_full_dual.grid()

        self.switch_variable_full = tk.StringVar()
        self.front_preview = tk.Radiobutton(
            self.preview_tab,
            text="Foreground",
            variable=self.switch_variable_full,
            indicatoron=False,
            value="0",
            width=8,
            command=toggle_layer,
        )
        self.switch_variable_full.set("0")
        self.front_preview.grid(column=0, row=1, sticky="ne")
        self.back_preview = tk.Radiobutton(
            self.preview_tab,
            text="Background",
            variable=self.switch_variable_full,
            indicatoron=False,
            value="1",
            width=8,
            command=toggle_layer,
        )
        self.back_preview.grid(column=1, row=1, sticky="nw")

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

        self.tree_levels = LevelsTree(
            self.editor_tab, self, self.modlunky_config, selectmode="browse"
        )  # This tree shows the rooms in the level editor
        self.tree_levels.place(x=30, y=95)
        self.vsb_tree_levels = ttk.Scrollbar(
            self.editor_tab, orient="vertical", command=self.tree_levels.yview
        )
        self.vsb_tree_levels.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_levels.configure(yscrollcommand=self.vsb_tree_levels.set)
        self.my_list = os.listdir(
            self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        )
        self.tree_levels.grid(row=0, column=0, rowspan=5, sticky="nswe")
        self.vsb_tree_levels.grid(row=0, column=0, rowspan=5, sticky="nse")

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
        self.canvas_grids.bind("<Enter>", lambda event: self._bind_to_mousewheel(event, self.hbar, self.vbar, self.canvas_grids))
        self.canvas_grids.bind("<Leave>", lambda event: self._unbind_from_mousewheel(event, self.canvas_grids))
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

        # the tile palletes are loaded into here as buttons with their image
        # as a tile and txt as their value to grab when needed
        self.tile_pallete = ScrollableFrameLegacy(
            self.editor_tab, text="Tile Pallete", width=50
        )
        self.tile_pallete.grid(row=2, column=9, columnspan=4, rowspan=1, sticky="swne")
        self.tile_pallete.scrollable_frame["width"] = 50

        # shows selected tile. Important because this is used for more than just user
        # convenience; we can grab the currently used tile here
        self.tile_label = ttk.Label(
            self.editor_tab,
            text="Primary Tile:",
        )
        self.tile_label.grid(row=0, column=10, columnspan=1, sticky="we")
        # shows selected tile. Important because this is used for more than just user
        # convenience; we can grab the currently used tile here
        self.tile_label_secondary = ttk.Label(
            self.editor_tab,
            text="Secondary Tile:",
        )
        self.tile_label_secondary.grid(row=1, column=10, columnspan=1, sticky="we")

        self.img_sel = ImageTk.PhotoImage(
            Image.open(
                BASE_DIR / "static/images/tilecodetextures.png"
            )  ########################################### set selected img
        )
        self.panel_sel = ttk.Label(
            self.editor_tab, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel.grid(row=0, column=11)
        self.panel_sel_secondary = ttk.Label(
            self.editor_tab, image=self.img_sel, width=50
        )  # shows selected tile image
        self.panel_sel_secondary.grid(row=1, column=11)
        
        self.button_tilecode_del = tk.Button(
            self.editor_tab,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=self.del_tilecode,
        )
        self.button_tilecode_del.grid(row=0, column=9, sticky="e")
        self.button_tilecode_del["state"] = tk.DISABLED

        self.button_tilecode_del_secondary = tk.Button(
            self.editor_tab,
            text="Del",
            bg="red",
            fg="white",
            width=10,
            command=self.del_tilecode_secondary,
        )
        self.button_tilecode_del_secondary.grid(row=1, column=9, sticky="e")
        self.button_tilecode_del_secondary["state"] = tk.DISABLED

        self.combobox = ttk.Combobox(self.editor_tab, height=20)
        self.combobox.grid(row=4, column=9, columnspan=1, sticky="nswe")
        self.combobox["state"] = tk.DISABLED
        self.combobox_alt = ttk.Combobox(self.editor_tab, height=40)
        self.combobox_alt.grid(row=4, column=10, columnspan=1, sticky="nswe")
        self.combobox_alt.grid_remove()
        self.combobox_alt["state"] = tk.DISABLED

        self.scale_frame = ttk.Frame(self.editor_tab)
        self.scale_frame.columnconfigure(0, weight=1)
        self.scale_frame.grid(row=3, column=9, columnspan=2, sticky="nswe")

        self.scale_var = tk.StringVar()
        self.scale_var.set("100")
        self.scale_value_label = ttk.Label(
            self.scale_frame, anchor="center", textvariable=self.scale_var
        )
        self.scale_value_label.grid(row=0, column=0, sticky="ew")

        self.scale = ttk.Scale(
            self.scale_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.update_value,
        )  # scale for the percent of a selected tile
        self.scale.grid(row=1, column=0, sticky="we")
        self.scale.set(100)
        self.scale["state"] = tk.DISABLED

        self.button_tilecode_add = tk.Button(
            self.editor_tab,
            text="Add TileCode",
            bg="yellow",
            command=lambda: self.add_tilecode(
                str(self.combobox.get()),
                str(int(float(self.scale.get()))),
                self.combobox_alt.get(),
                self.tile_pallete,
                self.tile_label,
                self.tile_label_secondary,
                self.panel_sel,
                self.panel_sel_secondary,
                self.mag
            ),
        )
        self.button_tilecode_add.grid(
            row=3, column=11, rowspan=2, columnspan=2, sticky="nswe"
        )

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

        # color_base = int(random.random())
        self.uni_tile_code_list = []
        self.tile_pallete_ref = []
        self.panel_sel["image"] = ImageTk.PhotoImage(self._sprite_fetcher.get("empty"))
        self.tile_label["text"] = "Primary Tile: " + "empty 0"
        self.panel_sel_secondary["image"] = ImageTk.PhotoImage(
            self._sprite_fetcher.get("empty")
        )
        self.tile_label_secondary["text"] = "Secondary Tile: " + "empty 0"

        self.draw_mode = []  # slight adjustments of textures for tile preview
        # 1 = lower half tile
        # 2 = draw from bottom left
        # 3 = center
        # 4 = center to the right
        # 5 = draw bottom left + raise 1 tile
        # 6 = position doors
        # 7 = draw bottom left + raise half tile
        # 8 = draw bottom left + lowere 1 tile
        # 9 = draw bottom left + raise 1 tile + move left 1 tile
        # 10 = draw bottom left + raise 1 tile + move left 1 tile
        # 11 = move left 1 tile
        # 12 = raise 1 tile
        # 13 = draw from bottom left + move left half tile
        # 14 = precise bottom left for yama
        self.draw_mode.append(["anubis", 2])
        self.draw_mode.append(["olmec", 5])
        self.draw_mode.append(["alienqueen", 7])
        self.draw_mode.append(["kingu", 2])
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
        self.draw_mode.append(["giant_frog", 3])
        self.draw_mode.append(["door", 13])
        self.draw_mode.append(["starting_exit", 13])
        self.draw_mode.append(["eggplant_door", 13])
        self.draw_mode.append(["door2", 6])
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

        combo_tile_ids = []
        for tile_info in VALID_TILE_CODES:
            combo_tile_ids.append(tile_info)

        self.combobox["values"] = sorted(combo_tile_ids, key=str.lower)
        self.combobox_alt["values"] = sorted(combo_tile_ids, key=str.lower)

        def canvas_click(event, canvas, tile_label, panel_sel): # when the level editor grid is clicked
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

            x_coord_offset = 0
            y_coord_offset = 0
            img = None
            # height, width, channels = img.shape
            for tile_name_ref in self.draw_mode:
                if tile_label["text"].split(" ", 4)[2] == str(tile_name_ref[0]):
                    logger.debug(
                        "Applying custom anchor for %s",
                        tile_label["text"].split(" ", 4)[2],
                    )
                    for tile_ref in self.tile_pallete_ref_in_use:
                        if (
                            str(tile_ref[0].split(" ", 1)[0])
                            == tile_label["text"].split(" ", 4)[2]
                        ):
                            logger.debug("Found %s", tile_ref[0])
                            img = tile_ref[1]
                            x_coord_offset, y_coord_offset = self.adjust_texture_xy(
                                img.width(),
                                img.height(),
                                int(tile_name_ref[1]),
                            )

            canvas.delete(self.tiles[int(row)][int(col)])
            if canvas == self.canvas_dual:
                x2_coord = int(int(col) - ((len(self.tiles[0]) - 1) / 2) - 1)
                self.tiles[int(row)][int(col)] = canvas.create_image(
                    x2_coord * self.mag - x_coord_offset,
                    int(row) * self.mag - y_coord_offset,
                    image=panel_sel["image"],
                    anchor="nw",
                )
            else:
                self.tiles[int(row)][int(col)] = canvas.create_image(
                    int(col) * self.mag - x_coord_offset,
                    int(row) * self.mag - y_coord_offset,
                    image=panel_sel["image"],
                    anchor="nw",
                )
            self.tiles_meta[row][col] = tile_label["text"].split(" ", 4)[3]
            logger.debug(
                "%s replaced with %s",
                self.tiles_meta[row][col],
                tile_label["text"].split(" ", 4)[3],
            )
            self.remember_changes()  # remember changes made


        def holding_shift(event, canvas):
            self.canvas.config(cursor="pencil")
            self.canvas_dual.config(cursor="pencil")
            print("holding shift!! ", event.keysym)

        def shift_up(event, canvas):
            self.canvas.config(cursor="")
            self.canvas_dual.config(cursor="")
            print("no longer holding shift!! ", event.keysym)


        self.bind_all("<KeyPress-Shift_L>", lambda event: holding_shift(event, self.canvas))
        self.bind_all("<KeyPress-Shift_R>", lambda event: holding_shift(event, self.canvas))
        self.bind_all("<KeyRelease-Shift_L>", lambda event: shift_up(event, self.canvas))
     #   self.canvas.bind("<Shift-Button-1>", lambda event: test1(event, self.canvas))
        self.canvas.bind("<Button-1>", lambda event: canvas_click(event, self.canvas, self.tile_label, self.panel_sel))
        self.canvas.bind(
            "<B1-Motion>", lambda event: canvas_click(event, self.canvas, self.tile_label, self.panel_sel)
        )  # These second binds are so the user can hold down their mouse button when painting tiles
        self.canvas.bind(
            "<Button-3>", lambda event: canvas_click(event, self.canvas, self.tile_label_secondary, self.panel_sel_secondary)
        )
        self.canvas.bind(
            "<B3-Motion>", lambda event: canvas_click(event, self.canvas, self.tile_label_secondary, self.panel_sel_secondary)
        )  # These second binds are so the user can hold down their mouse button when painting tiles
        # self.canvas.bind("<Key>", lambda event: )
        self.canvas_dual.bind(
            "<Button-1>", lambda event: canvas_click(event, self.canvas_dual, self.tile_label, self.panel_sel)
        )
        self.canvas_dual.bind(
            "<B1-Motion>", lambda event: canvas_click(event, self.canvas_dual, self.tile_label, self.panel_sel)
        )
        self.canvas_dual.bind(
            "<Button-3>", lambda event: canvas_click(event, self.canvas_dual, self.tile_label_secondary, self.panel_sel_secondary)
        )
        self.canvas_dual.bind(
            "<B3-Motion>", lambda event: canvas_click(event, self.canvas_dual, self.tile_label_secondary, self.panel_sel_secondary)
        )
        self.tree_files.bind("<ButtonRelease-1>", lambda event: self.tree_filesitemclick(event, self.tree_files, EditorType.VANILLA_ROOMS))

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile_name, tile_code, tile_size):
        for tile_name_ref in self.draw_mode:
            if tile_name != str(tile_name_ref[0]):
                continue
            logger.debug("Applying custom anchor for %s", tile_name)
            tile_ref = self.tile_pallete_map[tile_code]
            if tile_ref:
                logger.debug("Found %s", tile_ref[0])
                img = tile_ref[1]
                return self.adjust_texture_xy(img.width(), img.height(), int(tile_name_ref[1]), tile_size)

        return 0, 0

    # Click event on a canvas for either left or right click to replace the tile at the cursor's position with
    # the selected tile.
    def canvas_click(self, event, canvas, tile_size, tile_label, panel_sel, tile_image_matrix, tile_code_matrix):
        column = int(event.x // tile_size)
        row = int(event.y // tile_size)
        if column < 0 or event.x > int(canvas["width"]):
            logger.debug("Column out of bounds.")
            print("Column out of bounds: " + str(row) + " " + str(event.x) + "  " + str(canvas["height"]))
            return
        if row < 0 or event.y > int(canvas["height"]):
            logger.debug("Row out of bounds.")
            print("Row out of bounds: " + str(row) + "  " + str(event.y) + "  " + str(canvas["height"]))
            return

        tile_name = tile_label["text"].split(" ", 4)[2]
        tile_code = tile_label["text"].split(" ", 4)[3]
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, tile_size)
        
        canvas.delete(tile_image_matrix[row][column])
        tile_image_matrix[row][column] = canvas.create_image(
            column * tile_size - x_offset,
            row * tile_size - y_offset,
            image=self.tile_pallete_map[tile_code][1],
            anchor="nw",
        )
        tile_code_matrix[row][column] = tile_code
        self.save_needed = True
        self.button_save_full["state"] = tk.NORMAL

    def reset(self):
        logger.debug("Resetting..")
        for i in self.tree_levels.get_children():
            self.tree_levels.delete(i)
        try:
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()
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
            tree.insert(
                "", "end", text=str(pack_name), image=self.icon_folder
            )
            i = i + 1
        tree.insert(
            "", "end", text=str("[Create_New_Pack]"), image=self.icon_add
        )

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
        defaults_path = self.extracts_path
        for i in tree.get_children():
            tree.delete(i)

        tree.insert("", "end", values=str("<<BACK"), text=str("<<BACK"))
        if not str(lvl_dir).endswith("Arena"):
            tree.insert(
                "", "end", text=str("ARENA"), image=self.icon_folder
            )
        else:
            defaults_path = self.extracts_path / "Arena"
        # Load lvls frome extracts that selected pack doesn't have

        loaded_pack = tree.heading("#0")["text"].split("/")[0]
        # self.textures_dir = self.packs_path / loaded_pack / "Data/Textures"
        root = Path(self.packs_path / loaded_pack)
        pattern = "*.lvl"

        for filepath in glob.iglob(str(defaults_path) + "/***.lvl"):
            lvl_in_use = False
            path_in_str = str(filepath)
            lvl_name = os.path.basename(os.path.normpath(path_in_str))
            for path, _, files in os.walk(Path(root)):
                for name in files:
                    if fnmatch(name, pattern):
                        found_lvl = str(os.path.join(path, name))
                        if os.path.basename(os.path.normpath(found_lvl)) == str(
                            lvl_name
                        ):
                            lvl_in_use = True
                            tree.insert(
                                "", "end", text=str(lvl_name), image=self.lvl_icon(True)
                            )
            if not lvl_in_use:
                tree.insert(
                    "", "end", text=str(lvl_name), image=self.lvl_icon(False)
                )

    def load_pack_custom_lvls(self, tree, lvl_dir):
        self.reset()
        self.lvls_path = Path(lvl_dir)
        self.organize_pack()
        logger.debug("lvls_path = %s", lvl_dir)
        defaults_path = self.extracts_path
        for i in tree.get_children():
            tree.delete(i)

        tree.insert("", "end", values=str("<<BACK"), text=str("<<BACK"))
        if not str(lvl_dir).endswith("Arena"):
            tree.insert(
                "", "end", text=str("ARENA"), image=self.icon_folder
            )
        else:
            defaults_path = self.extracts_path / "Arena"


        for filepath in glob.iglob(str(lvl_dir) + "/***.lvl"):
            path_in_str = str(filepath)
            lvl_name = os.path.basename(os.path.normpath(path_in_str))
            if not (defaults_path / lvl_name).exists():
                tree.insert(
                    "", "end", text = str(lvl_name), image=self.lvl_icon(True)
                )
            
        
        

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
                tree.heading(
                    "#0", text=tree.heading("#0")["text"].split("/")[0]
                )
                self.loaded_pack = tree.heading("#0")["text"].split("/")[0]
                self.load_pack_lvls(
                    tree,
                    editor_type,
                    Path(self.packs_path / self.loaded_pack / "Data" / "Levels"),
                )
            else:
                self.load_packs(tree)
        elif (
            item_text == "ARENA"
            and tree.heading("#0")["text"] != "Select Pack"
        ):
            tree.heading(
                "#0", text=tree.heading("#0")["text"] + "/Arena"
            )
            self.loaded_pack = tree.heading("#0")["text"].split("/")[0]
            self.load_pack_lvls(
                tree,
                editor_type,
                Path(self.packs_path / self.loaded_pack / "Data" / "Levels" / "Arena")
            )
        elif item_text == "[Create_New_Pack]":
            logger.debug("Creating new pack")
            self.create_pack_dialog(tree)
            # self.tree_files.heading('#0', text='Select Pack', anchor='center')
        elif tree.heading("#0")["text"] == "Select Pack":
            for item in tree.selection():
                self.last_selected_file = item
                item_text = tree.item(item, "text")
                tree.heading("#0", text=item_text)
                self.loaded_pack = tree.heading("#0")["text"].split("/")[0]
                self.load_pack_lvls(
                    tree,
                    editor_type,
                    Path(self.packs_path / self.loaded_pack) / "Data" / "Levels"
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
            canvas.bind_all("<MouseWheel>", lambda event: self._on_mousewheel(event, hbar, vbar, canvas))
        else:
            canvas.bind_all("<Button-4>", lambda event: self._on_mousewheel(event, hbar, vbar, canvas))
            canvas.bind_all("<Button-5>", lambda event: self._on_mousewheel(event, hbar, vbar, canvas))

    def _unbind_from_mousewheel(self, _event, canvas):
        if is_windows():
            canvas.unbind_all("<MouseWheel>")
        else:
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

    def tile_pick(
        self, _event, button_row, button_col, tile_palette, tile_label, panel_sel
    ):  # When a tile is selected from the tile pallete
        selected_tile = tile_palette.scrollable_frame.grid_slaves(
            button_row, button_col
        )[0]
        panel_sel["image"] = selected_tile["image"]
        tile_label["text"] = "Primary Tile: " + selected_tile["text"]

    def tile_pick_secondary(
        self, _event, button_row, button_col, tile_palette, tile_label, panel_sel
    ):  # When a tile is selected from the tile pallete
        selected_tile = tile_palette.scrollable_frame.grid_slaves(
            button_row, button_col
        )[0]
        panel_sel["image"] = selected_tile["image"]
        tile_label["text"] = "Secondary Tile: " + selected_tile["text"]

    def suggested_tile_pick(
        self, suggested_tile, is_secondary, tile_palette, tile_label,
        tile_label_secondary, panel_sel, panel_sel_secondary, scale 
    ):
        tile = self.add_tilecode(
            suggested_tile, 100, "empty", tile_palette, tile_label, tile_label_secondary,
            panel_sel, panel_sel_secondary, scale
        )
        if not tile:
            return
        curr_panel_sel = None
        curr_tile_label = None
        prefix = ""
        if is_secondary:
            curr_panel_sel = panel_sel_secondary
            curr_tile_label = tile_label_secondary
            prefix = "Secondary Tile: "
        else:
            curr_panel_sel = panel_sel
            curr_tile_label = tile_label
            prefix = "Primary Tile: "
        curr_panel_sel["image"] = tile[1]
        curr_tile_label["text"] = prefix + tile[0]
        
    def get_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        logger.debug("%s codes left (%s)", len(self.usable_codes), codes)

    def dual_toggle(self):
        item_iid = self.tree_levels.selection()[0]
        parent_iid = self.tree_levels.parent(item_iid)  # gets selected room
        if parent_iid:
            room_name = self.tree_levels.item(item_iid, option="text")
            room_rows = self.tree_levels.item(item_iid, option="values")
            new_room_data = []

            tags = []
            tags.append(r"\!ignore")
            tags.append(r"\!flip")
            tags.append(r"\!onlyflip")
            tags.append(r"\!dual")
            tags.append(r"\!rare")
            tags.append(r"\!hard")
            tags.append(r"\!liquid")
            tags.append(r"\!purge")

            if self.var_dual.get() == 1:  # converts room into dual
                new_room_data.append(r"\!dual")
                for row in room_rows:
                    tag_row = False
                    new_row = ""
                    for tag in tags:
                        if row.startswith(tag):
                            tag_row = True
                    if not tag_row:
                        new_row = row + " "
                        for _char in row:
                            new_row += "0"
                        new_room_data.append(str(new_row))
                    else:
                        new_room_data.append(str(row))
            else:  # converts room into none dual
                msg_box = tk.messagebox.askquestion(
                    "Delete Dual Room?",
                    "Un-dualing this room will delete your background layer. This is not recoverable.\nContinue?",
                    icon="warning",
                )
                if msg_box == "yes":
                    for row in room_rows:
                        tag_row = False
                        new_row = ""
                        for tag in tags:
                            if str(row).startswith(tag):
                                tag_row = True
                        if not tag_row:
                            new_row = str(row).split(" ", 2)[0]
                        else:
                            if not row.startswith(r"\!dual"):
                                new_row = row
                        if new_row != "":
                            new_room_data.append(str(new_row))

            edited = self.tree_levels.insert(
                parent_iid,
                self.tree_levels.index(item_iid),
                text=room_name,
                values=new_room_data,
            )
            # Remove it from the tree
            self.tree_levels.delete(item_iid)
            self.tree_levels.selection_set(edited)
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

    def save_changes_full(self):
        if self.save_needed:
            try:
                tile_codes = TileCodes()
                level_chances = LevelChances()
                level_settings = LevelSettings()
                monster_changes = MonsterChances()
                level_templates = LevelTemplates()

                hard_floor_code = None
                for tilecode in self.tile_pallete_ref_in_use:
                    tile_codes.set_obj(
                        TileCode(
                            name=tilecode[0].split(" ", 1)[0],
                            value=tilecode[0].split(" ", 1)[1],
                            comment="",
                        )
                    )
                    if tilecode[0].split(" ", 1)[0] == "floor_hard":
                        hard_floor_code = tilecode[0].split(" ", 1)[1]

                for room_y in range(len(self.custom_editor_foreground_tile_codes) // 8):
                    for room_x in range(len(self.custom_editor_foreground_tile_codes[0]) // 10):
                        room_foreground = []
                        room_background = []
                        for row in range(8):
                            foreground_row = self.custom_editor_foreground_tile_codes[room_y * 8 + row]
                            background_row = self.custom_editor_background_tile_codes[room_y * 8 + row]
                            room_foreground.append("".join(foreground_row[room_x * 10:room_x * 10 + 10]))
                            room_background.append("".join(background_row[room_x * 10:room_x * 10 + 10]))
                        print(room_foreground)
                        room_settings = []
                        dual = (not hard_floor_code) or room_background != [hard_floor_code * 10 for _ in range(8)]
                        if dual:
                            room_settings.append(TemplateSetting.DUAL)
                            print("it's dual!")
                        template_chunks = [Chunk(
                            comment = None,
                            settings = room_settings,
                            foreground = room_foreground,
                            background = room_background if dual else [],
                        )]
                        level_templates.set_obj(
                            LevelTemplate(
                                name=self.current_save_format.room_template_format.format(y=room_y, x=room_x),
                                comment=self.lvl_biome,
                                chunks=template_chunks,
                            )
                        )
                old_level_file = self.current_level_full
                level_file = LevelFile(
                    old_level_file.comment,
                    old_level_file.level_settings,
                    tile_codes,
                    old_level_file.level_chances,
                    old_level_file.monster_chances,
                    level_templates,
                )

                if not os.path.exists(Path(self.lvls_path)):
                    os.makedirs(Path(self.lvls_path))
                save_path = self.current_level_path_full
                self.make_backup(save_path)
                logger.debug("Saving to %s", save_path)

                with Path(save_path).open("w", encoding="cp1252") as handle:
                    level_file.write(handle)

                logger.debug("Saved!")

                self.save_needed = False
                self.button_save_full["state"] = tk.DISABLED
                logger.debug("Saved")
            except Exception:  # pylint: disable=broad-except
                logger.critical("Failed to save level: %s", tb_info())
                _msg_box = tk.messagebox.showerror(
                    "Oops?",
                    "Error saving..",
                )
        else:
            logger.debug("No changes to save.")

    def save_changes(self):
        if self.save_needed:
            try:
                tags = []
                tags.append(r"\!ignore")
                tags.append(r"\!flip")
                tags.append(r"\!onlyflip")
                tags.append(r"\!dual")
                tags.append(r"\!rare")
                tags.append(r"\!hard")
                tags.append(r"\!liquid")
                tags.append(r"\!purge")
                tile_codes = TileCodes()
                level_chances = LevelChances()
                level_settings = LevelSettings()
                monster_chances = MonsterChances()
                level_templates = LevelTemplates()

                for tilecode in self.tile_pallete_ref_in_use:
                    tile_codes.set_obj(
                        TileCode(
                            name=tilecode[0].split(" ", 1)[0],
                            value=tilecode[0].split(" ", 1)[1],
                            comment="",
                        )
                    )

                bad_chars = ["[", "]", "'", '"']
                bad_chars_settings = ["[", "]", "'", '"', ","]
                for entry in self.tree.get_children():
                    values = self.tree.item(entry)["values"]
                    value_final = ""
                    for i in bad_chars_settings:
                        value_final = str(values[1]).replace(i, "")
                    level_settings.set_obj(
                        LevelSetting(
                            name=str(values[0]),
                            value=value_final,
                            comment=str(values[2]),
                        )
                    )

                for entry in self.tree_chances_monsters.get_children():
                    values = self.tree_chances_monsters.item(entry)["values"]
                    value_final = ""
                    for i in bad_chars:
                        value_final = str(values[1]).replace(i, "")
                    monster_chances.set_obj(
                        MonsterChance(
                            name=str(values[0]),
                            value=value_final,
                            comment=str(values[2]),
                        )
                    )

                for entry in self.tree_chances_levels.get_children():
                    values = self.tree_chances_levels.item(entry)["values"]
                    value_final = ""
                    for i in bad_chars:
                        value_final = str(values[1]).replace(i, "")
                    level_chances.set_obj(
                        LevelChance(
                            name=str(values[0]),
                            value=value_final,
                            comment=str(values[2]),
                        )
                    )

                for room_parent in self.tree_levels.get_children():
                    template_chunks = []
                    room_list_name = self.tree_levels.item(room_parent)["text"].split(
                        " ", 1
                    )[0]
                    room_list_comment = ""
                    if (
                        len(self.tree_levels.item(room_parent)["text"].split("//", 1))
                        > 1
                    ):
                        room_list_comment = self.tree_levels.item(room_parent)[
                            "text"
                        ].split("//", 1)[1]
                    for room in self.tree_levels.get_children(room_parent):
                        room_data = self.tree_levels.item(room, option="values")
                        room_name = self.tree_levels.item(room)["text"]
                        room_foreground = []
                        room_background = []
                        room_settings = []

                        for line in room_data:
                            row = []
                            back_row = []
                            tag_found = False
                            background_found = False
                            for tag in tags:
                                if str(line) == str(tag):  # this line is a tag
                                    tag_found = True
                            if not tag_found:
                                for char in str(line):
                                    if not background_found and str(char) != " ":
                                        row.append(str(char))
                                    elif background_found and str(char) != " ":
                                        back_row.append(str(char))
                                    elif char == " ":
                                        background_found = True
                            else:
                                room_settings.append(
                                    TemplateSetting(str(line.split("!", 1)[1]))
                                )
                                logger.debug("FOUND %s", line.split("!", 1)[1])

                            if not tag_found:
                                room_foreground.append(row)
                                if back_row != []:
                                    room_background.append(back_row)

                        template_chunks.append(
                            Chunk(
                                comment=room_name,
                                settings=room_settings,
                                foreground=room_foreground,
                                background=room_background,
                            )
                        )
                    level_templates.set_obj(
                        LevelTemplate(
                            name=room_list_name,
                            comment=room_list_comment,
                            chunks=template_chunks,
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
                   self.tree_files.item(item, image = self.lvl_icon(True))
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

        usable_codes = []
        for code in self.usable_codes_string:
            usable_codes.append(code)

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
                                self.tree_filesitemclick(self, self.tree_files, EditorType.VANILLA_ROOMS)
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
        item_iid = self.tree_levels.selection()[0]
        parent_iid = self.tree_levels.parent(item_iid)  # gets selected room
        try:
            if parent_iid:
                room_name = str(self.tree_levels.item(item_iid)["text"])
                # self.canvas.delete("all")
                # self.canvas_dual.delete("all")
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
                edited = self.tree_levels.insert(
                    parent_iid,
                    self.tree_levels.index(item_iid),
                    text=room_name,
                    values=room_save,
                )
                # Remove it from the tree
                self.tree_levels.delete(item_iid)
                self.tree_levels.selection_set(edited)
                # self.room_select(None)
                logger.debug("temp saved: \n%s", new_room_data)
                logger.debug("Changes remembered!")
                self.save_needed = True
                self.button_save["state"] = tk.NORMAL
            else:
                self.canvas.delete("all")
                self.canvas_dual.delete("all")
                self.canvas.grid_remove()
                self.canvas_dual.grid_remove()
                self.foreground_label.grid_remove()
                self.background_label.grid_remove()
        except Exception:  # pylint: disable=broad-except
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            self.canvas.grid_remove()
            self.canvas_dual.grid_remove()
            self.foreground_label.grid_remove()
            self.background_label.grid_remove()

    def toggle_list_hide(self):
        if self.button_hide_tree["text"] == "<<":
            self.tree_levels.grid_remove()
            self.vsb_tree_levels.grid_remove()
            self.editor_tab.columnconfigure(0, minsize=0)  # Column 0 = Level List
            self.button_hide_tree["text"] = ">>"
        else:
            self.tree_levels.grid()
            self.vsb_tree_levels.grid()
            self.editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
            self.button_hide_tree["text"] = "<<"

    def replace_tiles_dia(self):
        # Set up window
        win = PopupWindow("Replace Tiles", self.modlunky_config)

        replacees = []
        for tile in self.tile_pallete_ref_in_use:
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

    def replace_tiles(self, tile, new_tile, replace_where):
        if replace_where == "all rooms":
            for room_parent in self.tree_levels.get_children():
                for room in self.tree_levels.get_children(room_parent):
                    room_data = []
                    room_name = self.tree_levels.item(room, option="text")
                    room_rows = self.tree_levels.item(room, option="values")
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
                    # Put it back in with the upated values
                    edited = self.tree_levels.insert(
                        room_parent,
                        self.tree_levels.index(room),
                        text=str(room_name),
                        values=room_data,
                    )
                    # Remove it from the tree
                    self.tree_levels.delete(room)
                    if room == self.last_selected_room:
                        self.tree_levels.selection_set(edited)
                        self.last_selected_room = edited
                        self.room_select(None)
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

    def del_tilecode(self):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air",
            icon="warning",
        )
        if msg_box == "yes":
            tile_id = self.tile_label["text"].split(" ", 3)[2]
            tile_code = self.tile_label["text"].split(" ", 3)[3]
            if tile_id == r"empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            for room_parent in self.tree_levels.get_children():
                for room in self.tree_levels.get_children(room_parent):
                    room_data = []
                    room_name = self.tree_levels.item(room, option="text")
                    room_rows = self.tree_levels.item(room, option="values")
                    for row in room_rows:
                        new_row = ""
                        if not str(row).startswith(r"\!"):
                            for replace_code in row:
                                if replace_code == tile_code:
                                    replace_code = "0"
                                    new_row += "0"
                                else:
                                    new_row += str(replace_code)
                        else:
                            new_row = str(row)
                        room_data.append(new_row)
                    # Put it back in with the upated values
                    edited = self.tree_levels.insert(
                        room_parent,
                        self.tree_levels.index(room),
                        text=str(room_name),
                        values=room_data,
                    )
                    # Remove it from the tree
                    self.tree_levels.delete(room)
                    if room == self.last_selected_room:
                        self.tree_levels.selection_set(edited)
                        self.last_selected_room = edited
                        self.room_select(None)
            logger.debug("Replaced %s in all rooms with air/empty", tile_id)

            self.usable_codes.append(str(tile_code))
            logger.debug("%s is now available for use", tile_code)
            # adds tilecode back to list to be reused
            for id_ in self.tile_pallete_ref_in_use:
                if str(tile_id) == str(id_[0].split(" ", 2)[0]):
                    self.tile_pallete_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile_id)
            self.populate_tilecode_pallete(self.tile_pallete, self.tile_label, self.tile_label_secondary, self.panel_sel, self.panel_sel_secondary, self.mag)
            new_selection = self.tile_pallete_ref_in_use[0]
            if str(self.tile_label["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label["text"] = (
                    "Primary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel["image"] = new_selection[1]
            if str(self.tile_label_secondary["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label_secondary["text"] = (
                    "Secondary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel_secondary["image"] = new_selection[1]

            self.get_codes_left()
            self.save_needed = True
            self.button_save["state"] = tk.NORMAL
            self.check_dependencies()
        else:
            return

    def del_tilecode_secondary(self, tile_pallete, tile_label, tile_label_secondary, panel_sel, panel_sel_secondary):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air",
            icon="warning",
        )
        if msg_box == "yes":
            tile_id = self.tile_label_secondary["text"].split(" ", 3)[2]
            tile_code = self.tile_label_secondary["text"].split(" ", 3)[3]
            if tile_id == r"empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            for room_parent in self.tree_levels.get_children():
                for room in self.tree_levels.get_children(room_parent):
                    room_data = []
                    room_name = self.tree_levels.item(room, option="text")
                    room_rows = self.tree_levels.item(room, option="values")
                    for row in room_rows:
                        new_row = ""
                        if not str(row).startswith(r"\!"):
                            for replace_code in row:
                                if replace_code == tile_code:
                                    replace_code = "0"
                                    new_row += "0"
                                else:
                                    new_row += str(replace_code)
                        else:
                            new_row = str(row)
                        room_data.append(new_row)
                    # Put it back in with the upated values
                    edited = self.tree_levels.insert(
                        room_parent,
                        self.tree_levels.index(room),
                        text=str(room_name),
                        values=room_data,
                    )
                    # Remove it from the tree
                    self.tree_levels.delete(room)
                    if room == self.last_selected_room:
                        self.tree_levels.selection_set(edited)
                        self.last_selected_room = edited
                        self.room_select(None)
            logger.debug("Replaced %s in all rooms with air/empty", tile_code)

            self.usable_codes.append(str(tile_code))
            logger.debug("%s is now available for use", tile_code)
            # adds tilecode back to list to be reused
            for id_ in self.tile_pallete_ref_in_use:
                if str(tile_id) == str(id_[0].split(" ", 2)[0]):
                    self.tile_pallete_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile_id)
            self.populate_tilecode_pallete(self.tile_pallete, self.tile_label, self.tile_label_secondary, self.panel_sel, self.panel_sel_secondary, self.mag)
            new_selection = self.tile_pallete_ref_in_use[0]
            if str(self.tile_label["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label["text"] = (
                    "Primary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel["image"] = new_selection[1]
            if str(self.tile_label_secondary["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label_secondary["text"] = (
                    "Secondary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel_secondary["image"] = new_selection[1]

            self.get_codes_left()
            self.save_needed = True
            self.button_save["state"] = tk.NORMAL
            self.check_dependencies()
        else:
            return

    def del_tilecode_custom(self, tile_label, canvases, tile_image_matrices, tile_code_matrices):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air",
            icon="warning",
        )
        if msg_box == "yes":
            tile_id = tile_label["text"].split(" ", 4)[2]
            tile_code = tile_label["text"].split(" ", 4)[3]
            if tile_id == r"empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            new_tile = self.tile_pallete_map["0"]
            for matrix_index in range(len(tile_image_matrices)):
                tile_image_matrix = tile_image_matrices[matrix_index]
                tile_code_matrix = tile_code_matrices[matrix_index]
                canvas = canvases[matrix_index]
                for row in range(len(tile_code_matrix)):
                    for column in range(len(tile_code_matrix[row])):
                        if str(tile_code_matrix[row][column]) == str(tile_code):
                            canvas.delete(tile_image_matrix[row][column])
                            tile_code_matrix[row][column] = '0'
                            tile_image_matrix[row][column] = canvas.create_image(
                                column * self.custom_editor_zoom_level,
                                row * self.custom_editor_zoom_level,
                                image=new_tile[1],
                                anchor="nw"
                            )

            self.usable_codes.append(str(tile_code))
            logger.debug("%s is now available for use", tile_code)
            # adds tilecode back to list to be reused
            for id_ in self.tile_pallete_ref_in_use:
                if str(tile_code) == str(id_[0].split(" ", 2)[1]):
                    self.tile_pallete_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile_id)
            self.populate_tilecode_pallete(self.tile_pallete_custom, self.tile_label_custom, self.tile_label_secondary_custom, self.panel_sel_custom, self.panel_sel_secondary_custom, self.custom_editor_zoom_level)
            new_selection = self.tile_pallete_ref_in_use[0]
            if str(self.tile_label_custom["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label_custom["text"] = (
                    "Primary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel_custom["image"] = new_selection[1]
            if str(self.tile_label_secondary_custom["text"]).split(" ", 3)[2] == tile_id:
                self.tile_label_secondary_custom["text"] = (
                    "Secondary Tile: "
                    + str(new_selection[0]).split(" ", 2)[0]
                    + " "
                    + str(new_selection[0]).split(" ", 2)[1]
                )
                self.panel_sel_secondary_custom["image"] = new_selection[1]

            self.get_codes_left()
            self.save_needed = True
            self.button_save["state"] = tk.NORMAL
        else:
            return
        

    def add_tilecode(
        self, tile, percent, alt_tile, tile_palette, tile_label,
        tile_label_secondary, panel_sel, panel_sel_secondary, scale
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
            self.get_texture(new_tile_code, self.lvl_biome, self.lvl, scale)
        )

        # compares tile id to tile ids in pallete list
        for palette_tile in self.tile_pallete_ref_in_use:
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

        # count_row = 0
        # count_col = 0
        # for _ in self.tile_pallete_ref_in_use:
        #     if count_col == 7:
        #         count_col = -1
        #         count_row = count_row + 1
        #     count_col = count_col + 1

        ref_tile = []
        ref_tile.append(new_tile_code + " " + str(usable_code))
        ref_tile.append(tile_image)
        self.tile_pallete_ref_in_use.append(ref_tile)
        self.tile_pallete_map[usable_code] = ref_tile
        # new_tile = tk.Button(
        #     self.tile_pallete.scrollable_frame,
        #     text=str(
        #         new_tile_code + " " + str(usable_code)
        #     ),  # keep seperate by space cause I use that for splitting
        #     width=40,
        #     height=40,
        #     image=tile_image,
        # )
        # new_tile.grid(row=count_row, column=count_col)
        # new_tile.bind(
        #     "<Button-1>",
        #     lambda event, r=count_row, c=count_col: self.tile_pick(event, r, c),
        # )
        # new_tile.bind(
        #     "<Button-3>",
        #     lambda event, r=count_row, c=count_col: self.tile_pick_secondary(
        #         event, r, c
        #     ),
        # )
        self.populate_tilecode_pallete(tile_palette, tile_label, tile_label_secondary, panel_sel, panel_sel_secondary, scale)
        self.get_codes_left()
        self.save_needed = True
        self.button_save["state"] = tk.NORMAL
        # self.check_dependencies()
        return ref_tile

    def on_double_click(self, tree_view):
        # First check if a blank space was selected
        entry_index = tree_view.focus()
        if entry_index == "":
            return

        win = PopupWindow("Edit Entry", self.modlunky_config)
        win.columnconfigure(1, minsize=500)

        # Grab the entry's values
        for child in tree_view.get_children():
            if child == entry_index:
                values = tree_view.item(child)["values"]
                break

        col1_lbl = ttk.Label(win, text="Entry: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, values[0])  # Default is column 1's current value
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        col2_lbl = ttk.Label(win, text="Value: ")
        col2_ent = ttk.Entry(win)
        col2_ent.insert(0, values[1])  # Default is column 2's current value
        col2_lbl.grid(row=1, column=0, padx=2, pady=2, sticky="nse")
        col2_ent.grid(row=1, column=1, padx=2, pady=2, sticky="nsew")

        col3_lbl = ttk.Label(win, text="Comment: ")
        col3_ent = ttk.Entry(win)
        col3_ent.insert(0, values[2])  # Default is column 3's current value
        col3_lbl.grid(row=2, column=0, padx=2, pady=2, sticky="nse")
        col3_ent.grid(row=2, column=1, padx=2, pady=2, sticky="nsew")

        def update_then_destroy():
            if self.confirm_entry(
                tree_view, col1_ent.get(), col2_ent.get(), col3_ent.get()
            ):
                win.destroy()
                self.save_needed = True
                self.button_save["state"] = tk.NORMAL

        separator = ttk.Separator(win)
        separator.grid(row=3, column=0, columnspan=3, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=4, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Ok", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

    def confirm_entry(self, tree_view, entry1, entry2, entry3):
        ####
        # Whatever validation you need
        ####

        # Grab the current index in the tree
        current_index = tree_view.index(tree_view.focus())

        # Remove it from the tree
        self.delete_current_entry(tree_view)

        # Put it back in with the upated values
        tree_view.insert("", current_index, values=(entry1, entry2, entry3))
        self.save_needed = True

        return True

    def delete_current_entry(self, tree_view):
        curr = tree_view.focus()

        if curr == "":
            return

        tree_view.delete(curr)
        self.save_needed = True
        self.button_save["state"] = tk.NORMAL

    def populate_tilecode_pallete(
        self, tile_palette, tile_label, tile_label_secondary,
        panel_sel, panel_sel_secondary, scale
    ):
        # resets tile pallete to add them all back without the deleted one
        for widget in tile_palette.scrollable_frame.winfo_children():
            widget.destroy()
        count_row = 0
        count_col = -1
        self.tile_images = []
        used_tile_names = []
        for tile_keep in self.tile_pallete_ref_in_use:
            if count_col == 7:
                count_col = -1
                count_row = count_row + 1
            count_col = count_col + 1
            tile_name = tile_keep[0].split(" ", 2)[0]
            used_tile_names.append(tile_name)
            tile_image = ImageTk.PhotoImage(self.get_texture(tile_name, self.lvl_biome, self.lvl, 40))
            self.tile_images.append(tile_image)
            new_tile = tk.Button(
                tile_palette.scrollable_frame,
                text=str(tile_name)
                + " "
                + str(
                    tile_keep[0].split(" ", 2)[1]
                ),  # keep seperate by space cause I use that for splitting
                width=40,
                height=40,
                image=tile_image,
            )
            new_tile.grid(row=count_row, column=count_col)
            new_tile.bind(
                "<Button-1>",
                lambda event, r=count_row, c=count_col: self.tile_pick(event, r, c, tile_palette, tile_label, panel_sel),
            )
            new_tile.bind(
                "<Button-3>",
                lambda event, r=count_row, c=count_col: self.tile_pick_secondary(
                    event, r, c, tile_palette, tile_label_secondary, panel_sel_secondary
                ),
            )


        if self.tile_pallete_suggestions and len(self.tile_pallete_suggestions):
            count_col = -1
            tile_palette.scrollable_frame.rowconfigure(count_row+1, minsize=15)
            count_row = count_row + 2
            suggestions_label = ttk.Label(tile_palette.scrollable_frame, text="Suggested Tiles:")
            suggestions_label.grid(row=count_row, column=0, columnspan=5, sticky="nw")
            count_row = count_row + 1

            for tile_suggestion in self.tile_pallete_suggestions:
                if tile_suggestion in used_tile_names:
                    continue
                if count_col == 7:
                    count_col = -1
                    count_row = count_row + 1
                count_col = count_col + 1
                tile_image = ImageTk.PhotoImage(self.get_texture(tile_suggestion, self.lvl_biome, self.lvl, 40))
                self.tile_images.append(tile_image)
                new_tile = tk.Button(
                    tile_palette.scrollable_frame,
                    text=tile_suggestion,
                    width=40,
                    height=40,
                    image=tile_image
                )
                new_tile.grid(row=count_row, column=count_col)
                new_tile.bind(
                    "<Button-1>",
                    lambda event, ts=tile_suggestion: self.suggested_tile_pick(
                        ts, False, tile_palette, tile_label,
                        tile_label_secondary, panel_sel, panel_sel_secondary, scale 
                    )
                )
                new_tile.bind(
                    "<Button-3>",
                    lambda event, ts=tile_suggestion: self.suggested_tile_pick(
                        ts, True, tile_palette, tile_label,
                        tile_label_secondary, panel_sel, panel_sel_secondary, scale 
                    )
                )

    def go_back(self):
        msg_box = tk.messagebox.askquestion(
            "Exit Editor?",
            "Exit editor and return to start screen?\n Load data will be lost.",
            icon="warning",
        )
        if msg_box == "yes":
            self.editor_tab_control.grid_remove()
            self.lvl_editor_start_frame.grid()
            # self.tab_control.grid_remove()
            # self.tree_files.grid_remove()
            # # Resets widgets
            # self.scale["state"] = tk.DISABLED
            # self.button_replace["state"] = tk.DISABLED
            # self.button_clear["state"] = tk.DISABLED
            # self.combobox["state"] = tk.DISABLED
            # self.combobox_alt["state"] = tk.DISABLED
            # self.button_tilecode_del["state"] = tk.DISABLED
            # self.button_tilecode_del_secondary["state"] = tk.DISABLED
            # self.canvas.delete("all")
            # self.canvas_dual.delete("all")
            # self.canvas.grid_remove()
            # self.canvas_dual.grid_remove()
            # self.foreground_label.grid_remove()
            # self.background_label.grid_remove()
            # self.button_back.grid_remove()
            # self.button_save.grid_remove()
            # self.vsb_tree_files.grid_remove()
            # removes any old tiles that might be there from the last file
            for widget in self.tile_pallete.scrollable_frame.winfo_children():
                widget.destroy()

    def update_value(self, _event):
        self.scale_var.set(str(int(float(self.scale.get()))))
        if int(float(self.scale.get())) == 100:
            self.combobox_alt.grid_remove()
            self.combobox.grid(columnspan=2)
        else:
            self.combobox.grid(columnspan=1)
            self.combobox_alt.grid()

    def load_full_preview(self):
        self.list_preview_tiles_ref = []
        # sets default level size for levels that might not have a size variable like the challenge levels.
        # 8x8 is what I went with
        level_height = 8 * 8
        level_width = 8 * 10

        self.full_size = None
        if len(self.tree_files.selection()) > 0:
            for entry in self.tree.get_children():
                if self.tree.item(entry, option="values")[0] == "size":
                    self.full_size = self.tree.item(entry, option="values")[1]
                    logger.debug(
                        "Size found: %s", self.tree.item(entry, option="values")[1]
                    )
                    if self.full_size is not None:
                        level_height = int(self.full_size.split(", ")[1]) * 8
                        level_width = int(self.full_size.split(", ")[0]) * 10
                    else:
                        level_height = int(8)
                        level_width = int(8)
                    self.canvas_full.delete("all")
                    self.canvas_full_dual.delete("all")
                    self._draw_grid_full(level_width, level_height, self.canvas_full)
                    self._draw_grid_full(
                        level_width, level_height, self.canvas_full_dual
                    )
            # if self.full_size == None:
            #    self.canvas_full.grid_remove()
            #    self.canvas_full_dual.grid_remove()
            #    return  # don't even try cause there's no size parameter for the level lol
        else:
            self.canvas_full.grid_remove()
            self.canvas_full_dual.grid_remove()
            return

        self.canvas_full.grid()

        def flip_text(x_coord):
            return x_coord[::-1]

        for room_template in self.tree_levels.get_children():
            room_x = 0
            room_y = 0
            if self.tree_levels.item(room_template, option="text").startswith(
                "setroom"
            ):
                room_y = int(
                    self.tree_levels.item(room_template, option="text")
                    .split("-")[0]
                    .split("room")[1]
                )
            elif self.tree_levels.item(room_template, option="text").startswith(
                "challenge_"
            ):
                if (
                    len(self.tree_levels.item(room_template, option="text").split("-"))
                    == 2
                ):
                    room_y = int(
                        self.tree_levels.item(room_template, option="text")
                        .split("-")[0]
                        .split("challenge_")[1]
                    )
                else:
                    continue
            elif self.tree_levels.item(room_template, option="text").startswith(
                "palaceofpleasure_"
            ):
                room_y = int(
                    self.tree_levels.item(room_template, option="text")
                    .split("-")[0]
                    .split("palaceofpleasure_")[1]
                )
            else:
                continue

            flip_room = False
            if len(self.tree_levels.item(room_template, option="text").split("//")) > 0:
                room_x = int(
                    self.tree_levels.item(room_template, option="text")
                    .split("-")[1]
                    .split("//")[0]
                    .strip()
                )
            else:
                room_x = int(
                    self.tree_levels.item(room_template, option="text").split("-")[1]
                )

            logger.debug("%s", self.tree_levels.item(room_template, option="text"))
            logger.debug("Room pos: %sx%s", room_x, room_y)
            current_room_tiles = []
            current_room_tiles_dual = []
            layers = []

            if len(self.tree_levels.get_children(room_template)) != 0:
                template = self.tree_levels.get_children(room_template)[0]
                for cr_line in self.tree_levels.item(template, option="values"):
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

                # Create a grid of None to store the references to the tiles
                self.tiles_full = [
                    [None for _ in range(level_width)] for _ in range(level_height)
                ]  # tile image displays

                self.tiles_full_dual = [
                    [None for _ in range(level_width)] for _ in range(level_height)
                ]  # tile image displays

                currow = -1
                curcol = 0

                layers.append(current_room_tiles)
                layers.append(current_room_tiles_dual)

                for layer in layers:
                    canvas_to_fill = None
                    grid_storage = None
                    if layer == current_room_tiles:
                        canvas_to_fill = self.canvas_full
                        grid_storage = self.tiles_full
                    else:
                        canvas_to_fill = self.canvas_full_dual
                        grid_storage = self.tiles_full_dual
                    for room_row in layer:
                        curcol = 0
                        currow = currow + 1
                        tile_image_full = None
                        logger.debug("Room row: %s", room_row)
                        for block in str(room_row):
                            if str(block) != " ":
                                tile_name = ""
                                for _pallete_block in self.tile_pallete_ref_in_use:
                                    tiles = [
                                        c
                                        for c in self.tile_pallete_ref_in_use
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
                                                    Image.ANTIALIAS,
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

                                x_coord = 0
                                y_coord = 0
                                for tile_name_ref in self.draw_mode:
                                    if tile_name == str(tile_name_ref[0]):
                                        x_coord, y_coord = self.adjust_texture_xy(
                                            tile_image_full.width(),
                                            tile_image_full.height(),
                                            tile_name_ref[1],
                                        )
                                grid_storage[currow][
                                    curcol
                                ] = canvas_to_fill.create_image(
                                    (room_x * 10 * (self.mag_full))
                                    + curcol * self.mag_full
                                    - x_coord,
                                    (room_y * 8 * (self.mag_full))
                                    + currow * self.mag_full
                                    - y_coord,
                                    image=tile_image_full,
                                    anchor="nw",
                                )
                                _coords = (
                                    curcol * self.mag_full,
                                    currow * self.mag_full,
                                    curcol * self.mag_full + self.mag_full,
                                    currow * self.mag_full + self.mag_full,
                                )
                            curcol = curcol + 1

                            
    def _draw_grid_custom(self, cols, rows, theme, canvas):
        zoom_level = self.custom_editor_zoom_level
        canvas["width"] = (zoom_level * cols * 10) - 3
        canvas["height"] = (zoom_level * rows * 8) - 3

        lvl_bg = self.lvl_bgs.get(theme)
        if not lvl_bg:
            background = self.background_for_theme(theme)
            print(background)
            
            image = Image.open(background).convert("RGBA")
            image = image.resize((zoom_level * 10, zoom_level * 8), Image.BILINEAR)
            enhancer = ImageEnhance.Brightness(image)
            im_output = enhancer.enhance(1.0)
            lvl_bg = ImageTk.PhotoImage(im_output)
            self.lvl_bgs[theme] = lvl_bg
        for x in range(0, cols):
            for y in range(0, rows):
                canvas.create_image(x * zoom_level * 10, y * zoom_level * 8, image=lvl_bg, anchor="nw")

        # finishes by drawing grid on top
        for i in range(0, cols * 10 + 2):
            canvas.create_line(
                i * zoom_level,
                0,
                i * zoom_level,
                rows * 8 * zoom_level,
                fill="#F0F0F0",
            )
        for i in range(0, rows * 8):
            canvas.create_line(
                0,
                i * zoom_level,
                zoom_level * (cols * 10 + 2),
                i * zoom_level,
                fill="#F0F0F0",
            )



    def _draw_grid_full(self, cols, rows, canvas):
        # resizes canvas for grids
        self.mag_full = int(self.slider_zoom_full.get() / 2)

        canvas["width"] = (self.mag_full * cols) - 3
        canvas["height"] = (self.mag_full * rows) - 3
        # self.canvas_grids_full["width"] = (self.mag_full * cols) - 3 * 10
        # self.canvas_grids_full["height"] = (self.mag_full * rows) - 3 * 4 * 8
        # self.scrollable_canvas_frame_full["width"] = (self.mag_full * cols) - 3 * 10
        # self.scrollable_canvas_frame_full["height"] = (self.mag_full * rows) - 3 * 8
        # self.canvas_grids_full["width"] = (self.mag_full * cols) - 3 * 10
        # self.canvas_grids_full["height"] = (self.mag_full * rows) - 3 * 8

        self.cur_lvl_bg_path = (
            self.lvl_bg_path
        )  # store as a temp dif variable so it can switch back to the normal bg when needed

        try:
            file_id = self.tree_files.selection()[0]
            room_item = self.tree_levels.selection()[0]
            room_id = self.tree_levels.parent(
                room_item
            )  # checks which room is being opened to see if a special bg is needed
            factor = 1.0  # keeps image the same
            if self.lvl_bg_path == self.textures_dir / "bg_ice.png" and str(
                self.tree_levels.item(room_id, option="text")
            ).startswith(
                r"\.setroom1"
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
        except Exception as err:  # pylint: disable=broad-except
            logger.critical("Failed to draw full grid: %s", err)

        # finishes by drawing grid on top
        for i in range(0, cols + 2):
            canvas.create_line(
                i * self.mag_full,
                0,
                i * self.mag_full,
                rows * self.mag_full,
                fill="#F0F0F0",
            )
        for i in range(0, rows):
            canvas.create_line(
                0,
                i * self.mag_full,
                self.mag_full * (cols + 2),
                i * self.mag_full,
                fill="#F0F0F0",
            )

    def _draw_grid(self, cols, rows, canvas, dual):
        # resizes canvas for grids
        canvas["width"] = (self.mag * cols) - 3
        canvas["height"] = (self.mag * rows) - 3

        if not dual:  # applies normal bg image settings to main grid
            self.cur_lvl_bg_path = (
                self.lvl_bg_path
            )  # store as a temp dif variable so it can switch back to the normal bg when needed

            file_id = self.tree_files.selection()[0]
            room_item = self.tree_levels.selection()[0]
            room_id = self.tree_levels.parent(
                room_item
            )  # checks which room is being opened to see if a special bg is needed
            factor = 1.0  # keeps image the same
            if self.lvl_bg_path == self.textures_dir / "bg_ice.png" and str(
                self.tree_levels.item(room_id, option="text")
            ).startswith(
                r"\.setroom1"
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

            print(self.cur_lvl_bg_path)
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
            room_item = self.tree_levels.selection()[0]
            room_id = self.tree_levels.parent(
                room_item
            )  # checks which room is being opened to see if a special bg is needed
            factor = 0.6  # darkens the image
            if self.lvl_bg_path == self.textures_dir / "bg_ice.png":
                if str(self.tree_levels.item(room_id, option="text")).startswith(
                    r"\.mothership"
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
        item_iid = self.tree_levels.selection()[0]
        parent_iid = self.tree_levels.parent(item_iid)
        if parent_iid:
            self.last_selected_room = item_iid
            self.canvas.delete("all")
            self.canvas_dual.delete("all")
            current_settings = self.tree_levels.item(item_iid, option="values")[
                0
            ]  # Room settings
            current_room = self.tree_levels.item(
                item_iid, option="values"
            )  # Room foreground
            current_room_tiles = []
            current_settings = []

            for cr_line in current_room:
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
                        for _pallete_block in self.tile_pallete_ref_in_use:
                            tiles = [
                                c
                                for c in self.tile_pallete_ref_in_use
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
                                    x_coord, y_coord = self.adjust_texture_xy(
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
                                    x_coord, y_coord = self.adjust_texture_xy(
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
        self.usable_codes = []
        self.check_dependencies()
        for code in self.usable_codes_string:
            self.usable_codes.append(code)

        # removes any old tiles that might be there from the last file
        for widget in self.tile_pallete.scrollable_frame.winfo_children():
            widget.destroy()

        # removes any old rules that might be there from the last file
        for i in self.tree_chances_levels.get_children():
            self.tree_chances_levels.delete(i)

        # removes any old rules that might be there from the last file
        for i in self.tree_chances_monsters.get_children():
            self.tree_chances_monsters.delete(i)

        # removes any old rules that might be there from the last file
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.tree.delete(*self.tree.get_children())
        self.tree_levels.delete(*self.tree_levels.get_children())

        # Enables widgets to use
        self.scale["state"] = tk.NORMAL
        self.combobox["state"] = tk.NORMAL
        self.combobox_alt["state"] = tk.NORMAL
        self.button_tilecode_del["state"] = tk.NORMAL
        self.button_tilecode_del_secondary["state"] = tk.NORMAL
        self.button_replace["state"] = tk.NORMAL

        self.combobox_alt.grid_remove()
        self.scale.set(100)
        self.combobox.set(r"empty")
        self.combobox_alt.set(r"empty")

        self.tree_levels.bind("<ButtonRelease-1>", self.room_select)
        self.tile_pallete_ref_in_use = []

        self.lvl = lvl

        self.lvl_biome = "cave"  # cave by default, depicts what background and sprites will be loaded
        self.lvl_bg_path = self.textures_dir / "bg_cave.png"
        if (
            lvl.startswith("abzu.lvl")
            or lvl.startswith("lake")
            or lvl.startswith("tide")
            or lvl.startswith("end")
            or lvl.endswith("_tidepool.lvl")
        ):
            self.lvl_biome = "tidepool"
            self.lvl_bg_path = self.textures_dir / "bg_tidepool.png"
        elif (
            lvl.startswith("babylon")
            or lvl.startswith("hallofu")
            or lvl.endswith("_babylon.lvl")
            or lvl.startswith("palace")
            or lvl.startswith("tiamat")
        ):
            self.lvl_biome = "babylon"
            self.lvl_bg_path = self.textures_dir / "bg_babylon.png"
        elif lvl.startswith("basecamp"):
            self.lvl_biome = "cave"
        elif lvl.startswith("beehive"):
            self.lvl_biome = "beehive"
            self.lvl_bg_path = self.textures_dir / "bg_beehive.png"
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("jungle")
            or lvl.startswith("challenge_moon")
            or lvl.endswith("_jungle.lvl")
        ):
            self.lvl_biome = "jungle"
            self.lvl_bg_path = self.textures_dir / "bg_jungle.png"
        elif (
            lvl.startswith("challenge_star")
            or lvl.startswith("temple")
            or lvl.endswith("_temple.lvl")
        ):
            self.lvl_biome = "temple"
            self.lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif (
            lvl.startswith("challenge_sun")
            or lvl.startswith("sunken")
            or lvl.startswith("hundun")
            or lvl.startswith("ending_hard")
            or lvl.endswith("_sunkencity.lvl")
        ):
            self.lvl_biome = "sunken"
            self.lvl_bg_path = self.textures_dir / "bg_sunken.png"
        elif lvl.startswith("city"):
            self.lvl_biome = "gold"
            self.lvl_bg_path = self.textures_dir / "bg_gold.png"
        elif lvl.startswith("duat"):
            self.lvl_biome = "duat"
            self.lvl_bg_path = self.textures_dir / "bg_temple.png"
        elif lvl.startswith("egg"):
            self.lvl_biome = "eggplant"
            self.lvl_bg_path = self.textures_dir / "bg_eggplant.png"
        elif lvl.startswith("ice") or lvl.endswith("_icecavesarea.lvl"):
            self.lvl_biome = "ice"
            self.lvl_bg_path = self.textures_dir / "bg_ice.png"
        elif lvl.startswith("olmec"):
            self.lvl_biome = "jungle"
            self.lvl_bg_path = self.textures_dir / "bg_stone.png"
        elif lvl.startswith("vlad"):
            self.lvl_biome = "volcano"
            self.lvl_bg_path = self.textures_dir / "bg_vlad.png"
        elif lvl.startswith("volcano") or lvl.endswith("_volcano.lvl"):
            self.lvl_biome = "volcano"
            self.lvl_bg_path = self.textures_dir / "bg_volcano.png"

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
        levels = []
        if not lvl.startswith("base"):
            if Path(self.lvls_path / "generic.lvl").is_dir():
                levels.append(LevelFile.from_path(Path(self.lvls_path / "generic.lvl")))
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "generic.lvl")
                )
        if lvl.startswith("base"):
            if Path(self.lvls_path / "basecamp.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "basecamp.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "basecamp.lvl")
                )
        elif lvl.startswith("cave"):
            if Path(self.lvls_path / "dwellingarea.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "dwellingarea.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "dwellingarea.lvl")
                )
        elif (
            lvl.startswith("blackmark")
            or lvl.startswith("beehive")
            or lvl.startswith("challenge_moon")
        ):
            if Path(self.lvls_path / "junglearea.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "junglearea.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "junglearea.lvl")
                )
        elif lvl.startswith("vlads"):
            if Path(self.lvls_path / "volcanoarea.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "volcanoarea.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "volcanoarea.lvl")
                )
        elif lvl.startswith("lake") or lvl.startswith("challenge_star"):
            if Path(self.lvls_path / "tidepoolarea.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "tidepoolarea.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "tidepoolarea.lvl")
                )
        elif (
            lvl.startswith("hallofush")
            or lvl.startswith("challenge_star")
            or lvl.startswith("babylonarea_1")
            or lvl.startswith("palace")
        ):
            if Path(self.lvls_path / "babylonarea.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "babylonarea.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "babylonarea.lvl")
                )
        elif lvl.startswith("challenge_sun"):
            if Path(self.lvls_path / "sunkencityarea.lvl").is_dir():
                levels.append(
                    LevelFile.from_path(Path(self.lvls_path / "sunkencityarea.lvl"))
                )
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "sunkencityarea.lvl")
                )
        elif lvl.startswith("end"):
            if Path(self.lvls_path / "ending.lvl").is_dir():
                levels.append(LevelFile.from_path(Path(self.lvls_path / "ending.lvl")))
            else:
                logger.debug(
                    "local dependency lvl not found, attempting load from extracts"
                )
                levels.append(
                    LevelFile.from_path(Path(self.extracts_path) / "ending.lvl")
                )
        levels.append(LevelFile.from_path(Path(lvl_path)))

        level = None
        for level in levels:
            logger.debug("%s loaded.", level.comment)
            level_tilecodes = level.tile_codes.all()

            for tilecode in level_tilecodes:
                tilecode_item = []
                tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

                img = self.get_texture(tilecode.name, self.lvl_biome, lvl, self.mag)

                tilecode_item.append(ImageTk.PhotoImage(img))
                self.panel_sel["image"] = tilecode_item[1]
                self.tile_label["text"] = "Primary Tile: " + tilecode_item[0]
                self.panel_sel_secondary["image"] = tilecode_item[1]
                self.tile_label_secondary["text"] = (
                    "Secondary Tile: " + tilecode_item[0]
                )

                for i in self.tile_pallete_ref_in_use:
                    if str(i[0]).split(" ", 1)[1] == str(tilecode.value):
                        self.tile_pallete_ref_in_use.remove(i)

                for i in self.usable_codes:
                    if str(i) == str(tilecode.value):
                        self.usable_codes.remove(i)

                self.tile_pallete_ref_in_use.append(tilecode_item)

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
                        for code_in_use in self.tile_pallete_ref_in_use
                    ):
                        for i in self.usable_codes:
                            if str(i) == str(need[0]):
                                self.usable_codes.remove(i)
                        tilecode_item = []
                        tilecode_item.append(str(need[1]) + " " + str(need[0]))

                        img = self.get_texture(str(need[1]), self.lvl_biome, lvl, self.mag)

                        tilecode_item.append(ImageTk.PhotoImage(img))
                        self.tile_pallete_ref_in_use.append(tilecode_item)
        self.populate_tilecode_pallete(self.tile_pallete, self.tile_label, self.tile_label_secondary, self.panel_sel, self.panel_sel_secondary, self.mag)


        level_rules = level.level_settings.all()
        self.full_size = None
        bad_chars = ["[", "]", '"', "'", "(", ")"]
        for rules in level_rules:
            value_final = str(rules.value)
            for i in bad_chars:
                value_final = value_final.replace(i, "")
            self.tree.insert(
                "",
                "end",
                text="L1",
                values=(str(rules.name), value_final, str(rules.comment)),
            )

        level_chances = level.monster_chances.all()
        for rules in level_chances:
            self.tree_chances_monsters.insert(
                "",
                "end",
                text="L1",
                values=(
                    str(rules.name),
                    str(rules.value)
                    .strip("[")
                    .strip("]")
                    .strip("(")
                    .strip(")")
                    .strip('"'),
                    str(rules.comment),
                ),
            )

        level_monsters = level.level_chances.all()
        for rules in level_monsters:
            self.tree_chances_levels.insert(
                "",
                "end",
                text="L1",
                values=(
                    str(rules.name),
                    str(rules.value)
                    .strip("[")
                    .strip("]")
                    .strip("(")
                    .strip(")")
                    .strip('"'),
                    str(rules.comment),
                ),
            )

        level_templates = level.level_templates.all()

        for template in level_templates:
            template_comment = ""
            if str(template.comment) != "":
                template_comment = "// " + str(template.comment)
            entry = self.node = self.tree_levels.insert(
                "", "end", text=str(template.name) + "   " + template_comment
            )
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

                self.node = self.tree_levels.insert(
                    entry, "end", values=room_string, text=str(room_name)
                )

    def read_custom_lvl_file(self, lvl):
        self.usable_codes = []
        for code in self.usable_codes_string:
            self.usable_codes.append(code)

        level = LevelFile.from_path(Path(self.lvls_path) / lvl)
        self.lvl = lvl
        self.current_level_full = level
        self.current_level_path_full = Path(self.lvls_path) / lvl
        self.current_save_format = self.read_save_format(level)
        if not self.current_save_format:
            self.show_format_error_dialog(lvl)
            return

        print(self.current_save_format.__dict__)

        self.combobox_custom["state"] = tk.NORMAL
        self.button_tilecode_del_custom["state"] = tk.NORMAL
        self.button_tilecode_del_secondary_custom["state"] = tk.NORMAL
        self.combobox_custom.set("empty")

        theme = self.read_theme(level, self.current_save_format)
        self.lvl_biome = theme
        background = self.background_for_theme(theme)

        self.tile_pallete_ref_in_use = []
        self.tile_pallete_map = {}
        hard_floor_code = None
        scale = self.custom_editor_zoom_level / 50
        for tilecode in level.tile_codes.all():
            tilecode_item = []
            tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

            img = self.get_texture(tilecode.name, theme, lvl, self.custom_editor_zoom_level)

            tilecode_item.append(ImageTk.PhotoImage(img))#.resize((int(img.width * scale), int(img.height * scale)), Image.ANTIALIAS).convert("RGBA")))
            
            self.usable_codes.remove(tilecode.value)
            self.tile_pallete_ref_in_use.append(tilecode_item)
            self.tile_pallete_map[tilecode.value] = tilecode_item
            if str(tilecode.name) == "floor_hard":
                hard_floor_code = tilecode.value

        if hard_floor_code is None:
            if self.usable_codes.count('X') > 0:
                hard_floor_code = 'X'
            else:
                hard_floor_code = self.usable_codes[0]
            self.usable_codes.remove(hard_floor_code)
            tilecode_item = ["floor_hard " + str(hard_floor_code), ImageTk.PhotoImage(self.get_texture("floor_hard", theme, lvl, self.custom_editor_zoom_level))]#.resize((int(img.width * scale), int(img.height * scale)), Image.ANTIALIAS).convert("RGBA"))]
            self.tile_pallete_ref_in_use.append(tilecode_item)
            self.tile_pallete_map[hard_floor_code] = tilecode_item

        secondary_backup_index = 0

        # If there is a "1" tile code, guess it is a good default tile since it is often the floor.
        if self.tile_pallete_map['1']:
            tile = self.tile_pallete_map['1']
            self.panel_sel_custom["image"] = tile[1]
            self.tile_label_custom["text"] = "Primary Tile: " + tile[0]
        elif len(self.tile_pallete_ref_in_use) > 0:
            tile = self.tile_pallete_ref_in_use[0]
            self.panel_sel_custom["image"] = tile[1]
            self.tile_label_custom["text"] = "Primary Tile: " + tile[0]
            secondary_backup_index = 1


        # If there is a "0" tile code, guess it is a good default secondary tile since it is often the empty tile.
        if self.tile_pallete_map['0']:
            tile = self.tile_pallete_map['0']
            self.panel_sel_secondary_custom["image"] = tile[1]
            self.tile_label_secondary_custom["text"] = "Secondary Tile: " + tile[0]
        elif len(self.tile_pallete_ref_in_use) > secondary_backup_index:
            tile = self.tile_pallete_ref_in_use[secondary_backup_index]
            self.panel_sel_secondary_custom["image"] = tile[1]
            self.tile_label_secondary_custom["text"] = "Secondary Tile: " + tile[0]
        elif len(self.tile_pallete_ref_in_use) > 0:
            tile = self.tile_pallete_ref_in_use[0]
            self.panel_sel_secondary_custom["image"] = tile[1]
            self.tile_label_secondary_custom["text"] = "Secondary Tile: " + tile[0]
        
        self.tile_pallete_suggestions = self.suggested_tiles_for_theme(theme)
        self.populate_tilecode_pallete(self.tile_pallete_custom, self.tile_label_custom, self.tile_label_secondary_custom, self.panel_sel_custom, self.panel_sel_secondary_custom, self.custom_editor_zoom_level)

        rooms = [[None for _ in range(8)] for _ in range(15)]
        template_regex = "^" + self.current_save_format.room_template_format.format(y="(?P<y>\d+)", x="(?P<x>\d+)") + "$"
        print(template_regex)
        for template in level.level_templates.all():
            match = re.search(template_regex, template.name)
            if match is not None:
                x = int(match.group('x'))
                y = int(match.group('y'))
                rooms[y][x] = template
        filtered_rooms = []
        for row in rooms:
            newrow = list(filter(lambda room: room is not None, row))
            if len(newrow) > 0:
                filtered_rooms.append(newrow)
            else:
                break
            
        height = len(filtered_rooms)
        width = len(filtered_rooms[0] or [])

        self.custom_level_canvas_foreground.delete("all")
        self.custom_level_canvas_background.delete("all")
        self._draw_grid_custom(width, height, theme, self.custom_level_canvas_foreground)
        self._draw_grid_custom(width, height, theme, self.custom_level_canvas_background)

        foreground_tiles = ["" for _ in range(height * 8)]
        background_tiles = ["" for _ in range(height * 8)]
        

        for i, row in enumerate(filtered_rooms):
            for template in row:
                room = template.chunks[0]
                for line_index, line in enumerate(room.foreground):
                    index = i * 8 + line_index
                    foreground_tiles[index] = foreground_tiles[index] + "".join(line)
                    if room.background is not None and len(room.background) > line_index:
                        background_tiles[index] = background_tiles[index] + "".join(room.background[line_index])
                    else:
                        background_tiles[index] = background_tiles[index] + hard_floor_code * 10



        def draw_layer(layer, canvas, tile_images, tile_codes):
            for row_index, room_row in enumerate(layer):
                for tile_index, tile in enumerate(str(room_row)):
                    tilecode = self.tile_pallete_map[tile]
                    tile_name = tilecode[0].split(" ", 1)[0]
                    tile_image = tilecode[1]
                    x_offset = 0
                    y_offset = 0
                    for tile_name_ref in self.draw_mode:
                        if tile_name == str(tile_name_ref[0]):
                            x_offset, y_offset = self.adjust_texture_xy(
                                tile_image.width(),
                                tile_image.height(),
                                tile_name_ref[1],
                                self.custom_editor_zoom_level
                            )
                    tile_images[row_index][tile_index] = canvas.create_image(
                        tile_index * self.custom_editor_zoom_level - x_offset,
                        row_index * self.custom_editor_zoom_level - y_offset,
                        image=tile_image,
                        anchor="nw"
                    )
                    tile_codes[row_index][tile_index] = tile

        self.custom_editor_foreground_tile_images = [
            [None for _ in range(width * 10)] for _ in range(height * 8)
        ]
        self.custom_editor_background_tile_images = [
            [None for _ in range(width * 10)] for _ in range(height * 8)
        ]
        self.custom_editor_foreground_tile_codes = [
            [None for _ in range(width * 10)] for _ in range(height * 8)
        ]
        self.custom_editor_background_tile_codes = [
            [None for _ in range(width * 10)] for _ in range(height * 8)
        ]

        draw_layer(
            foreground_tiles,
            self.custom_level_canvas_foreground,
            self.custom_editor_foreground_tile_images,
            self.custom_editor_foreground_tile_codes)
        draw_layer(
            background_tiles,
            self.custom_level_canvas_background,
            self.custom_editor_background_tile_images,
            self.custom_editor_background_tile_codes)

        # print(background_tiles)

        # Load scrolled to the center.
        # self.custom_level_canvas.configure(scrollregion=(0, 0, self.custom_editor_zoom_level * 50 - 3, self.custom_editor_zoom_level * 50 - 3))
        # self.custom_level_canvas.after(10, self.custom_level_canvas.xview_moveto, .3)
        # self.custom_level_canvas.yview_moveto(.5)

    def read_save_format(self, level):
        valid_save_formats = [self.default_save_format] + self.custom_save_formats + self.base_save_formats
        for save_format in valid_save_formats:
            for template in level.level_templates.all():
                if template.name == save_format.room_template_format.format(y=0, x=0):
                    return save_format
    
    def read_theme(self, level, save_format):
        for template in level.level_templates.all():
            if template.name == save_format.room_template_format.format(y=0, x=0):
                return template.comment or "cave"
        return "cave"
            
    def background_for_theme(self, theme):
        def background_file(theme):
            if theme == "cave":
                return "bg_cave.png"
            elif theme == "tidepool":
                return "bg_tidepool.png"
            elif theme == "babylon":
                return "bg_babylon.png"
            elif theme == "jungle":
                return "bg_jungle.png"
            elif theme == "temple":
                return "bg_temple.png"
            elif theme == "sunken":
                return "bg_sunken.png"
            elif theme == "gold":
                return "bg_gold.png"
            elif theme == "duat":
                return "bg_temple.png"
            elif theme == "eggplant":
                return "bg_eggplant.png"
            elif theme == "ice":
                return "bg_ice.png"
            elif theme == "olmec":
                return "bg_stone.png"
            elif theme == "volcano":
                return "bg_volcano.png"
            return "bg_cave.png"

        return self.textures_dir / background_file(theme)

    def suggested_tiles_for_theme(self, theme):
        common_tiles = [
             "floor", "empty", "floor%50", "minewood_floor", "floor_hard",
             "floor_hard%50%floor", "push_block", "ladder", "ladder_plat",
             "door", "door2", "door2_secret",
             "locked_door", "treasure", "treasure_chest", "treasure_vaultchest",
        ]
        def theme_tiles(theme):
            beehive_tiles = [
                "beehive_floor", "beehive_floor%50", "honey_upwards", "honey_downwards",
                "bee",
            ]
            if theme == "cave":
                return [
                    "bone_block", "platform",
                    "arrow_trap", "totem_trap", "spikes", "snake",
                    "bat", "skeleton", "caveman", "caveman_asleep", "caveman_asleep%50",
                    "scorpion", "mole", "lizard", "critter_dungbeetle",
                    "cookfire", "turkey", "yang", "cavemanboss", "autowalltorch",
                    "litwalltorch", "ghist_shopkeeper", "ghist_door2",
                ]
            elif theme == "volcano":
                return [
                    "powder_keg", "timed_powder_keg",
                    "falling_platform", "chain_ceiling", "chainandblocks_ceiling",
                    "spikeball_trap", "conveyorbelt_left", "conveyorbelt_right",
                    "factory_generator", "robot", "imp", "firebug", "caveman",
                    "caveman_asleep", "lavamander", "bat", "vampire", "vlad", "oldhunter", "critter_snail",
                    "lava", "vlad_floor", "nonreplaceable_babylon_floor", "drill",
                    "udjat_socket", "slidingwall_switch", "slidingwall_ceiling", "crown_statue",
                ]
            elif theme == "jungle":
                return [
                    "stone_floor", "vine", "growable_vine", "spikes", "bush_block",
                    "thorn_vine", "jungle_spear_trap", "tree_base",
                    "cookfire", "caveman", "mantrap", "witchdoctor", "tikiman", "mosquito",
                    "giant_spider", "hangspider", "bat", "monkey", "critter_butterfly", "snap_trap",
                ] + beehive_tiles
            elif theme == "olmec":
                return [
                    "stone_floor", "crate_parachute", "storage_guy",
                    "storage_floor", "autowalltorch", "olmec", "ankh", "pillar",
                    "critter_crab", "critter_locust",
                ]
            elif theme == "tidepool":
                return [
                    "pagoda_floor", "pagoda_floor%50%floor", "climbing_pole",
                    "growable_climbing_pole", "pagoda_platform", "spikes", "bone_block",
                    "powder_keg", "water", "jiangshi", "assassin", "octopus",
                    "hermitcrab", "crabman", "flying_fish", "critter_fish", "critter_anchovy",
                    "critter_crab", "giantclam", "fountain_head", "fountain_drain",
                    "slidingwall_switch", "slidingwall_ceiling", "minewood_floor", "excalibur",
                    "excalibur_stone", "haunted_corpse",
                ]
            elif theme == "temple":
                return [
                    "quicksand", "temple_floor", "temple_floor%50", "pot", "crushtrap",
                    "crushtraplarge", "catmummy", "cobra", "crocman", "anubis", "mummy",
                    "sorceress", "necromancer", "critter_locust",
                ] + beehive_tiles
            elif theme == "ice":
                return [
                    "minewood_floor", "icefloor", "icefloor%50", "spikes", "upsidedown_spikes",
                    "falling_platform", "thinice", "spring_trap", "forcefield", "timed_forcefield",
                    "forcefield_top", "litwalltorch", "autowalltorch", "cookfire", "landmine",
                    "storage_guy", "storage_floor", "eggplant_altar", "moai_statue",
                    "eggplant_child", "mothership_floor", "plasma_cannon", "alienqueen",
                    "shopkeeper_vat", "alien_generator", "alien", "ufo", "yeti", "empty_mech",
                    "critter_penguin", "critter_firefly",
                ]
            elif theme == "babylon":
                return [
                    "babylon_floor", "babylon_floor%50%floor", "laser_trap", "spark_trap",
                    "forcefield", "timed_forcefield", "forcefield_top", "elevator", "zoo_exhibit",
                    "litwalltorch", "mushroom_base", "lava", "lava%50%floor", "lamassu", "olmite",
                    "ufo", "empty_mech", "critter_drone",
                    "ushabti", "palace_floor", "palace_entrance",
                    "palace_table", "palace_table_tray", "palace_chandelier", "palace_candle",
                    "palace_bookcase", "stone_floor", "bone_block", "madametusk", "bodyguard",
                ]
            elif theme == "sunken":
                return [
                    "sunken_floor", "sunken_floor%50", "spikes", "pipe", "regenerating_block",
                    "bigspear_trap", "bone_block", "sticky_trap", "storage_guy", "storage_floor",
                    "autowalltorch", "mother_statue", "eggplant_door", "giant_frog", "guts_floor",
                    "water", "frog", "firefrog", "tadpole", "giantfly", "critter_slime", "skull_drop_trap",
                    "eggsac",
                ]
            elif theme == "gold":
                return [
                    "quicksand", "cog_floor", "cog_floor%50", "crushtrap", "crushtraplarge",
                    "slidingwall_switch", "slidingwall_ceiling",
                    "crocman", "leprechaun", "mummy", "cobra", "sorceress", "critter_locust",
                ]
            elif theme == "duat":
                return [
                    "duat_floor", "duat_floor%50", "chain_ceiling", "lava", "ammit%50",
                    "crocman", "snake", "cobra", "osiris", "anubis2",
                ]
            elif theme == "eggplant":
                return [
                    "pagoda_floor", "pagoda_floor%50", "pagoda_platform", "slidingwall_switch",
                    "slidingwall_ceiling", "fountain_head", "fountain_drain", "water",
                    "vine", "growable_vine", "jumpdog", "minister", "yama", "empress_grave",
                ]
            return []
        return common_tiles + theme_tiles(theme)

    def show_format_error_dialog(self, lvl):
            win = PopupWindow("Couldn't find room templates", self.modlunky_config)
            message = ttk.Label(win, text="Create a new room template format to load this level file?\n{x} and {y} are the coordinates of the room.\n")
            name_label = ttk.Label(win, text="Name: ")
            name_entry = ttk.Entry(win, foreground = 'gray')
            format_label = ttk.Label(win, text="Format: ")
            format_entry = ttk.Entry(win, foreground = 'gray')
            win.columnconfigure(1, weight=1)
            message.grid(row=0, column=0, columnspan=2, sticky="nswe")
            name_label.grid(row=1, column=0, sticky="nse")
            name_entry.grid(row=1, column=1, sticky="nswe")
            format_label.grid(row=2, column=0, sticky="nse")
            format_entry.grid(row=2, column=1, sticky="nswe")
            name_entry.insert(0, "Optional")
            format_entry.insert(0, "setroom{y}_{x}")
            name_entry_changed = False
            format_entry_changed = False
            
            def focus_name(event):
                nonlocal name_entry_changed
                if name_entry_changed:
                    return
                name_entry.delete('0', 'end')
                name_entry.config(foreground = 'black')
            def focus_format(event):
                nonlocal format_entry_changed
                if format_entry_changed:
                    return
                format_entry.delete('0', 'end')
                format_entry.config(foreground = 'black')
            def defocus_name(event):
                nonlocal name_entry_changed
                if str(name_entry.get()) == "":
                    name_entry_changed = False
                    name_entry.insert(0, "Optional")
                    name_entry.config(foreground = 'gray')
                else:
                    name_entry_changed = True
            def defocus_format(event):
                nonlocal format_entry_changed
                if str(format_entry.get()) == "":
                    format_entry_changed = False
                    format_entry.insert(0, "setroom{y}_{x}")
                    format_entry.config(foreground = 'gray')
                else:
                    format_entry_changed = True

            name_entry.bind("<FocusIn>", focus_name)
            name_entry.bind("<FocusOut>", defocus_name)
            format_entry.bind("<FocusIn>", focus_format)
            format_entry.bind("<FocusOut>", defocus_format)

            add_vanilla_var = tk.IntVar()
            add_vanilla_var.set(True)
            add_vanilla_label = ttk.Label(win, text="Include vanilla setrooms:")
            add_vanilla_check = ttk.Checkbutton(win, variable=add_vanilla_var)
            add_vanilla_label.grid(row=3, column=0, sticky="nse")
            add_vanilla_check.grid(row=3, column=1, sticky="nsw")

            add_vanilla_tip = ttk.Label(win, text="It is recommended to include vanilla setrooms.\nThis setting adds setrooms for some themes which require them.\nThere could be errors if not using this in some themes.")
            add_vanilla_tip.grid(row=4, column=0, columnspan=2, sticky="nswe")

            win.rowconfigure(5, minsize=20)

            buttons = ttk.Frame(win)
            buttons.grid(row=6, column=0, columnspan=2, sticky="nswe")
            buttons.columnconfigure(0, weight=1)
            buttons.columnconfigure(1, weight=1)

            def continue_open():
                format = str(format_entry.get())
                name = str(name_entry.get()) if name_entry_changed else format
                if format == "" or name == "" or format == "setroom{y}-{x}" or format == "setroom{x}-{y}":
                    return
                save_format = CustomLevelSaveFormat(name, format, bool(add_vanilla_var.get()))
                win.destroy()
                self.add_save_format(save_format)
                self.read_custom_lvl_file(lvl)

            continue_button = ttk.Button(buttons, text="Continue", command=continue_open)
            continue_button.grid(row=0, column=0, sticky="nswe")


            cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
            cancel_button.grid(row=0, column=1, sticky="nswe")

    def add_save_format(self, save_format):
        self.custom_save_formats.append(save_format)
        self.modlunky_config.config_file.custom_level_editor_custom_save_formats = list(map(
            lambda save_format: save_format.toJSON(),
            self.custom_save_formats
        ))
        self.modlunky_config.config_file.save()

    @staticmethod
    def adjust_texture_xy(width, height, mode, scale=50):
        # slight adjustments of textures for tile preview
        # 1 = lower half tile
        # 2 = draw from bottom left
        # 3 = center
        # 4 = center to the right
        # 5 = draw bottom left + raise 1 tile
        # 6 = position doors
        # 7 = draw bottom left + raise half tile
        # 8 = draw bottom left + lowere 1 tile
        # 9 = draw bottom left + raise 1 tile + move left 1 tile
        # 10 = draw bottom left + raise 1 tile + move left 1 tile
        # 11 = move left 1 tile
        # 12 = raise 1 tile
        # 13 = draw from bottom left + move left half tile
        # 14 = precise bottom left for yama
        x_coord = 0
        y_coord = 0
        scale_factor = scale / 50
        print(scale)
        print(scale_factor)
        if mode == 1:
            y_coord = (height * -1) / 2
        elif mode == 2:
            y_coord = height / 2
        elif mode == 3:
            x_coord = width / 3.2
            y_coord = height / 2
        elif mode == 4:
            x_coord = (width * -1) / 2
        elif mode == 5:
            y_coord = height / 2 + 50 * scale_factor
        elif mode == 6:
            x_coord = 25 * scale_factor
            y_coord = 22 * scale_factor
        elif mode == 7:
            y_coord = height / 2 + 25 * scale_factor
        elif mode == 8:
            y_coord = (height / 2 + 50 * scale_factor) * -1
        elif mode == 9:
            y_coord = height / 2 + 50 * scale_factor
            x_coord = 75 * scale_factor
        elif mode == 10:
            y_coord = height / 2 + 100 * scale_factor
        elif mode == 11:
            x_coord = 50 * scale_factor
        elif mode == 12:
            y_coord = 50 * scale_factor
        elif mode == 13:
            y_coord = height / 2
            x_coord = 25 * scale_factor
        elif mode == 14:
            y_coord = height - 50 * scale_factor
            x_coord = 100 * scale_factor
        return int(x_coord), int(y_coord)

    def get_texture(self, tile, biome, lvl, scale):
        def get_specific_tile(tile):
            img_spec = None

            if (
                lvl.startswith("generic")
                or lvl.startswith("challenge")
                or lvl.startswith("testing")
                or lvl.startswith("beehive")
                or lvl.startswith("palace")
            ):
                if tile == "floor":
                    img_spec = self._sprite_fetcher.get("generic_floor", str(biome))
                elif tile == "styled_floor":
                    img_spec = self._sprite_fetcher.get(
                        "generic_styled_floor", str(biome)
                    )
            # base is weird with its tiles so I gotta get specific here
            if lvl.startswith("base"):
                if tile == "floor":
                    img_spec = self._sprite_fetcher.get("floor", "cave")
            if lvl.startswith("duat"):  # specific floor hard for this biome
                if tile == "floor_hard":
                    img_spec = self._sprite_fetcher.get("duat_floor_hard")
                elif tile == "coffin":
                    img_spec = self._sprite_fetcher.get(
                        "duat_coffin",
                    )
            # specific floor hard for this biome
            if (
                lvl.startswith("sunken")
                or lvl.startswith("hundun")
                or lvl.endswith("_sunkencity.lvl")
            ):
                if tile == "floor_hard":
                    img_spec = self._sprite_fetcher.get("sunken_floor_hard")
            # specific floor styled for this biome
            if (
                lvl.startswith("volcan")
                or lvl.startswith("ice")
                or lvl.endswith("_icecavesarea.lvl")
                or lvl.endswith("_volcano.lvl")
            ):
                if tile == "styled_floor":
                    img_spec = self._sprite_fetcher.get("empty")
            if lvl.startswith("olmec"):  # specific door
                if tile == "door":
                    img_spec = self._sprite_fetcher.get(
                        "stone_door",
                    )
            if lvl.startswith("cityofgold"):  # specific door
                if tile == "crushtraplarge":
                    img_spec = self._sprite_fetcher.get(
                        "gold_crushtraplarge",
                    )
                elif tile == "coffin":
                    img_spec = self._sprite_fetcher.get(
                        "gold_coffin",
                    )
            if lvl.startswith("temple"):  # specific door
                if tile == "coffin":
                    img_spec = self._sprite_fetcher.get(
                        "temple_coffin",
                    )

            return img_spec

        img = self._sprite_fetcher.get(str(tile), str(biome))
        if get_specific_tile(str(tile)) is not None:
            img = get_specific_tile(str(tile))

        if len(tile.split("%", 2)) > 1:
            img1 = self._sprite_fetcher.get("unknown")
            img2 = self._sprite_fetcher.get("unknown")
            primary_tile = tile.split("%", 2)[0]
            if self._sprite_fetcher.get(primary_tile, str(biome)):
                img1 = self._sprite_fetcher.get(primary_tile, str(biome))
                if get_specific_tile(str(tile)) is not None:
                    img1 = get_specific_tile(str(primary_tile))
            percent = tile.split("%", 2)[1]
            secondary_tile = "empty"
            img2 = None
            if len(tile.split("%", 2)) > 2:
                secondary_tile = tile.split("%", 2)[2]
                if self._sprite_fetcher.get(secondary_tile, str(biome)):
                    img2 = self._sprite_fetcher.get(secondary_tile, str(biome))
                    if get_specific_tile(str(tile)) is not None:
                        img2 = get_specific_tile(str(secondary_tile))
            img = self.get_tilecode_percent_texture(
                primary_tile, secondary_tile, percent, img1, img2
            )

        if img is None:
            img = self._sprite_fetcher.get("lua_tile")
        width, height = img.size

        scale_factor = 128 / scale
        width = int(
            width / scale_factor
        )  # 2.65 is the scale to get the typical 128 tile size down to the needed 50
        height = int(height / scale_factor)

        _scale = 1
        # for some reason these are sized differently then everything elses typical universal scale
        # if (tile == "door2" or tile == "door2_secret" or tile == "ghist_door2"):
        #    width = int(width/2)
        #    height = int(height/2)

        # since theres rounding involved, this makes sure each tile is size
        # correctly by making up for what was rounded off
        if width < scale and height < scale:
            difference = 0
            if width > height:
                difference = scale - width
            else:
                difference = scale - height

            width = width + difference
            height = height + difference

        img = img.resize((width, height), Image.ANTIALIAS)
        return img

    @staticmethod
    def get_tilecode_percent_texture(_tile, alt_tile, percent, img1, img2):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = Path(tempdir)
            temp1 = tempdir_path / "temp1.png"
            temp2 = tempdir_path / "temp2.png"
            # ImageTk.PhotoImage()._PhotoImage__photo.write(temp1, format="png")

            image1_save = ImageTk.PhotoImage(img1)
            # pylint: disable=protected-access
            image1_save._PhotoImage__photo.write(temp1, format="png")
            image1 = Image.open(
                temp1,
            ).convert("RGBA")
            image1 = image1.resize((50, 50), Image.BILINEAR)
            tile_text = percent + "%"
            if alt_tile != "empty":
                tile_text += "/" + str(100 - int(percent)) + "%"

                # ImageTk.PhotoImage()._PhotoImage__photo.write(temp2, format="png")

                image2_save = ImageTk.PhotoImage(img2)
                # pylint: disable=protected-access
                image2_save._PhotoImage__photo.write(temp2, format="png")
                image2 = Image.open(temp2).convert("RGBA")
                image2 = image2.resize((50, 50), Image.BILINEAR).convert("RGBA")
                image2.crop([25, 0, 50, 50]).save(temp2)
                image1.save(temp1)
                image1 = Image.open(temp1).convert("RGBA")
                image2 = Image.open(temp2).convert("RGBA")

                offset = (25, 0)
                image1.paste(image2, offset)
            # make a blank image for the text, initialized to transparent text color
            txt = Image.new("RGBA", (50, 50), (255, 255, 255, 0))

            # get a drawing context
            draw_ctx = ImageDraw.Draw(txt)

            # draw text, half opacity
            draw_ctx.text((6, 34), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((4, 34), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((6, 36), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((4, 36), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((5, 35), tile_text, fill=(255, 255, 255, 255))

            out = Image.alpha_composite(image1, txt)
        return out


@dataclass
class RoomType:
    name: str
    x_size: int
    y_size: int


ROOM_TYPES = {
    f"{room_type.name}: {room_type.x_size}x{room_type.y_size}": room_type
    for room_type in [
        RoomType("normal", 10, 8),
        RoomType("machine_wideroom", 20, 8),
        RoomType("machine_tallroom", 10, 16),
        RoomType("machine_bigroom", 20, 16),
        RoomType("coffin_frog", 10, 16),
        RoomType("ghistroom", 5, 5),
        RoomType("feeling", 20, 16),
        RoomType("chunk_ground", 5, 3),
        RoomType("chunk_door", 6, 3),
        RoomType("chunk_air", 5, 3),
        RoomType("cache", 5, 5),
    ]
}
DEFAULT_ROOM_TYPE = "normal"


class LevelsTree(ttk.Treeview):
    def __init__(self, parent, levels_tab, config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.config = config

        self.levels_tab = levels_tab

        # two different context menus to show depending on what is clicked (room or room list)
        self.popup_menu_child = tk.Menu(self, tearoff=0)
        self.popup_menu_parent = tk.Menu(self, tearoff=0)

        self.popup_menu_child.add_command(label="Rename Room", command=self.rename)
        self.popup_menu_child.add_command(
            label="Duplicate Room", command=self.duplicate
        )
        self.popup_menu_child.add_command(label="Copy Room", command=self.copy)
        self.popup_menu_child.add_command(label="Paste Room", command=self.paste)
        self.popup_menu_child.add_command(
            label="Delete Room", command=self.delete_selected
        )
        self.popup_menu_child.add_command(label="Add Room", command=self.add_room)
        self.popup_menu_parent.add_command(label="Add Room", command=self.add_room)
        self.popup_menu_parent.add_command(label="Paste Room", command=self.paste)

        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            item_iid = self.selection()[0]
            parent_iid = self.parent(item_iid)  # gets selected room
            if parent_iid:  # if actual room is clicked
                self.popup_menu_child.tk_popup(event.x_root, event.y_root, 0)
            else:  # if room list is clicked
                self.popup_menu_parent.tk_popup(event.x_root, event.y_root, 0)

            self.levels_tab.save_needed = True
            self.levels_tab.button_save["state"] = tk.NORMAL
        except Exception:  # pylint: disable=broad-except
            self.popup_menu_child.grab_release()
            self.popup_menu_parent.grab_release()

    def rename(self):
        for _ in self.selection()[::-1]:
            self.rename_dialog()

    def duplicate(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            item_name = self.item(item_iid)["text"]
            room_data = self.item(item_iid, option="values")
            self.insert(parent_iid, "end", text=item_name + " COPY", values=room_data)

    def copy(self):
        item = self.selection()[0]
        copy_text = str(self.item(item, option="text"))
        copy_values_raw = self.item(item, option="values")
        copy_values = ""
        for line in copy_values_raw:
            copy_values += str(line) + "\n"
        logger.debug("copied %s", copy_values)
        pyperclip.copy(copy_text + "\n" + copy_values)

    def paste(self):
        data = pyperclip.paste().encode("utf-8").decode("cp1252")

        paste_text = data.split("\n", 1)[0]
        paste_values_raw = data.split("\n", 1)[1]

        paste_values = []
        paste_values = paste_values_raw.split("\n")

        for item in paste_values:
            if item == "":
                paste_values.remove(item)  # removes empty line
        logger.debug("pasted %s", paste_values)

        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            self.insert(parent_iid, "end", text=paste_text, values=paste_values)
        else:
            self.insert(item_iid, "end", text=paste_text, values=paste_values)

    def delete_selected(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if parent_iid:
            msg_box = tk.messagebox.askquestion(
                "Delete Room?",
                "Are you sure you want to delete "
                + self.item(item_iid)["text"]
                + "?"
                + "\nThis won't be recoverable.",
                icon="warning",
            )
            if msg_box == "yes":
                self.delete(item_iid)
                self.levels_tab.canvas.delete("all")
                self.levels_tab.canvas_dual.delete("all")
                self.levels_tab.canvas.grid_remove()
                self.levels_tab.canvas_dual.grid_remove()

    def add_room(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        parent = None
        if parent_iid:
            parent = parent_iid
        else:
            parent = item_iid

        # First check if a blank space was selected
        entry_index = self.focus()
        if entry_index == "":
            return

        # Set default prompt based on parent name
        roomsize_key = "normal: 10x8"
        parent_room_type = self.item(parent)["text"]
        for room_size_text, room_type in ROOM_TYPES.items():
            if parent_room_type.startswith(room_type.name):
                roomsize_key = room_size_text
                break

        room_type = ROOM_TYPES[roomsize_key]
        new_room_data = ["0" * room_type.x_size] * room_type.y_size
        self.insert(parent, "end", text="new room", values=new_room_data)

    def rename_dialog(self):
        item_iid = self.selection()[0]
        parent_iid = self.parent(item_iid)  # gets selected room
        if not parent_iid:
            return

        # First check if a blank space was selected
        entry_index = self.focus()
        if entry_index == "":
            return

        win = PopupWindow("Edit Name", self.config)

        item_name = ""
        item_name = self.item(item_iid)["text"]

        col1_lbl = ttk.Label(win, text="Name: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, item_name)  # Default to rooms current name
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="nswe")

        def update_then_destroy():
            if self.confirm_entry(col1_ent.get()):
                win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=1, column=0, columnspan=2, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=2, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Ok", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

    def confirm_entry(self, entry1):
        if entry1 != "":
            self.item(self.focus(), text=entry1)
            return True
        else:
            return False


class RulesTree(ttk.Treeview):
    def __init__(self, parent, levels_tab, *args, **kwargs):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)
        self.levels_tab = levels_tab

        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu_parent = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Add", command=self.add)
        self.popup_menu_parent.add_command(label="Add", command=self.add)
        self.popup_menu.add_command(label="Delete", command=self.delete_selected)

        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            if len(self.selection()) == 1:
                self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
            else:
                self.popup_menu_parent.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def delete_selected(self):
        msg_box = tk.messagebox.askquestion(
            "Delete?",
            "Delete this rule?",
            icon="warning",
        )
        if msg_box == "yes":
            item_iid = self.selection()[0]
            self.delete(item_iid)
            self.levels_tab.save_needed = True
            self.levels_tab.button_save["state"] = tk.NORMAL

    def add(self):
        _edited = self.insert(
            "",
            "end",
            values=["COMMENT", "VAL", "// COMMENT"],
        )
        self.levels_tab.save_needed = True
        self.levels_tab.button_save["state"] = tk.NORMAL
        # self.selection_set(0, 'end')
