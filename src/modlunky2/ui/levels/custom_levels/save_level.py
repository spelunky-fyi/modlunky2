import logging
import os
import os.path
from pathlib import Path
from modlunky2.utils import tb_info

from modlunky2.levels import LevelFile
from modlunky2.levels.level_settings import LevelSetting
from modlunky2.levels.level_templates import (
    Chunk,
    LevelTemplate,
    LevelTemplates,
    TemplateSetting,
)
from modlunky2.levels.tile_codes import TileCode, TileCodes
from modlunky2.ui.levels.shared.make_backup import make_backup
from modlunky2.ui.levels.shared.setrooms import VANILLA_SETROOM_TYPE

logger = logging.getLogger(__name__)

def vanilla_setroom_type_for(theme, x, y):
    if theme == "ice":
        if y in [4, 5, 6, 7] and x in [0, 1, 2]:
            return VANILLA_SETROOM_TYPE.DUAL
        elif y in [10, 11, 12, 13] and x in [0, 1, 2]:
            return VANILLA_SETROOM_TYPE.BACK
    elif theme == "tiamat":
        if y == 0 and x in [0, 1, 2]:
            return VANILLA_SETROOM_TYPE.DUAL
        elif y in range(2, 10 + 1) and x in [0, 1, 2]:
            return VANILLA_SETROOM_TYPE.FRONT
    elif theme == "duat":
        if y in [0, 1, 2, 3] and x in [0, 1, 2]:
            return VANILLA_SETROOM_TYPE.FRONT
    elif theme == "eggplant":
        if y in [0, 1] and x in [0, 1, 2, 3]:
            return VANILLA_SETROOM_TYPE.FRONT
    elif theme == "olmec":
        if (y in [0, 1, 6, 7] and x in [0, 1, 2, 3, 4]) or (
            y in [2, 3, 4, 5] and x in [1, 2, 3]
        ):
            return VANILLA_SETROOM_TYPE.DUAL
        elif (y in [2, 3, 4, 5] and x in [0, 4]) or (
            y == 7 and x in [0, 1, 2, 3, 4]
        ):
            return VANILLA_SETROOM_TYPE.FRONT
    elif theme == "hundun":
        if y in [0, 1, 2, 10, 11] and x in [0, 1, 2]:
            return VANILLA_SETROOM_TYPE.FRONT
    elif theme == "abzu":
        if y in [0, 1, 2, 3] and x in [0, 1, 2, 3]:
            return VANILLA_SETROOM_TYPE.DUAL
        elif y in [4, 5, 6, 7, 8] and x in [0, 1, 2, 3]:
            return VANILLA_SETROOM_TYPE.FRONT

    return VANILLA_SETROOM_TYPE.NONE

