import logging
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import webbrowser
from functools import wraps
from pathlib import Path

from tkinter import PhotoImage, ttk
from tkinter.scrolledtext import ScrolledText
import numpy as np
from PIL import Image
import tkinter.messagebox as tkMessageBox

import random

import requests
from packaging import version
from PIL import Image, ImageTk

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.constants import (
    EXTRACTED_DIR,
    FILEPATH_DIRS,
    OVERRIDES_DIR,
    PACKS_DIR,
)
from modlunky2.assets.exc import MissingAsset
from modlunky2.assets.patcher import Patcher
from modlunky2.constants import BASE_DIR, ROOT_DIR

logger = logging.getLogger("modlunky2")

cwd = os.getcwd()

MODS = Path("Mods")

TOP_LEVEL_DIRS = [EXTRACTED_DIR, PACKS_DIR, OVERRIDES_DIR]


def is_patched(exe_filename):
    with exe_filename.open("rb") as exe:
        return Patcher(exe).is_checksum_patched()


def log_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected failure")

    return wrapper


def get_latest_version():
    try:
        return version.parse(
            requests.get(
                "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest"
            ).json()["tag_name"]
        )
    except Exception:  # pylint: disable=broad-except
        return None


def get_current_version():
    with (ROOT_DIR / "VERSION").open() as version_file:
        return version.parse(version_file.read().strip())


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


# Adapted from https://beenje.github.io/blog/posts/logging-to-a-tkinter-scrolledtext-widget/
class ConsoleWindow(tk.Toplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wm_title("Modlunky2 Console")
        self.geometry("1024x600")
        # self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.close)

        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(self, state="disabled")
        self.scrolled_text.pack(expand=True, fill="both")
        self.scrolled_text.configure(font="TkFixedFont")
        self.scrolled_text.tag_config("INFO", foreground="green")
        self.scrolled_text.tag_config("DEBUG", foreground="gray")
        self.scrolled_text.tag_config("WARNING", foreground="orange")
        self.scrolled_text.tag_config("ERROR", foreground="red")
        self.scrolled_text.tag_config("CRITICAL", foreground="red", underline=1)

        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter("%(asctime)s: %(message)s")
        self.queue_handler.setFormatter(formatter)
        logger.addHandler(self.queue_handler)

        # Start polling messages from the queue
        self.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state="normal")
        self.scrolled_text.insert(tk.END, msg + "\n", record.levelname)
        self.scrolled_text.configure(state="disabled")
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.after(100, self.poll_log_queue)

    def close(self):
        pass


class Tab(ttk.Frame):
    """ Base class that all tabs should inherit from."""

    def on_load(self):
        """ Called whenever the tab is loaded."""


