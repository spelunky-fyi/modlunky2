# pylint: disable=too-many-lines

import json
import logging
import shutil
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
import zipfile
from io import BytesIO
from pathlib import Path
from shutil import copyfile
from tkinter import PhotoImage
from tkinter import font as tk_font
from tkinter import ttk

import requests
from PIL import Image, ImageTk

from modlunky2.config import CACHE_DIR, DATA_DIR
from modlunky2.constants import BASE_DIR
from modlunky2.ui.play.config import PlaylunkyConfig
from modlunky2.ui.widgets import ScrollableFrame, Tab, ToolTip

logger = logging.getLogger("modlunky2")

MODS = Path("Mods")
PLAYLUNKY_RELEASES_URL = "https://api.github.com/repos/spelunky-fyi/Playlunky/releases"
PLAYLUNKY_RELEASES_PATH = CACHE_DIR / "playlunky-releases.json"
PLAYLUNKY_DATA_DIR = DATA_DIR / "playlunky"

SPEL2_DLL = "spel2.dll"
PLAYLUNKY_DLL = "playlunky64.dll"
PLAYLUNKY_EXE = "playlunky_launcher.exe"
PLAYLUNKY_FILES = [SPEL2_DLL, PLAYLUNKY_DLL, PLAYLUNKY_EXE]


class Entry(tk.Entry):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.bind("<Control-a>", self._select_all)
        self.bind("<Key>", self._on_key)

        self._on_key_func = None
        self._after_id = None
        self._debounce_ms = 200

    def _select_all(self, _event=None):
        self.select_range(0, "end")
        return "break"

    def _on_key(self, event=None):
        if self._on_key_func is None:
            return

        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self._debounce_ms, self._on_key_func, event)

    def bind_on_key(self, func, debounce_ms=None):
        self._on_key_func = func
        if debounce_ms is not None:
            self._debounce_ms = debounce_ms


cache_releases_lock = threading.Lock()


def cache_playlunky_releases(call):
    logger.debug("Caching Playlunky releases")
    acquired = cache_releases_lock.acquire(blocking=False)
    if not acquired:
        logger.warning(
            "Attempted to cache playlunky releases while another task is running..."
        )
        return

    temp_path = PLAYLUNKY_RELEASES_PATH.with_suffix(
        f"{PLAYLUNKY_RELEASES_PATH.suffix}.tmp"
    )
    try:
        logger.debug("Downloading releases to %s", temp_path)
        response = requests.get(PLAYLUNKY_RELEASES_URL, allow_redirects=True)
        if not response.ok:
            logger.warning(
                "Failed to cache playlunky releases... Will try again later."
            )
            return

        with temp_path.open("wb") as handle:
            handle.write(response.content)

        logger.debug("Copying %s to %s", temp_path, PLAYLUNKY_RELEASES_PATH)
        copyfile(temp_path, PLAYLUNKY_RELEASES_PATH)
        logger.debug("Removing temp file %s", temp_path)
        temp_path.unlink()
    finally:
        cache_releases_lock.release()

    # TODO: Only run if something has actually changed
    call("play:cache_releases_updated")


def download_playlunky_release(call, tag, download_url, launch):

    dest_path = PLAYLUNKY_DATA_DIR / tag
    if not dest_path.exists():
        dest_path.mkdir(parents=True)

    download_file = BytesIO()
    response = requests.get(download_url, stream=True)
    amount_downloaded = 0
    block_size = 102400

    for data in response.iter_content(block_size):
        amount_downloaded += len(data)
        call("play:download_progress", amount_downloaded=amount_downloaded)
        download_file.write(data)

    playlunky_zip = zipfile.ZipFile(download_file)
    for member in playlunky_zip.infolist():
        if member.filename in PLAYLUNKY_FILES:
            playlunky_zip.extract(member, dest_path)

    call("play:download_finished", launch=launch)


