import configparser
import logging
import subprocess
import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from modlunky2.config import Config
from modlunky2.ui.play.config import SECTIONS, PlaylunkyConfig
from modlunky2.ui.widgets import (
    ScrollableFrameLegacy,
    Tab,
)

from modlunky2.ui.play.constants import (
    PLAYLUNKY_DATA_DIR,
    PLAYLUNKY_EXE,
    PLAYLUNKY_VERSION_FILENAME,
)
from modlunky2.ui.play.controls import ControlsFrame
from modlunky2.ui.play.filters import FiltersFrame
from modlunky2.ui.play.load_order import LoadOrderFrame
from modlunky2.ui.play.options import OptionsFrame
from modlunky2.ui.play.packs import PacksFrame
from modlunky2.ui.play.releases import VersionFrame, parse_download_url

logger = logging.getLogger(__name__)


def launch_playlunky(
    _call, install_dir, exe_path, use_console, command_prefix: Optional[List[str]]
):
    logger.info(
        "Executing Playlunky Launcher with %s", exe_path.relative_to(PLAYLUNKY_DATA_DIR)
    )
    working_dir = exe_path.parent
    cmd = [f"{exe_path}", f"--exe_dir={install_dir}"]

    if command_prefix:
        cmd = command_prefix + cmd

    if use_console:
        cmd.append("--console")

    proc = subprocess.Popen(cmd, cwd=working_dir)
    proc.communicate()


