import logging
import json
try:
    import winreg
except ImportError:
    winreg = None

from shutil import copyfile
from pathlib import Path

from modlunky2.constants import APP_DIR


PROGRAMS_KEY = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
DEFAULT_PATH = Path("C:/Program Files (x86)/Steam/steamapps/common/Spelunky 2")
EXE_NAME = "Spel2.exe"

# Sentinel for tracking unset fields
NOT_PRESENT = object()

logger = logging.getLogger("modlunky2")


def check_registry_for_spel2():
    if winreg is None:
        return None

    programs = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PROGRAMS_KEY)

    index = 0
    while True:
        try:
            keyname = winreg.EnumKey(programs, index)
            index += 1
        except OSError:
            return None

        try:
            subkey = winreg.OpenKey(programs, keyname)
            name, _ = winreg.QueryValueEx(subkey, "DisplayName")
            if name == 'Spelunky 2':
                return Path(winreg.QueryValueEx(subkey, "InstallLocation")[0])
        except OSError:
            continue

    return None


def guess_install_dir():
    logger.info("Checking if Spelunky 2 is installed in %s", APP_DIR)
    if (APP_DIR / EXE_NAME).exists():
        logger.info("Found Spelunky 2!")
        return APP_DIR

    logger.info("Checking if Spelunky 2 is installed in %s", DEFAULT_PATH)
    if (DEFAULT_PATH / EXE_NAME).exists():
        logger.info("Found Spelunky 2!")
        return DEFAULT_PATH

    logger.info("Checking Windows Registry for Spelunky 2 Installation")
    reg_path = check_registry_for_spel2()
    if (reg_path / EXE_NAME).exists():
        logger.info("Found Spelunky 2!")
        return reg_path

    logger.warning("No Spelunky 2 installation found...")
    return None


class ConfigFile:
    def __init__(self, config_path: Path):
        self.config_path = config_path

        self.install_dir = None

    @classmethod
    def from_path(cls, config_path: Path):
        obj = cls(config_path=config_path)
        needs_save = False

        if config_path.exists():
            with config_path.open("r") as config_file:
                config_data = json.load(config_file)
        else:
            config_data = {}

        # Initialize install-dir
        install_dir = config_data.get("install-dir", NOT_PRESENT)
        if install_dir is NOT_PRESENT:
            install_dir = guess_install_dir()
            needs_save = True
        elif install_dir is not None:
            install_dir = Path(install_dir)
        obj.install_dir = install_dir

        if needs_save:
            obj.save()

        return obj

    def to_dict(self):
        install_dir = None
        if self.install_dir:
            install_dir = self.install_dir.as_posix()

        return {
            "install-dir": install_dir,
        }

    def _get_tmp_path(self):
        return self.config_path.with_suffix(f"{self.config_path.suffix}.tmp")

    def save(self):
        # Make a temporary file so we can do an atomic replace
        # in case something crashes while writing out the config.
        tmp_path = self._get_tmp_path()
        with tmp_path.open("w") as tmp_file:
            json.dump(self.to_dict(), tmp_file)

        copyfile(tmp_path, self.config_path)
        tmp_path.unlink()


class Config:
    CONFIG_FIELDS = set(["install_dir"])

    def __init__(self, config_file: ConfigFile):
        self.config_file = config_file

        self._install_dir = NOT_PRESENT
        self.beta = False

    @classmethod
    def from_path(cls, config_path: Path):
        return cls(config_file=ConfigFile.from_path(config_path))

    @property
    def install_dir(self):
        if self._install_dir is NOT_PRESENT:
            if self.config_file.install_dir is None:
                return APP_DIR
            return self.config_file.install_dir
        return self._install_dir

    @install_dir.setter
    def install_dir(self, value):
        self._install_dir = value
