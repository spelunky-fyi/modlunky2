from dataclasses import dataclass
from typing import Dict, List, Optional, TypeVar, Set
from pathlib import Path
from shutil import copyfile
from serde.core import field
from serde.de import deserialize
from serde.se import serialize
import serde.json

from modlunky2.ui.levels.custom_levels.level_configurations.level_configuration import (
    LevelConfiguration,
)

LEVEL_CONFIGURATION_FILE_NAME = "level_configuration.ls"


@serialize
@deserialize
@dataclass
class LevelConfigurations:
    sequence: List[LevelConfiguration] = field(default_factory=list)
    all_configurations: Dict[str, LevelConfiguration] = field(
        default_factory=dict, skip_if_default=True
    )

    @classmethod
    def from_path(cls, lvl_path: Path):
        level_configuration_path = lvl_path / LEVEL_CONFIGURATION_FILE_NAME

        if level_configuration_path.exists():
            with level_configuration_path.open(
                "r", encoding="utf-8"
            ) as level_configuration_file:
                try:
                    level_configuration = serde.json.from_json(
                        LevelConfigurations, level_configuration_file.read()
                    )

                    return level_configuration
                except:
                    return LevelConfigurations()

        return LevelConfigurations()

    def save(self, lvl_path: Path):
        level_configuration_path = lvl_path / LEVEL_CONFIGURATION_FILE_NAME

        print(level_configuration_path.suffix)
        tmp_path = level_configuration_path.with_suffix(f"{level_configuration_path.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as tmp_file:
            file_content = serde.json.to_json(self, indent=2)
            tmp_file.write(file_content)

        copyfile(tmp_path, level_configuration_path)
        tmp_path.unlink()
