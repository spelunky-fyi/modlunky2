import argparse
import logging
from pathlib import Path
import sys
import tkinter as tk
import traceback
from tkinter import PhotoImage, ttk
from typing import Optional

from modlunky2.config import MIN_HEIGHT, MIN_WIDTH, Config, make_user_dirs
from modlunky2.constants import BASE_DIR
from modlunky2.ui.levels.tab import LevelsTab
from modlunky2.utils import tb_info, temp_chdir

# Explicit name since this module can be __main__
logger = logging.getLogger("modlunky2.ui.levels.cli")


def exception_logger(type_, value, traceb):
    exc = traceback.format_exception(type_, value, traceb)
    logger.critical("Unhandled Exception: %s", "".join(exc).strip())


class LevelEditor:
    def __init__(self, modlunky_config: Config):
        logger.debug("Initializing UI")
        self.modlunky_config = modlunky_config

        self._shutdown_handlers = []
        self._shutting_down = False

        self.root = tk.Tk(className="Modlunky2 Level Editor")
        self.load_themes()
        style = ttk.Style(self.root)
        self.root.default_theme = style.theme_use()
        valid_themes = self.root.call("ttk::themes")

        self.root.title("Modlunky2 Level Editor")
        if modlunky_config.theme and modlunky_config.theme in valid_themes:
            style.theme_use(modlunky_config.theme)
        self.root.event_add("<<ThemeChange>>", "None")

        style.configure(
            "ModList.TCheckbutton",
            font=("Segoe UI", 12, "bold"),
            # TODO: dynamic sizing for larger windows
            wraplength="640",
        )
        style.configure("Update.TButton", font="sans 12 bold")
        style.configure("TOptionMenu", anchor="w")
        style.configure("Link.TLabel", foreground="royal blue")
        style.configure(
            "Thicc.TButton",
            font=("Arial", 16, "bold"),
        )

        default_background = style.lookup("TFrame", "background")
        self.root.configure(bg=default_background)

        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")
        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.root.iconphoto(False, self.icon_png)

        sys.excepthook = exception_logger
        self.root.report_callback_exception = exception_logger

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.top_frame = ttk.Frame(self.root)
        self.top_frame.grid(row=0, column=0, sticky="nsew")

        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_rowconfigure(0, weight=0)
        self.top_frame.grid_rowconfigure(1, weight=1)
        self.top_frame.grid_rowconfigure(2, weight=0)

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<Escape>", self.quit)

        self.tab_control = ttk.Notebook(self.top_frame)
        self.tab_control.grid(column=0, row=1, padx=2, pady=(4, 0), sticky="nsew")
        self.tab = LevelsTab(
            tab_control=self.tab_control,
            modlunky_ui=self,
            modlunky_config=modlunky_config,
            standalone=True,
        )
        self.tab_control.add(self.tab, text="Level Editor")

    def tabs_needing_save(self):
        return self.tab.save_needed

    def should_close(self):
        msg_box = tk.messagebox.askquestion(
            "Close Modlunky2?",
            (
                "You have unsaved changes.\n"
                "Are you sure you want to exit without saving?"
            ),
            icon="warning",
        )
        return msg_box == "yes"

    def quit(self, _event=None):
        if self._shutting_down:
            return

        should_close = True
        if self.tab.save_needed:
            should_close = self.should_close()

        if not should_close:
            return

        self._shutting_down = True
        logger.info("Shutting Down.")
        for handler in self._shutdown_handlers:
            handler()

        self.root.quit()
        self.root.destroy()

    def register_shutdown_handler(self, func):
        self._shutdown_handlers.append(func)

    def forget_console(self):
        pass

    def mainloop(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()

    def load_themes(self):
        static_dir = BASE_DIR / "static"
        themes_dir = static_dir / "themes"
        with temp_chdir(static_dir):
            self.root.call("lappend", "auto_path", f"[{themes_dir}]")
            self.root.eval("source themes/pkgIndex.tcl")


def main():
    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument(
        "--config-file",
        type=Path,
        default=None,
        help="The modlunky2 config file to use",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="What level to log at. Default: %(default)s",
    )
    parser.add_argument(
        "--launcher-exe",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    log_format = "%(asctime)s.%(msecs)03d: %(message)s"
    log_level = logging.getLevelName(args.log_level)
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(log_level)

    try:
        launch(args)
    except Exception:  # pylint: disable=broad-except
        logger.critical("%s", tb_info())
        input("Failed to launch Modlunky 2. Press Enter to exit...")


def launch(args):
    make_user_dirs()
    launcher_exe: Optional[Path] = args.launcher_exe
    exe_dir = None
    if launcher_exe:
        exe_dir = launcher_exe.parent

    config = Config.from_path(
        config_path=args.config_file,
        launcher_exe=launcher_exe,
        exe_dir=exe_dir,
    )

    native_ui = LevelEditor(config)
    native_ui.mainloop()


if __name__ == "__main__":
    main()
