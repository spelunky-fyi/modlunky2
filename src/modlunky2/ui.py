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

        self.frame = ScrollableFrame(self, text="Select mods to pack")
        self.frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(self, length=100, mode="determinate")
        self.progress.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        self.button_pack = ttk.Button(self, text="Pack", command=self.pack)
        self.button_pack.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")

        default_icon_path = BASE_DIR / "static/images/noicon.png"
        self.default_icon = ImageTk.PhotoImage(Image.open(default_icon_path))

        self.checkbox_vars = []

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

        for dir_ in (self.install_dir / "Mods" / "Packs").iterdir():
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
        self.rowconfigure(1, minsize=60)

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

        self.button_extract = ttk.Button(self, text="Extract", command=self.extract)
        self.button_extract.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

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

        self.columnconfigure(0, minsize=200)  # Column 0 = Level List
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
        self.my_list = os.listdir(
            self.install_dir / "Mods" / "Extracted" / "Data" / "Levels"
        )
        self.tree_files.grid(row=0, column=0, rowspan=4, sticky="nswe")
        self.vsb_tree_files.grid(row=0, column=0, sticky="nse")

        for file in self.my_list:
            self.tree_files.insert("", "end", values=str(file), text=str(file))

        # Seperates Level Rules and Level Editor into two tabs
        self.tab_control = ttk.Notebook(self)

        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)

        self.tab_control.add(
            self.tab1, text="Rules"
        )  # Rules Tab ----------------------------

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

        self.tab_control.add(
            self.tab2, text="Level Editor"
        )  # Level Editor Tab ----------------------------
        self.tab2.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.tab2.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.tab2.rowconfigure(0, weight=1)  # Row 0 = List box / Label

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

        self.mag = 70
        self.rows = 6
        self.cols = 7

        self.canvas = tk.Canvas(
            self.tab2,
            width=self.mag * self.cols,
            height=self.mag * self.rows,
            bg="white",
        )

        # Create a grid of None to store the references to the tiles
        tiles = [[None for _ in range(self.cols)] for _ in range(self.rows)]

        def callback(event):
            # Get rectangle diameters
            col_width = self.mag
            row_height = self.mag
            # Calculate column and row number
            col = event.x // col_width
            row = event.y // row_height
            # If the tile is not filled, create a rectangle
            if not tiles[int(row)][int(col)]:
                tiles[int(row)][int(col)] = self.canvas.create_rectangle(
                    col * col_width,
                    row * row_height,
                    (col + 1) * col_width,
                    (row + 1) * row_height,
                    fill="black",
                )
            # If the tile is filled, delete the rectangle and clear the reference
            else:
                self.canvas.delete(tiles[int(row)][int(col)])
                tiles[int(row)][int(col)] = None

        self.canvas.bind("<Button-1>", callback)

        self.__draw_grid()
        self.canvas.grid(row=0, column=1, columnspan=1)

        def tree_filesitemclick(_event):
            # Using readlines()
            item_text = ""
            for item in self.tree_files.selection():
                item_text = self.tree_files.item(item, "text")
                self.read_lvl_file(item_text)

        self.tree_files.bind("<ButtonRelease-1>", tree_filesitemclick)

    def read_lvl_file(self, lvl):
        file1 = open(
            self.install_dir / "Mods" / "Extracted" / "Data" / "Levels" / lvl, "r"
        )
        lines = file1.readlines()

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

        for line in lines:
            line = " ".join(line.split())  # remove duplicate spaces
            print(line)
            if (
                line.strip() == "// ------------------------------"
                and not pointed
                and pointer == 0
                and load_mode != "Templates"
                and line.strip()
            ):
                pointer = pointer + 1
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
            elif (
                line.strip() == "// ------------------------------"
                and pointer
                and pointer == 1
                and load_mode != "Templates"
                and line.strip()
            ):
                pointer = 0
                pointed = False
            elif (
                load_mode == "RoomChances"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 4)
                comment = line.strip().split("//", 1)
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(data[1]), str(comment[0])),
                )
            elif (
                load_mode == "TileCodes"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 4)
                blocks.append(str(data[0]))
            elif (
                load_mode == "LevelChances"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 4)
                comment = line.strip().split("//", 1)
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(data[1]), str(comment[0])),
                )
            elif (
                load_mode == "MonsterChances"
                and not pointed
                and pointer == 0
                and line.strip()
            ):
                data = line.strip().split(" ", 3)
                comment = line.strip().split("//", 1)
                self.tree.insert(
                    "",
                    "end",
                    text="L1",
                    values=(str(data[0]), str(data[1]), str(comment[0])),
                )
            elif load_mode == "Templates":
                if line.strip().startswith("// "):
                    self.tree.insert(
                        "", "end", text="L1", values=("", line.strip(), "")
                    )
                elif (
                    line.strip() == "/" * 80
                    and not pointed
                    and pointer == 0
                    and line.strip()
                ):
                    pointer = pointer + 1
                elif not pointed and pointer == 1 and line.strip():
                    self.node = self.tree_levels.insert(
                        "", "end", values=line.strip(), text=line.strip()
                    )
                    pointed = True
                elif (
                    line.strip() == "/" * 80
                    and pointed
                    and pointer == 1
                    and line.strip()
                ):
                    pointed = False
                    pointer = 0
                elif not line.strip() and self.rooms is not None:
                    self.tree_levels.insert(
                        self.node, "end", values=self.rooms, text="room template"
                    )
                    self.rooms.clear()
                else:
                    self.rooms.append(line.strip)

    def __draw_grid(self):
        for i in range(0, self.cols):
            self.canvas.create_line(
                (i) * self.mag, 0, (i) * self.mag, (self.rows) * self.mag
            )
        for i in range(0, self.rows):
            self.canvas.create_line(
                0, (i) * self.mag, self.mag * (self.cols), (i) * self.mag
            )

    def draw_circle(self, row, col, player_num):  # for testing purposes
        if player_num == 1:
            fill_color = "red"
        elif player_num == 2:
            fill_color = "black"
        # (startx, starty, endx, endy)
        self.canvas.create_oval(
            col * self.mag,
            row * self.mag,
            (col + 1) * self.mag,
            (row + 1) * self.mag,
            fill=fill_color,
        )


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
        self.root.resizable(False, False)
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
        self.register_tab(
            "Levels",
            LevelsTab(
                tab_control=self.tab_control,
                install_dir=install_dir,
            ),
            self.beta
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

    def register_tab(self, name, obj, display=True):
        if not display:
            return
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
