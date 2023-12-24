from dataclasses import dataclass
from typing import List, Optional

from modlunky2.levels.level_templates import TemplateSetting
from modlunky2.ui.levels.shared.setrooms import MatchedSetroom


@dataclass
class DependencyPalette:
    name: str
    tiles: List