def save_level(
        lvls_path,
        level_path,
        backup_dir,
        width,
        height,
        theme,
        save_format,
        comment,
        level_chances,
        level_settings,
        monster_chances,
        used_tiles,
        foreground_tiles,
        background_tiles,
):
        try:
            tile_codes = TileCodes()
            level_templates = LevelTemplates()

            hard_floor_code = None
            air_code = "0"
            for tilecode in used_tiles:
                tile_codes.set_obj(
                    TileCode(
                        name=tilecode[0].split(" ", 1)[0],
                        value=tilecode[0].split(" ", 1)[1],
                        comment="",
                    )
                )
                if tilecode[0].split(" ", 1)[0] == "floor_hard":
                    hard_floor_code = tilecode[0].split(" ", 1)[1]
                elif tilecode[0].split(" ", 1)[0] == "empty":
                    air_code = tilecode[0].split(" ", 1)[1]

            def write_vanilla_room(
                x,
                y,
                foreground,
                background,
                save_format,
                level_templates,
                hard_floor_code,
            ):
                if not save_format.include_vanilla_setrooms:
                    return
                vanilla_setroom_type = vanilla_setroom_type_for(theme, x, y)
                if vanilla_setroom_type == VANILLA_SETROOM_TYPE.NONE:
                    return
                vf = []
                vb = []
                vs = []
                vm = ""
                dual = (not hard_floor_code) or background != [
                    hard_floor_code * 10 for _ in range(8)
                ]
                if vanilla_setroom_type == VANILLA_SETROOM_TYPE.FRONT:
                    vf = foreground
                    vm = "the front layer"
                elif vanilla_setroom_type == VANILLA_SETROOM_TYPE.BACK:
                    vf = background
                    vm = "the back layer"
                elif vanilla_setroom_type == VANILLA_SETROOM_TYPE.DUAL:
                    vf = foreground
                    vm = "both layers"
                    if dual:
                        vb = background
                        vs.append(TemplateSetting.DUAL)

                template_chunks = [
                    Chunk(
                        comment=None,
                        settings=vs,
                        foreground=vf,
                        background=vb,
                    )
                ]
                template_name = save_format.room_template_format.format(y=y, x=x)
                comment = f"Auto-generated template to match {vm} of {template_name}."
                level_templates.set_obj(
                    LevelTemplate(
                        name=f"setroom{room_y}-{room_x}",
                        comment=comment,
                        chunks=template_chunks,
                    )
                )

            for room_y in range(height):
                for room_x in range(width):
                    room_foreground = []
                    room_background = []
                    for row in range(8):
                        foreground_row = foreground_tiles[room_y * 8 + row]
                        background_row = background_tiles[room_y * 8 + row]
                        room_foreground.append(
                            "".join(foreground_row[room_x * 10 : room_x * 10 + 10])
                        )
                        room_background.append(
                            "".join(background_row[room_x * 10 : room_x * 10 + 10])
                        )

                    room_settings = []
                    dual = (not hard_floor_code) or room_background != [
                        hard_floor_code * 10 for _ in range(8)
                    ]
                    if dual:
                        room_settings.append(TemplateSetting.DUAL)
                    template_chunks = [
                        Chunk(
                            comment=None,
                            settings=room_settings,
                            foreground=room_foreground,
                            background=room_background if dual else [],
                        )
                    ]
                    template_name = save_format.room_template_format.format(
                        y=room_y, x=room_x
                    )
                    level_templates.set_obj(
                        LevelTemplate(
                            name=template_name,
                            comment=theme,
                            chunks=template_chunks,
                        )
                    )
                    write_vanilla_room(
                        room_x,
                        room_y,
                        room_foreground,
                        room_background,
                        save_format,
                        level_templates,
                        hard_floor_code,
                    )

            # Write vanilla setrooms for any room that the game expects a setroom for, but does not
            # exist in the current size of the level.
            for room_y in range(15):
                for room_x in range(8):
                    # If the room has already been handled, just continue to the next room.
                    if room_y < height and room_x < width:
                        continue
                    room_foreground = [air_code * 10] * 8
                    room_background = [(hard_floor_code or "X") * 10] * 8
                    write_vanilla_room(
                        room_x,
                        room_y,
                        room_foreground,
                        room_background,
                        save_format,
                        level_templates,
                        hard_floor_code,
                    )

            level_settings.set_obj(
                LevelSetting(
                    name="size",
                    value="{width} {height}".format(width=width, height=height),
                    comment=None,
                )
            )
            level_file = LevelFile(
                comment,
                level_settings,
                tile_codes,
                level_chances,
                monster_chances,
                level_templates,
            )

            if not os.path.exists(Path(lvls_path)):
                os.makedirs(Path(lvls_path))
            save_path = level_path
            make_backup(save_path, backup_dir)
            logger.debug("Saving to %s", save_path)

            with Path(save_path).open("w", encoding="cp1252") as handle:
                level_file.write(handle)

            logger.debug("Saved!")
            return True
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed to save level: %s", tb_info())

            return False