class DownloadFrame(tk.Frame):
    def __init__(self, parent, task_manager):
        super().__init__(parent)

        self.parent = parent
        self.task_manager = task_manager
        self.columnconfigure(0, weight=1)

        self.task_manager.register_task(
            "play:start_download",
            download_playlunky_release,
            True,
        )
        self.task_manager.register_handler(
            "play:download_progress", self.on_download_progress
        )
        self.task_manager.register_handler(
            "play:download_finished", self.on_download_finished
        )

        self.separator = ttk.Separator(self)
        self.separator.grid(row=0, column=0, pady=(10, 5), padx=5, sticky="we")
        self.label = ttk.Label(self, text="Download this version?")
        self.label.grid(row=1, column=0, padx=5, sticky="we")
        self.button = ttk.Button(self, text="Download", command=self.download)
        self.button.grid(row=2, column=0, pady=5, padx=5, sticky="we")
        self.progress_bar = ttk.Progressbar(self)
        self.progress_bar.grid(row=3, column=0, pady=5, padx=5, sticky="we")

    def download(self, launch=False):
        tag = self.parent.selected_var.get()
        release = self.parent.available_releases.get(tag)
        if release is None:
            logger.error("Failed to find available release for %s", tag)
            return

        if len(release["assets"]) != 1:
            logger.error("Expected to find only a single asset for %s", tag)
            return

        asset = release["assets"][0]

        self.progress_bar["maximum"] = asset["size"]
        self.button["state"] = tk.DISABLED
        self.parent.selected_dropdown["state"] = tk.DISABLED
        self.parent.parent.disable_button()
        self.task_manager.call(
            "play:start_download",
            tag=tag,
            download_url=asset["browser_download_url"],
            launch=launch,
        )

    def on_download_progress(self, amount_downloaded):
        self.progress_bar["value"] = amount_downloaded

    def on_download_finished(self, launch=False):
        self.progress_bar["value"] = 0
        if launch:
            self.parent.parent.play()
        else:
            self.parent.parent.enable_button()
            self.button["state"] = tk.NORMAL
            self.parent.render()


def uninstall_playlunky_release(call, tag):
    dest_dir = PLAYLUNKY_DATA_DIR / tag
    logger.info("Removing Playlunky version %s", tag)
    for file_ in PLAYLUNKY_FILES:
        (dest_dir / file_).unlink(missing_ok=True)
    dest_dir.rmdir()
    call("play:uninstall_finished")


class UninstallFrame(tk.Frame):
    def __init__(self, parent, task_manager):
        super().__init__(parent)

        self.parent = parent
        self.task_manager = task_manager
        self.columnconfigure(0, weight=1)

        self.task_manager.register_task(
            "play:start_uninstall",
            uninstall_playlunky_release,
            True,
        )
        self.task_manager.register_handler(
            "play:uninstall_finished", self.on_uninstall_finished
        )

        self.separator = ttk.Separator(self)
        self.separator.grid(row=0, column=0, pady=(10, 5), padx=5, sticky="we")
        self.label = ttk.Label(self, text="Uninstall this version?")
        self.label.grid(row=1, column=0, padx=5, sticky="we")
        self.button = ttk.Button(self, text="Uninstall", command=self.uninstall)
        self.button.grid(row=2, column=0, pady=5, padx=5, sticky="we")

    def uninstall(self):
        tag = self.parent.selected_var.get()

        self.button["state"] = tk.DISABLED
        self.parent.selected_dropdown["state"] = tk.DISABLED
        self.parent.parent.disable_button()

        self.task_manager.call(
            "play:start_uninstall",
            tag=tag,
        )

    def on_uninstall_finished(self):
        self.button["state"] = tk.NORMAL
        self.parent.render()
        self.parent.parent.enable_button()


def is_installed(tag):
    return (PLAYLUNKY_DATA_DIR / tag).exists()


