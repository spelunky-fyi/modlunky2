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

logger = logging.getLogger(__name__)


class DependenciesTree(ttk.Treeview):
    def __init__(self, parent, lvls_path, extracts_path, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.lvls_path = lvls_path
        self.extracts_path = extracts_path
        self.sister_locations = []

        self["columns"] = ("1", "2", "3")
        self["show"] = "headings"
        self.column("1", width=100, anchor="w")
        self.column("2", width=10, anchor="w")
        self.column("3", width=100, anchor="w")
        self.heading("1", text="Tile Id")
        self.heading("2", text="Tilecode")
        self.heading("3", text="File")

    def resolve_conflicts(self):
        def get_level(file):
            if os.path.exists(Path(self.lvls_path / file)):
                levelp = LevelFile.from_path(Path(self.lvls_path / file))
            else:
                levelp = LevelFile.from_path(Path(self.extracts_path) / file)
            return levelp

        usable_codes = ShortCode.usable_codes()

        # finds tilecodes that are taken in all the dependacy files
        for level in self.sister_locations:
            used_codes = level[1].tile_codes.all()
            for code in used_codes:
                for usable_code in usable_codes:
                    if str(code.value) == str(usable_code):
                        usable_codes.remove(usable_code)
                        # "sister location" = nick name for lvl files in a dependency group
                        logger.debug("removed %s from sister location", code.value)

        for i in self.get_children():  # gets base level conflict to compare
            try:
                item = self.item(
                    i, option="values"
                )  # gets it values ([0] = tile id [1] = tile code [2] = level file name)

                levels = []  # gets list of levels to fix tilecodes among
                # adds item as (level, item values)
                levels.append([get_level(item[2].split(" ")[0]), item])
                # removes item cause its already being worked on so it doesn't
                # get worked on or compared to again
                # self.tree_depend.delete(i)

                for child in self.get_children():
                    item2 = self.item(child, option="values")
                    # finds item with conflicting codes
                    if str(item2[1]) == str(item[1]):
                        levels.append([get_level(item2[2].split(" ")[0]), item2])
                        # removes item cause its already being worked on so it doesn't
                        # get worked on or compared to again
                        # self.tree_depend.delete(child)

                # finds tilecodes that are not available in all the dependacy files
                # (again cause it could have changed since tilecodes are being messed with)
                # might not actually be needed
                for level in levels:
                    used_codes = level[0].tile_codes.all()
                    for code in used_codes:
                        for usable_code in usable_codes:
                            if str(code.value) == str(usable_code):
                                usable_codes.remove(usable_code)
                                logger.debug(
                                    "removed %s cause its already in use", code.value
                                )

                # replaces all the old tile codes with the new ones in the rooms
                for level in levels:
                    # gives tilecodes their own loop
                    tilecode_count = 0
                    tile_codes_new = TileCodes()  # new tilecode database

                    for code in level[0].tile_codes.all():
                        tile_id = str(level[1][0])
                        old_code = str(level[1][1])
                        if str(code.name) == str(
                            tile_id
                        ):  # finds conflicting tilecode by id
                            # makes sure there's even codes left to assing new unique ones
                            if len(usable_codes) > 0:
                                # gets the next available usable code
                                new_code = str(usable_codes[0])
                                tile_codes_new.set_obj(
                                    TileCode(
                                        name=tile_id,
                                        value=new_code,
                                        comment="",
                                    )
                                )  # adds new tilecode to database with new code
                                old_code_found = False
                                for usable_code in usable_codes:
                                    if str(new_code) == str(usable_code):
                                        usable_codes.remove(usable_code)
                                        logger.debug("used and removed %s", new_code)
                                    if str(old_code) == str(usable_code):
                                        old_code_found = True
                                if not old_code_found:
                                    usable_codes.append(
                                        old_code
                                    )  # adds back replaced code since its now free for use again
                            else:
                                logger.warning("Not enough unique tilecodes left")
                                return
                        else:
                            tile_codes_new.set_obj(
                                TileCode(
                                    name=code.name,
                                    value=code.value,
                                    comment="",
                                )  # adds tilecode back to database
                            )
                        tilecode_count = tilecode_count + 1

                    for code in level[0].tile_codes.all():
                        tile_id = str(level[1][0])
                        old_code = str(level[1][1])
                        if str(code.name) == str(tile_id):  # finds conflicting tilecode
                            for new_code in tile_codes_new.all():
                                if new_code.name == code.name:
                                    template_count = 0
                                    for template in level[0].level_templates.all():
                                        new_chunks = []
                                        for room in template.chunks:
                                            row_count = 0
                                            for row in room.foreground:
                                                col_count = 0
                                                for col in row:
                                                    if str(col) == str(old_code):
                                                        room.foreground[row_count][
                                                            col_count
                                                        ] = str(new_code.value)
                                                        logger.debug(
                                                            "replaced %s with %s",
                                                            old_code,
                                                            new_code.value,
                                                        )
                                                    col_count = col_count + 1
                                                row_count = row_count + 1
                                            row_count = 0
                                            for row in room.background:
                                                col_count = 0
                                                for col in row:
                                                    if str(col) == str(old_code):
                                                        room.background[row_count][
                                                            col_count
                                                        ] = str(new_code.value)
                                                        logger.debug(
                                                            "replaced %s with %s",
                                                            old_code,
                                                            new_code.value,
                                                        )
                                                    col_count = col_count + 1
                                                row_count = row_count + 1
                                            new_chunks.append(
                                                Chunk(
                                                    comment=room.comment,
                                                    settings=room.settings,
                                                    foreground=room.foreground,
                                                    background=room.background,
                                                )
                                            )
                                        level[0].level_templates.all()[
                                            template_count
                                        ].chunks = new_chunks
                                        template_count = template_count + 1
                    level[0].tile_codes = tile_codes_new

                    if not self.lvls_path:
                        raise RuntimeError("self.lvls_path not configured.")

                    path = Path(self.lvls_path / str(level[1][2].split(" ")[0]))
                    with Path(path).open("w", encoding="cp1252") as handle:
                        level[0].write(handle)
                        logger.debug("Fixed conflicts in %s", level[1][2].split(" ")[0])
            except Exception:  # pylint: disable=broad-except
                logger.critical("Error: %s", tb_info())

    def update_dependencies(self, levels):
        self.sister_locations = levels
        tilecode_compare = []
        for level in levels:
            logger.debug("getting tilecodes from %s", level[0])
            tilecodes = []
            tilecodes.append(str(level[0]) + " " + str(level[2]) + " file")
            level_tilecodes = level[1].tile_codes.all()

            for tilecode in level_tilecodes:
                tilecodes.append(str(tilecode.name) + " " + str(tilecode.value))
            tilecode_compare.append(tilecodes)

        for lvl_tilecodes in tilecode_compare:  # for list of tilecodes in each lvl
            for tilecode in lvl_tilecodes:  # for each tilecode in the lvl
                # for list of tilecodes in each lvl to compare to
                for lvl_tilecodes_compare in tilecode_compare:
                    # makes sure it doesn't compare to itself
                    if lvl_tilecodes_compare[0] != lvl_tilecodes[0]:
                        # for each tilecode in the lvl being compared to
                        for tilecode_compare_to in lvl_tilecodes_compare:
                            # makes sure its not the header
                            if (
                                len(tilecode.split(" ")) != 3
                                and len(tilecode_compare_to.split(" ")) != 3
                            ):
                                # if tilecodes match
                                if str(tilecode.split(" ")[1]) == str(
                                    tilecode_compare_to.split(" ")[1]
                                ):
                                    # if tilecodes aren't assigned to same thing
                                    if str(tilecode.split(" ")[0]) != str(
                                        tilecode_compare_to.split(" ")[0]
                                    ):
                                        logger.debug(
                                            "tilecode conflict: %s",
                                            tilecode.split(" ")[1],
                                        )
                                        logger.debug(
                                            "in %s and %s",
                                            lvl_tilecodes[0],
                                            lvl_tilecodes_compare[0],
                                        )
                                        logger.debug(
                                            "comparing tileids %s to %s",
                                            tilecode.split(" ")[0],
                                            tilecode_compare_to.split(" ")[0],
                                        )
                                        compare_exists = False
                                        compare_to_exists = False
                                        # makes sure the detected conflicts are already listed
                                        for tree_item in self.get_children():
                                            tree_item_check = self.item(
                                                tree_item, option="values"
                                            )
                                            if (
                                                tree_item_check[0]
                                                == str(tilecode.split(" ")[0])
                                                and tree_item_check[1]
                                                == str(tilecode.split(" ")[1])
                                                and tree_item_check[2]
                                                == str(lvl_tilecodes[0])
                                            ):
                                                compare_exists = True
                                            elif (
                                                tree_item_check[0]
                                                == str(
                                                    tilecode_compare_to.split(" ")[0]
                                                )
                                                and tree_item_check[1]
                                                == str(
                                                    tilecode_compare_to.split(" ")[1]
                                                )
                                                and tree_item_check[2]
                                                == str(lvl_tilecodes_compare[0])
                                            ):
                                                compare_to_exists = True
                                        if not compare_exists:
                                            self.insert(
                                                "",
                                                "end",
                                                text="L1",
                                                values=(
                                                    str(tilecode.split(" ")[0]),
                                                    str(tilecode.split(" ")[1]),
                                                    str(lvl_tilecodes[0]),
                                                ),
                                            )
                                        if not compare_to_exists:
                                            self.insert(
                                                "",
                                                "end",
                                                text="L1",
                                                values=(
                                                    str(
                                                        tilecode_compare_to.split(" ")[
                                                            0
                                                        ]
                                                    ),
                                                    str(
                                                        tilecode_compare_to.split(" ")[
                                                            1
                                                        ]
                                                    ),
                                                    str(lvl_tilecodes_compare[0]),
                                                ),
                                            )

    def clear(self):
        for i in self.get_children():
            self.delete(i)

    def update_lvls_path(self, new_path):
        self.lvls_path = new_path