class ScrollableFrame(ttk.LabelFrame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Enter>", self._bind_to_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_from_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        scroll_dir = None
        if event.num == 5 or event.delta == -120:
            scroll_dir = 1
        elif event.num == 4 or event.delta == 120:
            scroll_dir = -1

        if scroll_dir is None:
            return

        # If the scrollbar is max size don't bother scrolling
        if self.scrollbar.get() == (0.0, 1.0):
            return

        self.canvas.yview_scroll(scroll_dir, "units")

    def _bind_to_mousewheel(self, _event):
        if "nt" in os.name:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else:
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_from_mousewheel(self, _event):
        if "nt" in os.name:
            self.canvas.unbind_all("<MouseWheel>")
        else:
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")


class PackTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.install_dir = install_dir

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, minsize=30)
        self.rowconfigure(2, minsize=60)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)


        self.frame = ScrollableFrame(self, text="Select mods to pack")
        self.frame.grid(row=0, column=0, columnspan=2, pady=5, padx=5, sticky="nswe")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(self, length=100, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=2, pady=5, padx=5, sticky="nswe")

        self.button_pack = ttk.Button(self, text="Pack", command=self.pack)
        self.button_pack.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")
        self.button_restore = ttk.Button(self, text="Restore EXE", command=self.restore)
        self.button_restore.grid(row=2, column=1, pady=5, padx=5, sticky="nswe")

        default_icon_path = BASE_DIR / "static/images/noicon.png"
        self.default_icon = ImageTk.PhotoImage(Image.open(default_icon_path))

        self.checkbox_vars = []

    def restore(self):
        mods_dir = self.install_dir / MODS
        extract_dir = mods_dir / "Extracted"
        source_exe = extract_dir / "Spel2.exe"
        dest_exe = self.install_dir / "Spel2.exe"

        if is_patched(source_exe):
            logger.critical(
                "Source exe (%s) is somehow patched. You need to validate game files in steam and re-extract."
            )
            return

        logger.info("Copying exe from %s to %s", source_exe, dest_exe)
        shutil.copy2(source_exe, dest_exe)
        logger.info("Done")


    def pack(self):
        packs = [
            self.install_dir / "Mods" / exe.get()
            for exe in self.checkbox_vars
            if exe.get()
        ]
        thread = threading.Thread(target=self.repack_assets, args=(packs,))
        thread.start()

    def get_packs(self):
        pack_dirs = []
        overrides_dir = self.install_dir / "Mods" / "Overrides"
        if overrides_dir.exists():
            pack_dirs.append(overrides_dir.relative_to(self.install_dir / "Mods"))

        packs_dir = self.install_dir / "Mods" / "Packs"
        if packs_dir.exists():
            for dir_ in packs_dir.iterdir():
                if not dir_.is_dir():
                    continue
                pack_dirs.append(dir_.relative_to(self.install_dir / "Mods"))

        return pack_dirs

    def on_load(self):
        for child in self.frame.scrollable_frame.winfo_children():
            child.destroy()
        self.checkbox_vars.clear()

        for idx, exe in enumerate(self.get_packs()):
            str_var = tk.StringVar()
            item = tk.Checkbutton(
                self.frame.scrollable_frame,
                text=f" {exe}",
                image=self.default_icon,
                font=("Segoe UI", 12, "bold"),
                variable=str_var,
                onvalue=f"{exe}",
                offvalue="",
                compound="left",
            )
            self.checkbox_vars.append(str_var)
            item.grid(row=idx, column=0, pady=5, padx=5, sticky="w")

    @log_exception
    def repack_assets(self, packs):
        mods_dir = self.install_dir / MODS
        extract_dir = mods_dir / "Extracted"
        source_exe = extract_dir / "Spel2.exe"
        dest_exe = self.install_dir / "Spel2.exe"

        if is_patched(source_exe):
            logger.critical(
                "Source exe (%s) is somehow patched. You need to re-extract."
            )
            return

        shutil.copy2(source_exe, dest_exe)

        with dest_exe.open("rb+") as dest_file:
            asset_store = AssetStore.load_from_file(dest_file)
            try:
                asset_store.repackage(
                    packs,
                    extract_dir,
                    mods_dir / ".compressed",
                )
            except MissingAsset as err:
                logger.error(
                    "Failed to find expected asset: %s. Unabled to proceed...", err
                )
                return

            patcher = Patcher(dest_file)
            patcher.patch_checksum()
            patcher.patch_release()
            logger.info("Repacking complete!")


class ExtractTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.install_dir = install_dir

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, minsize=30)
        self.rowconfigure(2, minsize=60)

        self.label_frame = ttk.LabelFrame(self, text="Select exe to Extract")
        self.label_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")
        self.label_frame.rowconfigure(0, weight=1)
        self.label_frame.columnconfigure(0, weight=1)

        self.scrollbar = ttk.Scrollbar(self.label_frame)
        self.scrollbar.grid(row=0, column=1, sticky="nes")

        self.list_box = tk.Listbox(self.label_frame)
        self.list_box.grid(row=0, column=0, sticky="nswe")

        self.list_box.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.list_box.yview)

        self.progress = ttk.Progressbar(self, length=100, mode="determinate")
        self.progress.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        self.button_extract = ttk.Button(self, text="Extract", command=self.extract)
        self.button_extract.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")

    def extract(self):
        idx = self.list_box.curselection()
        if not idx:
            return

        selected_exe = self.list_box.get(idx)
        thread = threading.Thread(target=self.extract_assets, args=(selected_exe,))
        thread.start()

    def get_exes(self):
        exes = []
        # Don't recurse forever. 3 levels should be enough
        exes.extend(self.install_dir.glob("*.exe"))
        exes.extend(self.install_dir.glob("*/*.exe"))
        exes.extend(self.install_dir.glob("*/*/*.exe"))
        return [
            exe.relative_to(self.install_dir)
            for exe in exes
            # Exclude modlunky2 which is likely in the install directory
            if exe.name not in ["modlunky2.exe"]
        ]

    def on_load(self):
        self.list_box.delete(0, tk.END)
        for exe in self.get_exes():
            self.list_box.insert(tk.END, str(exe))

    @log_exception
    def extract_assets(self, target):

        exe_filename = self.install_dir / target

        if is_patched(exe_filename):
            logger.critical("%s is a patched exe. Can't extract.", exe_filename)
            return

        mods_dir = self.install_dir / MODS

        for dir_ in TOP_LEVEL_DIRS:
            (mods_dir / dir_).mkdir(parents=True, exist_ok=True)

        for dir_ in FILEPATH_DIRS:
            (mods_dir / EXTRACTED_DIR / dir_).mkdir(parents=True, exist_ok=True)
            (mods_dir / ".compressed" / EXTRACTED_DIR / dir_).mkdir(
                parents=True, exist_ok=True
            )

        with exe_filename.open("rb") as exe:
            asset_store = AssetStore.load_from_file(exe)
            unextracted = asset_store.extract(
                mods_dir / EXTRACTED_DIR,
                mods_dir / ".compressed" / EXTRACTED_DIR,
            )

        for asset in unextracted:
            logger.warning("Un-extracted Asset %s", asset.asset_block)

        dest = mods_dir / EXTRACTED_DIR / "Spel2.exe"
        if exe_filename != dest:
            logger.info("Backing up exe to %s", dest)
            shutil.copy2(exe_filename, dest)

        logger.info("Extraction complete!")


