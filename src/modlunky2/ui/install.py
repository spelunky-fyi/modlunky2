import json
import logging
import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import requests
from requests import HTTPError

from modlunky2.ui.widgets import Tab, Entry

logger = logging.getLogger("modlunky2")


class SourceChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text="Source",
            font="sans 11 bold",
        ).grid(row=0, column=0, padx=5, sticky="ew")

        file_chooser_label = ttk.Label(self, text="Choose the file you want to install")
        file_chooser_label.grid(
            row=1, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.file_chooser_var = tk.StringVar()
        file_chooser_entry = ttk.Entry(
            self,
            textvariable=self.file_chooser_var,
            state=tk.DISABLED,
        )
        file_chooser_entry.columnconfigure(0, weight=1)
        file_chooser_entry.columnconfigure(1, weight=1)
        file_chooser_entry.columnconfigure(2, weight=1)
        file_chooser_entry.grid(
            row=2, column=0, padx=5, pady=5, columnspan=3, sticky="nsew"
        )

        file_chooser_browse = ttk.Button(self, text="Browse", command=self.browse)
        file_chooser_browse.grid(row=3, column=0, pady=5, padx=5, sticky="nsew")

    def browse(self):
        initial_dir = Path(self.modlunky_config.config_file.last_install_browse)
        if not initial_dir.exists():
            initial_dir = Path("/")

        filename = tk.filedialog.askopenfilename(parent=self, initialdir=initial_dir)
        if not filename:
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        self.file_chooser_var.set(filename)
        parent = Path(filename).parent

        self.modlunky_config.config_file.last_install_browse = str(parent.as_posix())
        self.modlunky_config.config_file.save()
        self.master.master.render()


class DestinationChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text="Destination",
            font="sans 11 bold",
        ).grid(row=0, column=0, padx=5, sticky="ew")
        file_chooser_label = ttk.Label(self, text="Choose or Create a Pack")
        file_chooser_label.grid(
            row=1, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.file_chooser_var = tk.StringVar()

        file_chooser_entry = ttk.Entry(
            self,
            textvariable=self.file_chooser_var,
            state=tk.DISABLED,
        )
        file_chooser_entry.columnconfigure(0, weight=1)
        file_chooser_entry.columnconfigure(1, weight=1)
        file_chooser_entry.columnconfigure(2, weight=1)
        file_chooser_entry.grid(
            row=2, column=0, padx=5, pady=5, columnspan=3, sticky="nsew"
        )

        file_chooser_browse = ttk.Button(self, text="Browse", command=self.browse)
        file_chooser_browse.grid(row=3, column=0, pady=5, padx=5, sticky="nsew")

    def browse(self):
        initial_dir = self.modlunky_config.install_dir / "Mods/Packs"
        if not initial_dir.exists():
            logger.critical("Expected Packs dir not found.")
            return

        directory = tk.filedialog.askdirectory(parent=self, initialdir=initial_dir)
        if not directory:
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        initial_dir = initial_dir.resolve()
        directory = Path(directory).resolve()

        if initial_dir == directory:
            logger.critical(
                "You must create a directory inside of Packs to install your mod into."
            )
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        # Directory chosen Packs or above
        if initial_dir not in directory.parents:
            logger.critical("You chose a directory outside of Packs which is invalid.")
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        # Directory chosen inside of a pack directory
        relative_pack_dir = directory.relative_to(initial_dir)
        if len(relative_pack_dir.parts) != 1:
            logger.critical(
                "You must choose a directory only one level deep inside of Packs."
            )
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        self.file_chooser_var.set(relative_pack_dir)
        self.master.master.render()


def install_local_mod(call, install_dir: Path, source: Path, pack: str):
    packs_dir = install_dir / "Mods/Packs"
    dest_dir = packs_dir / pack

    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)

    if source.suffix == ".zip":
        logger.info("Extracting %s to %s", source.name, dest_dir)
        shutil.unpack_archive(source, dest_dir)
    else:
        logger.info("Copying file %s to %s", source.name, dest_dir)
        shutil.copy(source.resolve(), dest_dir.resolve())

    logger.info("Finished installing %s to %s", source.name, dest_dir)
    call("play:reload")


