import logging
import os
import os.path
from pathlib import Path
import glob
from PIL import Image, ImageTk
import re
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkMessageBox

from modlunky2.constants import BASE_DIR
from modlunky2.mem.state import Theme
from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.levels import LevelFile
from modlunky2.levels.tile_codes import VALID_TILE_CODES, ShortCode
from modlunky2.ui.levels.custom_levels.options_panel import OptionsPanel
from modlunky2.ui.levels.custom_levels.save_formats import SaveFormats
from modlunky2.ui.levels.custom_levels.save_level import save_level
from modlunky2.ui.levels.custom_levels.level_configurations.level_configuration import (
    LevelConfiguration,
)
from modlunky2.ui.levels.custom_levels.level_configurations.level_configurations import (
    LevelConfigurations,
)
from modlunky2.ui.levels.custom_levels.level_configurations.level_configuration_panel import (
    LevelConfigurationPanel,
)
from modlunky2.ui.levels.custom_levels.sequence_panel import SequencePanel
from modlunky2.ui.levels.custom_levels.tile_sets import suggested_tiles_for_theme
from modlunky2.ui.levels.shared.biomes import Biomes
from modlunky2.ui.levels.shared.files_tree import FilesTree, PACK_LIST_TYPE, LEVEL_TYPE
from modlunky2.ui.levels.shared.level_canvas import CANVAS_MODE
from modlunky2.ui.levels.shared.tile import Tile
from modlunky2.ui.levels.shared.multi_canvas_container import (
    MultiCanvasContainer,
    CanvasIndex,
)
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import Setroom
from modlunky2.ui.levels.shared.tool_select import ToolSelect

logger = logging.getLogger(__name__)


