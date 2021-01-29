import logging
import shutil
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.exc import MissingAsset
from modlunky2.assets.hashing import md5sum_path
from modlunky2.assets.patcher import Patcher
from modlunky2.constants import BASE_DIR
from modlunky2.ui.utils import is_patched, log_exception
from modlunky2.ui.widgets import ScrollableFrame, Tab, ToolTip

logger = logging.getLogger("modlunky2")

MODS = Path("Mods")


class PackTab(Tab):
    def __init__(self, tab_control, install_dir, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.install_dir = install_dir

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, minsize=60)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)


        self.frame = ScrollableFrame(self, text="Select mods to pack")
        self.frame.grid(row=0, column=0, columnspan=3, pady=5, padx=5, sticky="nswe")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.button_pack = ttk.Button(self, text="Pack", command=self.pack)
        self.button_pack.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_pack, "Pack modded assets into the EXE.")

        self.button_restore = ttk.Button(self, text="Restore EXE", command=self.restore)
        self.button_restore.grid(row=1, column=1, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_restore, "Restore EXE to vanilla state from backup.")

        self.button_validate = ttk.Button(self, text="Validate Game Files", command=self.validate)
        self.button_validate.grid(row=1, column=2, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_validate, "Redownload vanilla EXE from steam.")

        default_icon_path = BASE_DIR / "static/images/noicon.png"
        self.default_icon = ImageTk.PhotoImage(Image.open(default_icon_path))

        self.checkbox_vars = []

    @staticmethod
    def validate():
        webbrowser.open_new_tab("steam://validate/418530")

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

        logger.info("Starting Pack of %s", source_exe)
        if is_patched(source_exe):
            logger.critical(
                "Source exe (%s) is somehow patched. You need to re-extract.", source_exe
            )
            return

        # If the destination isn't patched we want to check if it differs
        # from the source exe as new updates are a regular point of confusion
        # for users.
        if not is_patched(dest_exe):
            logger.info("Checking for new release...")
            logger.info("Hashing %s", source_exe)
            src_md5 = md5sum_path(source_exe)
            logger.info("Hashing %s", dest_exe)
            dest_md5 = md5sum_path(dest_exe)
            if src_md5 != dest_md5:
                logger.critical((
                    "%s appears to be a new version. You need to extract before packing again."
                ), dest_exe)
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