class LocalInstall(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(parent, text="Local Installation", *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.task_manager.register_task(
            "install:install_local_mod",
            install_local_mod,
            True,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, minsize=60)

        source_frame = ttk.Frame(self)
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)
        source_frame.grid(row=0, column=0, pady=5, sticky="nswe")

        self.file_chooser_frame = SourceChooser(source_frame, modlunky_config)
        self.file_chooser_frame.grid(row=0, column=0, pady=5, sticky="new")

        dest_frame = ttk.Frame(self)
        dest_frame.rowconfigure(0, weight=1)
        dest_frame.columnconfigure(0, weight=1)
        dest_frame.grid(row=1, column=0, pady=5, sticky="nswe")

        self.file_chooser_frame2 = DestinationChooser(dest_frame, modlunky_config)
        self.file_chooser_frame2.grid(row=0, column=0, pady=5, sticky="new")

        self.button_install = ttk.Button(self, text="Install", command=self.install)
        self.button_install.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")

    def install(self):
        source = Path(self.file_chooser_frame.file_chooser_var.get())
        pack = self.file_chooser_frame2.file_chooser_var.get()

        if not all([source, pack]):
            logger.critical("Attempted to install mod with missing source and pack")
            return

        self.file_chooser_frame.file_chooser_var.set("")
        self.file_chooser_frame2.file_chooser_var.set("")
        self.render()

        self.task_manager.call(
            "install:install_local_mod",
            install_dir=self.modlunky_config.install_dir,
            source=source,
            pack=pack,
        )

    def render(self):
        source = self.file_chooser_frame.file_chooser_var.get()
        dest = self.file_chooser_frame2.file_chooser_var.get()
        if source and dest:
            self.button_install["state"] = tk.NORMAL
        else:
            self.button_install["state"] = tk.DISABLED


def write_manifest(dest_dir: Path, mod_details, latest_mod_file):
    manifest = {
        "name": mod_details["name"],
        "slug": mod_details["slug"],
        "description": mod_details["description"],
        "mod_file": {
            "id": latest_mod_file["id"],
            "created_at": latest_mod_file["created_at"],
            "download_url": latest_mod_file["download_url"],
        },
    }

    with (dest_dir / "manifest.json").open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file)


def install_fyi_mod(
    call, install_dir: Path, spelunky_fyi_root: str, api_token: str, install_code: str
):
    packs_dir = install_dir / "Mods/Packs"

    url = f"{spelunky_fyi_root}api/mods/{install_code}/"
    logger.debug("Checking for mod at %s", url)
    response = requests.get(
        url,
        headers={
            "Authorization": f"Token {api_token}",
        },
    )

    if response.status_code == 401:
        logger.critical(
            "Request was unauthorized. Make sure you have a valid API token."
        )
        return

    if response.status_code == 404:
        logger.critical("No mod found with install code: %s", install_code)
        return

    try:
        response.raise_for_status()
    except HTTPError:
        logger.critical("Failed to download mod. Try again later.")
        return

    mod_details = response.json()
    if not mod_details["mod_files"]:
        logger.critical("Mod `%s` has no files to download.", install_code)
        return

    latest_mod_file = mod_details["mod_files"][0]

    dest_dir = packs_dir / f"fyi.{install_code}"
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)

    write_manifest(dest_dir, mod_details, latest_mod_file)

    # TODO:
    #    Download Logo
    #    Download file
    #    Handle collisions

    # if source.suffix == ".zip":
    #     logger.info("Extracting %s to %s", source.name, dest_dir)
    #     shutil.unpack_archive(source, dest_dir)
    # else:
    #     logger.info("Copying file %s to %s", source.name, dest_dir)
    #     shutil.copy(source.resolve(), dest_dir.resolve())

    logger.info("Finished installing %s to %s", install_code, dest_dir)
    call("play:reload")


class FyiInstall(ttk.LabelFrame):
    VALID_SLUG = re.compile(r"^[-\w]+$")

    def __init__(self, parent, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(parent, text="spelunky.fyi Installation", *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.task_manager.register_task(
            "install:install_fyi_mod",
            install_fyi_mod,
            True,
        )

        frame = ttk.Frame(self)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(4, minsize=60)
        frame.grid(row=0, column=0, sticky="nswe")

        ttk.Label(
            frame,
            text="Install Code",
            font="sans 11 bold",
        ).grid(row=1, column=0, padx=5, sticky="ew")
        ttk.Label(
            frame,
            text="Enter the 'Install Code' from a mod page on spelunky.fyi",
        ).grid(row=2, column=0, padx=5, sticky="ew")

        self.entry = Entry(frame)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.grid(row=3, column=0, pady=5, padx=5, sticky="new")

        self.button_install = ttk.Button(frame, text="Install", command=self.install)
        self.button_install.grid(row=4, column=0, pady=5, padx=5, sticky="nswe")

    def install(self):

        spelunky_fyi_root = self.modlunky_config.config_file.spelunky_fyi_root
        api_token = self.modlunky_config.config_file.spelunky_fyi_api_token
        if not api_token:
            logger.warning(
                "This feature requires an API token. You can set one on your Config tab."
            )
            return

        install_code = self.entry.get().strip()
        if not self.VALID_SLUG.match(install_code):
            logger.critical("Invalid Install Code...")
            return

        self.entry.delete(0, "end")
        self.render()
        self.task_manager.call(
            "install:install_fyi_mod",
            install_dir=self.modlunky_config.install_dir,
            spelunky_fyi_root=spelunky_fyi_root,
            api_token=api_token,
            install_code=install_code,
        )

    def render(self):
        install_code = self.entry.get().strip()
        if install_code:
            self.button_install["state"] = tk.NORMAL
        else:
            self.button_install["state"] = tk.DISABLED

    def _on_key(self, _event):
        self.render()


class InstallTab(Tab):
    def __init__(self, tab_control, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        self.fyi_install = FyiInstall(self, modlunky_config, task_manager)
        self.fyi_install.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        sep = ttk.Separator(self, orient=tk.VERTICAL)
        sep.grid(row=0, column=1, padx=10, sticky="ns")

        self.local_install = LocalInstall(self, modlunky_config, task_manager)
        self.local_install.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

    def on_load(self):
        self.render()

    def render(self):
        self.fyi_install.render()
        self.local_install.render()
