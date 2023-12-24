from dataclasses import dataclass
from typing import List
from PIL import ImageTk


@dataclass
class Tile:
    name: str
    code: str
    image: ImageTk.PhotoImage
    picker_image: ImageTk.PhotoImage


@dataclass
class DependencyPalette:
    name: str
    tiles: List
