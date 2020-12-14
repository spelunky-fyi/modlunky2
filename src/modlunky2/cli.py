import argparse
import logging
from pathlib import Path

from .constants import APP_DIR
from .ui import ModlunkyUI


def main():
    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument(
        "--install-dir",
        default=APP_DIR,
        help="Path to Spelunky 2 installation. (Default: %(default)s",
    )
    parser.add_argument(
        "--beta", default=False, action="store_true", help="Display beta features."
    )
    args = parser.parse_args()

    log_format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")

    install_dir = Path(args.install_dir)

    native_ui = ModlunkyUI(install_dir, args.beta)
    native_ui.mainloop()
