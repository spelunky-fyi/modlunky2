import logging
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from ctypes.util import find_library  # pylint: disable=unused-import

from fsb5.utils import load_lib, LibraryNotFoundException

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.constants import (
    EXTRACTED_DIR,
    FILEPATH_DIRS,
    OVERRIDES_DIR,
    PACKS_DIR,
)
from modlunky2.utils import is_patched, open_directory
from modlunky2.ui.widgets import Tab, ToolTip
from modlunky2.assets.soundbank import Extension as SoundExtension

logger = logging.getLogger("modlunky2")


MODS = Path("Mods")

TOP_LEVEL_DIRS = [EXTRACTED_DIR, PACKS_DIR, OVERRIDES_DIR]


def try_load_vorbis():
    try:
        load_lib("vorbis")
        return True
    except LibraryNotFoundException:
        return False


def extract_assets(
    _call,
    install_dir,
    target,
    recompress,
    generate_string_hashes,
    create_entity_sheets,
    extract_sound_extensions,
    reuse_extracted,
):
    exe_filename = install_dir / target

    if is_patched(exe_filename):
        logger.critical(
            (
                "%s is a patched exe. Can't extract. You should Restore Exe"
                " or validate game files to get a clean exe before Extracting."
            ),
            exe_filename,
        )
        return

    mods_dir = install_dir / MODS

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
            recompress=recompress,
            generate_string_hashes=generate_string_hashes,
            create_entity_sheets=create_entity_sheets,
            extract_sound_extensions=extract_sound_extensions,
            reuse_extracted=reuse_extracted,
        )

    for asset in unextracted:
        logger.warning("Un-extracted Asset %s", asset.asset_block)

    dest = mods_dir / EXTRACTED_DIR / "Spel2.exe"
    if not reuse_extracted and exe_filename != dest:
        logger.info("Backing up exe to %s", dest)
        shutil.copy2(exe_filename, dest)

    logger.info("Extraction complete!")


