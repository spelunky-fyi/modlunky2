from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import logging
import shutil
import time
from enum import Enum
from typing import List, Optional, TypeVar, Set

try:
    import winreg
except ImportError:
    winreg = None

from pathlib import Path
from shutil import copyfile
from urllib.parse import urlparse, urlunparse

from platformdirs import user_config_dir, user_data_dir, user_cache_dir
from serde.core import field
from serde.de import deserialize
from serde.se import serialize
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
DEFAULT_FONT_SIZE = 24
DEFAULT_FONT_FAMILY = "Helvetica"

logger = logging.getLogger(__name__)


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


def guess_install_dir(exe_dir: Optional[Path] = None):
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


T = TypeVar("T")


# Common config for all trackers. Currently a placeholder
@dataclass
class CommonTrackerConfig:
    def clone(self: T) -> T:
        return deepcopy(self)


class SaveableCategory(Enum):
    NO = "No%"
    NO_GOLD = "No Gold"
    PACIFIST = "Pacifist"


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class CategoryTrackerConfig(CommonTrackerConfig):
    always_show_modifiers: bool = field(default=False, skip_if_default=True)
    excluded_categories: Optional[Set[SaveableCategory]] = field(
        default=None, skip_if_default=True
    )


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class PacifistTrackerConfig(CommonTrackerConfig):
    show_kill_count: bool = field(default=False, skip_if_default=True)


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class TimerTrackerConfig(CommonTrackerConfig):
    show_total: bool = field(default=True, skip_if_default=True)
    show_level: bool = field(default=True, skip_if_default=True)
    show_last_level: bool = field(default=True, skip_if_default=True)
    show_tutorial: bool = field(default=False, skip_if_default=True)
    show_session: bool = field(default=False, skip_if_default=True)
    show_ils: bool = field(default=False, skip_if_default=True)


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class GemTrackerConfig(CommonTrackerConfig):
    show_total_gem_count: bool = field(default=False, skip_if_default=True)
    show_colored_gem_count: bool = field(default=False, skip_if_default=True)
    show_diamond_count: bool = field(default=True, skip_if_default=True)
    show_yem_count: bool = field(default=True, skip_if_default=True)
    show_diamond_percentage: bool = field(default=True, skip_if_default=True)


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class PacinoGolfTrackerConfig(CommonTrackerConfig):
    show_total_strokes: bool = field(default=True, skip_if_default=True)
    show_resource_strokes: bool = field(default=False, skip_if_default=True)
    show_treasure_strokes: bool = field(default=False, skip_if_default=True)
    show_pacifist_strokes: bool = field(default=False, skip_if_default=True)


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class TrackersConfig:
    category: CategoryTrackerConfig = field(default_factory=CategoryTrackerConfig)
    pacifist: PacifistTrackerConfig = field(default_factory=PacifistTrackerConfig)
    timer: TimerTrackerConfig = field(default_factory=TimerTrackerConfig)
    gem: GemTrackerConfig = field(default_factory=GemTrackerConfig)
    pacino_golf: PacinoGolfTrackerConfig = field(
        default_factory=PacinoGolfTrackerConfig
    )


@serialize  # Note: these fields aren't renamed for historical reasons
@deserialize
@dataclass
class CustomLevelSaveFormat:
    name: str
    room_template_format: str
    include_vanilla_setrooms: bool

    @classmethod
    def level_sequence(cls):
        return cls("LevelSequence", "setroom{y}_{x}", True)

    @classmethod
    def vanilla(cls):
        return cls("Vanilla setroom [warning]", "setroom{y}-{x}", False)


@serialize(rename_all="kebabcase")
@deserialize(rename_all="kebabcase")
@dataclass
class Config:
    config_path: Optional[Path] = field(default=None, metadata={"serde_skip": True})
    dirty: bool = field(default=False, metadata={"serde_skip": True})

    launcher_exe: Optional[Path] = field(default=None, metadata={"serde_skip": True})
    exe_dir: Optional[Path] = field(default=None, metadata={"serde_skip": True})

    install_dir: Optional[Path] = field(
        default=None,
        # Use custom deserializer to handle None. Unclear why only this field fails
        metadata={"serde_deserializer": lambda v: v if v is None else Path(v)},
    )
    playlunky_version: Optional[str] = field(default=None, skip_if_default=True)
    playlunky_console: bool = field(default=False, skip_if_default=True)
    playlunky_overlunky: bool = field(default=False, skip_if_default=True)
    playlunky_shortcut: bool = field(default=False, skip_if_default=True)
    geometry: str = field(default=f"{MIN_WIDTH}x{MIN_HEIGHT}", skip_if_default=True)
    spelunky_fyi_root: str = field(
        default=SPELUNKY_FYI_ROOT_DEFAULT, skip_if_default=True
    )
    spelunky_fyi_api_token: Optional[str] = field(default=None, skip_if_default=True)
    theme: Optional[str] = field(default=None, skip_if_default=True)
    last_install_browse: Path = field(
        default=Path(LAST_INSTALL_BROWSE_DEFAULT), skip_if_default=True
    )
    last_tab: Optional[str] = field(default=None, skip_if_default=True)
    tracker_color_key: str = field(default=DEFAULT_COLOR_KEY, skip_if_default=True)
    tracker_font_size: int = field(default=DEFAULT_FONT_SIZE, skip_if_default=True)
    tracker_font_family: str = field(default=DEFAULT_FONT_FAMILY, skip_if_default=True)
    trackers: TrackersConfig = field(default_factory=TrackersConfig)
    show_packing: bool = field(default=False, skip_if_default=True)
    level_editor_tab: Optional[int] = field(default=None, skip_if_default=True)
    custom_level_editor_custom_save_formats: List[CustomLevelSaveFormat] = field(
        default_factory=list
    )
    custom_level_editor_default_save_format: Optional[CustomLevelSaveFormat] = field(
        default=None, skip_if_default=True
    )
    command_prefix: Optional[List[str]] = field(default=None, skip_if_default=True)
    api_port: int = field(default=9526)

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

        config = None
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as config_file:
                try:
                    config = serde.json.from_json(Config, config_file.read())
                    config.config_path = config_path
                except json.decoder.JSONDecodeError:
                    now = int(time.time())
                    backup_path = config_path.with_suffix(f".{now}.json")
                    logger.exception(
                        "Failed to load config. Backing up to %s",
                    )
                    shutil.copyfile(config_path, backup_path)

        if config is None:
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
        if self.config_path is None:
            raise TypeError("config_path shouldn't be None")
        return self.config_path.with_suffix(f"{self.config_path.suffix}.tmp")

    def save(self):
        if self.config_path is None:
            raise TypeError("config_path shouldn't be None")
        self.dirty = False

        # Make a temporary file so we can do an atomic replace
        # in case something crashes while writing out the config.
        tmp_path = self._get_tmp_path()
        with tmp_path.open("w", encoding="utf-8") as tmp_file:
            file_content = serde.json.to_json(self, indent=4, sort_keys=True)
            tmp_file.write(file_content)

        copyfile(tmp_path, self.config_path)
        tmp_path.unlink()
