import argparse
import logging
from pathlib import Path

from modlunky2.ui import ModlunkyUI
from modlunky2.config import Config, make_user_dirs
from modlunky2.utils import tb_info

logger = logging.getLogger("modlunky2")


def main():
    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument(
        "--install-dir",
        default=None,
        help="Path to Spelunky 2 installation. (Default: %(default)s",
    )
    parser.add_argument(
        "--beta", default=False, action="store_true", help="Display beta features."
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
        default=None,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    log_format = "%(asctime)s: %(message)s"
    log_level = logging.getLevelName(args.log_level)
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")
    logger.setLevel(log_level)

    try:
        launch(args, log_level)
    except Exception:  # pylint: disable=broad-except
        logger.critical("%s", tb_info())
        input("Failed to launch Modlunky 2. Press Enter to exit...")


def launch(args, log_level):

    make_user_dirs()
    launcher_exe = args.launcher_exe
    exe_dir = None
    if launcher_exe:
        launcher_exe = Path(launcher_exe)
        exe_dir = launcher_exe.parent

    config = Config.default(launcher_exe=launcher_exe, exe_dir=exe_dir)

    if args.install_dir:
        config.install_dir = Path(args.install_dir)

    if args.beta:
        config.beta = True

    native_ui = ModlunkyUI(config, log_level)
    native_ui.mainloop()
