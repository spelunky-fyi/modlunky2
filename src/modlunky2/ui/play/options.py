import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from modlunky2.config import Config
from modlunky2.ui.play.config import SECTIONS, OPTION_TYPES
from modlunky2.utils import is_windows

from .constants import (
    PLAYLUNKY_DATA_DIR,
    PLAYLUNKY_EXE,
)

if is_windows():
    import winshell  # type: ignore

logger = logging.getLogger(__name__)


class OptionsFrame(ttk.Frame):
    def __init__(self, parent, play_tab, modlunky_config: Config):
        logger.debug("Initializing Playlunky OptionsFrame")
        super().__init__(parent)
        self.parent = parent
        self.play_tab = play_tab
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)

        row_num = 0
        self.ini_options = {}

        self.enable_console_var = tk.BooleanVar()
        self.enable_console_var.set(self.modlunky_config.playlunky_console)
        self.enable_console_checkbox = ttk.Checkbutton(
            self,
            text="Leave Terminal Running",
            variable=self.enable_console_var,
            compound="left",
            command=self.handle_console_checkbutton,
        )

        self.desktop_shortcut_var = tk.BooleanVar()
        self.desktop_shortcut_var.set(self.modlunky_config.playlunky_shortcut)
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
                option_type = OPTION_TYPES.get(option, bool)
                if option_type == int:

                    self.ini_options[option] = tk.IntVar()
                    _frame = ttk.Frame(self)
                    _frame.grid(row=row_num, column=0, sticky="ew")
                    _frame.columnconfigure(0, minsize=60)
                    _frame.columnconfigure(1, weight=1)
                    field = ttk.Entry(
                        _frame,
                        text=self.format_text(option),
                        textvariable=self.ini_options[option],
                        width=4,
                    )
                    field.grid(row=0, column=0, padx=3, sticky="ew")
                    text = ttk.Label(_frame, text=self.format_text(option))
                    text.grid(row=0, column=1, padx=(1, 0), sticky="ew")
                elif option_type == bool:
                    self.ini_options[option] = tk.BooleanVar()
                    checkbox = ttk.Checkbutton(
                        self,
                        text=self.format_text(option),
                        variable=self.ini_options[option],
                        compound="left",
                    )
                    checkbox.grid(row=row_num, column=0, padx=3, sticky="w")
                else:
                    logger.error("Can not handle option type %s", str(option_type))
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
        self.modlunky_config.playlunky_console = self.enable_console_var.get()
        self.modlunky_config.save()

    @property
    def shortcut_path(self):
        return Path(winshell.desktop(), "Playlunky.lnk")

    def make_shortcut(self):
        version = self.modlunky_config.playlunky_version
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
        self.modlunky_config.playlunky_shortcut = shortcut

        self.modlunky_config.save()

        if shortcut:
            self.make_shortcut()
        else:
            self.remove_shortcut()