class PlayTab(Tab):
    def __init__(
        self, tab_control, modlunky_config: Config, task_manager, *args, **kwargs
    ):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config
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
        self.task_manager.register_handler("play:reload", self.on_load)
        self.playlunky_running = False

        self.rowconfigure(0, minsize=200)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, minsize=60)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=250)
        self.columnconfigure(2, minsize=250)

        self.play_wrapper = ttk.Frame(self)
        self.play_wrapper.grid(row=0, column=0, rowspan=3, sticky="nswe")
        self.play_wrapper.columnconfigure(0, weight=1)
        self.play_wrapper.rowconfigure(1, weight=1)

        self.filter_frame = FiltersFrame(self.play_wrapper, play_tab=self)
        self.filter_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.packs_frame = PacksFrame(
            self, self.play_wrapper, self.modlunky_config, self.task_manager
        )
        self.packs_frame.grid(
            row=1, column=0, columnspan=2, pady=5, padx=5, sticky="nswe"
        )

        # Load Order Frame
        self.load_order = LoadOrderFrame(self)
        self.load_order.grid(row=0, column=1, rowspan=2, pady=5, padx=5, sticky="nswe")

        # Versions Frame
        self.version_frame = VersionFrame(self, modlunky_config, task_manager)
        self.version_frame.grid(
            row=2, column=1, rowspan=2, pady=5, padx=5, sticky="nswe"
        )

        # Options Frame
        self.scrollable_options_frame = ScrollableFrameLegacy(self, text="Options")
        self.scrollable_options_frame.grid(
            row=0, column=2, rowspan=2, pady=5, padx=5, sticky="nswe"
        )
        self.options_frame = OptionsFrame(
            self.scrollable_options_frame.scrollable_frame, self, modlunky_config
        )
        self.options_frame.grid(row=0, column=0, sticky="nsew")

        # Controls Frame
        self.scrollable_controls_frame = ScrollableFrameLegacy(
            self, text="Stuff & Things"
        )
        self.scrollable_controls_frame.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_controls_frame.grid(
            row=2, column=2, rowspan=2, pady=5, padx=5, sticky="nswe"
        )
        self.controls_frame = ControlsFrame(
            self.scrollable_controls_frame.scrollable_frame, self, modlunky_config
        )
        self.controls_frame.grid(row=0, column=0, padx=(0, 20), sticky="nswe")

        # Play Button
        self.button_play = ttk.Button(
            self, text="Play!", state=tk.DISABLED, command=self.play
        )
        self.button_play.grid(row=3, column=0, pady=5, padx=5, sticky="nswe")

        self.version_frame.render()
        self.version_frame.cache_releases()

        self.ini = None

        logger.debug("Initializing Playlunky on_load")
        self.on_load()
        logger.debug("Initializing Playlunky load_from_ini")
        self.load_from_ini()
        logger.debug("Initializing Playlunky load_from_load_order")
        self.load_from_load_order()
        logger.debug("Initalizing Playlunky complete!")

    def make_dirs(self):
        if not self.modlunky_config.install_dir:
            return

        packs_dir = self.modlunky_config.install_dir / "Mods/Packs"
        if packs_dir.exists():
            return

        packs_dir.mkdir(parents=True, exist_ok=True)

    def enable_button(self):
        self.button_play["state"] = tk.NORMAL

    def disable_button(self):
        self.button_play["state"] = tk.DISABLED

    def load_from_ini(self):
        self.ini = PlaylunkyConfig()
        if self.modlunky_config.install_dir:
            path = self.modlunky_config.install_dir / "playlunky.ini"
            if path.exists():
                with path.open() as ini_file:
                    try:
                        self.ini = PlaylunkyConfig.from_ini(ini_file)
                    except configparser.Error:
                        logger.warning(
                            "Failed to parse playlunky config %s", path, exc_info=True
                        )

        for options in SECTIONS.values():
            for option in options:
                option_var = self.options_frame.ini_options[option]
                option_var.set(getattr(self.ini, option))
                option_var.trace_add(
                    "write",
                    lambda *args: self.write_ini(),
                )

    def write_ini(self):
        if not self.modlunky_config.install_dir:
            return

        path = self.modlunky_config.install_dir / "playlunky.ini"

        for options in SECTIONS.values():
            for option in options:
                try:
                    setattr(
                        self.ini, option, self.options_frame.ini_options[option].get()
                    )
                except tk.TclError:
                    logger.info(
                        "Setting '%s' could not be set, maybe the field is currently empty?",
                        option,
                    )

        with path.open("w") as handle:
            self.ini.write(handle)

    def load_from_load_order(self):
        load_order_path = self.load_order_path
        if not load_order_path or not load_order_path.exists():
            return

        with load_order_path.open("r") as load_order_file:
            for line in load_order_file:
                line = line.strip()

                selected = True
                if line.startswith("--"):
                    selected = False
                    line = line[2:]

                pack = self.packs_frame.pack_objs.get(line)
                if pack is None:
                    continue

                pack.set(selected, skip_render=True)

        self.packs_frame.render_packs()

    def write_load_order(self):
        load_order_path = self.load_order_path
        with load_order_path.open("w") as load_order_file:
            all_packs = set(self.packs_frame.pack_objs.keys())
            for pack in self.load_order.all():
                all_packs.remove(pack)
                load_order_file.write(f"{pack}\n")

            for pack in all_packs:
                load_order_file.write(f"--{pack}\n")

    def write_steam_appid(self):
        if not self.modlunky_config.install_dir:
            return

        path = self.modlunky_config.install_dir / "steam_appid.txt"
        with path.open("w") as handle:
            handle.write("418530")

    @property
    def load_order_path(self):
        if not self.modlunky_config.install_dir:
            return False
        return self.modlunky_config.install_dir / "Mods/Packs/load_order.txt"

    def should_install(self):
        version = self.modlunky_config.playlunky_version
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

    def needs_update(self):
        selected_version = self.modlunky_config.playlunky_version
        if selected_version not in ["nightly", "stable"]:
            return False

        release_info = self.version_frame.available_releases[selected_version]
        release_version, _ = parse_download_url(
            release_info["assets"][0]["browser_download_url"]
        )

        downloaded_version_path = (
            PLAYLUNKY_DATA_DIR
            / self.modlunky_config.playlunky_version
            / PLAYLUNKY_VERSION_FILENAME
        )
        downloaded_version = None
        if not downloaded_version_path.exists():
            logger.info("No version info for current download. Updating to latest.")
            return True

        with downloaded_version_path.open("r") as downloaded_version_file:
            downloaded_version = downloaded_version_file.read().strip()

        if downloaded_version != release_version:
            logger.info("New version of %s available. Updating...", selected_version)
            return True

        return False

    def play(self):
        exe_path = (
            PLAYLUNKY_DATA_DIR / self.modlunky_config.playlunky_version / PLAYLUNKY_EXE
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

        if self.needs_update():
            self.version_frame.download_frame.download(launch=True)
            return

        self.write_steam_appid()
        self.write_load_order()
        self.write_ini()

        self.version_frame.selected_dropdown["state"] = tk.DISABLED
        self.version_frame.uninstall_frame.button["state"] = tk.DISABLED
        self.task_manager.call(
            "play:launch_playlunky",
            install_dir=self.modlunky_config.install_dir,
            exe_path=exe_path,
            use_console=self.modlunky_config.playlunky_console,
            command_prefix=self.modlunky_config.command_prefix,
        )

    def playlunky_closed(self):
        self.version_frame.selected_dropdown["state"] = tk.NORMAL
        self.version_frame.uninstall_frame.button["state"] = tk.NORMAL
        self.enable_button()
        self.version_frame.render()

    def on_load(self):
        self.make_dirs()
        self.packs_frame.on_load()
        self.controls_frame.on_load()
