import logging
import queue
import shutil
import threading
import tkinter as tk
import webbrowser
from functools import wraps
from pathlib import Path
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import requests
from packaging import version

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.constants import (EXTRACTED_DIR, FILEPATH_DIRS,
                                        OVERRIDES_DIR, PACKS_DIR)
from modlunky2.assets.exc import MissingAsset
from modlunky2.assets.patcher import Patcher
from modlunky2.constants import ROOT_DIR

logger = logging.getLogger("modlunky2")


MODS = Path("Mods")

TOP_LEVEL_DIRS = [
    EXTRACTED_DIR,
    PACKS_DIR,
    OVERRIDES_DIR
]


def is_patched(exe_filename):
    with exe_filename.open("rb") as exe:
        return Patcher(exe).is_patched()


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
        #self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.close)

        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(self, state='disabled')
        self.scrolled_text.pack(expand=True, fill="both")
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='green')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)

        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        logger.addHandler(self.queue_handler)

        # Start polling messages from the queue
        self.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
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


class PackTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.install_dir = install_dir

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, minsize=60)

        self.label_frame = ttk.LabelFrame(self, text="Select Mods to pack")
        self.label_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")
        self.label_frame.rowconfigure(0, weight=1)
        self.label_frame.columnconfigure(0, weight=1)

        self.scrollbar = ttk.Scrollbar(self.label_frame)
        self.scrollbar.grid(row=0, column=1, sticky="nes")

        self.list_box = tk.Listbox(self.label_frame, selectmode=tk.MULTIPLE)
        self.list_box.grid(row=0, column=0, sticky="nswe")

        self.list_box.config(yscrollcommand = self.scrollbar.set)
        self.scrollbar.config(command = self.list_box.yview)

        self.button_pack = ttk.Button(self, text="Pack", command=self.pack)
        self.button_pack.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

    def pack(self):
        packs = [
            self.install_dir / "Mods" / self.list_box.get(idx)
            for idx in self.list_box.curselection()
        ]
        thread = threading.Thread(
            target=self.repack_assets, args=(packs,)
        )
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
        self.list_box.delete(0, tk.END)
        for exe in self.get_packs():
            self.list_box.insert(tk.END, str(exe))

    @log_exception
    def repack_assets(self, packs):
        mods_dir = self.install_dir / MODS
        extract_dir = mods_dir / "Extracted"
        source_exe = extract_dir / "Spel2.exe"
        dest_exe = self.install_dir / "Spel2.exe"

        if is_patched(source_exe):
            logger.critical("Source exe (%s) is somehow patched. You need to re-extract.")
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
            patcher.patch()
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

        self.list_box.config(yscrollcommand = self.scrollbar.set)
        self.scrollbar.config(command = self.list_box.yview)

        self.button_extract = ttk.Button(self, text="Extract", command=self.extract)
        self.button_extract.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

    def extract(self):
        idx = self.list_box.curselection()
        if not idx:
            return

        selected_exe = self.list_box.get(idx)
        thread = threading.Thread(
            target=self.extract_assets, args=(selected_exe,)
        )
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
            (mods_dir / ".compressed" / EXTRACTED_DIR / dir_).mkdir(parents=True, exist_ok=True)

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


class ModlunkyUI:
    def __init__(self, install_dir):
        self.install_dir = install_dir
        self.current_version = get_current_version()
        self.latest_version = get_latest_version()
        self.needs_update = self.current_version < self.latest_version

        self._shutdown_handlers = []
        self._shutting_down = False

        self.root = tk.Tk()
        self.root.title("Modlunky 2")
        self.root.geometry('750x450')
        self.root.resizable(False, False)

        if self.needs_update:
            update_button = ttk.Button(
                self.root, text="Update Modlunky2!", command=self.update,
            )
            update_button.pack()

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.tabs = {}
        self.tab_control = ttk.Notebook(self.root)

        self.register_tab("Pack Assets", PackTab(
            tab_control=self.tab_control,
            install_dir=install_dir,
        ))
        self.register_tab("Extract Assets", ExtractTab(
            tab_control=self.tab_control,
            install_dir=install_dir,
        ))

        self.tab_control.bind('<<NotebookTabChanged>>', self.on_tab_change)
        self.tab_control.pack(expand=1, fill="both")

        self.console = ConsoleWindow()

    def update(self):
        webbrowser.open_new_tab(
            f"https://github.com/spelunky-fyi/modlunky2/releases/tag/{self.latest_version}"
        )

    def on_tab_change(self, event):
        tab = event.widget.tab('current')['text']
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
