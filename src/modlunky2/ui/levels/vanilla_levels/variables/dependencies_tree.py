from dataclasses import dataclass
import logging
import os
import os.path
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from modlunky2.levels import LevelFile
from modlunky2.levels.level_templates import Chunk
from modlunky2.levels.tile_codes import VALID_TILE_CODES, TileCode, TileCodes, ShortCode
from modlunky2.utils import tb_info
from modlunky2.ui.levels.vanilla_levels.variables.level_dependencies import SisterLocation

logger = logging.getLogger(__name__)

@dataclass
class BrokenTile:
    level: SisterLocation
    tile: TileCode

class DependenciesTree(ttk.Treeview):
    def __init__(self, parent, lvls_path, extracts_path, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.lvls_path = lvls_path
        self.extracts_path = extracts_path
        self.sister_locations = []
        self.current_location = None

        self["columns"] = ("1", "2", "3")
        self["show"] = "headings"
        self.column("1", width=100, anchor="w")
        self.column("2", width=10, anchor="w")
        self.column("3", width=100, anchor="w")
        self.heading("1", text="Tile Id")
        self.heading("2", text="Tilecode")
        self.heading("3", text="File")

    def find_broken_tiles(self):
        broken_tiles = []

        for tilecode in self.current_location.level.tile_codes.all():
            checked_levels = [self.current_location.level_name]
            added_code = False
            for level_path in self.sister_locations:
                for other_location in level_path:
                    if other_location.level_name in checked_levels:
                        continue

                    checked_levels.append(other_location.level_name)
                    for othertilecode in other_location.level.tile_codes.all():
                        if tilecode.value == othertilecode.value and tilecode.name != othertilecode.name:
                            if not added_code:
                                added_code = True
                                broken_tiles.append(
                                    BrokenTile(self.current_location, tilecode)
                                )
                            broken_tiles.append(BrokenTile(other_location, othertilecode))
                            logger.debug(
                                "tilecode conflict: %s",
                                tilecode.value,
                            )
                            logger.debug(
                                "in %s %s file and %s %s file",
                                self.current_location.level_name,
                                self.current_location.location,
                                other_location.level_name,
                                other_location.location,
                            )
                            logger.debug(
                                "comparing tileids %s to %s",
                                tilecode.name,
                                othertilecode.name,
                            )
        return broken_tiles

    def resolve_conflicts(self):
        usable_codes = ShortCode.usable_codes()

        # finds tilecodes that are taken in all the dependacy files
        for levelpath in self.sister_locations:
            for level in levelpath:
                used_codes = level.level.tile_codes.all()
                for code in used_codes:
                    if code.value in usable_codes:
                        usable_codes.remove(code.value)

        for broken_tile in self.find_broken_tiles():
            if broken_tile.level.level != self.current_location.level:
                continue

            old_tile = broken_tile.tile
            old_tile_code = old_tile.value

            level = broken_tile.level.level
            if len(usable_codes) > 0:
                new_code = str(usable_codes[0])
                usable_codes.remove(new_code)
                level.tile_codes.set_obj(
                    TileCode(
                        name = old_tile.name,
                        value = new_code,
                        comment = old_tile.comment
                    )
                )  # adds new tile to database with new code
            else:
                logger.warning("Not enough unique tilecodes left")
                break

            for template in level.level_templates.all():
                new_chunks = []
                for room in template.chunks:
                    foreground = [ [ str(new_code) if str(code) == str(old_tile_code) else str(code) for code in row] for row in room.foreground]
                    background = [ [ str(new_code) if str(code) == str(old_tile_code) else str(code) for code in row] for row in room.background]
                    new_chunks.append(
                        Chunk(
                            comment = room.comment,
                            settings = room.settings,
                            foreground = foreground,
                            background = background,
                        )
                    )
                template.chunks = new_chunks

        if not self.lvls_path:
            raise RuntimeError("self.lvls_path not configured.")

        if not os.path.exists(Path(self.lvls_path)):
            os.makedirs(Path(self.lvls_path))

        path = Path(self.lvls_path / self.current_location.level_name)
        with Path(path).open("w", encoding="cp1252") as handle:
            self.current_location.level.write(handle)
            logger.debug("Fixed conflicts in %s", self.current_location.level_name)

    def update_dependencies(self, level_paths, current_location):
        self.sister_locations = level_paths
        self.current_location = current_location
        broken_tiles = self.find_broken_tiles()

        for broken_tile in broken_tiles:
            self.insert(
                "",
                "end",
                text="L1",
                values=(
                    str(broken_tile.tile.name),
                    str(broken_tile.tile.value),
                    str(broken_tile.level.level_name) + " " + str(broken_tile.level.location) + " file",
                ),
            )

    def clear(self):
        for i in self.get_children():
            self.delete(i)

    def update_lvls_path(self, new_path):
        self.lvls_path = new_path
