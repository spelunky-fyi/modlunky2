import logging
import shutil
import tkinter as tk
import webbrowser
from tkinter import ttk

from modlunky2.ui.widgets import ToolTip
from modlunky2.utils import open_directory

logger = logging.getLogger("modlunky2")


class ControlsFrame(ttk.Frame):
    def __init__(self, parent, play_tab, modlunky_config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.modlunky_config = modlunky_config
        self.play_tab = play_tab

        self.columnconfigure(0, weight=1)

        self.refresh_button = ttk.Button(
            self, text="Refresh Mods", command=self.refresh_mods
        )
        self.refresh_button.grid(row=0, column=0, pady=3, padx=10, sticky="nswe")
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
        self.open_packs_button.grid(row=1, column=0, pady=3, padx=10, sticky="nswe")
        ToolTip(self.open_packs_button, ("Open the directory where Packs are saved"))

        self.guide_button = ttk.Button(self, text="User Guide", command=self.guide)
        self.guide_button.grid(row=2, column=0, pady=3, padx=10, sticky="nswe")
        ToolTip(self.guide_button, ("Open the User Guide"))

        self.update_releases_button = ttk.Button(
            self, text="Update Releases", command=self.update_releases
        )
        self.update_releases_button.grid(
            row=3, column=0, pady=3, padx=10, sticky="nswe"
        )
        ToolTip(
            self.update_releases_button,
            (
                "If you want to check for a new version of Playlunky\n"
                "you can force an update with this button."
            ),
        )

        self.check_fyi_updates_button = ttk.Button(
            self, text="Check for Mod Updates", command=self.check_fyi_updates
        )
        self.check_fyi_updates_button.grid(
            row=4, column=0, pady=3, padx=10, sticky="nswe"
        )
        ToolTip(
            self.check_fyi_updates_button,
            ("Check to see if any mods have updates available."),
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

    def on_load(self):
        if self.modlunky_config.config_file.spelunky_fyi_api_token:
            self.check_fyi_updates_button["state"] = tk.NORMAL
        else:
            self.check_fyi_updates_button["state"] = tk.DISABLED

    def refresh_mods(self):
        self.play_tab.on_load()

    def open_packs(self):
        packs_dir = self.modlunky_config.install_dir / "Mods/Packs"
        if not packs_dir.exists():
            logger.info("Couldn't find Packs directory. Looked in %s", packs_dir)
            return

        open_directory(packs_dir)

    def guide(self):
        webbrowser.open_new_tab("https://github.com/spelunky-fyi/Playlunky/wiki")

    def update_releases(self):
        self.play_tab.version_frame.task_manager.call("play:cache_releases")

    def check_fyi_updates(self):
        self.play_tab.packs_frame.cache_fyi_pack_details()

    def clear_cache(self):
        cache_dir = self.modlunky_config.install_dir / "Mods/Packs/.db"
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
