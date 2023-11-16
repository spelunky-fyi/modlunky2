import logging
from pathlib import Path
from PIL import ImageTk
import re
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkMessageBox

from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.levels import LevelFile
from modlunky2.levels.tile_codes import VALID_TILE_CODES, ShortCode
from modlunky2.ui.levels.custom_levels.options_panel import OptionsPanel
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.custom_levels.save_level import save_level
from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.ui.levels.shared.biomes import BIOME
from modlunky2.ui.levels.shared.files_tree import FilesTree, PACK_LIST_TYPE, LEVEL_TYPE
from modlunky2.ui.levels.shared.multi_canvas_container import MultiCanvasContainer
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import Setroom

logger = logging.getLogger(__name__)

class CustomLevelEditor(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config,
        texture_fetcher,
        packs_path,
        extracts_path,
        textures_dir,
        standalone,
        on_go_back,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)

        self.modlunky_config = modlunky_config
        self.texture_fetcher = texture_fetcher
        self.packs_path = packs_path
        self.extracts_path = extracts_path
        self.lvls_path = None
        self.tile_codes = None

        self.zoom_level = 30
        self.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.rowconfigure(0, weight=1)

        # Set the format that will be used for saving new level files.
        if not self.modlunky_config.custom_level_editor_default_save_format:
            self.modlunky_config.custom_level_editor_default_save_format = (
                SaveFormats.base_save_formats()[0]
            )
        self.current_save_format = None

        self.files_tree = FilesTree(
            self,
            modlunky_config,
            packs_path,
            extracts_path,
            PACK_LIST_TYPE.CUSTOM_LEVELS,
            lambda: self.save_needed,
            self.reset_save_button,
            self.update_lvls_path,
            self.on_select_file,
        )
        self.files_tree.grid(row=0, column=0, rowspan=1, sticky="news")
        self.files_tree.load_packs()

        # Button below the file list to exit the editor.
        self.back_button = tk.Button(
            self, text="Exit Editor", bg="black", fg="white", command=on_go_back
        )
        if not standalone:
            self.back_button.grid(row=1, column=0, sticky="news")

        # Button below the file list to save changes to the current file.
        self.save_button = tk.Button(
            self, text="Save", bg="Blue", fg="white", command=self.save_changes
        )
        self.save_button.grid(row=2, column=0, sticky="news")
        self.save_button["state"] = tk.DISABLED

        # View that contains the canvases to edit the level along with some controls.
        editor_view = tk.Frame(self)
        editor_view.grid(row=0, column=1, rowspan=3, sticky="news")
        self.editor_container = editor_view

        editor_view.columnconfigure(0, weight=1)
        editor_view.columnconfigure(2, minsize=0)
        editor_view.columnconfigure(1, minsize=50)
        editor_view.rowconfigure(1, weight=1)

        self.canvas = MultiCanvasContainer(
            editor_view,
            textures_dir,
            ["Foreground", "Background"],
            self.zoom_level,
            lambda index, row, column, is_primary: self.canvas_click(
                index,
                row,
                column,
                is_primary,
            ),
            lambda index, row, column, is_primary: self.canvas_shiftclick(
                index,
                row,
                column,
                is_primary,
            ),
            "Select a level file to begin editing",
        )
        self.canvas.grid(row=0, column=0, columnspan=3, rowspan=2, sticky="news")

        # Side panel with the tile palette and level settings.
        side_panel = tk.Frame(self)
        side_panel.grid(column=2, row=0, rowspan=3, sticky="news")
        side_panel.rowconfigure(0, weight=1)
        side_panel.columnconfigure(0, weight=1)

        # Allow hiding the side panel so more level can be seen.
        side_panel_hidden = False
        side_panel_hide_button = tk.Button(editor_view, text=">>")

        def toggle_panel_hidden():
            nonlocal side_panel_hidden
            side_panel_hidden = not side_panel_hidden
            if side_panel_hidden:
                side_panel.grid_remove()
                side_panel_hide_button.configure(text="<<")
            else:
                side_panel.grid()
                side_panel_hide_button.configure(text=">>")

        side_panel_hide_button.configure(
            command=toggle_panel_hidden,
        )
        side_panel_hide_button.grid(column=1, row=0, sticky="nwe")

        side_panel_tab_control = ttk.Notebook(side_panel)
        side_panel_tab_control.grid(row=0, column=0, sticky="nswe")

        self.palette_panel = PalettePanel(
            side_panel_tab_control,
            self.delete_tilecode,
            self.add_tilecode,
            self.texture_fetcher,
            self.texture_fetcher.sprite_fetcher,
        )
        self.options_panel = OptionsPanel(
            side_panel_tab_control,
            modlunky_config,
            self.zoom_level,
            self.select_theme,
            self.update_level_size,
            self.set_current_save_format,
            self.canvas.hide_grid_lines,
            self.canvas.hide_room_lines,
            self.update_zoom,
        )
        side_panel_tab_control.add(self.palette_panel, text="Tiles")
        side_panel_tab_control.add(self.options_panel, text="Settings")

    def reset_save_button(self):
        self.save_needed = False
        self.save_button["state"] = tk.DISABLED

    def changes_made(self):
        self.save_needed = True
        self.button_save["state"] = tk.NORMAL

    def save_changes(self):
        if not self.save_needed:
            logger.debug("No changes to save.")
            return
        old_level_file = self.current_level

        loaded_pack = self.files_tree.get_loaded_pack()
        backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
        if save_level(
            self.lvls_path,
            self.current_level_path,
            backup_dir,
            self.lvl_width,
            self.lvl_height,
            self.lvl_biome,
            self.current_save_format,
            old_level_file.comment,
            old_level_file.level_chances,
            old_level_file.level_settings,
            old_level_file.monster_chances,
            self.tile_palette_ref_in_use,
            self.tile_codes[0],
            self.tile_codes[1],
        ):
            self.reset_save_button()
            logger.debug("Saved")
            self.files_tree.update_selected_file_icon(LEVEL_TYPE.MODDED)
        else:
            _msg_box = tk.messagebox.showerror(
                "Oops?",
                "Error saving..",
            )

    # def on_select_file(self, lvl):
    #     self.reset()
    #     self.read_lvl_file(lvl)

    def read_lvl_file(self, lvl, theme=None):
        if Path(self.lvls_path / lvl).exists():
            logger.debug("Found this lvl in pack; loading it")
            lvl_path = Path(self.lvls_path) / lvl
        else:
            logger.debug(
                "Did not find this lvl in pack; loading it from extracts instead"
            )
            if self.files_tree.selected_file_is_arena():
                lvl_path = self.extracts_path / "Arena" / lvl
            else:
                lvl_path = self.extracts_path / lvl
        level = LevelFile.from_path(lvl_path)

        # Try to detect what save format the file uses by attempting to read the room
        # at (0, 0) which should always exist in a valid lvl file.
        save_format = self.read_save_format(level)
        if not save_format:
            # If the room couldn't be found, pop up a dialog asking the user to create
            # a new save format to load the file with. If a new format is created,
            # we can then attempt to load the file again.
            self.show_format_error_dialog(lvl, level)
            return

        # Refresh the list of usable tile codes to contain all of the tile codes
        # that are supported by the level editor.
        self.usable_codes = ShortCode.usable_codes()

        self.lvl = lvl
        self.current_level = level
        self.current_level_path = Path(self.lvls_path) / lvl
        self.hide_intro()

        self.set_current_save_format(save_format)

        # Attempt to read the theme from the level file. The theme will be saved in
        # a comment in each room.
        theme = self.read_theme(level, self.current_save_format)
        # if not theme and self.tree_files_custom.heading("#0")["text"].endswith("Arena"):
        if not theme and self.files_tree.selected_file_is_arena():
            themes = [
                BIOME.DWELLING,
                BIOME.JUNGLE,
                BIOME.VOLCANA,
                BIOME.TIDE_POOL,
                BIOME.TEMPLE,
                BIOME.ICE_CAVES,
                BIOME.NEO_BABYLON,
                BIOME.SUNKEN_CITY,
            ]
            for x, themeselect in enumerate(themes):
                if lvl.startswith("dm" + str(x + 1)):
                    theme = themeselect
        self.lvl_biome = theme or BIOME.DWELLING

        self.options_panel.update_theme(theme)
        self.options_panel.enable_controls()

        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        hard_floor_code = None
        # Populate the tile palette from the tile codes listed in the level file.
        for tilecode in level.tile_codes.all():
            tilecode_item = []
            tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

            img = self.texture_fetcher.get_texture(
                tilecode.name, theme, lvl, self.zoom_level
            )
            img_select = self.texture_fetcher.get_texture(
                tilecode.name, theme, lvl, 40
            )

            tilecode_item.append(ImageTk.PhotoImage(img))
            tilecode_item.append(ImageTk.PhotoImage(img_select))

            if tilecode.value in self.usable_codes:
                self.usable_codes.remove(tilecode.value)
            self.tile_palette_ref_in_use.append(tilecode_item)
            self.tile_palette_map[tilecode.value] = tilecode_item
            if str(tilecode.name) == "floor_hard":
                # Keep track of the tile code used for hard floors since this will be
                # used to populate the back layer tiles for rooms that are not dual.
                hard_floor_code = tilecode.value

        # If a tile for hard floor was not found, create one since it is needed for the
        # empty back layer rooms.
        if hard_floor_code is None:
            # The preferred tile code for hard floor is X, so use that if it is available.
            # Otherwise, just use the first available code.
            if self.usable_codes.count("X") > 0:
                hard_floor_code = "X"
            else:
                hard_floor_code = self.usable_codes[0]
            self.usable_codes.remove(hard_floor_code)
            tilecode_item = [
                "floor_hard " + str(hard_floor_code),
                ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        "floor_hard", theme, lvl, self.zoom_level
                    )
                ),
                ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        "floor_hard", theme, lvl, 40
                    )
                ),
            ]
            self.tile_palette_ref_in_use.append(tilecode_item)
            self.tile_palette_map[hard_floor_code] = tilecode_item

        secondary_backup_index = 0

        # Populate the default tile code for left clicks.
        if "1" in self.tile_palette_map:
            # If there is a "1" tile code, guess it is a good default tile since it is often the floor.
            tile = self.tile_palette_map["1"]
            self.palette_panel.select_tile(tile[0], tile[2], True)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there is no "1" tile, just populate with the first tile.
            tile = self.tile_palette_ref_in_use[0]
            self.palette_panel.select_tile(tile[0], tile[2], True)
            secondary_backup_index = 1

        # Populate the default tile code for right clicks.
        if "0" in self.tile_palette_map:
            # If there is a "0" tile code, guess it is a good default secondary tile since it is often the empty tile.
            tile = self.tile_palette_map["0"]
            self.palette_panel.select_tile(tile[0], tile[2], False)
        elif len(self.tile_palette_ref_in_use) > secondary_backup_index:
            # If there is not a "0" tile code, populate with the second tile code if the
            # primary tile code was populated from the first one.
            tile = self.tile_palette_ref_in_use[secondary_backup_index]
            self.palette_panel.select_tile(tile[0], tile[2], False)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there are only one tile code available, populate both right and
            # left click with it.
            tile = self.tile_palette_ref_in_use[0]
            self.palette_panel.select_tile(tile[0], tile[2], False)

        # Populate the list of suggested tiles based on the current theme.
        self.tile_palette_suggestions = suggested_tiles_for_theme(theme)
        # Load images and create buttons for all of the tile codes and suggestions that
        # we populated.
        self.populate_tilecode_palette()

        # Creates a matrix of empty elements that rooms from the level file will load into.
        rooms = [[None for _ in range(8)] for _ in range(15)]

        for template in level.level_templates.all():
            match = Setroom.match_setroom(self.current_save_format.room_template_format, template.name)
            if match is not None:
                # Fill in the room list at the coordinate of this room with the loaded template data.
                rooms[match.y][match.x] = template

        # Filtered room matrix which will be populated with the rooms that were not empty.
        # Essentially, we are going to be removing all of the 'None' from the rooms matrix
        # which weren't replaced with an actual room.
        filtered_rooms = []
        for row in rooms:
            # Filter out all of the None from each row in the matrix.
            newrow = list(filter(lambda room: room is not None, row))
            if len(newrow) > 0:
                filtered_rooms.append(newrow)
            else:
                # If the row was empty, do not include it at all and also break out
                # of the loop to not include any future rows.
                break

        height = len(filtered_rooms)
        width = len(filtered_rooms[0])
        self.lvl_width = width
        self.lvl_height = height

        self.options_panel.update_level_size(width, height)

        foreground_tiles = ["" for _ in range(height * 8)]
        background_tiles = ["" for _ in range(height * 8)]

        # Takes the matrix of rooms and creates an array of strings out of it, where each
        # element in the array is a full row of tiles across the entire level, combining
        # all rooms in the row.
        for i, row in enumerate(filtered_rooms):
            for template in row:
                room = template.chunks[0]
                for line_index, line in enumerate(room.foreground):
                    index = i * 8 + line_index
                    foreground_tiles[index] = foreground_tiles[index] + "".join(line)
                    if (
                        room.background is not None
                        and len(room.background) > line_index
                    ):
                        background_tiles[index] = background_tiles[index] + "".join(
                            room.background[line_index]
                        )
                    else:
                        # If there is no back layer for this room, populate the back layer tile codes
                        # with hard floor tile codes.
                        background_tiles[index] = (
                            background_tiles[index] + hard_floor_code * 10
                        )

        # Map each long string that contains the entire row of tile codes into an
        # array where each element of the array is a single tile code.
        def map_rooms(layer):
            return list(
                map(lambda room_row: list(map(lambda tile: tile, str(room_row))), layer)
            )

        self.tile_codes = [
            map_rooms(foreground_tiles),
            map_rooms(background_tiles),
        ]

        # Fetch the images for each tile and draw them in the canvases.
        self.draw_canvas()
        
    def populate_tilecode_palette(self):
        self.palette_panel.update_with_palette(
            self.tile_palette_ref_in_use,
            self.tile_palette_suggestions,
            self.lvl_biome,
            self.lvl,
        )

    # Read the comment of the template at room (0, 0) to extract the theme, defaulting to dwelling.
    def read_theme(self, level, save_format):
        for template in level.level_templates.all():
            if template.name == save_format.room_template_format.format(y=0, x=0):
                return template.comment
        return None
    
    # Look through the level templates and try to find one that matches an existing save
    # format.
    def read_save_format(self, level):
        if self.modlunky_config.custom_level_editor_default_save_format is None:
            raise TypeError("custom_level_editor_default_save_format shouldn't be None")

        valid_save_formats = (
            [self.modlunky_config.custom_level_editor_default_save_format]
            + self.modlunky_config.custom_level_editor_custom_save_formats
            + SaveFormats.base_save_formats()
        )
        for save_format in valid_save_formats:
            for template in level.level_templates.all():
                if template.name == save_format.room_template_format.format(y=0, x=0):
                    return save_format

    # Shows an error dialog when attempting to open a level using an unrecognized template format.
    def show_format_error_dialog(self, lvl, level_info):
        def on_create(save_format):
            self.options_panel.add_save_format(save_format)

            # When a new format is created, try reading the level file again.
            self.read_lvl_file(lvl)

        SaveFormats.show_setroom_create_dialog(
            self.modlunky_config,
            "Couldn't find room templates",
            "Create a new room template format to load this level file?\n{x} and {y} are the coordinates of the room.\n",
            "Continue",
            on_create,
            self.get_suggested_saveroom_format(level_info),
        )

    def get_suggested_saveroom_format(self, level_info):
        template_regex = (
            "^"
            + r"(?P<begin>[^0-9]*)" + r"(?P<y>\d+)" + r"(?P<mid>[^0-9]*)" + r"(?P<x>\d+)" + r"(?P<end>[^0-9]*)"
            + "$"
        )
        logger.info(template_regex)
        for template in level_info.level_templates.all():
            match = re.search(template_regex, template.name)
            logger.info(template.name)
            if match is not None:
                logger.info("MATCHED")
                begin = match.group("begin")
                mid = match.group("mid")
                ending = match.group("end")
                return begin + "{y}" + mid + "{x}" + ending

    def draw_canvas(self):
        width = self.lvl_width
        height = self.lvl_height
        theme = self.lvl_biome

        # Clear all existing images from the canvas before drawing the new images.
        self.canvas.clear()
        self.canvas.configure_size(width, height)

        # Draw lines to fill the size of the level.
        self.canvas.draw_background(theme)
        self.canvas.draw_grid()
        self.canvas.draw_room_grid()

        # Draws all of the images of a layer on its canvas, and stores the images in
        # the proper index of tile_images so they can be removed from the grid when
        # replaced with another tile.
        def draw_layer(canvas_index, tile_codes):
            for row_index, room_row in enumerate(tile_codes):
                if row_index >= self.lvl_height * 8:
                    continue
                for tile_index, tile in enumerate(room_row):
                    if tile_index >= self.lvl_width * 10:
                        continue
                    tilecode = self.tile_palette_map[tile]
                    tile_name = tilecode[0].split(" ", 1)[0]
                    tile_image = tilecode[1]
                    x_offset, y_offset = self.texture_fetcher.adjust_texture_xy(
                        tile_image.width(),
                        tile_image.height(),
                        tile_name,
                        self.zoom_level,
                    )
                    self.canvas.replace_tile_at(
                        canvas_index,
                        row_index,
                        tile_index,
                        tile_image,
                        x_offset,
                        y_offset,
                    )

        for index, tileset in enumerate(self.tile_codes):
            draw_layer(index, tileset)

    # Click event on a canvas for either left or right click to replace the tile at the cursor's position with
    # the selected tile.
    def canvas_click(
        self,
        canvas_index,
        row,
        column,
        is_primary,
    ):

        tile_name, tile_code = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, self.zoom_level)

        self.canvas.replace_tile_at(canvas_index, row, column, self.tile_palette_map[tile_code][1], x_offset, y_offset)
        self.tile_codes[row][column] = tile_code
        self.changes_made()

    def canvas_shiftclick(self, index, row, column, is_primary):
        tile_code = self.tile_codes[index][row][column]
        tile = self.tile_palette_map[tile_code]

        self.palette_panel.select_tile(tile[0], tile[2], is_primary)

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile_name, tile_code, tile_size):
        logger.debug("Applying custom anchor for %s", tile_name)
        tile_ref = self.tile_palette_map[tile_code]
        if tile_ref:
            logger.debug("Found %s", tile_ref[0])
            img = tile_ref[1]
            return self.texture_fetcher.adjust_texture_xy(
                img.width(), img.height(), tile_name, tile_size
            )

        return 0, 0

    def add_tilecode(
        self,
        tile,
        percent,
        alt_tile,
    ):
        usable_code = None

        invalid_tilecodes = []
        if tile not in VALID_TILE_CODES:
            invalid_tilecodes.append(tile)

        if alt_tile not in VALID_TILE_CODES:
            invalid_tilecodes.append(alt_tile)

        i = 0
        for invalid_tile in invalid_tilecodes:
            lua_tile = tkMessageBox.askquestion(
                "Uh Oh!",
                str(invalid_tile) + " isn't a valid tile id. Add as a custom lua tile?",
            )
            if lua_tile != "yes":
                return
            i = i + 1

        new_tile_code = tile
        if int(percent) < 100:
            new_tile_code += "%" + percent
            # Have to use a temporary directory due to TCL/Tkinter is trying to write
            # to a file name, not a file handle, and windows doesn't support sharing the
            # file between processes
            if alt_tile != "empty":
                new_tile_code += "%" + alt_tile

        tile_image = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(new_tile_code, self.lvl_biome, self.lvl, self.zoom_level)
        )
        tile_image_picker = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(new_tile_code, self.lvl_biome, self.lvl, 40)
        )

        # compares tile id to tile ids in palette list
        for palette_tile in self.tile_palette_ref_in_use:
            palette_tile = palette_tile[0].split()[0].strip()
            if new_tile_code == palette_tile:
                tkMessageBox.showinfo("Uh Oh!", "You already have that!")
                return

        if len(self.usable_codes) > 0:
            usable_code = self.usable_codes[0]
            for code in self.usable_codes:
                if code == usable_code:
                    self.usable_codes.remove(code)
        else:
            tkMessageBox.showinfo(
                "Uh Oh!", "You've reached the tilecode limit; delete some to add more"
            )
            return

        ref_tile = []
        ref_tile.append(new_tile_code + " " + str(usable_code))
        ref_tile.append(tile_image)
        ref_tile.append(tile_image_picker)
        self.tile_palette_ref_in_use.append(ref_tile)
        self.tile_palette_map[usable_code] = ref_tile

        self.populate_tilecode_palette()
        self.log_codes_left()
        self.changes_made()
        return ref_tile

    def delete_tilecode(self, tile_name, tile_code):
        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air.",
            icon="warning",
        )
        if msg_box == "yes":
            if tile_name == r"empty":
                tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
                return

            new_tile = self.tile_palette_map["0"]
            for matrix_index, tile_code_matrix in enumerate(self.tile_codes):
                for row in range(len(tile_code_matrix)):
                    for column in range(len(tile_code_matrix[row])):
                        if str(tile_code_matrix[row][column]) == str(tile_code):
                            self.canvas.replace_tile_at(matrix_index, row, column, new_tile[1])
                            tile_code_matrix[row][column] = "0"
            self.usable_codes.append(str(tile_code))
            logger.debug("%s is now available for use.", tile_code)

            # Adds tilecode back to list to be reused.
            for id_ in self.tile_palette_ref_in_use:
                if str(tile_code) == str(id_[0].split(" ", 2)[1]):
                    self.tile_palette_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile_name)

            self.populate_tilecode_palette()

            self.log_codes_left()
            self.changes_made()

    def log_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        logger.debug("%s codes left (%s)", len(self.usable_codes), codes)

    # Selects a new theme, updating the grid to theme tiles and backgrounds for the
    # new theme.
    def select_theme(self, theme):
        if theme == self.lvl_biome:
            return
        self.lvl_biome = theme

        # Retexture all of the tiles in use
        for tilecode_item in self.tile_palette_ref_in_use:
            tile_name = tilecode_item[0].split(" ", 2)[0]
            img = self.texture_fetcher.get_texture(
                tile_name, theme, self.lvl, self.zoom_level
            )
            tilecode_item[1] = ImageTk.PhotoImage(img)

        # Load suggested tiles for the new theme.
        self.tile_palette_suggestions = suggested_tiles_for_theme(theme)
        # Redraw the tilecode palette with the new textures of tiles and the new suggestions.
        self.populate_tilecode_palette()
        # Draw the grid now that we have the newly textured tiles.
        self.draw_canvas()

        self.changes_made()

    # Updates the level size from the options menu.
    def update_level_size(self, width, height):
        if width == self.lvl_width and height == self.lvl_height:
            return

        # If the new level size is greater than the current level size, fill in
        # the level tile matrix with default tiles to fill the new size.
        def fill_to_size_with_tile(tile_matrix, tile, width, height):
            fill_rows = list(
                map(
                    lambda row: row
                    + (
                        []
                        if (width * 10 <= len(row))
                        else [tile for _ in range(width * 10 - len(row))]
                    ),
                    tile_matrix,
                )
            )
            return fill_rows + (
                []
                if (height * 8 <= len(fill_rows))
                else [
                    [tile for _ in range(width * 10)]
                    for _ in range(height * 8 - len(fill_rows))
                ]
            )

        empty = None
        hard_floor = None
        # Try to find a tile code for the empty tile and the hard floor to use as the
        # default tile codes of the front and back layers, respectively.
        for tile_ref in self.tile_palette_ref_in_use:
            tile_name = str(tile_ref[0].split(" ", 2)[0])
            tile_code = str(tile_ref[0].split(" ", 2)[1])
            if tile_name == "empty":
                empty = tile_code
            elif tile_name == "floor_hard":
                hard_floor = tile_code

        # If we didn't find an "empty" tile code, create one and use it.
        if not empty:
            empty = self.add_tilecode(
                "empty",
                "100",
                "empty",
            )[0].split(" ", 2)[1]
        # If we did not find a "hard_floor" tile code, create one and use it.
        if not hard_floor:
            hard_floor = self.add_tilecode(
                "hard_floor",
                "100",
                "empty",
            )[0].split(" ", 2)[1]

        self.tile_codes = [
            fill_to_size_with_tile(
                self.self.tile_codes[0], empty, width, height
            ),
            fill_to_size_with_tile(
                self.self.tile_codes[1], hard_floor, width, height
            ),
        ]

        self.lvl_width = width
        self.lvl_height = height
        self.changes_made()
        self.draw_canvas()

    def update_zoom(self, zoom):
        self.zoom_level = zoom
        if self.lvl:
            for tile in self.tile_palette_ref_in_use:
                tile_name = tile[0].split(" ", 2)[0]
                tile[1] = ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        tile_name,
                        self.lvl_biome,
                        self.lvl,
                        self.zoom_level,
                    )
                )
            self.canvas.set_zoom(zoom)
            self.draw_canvas()

    def set_current_save_format(self, save_format):
        self.current_save_format = save_format
        self.files_tree.current_save_format = save_format

    def update_lvls_path(self, new_path):
        self.reset()
        self.lvls_path = new_path

    def show_intro(self):
        self.canvas.show_intro()
        self.editor_container.columnconfigure(2, minsize=0)

    def hide_intro(self):
        self.canvas.hide_intro()
        self.editor_container.columnconfigure(2, minsize=17)

    def load_packs(self):
        self.reset()
        self.files_tree.load_packs()

    def reset(self):
        logger.debug("Resetting...")
        try:
            self.palette_panel.reset()
            self.options_panel.disable_controls()
            self.show_intro()
            self.canvas.clear()
            self.tile_palette_map = {}
            self.tile_palette_ref_in_use = None
            self.tile_palette_suggestions = None
            self.lvl = None
            self.lvl_biome = None
            self.tile_codes = None
            self.reset_save_button()
        except Exception:  # pylint: disable=broad-except
            logger.debug("canvas does not exist yet")