class LAYER:
    FRONT = 0
    BACK = 1


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
        self.loaded_pack_path = None

        self.tile_codes = None
        self.usable_codes = ShortCode.usable_codes()
        self.lvl = None
        self.lvl_theme = None
        self.lvl_name = None
        self.lvl_subtheme = None
        self.lvl_border_theme = None
        self.lvl_loop = None
        self.lvl_border_entity_theme = None
        self.lvl_background_theme = None
        self.lvl_background_subtheme = None
        self.lvl_floor_theme = None
        self.lvl_music_theme = None
        self.lvl_skip_co_fixes = None
        self.lvl_spawn_door_jellyfish = None

        self.current_level = None
        self.current_level_path = None
        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        self.tile_palette_suggestions = []
        self.lvl_width = None
        self.lvl_height = None
        self.level_configurations = None
        self.sequence = None
        self.has_sequence = False

        self.zoom_level = 30
        self.tool = CANVAS_MODE.DRAW

        image_path = BASE_DIR / "static/images/help.png"
        self.error_image = ImageTk.PhotoImage(
            Image.open(image_path).resize((self.zoom_level, self.zoom_level))
        )

        self.save_needed = False

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
            self.on_create_file,
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
            [],
            self.zoom_level,
            self.canvas_click,
            self.canvas_shiftclick,
            self.canvas_fill,
            self.canvas_fill_type,
            self.canvas_move,
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

        self.tool_select_bar = ToolSelect(editor_view, self.select_tool)
        self.tool_select_bar.grid(row=1, column=1, sticky="ne", pady=10)

        side_panel_tab_control = ttk.Notebook(side_panel)
        side_panel_tab_control.grid(row=0, column=0, sticky="nswe")

        self.palette_panel = PalettePanel(
            side_panel_tab_control,
            self.delete_tilecode,
            self.add_tilecode,
            None,
            None,
            self.texture_fetcher,
            self.texture_fetcher.sprite_fetcher,
        )
        self.options_panel = OptionsPanel(
            side_panel_tab_control,
            modlunky_config,
            self.zoom_level,
            self.set_current_save_format,
            self.canvas.hide_grid_lines,
            self.canvas.hide_room_lines,
            self.update_zoom,
        )
        self.level_configuration_panel = LevelConfigurationPanel(
            side_panel_tab_control,
            modlunky_config,
            self.update_level_size,
            self.update_level_name,
            self.select_theme,
            self.select_border_theme,
            self.select_border_entity_theme,
            self.select_background_theme,
            self.select_floor_theme,
            self.select_music_theme,
            self.select_skip_co_fixes,
            self.select_spawn_door_jellyfish,
        )
        self.sequence_panel = SequencePanel(
            side_panel_tab_control,
            modlunky_config,
            self.update_level_sequence,
        )
        side_panel_tab_control.add(self.palette_panel, text="Tiles")
        side_panel_tab_control.add(self.options_panel, text="Settings")
        side_panel_tab_control.add(
            self.level_configuration_panel, text="Configure Level"
        )
        side_panel_tab_control.add(self.sequence_panel, text="Level Sequence")

    def reset_save_button(self):
        self.save_needed = False
        self.save_button["state"] = tk.DISABLED

    def changes_made(self):
        self.save_needed = True
        self.save_button["state"] = tk.NORMAL

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
            self.lvl_biome(),
            self.current_save_format,
            old_level_file.comment,
            old_level_file.level_chances,
            old_level_file.level_settings,
            old_level_file.monster_chances,
            self.tile_palette_ref_in_use,
            self.tile_codes[LAYER.FRONT],
            self.tile_codes[LAYER.BACK],
        ):
            self.write_current_level_configuration()
            self.reset_save_button()
            logger.debug("Saved")
            self.files_tree.update_selected_file_icon(LEVEL_TYPE.MODDED)
        else:
            _msg_box = tk.messagebox.showerror(
                "Oops?",
                "Error saving..",
            )

    # Load selected level file.
    def on_select_file(self, lvl):
        self.reset()
        self.read_lvl_file(lvl)

    # A new level was created. Add it to the sequence if the box was ticked, then load the level.
    def on_create_file(self, lvl, add_to_sequence):
        self.reset()
        if add_to_sequence:
            if self.sequence is None:
                sequence = [lvl]
            else:
                sequence = [existing_lvl for existing_lvl in self.sequence]
                sequence.append(lvl)
            self.update_level_sequence(sequence)

            self.sequence_panel.update_pack(
                self.loaded_pack_path,
                self.sequence,
                self.list_custom_level_file_names(),
            )
        self.read_lvl_file(lvl)

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

        # Attempt to read the theme from the level configuration. If it does not exist
        # there, attempt to read it from the level file. The theme will be saved in
        # a comment in each room.
        theme, subtheme = self.find_theme(lvl, level, self.current_save_format)
        configuration = self.configuration_for_level(lvl)

        self.lvl_border_theme = None
        self.lvl_border_entity_theme = None
        self.lvl_loop = None
        self.lvl_name = None
        self.lvl_background_theme = None
        self.lvl_background_subtheme = None
        self.lvl_floor_theme = None
        self.lvl_music_theme = None
        self.lvl_skip_co_fixes = False
        self.lvl_spawn_door_jellyfish = False
        self.level_configuration_panel.disable_controls()

        if configuration:
            self.lvl_border_theme = configuration.border_theme
            self.lvl_border_entity_theme = configuration.border_entity_theme
            if configuration.loop:
                self.lvl_loop = True
            if configuration.dont_loop:
                self.lvl_loop = False
            if configuration.name != Path(configuration.file_name).stem.capitalize():
                self.lvl_name = configuration.name
            self.lvl_background_theme = configuration.background_theme
            self.lvl_background_subtheme = configuration.background_texture_theme
            self.lvl_floor_theme = configuration.floor_theme
            self.lvl_music_theme = configuration.music_theme
            self.lvl_skip_co_fixes = configuration.skip_co_fixes
            self.lvl_spawn_door_jellyfish = configuration.spawn_door_jellyfish
            self.level_configuration_panel.enable_controls()

        # if not theme and self.tree_files_custom.heading("#0")["text"].endswith("Arena"):
        if not theme and self.files_tree.selected_file_is_arena():
            themes = [
                Theme.DWELLING,
                Theme.JUNGLE,
                Theme.VOLCANA,
                Theme.TIDE_POOL,
                Theme.TEMPLE,
                Theme.ICE_CAVES,
                Theme.NEO_BABYLON,
                Theme.SUNKEN_CITY,
            ]
            for x, themeselect in enumerate(themes):
                if lvl.startswith("dm" + str(x + 1)):
                    theme = themeselect

        self.lvl_theme = theme or Theme.DWELLING
        self.lvl_subtheme = subtheme
        biome = Biomes.biome_for_theme(theme, subtheme)
        floor_biome = self.lvl_floor_theme and Biomes.biome_for_theme(
            self.lvl_floor_theme, None
        )
        border_biome = self.lvl_border_entity_theme and Biomes.biome_for_theme(
            self.lvl_border_entity_theme, None
        )

        self.level_configuration_panel.set_sequence_exists(self.has_sequence)
        self.level_configuration_panel.set_level_in_sequence(lvl in self.sequence)
        self.level_configuration_panel.update_level_name(self.lvl_name)
        self.level_configuration_panel.update_theme(theme, subtheme)
        self.level_configuration_panel.update_border_theme(
            self.lvl_border_theme, self.lvl_loop
        )
        self.level_configuration_panel.update_border_entity_theme(
            self.lvl_border_entity_theme
        )
        self.level_configuration_panel.update_background_theme(
            self.lvl_background_theme, self.lvl_background_subtheme
        )
        self.level_configuration_panel.update_floor_theme(self.lvl_floor_theme)
        self.level_configuration_panel.update_music_theme(self.lvl_music_theme)
        self.level_configuration_panel.update_skip_co_fix(self.lvl_skip_co_fixes)
        self.level_configuration_panel.update_spawn_jelly(self.lvl_spawn_door_jellyfish)

        self.options_panel.enable_controls()

        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        hard_floor_code = None
        # Populate the tile palette from the tile codes listed in the level file.
        for tilecode in level.tile_codes.all():
            img = self.texture_fetcher.get_texture(
                tilecode.name, biome, floor_biome, border_biome, lvl, self.zoom_level
            )
            img_select = self.texture_fetcher.get_texture(
                tilecode.name, biome, floor_biome, border_biome, lvl, 40
            )

            tilecode_item = Tile(
                tilecode.name,
                tilecode.value,
                tilecode.comment,
                ImageTk.PhotoImage(img),
                ImageTk.PhotoImage(img_select),
            )
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
            tilecode_item = Tile(
                "floor_hard",
                str(hard_floor_code),
                "",
                ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        "floor_hard",
                        biome,
                        floor_biome,
                        border_biome,
                        lvl,
                        self.zoom_level,
                    )
                ),
                ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        "floor_hard", biome, floor_biome, border_biome, lvl, 40
                    )
                ),
            )
            self.tile_palette_ref_in_use.append(tilecode_item)
            self.tile_palette_map[hard_floor_code] = tilecode_item

        secondary_backup_index = 0

        # Populate the default tile code for left clicks.
        if "1" in self.tile_palette_map:
            # If there is a "1" tile code, guess it is a good default tile since it is often the floor.
            tile = self.tile_palette_map["1"]
            self.palette_panel.select_tile(tile, True)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there is no "1" tile, just populate with the first tile.
            tile = self.tile_palette_ref_in_use[0]
            self.palette_panel.select_tile(tile, True)
            secondary_backup_index = 1

        # Populate the default tile code for right clicks.
        if "0" in self.tile_palette_map:
            # If there is a "0" tile code, guess it is a good default secondary tile since it is often the empty tile.
            tile = self.tile_palette_map["0"]
            self.palette_panel.select_tile(tile, False)
        elif len(self.tile_palette_ref_in_use) > secondary_backup_index:
            # If there is not a "0" tile code, populate with the second tile code if the
            # primary tile code was populated from the first one.
            tile = self.tile_palette_ref_in_use[secondary_backup_index]
            self.palette_panel.select_tile(tile, False)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there are only one tile code available, populate both right and
            # left click with it.
            tile = self.tile_palette_ref_in_use[0]
            self.palette_panel.select_tile(tile, False)

        # Populate the list of suggested tiles based on the current theme.
        self.tile_palette_suggestions = suggested_tiles_for_theme(theme, subtheme)
        # Load images and create buttons for all of the tile codes and suggestions that
        # we populated.
        self.populate_tilecode_palette()

        # Creates a matrix of empty elements that rooms from the level file will load into.
        rooms = [[None for _ in range(8)] for _ in range(15)]

        for template in level.level_templates.all():
            match = Setroom.match_setroom(
                self.current_save_format.room_template_format, template.name
            )
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

        self.level_configuration_panel.update_level_size(width, height)

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
        self.draw_canvas(True)

    def populate_tilecode_palette(self):
        self.palette_panel.update_with_palette(
            self.tile_palette_ref_in_use,
            self.tile_palette_suggestions,
            None,
            self.lvl_biome(),
            self.floor_biome(),
            self.border_biome(),
            self.lvl,
        )

    # Find the theme of a level from the level configurations, or read it from the level file if
    # there is no level configuration for the level.
    def find_theme(self, level_file, level, save_format):
        if level_file in self.level_configurations:
            configuration = self.level_configurations[level_file]
            return configuration.theme, configuration.subtheme
        return self.read_theme(level, save_format), None

    # Read the comment of the template at room (0, 0) to extract the theme, defaulting to dwelling.
    def read_theme(self, level, save_format):
        if self.files_tree.selected_file_is_arena():
            return None

        for template in level.level_templates.all():
            if template.name == save_format.room_template_format.format(y=0, x=0):
                return Biomes.theme_for_biome(template.comment)
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
            + r"(?P<begin>[^0-9]*)"
            + r"(?P<y>\d+)"
            + r"(?P<mid>[^0-9]*)"
            + r"(?P<x>\d+)"
            + r"(?P<end>[^0-9]*)"
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

    def draw_canvas(self, fresh):
        width = self.lvl_width
        height = self.lvl_height

        # Clear all existing images from the canvas before drawing the new images.
        self.canvas.clear()
        self.canvas.configure_size(width * 10, height * 8)

        # Draw lines to fill the size of the level.
        bg_theme = self.lvl_background_theme or self.lvl_theme
        bg_subtheme = self.lvl_background_subtheme or self.lvl_subtheme
        self.canvas.draw_background(bg_theme, bg_subtheme)
        self.canvas.draw_grid()
        self.canvas.draw_room_grid()

        # Draws all of the images of a layer on its canvas, and stores the images in
        # the proper index of tile_images so they can be removed from the grid when
        # replaced with another tile.
        def draw_layer(canvas_index, tile_codes):
            for row_index, room_row in enumerate(tile_codes):
                if row_index >= self.lvl_height * 8:
                    continue
                for tile_index, tilecode in enumerate(room_row):
                    if tile_index >= self.lvl_width * 10:
                        continue
                    tile = self.tile_palette_map.get(tilecode)
                    if tile:
                        tile_image = tile.image
                        x_offset, y_offset = self.texture_fetcher.adjust_texture_xy(
                            tile_image.width(),
                            tile_image.height(),
                            tile.name,
                            self.zoom_level,
                        )
                    else:
                        logger.warning(
                            "Tile code %s found in room, but does not map to a valid tile code.",
                            tilecode,
                        )
                        tile_image = self.error_image
                        x_offset, y_offset = 0, 0
                    self.canvas.replace_tile_at(
                        canvas_index,
                        row_index,
                        tile_index,
                        tile_image,
                        x_offset,
                        y_offset,
                    )

        for index, tileset in enumerate(self.tile_codes):
            draw_layer(CanvasIndex(index, 0), tileset)

        self.canvas.update_scroll_region(fresh)
        self.canvas.set_mode(self.tool)

    # Click event on a canvas for either left or right click to replace the tile at the cursor's position with
    # the selected tile.
    def canvas_click(self, canvas_index, row, column, is_primary):
        tile = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile, self.zoom_level)

        self.canvas.replace_tile_at(
            canvas_index,
            row,
            column,
            self.tile_palette_map[tile.code].image,
            x_offset,
            y_offset,
        )
        self.tile_codes[canvas_index.tab_index][row][column] = tile.code
        self.changes_made()

    def canvas_shiftclick(self, index, row, column, is_primary):
        tile_code = self.tile_codes[index.tab_index][row][column]
        tile = self.tile_palette_map[tile_code]

        self.palette_panel.select_tile(tile, is_primary)

    def canvas_fill(self, canvas_index, tiles, is_primary):
        for tile in tiles:
            self.canvas_click(canvas_index, tile.y, tile.x, is_primary)

    def canvas_fill_type(self, canvas_index, row, column, is_primary):
        tile = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile, self.zoom_level)

        replace_code = self.tile_codes[canvas_index.tab_index][row][column]

        layer = self.tile_codes[canvas_index.tab_index]

        for r, tilerow in enumerate(layer):
            for c, tc in enumerate(tilerow):
                if tc == replace_code:
                    self.canvas.replace_tile_at(
                        canvas_index,
                        r,
                        c,
                        self.tile_palette_map[tile.code].image,
                        x_offset,
                        y_offset,
                    )
                    self.tile_codes[canvas_index.tab_index][r][c] = tile.code
        self.changes_made()

    def canvas_move(self, canvas_index, tiles, dist_x, dist_y):
        replacement_tiles = [
            (tile.x, tile.y, self.tile_codes[canvas_index.tab_index][tile.y][tile.x])
            for tile in tiles
        ]
        empty = None
        for tile_ref in self.tile_palette_ref_in_use:
            if tile_ref.name == "empty":
                empty = tile_ref

        # If we didn't find an "empty" tile code, create one and use it.
        if not empty:
            empty = self.add_tilecode(
                "empty",
                "100",
                "empty",
            )

        for origin_x, origin_y, tile_code in replacement_tiles:
            self.canvas.replace_tile_at(canvas_index, origin_y, origin_x, empty.image)
            self.tile_codes[canvas_index.tab_index][origin_y][origin_x] = empty.code

        for origin_x, origin_y, tile_code in replacement_tiles:
            new_x = origin_x + dist_x
            new_y = origin_y + dist_y
            if (
                new_x < 0
                or new_x >= self.lvl_width * 10
                or new_y < 0
                or new_y >= self.lvl_height * 8
            ):
                continue
            tile = self.tile_palette_map[tile_code]
            x_offset, y_offset = self.offset_for_tile(tile, self.zoom_level)

            self.canvas.replace_tile_at(
                canvas_index,
                new_y,
                new_x,
                tile.image,
                x_offset,
                y_offset,
            )
            self.tile_codes[canvas_index.tab_index][new_y][new_x] = tile_code
        self.changes_made()

    def select_tool(self, tool):
        self.tool = tool
        self.canvas.set_mode(tool)

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile, tile_size):
        if tile is None:
            return

        logger.debug("Applying custom anchor for %s", tile.name)

        logger.debug("Found %s", tile.name)
        img = tile.image
        return self.texture_fetcher.adjust_texture_xy(
            img.width(), img.height(), tile.name, tile_size
        )

    def add_tilecode(self, tile, percent, alt_tile):
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
            # file between processes.
            if alt_tile != "empty":
                new_tile_code += "%" + alt_tile

        tile_image = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(
                new_tile_code,
                self.lvl_biome(),
                self.floor_biome(),
                self.border_biome(),
                self.lvl,
                self.zoom_level,
            )
        )
        tile_image_picker = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(
                new_tile_code,
                self.lvl_biome(),
                self.floor_biome(),
                self.border_biome(),
                self.lvl,
                40,
            )
        )

        # compares tile id to tile ids in palette list
        for palette_tile in self.tile_palette_ref_in_use:
            palette_tile = palette_tile.name
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

        ref_tile = Tile(
            new_tile_code, str(usable_code), "", tile_image, tile_image_picker
        )
        self.tile_palette_ref_in_use.append(ref_tile)
        self.tile_palette_map[usable_code] = ref_tile

        self.populate_tilecode_palette()
        self.log_codes_left()
        self.changes_made()
        return ref_tile

    def delete_tilecode(self, tile):
        if tile.name == r"empty":
            tkMessageBox.showinfo("Uh Oh!", "Can't delete empty!")
            return False

        msg_box = tk.messagebox.askquestion(
            "Delete Tilecode?",
            "Are you sure you want to delete this Tilecode?\nAll of its placements will be replaced with air.",
            icon="warning",
        )
        if msg_box == "yes":
            new_tile = self.tile_palette_map["0"]
            for matrix_index, tile_code_matrix in enumerate(self.tile_codes):
                for row in range(len(tile_code_matrix)):
                    for column in range(len(tile_code_matrix[row])):
                        if str(tile_code_matrix[row][column]) == tile.code:
                            self.canvas.replace_tile_at(
                                CanvasIndex(matrix_index, 0),
                                row,
                                column,
                                new_tile.image,
                            )
                            tile_code_matrix[row][column] = "0"
            self.usable_codes.append(tile.code)
            logger.debug("%s is now available for use.", tile.code)

            # Adds tilecode back to list to be reused.
            for id_ in self.tile_palette_ref_in_use:
                if tile.code == id_.code:
                    self.tile_palette_ref_in_use.remove(id_)
                    logger.debug("Deleted %s", tile.name)

            self.populate_tilecode_palette()

            self.log_codes_left()
            self.changes_made()

            return True
        else:
            return False

    def log_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        logger.debug("%s codes left (%s)", len(self.usable_codes), codes)

    def lvl_biome(self):
        return Biomes.biome_for_theme(self.lvl_theme, self.lvl_subtheme)

    def floor_biome(self):
        if self.lvl_floor_theme is not None:
            return Biomes.biome_for_theme(self.lvl_floor_theme, None)

    def border_biome(self):
        if self.lvl_border_entity_theme:
            return Biomes.biome_for_theme(self.lvl_border_entity_theme, None)

    # Selects a new theme, updating the grid to theme tiles and backgrounds for the
    # new theme.
    def select_theme(self, theme, subtheme):
        if theme == self.lvl_theme and subtheme == self.lvl_subtheme:
            return
        self.lvl_theme = theme
        self.lvl_subtheme = subtheme

        self.update_tiles_for_new_theme()

    def update_tiles_for_new_theme(self):
        # Retexture all of the tiles in use
        for tilecode_item in self.tile_palette_ref_in_use:
            tile_name = tilecode_item.name
            img = self.texture_fetcher.get_texture(
                tile_name,
                self.lvl_biome(),
                self.floor_biome(),
                self.border_biome(),
                self.lvl,
                self.zoom_level,
            )
            img_select = self.texture_fetcher.get_texture(
                tile_name,
                self.lvl_biome(),
                self.floor_biome(),
                self.border_biome(),
                self.lvl,
                40,
            )
            tilecode_item.image = ImageTk.PhotoImage(img)
            tilecode_item.picker_image = ImageTk.PhotoImage(img_select)

        # Load suggested tiles for the new theme.
        self.tile_palette_suggestions = suggested_tiles_for_theme(
            self.lvl_theme, self.lvl_subtheme
        )
        # Redraw the tilecode palette with the new textures of tiles and the new suggestions.
        self.populate_tilecode_palette()
        # Draw the grid now that we have the newly textured tiles.
        self.draw_canvas(False)

        self.changes_made()

    # Store new display name to save in the level sequence.
    def update_level_name(self, name):
        self.lvl_name = name
        self.changes_made()

    # Store new border theme and looping info to save in the level sequence.
    def select_border_theme(self, border_theme, loop):
        self.lvl_border_theme = border_theme
        self.lvl_loop = loop
        self.changes_made()

    # Store new border entity type to save in the level sequence.
    def select_border_entity_theme(self, border_entity_theme):
        self.lvl_border_entity_theme = border_entity_theme
        self.update_tiles_for_new_theme()
        self.changes_made()

    # Store new background theme to save in the level sequence.
    def select_background_theme(self, background_theme, background_subtheme):
        self.lvl_background_theme = background_theme
        self.lvl_background_subtheme = background_subtheme
        self.draw_canvas(False)
        self.changes_made()

    # Store new floor theme to save in the level sequence.
    def select_floor_theme(self, floor_theme):
        self.lvl_floor_theme = floor_theme
        self.update_tiles_for_new_theme()
        self.changes_made()

    # Store new music theme to save in the level sequence.
    def select_music_theme(self, music_theme):
        self.lvl_music_theme = music_theme
        self.changes_made()

    # Store new value of whether to skip CO fixes for jellyfish and orbs to save in the level sequence.
    def select_skip_co_fixes(self, skip_co_fixes):
        self.lvl_skip_co_fixes = skip_co_fixes
        self.changes_made()

    # Store new value of whether to spawn jellyfish at every exit door to save in the level sequence.
    def select_spawn_door_jellyfish(self, spawn_door_jellyfish):
        self.lvl_spawn_door_jellyfish = spawn_door_jellyfish
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
            if tile_ref.name == "empty":
                empty = tile_ref.code
            elif tile_ref.name == "floor_hard":
                hard_floor = tile_ref.code

        # If we didn't find an "empty" tile code, create one and use it.
        if not empty:
            empty = self.add_tilecode(
                "empty",
                "100",
                "empty",
            ).code
        # If we did not find a "hard_floor" tile code, create one and use it.
        if not hard_floor:
            hard_floor = self.add_tilecode(
                "hard_floor",
                "100",
                "empty",
            ).code

        self.tile_codes = [
            fill_to_size_with_tile(self.tile_codes[LAYER.FRONT], empty, width, height),
            fill_to_size_with_tile(
                self.tile_codes[LAYER.BACK], hard_floor, width, height
            ),
        ]

        self.lvl_width = width
        self.lvl_height = height
        self.changes_made()
        self.draw_canvas(False)

    def update_zoom(self, zoom):
        self.zoom_level = zoom
        image_path = BASE_DIR / "static/images/help.png"
        self.error_image = ImageTk.PhotoImage(
            Image.open(image_path).resize((zoom, zoom))
        )
        if self.lvl:
            for tile in self.tile_palette_ref_in_use:
                tile_name = tile.name
                tile.image = ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        tile_name,
                        self.lvl_biome(),
                        self.floor_biome(),
                        self.border_biome(),
                        self.lvl,
                        self.zoom_level,
                    )
                )
            self.canvas.set_zoom(zoom)
            self.draw_canvas(False)

    def set_current_save_format(self, save_format):
        self.current_save_format = save_format
        self.files_tree.current_save_format = save_format

    # Updates the list of levels in the sequence, then saves the sequence to a file.
    def update_level_sequence(self, new_sequence):
        if len(new_sequence) > 0:
            self.has_sequence = True

        self.files_tree.update_has_sequence(self.has_sequence)

        self.sequence = new_sequence
        self.save_level_sequence()

    # Save the current sequence configuration and configurations of all levels to a file.
    def save_level_sequence(self):
        if not self.has_sequence:
            return  # Do not attempt to save level configurations if a sequence hasn't been created.

        configuration_sequence = [
            self.configuration_for_level(level) for level in self.sequence
        ]

        level_configurations = LevelConfigurations(
            configuration_sequence, self.level_configurations
        )
        level_configurations.save(self.loaded_pack_path)

    # Returns the configuration of a level if it exists. If no configuration exists, one is
    # generated from the information in the lvl file.
    def configuration_for_level(self, level_name):
        if self.files_tree.selected_file_is_arena():
            return None

        if level_name in self.level_configurations:
            return self.level_configurations[level_name]

        level = self.read_custom_level_file(level_name)
        level_path = Path(level_name)
        save_format = self.read_save_format(level)
        if save_format is not None:
            theme = self.read_theme(level, save_format)
        else:
            theme = Theme.DWELLING

        configuration = LevelConfiguration(
            level_path.stem, level_path.stem.capitalize(), level_name, theme
        )

        self.level_configurations[level_name] = configuration

        return configuration

    # Updates the configuration of the currently loaded level to the properties that
    # have been set since the last level save.
    def write_current_level_configuration(self):
        if self.files_tree.selected_file_is_arena():
            return

        configuration = self.configuration_for_level(self.lvl)
        configuration.theme = self.lvl_theme
        configuration.subtheme = self.lvl_subtheme
        configuration.border_theme = self.lvl_border_theme
        configuration.loop = None
        configuration.dont_loop = None
        if self.lvl_loop is not None:
            if self.lvl_loop:
                configuration.loop = True
            else:
                configuration.dont_loop = True
        configuration.border_entity_theme = self.lvl_border_entity_theme
        if self.lvl_border_entity_theme is None and self.lvl_border_theme is not None:
            # Set the default border entity to the proper entity type for the border theme.
            def theme_is(theme):
                return self.lvl_theme == theme or (
                    self.lvl_theme == Theme.COSMIC_OCEAN and self.lvl_subtheme == theme
                )

            if (
                self.lvl_border_theme == Theme.DWELLING
                or self.lvl_border_theme == Theme.TIAMAT
                or self.lvl_border_theme == Theme.ICE_CAVES
                or self.lvl_border_theme == Theme.COSMIC_OCEAN
            ):
                if theme_is(Theme.SUNKEN_CITY) or theme_is(Theme.HUNDUN):
                    configuration.border_entity_theme = Theme.SUNKEN_CITY
                elif theme_is(Theme.NEO_BABYLON) or theme_is(Theme.TIAMAT):
                    configuration.border_entity_theme = Theme.NEO_BABYLON
                else:
                    configuration.border_entity_theme = Theme.DWELLING
            elif self.lvl_border_theme == Theme.DUAT:
                configuration.border_entity_theme = Theme.DUAT
        configuration.background_theme = self.lvl_background_theme
        configuration.background_texture_theme = None
        if self.lvl_background_theme == Theme.COSMIC_OCEAN:
            configuration.background_texture_theme = self.lvl_background_subtheme
            # With no subtheme configured, the game will crash, so configure the texture
            # by the theme as a fallback to attempt to avoid this.
            if self.lvl_background_subtheme is None and self.lvl_subtheme is None:
                configuration.background_texture_theme = self.lvl_theme
        configuration.floor_theme = self.lvl_floor_theme
        configuration.music_theme = self.lvl_music_theme
        configuration.skip_co_fixes = self.lvl_skip_co_fixes
        configuration.spawn_door_jellyfish = self.lvl_spawn_door_jellyfish
        configuration.width = self.lvl_width
        configuration.height = self.lvl_height
        if self.lvl_name:
            configuration.name = self.lvl_name
        self.level_configurations[self.lvl] = configuration
        self.save_level_sequence()

    # Parses the level at the path provided and returns an object with the level info.
    def read_custom_level_file(self, lvl_name):
        return LevelFile.from_path(self.lvls_path / lvl_name)

    # Returns the list of all levels in the current selected modpack that do not exist
    # in the vanilla game.
    def list_custom_level_file_names(self):
        level_files = [
            os.path.basename(os.path.normpath(i))
            for i in glob.iglob(str(self.lvls_path) + "/***.lvl")
        ]

        def is_custom(lvl):
            return not (self.extracts_path / lvl).exists()

        level_files = filter(is_custom, level_files)

        return list(level_files)

    # Updates the path of the pack that has been selected, and extracts some info
    # about the level sequence in the pack.
    def update_lvls_path(self, new_path):
        self.reset()
        self.lvls_path = new_path
        self.loaded_pack_path = Path(
            self.packs_path / self.files_tree.get_loaded_pack()
        )

        level_configurations = LevelConfigurations.from_path(self.loaded_pack_path)
        self.sequence = [
            sequence_configuration.file_name
            for sequence_configuration in level_configurations.sequence
        ]
        self.level_configurations = level_configurations.all_configurations
        self.sequence_panel.update_pack(
            self.loaded_pack_path, self.sequence, self.list_custom_level_file_names()
        )
        self.has_sequence = (
            len(level_configurations.sequence) > 0
            or len(level_configurations.all_configurations) > 0
        )
        self.files_tree.update_has_sequence(self.has_sequence)

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
            self.level_configuration_panel.disable_controls()
            self.show_intro()
            self.canvas.clear()
            self.tile_palette_map = {}
            self.tile_palette_ref_in_use = None
            self.tile_palette_suggestions = None
            self.lvl = None
            self.lvl_theme = None
            self.lvl_subtheme = None
            self.tile_codes = None
            self.reset_save_button()
        except Exception:  # pylint: disable=broad-except
            logger.debug("canvas does not exist yet")