class VersionFrame(tk.LabelFrame):
    CACHE_RELEASES_INTERVAL = 1000 * 30 * 60

    def __init__(self, parent, config, task_manager):
        super().__init__(parent, text="Version")
        self.parent = parent
        self.available_releases = {}

        self.columnconfigure(0, weight=1)

        self.config = config
        self.task_manager = task_manager
        self.task_manager.register_task(
            "play:cache_releases",
            cache_playlunky_releases,
            True,
        )
        self.task_manager.register_handler(
            "play:cache_releases_updated", self.on_cache_releases_updated
        )

        self.default_font = tk_font.nametofont("TkDefaultFont")
        self.bold_font = tk_font.Font(font="TkDefaultFont")
        self.bold_font.configure(weight="bold")
        self.italic_font = tk_font.Font(font="TkDefaultFont")
        self.italic_font.configure(slant="italic")

        self.selected_label = tk.Label(self, text="Playlunky Version")
        self.selected_label.grid(row=2, column=0, pady=(5, 0), padx=10, sticky="w")
        self.selected_var = tk.StringVar()
        self.selected_dropdown = tk.Label(text="Loading...")
        self.selected_dropdown.grid(row=3, column=0, pady=0, padx=10, sticky="ew")

        self.download_frame = DownloadFrame(self, self.task_manager)
        self.uninstall_frame = UninstallFrame(self, self.task_manager)

    def show_download_frame(self):
        self.uninstall_frame.grid_forget()
        self.download_frame.grid(row=4, column=0, padx=10, sticky="ew")
        if not self.selected_var.get():
            self.download_frame.button["state"] = tk.DISABLED
        else:
            self.download_frame.button["state"] = tk.NORMAL

    def show_uninstall_frame(self):
        self.download_frame.grid_forget()
        self.uninstall_frame.grid(row=4, column=0, padx=10, sticky="ew")

    def get_available_releases(self):
        available_releases = {}

        if not PLAYLUNKY_RELEASES_PATH.exists():
            return available_releases

        with PLAYLUNKY_RELEASES_PATH.open("r") as releases_file:
            releases = json.load(releases_file)
            for release in releases:
                tag = release.get("tag_name")
                if tag is None:
                    continue
                available_releases[tag] = release
        return available_releases

    def cache_releases(self):
        next_run = self.CACHE_RELEASES_INTERVAL
        if PLAYLUNKY_RELEASES_PATH.exists():
            mtime = int(PLAYLUNKY_RELEASES_PATH.stat().st_mtime) * 1000
            now = int(time.time()) * 1000
            delta = now - mtime
            if delta < self.CACHE_RELEASES_INTERVAL - 1000:
                next_run = self.CACHE_RELEASES_INTERVAL - delta
                logger.debug(
                    "Playlunky releases were retrieved too recently. Retrying in %s seconds",
                    next_run / 1000,
                )
                self.after(next_run, self.cache_releases)
                return

        self.task_manager.call("play:cache_releases")
        logger.debug(
            "Scheduling next run for caching releases in %s seconds",
            self.CACHE_RELEASES_INTERVAL / 1000,
        )
        self.after(self.CACHE_RELEASES_INTERVAL, self.cache_releases)

    def release_selected(self, value):
        if value != self.config.config_file.playlunky_version:
            self.config.config_file.playlunky_version = value
            self.config.config_file.save()
            self.render()

    def render(self):
        self.available_releases = self.get_available_releases()
        installed_releases = set()
        if PLAYLUNKY_DATA_DIR.exists():
            for dir_ in PLAYLUNKY_DATA_DIR.iterdir():
                installed_releases.add(dir_.name)
        available_releases = list(self.available_releases.keys())

        self.selected_dropdown.destroy()

        if not available_releases:
            self.selected_dropdown = tk.Label(self, text="hi")
            return

        self.selected_dropdown = tk.OptionMenu(
            self,
            self.selected_var,
            available_releases[0],
            *available_releases[1:],
            command=self.release_selected,
        )
        self.selected_dropdown.configure(anchor="w")
        self.selected_dropdown.grid(row=3, column=0, pady=0, padx=10, sticky="ew")

        selected_version = self.config.config_file.playlunky_version
        if selected_version:
            self.selected_var.set(selected_version)
        else:
            selected_version = available_releases[0]
            self.config.config_file.playlunky_version = selected_version
            self.config.config_file.save()
            self.selected_var.set(selected_version)

        for release in self.available_releases:
            if release in installed_releases:
                self.selected_dropdown["menu"].entryconfigure(
                    release, font=self.bold_font
                )

        if selected_version in installed_releases:
            self.show_uninstall_frame()
        else:
            self.show_download_frame()

        self.parent.enable_button()

    def on_cache_releases_updated(self):
        self.render()


