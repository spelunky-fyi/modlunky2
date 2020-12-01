import argparse
import logging
from pathlib import Path

import requests
from packaging import version

from .constants import APP_DIR, ROOT_DIR
from .ui import ModlunkyUI


def get_latest_version():
    try:
        return version.parse(
            requests.get(
                "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest"
            ).json()["tag_name"]
        )
    except Exception:  # pylint: disable=broad-except
        return None


def get_current_version():
    with (ROOT_DIR / "VERSION").open() as version_file:
        return version.parse(version_file.read().strip())


def main():
    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="The host to listen on."
    )
    parser.add_argument("--port", type=int, default=8040, help="Port to listen on.")
    parser.add_argument("--debug", default=False, action="store_true")
    parser.add_argument(
        "--install-dir",
        default=APP_DIR,
        help="Path to Spelunky 2 installation. (Default: %(default)s",
    )
    args = parser.parse_args()

    log_format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")

    install_dir = Path(args.install_dir)

    current_version = get_current_version()
    latest_version = get_latest_version()
    needs_update = current_version < latest_version

    native_ui = ModlunkyUI(install_dir, needs_update)
    native_ui.mainloop()