class ToggledFrame(tk.Frame):
    def __init__(self, parent, text, *args, **options):
        tk.Frame.__init__(self, parent, *args, **options)

        self.show = tk.IntVar()
        self.show.set(0)

        self.title_frame = ttk.Frame(self)
        self.title_frame.pack(fill="x", expand=1)

        ttk.Label(self.title_frame, text=text).pack(side="left", fill="x", expand=1)

        self.toggle_button = ttk.Checkbutton(
            self.title_frame,
            width=2,
            text="+",
            command=self.toggle,
            variable=self.show,
            style="Toolbutton",
        )
        self.toggle_button.pack(side="left")

        self.sub_frame = tk.Frame(self, relief="sunken", borderwidth=1)

    def toggle(self):
        if bool(self.show.get()):
            self.sub_frame.pack(fill="x", expand=1)
            self.toggle_button.configure(text="-")
        else:
            self.sub_frame.forget()
            self.toggle_button.configure(text="+")


class LevelsTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.install_dir = install_dir

        self.lvl_editor_start_canvas = tk.Canvas(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.lvl_editor_start_canvas.grid(row = 0, column = 0, sticky="nswe")
        self.lvl_editor_start_canvas.columnconfigure(0, weight=1)
        self.lvl_editor_start_canvas.rowconfigure(0, weight=1)

        self.welcome_label = tk.Label(self.lvl_editor_start_canvas, text="Welcome to the Spelunky 2 Level Editor! created by JackHasWifi with lots of help from garebear, fingerspit, wolfo, and the community\n\n NOTICE: Saving when viewing extracts will save the changes to a new file in overrides", anchor="center")
        self.welcome_label.grid(row = 0, column = 0, sticky="nswe", ipady=30, padx=(10, 10))

        def select_lvl_folder():
            from tkinter import filedialog
            dirname = filedialog.askdirectory(parent=self,initialdir="/",title='Please select a directory')
            if not dirname:
                return
            else:
                self.load_editor(dirname)

        def load_extracts_lvls():
            extracts_path = self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
            if os.path.isdir(extracts_path):
                self.load_editor(extracts_path)

        self.btn_lvl_extracts = ttk.Button(self.lvl_editor_start_canvas, text="Load From Extracts", command=load_extracts_lvls)
        self.btn_lvl_extracts.grid(row = 1, column = 0, sticky="nswe", ipady=30, padx=(20, 20), pady=(10, 1))

        self.btn_lvl_folder = ttk.Button(self.lvl_editor_start_canvas, text="Load Levels Folder", command=select_lvl_folder)
        self.btn_lvl_folder.grid(row = 2, column = 0, sticky="nswe", ipady=30, padx=(20, 20), pady=(10, 10))

    def load_editor(self, lvls_path):
            self.lvl_editor_start_canvas.grid_remove()
            self.columnconfigure(0, minsize=200)  # Column 0 = Level List
            self.columnconfigure(0, weight=0)
            self.columnconfigure(1, weight=1)  # Column 1 = Everything Else
            self.rowconfigure(0, weight=1)  # Row 0 = List box / Label

            # Loads lvl Files
            self.tree_files = ttk.Treeview(self, selectmode="browse")
            self.tree_files.place(x=30, y=95)
            self.vsb_tree_files = ttk.Scrollbar(
                self, orient="vertical", command=self.tree_files.yview
            )
            self.vsb_tree_files.place(x=30 + 200 + 2, y=95, height=200 + 20)
            self.tree_files.configure(yscrollcommand=self.vsb_tree_files.set)
            self.tree_files["columns"] = ("1",)
            self.tree_files["show"] = "headings"
            self.tree_files.column("1", width=100, anchor="w")
            self.tree_files.heading("1", text="Level Files")
            self.my_list = os.listdir(lvls_path)
            self.tree_files.grid(row=0, column=0, rowspan=3, sticky="nswe")
            self.vsb_tree_files.grid(row=0, column=0, sticky="nse")

            for file in self.my_list: # Loads list of all the lvl files in the left farthest treeview
                self.tree_files.insert("", "end", values=str(file), text=str(file))

            # Seperates Level Rules and Level Editor into two tabs
            self.tab_control = ttk.Notebook(self)

            self.tab1 = ttk.Frame(self.tab_control) # Tab 1 shows a lvl files rules
            self.tab2 = ttk.Frame(self.tab_control) # Tab 2 is the actual level editor

            self.tab_control.add( # Rules Tab ----------------------------------------------------
                self.tab1, text="Rules"
            )

            self.tab1.columnconfigure(0, weight=1)  # Column 1 = Everything Else
            self.tab1.rowconfigure(0, weight=1)  # Row 0 = List box / Label

            self.tree = ttk.Treeview(self.tab1, selectmode="browse")
            self.tree.place(x=30, y=95)
            self.vsb = ttk.Scrollbar(self.tab1, orient="vertical", command=self.tree.yview)
            self.vsb.place(x=30 + 200 + 2, y=95, height=200 + 20)
            self.tree.configure(yscrollcommand=self.vsb.set)
            self.tree["columns"] = ("1", "2", "3")
            self.tree["show"] = "headings"
            self.tree.column("1", width=100, anchor="w")
            self.tree.column("2", width=10, anchor="w")
            self.tree.column("3", width=100, anchor="w")
            self.tree.heading("1", text="Entry")
            self.tree.heading("2", text="Value")
            self.tree.heading("3", text="Notes")
            self.tree.grid(row=0, column=0, sticky="nwse")
            self.vsb.grid(row=0, column=1, sticky="nse")

            self.tab_control.add(  # Level Editor Tab -------------------------------------------------
                self.tab2, text="Level Editor"
            )
            self.tab2.columnconfigure(0, minsize=200)  # Column 0 = Level List
            self.tab2.columnconfigure(1, weight=1)  # Column 1 = Everything Else
            self.tab2.rowconfigure(2, weight=1)  # Row 0 = List box / Label

            self.tree_levels = ttk.Treeview(self.tab2, selectmode="browse")
            self.tree_levels.place(x=30, y=95)
            self.vsb_tree_levels = ttk.Scrollbar(
                self, orient="vertical", command=self.tree_levels.yview
            )
            self.vsb_tree_levels.place(x=30 + 200 + 2, y=95, height=200 + 20)
            self.tree_levels.configure(yscrollcommand=self.vsb_tree_files.set)
            self.my_list = os.listdir(
                self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
            )
            self.tree_levels.grid(row=0, column=0, rowspan=4, sticky="nswe")
            self.vsb_tree_levels.grid(row=0, column=0, sticky="nse")
            self.tab_control.grid(row=0, column=1, sticky="nwse")

            self.mag = 50 # the size of each tiles in the grid; 50 is optimal
            self.rows = 15 # default values, could be set to none and still work I think lol
            self.cols = 15 # default values, could be set to none and still work I think lol

            self.canvas = tk.Canvas( # this is the main level editor grid
                self.tab2,
                width=self.mag * self.cols,
                height=self.mag * self.rows,
                bg="white",
            )
            self.canvas.grid(row=0, column=1, rowspan=3, columnspan=1)
            self.canvas_dual = tk.Canvas( # this is for dual level, it shows the back area
                self.tab2,
                width = 0,
                bg="white",
            )
            self.canvas_dual.grid(row=0, column=2, rowspan=3, columnspan=1, padx=(0, 50))

            tiles = [[None for _ in range(self.cols)] for _ in range(self.rows)] # this is for the tiles

            self.tile_pallete = ScrollableFrame( # the tile palletes are loaded into here as buttons with their image as a tile and txt as their value to grab when needed
                self.tab2,
                text = "Tile Pallete",
                width=50
            )
            self.tile_pallete.grid(row=2, column=3, columnspan=2, rowspan=2, sticky="swne")
            self.tile_pallete.scrollable_frame["width"]=50

            self.tile_label = tk.Label( self.tab2, text="Selected Tile:" , width=40) # shows selected tile. Important because this is used for more than just user convenience; we can grab the currently used tile here
            self.tile_label.grid(row=0, column=3, sticky="w")

            self.imgSel = ImageTk.PhotoImage(Image.open(BASE_DIR / "static/images/tilecodetextures.png"))
            self.panelSel = tk.Label(self.tab2, image = self.imgSel, width=50) # shows selected tile image
            self.panelSel.grid(row=0, column=4)

            self.scale = tk.Scale(self.tab2, from_=0, to=100, orient=tk.HORIZONTAL) # scale for the percent of a selected tile
            self.scale.grid(row=1, column=3, columnspan = 2, sticky="n")

            self.tags = tk.Text(self.tab2, height=2, width=30) # text box for tags each room has like \!dual for example
            self.tags.grid(row=3, column=1, columnspan=2, sticky="nswe")

            # the tilecodes are in the same order as the tiles in the image(50x50, left to right)
            self.texture_images = []
            fileTileCodes = open(BASE_DIR / "tilecodes.txt", encoding="utf8")
            Lines = fileTileCodes.readlines()
            count = 0
            self.countCol = 0
            self.countRow = 0
            count_total = 0
            x = 99
            y = 0
            y2 = 0
            color_base = int(random.random())
            self.uni_tile_code_list = []
            self.tile_pallete_ref = []
            for line in Lines:
                self.uni_tile_code_list.append(line.strip())
                im = Image.open(BASE_DIR / "static/images/tilecodetextures.png")
                im = im.crop((count*50,y*50,5000-(x*50),(1+y)*50))
                self.tile_texture = ImageTk.PhotoImage(im)
                self.texture_images.append(self.tile_texture)
                r = int(color_base * 256 + (256 / (count+1)))
                g = int(color_base * 256 + (256 / (count+1)))
                b = int(color_base * 256 + (256 / (count+1)))
                color = str(r)+str(g)+str(b)
                tile_ref = []
                tile_ref.append(line.strip())
                tile_ref.append(self.texture_images[count_total])
                self.btn = tk.Button(self.tile_pallete.scrollable_frame, text = line.strip() ,width=40, height=40, image=self.texture_images[count_total], command=lambda r = self.countRow , c = self.countCol: self.Tile_Pick(r, c)).grid(row=self.countRow, column=self.countCol)
                self.tile_pallete_ref.append(tile_ref)
                count = count + 1
                self.countCol = self.countCol + 1
                x = x - 1
                if self.countCol>7:
                    self.countRow = self.countRow + 1
                    self.countCol = 0
                if count == 100: #theres a 100 tiles in each row on the image so this lets me know when to start grabbing from the next row
                    y = y + 1
                    x = 99
                    count = 0
                count_total = count_total + 1
            self.panelSel['image']=self.texture_images[0]
            self.tile_label['text']="Selected Tile: " + "\?empty a"

            def Canvas_Click(event, canvas): # when the level editor grid is clicked
                # Get rectangle diameters
                col_width = self.mag
                row_height = self.mag
                # Calculate column and row number
                col = event.x // col_width
                row = event.y // row_height
                # If the tile is not filled, create a rectangle
                canvas.delete(self.tiles[int(row)][int(col)])
                self.tiles[row][col] = canvas.create_image(int(col) * self.mag,
                    int(row) * self.mag, image=self.panelSel['image'], anchor='nw')
                coords = (col * self.mag, row * self.mag, col * self.mag + 50, row * self.mag + 50)
                print(str(self.tiles_meta[row][col]) + " replaced with " + self.tile_label['text'].split(" ", 4)[3])
                self.tiles_meta[row][col] = self.tile_label['text'].split(" ", 4)[3]
            self.canvas.bind("<Button-1>", lambda event: Canvas_Click(event, self.canvas))
            self.canvas_dual.bind("<Button-1>", lambda event: Canvas_Click(event, self.canvas_dual))

            def tree_filesitemclick(_event):
                # Using readlines()
                item_text = ""
                for item in self.tree_files.selection():
                    item_text = self.tree_files.item(item, "text")
                    self.read_lvl_file(lvls_path, item_text)

            self.tree_files.bind("<ButtonRelease-1>", tree_filesitemclick)

    def Tile_Pick(self, button_row, button_col): # When a tile is selected from the tile pallete
        selected_tile = self.tile_pallete.scrollable_frame.grid_slaves(button_row, button_col)[0]
        self.panelSel['image']=selected_tile['image']
        self.tile_label['text']="Selected Tile: " + selected_tile['text']

    def read_lvl_file(self, lvls_path, lvl):
        file1 = open(
            lvls_path / lvl, encoding="utf8"
        )
        lines = file1.readlines()

        self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        if (lvl=="abzu.lvl"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_tidepool.png"
        elif lvl.startswith("babylon"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_babylon.png"
        elif lvl.startswith("basecamp"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("beehive"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_beehive.png"
        elif lvl.startswith("blackmark"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_jungle.png"
        elif lvl.startswith("caveboss"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("challenge_moon"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_jungle.png"
        elif lvl.startswith("challenge_star"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_temple.png"
        elif lvl.startswith("challenge_sun"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_sunken.png"
        elif lvl.startswith("city"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_gold.png"
        elif lvl.startswith("cosmic"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("duat"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("dwelling"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("egg"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_eggplant.png"
        elif lvl.startswith("ending_hard"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("end"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("hallofu"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_babylon.png"
        elif lvl.startswith("hundun"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_sunken.png"
        elif lvl.startswith("ice"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_ice.png"
        elif lvl.startswith("jungle"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_jungle.png"
        elif lvl.startswith("lake"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_tidepool.png"
        elif lvl.startswith("olmec"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_stone.png"
        elif lvl.startswith("palace"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_cave.png"
        elif lvl.startswith("sunken"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_sunken.png"
        elif lvl.startswith("tiamat"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_tidepool.png"
        elif lvl.startswith("temple"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_temple.png"
        elif lvl.startswith("tide"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_tidepool.png"
        elif lvl.startswith("vlad"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_vlad.png"
        elif lvl.startswith("volcano"):
                self.lvlbgPath = BASE_DIR / "static/images/bg_volcano.png"

        self.lvlbg = ImageTk.PhotoImage(Image.open(self.lvlbgPath))
        self.canvas.create_image(0, 0, image = self.lvlbg, anchor='nw')

        # Strips the newline character
        self.tree.delete(*self.tree.get_children())
        self.tree_levels.delete(*self.tree_levels.get_children())
        pointer = 0
        pointed = False
        load_mode = ""
        blocks = []
        # cur_item = self.tree.focus()
        self.node = self.tree_levels.insert("", "end", text="placeholder")
        self.child = None
        self.rooms = []
        # room_found = False
        def room_select(_event): # Loads room when click if not parent node
            self.dual_mode = False
            item_iid = self.tree_levels.selection()[0]
            parent_iid = self.tree_levels.parent(item_iid)
            if parent_iid:
                self.canvas.delete("all")
                self.canvas_dual.delete("all")
                self.lvlbg = ImageTk.PhotoImage(Image.open(self.lvlbgPath))
                self.canvas.create_image(0, 0, image = self.lvlbg, anchor='nw')
                current_room = self.tree_levels.item(item_iid, option='values')
                current_room_tiles = []
                tags = ""
                self.tags.delete(1.0,"end")
                for cr_line in current_room:
                    if str(cr_line).startswith('\!'):
                        print("found tag " + str(cr_line))
                        tags += cr_line + " "
                    else:
                        print("appending " + str(cr_line))
                        current_room_tiles.append(str(cr_line))
                        for char in str(cr_line):
                            if str(char)==" ":
                                self.dual_mode = True

                self.tags.insert(1.0, tags)

                self.rows = len(current_room_tiles)
                self.cols = len(str(current_room_tiles[0]))

                print(str(self.rows) + " " + str(self.cols) + "-------------------------------------------------")

                #self.mag = self.canvas.winfo_height() / self.rows - 30
                if not self.dual_mode:
                    self.__draw_grid(self.cols, self.rows, self.canvas)
                    self.canvas_dual['width']=0
                else:
                    self.__draw_grid(int((self.cols-1)/2), self.rows, self.canvas)
                    self.__draw_grid(int((self.cols-1)/2), self.rows, self.canvas_dual)

                # Create a grid of None to store the references to the tiles
                self.tiles = [[None for _ in range(self.cols)] for _ in range(self.rows)] # tile image displays
                self.tiles_meta = [[None for _ in range(self.cols)] for _ in range(self.rows)] # meta for tile

                currow = -1
                curcol = 0
                for room_row in current_room_tiles:
                    curcol = 0
                    currow = currow + 1
                    tile_image = None
                    print(room_row)
                    for block in str(room_row):
                        if str(block)!=" ":
                            for pallete_block in self.tile_pallete_ref:
                                if any(str(" " + block) in self.c[0] for self.c in self.tile_pallete_ref):
                                    tile_image = self.c[1]
                                else:
                                    print(str(block) + " " + self.c[0] + " Not Found") # There's a missing tile id somehow
                            if self.dual_mode and curcol>int((self.cols-1)/2):
                                x = int(curcol - ((self.cols-1)/2)-1)
                                self.tiles[currow][curcol] = self.canvas_dual.create_image(x * self.mag,
                                currow * self.mag, image=tile_image, anchor='nw')
                                coords = (x * self.mag, currow * self.mag, x * self.mag + 50, currow * self.mag + 50)
                                self.tiles_meta[currow][curcol] = block
                            else:
                                self.tiles[currow][curcol] = self.canvas.create_image(curcol * self.mag,
                                currow * self.mag, image=tile_image, anchor='nw')
                                coords = (curcol * self.mag, currow * self.mag, curcol * self.mag + 50, currow * self.mag + 50)
                                self.tiles_meta[currow][curcol] = block
                            #print("loaded layer col " + str(curcol) + " " + str(self.c[0]) + " out of " + str(len(str(room_row))))


                        curcol = curcol + 1


        self.tree_levels.bind("<ButtonRelease-1>", room_select)

        tile_count = 0
        tl_col = 0
        color_base = int(random.random())
        self.tile_convert = []
        for line in lines:
            line = " ".join(line.split())  # remove duplicate spaces
            print("parsing " + line)
            if (
                line.strip() == "// ------------------------------"
                and not pointed
                and pointer == 0
                and load_mode != "Templates"
                and line.strip()
            ):
                pointer = pointer + 1
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=("COMMENT", "", str(line.strip())),
                )
            elif (
                pointer == 1
                and not pointed
                and load_mode != "Templates"
                and line.strip()
            ):
                load_mode = "RoomChances"  # default because its usually at the top
                pointed = True
                if line.strip() == "// TILE CODES" and line.strip():
                    load_mode = "TileCodes"
                elif line.strip() == "// LEVEL CHANCES" and line.strip():
                    load_mode = "LevelChances"
                elif line.strip() == "// MONSTER CHANCES" and line.strip():
                    load_mode = "MonsterChances"
                elif line.strip() == "// TEMPLATES" and line.strip():
                    load_mode = "Templates"
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=("COMMENT", "", str(line.strip())),
                )
            elif (
                line.strip() == "// ------------------------------"
                and pointer == 1
                #and load_mode != "Templates"
                and line.strip()
            ):
                pointer = 0
                pointed = False
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=("COMMENT", "", str(line.strip())),
                )
            elif (
                load_mode == "RoomChances"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 4)
                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.strip().split("//", 1)
                if len(comments)>1: # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif (
                load_mode == "TileCodes"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 4)
                if any(str(data[0]) in self.s for self.s in self.uni_tile_code_list): # compares tilecode id to its universal tilecode counterpart
                    self.tile_convert.append(str(line)+" 100") # adds tilecode to be converted into universal TileCodes; has no percent value so its 100% likely to spawn
                    print("gonna change " + str(line)+" 100") # structure (id tilecode percent-without-percent-sign)
                else:
                    try:
                        if len(data[0].split("%", 2))==2: # tile with already existing percent
                            self.tile_convert.append(str(data[0].split("%", 2)[0]) + " " + str(data[1]) + " " + str(data[0].split("%", 2)[1].split(" ", 2)[0]) + " None")
                            print("gonna change " + str(data[0].split("%", 2)[0]) + " " + str(data[1]) + " " + str(data[0].split("%", 2)[1].split(" ", 2)[0]) + " None")
                            tkMessageBox.showinfo("Debug", str(data[0].split("%", 2)[0]) + " " + str(data[1]) + " " + str(data[0].split("%", 2)[1].split(" ", 2)[0]) + " None") # 100 default percent value and None default alt tile value
                        elif len(data[0].split("%", 2))==3: # tile with already existing percent and alt tile
                            self.tile_convert.append(str(data[0].split("%", 2)[0]) + " " + str(data[1]) + " " + str(data[0].split("%", 2)[1]) + " " + str(data[0].split("%", 2)[2].split(" ", 2)[0]))
                            print("gonna change " + str(data[0].split("%", 2)[0]) + " " + str(data[1]) + " " + str(data[0].split("%", 2)[1]) + " " + str(data[0].split("%", 2)[2].split(" ", 2)[0]))
                            tkMessageBox.showinfo("Debug", str(data[0].split("%", 2)[0]) + " " + str(data[1]) + " " + str(data[0].split("%", 2)[1] + " " + str(data[0].split("%", 2)[2].split(" ", 2)[0])))
                    except:
                        tkMessageBox.showinfo("Uh Oh!", "skipped " + str(data[0])) # A tilecode id thats missing from the universal database and needs to be added
                        # structure (id tilecode percent-without-percent-sign second-tile)


                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.strip().split("//", 1)
                if len(comments)>1: # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif (
                load_mode == "LevelChances"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 4)
                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.strip().split("//", 1)
                if len(comments)>1: # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif (
                load_mode == "MonsterChances"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 1)
                comment = ""
                value = ""
                if str(data[1]):
                    value = str(data[1])
                comments = line.strip().split("//", 1)
                if len(comments)>1: # Makes sure a comment even exists
                    comment = comments[1]
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(value), str(comment)),
                )
            elif load_mode == "Templates":
                if (
                    line.strip() == "/" * 80
                    and not pointed
                    and pointer == 0
                    and line.strip()
                ):
                    pointer = 1
                elif not pointed and pointer == 1 and line.strip().startswith("\.") and line.strip():
                    if self.tree_levels.item(self.tree_levels.get_children()[0])["text"]=="placeholder":
                        self.tree_levels.item(self.tree_levels.get_children()[0],values=line.strip(), text=line.strip())
                    else:
                        self.node = self.tree_levels.insert(
                        "", "end", values=line.strip(), text=line.strip()
                    )
                    pointed = True
                elif (
                    line.strip() == "/" * 80
                    and pointed == True
                    and pointer == 1
                    and line.strip()
                ):
                    pointed = False
                    pointer = 0
                elif line.strip().startswith("//") and pointed == False and line.strip():
                    self.tree.insert(
                        "", "end", text="L1", values=("COMMENT", "", line.strip())
                    )
                elif not line.strip() and len(self.rooms)>0:
                    self.new_room = self.tree_levels.insert(
                        self.node, "end", values=self.rooms, text="room"
                    )
                    self.rooms.clear()
                elif line.strip()=="":
                    pointer = 0
                elif line.strip():
                    converted_room_row = ""
                    if not (str(line).startswith('\!')):
                        for char in str(line): # read each character in room row
                            newChar = str(char)
                            if any(str(" " + char) in self.a for self.a in self.tile_convert): # finds the char in tiles listed for conversion earlier
                                parse = self.a.split(" ", 3) # splits code from its id [0] = id [1] = code [2] = percent value [3] = alt tile
                                if any(str(parse[0] + " ") in self.b for self.b in self.uni_tile_code_list): # finds id of tile needing conversion in the universal tile code list
                                    parseb = self.b.split(" ", 2) # splits code from its id [0] = id [1] = code
                                    print(str(parse[0]) + " converted to " + str(parseb[0]))
                                    newChar = str(parseb[1]) # replaces char with tile code from universal lists
                                #self.tile_convert.append(str(line)) # notes line as needing conversion

                            converted_room_row += str(newChar)
                    else:
                        converted_room_row = str(line)
                    self.rooms.append(str(converted_room_row))
                    print(str(converted_room_row) + " completed")

    def __draw_grid(self, rows, cols, canvas):
        for i in range(0, cols+2):
            canvas.create_line(
                (i) * self.mag, 0, (i) * self.mag, (rows) * self.mag, fill='#fffff1'
            )
        for i in range(0, rows):
            canvas.create_line(
                0, (i) * self.mag, self.mag * (cols+2), (i) * self.mag, fill='#fffff1'
            )
        canvas['width']=self.mag * rows
        canvas['height']=self.mag * cols


class ModlunkyUI:
    def __init__(self, install_dir, beta=False):
        self.install_dir = install_dir
        self.beta = beta
        self.current_version = get_current_version()
        self.latest_version = get_latest_version()
        if self.latest_version is None or self.current_version is None:
            self.needs_update = False
        else:
            self.needs_update = self.current_version < self.latest_version

        self._shutdown_handlers = []
        self._shutting_down = False

        self.root = tk.Tk(className="Modlunky2")
        self.root.title("Modlunky 2")
        self.root.geometry("950x650")
        #self.root.resizable(False, False)
        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.root.iconphoto(False, self.icon_png)

        if self.needs_update:
            update_button = ttk.Button(
                self.root, text="Update Modlunky2!", command=self.update
            )
            update_button.pack()

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.tabs = {}
        self.tab_control = ttk.Notebook(self.root)

        self.register_tab(
            "Pack Assets",
            PackTab(
                tab_control=self.tab_control,
                install_dir=install_dir,
            ),
        )
        self.register_tab(
            "Extract Assets",
            ExtractTab(
                tab_control=self.tab_control,
                install_dir=install_dir,
            ),
        )
        if beta:
            self.register_tab(
                "Levels",
                LevelsTab(
                    tab_control=self.tab_control,
                    install_dir=install_dir,
                ),
            )

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.tab_control.pack(expand=1, fill="both")

        self.console = ConsoleWindow()

    def update(self):
        webbrowser.open_new_tab(
            f"https://github.com/spelunky-fyi/modlunky2/releases/tag/{self.latest_version}"
        )

    def self_update(self):
        updater = Path(cwd + "/updater.exe")
        subprocess.call([updater])  # if file exists
        self.root.quit()
        self.root.destroy()

    def on_tab_change(self, event):
        tab = event.widget.tab("current")["text"]
        self.tabs[tab].on_load()

    def register_tab(self, name, obj):
        self.tabs[name] = obj
        self.tab_control.add(obj, text=name)

    def quit(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        logger.info("Shutting Down.")
        for handler in self._shutdown_handlers:
            handler()

        self.root.quit()
        self.root.destroy()

    def register_shutdown_handler(self, func):
        self._shutdown_handlers.append(func)

    def mainloop(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()
