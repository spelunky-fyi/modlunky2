import logging
import os
import queue
import random
import shutil
import subprocess
import threading
import tkinter as tk
import tkinter.messagebox as tkMessageBox
import webbrowser
from pathlib import Path
from tkinter import PhotoImage, ttk
from tkinter.scrolledtext import ScrolledText

import requests
from packaging import version
from PIL import Image, ImageTk

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.constants import (
    EXTRACTED_DIR,
    FILEPATH_DIRS,
    OVERRIDES_DIR,
    PACKS_DIR,
)
from modlunky2.assets.exc import MissingAsset
from modlunky2.assets.patcher import Patcher
from modlunky2.constants import BASE_DIR, ROOT_DIR
from modlunky2.ui.extract import ExtractTab
from modlunky2.ui.levels import LevelsTab
from modlunky2.ui.pack import PackTab
from modlunky2.ui.widgets import ConsoleWindow

logger = logging.getLogger("modlunky2")

cwd = os.getcwd()


def get_latest_version():
    try:
        return version.parse(
            requests.get(
                "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest"
            ).json()["tag_name"]
        )
    except Exception:  # pylint: disable=broad-except
        return None


def get_current_version():
    with (ROOT_DIR / "VERSION").open() as version_file:
        return version.parse(version_file.read().strip())


class ModlunkyUI:
    def __init__(self, install_dir, beta=False):
        self.install_dir = install_dir
        self.beta = beta
        self.current_version = get_current_version()
        self.latest_version = get_latest_version()
        if self.latest_version is None or self.current_version is None:
            self.needs_update = False
        else:
            self.needs_update = self.current_version < self.latest_version

        self._shutdown_handlers = []
        self._shutting_down = False

        self.root = tk.Tk(className="Modlunky2")
        self.root.title("Modlunky 2")
        self.root.geometry("950x650")
        # self.root.resizable(False, False)
        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.root.iconphoto(False, self.icon_png)

        if self.needs_update:
            update_button = ttk.Button(
                self.root, text="Update Modlunky2!", command=self.update
            )
            update_button.pack()

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.tabs = {}
        self.tab_control = ttk.Notebook(self.root)

        self.register_tab(
            "Pack Assets",
            PackTab(
                tab_control=self.tab_control,
                install_dir=install_dir,
            ),
        )
        self.register_tab(
            "Extract Assets",
            ExtractTab(
                tab_control=self.tab_control,
                install_dir=install_dir,
            ),
        )
        if beta:
            self.register_tab(
                "Levels",
                LevelsTab(
                    tab_control=self.tab_control,
                    install_dir=install_dir,
                ),
            )

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.tab_control.pack(expand=1, fill="both")

        self.console = ConsoleWindow()

    def update(self):
        webbrowser.open_new_tab(
            f"https://github.com/spelunky-fyi/modlunky2/releases/tag/{self.latest_version}"
        )

    def self_update(self):
        updater = Path(cwd + "/updater.exe")
        subprocess.call([updater])  # if file exists
        self.root.quit()
        self.root.destroy()

    def on_tab_change(self, event):
        tab = event.widget.tab("current")["text"]
        self.tabs[tab].on_load()

    def register_tab(self, name, obj):
        self.tabs[name] = obj
        self.tab_control.add(obj, text=name)

    def quit(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        logger.info("Shutting Down.")
        for handler in self._shutdown_handlers:
            handler()

        self.root.quit()
        self.root.destroy()

    def register_shutdown_handler(self, func):
        self._shutdown_handlers.append(func)

    def mainloop(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()
