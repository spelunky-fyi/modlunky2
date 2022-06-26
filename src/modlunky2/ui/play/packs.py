import json
import logging
import threading
from pathlib import Path
from shutil import copyfile
from tkinter import ttk
from typing import Dict, List

from PIL import Image, ImageTk

from modlunky2.api import SpelunkyFYIClient
from modlunky2.config import Config
from modlunky2.constants import BASE_DIR
from modlunky2.ui.widgets import (
    ScrollableLabelFrame,
)

from .pack import Pack

logger = logging.getLogger(__name__)

ICON_PATH = BASE_DIR / "static/images"


cache_lock = threading.Lock()


def _cache_fyi_pack_details(
    _call,
    install_dir: Path,
    spelunky_fyi_root: str,
    api_token: str,
    packs: List[str],
):
    api_client = SpelunkyFYIClient(spelunky_fyi_root, api_token)
    mods_dir = install_dir / "Mods"
    metadata_dir = mods_dir / ".ml/pack-metadata"

    for pack in packs:
        pack_metadata_dir = metadata_dir / f"fyi.{pack}"
        if not pack_metadata_dir.exists():
            pack_metadata_dir.mkdir(parents=True, exist_ok=True)

        skip_file = pack_metadata_dir / ".skip"
        if skip_file.exists():
            continue

        logger.debug("Getting latest details for %s", pack)
        details, code = api_client.get_mod(pack)
        # Invalid code, don't bother checking for more
        if code == 401:
            break

        if code == 404:
            skip_file.touch()
            continue

        if details is None:
            continue

        mod_file = api_client.get_mod_file_from_details(details)
        if mod_file is None:
            continue

        latest_details = {
            "id": mod_file["id"],
        }
        pack_details_latest = pack_metadata_dir / "latest.json"
        if pack_details_latest.exists():
            with pack_details_latest.open("r", encoding="utf-8") as handle:
                prev_lastest_details = json.load(handle)
                if latest_details == prev_lastest_details:
                    continue

        temp_path = pack_metadata_dir / "latest.json.tmp"
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(latest_details, handle)

        logger.debug("Copying %s to %s", temp_path, pack_details_latest)
        copyfile(temp_path, pack_details_latest)
        logger.debug("Removing temp file %s", temp_path)
        temp_path.unlink()


def cache_fyi_pack_details(
    call,
    install_dir: Path,
    spelunky_fyi_root: str,
    api_token: str,
    packs: List[str],
):
    logger.debug("Caching latest pack details for: %s", ", ".join(packs))
    acquired = cache_lock.acquire(blocking=False)
    if not acquired:
        logger.warning(
            "Attempted to cache pack details while another task is running..."
        )
        return

    try:
        _cache_fyi_pack_details(call, install_dir, spelunky_fyi_root, api_token, packs)
        call("play:reload")
    finally:
        cache_lock.release()


class PacksFrame(ScrollableLabelFrame):

    CACHE_FYI_INTERVAL = 1000 * 10 * 60

    def __init__(self, play_tab, parent, modlunky_config: Config, task_manager):
        logger.debug("Initializing Playlunky PacksFrame")

        super().__init__(parent, text="Select Mods to Play")
        self._loaded = False

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.play_tab = play_tab
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager
        self.task_manager.register_task(
            "play:cache_fyi_pack_details",
            cache_fyi_pack_details,
            True,
        )

        self.packs = []
        self.separators = []
        self.pack_objs: Dict[str, Pack] = {}

        self.folder_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "folder.png").resize((36, 36), Image.ANTIALIAS)
        )
        self.trash_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "trash.png").resize((36, 36), Image.ANTIALIAS)
        )
        self.options_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "options.png").resize((36, 36), Image.ANTIALIAS)
        )
        self.update_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "update.png").resize((36, 36), Image.ANTIALIAS)
        )

        # Schedule cache update in the future. Will attempt immediate pull first
        # time the tab is loaded.
        self.after(self.CACHE_FYI_INTERVAL, self.schedule_cache_fyi_pack_details)

    def get_fyi_pack_names(self):
        packs = set()
        for pack in self.pack_objs.values():
            if pack.is_fyi_pack():
                packs.add(pack.slug)
        return sorted(packs)

    def cache_fyi_pack_details(self):
        spelunky_fyi_root = self.modlunky_config.spelunky_fyi_root
        api_token = self.modlunky_config.spelunky_fyi_api_token

        if not api_token:
            return

        fyi_packs = self.get_fyi_pack_names()
        if not fyi_packs:
            return

        self.task_manager.call(
            "play:cache_fyi_pack_details",
            install_dir=self.modlunky_config.install_dir,
            spelunky_fyi_root=spelunky_fyi_root,
            api_token=api_token,
            packs=fyi_packs,
        )

    def schedule_cache_fyi_pack_details(self):
        try:
            self.cache_fyi_pack_details()
        finally:
            logger.debug(
                "Scheduling next run for caching fyi pack details in %s seconds",
                self.CACHE_FYI_INTERVAL / 1000,
            )
            self.after(self.CACHE_FYI_INTERVAL, self.schedule_cache_fyi_pack_details)

    @staticmethod
    def diff_packs(before, after):
        before, after = set(before), set(after)
        return list(after - before), list(before - after)

    def get_packs(self):
        packs = []
        if not self.modlunky_config.install_dir:
            return packs

        packs_dir = self.modlunky_config.install_dir / "Mods/Packs"
        if not packs_dir.exists():
            return packs

        for path in packs_dir.iterdir():
            if path.name.startswith("."):
                continue

            if not path.is_dir():
                continue

            packs.append(
                str(path.relative_to(self.modlunky_config.install_dir / "Mods/Packs"))
            )
        return packs

    def render_packs(self):
        query = self.play_tab.filter_frame.name.get()
        if query:
            query = query.lower()

        filter_selected = self.play_tab.filter_frame.selected_var.get()

        for sep in self.separators:
            sep.destroy()
        self.separators.clear()

        row_num = 0
        for pack_name in self.packs:
            display = True
            pack = self.pack_objs[pack_name]
            pack.forget()
            pack.render_buttons()

            if query and (
                query not in pack_name.lower() and query not in pack.name.lower()
            ):
                display = False

            if filter_selected == "Selected" and not pack.selected():
                display = False
            elif filter_selected == "Unselected" and pack.selected():
                display = False

            if display:
                if row_num > 0:
                    sep = ttk.Separator(self)
                    sep.grid(row=row_num, column=0, columnspan=3, pady=1, sticky="ew")
                    self.separators.append(sep)
                    row_num += 1
                pack.grid(row_num)
                row_num += 1

    def on_load(self):
        packs = self.get_packs()
        packs_added, packs_removed = self.diff_packs(self.packs, packs)

        for pack_name in packs_added:
            pack = Pack(self.play_tab, self, self.modlunky_config, pack_name)
            self.pack_objs[pack_name] = pack

        for pack_name in packs_removed:
            pack = self.pack_objs[pack_name]
            pack.destroy()
            del self.pack_objs[pack_name]

        for pack in self.pack_objs.values():
            pack.on_load()

        self.packs = [
            pack.folder
            for pack in sorted(self.pack_objs.values(), key=lambda p: p.name)
        ]

        self.render_packs()

        if not self._loaded:
            self.cache_fyi_pack_details()
            self._loaded = True
