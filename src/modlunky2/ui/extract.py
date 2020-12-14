import logging
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.constants import (
    EXTRACTED_DIR,
    FILEPATH_DIRS,
    OVERRIDES_DIR,
    PACKS_DIR,
)
from modlunky2.ui.utils import is_patched, log_exception
from modlunky2.ui.widgets import Tab

logger = logging.getLogger("modlunky2")


MODS = Path("Mods")

TOP_LEVEL_DIRS = [EXTRACTED_DIR, PACKS_DIR, OVERRIDES_DIR]


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
