import argparse
import logging
from pathlib import Path
from typing import Optional

from modlunky2.ui import ModlunkyUI
from modlunky2.config import Config, make_user_dirs
from modlunky2.utils import tb_info
import modlunky2.web.service as web_service

# Explicit name since this module can be __main__
logger = logging.getLogger("modlunky2.cli")


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
        launch(args, log_level)
    except Exception:  # pylint: disable=broad-except
        logger.critical("%s", tb_info())
        input("Failed to launch Modlunky 2. Press Enter to exit...")


def launch(args, log_level):
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

    shutdown_callback = web_service.launch_in_thread(config)
    native_ui = ModlunkyUI(config, log_level)
    native_ui.mainloop()
    shutdown_callback()
