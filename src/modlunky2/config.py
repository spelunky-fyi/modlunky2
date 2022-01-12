from __future__ import annotations

import dataclasses
from dataclasses import dataclass
import json
import logging
import shutil
import time
from enum import Enum
from typing import Dict, List, Optional, TypeVar, Set

try:
    import winreg
except ImportError:
    winreg = None

from pathlib import Path
from shutil import copyfile
from urllib.parse import urlparse, urlunparse

from platformdirs import user_config_dir, user_data_dir, user_cache_dir
from serde import serialize, deserialize
import serde.json

from modlunky2.utils import is_windows

if is_windows():
    # Import for pyinstaller to detect this module
    import platformdirs.windows  # pylint: disable=unused-import

PROGRAMS_KEY = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
DEFAULT_PATH = Path("C:/Program Files (x86)/Steam/steamapps/common/Spelunky 2")
EXE_NAME = "Spel2.exe"

APP_AUTHOR = "spelunky.fyi"
APP_NAME = "modlunky2"
CONFIG_DIR = Path(user_config_dir(APP_NAME, APP_AUTHOR))
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
SHOW_PACKING_DEFAULT = False

MIN_WIDTH = 1280
MIN_HEIGHT = 768


# Sentinel for tracking unset fields
NOT_PRESENT = object()

SPELUNKY_FYI_ROOT_DEFAULT = "https://spelunky.fyi/"
LAST_INSTALL_BROWSE_DEFAULT = "/"

DEFAULT_COLOR_KEY = "#ff00ff"

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


def guess_install_dir(exe_dir=None):
    if exe_dir:
        logger.info("Checking if Spelunky 2 is installed in %s", exe_dir)
        if (exe_dir / EXE_NAME).exists():
            logger.info("Found Spelunky 2!")
            return exe_dir

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


def skip_default_field(default, metadata: Optional[Dict] = None, **kwargs):
    if metadata is None:
        metadata = {}
    if "serde_skip_if" in metadata:
        raise ValueError(
            f"metadata already contains 'serde_skip_if' with value {metadata['serde_skip_if']}"
        )
    # Technically, pyserde permits these to be set with 'serde_skip_if', but it seems dubious
    if "serde_skip" in metadata:
        raise ValueError(
            "metadata  contains 'serde_skip' which conflicts with 'serde_skip_if'"
        )
    if "serde_skip_if_false" in metadata:
        raise ValueError(
            "metadata  contains 'serde_skip_if_false' which conflicts with 'serde_skip_if'"
        )
    metadata["serde_skip_if"] = lambda v: v == default
    return dataclasses.field(default=default, metadata=metadata, **kwargs)


T = TypeVar("T")

# Common config for all trackers. Currently a placeholder
@dataclass
class CommonTrackerConfig:
    def clone(self: T) -> T:
        return dataclasses.replace(self)


class SaveableCategory(Enum):
    NO = "No%"
    NO_GOLD = "No Gold"
    PACIFIST = "Pacifist"


@serialize(rename_all="spinalcase")
@deserialize(rename_all="spinalcase")
@dataclass
class CategoryTrackerConfig(CommonTrackerConfig):
    always_show_modifiers: bool = skip_default_field(default=False)
    excluded_categories: Optional[Set[SaveableCategory]] = skip_default_field(
        default=None
    )


@serialize(rename_all="spinalcase")
@deserialize(rename_all="spinalcase")
@dataclass
class PacifistTrackerConfig(CommonTrackerConfig):
    show_kill_count: bool = skip_default_field(default=False)


@serialize(rename_all="spinalcase")
@deserialize(rename_all="spinalcase")
@dataclass
class TrackersConfig:
    category: CategoryTrackerConfig = dataclasses.field(
        default_factory=CategoryTrackerConfig
    )
    pacifist: PacifistTrackerConfig = dataclasses.field(
        default_factory=PacifistTrackerConfig
    )


