import argparse
import logging
from os.path import exists
from pathlib import Path

from appdirs import user_config_dir, user_data_dir
from setuptools.command.bdist_egg import INSTALL_DIRECTORY_ATTRS

from .constants import APP_DIR
from .ui import ModlunkyUI

APP_AUTHOR = "spelunky.fyi"
APP_NAME = "modlunky2"


def make_dirs(*dirs):
    for dir_ in dirs:
        if not dir_.exists():
            dir_.mkdir(parents=True, exist_ok=True)


class Config:
    def __init__(self, config_path):
        self.config_path = config_path

        self.install_dir = None

    @classmethod
    def from_path(cls, config_path):
        obj = cls(config_path=config_path)

        if config_path.exists():
            with config_path.open("r") as config_file:
                config_data = json.load(config_file)
        else:
            config_data = {}

        obj.install_dir = config_data.get("install-dir")

        return obj

    def to_dict(self):
        return {
            "install-dir": self.install_dir,
        }

    def _get_tmp_path(self):
        return self.config_path.with_suffix(f"{self.config_path.suffix}.tmp")

    def save(self):
        tmp_path = self._get_tmp_path()




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

    config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))

    make_dirs(config_dir, data_dir)

    native_ui = ModlunkyUI(install_dir, args.beta)
    native_ui.mainloop()
