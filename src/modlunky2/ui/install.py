import json
import logging
import re
import shutil
import tkinter as tk
import zipfile
from io import BytesIO
from pathlib import Path
from os.path import commonprefix
from tkinter import filedialog, ttk
from typing import Optional
from urllib.parse import urlparse

import requests

from modlunky2.config import Config
from modlunky2.ui.widgets import Entry, Tab
from modlunky2.utils import tb_info, zipinfo_fixup_filename
from modlunky2.api import SpelunkyFYIClient

logger = logging.getLogger(__name__)


class SourceChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text="Source",
            font="sans 11 bold",
        ).grid(row=0, column=0, padx=5, sticky="ew")

        file_chooser_label = ttk.Label(
            self,
            text="Drop a file anywhere or choose file to install (.zip, .lua, .png...)",
        )
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
        initial_dir = self.modlunky_config.last_install_browse
        if not initial_dir.exists():
            initial_dir = Path("/")

        filename = filedialog.askopenfilename(parent=self, initialdir=initial_dir)
        if not filename:
            self.file_chooser_var.set("")
            self.master.master.render()
            return

        self.file_chooser_var.set(filename)
        parent = Path(filename).parent

        self.modlunky_config.last_install_browse = parent
        self.modlunky_config.save()
        self.master.master.render()


class DestinationChooser(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config):
        super().__init__(parent)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text="Destination",
            font="sans 11 bold",
        ).grid(row=0, column=0, padx=5, sticky="ew")
        file_chooser_label = ttk.Label(
            self,
            text="Enter new pack name or choose existing pack",
        )
        file_chooser_label.grid(
            row=1, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.file_chooser_var = tk.StringVar()

        file_chooser_entry = ttk.Entry(
            self,
            textvariable=self.file_chooser_var,
            validate="all",
        )
        file_chooser_entry["validatecommand"] = (
            file_chooser_entry.register(self.changed),
            "%P",
        )
        file_chooser_entry.columnconfigure(0, weight=1)
        file_chooser_entry.columnconfigure(1, weight=1)
        file_chooser_entry.columnconfigure(2, weight=1)
        file_chooser_entry.grid(
            row=2, column=0, padx=5, pady=5, columnspan=3, sticky="nsew"
        )

        file_chooser_browse = ttk.Button(self, text="Browse", command=self.browse)
        file_chooser_browse.grid(row=3, column=0, pady=5, padx=5, sticky="nsew")

    def changed(self, val):
        self.master.master.check_exists(
            self.master.master.file_chooser_frame.file_chooser_var.get(), val
        )
        return True

    def browse(self):
        if not self.modlunky_config.install_dir:
            return

        initial_dir = self.modlunky_config.install_dir / "Mods/Packs"
        if not initial_dir.exists():
            logger.critical("Expected Packs dir not found.")
            return

        directory = filedialog.askdirectory(parent=self, initialdir=initial_dir)
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
        with zipfile.ZipFile(source) as zip_file:
            zip_file.extractall(dest_dir, get_zip_members(zip_file))

    elif source.suffix == ".lua":
        main_lua = dest_dir / "main.lua"
        logger.info("Copying file %s to %s", source.name, main_lua)
        shutil.copy(source.resolve(), main_lua.resolve())

    else:
        logger.info("Copying file %s to %s", source.name, dest_dir)
        shutil.copy(source.resolve(), dest_dir.resolve())

    logger.info("Finished installing %s to %s", source.name, dest_dir)
    call("play:reload")


class LocalInstall(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config: Config, task_manager, *args, **kwargs):
        super().__init__(parent, text="Local Installation", *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.task_manager = task_manager

        self.task_manager.register_task(
            "install:install_local_mod",
            install_local_mod,
            True,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=10000)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, minsize=60)

        source_frame = ttk.Frame(self)
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)
        source_frame.grid(row=1, column=0, pady=5, sticky="nswe")

        self.file_chooser_frame = SourceChooser(source_frame, modlunky_config)
        self.file_chooser_frame.grid(row=0, column=0, pady=5, sticky="new")

        dest_frame = ttk.Frame(self)
        dest_frame.rowconfigure(0, weight=1)
        dest_frame.columnconfigure(0, weight=1)
        dest_frame.grid(row=2, column=0, pady=5, sticky="nswe")

        self.file_chooser_frame2 = DestinationChooser(dest_frame, modlunky_config)
        self.file_chooser_frame2.grid(row=0, column=0, pady=5, sticky="new")

        self.button_install = ttk.Button(
            self,
            text="Select source and destination or drop a file anywhere",
            command=self.install,
        )
        self.button_install.grid(row=3, column=0, pady=5, padx=5, sticky="nswe")

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

    def check_exists(self, source, dest):
        source_path = Path(source)
        dest_path = self.modlunky_config.install_dir / "Mods/Packs" / Path(dest).stem
        if (
            not dest
            or not source
            or not source_path.exists()
            or not source_path.is_file()
        ):
            self.button_install["state"] = tk.DISABLED
            return
        self.button_install["state"] = tk.NORMAL
        if dest_path.exists():
            self.button_install["text"] = "Install selected file to existing pack"
        else:
            self.button_install["text"] = "Install selected file as new pack"

    def render(self):
        source = self.file_chooser_frame.file_chooser_var.get()
        dest = self.file_chooser_frame2.file_chooser_var.get()
        if source and not dest:
            self.file_chooser_frame2.file_chooser_var.set(Path(source).stem)
            dest = self.file_chooser_frame2.file_chooser_var.get()
        if source and dest:
            self.button_install["state"] = tk.NORMAL
            self.check_exists(source, dest)
        else:
            self.button_install["state"] = tk.DISABLED
            self.button_install[
                "text"
            ] = "Select source and destination or drop a file anywhere"

    def drop_file(self, data):
        files = self.file_chooser_frame.tk.splitlist(data)
        if files[0] and Path(files[0]).exists() and Path(files[0]).is_file():
            logger.info(
                "Click 'Install' in the right column to complete installation of %s",
                Path(files[0]).name,
            )
            self.file_chooser_frame.file_chooser_var.set(Path(files[0]))
            self.file_chooser_frame2.file_chooser_var.set(Path(files[0]).stem)
            self.render()