class OptionsFrame(tk.LabelFrame):
    def __init__(self, parent, config):
        super().__init__(parent, text="Options")
        self.parent = parent
        self.config = config
        self.columnconfigure(0, weight=1)

        self.random_char_var = tk.BooleanVar()
        self.random_char_checkbox = tk.Checkbutton(
            self,
            text="Random Character Select",
            variable=self.random_char_var,
            compound="left",
        )
        self.random_char_checkbox.grid(row=0, column=0, sticky="w")

        self.loose_audio_var = tk.BooleanVar()
        self.loose_audio_checkbox = tk.Checkbutton(
            self,
            text="Enable Loose Audio Loading",
            variable=self.loose_audio_var,
            compound="left",
        )
        self.loose_audio_checkbox.grid(row=1, column=0, sticky="w")

        self.cache_decoded_audio_var = tk.BooleanVar()
        self.cache_decoded_audio_checkbox = tk.Checkbutton(
            self,
            text="Cache Decoded Audio Files",
            variable=self.cache_decoded_audio_var,
            compound="left",
        )
        self.cache_decoded_audio_checkbox.grid(row=2, column=0, sticky="w")

        self.enable_developer_mode_var = tk.BooleanVar()
        self.enable_developer_mode_checkbox = tk.Checkbutton(
            self,
            text="Enable Developer Mode",
            variable=self.enable_developer_mode_var,
            compound="left",
        )
        self.enable_developer_mode_checkbox.grid(row=3, column=0, sticky="w")

        self.enable_console_var = tk.BooleanVar()
        self.enable_console_var.set(self.config.config_file.playlunky_console)
        self.enable_console_checkbox = tk.Checkbutton(
            self,
            text="Enable Console",
            variable=self.enable_console_var,
            compound="left",
            command=self.handle_console_checkbutton,
        )
        self.enable_console_checkbox.grid(row=4, column=0, sticky="w")

    def handle_console_checkbutton(self):
        self.config.config_file.playlunky_console = self.enable_console_var.get()
        self.config.config_file.save()