class ExtractTab(Tab):
    def __init__(self, tab_control, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager
        self.task_manager.register_task(
            "extract:extract_assets",
            extract_assets,
            True,
            on_complete="extract:extract_finished",
        )
        self.task_manager.register_handler(
            "extract:extract_finished", self.extract_finished
        )

        self.vorbis_loaded = try_load_vorbis()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, minsize=60)

        self.top_frame = ttk.Frame(self)
        self.top_frame.rowconfigure(0, minsize=60)
        self.top_frame.rowconfigure(1, weight=1)
        self.top_frame.columnconfigure(0, weight=1)
        self.top_frame.columnconfigure(1, minsize=250)
        self.top_frame.grid(row=0, column=0, sticky="nswe")

        self.exe_frame = ttk.LabelFrame(self.top_frame, text="Select exe to Extract")
        self.exe_frame.grid(row=0, column=0, rowspan=2, pady=5, padx=5, sticky="nswe")
        self.exe_frame.rowconfigure(0, weight=1)

        self.exe_frame.columnconfigure(0, weight=1)
        self.exe_frame.columnconfigure(1)

        self.list_box = tk.Listbox(self.exe_frame)
        self.list_box.grid(row=0, column=0, sticky="nswe")
        self.scrollbar = ttk.Scrollbar(self.exe_frame)
        self.scrollbar.grid(row=0, column=1, sticky="nes")

        self.button_open = ttk.Button(
            self.top_frame, text="Open Extract Dir", command=self.open_extract_dir
        )
        self.button_open.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

        self.config_frame = ttk.LabelFrame(self.top_frame, text="Options")
        self.config_frame.grid(row=1, column=1, pady=5, padx=5, sticky="nswe")

        self.recompress = tk.BooleanVar()
        self.recompress.set(False)
        self.checkbox_recompress = ttk.Checkbutton(
            self.config_frame,
            text="Recompress",
            variable=self.recompress,
            onvalue=True,
            offvalue=False,
        )
        self.checkbox_recompress.grid(row=0, sticky="nw")
        ToolTip(
            self.checkbox_recompress,
            (
                "Recompress assets to speed up futuring packing.\n"
                "Not necessary if you just want the extracted assets."
            ),
        )

        self.create_entity = tk.BooleanVar()
        self.create_entity.set(True)
        self.checkbox_create_entity = ttk.Checkbutton(
            self.config_frame,
            text="Create Entity Sprites",
            variable=self.create_entity,
            onvalue=True,
            offvalue=False,
        )
        self.checkbox_create_entity.grid(row=1, sticky="nw")
        ToolTip(
            self.checkbox_create_entity,
            (
                "Create merged entity spritesheets. These provide a simpler\n"
                "interface to some entity mods."
            ),
        )

        self.generate_string_hashes = tk.BooleanVar()
        self.generate_string_hashes.set(True)
        self.checkbox_string_hashes = ttk.Checkbutton(
            self.config_frame,
            text="Generate String Hashes",
            variable=self.generate_string_hashes,
            onvalue=True,
            offvalue=False,
        )
        self.checkbox_string_hashes.grid(row=2, sticky="nw")
        ToolTip(
            self.checkbox_string_hashes,
            (
                "Generate string hash files. These provide a better\n"
                "interface for creating mods that use strings."
            ),
        )

        self.extract_wavs = tk.BooleanVar()
        self.extract_wavs.set(False)
        self.checkbox_extract_wavs = ttk.Checkbutton(
            self.config_frame,
            text="Extract .wav files",
            variable=self.extract_wavs,
            onvalue=True,
            offvalue=False,
        )
        self.checkbox_extract_wavs.grid(row=3, sticky="nw")
        ToolTip(self.checkbox_extract_wavs, ("Extract .wav files from the soundbank."))

        oggs_state = tk.NORMAL
        if not self.vorbis_loaded:
            oggs_state = tk.DISABLED
        self.extract_oggs = tk.BooleanVar()
        self.extract_oggs.set(False)
        self.checkbox_extract_oggs = ttk.Checkbutton(
            self.config_frame,
            state=oggs_state,
            text="Extract .ogg files",
            variable=self.extract_oggs,
            onvalue=True,
            offvalue=False,
        )
        self.checkbox_extract_oggs.grid(row=4, sticky="nw")
        ToolTip(self.checkbox_extract_oggs, ("Extract .ogg files from the soundbank."))

        self.reuse_extracted = tk.BooleanVar()
        self.reuse_extracted.set(False)
        self.checkbox_reuse_extracted = ttk.Checkbutton(
            self.config_frame,
            text="Reuse Extracted Assets",
            variable=self.reuse_extracted,
            onvalue=True,
            offvalue=False,
        )
        self.checkbox_reuse_extracted.grid(row=5, sticky="nw")
        ToolTip(
            self.checkbox_reuse_extracted,
            (
                "If checked we will not re-extract from the binary\n"
                "and only rerun post processing steps."
            ),
        )

        self.list_box.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.list_box.yview)

        self.button_extract = ttk.Button(self, text="Extract", command=self.extract)
        self.button_extract.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")
        ToolTip(self.button_extract, ("Extract assets from EXE."))

    def open_extract_dir(self):
        extract_dir = self.modlunky_config.install_dir / MODS / EXTRACTED_DIR
        open_directory(extract_dir)

    def extract_finished(self):
        self.button_extract["state"] = tk.NORMAL

    def extract(self):
        idx = self.list_box.curselection()
        if not idx:
            logger.error("Didn't select exe")
            return

        self.button_extract["state"] = tk.DISABLED

        extract_sound_extensions = []
        if self.extract_wavs.get():
            extract_sound_extensions.append(SoundExtension.WAV)

        if self.extract_oggs.get():
            extract_sound_extensions.append(SoundExtension.OGG)

        selected_exe = self.list_box.get(idx)
        self.task_manager.call(
            "extract:extract_assets",
            install_dir=self.modlunky_config.install_dir,
            target=selected_exe,
            recompress=self.recompress.get(),
            generate_string_hashes=self.generate_string_hashes.get(),
            create_entity_sheets=self.create_entity.get(),
            extract_sound_extensions=extract_sound_extensions,
            reuse_extracted=self.reuse_extracted.get(),
        )

    def get_exes(self):
        exes = []
        # Don't recurse forever. 3 levels should be enough
        exes.extend(self.modlunky_config.install_dir.glob("*.exe"))
        exes.extend(self.modlunky_config.install_dir.glob("*/*.exe"))
        exes.extend(self.modlunky_config.install_dir.glob("*/*/*.exe"))
        return [
            exe.relative_to(self.modlunky_config.install_dir)
            for exe in exes
            # Exclude modlunky2 which is likely in the install directory
            if exe.name not in ["modlunky2.exe"]
        ]

    def on_load(self):
        self.list_box.delete(0, tk.END)
        for exe in self.get_exes():
            self.list_box.insert(tk.END, str(exe))
