import argparse
import logging
from pathlib import Path

from appdirs import user_config_dir, user_data_dir

from .ui import ModlunkyUI
from .config import Config

APP_AUTHOR = "spelunky.fyi"
APP_NAME = "modlunky2"

logger = logging.getLogger("modlunky2")


def make_dirs(*dirs):
    for dir_ in dirs:
        if not dir_.exists():
            dir_.mkdir(parents=True, exist_ok=True)


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
    args = parser.parse_args()

    log_format = "%(asctime)s: %(message)s"
    log_level = logging.getLevelName(args.log_level)

    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")
    logger.setLevel(log_level)
    launch(args, log_level)


def launch(args, log_level):
    config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))

    make_dirs(config_dir, data_dir)
    config = Config.from_path(config_dir / "config.json")

    if args.install_dir:
        config.install_dir = Path(args.install_dir)

    if args.beta:
        config.beta = True

    native_ui = ModlunkyUI(config, log_level)
    native_ui.mainloop()
