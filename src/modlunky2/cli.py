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
    args = parser.parse_args()

    log_format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")
    launch(args)


def launch(args):
    config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))

    make_dirs(config_dir, data_dir)
    config = Config.from_path(config_dir / "config.json")

    if args.install_dir:
        config.install_dir = Path(args.install_dir)

    if args.beta:
        config.beta = True

    native_ui = ModlunkyUI(config, data_dir)
    native_ui.mainloop()
