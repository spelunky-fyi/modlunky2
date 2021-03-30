import logging
import json

try:
    import winreg
except ImportError:
    winreg = None
from shutil import copyfile
from pathlib import Path

from appdirs import user_config_dir, user_data_dir, user_cache_dir

from modlunky2.constants import APP_DIR

PROGRAMS_KEY = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
DEFAULT_PATH = Path("C:/Program Files (x86)/Steam/steamapps/common/Spelunky 2")
EXE_NAME = "Spel2.exe"

APP_AUTHOR = "spelunky.fyi"
APP_NAME = "modlunky2"
CONFIG_DIR = Path(user_config_dir(APP_NAME, APP_AUTHOR))
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))

MIN_WIDTH = 1280
MIN_HEIGHT = 768


# Sentinel for tracking unset fields
NOT_PRESENT = object()

SPELUNKY_FYI_ROOT_DEFAULT = "https://spelunky.fyi/"

logger = logging.getLogger("modlunky2")


def make_user_dirs():
    for dir_ in [CONFIG_DIR, DATA_DIR, CACHE_DIR]:
        if not dir_.exists():
            dir_.mkdir(parents=True, exist_ok=True)


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
            if name == "Spelunky 2":
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
    if reg_path and (reg_path / EXE_NAME).exists():
        logger.info("Found Spelunky 2!")
        return reg_path

    logger.warning("No Spelunky 2 installation found...")
    return None


class ConfigFile:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.dirty = False

        self.install_dir = None
        self.playlunky_version = None
        self.playlunky_console = False
        self.geometry = None
        self.spelunky_fyi_root = None
        self.spelunky_fyi_api_token = None
        self.theme = None

    @classmethod
    def from_path(cls, config_path: Path):
        obj = cls(config_path=config_path)
        needs_save = False

        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as config_file:
                try:
                    config_data = json.load(config_file)
                except Exception as err:  # pylint: disable=broad-except
                    logger.critical(
                        "Failed to read config file: %s. Creating new one from defaults.",
                        err,
                    )
                    needs_save = True
                    config_data = {}
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

        # Initialize playlunky config
        obj.playlunky_version = config_data.get("playlunky-version")
        obj.playlunky_console = config_data.get("playlunky-console", False)

        # Initialize geometry
        obj.geometry = config_data.get("geometry", f"{MIN_WIDTH}x{MIN_HEIGHT}")

        # FYI Config
        obj.spelunky_fyi_root = config_data.get(
            "spelunky-fyi-root", SPELUNKY_FYI_ROOT_DEFAULT
        )
        obj.spelunky_fyi_api_token = config_data.get("spelunky-fyi-api-token")

        obj.theme = config_data.get("theme", None)

        if needs_save:
            obj.save()

        return obj

    def to_dict(self):
        install_dir = None
        if self.install_dir:
            install_dir = self.install_dir.as_posix()

        out = {}
        out["install-dir"] = install_dir

        if self.playlunky_version is not None:
            out["playlunky-version"] = self.playlunky_version
        out["playlunky-console"] = self.playlunky_console

        out["geometry"] = self.geometry

        if self.spelunky_fyi_api_token is not None:
            out["spelunky-fyi-api-token"] = self.spelunky_fyi_api_token

        if self.spelunky_fyi_root != SPELUNKY_FYI_ROOT_DEFAULT:
            out["spelunky-fyi-root"] = self.spelunky_fyi_root

        out["theme"] = self.theme

        return out

    def _get_tmp_path(self):
        return self.config_path.with_suffix(f"{self.config_path.suffix}.tmp")

    def save(self):
        self.dirty = False

        # Make a temporary file so we can do an atomic replace
        # in case something crashes while writing out the config.
        tmp_path = self._get_tmp_path()
        with tmp_path.open("w", encoding="utf-8") as tmp_file:
            json.dump(self.to_dict(), tmp_file, indent=4, sort_keys=True)

        copyfile(tmp_path, self.config_path)
        tmp_path.unlink()


class Config:
    def __init__(self, config_file: ConfigFile):
        self.config_file = config_file

        self._install_dir = NOT_PRESENT
        self.beta = False

    @classmethod
    def from_path(cls, config_path: Path):
        return cls(config_file=ConfigFile.from_path(config_path))

    @classmethod
    def default(cls):
        return Config.from_path(CONFIG_DIR / "config.json")

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