@serialize(rename_all="spinalcase")
@deserialize(rename_all="spinalcase")
@dataclass
class Config:
    config_path: Optional[Path] = dataclasses.field(
        default=None, metadata={"serde_skip": True}
    )
    dirty: bool = dataclasses.field(default=False, metadata={"serde_skip": True})

    launcher_exe: Optional[Path] = dataclasses.field(
        default=None, metadata={"serde_skip": True}
    )
    exe_dir: Optional[Path] = dataclasses.field(
        default=None, metadata={"serde_skip": True}
    )

    install_dir: Optional[Path] = dataclasses.field(
        default=None,
        # Use custom deserializer to handle None. Unclear why only this field fails
        metadata={"serde_deserializer": lambda v: v if v is None else Path(v)},
    )
    playlunky_version: Optional[str] = skip_default_field(default=None)
    playlunky_console: bool = skip_default_field(default=False)
    playlunky_shortcut: bool = skip_default_field(default=False)
    geometry: str = skip_default_field(default=f"{MIN_WIDTH}x{MIN_HEIGHT}")
    spelunky_fyi_root: str = skip_default_field(default=SPELUNKY_FYI_ROOT_DEFAULT)
    spelunky_fyi_api_token: Optional[str] = skip_default_field(default=None)
    theme: Optional[str] = skip_default_field(default=None)
    last_install_browse: Path = skip_default_field(
        default=Path(LAST_INSTALL_BROWSE_DEFAULT)
    )
    last_tab: Optional[str] = skip_default_field(default=None)
    tracker_color_key: str = skip_default_field(default=DEFAULT_COLOR_KEY)
    trackers: TrackersConfig = dataclasses.field(default_factory=TrackersConfig)
    show_packing: bool = skip_default_field(default=False)
    level_editor_tab: Optional[int] = skip_default_field(default=None)
    custom_level_editor_custom_save_formats: Optional[List[Dict]] = skip_default_field(
        default=None
    )
    custom_level_editor_default_save_format: Optional[Dict] = skip_default_field(
        default=None
    )

    def __post_init__(self):
        if self.exe_dir is None:
            self.exe_dir = Path(__file__).resolve().parent

    @classmethod
    def from_path(
        cls,
        config_path: Path = None,
        exe_dir: Optional[Path] = None,
        launcher_exe: Optional[Path] = None,
    ):
        if config_path is None:
            config_path = CONFIG_DIR / "config.json"
        if exe_dir is None:
            exe_dir = Path(__file__).resolve().parent

        make_new = True
        if config_path.exists():
            make_new = False
            with config_path.open("r", encoding="utf-8") as config_file:
                try:
                    config = serde.json.from_json(Config, config_file.read())
                    config.config_path = config_path
                except json.decoder.JSONDecodeError:
                    make_new = True
                    now = int(time.time())
                    backup_path = config_path.with_suffix(f".{now}.json")
                    logger.exception(
                        "Failed to load config. Backing up to %s",
                    )
                    shutil.copyfile(config_path, backup_path)

        if make_new:
            config = Config()
            config.install_dir = guess_install_dir(exe_dir)
            config.config_path = config_path
            config.save()

        config.launcher_exe = launcher_exe
        config.exe_dir = exe_dir

        return config

    @property
    def spelunky_fyi_ws_root(self):
        if not self.spelunky_fyi_root:
            return None

        parts = urlparse(self.spelunky_fyi_root)
        if parts.scheme == "http":
            parts = parts._replace(scheme="ws")
        elif parts.scheme == "https":
            parts = parts._replace(scheme="wss")
        else:
            raise RuntimeError(f"Unexpected scheme found: {self.spelunky_fyi_root}")

        return urlunparse(parts)

    def _get_tmp_path(self):
        return self.config_path.with_suffix(f"{self.config_path.suffix}.tmp")

    def save(self):
        self.dirty = False

        # Make a temporary file so we can do an atomic replace
        # in case something crashes while writing out the config.
        tmp_path = self._get_tmp_path()
        with tmp_path.open("w", encoding="utf-8") as tmp_file:
            file_content = serde.json.to_json(self, indent=4, sort_keys=True)
            tmp_file.write(file_content)

        copyfile(tmp_path, self.config_path)
        tmp_path.unlink()
