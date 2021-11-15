import logging
import subprocess
import tkinter as tk
import zipfile
from io import BytesIO
from tkinter import ttk

import requests

from modlunky2.config import Config
from modlunky2.ui.widgets import Tab
from modlunky2.utils import tb_info

logger = logging.getLogger("modlunky2")

OVERLUNKY_RELEASE_URL = "https://github.com/spelunky-fyi/overlunky/releases/download/whip/Overlunky_WHIP.zip"
OVERLUNKY_EXE = "Overlunky/Overlunky.exe"


def download_overlunky_release(call, install_dir, launch):
    logger.debug("Downloading %s", OVERLUNKY_RELEASE_URL)

    try:
        download_file = BytesIO()
        response = requests.get(OVERLUNKY_RELEASE_URL, stream=True)
        amount_downloaded = 0
        block_size = 102400

        for data in response.iter_content(block_size):
            amount_downloaded += len(data)
            call("overlunky:download_progress", amount_downloaded=amount_downloaded)
            download_file.write(data)

        logger.info("Extracting to %s", install_dir)
        overlunky_zip = zipfile.ZipFile(download_file)
        overlunky_zip.extractall(install_dir)

    except Exception:  # pylint: disable=broad-except
        logger.critical("Failed to download %s: %s", OVERLUNKY_RELEASE_URL, tb_info())
        call("overlunky:download_failed")
        return

    call("overlunky:download_finished", launch=launch)


class DownloadFrame(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, task_manager):
        super().__init__(parent)

        self.parent = parent
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)

        self.task_manager.register_task(
            "overlunky:start_download",
            download_overlunky_release,
            True,
        )
        self.task_manager.register_handler(
            "overlunky:download_progress", self.on_download_progress
        )
        self.task_manager.register_handler(
            "overlunky:download_finished", self.on_download_finished
        )
        self.task_manager.register_handler(
            "overlunky:download_failed", self.on_download_failed
        )

        self.button = ttk.Button(self, text="Download Latest", command=self.download)
        self.button.grid(row=0, column=0, sticky="nswe")

    def download(self, launch=False):
        self.button["state"] = tk.DISABLED
        self.parent.master.disable_button()
        self.task_manager.call(
            "overlunky:start_download",
            install_dir=self.modlunky_config.install_dir,
            launch=launch,
        )

    def on_download_progress(self, amount_downloaded):
        logger.info("Downloaded %s bytes", amount_downloaded)

    def on_download_failed(self):
        self.parent.master.enable_button()
        self.button["state"] = tk.NORMAL

    def on_download_finished(self, launch=False):
        logger.info("Download Finished")
        if launch:
            self.parent.master.launch()
        else:
            self.parent.master.enable_button()
            self.button["state"] = tk.NORMAL


def launch_overlunky(_call, exe_path):
    logger.info("Executing Overlunky Launcher with %s", exe_path)
    working_dir = exe_path.parent
    cmd = [f"{exe_path}"]
    proc = subprocess.Popen(cmd, cwd=working_dir)
    proc.communicate()


class OverlunkyTab(Tab):
    def __init__(self, tab_control, modlunky_config, task_manager, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager
        self.task_manager.register_task(
            "overlunky:launch_overlunky",
            launch_overlunky,
            True,
            on_complete="overlunky:overlunky_closed",
        )
        self.task_manager.register_handler(
            "overlunky:overlunky_closed", self.overlunky_closed
        )
        self.overlunky_running = False

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.overlunky_frame = ttk.LabelFrame(self, text="Overlunky")
        self.overlunky_frame.grid(sticky="nsew")

        self.overlunky_frame.rowconfigure(0, weight=0)
        self.overlunky_frame.rowconfigure(1, weight=1)
        self.overlunky_frame.rowconfigure(2, minsize=60)
        self.overlunky_frame.columnconfigure(0, weight=1)

        self.download_frame = DownloadFrame(
            self.overlunky_frame, self.modlunky_config, self.task_manager
        )
        self.download_frame.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        self.button_launch = ttk.Button(
            self.overlunky_frame, text="Launch!", command=self.launch
        )
        self.button_launch.grid(row=2, column=0, pady=5, padx=5, sticky="nswe")
        self.on_load()

    def enable_button(self):
        self.button_launch["state"] = tk.NORMAL

    def disable_button(self):
        self.button_launch["state"] = tk.DISABLED

    def is_installed(self):
        return (self.modlunky_config.install_dir / OVERLUNKY_EXE).exists()

    def should_install(self):

        msg = (
            f"You don't have Overlunky installed at {self.modlunky_config.install_dir / OVERLUNKY_EXE}.\n\n"
            "Would you like to install and run the latest?"
        )

        answer = tk.messagebox.askokcancel(
            title="Install?",
            message=msg,
            icon=tk.messagebox.INFO,
        )

        return answer

    def launch(self):
        exe_path = self.modlunky_config.install_dir / OVERLUNKY_EXE

        self.disable_button()

        if not exe_path.exists():
            should_install = self.should_install()
            if should_install:
                self.download_frame.download(launch=True)
            else:
                logger.critical("Can't run without an installed version of Overlunky")
                self.enable_button()
            return

        self.task_manager.call(
            "overlunky:launch_overlunky",
            exe_path=exe_path,
        )

    def overlunky_closed(self):
        self.enable_button()
        self.on_load()