def write_manifest(dest_dir: Path, mod_details, mod_file, logo=None):
    manifest = {
        "name": mod_details["name"],
        "slug": mod_details["slug"],
        "description": mod_details["description"],
        "logo": str(logo),
        "mod_file": {
            "id": mod_file["id"],
            "created_at": mod_file["created_at"],
            "download_url": mod_file["download_url"],
        },
    }

    with (dest_dir / "manifest.json").open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file)


def download_contents(_call, url):
    contents = BytesIO()

    try:
        response = requests.get(url, stream=True, allow_redirects=True, timeout=5)
        response.raise_for_status()
        amount_downloaded = 0
        block_size = 102400

        for data in response.iter_content(block_size):
            amount_downloaded += len(data)
            logger.info("Downloaded %s bytes", amount_downloaded)
            contents.write(data)

    except Exception:  # pylint: disable=broad-except
        logger.critical("Failed to download %s: %s", url, tb_info())
        return None

    contents.seek(0)
    return contents


def download_file(call, url: str, dest_path: Path):
    contents = download_contents(call, url)
    if contents is None:
        logger.warning("Failed to download file from %s", url)
        return

    with dest_path.open("wb") as dest_file:
        shutil.copyfileobj(contents, dest_file)


def get_zip_members(zip_file):
    paths = set()
    num_lua_files = 0

    # Get path prefixes
    for name in zip_file.namelist():
        if name.endswith("/"):
            continue

        if name.endswith(".lua"):
            num_lua_files += 1

        path_parts = name.split("/")[:-1]
        if path_parts:
            paths.add("/".join(path_parts) + "/")
        else:
            paths.add("")

    # now find the common path prefix (if any)
    prefix = commonprefix(list(paths))

    if prefix.lower().startswith(("data/", "soundbank/")):
        prefix = ""

    prefix_len = len(prefix)

    for zipinfo in zip_file.infolist():
        zipinfo_fixup_filename(zipinfo)
        filename: str = zipinfo.filename
        if len(filename) <= prefix_len:
            continue
        zipinfo.filename = filename[prefix_len:]
        if filename.endswith(".lua") and num_lua_files == 1:
            zipinfo.filename = "main.lua"
        yield zipinfo


