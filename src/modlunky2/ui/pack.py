import logging
import shutil
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.exc import MissingAsset
from modlunky2.assets.hashing import md5sum_path
from modlunky2.assets.patcher import Patcher
from modlunky2.config import Config
from modlunky2.constants import BASE_DIR
from modlunky2.ui.widgets import ScrollableLabelFrame, Tab, ToolTip
from modlunky2.utils import is_patched

logger = logging.getLogger("modlunky2")

MODS = Path("Mods")


def pack_assets(_call, install_dir, packs):
    mods_dir = install_dir / MODS
    extract_dir = mods_dir / "Extracted"
    source_exe = extract_dir / "Spel2.exe"
    dest_exe = install_dir / "Spel2.exe"

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
            logger.critical(
                (
                    "%s appears to be a new version. You need to extract before packing again."
                ),
                dest_exe,
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


class WarningFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.columnconfigure(0, minsize=20)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        self.color_bar = tk.Frame(self, bg="red", width=20)
        self.color_bar.grid(row=0, column=0, sticky="nswe")

        self.label = ttk.Label(
            self,
            text=(
                "Packing is deprecated and continues to exist solely for legacy support.\n"
                "The playlunky tab is the primary supported method for playing mods.\n\n"
                "Packing is broken after 1.21.0c of Spelunky 2.\n"
                "This tab continues to exist for support of older versions."
            ),
            font="sans 12 bold",
            justify=tk.CENTER,
            anchor="e",
        )
        self.label.grid(row=0, column=1, sticky="nswe")
        self.label.bind(
            "<Configure>",
            lambda e: self.label.config(wraplength=self.winfo_width() - 60),
        )

        self.color_bar = tk.Frame(self, bg="red", width=20)
        self.color_bar.grid(row=0, column=2, sticky="nse")


class PackTab(Tab):
    def __init__(
        self, tab_control, modlunky_config: Config, task_manager, *args, **kwargs
    ):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager
        self.task_manager.register_task(
            "pack_assets",
            pack_assets,
            True,
            on_complete="pack_finished",
        )
        self.task_manager.register_handler("pack_finished", self.pack_finished)

        self.rowconfigure(0, minsize=60)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, minsize=60, weight=0)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        self.warning = WarningFrame(self)
        self.warning.grid(row=0, column=0, columnspan=3, pady=5, padx=5, sticky="nswe")

        self.frame = ScrollableLabelFrame(self, text="Select mods to pack")
        self.frame.grid(row=1, column=0, columnspan=3, pady=5, padx=5, sticky="nswe")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.button_pack = ttk.Button(self, text="Pack", command=self.pack)
        self.button_pack.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_pack, "Pack modded assets into the EXE.")

        self.button_restore = ttk.Button(self, text="Restore EXE", command=self.restore)
        self.button_restore.grid(row=2, column=1, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_restore, "Restore EXE to vanilla state from backup.")

        self.button_validate = ttk.Button(
            self, text="Validate Game Files", command=self.validate
        )
        self.button_validate.grid(row=2, column=2, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_validate, "Redownload vanilla EXE from steam.")

        default_icon_path = BASE_DIR / "static/images/folder.png"
        self.default_icon = ImageTk.PhotoImage(Image.open(default_icon_path))

        self.checkbox_vars = []

    def pack_finished(self):
        self.button_pack["state"] = tk.NORMAL
        self.button_restore["state"] = tk.NORMAL
        self.button_validate["state"] = tk.NORMAL

    @staticmethod
    def validate():
        webbrowser.open_new_tab("steam://validate/418530")

    def restore(self):
        mods_dir = self.modlunky_config.install_dir / MODS
        extract_dir = mods_dir / "Extracted"
        source_exe = extract_dir / "Spel2.exe"
        dest_exe = self.modlunky_config.install_dir / "Spel2.exe"

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
            self.modlunky_config.install_dir / "Mods" / exe.get()
            for exe in self.checkbox_vars
            if exe.get()
        ]
        self.button_pack["state"] = tk.DISABLED
        self.button_restore["state"] = tk.DISABLED
        self.button_validate["state"] = tk.DISABLED
        self.task_manager.call(
            "pack_assets", install_dir=self.modlunky_config.install_dir, packs=packs
        )

    def get_packs(self):
        pack_dirs = []
        packs_dir = self.modlunky_config.install_dir / "Mods" / "Packs"
        if packs_dir.exists():
            for dir_ in packs_dir.iterdir():
                if not dir_.is_dir():
                    continue
                if dir_.name == ".db":
                    continue
                pack_dirs.append(
                    dir_.relative_to(
                        self.modlunky_config.install_dir / "Mods" / "Packs"
                    )
                )

        return pack_dirs

    def on_load(self):
        for child in self.frame.winfo_children():
            child.destroy()
        self.checkbox_vars.clear()

        for idx, exe in enumerate(self.get_packs()):
            str_var = tk.StringVar()
            item = ttk.Checkbutton(
                self.frame,
                text=f" {exe}",
                image=self.default_icon,
                style="ModList.TCheckbutton",
                variable=str_var,
                onvalue=f"{exe}",
                offvalue="",
                compound="left",
            )
            self.checkbox_vars.append(str_var)
            item.grid(row=idx, column=0, pady=5, padx=5, sticky="w")
