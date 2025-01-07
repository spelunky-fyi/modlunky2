from dataclasses import dataclass
from typing import Optional
from serde.core import field
from serde.de import deserialize
from serde.se import serialize


@serialize
@deserialize
@dataclass
class LevelConfiguration:
    identifier: str
    name: str
    file_name: str
    theme: int
    subtheme: Optional[int] = field(default=None, skip_if_default=True)
    width: Optional[int] = field(default=None, skip_if_default=True) # Required only for Cosmic Ocean levels.
    height: Optional[int] = field(default=None, skip_if_default=True) # Required only for Cosmic Ocean levels.
    border_theme: Optional[int] = field(default=None, skip_if_default=True)
    border_entity_theme: Optional[int] = field(default=None, skip_if_default=True)
    floor_theme: Optional[int] = field(default=None, skip_if_default=True)
    background_theme: Optional[int] = field(default=None, skip_if_default=True)
    background_texture_theme: Optional[int] = field(default=None, skip_if_default=True)
    music_theme: Optional[int] = field(default=None, skip_if_default=True)