def download_zip(call, download_url, pack_dir):
    contents = download_contents(call, download_url)
    if contents is None:
        logger.warning("Failed to download file from %s", download_url)
        return

    modzip = zipfile.ZipFile(contents)
    modzip.extractall(pack_dir, get_zip_members(modzip))


def download_mod_file(call, mod_file, pack_dir):
    download_url = mod_file["download_url"]
    filename = Path(mod_file["filename"])

    if filename.suffix == ".lua":
        filename = Path("main.lua")

    if filename.suffix == ".zip":
        download_zip(call, download_url, pack_dir)

    else:
        download_file(call, download_url, pack_dir / filename)


def download_logo(call, logo_url, pack_dir):
    logger.info("Downloading logo")
    url_path = Path(urlparse(logo_url).path)
    logo_name = Path("mod_logo").with_suffix(url_path.suffix)
    download_file(call, logo_url, pack_dir / logo_name)
    return logo_name


def install_fyi_mod(
    call,
    install_dir: Path,
    spelunky_fyi_root: str,
    api_token: str,
    install_code: str,
    mod_file_id: Optional[str] = None,
    channel_name: Optional[str] = None,
    overwrite: bool = False,
):
    mods_dir = install_dir / "Mods"
    packs_dir = mods_dir / "Packs"
    metadata_dir = mods_dir / ".ml/pack-metadata"

    pack_dir = packs_dir / f"fyi.{install_code}"
    tmp_dir = packs_dir / f"temp_fyi.{install_code}"

    save_path = pack_dir / "save.dat"
    tmp_save_path = tmp_dir / "save.dat"
    if pack_dir.exists():
        if save_path.exists():
            # Store the save file into a temp directory while downloading the new version.
            tmp_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(save_path, tmp_save_path)
        if overwrite:
            logger.debug("Removing previous installation at %s", pack_dir)
            shutil.rmtree(pack_dir)
        else:
            call(
                "install:needs_confirmation",
                install_dir=install_dir,
                spelunky_fyi_root=spelunky_fyi_root,
                api_token=api_token,
                install_code=install_code,
                mod_file_id=mod_file_id,
                channel_name=channel_name,
            )
            return

    api_client = SpelunkyFYIClient(spelunky_fyi_root, api_token)
    logger.debug("Checking for mod: %s", install_code)

    mod_details, code = api_client.get_mod(install_code)
    if mod_details.get("mod_type") == 5:  # Library
        logger.warning("Tried to install Library mod. Doesn't make sense...")
        return

    if mod_details is None:
        if code == 404:
            logger.debug("No mod found with install code: %s", install_code)
        return

    mod_file = api_client.get_mod_file_from_details(mod_details, mod_file_id)
    if mod_file is None:
        logger.critical(
            "Mod file `%s` with mod file id %s not found.", install_code, mod_file_id
        )
        return

    pack_dir.mkdir(parents=True, exist_ok=True)
    pack_metadata_dir = metadata_dir / f"fyi.{install_code}"
    if not pack_metadata_dir.exists():
        pack_metadata_dir.mkdir(parents=True, exist_ok=True)

    download_mod_file(call, mod_file, pack_dir)

    logo_url = mod_details["logo"]
    logo_name = None
    if logo_url:
        logo_name = download_logo(call, logo_url, pack_metadata_dir)

    write_manifest(pack_metadata_dir, mod_details, mod_file, logo_name)

    if tmp_save_path.exists():
        # If there was a save file, move it into the new pack.
        shutil.copy(tmp_save_path, save_path)
        shutil.rmtree(tmp_dir)

    logger.info("Finished installing %s to %s", install_code, pack_dir)
    if channel_name is not None:
        call("fyi:install-complete", channel_name=channel_name)
    call("play:reload")


