from enum import Enum
from fnmatch import fnmatch
from functools import lru_cache
import glob
import logging
import os
import os.path
from pathlib import Path
from PIL import Image, ImageTk
import shutil
import tkinter as tk
from tkinter import ttk

from modlunky2.constants import BASE_DIR
from modlunky2.ui.levels.custom_levels.create_level_dialog import (
    present_create_level_dialog,
)
from modlunky2.ui.widgets import PopupWindow

logger = logging.getLogger(__name__)


class LEVEL_TYPE(Enum):
    VANILLA = 1
    MODDED = 2
    CUSTOM = 3


class PACK_LIST_TYPE(Enum):
    VANILLA_ROOMS = "single_room"
    CUSTOM_LEVELS = "custom_levels"


class FilesTree(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        packs_path,
        extracts_path,
        pack_list_type,
        is_save_required,
        on_level_exited,
        on_update_lvls_path,
        on_select_file,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.packs_path = packs_path
        self.extracts_path = extracts_path
        self.pack_list_type = pack_list_type

        self.is_save_required = is_save_required
        self.on_level_exited = on_level_exited
        self.on_update_lvls_path = on_update_lvls_path
        self.on_select_file = on_select_file

        self.icon_add = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/add.png").resize((20, 20))
        )
        self.icon_folder = ImageTk.PhotoImage(
            Image.open(BASE_DIR / "static/images/folder.png").resize((20, 20))
        )

        self.current_save_format = None
        self.last_selected_file = None
        self.lvls_path = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self, selectmode="browse", padding=[-15, 0, 0, 0]
        )  # This tree shows the lvl files loaded from the chosen dir, excluding vanilla lvl files.

        self.tree.place(x=30, y=95)
        vsb_tree_files = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb_tree_files.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree.configure(yscrollcommand=vsb_tree_files.set)
        self.tree.grid(row=0, column=0, rowspan=1, sticky="nswe")
        vsb_tree_files.grid(row=0, column=0, sticky="nse")

        self.tree.bind(
            "<ButtonRelease-1>",
            self.on_click,
        )

    @lru_cache
    def lvl_icon(self, level_type):
        if level_type == LEVEL_TYPE.CUSTOM:
            image_path = BASE_DIR / "static/images/lvl_custom.png"
        elif level_type == LEVEL_TYPE.MODDED:
            image_path = BASE_DIR / "static/images/lvl_modded.png"
        else:
            image_path = BASE_DIR / "static/images/lvl.png"

        return ImageTk.PhotoImage(Image.open(image_path).resize((20, 20)))

    def update_lvls_path(self, lvls_path):
        self.lvls_path = lvls_path
        self.on_update_lvls_path(lvls_path)

    def load_packs(self):
        logger.debug("loading packs")

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.tree.heading("#0", text="Select Pack")
        i = 0
        for filepath in glob.iglob(str(self.packs_path) + "/*/"):
            # Convert the filepath to a string.
            path_in_str = str(filepath)
            pack_name = os.path.basename(os.path.normpath(path_in_str))
            # Add the file to the tree with the folder icon.
            self.tree.insert("", "end", text=str(pack_name), image=self.icon_folder)
            i = i + 1
        self.tree.insert("", "end", text=str("[Create_New_Pack]"), image=self.icon_add)

    def load_pack_lvls(self, lvl_dir):
        if self.pack_list_type == PACK_LIST_TYPE.VANILLA_ROOMS:
            self.load_pack_vanilla_lvls(lvl_dir)
        else:
            self.load_pack_custom_lvls(lvl_dir)

    def load_pack_vanilla_lvls(self, lvl_dir):
        self.update_lvls_path(Path(lvl_dir))
        self.organize_pack()
        logger.debug("lvls_path = %s", lvl_dir)
        self.reset_tree()

        self.tree.insert("", "end", values=str("<<BACK"), text=str("<<BACK"))

        loaded_pack = self.get_loaded_pack()
        root = Path(self.packs_path / loaded_pack) / "Data/Levels"

        in_arena_folder = str(lvl_dir).endswith("Arena")
        if not in_arena_folder:
            defaults_path = self.extracts_path
            self.tree.insert("", "end", text=str("ARENA"), image=self.icon_folder)
        else:
            defaults_path = self.extracts_path / "Arena"
            root = root / "Arena"

        def get_levels_in_dir(dir_path):
            levels = glob.iglob(str(dir_path))
            levels = [str(file_path) for file_path in levels]
            levels = [
                os.path.basename(os.path.normpath(file_path)) for file_path in levels
            ]
            return levels

        # Load all .lvl files from extracts so we know which are modded and which are not
        # Treat all that don't exist in extracts as a custom level file
        custom_levels = get_levels_in_dir(root / "***.lvl")
        vanilla_levels = get_levels_in_dir(defaults_path / "***.lvl")

        modded_levels = [
            lvl_name for lvl_name in custom_levels if lvl_name in vanilla_levels
        ]
        custom_levels = [
            lvl_name for lvl_name in custom_levels if lvl_name not in modded_levels
        ]

        for lvl_name in custom_levels:
            self.tree.insert(
                "", "end", text=lvl_name, image=self.lvl_icon(LEVEL_TYPE.CUSTOM)
            )
        for lvl_name in vanilla_levels:
            if lvl_name in modded_levels:
                self.tree.insert(
                    "", "end", text=lvl_name, image=self.lvl_icon(LEVEL_TYPE.MODDED)
                )
            else:
                self.tree.insert(
                    "", "end", text=lvl_name, image=self.lvl_icon(LEVEL_TYPE.VANILLA)
                )

    def load_pack_custom_lvls(self, lvl_dir, selected_lvl=None):
        self.update_lvls_path(Path(lvl_dir))
        logger.debug("lvls_path = %s", lvl_dir)
        defaults_path = self.extracts_path
        self.reset_tree()

        self.tree.insert("", "end", values=str("<<BACK"), text=str("<<BACK"))

        level_files = [
            os.path.basename(os.path.normpath(i))
            for i in glob.iglob(str(lvl_dir) + "/***.lvl")
        ]
        mod_files = level_files
        is_arenas = False
        if not str(lvl_dir).endswith("Arena"):
            self.tree.insert("", "end", text=str("ARENA"), image=self.icon_folder)
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
                        item = self.tree.insert(
                            "",
                            "end",
                            text=str(lvl_name),
                            image=self.lvl_icon(LEVEL_TYPE.MODDED),
                        )
                if not lvl_in_use:
                    item = self.tree.insert(
                        "",
                        "end",
                        text=str(lvl_name),
                        image=self.lvl_icon(LEVEL_TYPE.VANILLA),
                    )
                if item != None and lvl_name == selected_lvl:
                    self.tree.selection_set(item)
                    self.last_selected_file = item

        self.tree.insert("", "end", text=str("[Create_New_Level]"), image=self.icon_add)

    def on_click(self, _event):
        if (
            self.tree.heading("#0")["text"] != "Select Pack"
            and self.last_selected_file is not None
        ):
            if self.is_save_required():
                msg_box = tk.messagebox.askquestion(
                    "Continue?",
                    "You have unsaved changes to "
                    + str(self.tree.item(self.last_selected_file, option="text"))
                    + "\nContinue without saving?",
                    icon="warning",
                )
                if msg_box == "yes":
                    self.on_level_exited()
                    logger.debug("Entered new files witout saving")
                else:
                    self.tree.selection_set(self.last_selected_file)
                    return

        item_text = ""
        for item in self.tree.selection():
            item_text = self.tree.item(item, "text")

        if item_text == "<<BACK":
            if self.tree.heading("#0")["text"].endswith("Arena"):
                self.tree.heading("#0", text=self.get_loaded_pack())
                loaded_pack = self.get_loaded_pack()
                self.load_pack_lvls(
                    Path(self.packs_path / loaded_pack / "Data" / "Levels"),
                )
            else:
                self.load_packs()
        elif item_text == "ARENA" and self.tree.heading("#0")["text"] != "Select Pack":
            self.tree.heading("#0", text=self.tree.heading("#0")["text"] + "/Arena")
            loaded_pack = self.get_loaded_pack()
            self.load_pack_lvls(
                Path(self.packs_path / loaded_pack / "Data" / "Levels" / "Arena"),
            )
        elif item_text == "[Create_New_Pack]":
            logger.debug("Creating new pack")
            self.create_pack_dialog()
        elif item_text == "[Create_New_Level]":
            logger.debug("Creating new level")
            self.create_level_dialog()
        elif self.tree.heading("#0")["text"] == "Select Pack":
            for item in self.tree.selection():
                self.last_selected_file = item
                item_text = self.tree.item(item, "text")
                self.tree.heading("#0", text=item_text)
                loaded_pack = self.get_loaded_pack()
                self.load_pack_lvls(
                    Path(self.packs_path / loaded_pack) / "Data" / "Levels",
                )
        else:
            for item in self.tree.selection():
                self.last_selected_file = item
                item_text = self.tree.item(item, "text")
                self.on_select_file(item_text)

    def organize_pack(self):
        loaded_pack = self.get_loaded_pack()
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

    def create_pack_dialog(self):
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
                self.load_packs()
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

    def create_level_dialog(self):
        def on_created(lvl_file_name):
            # Reload the file list tree so that the new file shows up, and select it.
            self.load_pack_custom_lvls(self.lvls_path, lvl_file_name)
            # Load the newly created file into the editor.
            self.on_select_file(lvl_file_name)

        loaded_pack = self.get_loaded_pack()
        backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
        present_create_level_dialog(
            self.modlunky_config,
            backup_dir,
            self.lvls_path,
            self.current_save_format,
            on_created,
        )

    def reset_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def get_loaded_pack(self):
        return self.tree.heading("#0")["text"].split("/")[0]

    def get_loaded_level(self):
        return self.tree.item(self.last_selected_file, option="text")

    def update_selected_file_icon(self, lvl_type):
        for item in self.tree.selection():
            self.tree.item(item, image=self.lvl_icon(lvl_type))

    def has_selected_file(self):
        return len(self.tree.selection()) > 0

    def selected_file_is_arena(self):
        return self.tree.heading("#0")["text"].endswith("Arena")
