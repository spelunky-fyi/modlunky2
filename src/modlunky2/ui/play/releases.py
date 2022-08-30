import json
import logging
import threading
import time
import tkinter as tk
import zipfile
from io import BytesIO
from pathlib import Path
from shutil import copyfile
from tkinter import font as tk_font
from tkinter import ttk
from urllib.parse import urlparse

import requests

from modlunky2.config import Config
from modlunky2.utils import tb_info

from .constants import (
    PLAYLUNKY_DATA_DIR,
    PLAYLUNKY_FILES,
    PLAYLUNKY_RELEASES_PATH,
    PLAYLUNKY_RELEASES_URL,
    PLAYLUNKY_VERSION_FILENAME,
)

logger = logging.getLogger(__name__)
cache_releases_lock = threading.Lock()


def parse_download_url(download_url):
    path = Path(urlparse(download_url).path)
    ext = path.suffix
    stem = path.stem
    version = stem.rpartition("_")[2]
    return version, ext


def download_playlunky_release(call, tag, download_url, launch):
    logger.debug("Downloading %s", download_url)

    dest_path = PLAYLUNKY_DATA_DIR / tag
    if not dest_path.exists():
        dest_path.mkdir(parents=True)

    try:
        version, ext = parse_download_url(download_url)
        if ext != ".zip":
            raise ValueError("Expected .zip but didn't find one")

        download_file = BytesIO()
        response = requests.get(download_url, stream=True, timeout=5)
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

        version_path = dest_path / PLAYLUNKY_VERSION_FILENAME
        logger.debug("Writing version to %s", version_path)
        with version_path.open("w") as version_file:
            version_file.write(version)

    except Exception:  # pylint: disable=broad-except
        logger.critical("Failed to download %s: %s", download_url, tb_info())
        call("play:download_failed")
        return

    call("play:download_finished", launch=launch)


class DownloadFrame(ttk.Frame):
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
        self.task_manager.register_handler(
            "play:download_failed", self.on_download_failed
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

    def on_download_failed(self):
        self.parent.parent.enable_button()
        self.button["state"] = tk.NORMAL
        self.parent.render()

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
    (dest_dir / PLAYLUNKY_VERSION_FILENAME).unlink(missing_ok=True)
    dest_dir.rmdir()
    call("play:uninstall_finished")


class UninstallFrame(ttk.Frame):
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
        response = requests.get(PLAYLUNKY_RELEASES_URL, allow_redirects=True, timeout=5)
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


class VersionFrame(ttk.LabelFrame):
    CACHE_RELEASES_INTERVAL = 1000 * 30 * 60

    def __init__(self, parent, modlunky_config: Config, task_manager):
        logger.debug("Initializing Playlunky VersionFrame")
        super().__init__(parent, text="Version")
        self.parent = parent
        self.available_releases = {}

        self.columnconfigure(0, weight=1)

        self.modlunky_config = modlunky_config
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

        self.selected_label = ttk.Label(self, text="Playlunky Version")
        self.selected_label.grid(row=2, column=0, pady=(5, 0), padx=10, sticky="w")
        self.selected_var = tk.StringVar()
        self.selected_dropdown = ttk.Label(text="Loading...")
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

        stable = None

        with PLAYLUNKY_RELEASES_PATH.open("r", encoding="utf-8") as releases_file:
            try:
                releases = json.load(releases_file)
            except json.JSONDecodeError:
                logger.warning("Failed to get read cached releases")
                self.task_manager.call("play:cache_releases")
                return available_releases

            for release in releases:
                tag = release.get("tag_name")
                prerelease = release.get("prerelease")
                if tag is None or prerelease is None:
                    continue
                if stable is None and not prerelease:
                    logger.debug("Marking %s as stable", tag)
                    stable = tag
                    available_releases["stable"] = release
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
        if value == self.modlunky_config.playlunky_version:
            return

        self.modlunky_config.playlunky_version = value
        self.modlunky_config.save()
        self.render()
        if self.modlunky_config.playlunky_shortcut:
            self.parent.options_frame.make_shortcut()

    def render(self):
        self.available_releases = self.get_available_releases()
        available_releases = ["stable", "nightly"] + [
            release
            for release in self.available_releases
            if release not in ["nightly", "stable"]
        ]
        available_set = set(available_releases)
        installed_releases = set()
        if PLAYLUNKY_DATA_DIR.exists():
            for dir_ in PLAYLUNKY_DATA_DIR.iterdir():
                installed_releases.add(dir_.name)

        orphans = installed_releases - available_set
        available_releases += orphans

        self.selected_dropdown.destroy()

        if not available_releases:
            self.selected_dropdown = ttk.Label(self, text="No available releases")
            return

        self.selected_dropdown = ttk.OptionMenu(
            self,
            self.selected_var,
            self.selected_var.get(),
            *available_releases,
            command=self.release_selected,
        )
        self.selected_dropdown.grid(row=3, column=0, pady=0, padx=10, sticky="ew")

        selected_version = self.modlunky_config.playlunky_version
        if selected_version:
            self.selected_var.set(selected_version)
        else:
            selected_version = available_releases[0]
            self.modlunky_config.playlunky_version = selected_version
            self.modlunky_config.save()
            self.selected_var.set(selected_version)

        for release in available_releases:
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