class FiltersFrame(tk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Filters")
        self.parent = parent

        self.name_label = tk.Label(self, text="Name:")
        self.name_label.grid(row=0, column=0, pady=(5, 5), padx=(5, 0), sticky="w")
        self.name = Entry(self, width="30")
        self.name_last_seen = ""
        self.name.bind_on_key(self.on_name_key)
        self.name.grid(row=0, column=1, pady=(5, 5), padx=(5, 0), sticky="w")

        self.selected_label = tk.Label(self, text="Show:")
        self.selected_label.grid(row=0, column=2, pady=(5, 5), padx=(5, 0), sticky="w")
        self.selected_var = tk.StringVar(value="Both")
        self.selected_dropdown = tk.OptionMenu(
            self,
            self.selected_var,
            "Both",
            "Selected",
            "Unselected",
            command=self.selected_command,
        )
        self.selected_dropdown.configure(anchor="w")
        self.selected_dropdown.grid(
            row=0, column=3, pady=(5, 5), padx=(5, 0), sticky="w"
        )

    def selected_command(self, _event=None):
        self.parent.master.render_packs()

    def on_name_key(self, _event=None):
        name = self.name.get().strip()
        if name != self.name_last_seen:
            self.name_last_seen = name
            self.parent.master.render_packs()


class ControlsFrame(tk.LabelFrame):
    def __init__(self, parent, config, *args, **kwargs):
        super().__init__(parent, text="Stuff & Things", *args, **kwargs)
        self.parent = parent
        self.config = config

        self.columnconfigure(0, weight=1)

        # self.install_button = ttk.Button(
        #    self, text="Install Mod", command=self.install_mod
        # )
        # self.install_button.grid(row=0, column=0, pady=3, padx=10, sticky="nswe")
        # ToolTip(self.install_button, "Browse for a mod file to install.")

        self.refresh_button = ttk.Button(
            self, text="Refresh Mods", command=self.refresh_mods
        )
        self.refresh_button.grid(row=1, column=0, pady=3, padx=10, sticky="nswe")
        ToolTip(
            self.refresh_button,
            (
                "If you've made any changes in the Packs directory\n"
                "that you want updated in the mod list."
            ),
        )

        self.open_packs_button = ttk.Button(
            self, text="Open Packs Directory", command=self.open_packs
        )
        self.open_packs_button.grid(row=2, column=0, pady=3, padx=10, sticky="nswe")
        ToolTip(self.open_packs_button, ("Open the directory where Packs are saved"))

        self.guide_button = ttk.Button(self, text="User Guide", command=self.guide)
        self.guide_button.grid(row=3, column=0, pady=3, padx=10, sticky="nswe")
        ToolTip(self.guide_button, ("Open the User Guide"))

        self.update_releases_button = ttk.Button(
            self, text="Update Releases", command=self.update_releases
        )
        self.update_releases_button.grid(
            row=4, column=0, pady=3, padx=10, sticky="nswe"
        )
        ToolTip(
            self.update_releases_button,
            (
                "If you want to check for a new version of Playlunky\n"
                "you can force an update with this button."
            ),
        )

        self.clear_cache_button = ttk.Button(
            self, text="Clear Cache", command=self.clear_cache
        )
        self.clear_cache_button.grid(row=5, column=0, pady=3, padx=10, sticky="nswe")
        ToolTip(
            self.clear_cache_button,
            (
                "Remove Playlunky cache. This could be helpful\n"
                "if things aren't working as expected."
            ),
        )

    def install_mod(self):
        tk.messagebox.showinfo(
            "Coming Soon",
            "This feature hasn't been implemented yet, but it will be soon!",
        )

    def refresh_mods(self):
        self.parent.on_load()

    def open_packs(self):
        packs_dir = self.config.install_dir / "Mods/Packs"
        if not packs_dir.exists():
            logger.info("Couldn't find Packs directory. Looked in %s", packs_dir)
            return

        webbrowser.open(f"file://{packs_dir}")

    def guide(self):
        webbrowser.open_new_tab("https://github.com/spelunky-fyi/Playlunky/wiki")

    def update_releases(self):
        self.parent.version_frame.task_manager.call("play:cache_releases")

    def clear_cache(self):
        cache_dir = self.config.install_dir / "Mods/Packs/.db"
        if not cache_dir.exists():
            logger.info("No cache directory found to remove. Looked in %s", cache_dir)
            return

        answer = tk.messagebox.askokcancel(
            title="Confirmation",
            message=(
                "Are you sure you want to remove Playlunky cache?\n"
                "\n"
                f"This will remove {cache_dir} and all of its contents."
            ),
            icon=tk.messagebox.WARNING,
        )

        if not answer:
            return

        shutil.rmtree(cache_dir)


class LoadOrderFrame(tk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="Load Order", *args, **kwargs)
        self.parent = parent
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE)
        self.listbox.grid(
            row=0, column=0, columnspan=2, pady=5, padx=(5, 0), sticky="nsew"
        )

        self.scrollbar = tk.Scrollbar(self)
        self.scrollbar.grid(row=0, column=1, columnspan=2, pady=5, sticky="nse")

        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.render_buttons)

        self.up_button = ttk.Button(
            self, text="Up", state=tk.DISABLED, command=self.move_up
        )
        self.up_button.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        self.down_button = ttk.Button(
            self, text="Down", state=tk.DISABLED, command=self.move_down
        )
        self.down_button.grid(row=1, column=1, pady=5, padx=5, sticky="nswe")

    def current_selection(self):
        cur = self.listbox.curselection()
        if not cur:
            return None
        return cur[0]

    def render_buttons(self, _event=None):
        size = self.listbox.size()
        selection = self.current_selection()

        # Too few items or none selected
        if size < 2 or selection is None:
            up_state = tk.DISABLED
            down_state = tk.DISABLED
        # First item selected
        elif selection == 0:
            up_state = tk.DISABLED
            down_state = tk.NORMAL
        # Last item selected
        elif selection == size - 1:
            up_state = tk.NORMAL
            down_state = tk.DISABLED
        else:
            up_state = tk.NORMAL
            down_state = tk.NORMAL

        self.up_button["state"] = up_state
        self.down_button["state"] = down_state

    def move_up(self):
        selection = self.current_selection()

        if selection is None:
            return

        if selection == 0:
            return

        label = self.listbox.get(selection)
        self.listbox.delete(selection)
        self.listbox.insert(selection - 1, label)
        self.listbox.selection_set(selection - 1)

        self.render_buttons()

    def move_down(self):
        size = self.listbox.size()
        selection = self.current_selection()

        if selection is None:
            return

        if selection == size - 1:
            return

        label = self.listbox.get(selection)
        self.listbox.delete(selection)
        self.listbox.insert(selection + 1, label)
        self.listbox.selection_set(selection + 1)

        self.render_buttons()

    def insert(self, label):
        self.listbox.insert(tk.END, label)
        self.render_buttons()

    def all(self):
        return self.listbox.get(0, tk.END)

    def delete(self, label):
        try:
            idx = self.listbox.get(0, tk.END).index(label)
        except ValueError:
            return
        self.listbox.delete(idx)
        self.render_buttons()


