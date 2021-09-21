import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from modlunky2.ui.play.config import SECTIONS
from modlunky2.utils import is_windows

from .constants import (
    PLAYLUNKY_DATA_DIR,
    PLAYLUNKY_EXE,
)

if is_windows():
    import winshell  # type: ignore

logger = logging.getLogger("modlunky2")


class OptionsFrame(ttk.Frame):
    def __init__(self, parent, play_tab, modlunky_config):
        logger.debug("Initializing Playlunky OptionsFrame")
        super().__init__(parent)
        self.parent = parent
        self.play_tab = play_tab
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)

        row_num = 0
        self.ini_options = {}

        self.enable_console_var = tk.BooleanVar()
        self.enable_console_var.set(self.modlunky_config.config_file.playlunky_console)
        self.enable_console_checkbox = ttk.Checkbutton(
            self,
            text="Leave Terminal Running",
            variable=self.enable_console_var,
            compound="left",
            command=self.handle_console_checkbutton,
        )

        self.desktop_shortcut_var = tk.BooleanVar()
        self.desktop_shortcut_var.set(
            self.modlunky_config.config_file.playlunky_shortcut
        )
        self.desktop_shortcut_checkbox = ttk.Checkbutton(
            self,
            text="Desktop Shortcut",
            variable=self.desktop_shortcut_var,
            compound="left",
            command=self.handle_desktop_shortcut,
        )

        for section_idx, (section, options) in enumerate(SECTIONS.items()):
            section_ypad = (5, 0)
            if section_idx == 0:
                section_ypad = 0
            section_label = ttk.Label(self, text=self.format_text(section))
            section_label.grid(
                row=row_num, column=0, padx=2, pady=section_ypad, sticky="w"
            )
            sep = ttk.Separator(self)
            sep.grid(row=row_num + 1, padx=2, sticky="we")
            row_num += 2

            for option in options:
                self.ini_options[option] = tk.BooleanVar()
                checkbox = ttk.Checkbutton(
                    self,
                    text=self.format_text(option),
                    variable=self.ini_options[option],
                    compound="left",
                    command=self.play_tab.write_ini,
                )
                checkbox.grid(row=row_num, column=0, padx=3, sticky="w")
                row_num += 1

            if section == "general_settings":
                self.enable_console_checkbox.grid(
                    row=row_num, column=0, padx=3, sticky="w"
                )
                row_num += 1
                self.desktop_shortcut_checkbox.grid(
                    row=row_num, column=0, padx=3, sticky="w"
                )
                row_num += 1

    @staticmethod
    def format_text(text):
        return " ".join(text.title().split("_"))

    def handle_console_checkbutton(self):
        self.modlunky_config.config_file.playlunky_console = (
            self.enable_console_var.get()
        )
        self.modlunky_config.config_file.save()

    @property
    def shortcut_path(self):
        return Path(winshell.desktop(), "Playlunky.lnk")

    def make_shortcut(self):
        version = self.modlunky_config.config_file.playlunky_version
        if not version:
            return

        exe_path = PLAYLUNKY_DATA_DIR / version / PLAYLUNKY_EXE

        if not is_windows():
            logger.debug("Making shortcut to %s", exe_path)
            return

        install_dir = self.modlunky_config.install_dir
        arguments = f'--exe_dir="{install_dir}"'

        with winshell.shortcut(f"{self.shortcut_path}") as link:
            link.path = f"{exe_path}"
            link.working_directory = f"{exe_path.parent}"
            link.arguments = arguments
            link.description = "Shortcut to playlunky"

    def remove_shortcut(self):
        if not is_windows():
            logger.debug("Removing shortcut")
            return

        if self.shortcut_path.exists():
            self.shortcut_path.unlink()

    def handle_desktop_shortcut(self):

        shortcut = self.desktop_shortcut_var.get()
        self.modlunky_config.config_file.playlunky_shortcut = shortcut

        self.modlunky_config.config_file.save()

        if shortcut:
            self.make_shortcut()
        else:
            self.remove_shortcut()