class FyiInstall(ttk.LabelFrame):
    VALID_SLUG = re.compile(r"^[-\w]+$")

    def __init__(self, parent, modlunky_config: Config, task_manager, *args, **kwargs):
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
        self.task_manager.register_handler(
            "install:needs_confirmation", self.on_needs_confirmation
        )

        frame = ttk.Frame(self)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        frame.rowconfigure(6, minsize=60)
        frame.grid(row=0, column=0, sticky="nswe")

        self.warning_text = ttk.Label(
            frame,
            text=(
                "Before this feature is enabled you must \n"
                "add an API token in the Settings tab."
            ),
            anchor=tk.CENTER,
        )

        self.install_header = ttk.Label(
            frame,
            text="Install Code",
            font="sans 11 bold",
        )
        self.install_description = ttk.Label(
            frame,
            text="Enter the 'Install Code' from a mod page on spelunky.fyi",
        )

        self.entry = Entry(frame)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda _: self.install())

        self.button_install = ttk.Button(frame, text="Install", command=self.install)

    def on_needs_confirmation(
        self,
        install_dir: Path,
        spelunky_fyi_root: str,
        api_token: str,
        install_code: str,
        mod_file_id: Optional[str] = None,
        channel_name: Optional[str] = None,
    ):
        answer = tk.messagebox.askokcancel(
            title="Pack Exists",
            message=(
                "The pack you're installing already exists.\n"
                "\n"
                "Do you want to overwrite the existing installation?\n"
            ),
            icon=tk.messagebox.WARNING,
        )

        if not answer:
            return

        self.task_manager.call(
            "install:install_fyi_mod",
            install_dir=install_dir,
            spelunky_fyi_root=spelunky_fyi_root,
            api_token=api_token,
            install_code=install_code,
            mod_file_id=mod_file_id,
            channel_name=channel_name,
            overwrite=True,
        )

    def install(self):
        spelunky_fyi_root = self.modlunky_config.spelunky_fyi_root
        api_token = self.modlunky_config.spelunky_fyi_api_token
        if not api_token:
            logger.warning(
                "This feature requires an API token. You can set one on your Settings tab."
            )
            return

        install_code = self.entry.get().strip()
        install_code = Path(urlparse(install_code).path).name

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
        api_token = self.modlunky_config.spelunky_fyi_api_token
        install_code = self.entry.get().strip()

        if api_token:
            self.install_header.grid(row=3, column=0, padx=5, sticky="ew")
            self.install_description.grid(row=4, column=0, padx=5, sticky="ew")
            self.entry.grid(row=5, column=0, pady=5, padx=5, sticky="new")
            self.button_install.grid(row=6, column=0, pady=5, padx=5, sticky="nswe")
            self.warning_text.grid_forget()
        else:
            self.install_header.grid_forget()
            self.install_description.grid_forget()
            self.entry.grid_forget()
            self.button_install.grid_forget()
            self.warning_text.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        if api_token and install_code:
            self.button_install["state"] = tk.NORMAL
        else:
            self.button_install["state"] = tk.DISABLED

    def _on_key(self, _event):
        self.render()


class InstallTab(Tab):
    def __init__(
        self, tab_control, modlunky_config: Config, task_manager, *args, **kwargs
    ):
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