def launch_playlunky(_call, install_dir, exe_path, use_console):
    logger.info(
        "Executing Playlunky Launcher with %s", exe_path.relative_to(PLAYLUNKY_DATA_DIR)
    )
    working_dir = exe_path.parent
    cmd = [f"{exe_path}", f"--exe_dir={install_dir}"]
    if use_console:
        cmd.append("--console")

    proc = subprocess.Popen(cmd, cwd=working_dir)
    proc.communicate()


class PlayTab(Tab):
    def __init__(self, tab_control, config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.config = config
        self.task_manager = task_manager
        self.task_manager.register_task(
            "play:launch_playlunky",
            launch_playlunky,
            True,
            on_complete="play:playlunky_closed",
        )
        self.task_manager.register_handler(
            "play:playlunky_closed", self.playlunky_closed
        )
        self.playlunky_running = False

        self.rowconfigure(0, minsize=200)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, minsize=60)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=250)
        self.columnconfigure(2, minsize=250)

        self.play_wrapper = tk.Frame(self)
        self.play_wrapper.grid(row=0, column=0, rowspan=3, sticky="nswe")
        self.play_wrapper.columnconfigure(0, weight=1)
        self.play_wrapper.rowconfigure(1, weight=1)

        self.filter_frame = FiltersFrame(self.play_wrapper)
        self.filter_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.packs_frame = ScrollableFrame(
            self.play_wrapper, text="Select Mods to Play"
        )
        self.packs_frame.rowconfigure(0, weight=1)
        self.packs_frame.columnconfigure(0, weight=1)
        self.packs_frame.scrollable_frame.columnconfigure(0, weight=1)
        self.packs_frame.grid(
            row=1, column=0, columnspan=2, pady=5, padx=5, sticky="nswe"
        )

        self.version_frame = VersionFrame(self, config, task_manager)
        self.version_frame.grid(
            row=0, column=1, rowspan=2, pady=5, padx=5, sticky="nswe"
        )

        self.install_mod_frame = ControlsFrame(self, config)
        self.install_mod_frame.grid(
            row=2, column=1, rowspan=2, pady=5, padx=5, sticky="nswe"
        )

        self.options_frame = OptionsFrame(self, config)
        self.options_frame.grid(
            row=0, column=2, rowspan=2, pady=5, padx=5, sticky="nswe"
        )

        self.load_order = LoadOrderFrame(self)
        self.load_order.grid(row=2, column=2, rowspan=2, pady=5, padx=5, sticky="nswe")

        self.button_play = ttk.Button(
            self, text="Play!", state=tk.DISABLED, command=self.play
        )
        self.button_play.grid(row=3, column=0, pady=5, padx=5, sticky="nswe")

        self.version_frame.render()
        self.version_frame.cache_releases()

        icon_path = BASE_DIR / "static/images"
        self.folder_icon = ImageTk.PhotoImage(
            Image.open(icon_path / "folder.png").resize((30, 30), Image.ANTIALIAS)
        )
        self.trash_icon = ImageTk.PhotoImage(
            Image.open(icon_path / "trash.png").resize((30, 30), Image.ANTIALIAS)
        )

        self.packs = []
        self.separators = []
        self.checkboxes = {}

        self.on_load()
        self.load_from_ini()
        self.load_from_load_order()

    def make_dirs(self):
        if not self.config.install_dir:
            return

        packs_dir = self.config.install_dir / "Mods/Packs"
        if packs_dir.exists():
            return

        packs_dir.mkdir(parents=True, exist_ok=True)

    def enable_button(self):
        self.button_play["state"] = tk.NORMAL

    def disable_button(self):
        self.button_play["state"] = tk.DISABLED

    def load_from_ini(self):
        path = self.config.install_dir / "playlunky.ini"
        if path.exists():
            with path.open() as ini_file:
                config = PlaylunkyConfig.from_ini(ini_file)
        else:
            config = PlaylunkyConfig()

        self.options_frame.random_char_var.set(config.random_character_select)
        self.options_frame.loose_audio_var.set(config.enable_loose_audio_files)
        self.options_frame.cache_decoded_audio_var.set(config.cache_decoded_audio_files)
        self.options_frame.enable_developer_mode_var.set(config.enable_developer_mode)

    def write_ini(self):
        path = self.config.install_dir / "playlunky.ini"
        config = PlaylunkyConfig(
            random_character_select=self.options_frame.random_char_var.get(),
            enable_loose_audio_files=self.options_frame.loose_audio_var.get(),
            cache_decoded_audio_files=self.options_frame.cache_decoded_audio_var.get(),
            enable_developer_mode=self.options_frame.enable_developer_mode_var.get(),
        )
        with path.open("w") as handle:
            config.write(handle)

    def load_from_load_order(self):
        load_order_path = self.load_order_path
        if not load_order_path.exists():
            return

        with load_order_path.open("r") as load_order_file:
            for line in load_order_file:
                line = line.strip()

                select = True
                if line.startswith("--"):
                    select = False
                    line = line[2:]

                var, checkbox, buttons = self.checkboxes.get(line, (None, None, None))
                if (var, checkbox, buttons) == (None, None, None):
                    continue

                if select:
                    checkbox.select()
                else:
                    checkbox.deselect()

                self.on_check(line, var)

    def write_load_order(self):
        load_order_path = self.load_order_path
        with load_order_path.open("w") as load_order_file:
            all_packs = set(self.checkboxes.keys())
            for pack in self.load_order.all():
                all_packs.remove(pack)
                load_order_file.write(f"{pack}\n")

            for pack in all_packs:
                load_order_file.write(f"--{pack}\n")

    def write_steam_appid(self):
        path = self.config.install_dir / "steam_appid.txt"
        with path.open("w") as handle:
            handle.write("418530")

    @property
    def load_order_path(self):
        return self.config.install_dir / "Mods/Packs/load_order.txt"

    def should_install(self):
        version = self.config.config_file.playlunky_version
        if version:
            msg = (
                f"You don't currently have version {version} installed.\n\n"
                "Would you like to install it?"
            )
        else:
            msg = (
                "You don't have any version of Playlunky selected.\n\n"
                "Would you like to install and run the latest?"
            )

        answer = tk.messagebox.askokcancel(
            title="Install?",
            message=msg,
            icon=tk.messagebox.INFO,
        )

        return answer

    def play(self):
        exe_path = (
            PLAYLUNKY_DATA_DIR
            / self.config.config_file.playlunky_version
            / PLAYLUNKY_EXE
        )
        self.disable_button()

        if not exe_path.exists():
            should_install = self.should_install()
            if should_install:
                self.version_frame.download_frame.download(launch=True)
            else:
                logger.critical("Can't run without an installed version of Playlunky")
                self.enable_button()
            return

        self.write_steam_appid()
        self.write_load_order()
        self.write_ini()

        self.version_frame.selected_dropdown["state"] = tk.DISABLED
        self.version_frame.uninstall_frame.button["state"] = tk.DISABLED
        self.task_manager.call(
            "play:launch_playlunky",
            install_dir=self.config.install_dir,
            exe_path=exe_path,
            use_console=self.config.config_file.playlunky_console,
        )

    def playlunky_closed(self):
        self.version_frame.selected_dropdown["state"] = tk.NORMAL
        self.version_frame.uninstall_frame.button["state"] = tk.NORMAL
        self.enable_button()
        self.version_frame.render()

    @staticmethod
    def diff_packs(before, after):
        before, after = set(before), set(after)
        return list(after - before), list(before - after)

    def get_packs(self):
        packs = []
        packs_dir = self.config.install_dir / "Mods/Packs"
        if not packs_dir.exists():
            return packs

        for path in packs_dir.iterdir():
            if path.name.startswith("."):
                continue

            if not path.is_dir() and not path.suffix.lower() == ".zip":
                continue

            if path.is_file and path.suffix.lower() == ".zip":
                path = path.with_suffix("")
                # If There's a version that's extracted with the same name
                # skip the zipped version
                if path.exists():
                    continue

            packs.append(str(path.relative_to(self.config.install_dir / "Mods/Packs")))
        return packs

    def render_packs(self):
        name = self.filter_frame.name.get()
        if name:
            name = name.lower()

        filter_selected = self.filter_frame.selected_var.get()

        for sep in self.separators:
            sep.destroy()
        self.separators.clear()

        row_num = 0
        for pack in self.packs:
            display = True
            checkbox_var, checkbox, buttons = self.checkboxes[pack]
            checkbox_val = checkbox_var.get()
            buttons.grid_forget()
            checkbox.grid_forget()

            if not (self.config.install_dir / "Mods/Packs" / str(pack)).exists():
                buttons.folder_button["state"] = tk.DISABLED
            else:
                buttons.folder_button["state"] = tk.NORMAL

            if name and name not in pack.lower():
                display = False

            if filter_selected == "Selected" and not checkbox_val:
                display = False
            elif filter_selected == "Unselected" and checkbox_val:
                display = False

            if display:
                if row_num > 0:
                    sep = ttk.Separator(self.packs_frame.scrollable_frame)
                    sep.grid(row=row_num, column=0, pady=1, sticky="ew")
                    self.separators.append(sep)
                    row_num += 1
                checkbox.grid(row=row_num, column=0, pady=0, padx=5, sticky="nsw")
                buttons.grid(row=row_num, column=1, pady=0, padx=(5, 25), sticky="e")
                row_num += 1

    def on_check(self, name, var):
        if var.get():
            self.load_order.insert(name)
        else:
            self.load_order.delete(name)
        self.render_packs()

    def on_check_wrapper(self, name, var):
        return lambda: self.on_check(name, var)

    def open_pack_dir(self, pack):
        if pack.startswith("/"):
            logger.warning("Got dangerous pack name, aborting...")
            return

        pack_dir = self.config.install_dir / "Mods/Packs" / pack
        if not pack_dir.exists():
            logger.info("No pack directory found to remove. Looked in %s", pack_dir)
            return

        webbrowser.open(f"file://{pack_dir}")

    def remove_pack(self, pack):
        if pack.startswith("/"):
            logger.warning("Got dangerous pack name, aborting...")
            return

        to_remove = []
        pack_dir = self.config.install_dir / "Mods/Packs" / pack
        if pack_dir.exists():
            to_remove.append(pack_dir)

        if pack_dir.with_suffix(".zip").exists():
            to_remove.append(pack_dir.with_suffix(".zip"))

        if not to_remove:
            logger.info("No pack directory found to remove. Looked in %s", pack_dir)

        removing = "\n".join(map(str, to_remove))
        answer = tk.messagebox.askokcancel(
            title="Confirmation",
            message=(
                "Are you sure you want to remove this pack?\n"
                "\n"
                "This will remove the following:\n"
                f"{removing}"
            ),
            icon=tk.messagebox.WARNING,
        )

        if not answer:
            return

        for path in to_remove:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        self.on_load()

    def on_load(self):
        self.make_dirs()
        packs = sorted(self.get_packs())
        packs_added, packs_removed = self.diff_packs(self.packs, packs)

        for pack in packs_added:
            var = tk.BooleanVar()

            item = tk.Checkbutton(
                self.packs_frame.scrollable_frame,
                text=f"{pack}",
                font=("Segoe UI", 12, "bold"),
                variable=var,
                onvalue=True,
                offvalue=False,
                compound="left",
                # TODO: dynamic sizing for larger windows
                wraplength="640",
                command=self.on_check_wrapper(pack, var),
            )

            buttons = tk.Frame(self.packs_frame.scrollable_frame)
            buttons.rowconfigure(0, weight=1)
            buttons.folder_button = ttk.Button(
                buttons,
                image=self.folder_icon,
                command=(lambda pack: lambda: self.open_pack_dir(str(pack)))(pack),
            )
            buttons.folder_button.grid(row=0, column=0, sticky="e")
            buttons.trash_button = ttk.Button(
                buttons,
                image=self.trash_icon,
                command=(lambda pack: lambda: self.remove_pack(str(pack)))(pack),
            )
            buttons.trash_button.grid(row=0, column=1, sticky="e")
            self.checkboxes[pack] = (var, item, buttons)

        for pack in packs_removed:
            (_, item, buttons) = self.checkboxes[pack]
            item.destroy()
            buttons.destroy()
            del self.checkboxes[pack]

        self.packs = packs
        self.render_packs()
