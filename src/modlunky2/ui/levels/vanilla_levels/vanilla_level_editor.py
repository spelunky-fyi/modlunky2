import logging
import math
import os
import os.path
from pathlib import Path
from PIL import Image, ImageTk
import re
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkMessageBox

from modlunky2.levels import LevelFile
from modlunky2.levels.tile_codes import VALID_TILE_CODES, TileCode, TileCodes, ShortCode
from modlunky2.ui.levels.shared.biomes import Biomes
from modlunky2.ui.levels.shared.files_tree import FilesTree, PACK_LIST_TYPE, LEVEL_TYPE
from modlunky2.ui.levels.shared.make_backup import make_backup
from modlunky2.ui.levels.shared.multi_canvas_container import MultiCanvasContainer
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.vanilla_levels.dual_util import make_dual, remove_dual
from modlunky2.ui.levels.vanilla_levels.level_list_panel import LevelListPanel
from modlunky2.ui.levels.vanilla_levels.level_settings_bar import LevelSettingsBar
from modlunky2.ui.levels.vanilla_levels.levels_tree import LevelsTreeRoom, LevelsTreeTemplate
from modlunky2.ui.levels.vanilla_levels.rules.rules_tab import RulesTab
from modlunky2.ui.levels.vanilla_levels.variables.level_dependencies import LevelDependencies
from modlunky2.ui.levels.vanilla_levels.variables.variables_tab import VariablesTab
from modlunky2.ui.widgets import PopupWindow
from modlunky2.utils import tb_info

logger = logging.getLogger(__name__)

class VanillaLevelEditor(ttk.Frame):
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

        self.save_needed = False
        self.extracts_path = extracts_path
        self.packs_path = packs_path
        self.lvls_path = None

        self.lvl_biome = None
        self.lvl = None
        self.last_selected_room = None
        self.usable_codes = ShortCode.usable_codes()
        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        self.tiles_meta = []

        self.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.rowconfigure(0, weight=1)  # Row 0 = List box / Label

        self.files_tree = FilesTree(
            self,
            modlunky_config,
            packs_path,
            extracts_path,
            PACK_LIST_TYPE.VANILLA_ROOMS,
            lambda: self.save_needed,
            self.reset_save_button,
            self.update_lvls_path,
            self.on_select_file,
        )
        self.files_tree.grid(row=0, column=0, rowspan=1, sticky="news")
        self.files_tree.load_packs()

        # Seperates Level Rules and Level Editor into two tabs
        self.tab_control = ttk.Notebook(self)
        self.tab_control.grid(row=0, column=1, rowspan=3, sticky="nwse")

        self.last_selected_tab = None

        def tab_selected(event):
            selection = event.widget.select()
            tab = event.widget.tab(selection, "text")
            self.last_selected_tab = str(tab)
            if str(tab) == "Full Level View":
                self.load_full_preview()

        self.tab_control.bind("<<NotebookTabChanged>>", tab_selected)

        self.rules_tab = RulesTab(self.tab_control, self.modlunky_config, self.changes_made)
        self.editor_tab = ttk.Frame(
            self.tab_control
        )  # Tab 2 is the actual level editor
        self.preview_tab = ttk.Frame(self.tab_control)
        self.variables_tab = VariablesTab(
            self.tab_control,
            self.modlunky_config,
            None,
            self.extracts_path,
            self.save_requested,
            lambda: self.files_tree.on_click(None),
        )

        self.back_button = tk.Button(
            self, text="Exit Editor", bg="black", fg="white", command=on_go_back
        )
        if not standalone:
            self.back_button.grid(row=1, column=0, sticky="nswe")

        self.save_button = tk.Button(
            self,
            text="Save",
            bg="purple",
            fg="white",
            command=self.save_changes,
        )
        self.save_button.grid(row=2, column=0, sticky="nswe")
        self.save_button["state"] = tk.DISABLED

        #  View Tab

        self.current_value_full = tk.DoubleVar()

        def slider_changed(_event):
            self.load_full_preview()

        config_container = tk.Frame(self.preview_tab)
        config_container.grid(row=0, column=0, columnspan=2, sticky="nw")

        self.slider_zoom_full = tk.Scale(
            config_container,
            from_=2,
            to=100,
            length=300,
            orient="horizontal",
            variable=self.current_value_full,
            command=slider_changed,
        )
        self.slider_zoom_full.set(50)
        self.slider_zoom_full.grid(row=0, column=0, sticky="nw")

        # Checkbox to toggle the visibility of the grid lines.
        hide_grid_var = tk.IntVar()
        hide_grid_var.set(False)

        def toggle_hide_grid():
            nonlocal hide_grid_var

            self.full_level_preview_canvas.hide_grid_lines(hide_grid_var.get())

        tk.Checkbutton(
            config_container,
            text="Hide grid lines",
            variable=hide_grid_var,
            onvalue=True,
            offvalue=False,
            command=toggle_hide_grid,
        ).grid(row=0, column=1, sticky="sw", pady=5)

        self.preview_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.preview_tab.rowconfigure(1, weight=1)  # Row 0 = List box / Label

        self.full_level_preview_canvas = MultiCanvasContainer(
            self.preview_tab,
            textures_dir,
            ["Foreground", "Background"],
            50,
            intro_text="Select a level file to begin viewing",
        )
        self.full_level_preview_canvas.grid(row=1, column=0, columnspan=2, rowspan=2, sticky="nw")

        # Level Editor Tab
        self.tab_control.add(self.editor_tab, text="Level Editor")
        self.tab_control.add(self.rules_tab, text="Rules")
        self.tab_control.add(self.preview_tab, text="Full Level View")
        self.tab_control.add(self.variables_tab, text="Variables (Experimental)")

        self.editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.editor_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.editor_tab.rowconfigure(2, weight=1)  # Row 0 = List box / Label

        self.level_list_panel = LevelListPanel(self.editor_tab, self.changes_made, self.reset_canvas, self.room_select, self.modlunky_config)
        self.level_list_panel.grid(row=0, column=0, rowspan=5, sticky="nswe")

        self.mag = 50  # The size of each tiles in the grid; 50 is optimal.

        vanilla_editor_container = tk.Frame(
            self.editor_tab,
            bg="#292929",
        )
        vanilla_editor_container.grid(row=0, column=1, rowspan=4, columnspan=8, sticky="news")

        self.canvas = MultiCanvasContainer(
            vanilla_editor_container,
            textures_dir,
            ["Foreground Area", "Background Area"],
            self.mag,
            self.canvas_click,
            self.canvas_shiftclick,
            "Select a room to begin editing",
            side_by_side=True,
        )
        self.canvas.grid(row=0, column=0, rowspan=4, columnspan=8, sticky="news")

        vanilla_editor_container.columnconfigure(3, weight=1)
        vanilla_editor_container.rowconfigure(0, weight=1)

        self.button_hide_tree = ttk.Button(
            vanilla_editor_container, text="<<", command=self.toggle_list_hide
        )
        self.button_hide_tree.grid(row=0, column=0, sticky="nw")

        self.button_replace = ttk.Button(
            vanilla_editor_container, text="Replace", command=self.replace_tiles_dia
        )
        self.button_replace.grid(row=0, column=1, sticky="nw")
        self.button_replace["state"] = tk.DISABLED

        self.button_clear = ttk.Button(
            vanilla_editor_container, text="Clear Canvas", command=self.clear_canvas
        )
        self.button_clear.grid(row=0, column=2, sticky="nw")
        self.button_clear["state"] = tk.DISABLED

        self.palette_panel = PalettePanel(
            self.editor_tab,
            self.delete_tilecode,
            lambda tile, percent, alt_tile: self.add_tilecode(
                tile,
                percent,
                alt_tile,
                self.palette_panel,
                self.mag
            ),
            self.texture_fetcher,
            self.texture_fetcher.sprite_fetcher,
        )
        self.palette_panel.grid(row=0, column=9, rowspan=5, columnspan=4, sticky="nwse")

        self.level_settings_bar = LevelSettingsBar(self.editor_tab, self.remember_changes, self.dual_toggle)
        self.level_settings_bar.grid(row=4, column=1, columnspan=8, sticky="news")


    def read_lvl_file(self, lvl):
        self.last_selected_room = None
        self.usable_codes = ShortCode.usable_codes()
        self.variables_tab.update_current_level_name(lvl)
        self.variables_tab.check_dependencies()

        self.rules_tab.reset()

        self.level_list_panel.reset()
        self.button_replace["state"] = tk.NORMAL

        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        self.lvl = lvl

        self.lvl_biome = Biomes.get_biome_for_level(lvl)

        logger.debug("searching %s", self.lvls_path / lvl)
        if Path(self.lvls_path / lvl).exists():
            logger.debug("Found this lvl in pack; loading it instead")
            lvl_path = Path(self.lvls_path) / lvl
        else:
            logger.debug(
                "Did not find this lvl in pack; loading it from extracts instead"
            )
            if self.files_tree.selected_file_is_arena():
                lvl_path = self.extracts_path / "Arena" / lvl
            else:
                lvl_path = self.extracts_path / lvl

        # Levels to load dependency tilecodes from.
        level_dependencies = LevelDependencies.dependencies_for_level(lvl)
        levels = []
        for dependency in level_dependencies:
            levels.append(LevelDependencies.loaded_level_file_for_path(dependency, self.lvls_path, self.extracts_path))
        levels.append(LevelFile.from_path(Path(lvl_path)))

        level = None
        for level in levels:
            logger.debug("%s loaded.", level.comment)
            level_tilecodes = level.tile_codes.all()

            for tilecode in level_tilecodes:
                tilecode_item = []
                tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

                img = self.texture_fetcher.get_texture(tilecode.name, self.lvl_biome, lvl, self.mag)
                selection_img = self.texture_fetcher.get_texture(tilecode.name, self.lvl_biome, lvl, 40)

                tilecode_item.append(ImageTk.PhotoImage(img))
                tilecode_item.append(ImageTk.PhotoImage(selection_img))

                self.palette_panel.select_tile(tilecode_item[0], tilecode_item[2], True)
                self.palette_panel.select_tile(tilecode_item[0], tilecode_item[2], False)

                for i in self.tile_palette_ref_in_use:
                    if str(i[0]).split(" ", 1)[1] == str(tilecode.value):
                        self.tile_palette_ref_in_use.remove(i)

                if tilecode.value in self.usable_codes:
                    self.usable_codes.remove(tilecode.value)

                self.tile_palette_ref_in_use.append(tilecode_item)
                self.tile_palette_map[tilecode.value] = tilecode_item

        if level is None:
            return

        if lvl.startswith(
            "generic"
        ):  # Adds tilecodes to generic that it relies on yet doesn't provide.
            generic_needs = [
                ["4", "push_block"],
                ["t", "treasure"],
                ["1", "floor"],
                ["6", "chunk_air"],
                ["=", "minewood_floor"],
            ]
            for need in generic_needs:
                for code in self.usable_codes:
                    if str(code) == need[0] and not any(
                        need[0] in str(code_in_use[0].split(" ", 3)[1])
                        for code_in_use in self.tile_palette_ref_in_use
                    ):
                        for i in self.usable_codes:
                            if str(i) == str(need[0]):
                                self.usable_codes.remove(i)
                        tilecode_item = []
                        tilecode_item.append(str(need[1]) + " " + str(need[0]))

                        img = self.texture_fetcher.get_texture(
                            str(need[1]), self.lvl_biome, lvl, self.mag
                        )
                        img_select = self.texture_fetcher.get_texture(
                            str(need[1]), self.lvl_biome, lvl, 40
                        )

                        tilecode_item.append(ImageTk.PhotoImage(img))
                        tilecode_item.append(ImageTk.PhotoImage(img_select))
                        self.tile_palette_ref_in_use.append(tilecode_item)
                        self.tile_palette_map[need[0]] = tilecode_item
        self.populate_tilecode_palette()

        self.rules_tab.load_level_settings(level.level_settings)
        self.rules_tab.load_monster_chances(level.monster_chances)
        self.rules_tab.load_level_chances(level.level_chances)

        level_templates = level.level_templates.all()

        tree_templates = []
        for template in level_templates:
            template_comment = ""
            if str(template.comment) != "":
                template_comment = "// " + str(template.comment)
            rooms = []
            for room in template.chunks:
                room_string = []  # Makes room data into string for storing.

                for setting in room.settings:
                    room_string.append(r"\!" + str(setting).split(".", 1)[1].lower())

                i = 0
                for line in room.foreground:
                    foreground = ""
                    background = ""
                    for code in line:
                        foreground += str(code)
                    if len(room.background) > 0:
                        background += " "
                        for code in room.background[i]:
                            background += str(code)
                    room_string.append(foreground + background)
                    i = i + 1

                room_name = "room"
                comment = str(room.comment).lstrip("/ ").strip()
                if comment:
                    room_name = comment

                rooms.append(LevelsTreeRoom(str(room_name), room_string))
            tree_templates.append(LevelsTreeTemplate(str(template.name) + "   " + template_comment, rooms))
        self.level_list_panel.set_rooms(tree_templates)


    def load_full_preview(self):
        self.list_preview_tiles_ref = []
        # Sets default level size for levels that might not have a size variable like the challenge levels.
        # 8x8 is what I went with.
        level_height = 8
        level_width = 8

        mag_full = int(self.slider_zoom_full.get() / 2)
        self.full_level_preview_canvas.clear()
        self.full_level_preview_canvas.set_zoom(mag_full)

        full_size = None
        if self.files_tree.has_selected_file():
            full_size = self.rules_tab.get_full_size()
            if full_size is not None:
                logger.debug("Size found: %s", full_size)
                level_height = int(full_size.split(", ")[1])
                level_width = int(full_size.split(", ")[0])
            self.full_level_preview_canvas.configure_size(level_width, level_height)
            self.full_level_preview_canvas.draw_background(self.lvl_biome)
            self.full_level_preview_canvas.draw_grid()
        else:
            self.full_level_preview_canvas.show_intro()
            return

        self.full_level_preview_canvas.hide_intro()

        def flip_text(x_coord):
            return x_coord[::-1]

        for setroom_template in self.level_list_panel.get_setrooms():
            room_x = setroom_template.setroom.coords.x
            room_y = setroom_template.setroom.coords.y

            logger.debug("%s", setroom_template.template.name)
            logger.debug("Room pos: %sx%s", room_x, room_y)
            current_room_tiles = []
            current_room_tiles_dual = []
            layers = []

            tree_rooms = setroom_template.template.rooms
            flip_room = False
            if len(tree_rooms) != 0:
                tree_room = tree_rooms[0]
                for cr_line in tree_room.rows:
                    if str(cr_line).startswith(r"\!"):
                        logger.debug("found tag %s", cr_line)
                        if str(cr_line) == r"\!onlyflip":
                            flip_room = True
                        elif str(cr_line) == r"\!ignore":
                            continue
                    else:
                        logger.debug("appending %s", cr_line)
                        load_line = ""
                        load_line_dual = ""
                        dual_mode = False
                        for char in str(cr_line):
                            if str(char) == " ":
                                dual_mode = True
                                logger.debug("dual room found")

                                if flip_room:
                                    current_room_tiles.append(flip_text(str(load_line)))
                                else:
                                    current_room_tiles.append(str(load_line))
                            else:
                                if dual_mode:
                                    load_line_dual += str(char)
                                else:
                                    load_line += str(char)
                        if dual_mode:
                            if flip_room:
                                current_room_tiles_dual.append(
                                    flip_text(str(load_line_dual))
                                )
                            else:
                                current_room_tiles_dual.append(str(load_line_dual))
                        else:
                            if flip_room:
                                current_room_tiles.append(flip_text(str(load_line)))
                            else:
                                current_room_tiles.append(str(load_line))

                curcol = 0

                layers.append(current_room_tiles)
                layers.append(current_room_tiles_dual)

                for layer_index, layer in enumerate(layers):
                    for currow, room_row in enumerate(layer):
                        curcol = 0
                        tile_image_full = None
                        logger.debug("Room row: %s", room_row)
                        for block in str(room_row):
                            if str(block) != " ":
                                tile_name = ""
                                tiles = [
                                    c
                                    for c in self.tile_palette_ref_in_use
                                    if str(" " + block) in str(c[0])
                                ]
                                if tiles:
                                    tile_name = str(tiles[-1][0]).split(" ", 1)[0]
                                    new_ref = True
                                    for (
                                        preview_tile_ref
                                    ) in self.list_preview_tiles_ref:
                                        if tile_name == str(preview_tile_ref[0]):
                                            new_ref = False
                                            tile_image_full = preview_tile_ref[1]

                                    if new_ref:
                                        tile_ref = []
                                        tile_image = ImageTk.PhotoImage(
                                            ImageTk.getimage(tiles[-1][1])
                                            .resize(
                                                (mag_full, mag_full),
                                                Image.Resampling.LANCZOS,
                                            )
                                            .convert("RGBA")
                                        )
                                        tile_ref.append(tile_name)
                                        tile_ref.append(tile_image)
                                        self.list_preview_tiles_ref.append(tile_ref)
                                        tile_image_full = (
                                            self.list_preview_tiles_ref[
                                                len(self.list_preview_tiles_ref) - 1
                                            ][1]
                                        )
                                else:
                                    # There's a missing tile id somehow
                                    logger.debug("%s Not Found", block)

                                self.full_level_preview_canvas.replace_tile_at(
                                    layer_index,
                                    room_y * 8 + currow,
                                    room_x * 10 + curcol,
                                    tile_image_full,
                                    0,
                                    0,
                                )
                            curcol = curcol + 1

    def populate_tilecode_palette(self):
        self.palette_panel.update_with_palette(
            self.tile_palette_ref_in_use,
            None,
            self.lvl_biome,
            self.lvl,
        )

    def save_requested(self):
        if self.save_needed:
            msg_box = tk.messagebox.askquestion(
                "Save now?",
                "This will save all your current changes. Continue?",
                icon="warning",
            )
            if msg_box == "no":
                return False
            else:
                return self.save_changes()
        return True

    def reset_save_button(self):
        self.save_needed = False
        self.save_button["state"] = tk.DISABLED

    def changes_made(self):
        self.save_needed = True
        self.save_button["state"] = tk.NORMAL

    def save_changes(self):
        if self.save_needed:
            try:
                level_chances = self.rules_tab.get_level_chances()
                level_settings = self.rules_tab.get_level_settings()
                monster_chances = self.rules_tab.get_monster_chances()
                level_templates = self.level_list_panel.get_level_templates()

                tile_codes = TileCodes()
                for tilecode in self.tile_palette_ref_in_use:
                    tile_codes.set_obj(
                        TileCode(
                            name=tilecode[0].split(" ", 1)[0],
                            value=tilecode[0].split(" ", 1)[1],
                            comment="",
                        )
                    )

                level_file = LevelFile(
                    "",
                    level_settings,
                    tile_codes,
                    level_chances,
                    monster_chances,
                    level_templates,
                )
                save_path = None
                if not os.path.exists(Path(self.lvls_path)):
                    os.makedirs(Path(self.lvls_path))
                save_path = Path(
                    self.lvls_path
                    / self.files_tree.get_loaded_level()
                )
                loaded_pack = self.files_tree.get_loaded_pack()
                backup_dir = str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
                make_backup(save_path, backup_dir)
                logger.debug("Saving to %s", save_path)

                with Path(save_path).open("w", encoding="cp1252") as handle:
                    level_file.write(handle)

                logger.debug("Saved!")
                self.files_tree.update_selected_file_icon(LEVEL_TYPE.MODDED)
                self.reset_save_button()
                logger.debug("Saved")
            except Exception:  # pylint: disable=broad-except
                logger.critical("Failed to save level: %s", tb_info())
                _msg_box = tk.messagebox.showerror(
                    "Oops?",
                    "Error saving..",
                )
                return False
        else:
            logger.debug("No changes to save")
        return True

    def remember_changes(self):  # Remembers changes made to rooms.
        current_room = self.level_list_panel.get_selected_room()
        if current_room:
            new_room_data = ""
            if self.level_settings_bar.dual():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!dual"
            if self.level_settings_bar.purge():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!purge"
            if self.level_settings_bar.flip():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!flip"
            if self.level_settings_bar.only_flip():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!onlyflip"
            if self.level_settings_bar.rare():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!rare"
            if self.level_settings_bar.hard():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!hard"
            if self.level_settings_bar.liquid():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!liquid"
            if self.level_settings_bar.ignore():
                if new_room_data != "":
                    new_room_data += "\n"
                new_room_data += r"\!ignore"

            for row in self.tiles_meta:
                if new_room_data != "":
                    new_room_data += "\n"
                for block in row:
                    if str(block) == "None":
                        new_room_data += str(" ")
                    else:
                        new_room_data += str(block)
            room_save = []
            for line in new_room_data.split("\n", 100):
                room_save.append(line)
            # Put it back in with the upated values.
            self.level_list_panel.replace_selected_room(LevelsTreeRoom(current_room.name, room_save))

            logger.debug("temp saved: \n%s", new_room_data)
            logger.debug("Changes remembered!")
            self.changes_made()
        else:
            self.canvas.clear()
            self.canvas.show_intro()

    def dual_toggle(self):
        current_room = self.level_list_panel.get_selected_room()

        if current_room:
            new_room_data = current_room.rows

            if self.level_settings_bar.dual():  # Converts room into dual.
                new_room_data = make_dual(current_room.rows)
            else:  # Converts room into non-dual.
                msg_box = tk.messagebox.askquestion(
                    "Delete Dual Room?",
                    "Un-dualing this room will delete your background layer. This is not recoverable.\nContinue?",
                    icon="warning",
                )
                if msg_box == "yes":
                    new_room_data = remove_dual(current_room.rows)
                else:
                    return

            self.level_list_panel.replace_selected_room(LevelsTreeRoom(current_room.name, new_room_data))
            self.room_select(None)
            self.remember_changes()

    def canvas_click(
        self,
        canvas_index,
        row,
        column,
        is_primary,
    ):
        tile_name, tile_code = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, self.mag)

        self.canvas.replace_tile_at(canvas_index, row, column, self.tile_palette_map[tile_code][1], x_offset, y_offset)

        col = column
        if canvas_index == 1:
            col = col + (len(self.tiles_meta[row]) + 1) // 2

        self.tiles_meta[row][col] = tile_code
        self.remember_changes()

    def canvas_shiftclick(self, canvas_index, row, column, is_primary):
        col = column
        if canvas_index == 1:
            col = col + (len(self.tiles_meta[row]) + 1) // 2

        tile_code = self.tiles_meta[row][col]
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

    def toggle_list_hide(self):
        if self.button_hide_tree["text"] == "<<":
            self.level_list_panel.grid_remove()
            self.editor_tab.columnconfigure(0, minsize=0)  # Column 0 = Level List
            self.button_hide_tree["text"] = ">>"
        else:
            self.level_list_panel.grid()
            self.editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
            self.button_hide_tree["text"] = "<<"

    def replace_tiles_dia(self):
        # Set up window.
        win = PopupWindow("Replace Tiles", self.modlunky_config)

        replacees = []
        for tile in self.tile_palette_ref_in_use:
            replacees.append(str(tile[0]))

        col1_lbl = ttk.Label(win, text="Replace all ")
        col1_lbl.grid(row=0, column=0)
        combo_replace = ttk.Combobox(win, height=20)
        combo_replace["values"] = replacees
        combo_replace.grid(row=0, column=1)

        col2_lbl = ttk.Label(win, text="with ")
        col2_lbl.grid(row=1, column=0)
        combo_replacer = ttk.Combobox(win, height=20)
        combo_replacer["values"] = replacees
        combo_replacer.grid(row=1, column=1)

        col3_lbl = ttk.Label(win, text="in ")
        col3_lbl.grid(row=2, column=0)
        combo_where = ttk.Combobox(win, height=20)
        combo_where["values"] = ["all rooms", "current room"]
        combo_where.set("current room")
        combo_where.grid(row=2, column=1)

        error_lbl = tk.Label(win, text="", fg="red")
        error_lbl.grid(row=3, column=0, columnspan=2)
        error_lbl.grid_remove()

        def update_then_destroy():
            if (
                str(combo_replace.get().split(" ", 1)[0]) != "empty"
                and combo_replace.get() != ""
                and combo_replacer.get() != ""
            ):
                if str(combo_where.get()) not in ["all rooms", "current room"]:
                    error_lbl["text"] = "Invalid parameter"
                    error_lbl.grid()
                    return
                valid_1 = False
                valid_2 = False
                for valid_tile in replacees:
                    if str(combo_replace.get()) == valid_tile:
                        valid_1 = True
                    if str(combo_replacer.get()) == valid_tile:
                        valid_2 = True
                if valid_1 is False or valid_2 is False:
                    error_lbl["text"] = "Invalid parameter"
                    error_lbl.grid()
                    return
                if (
                    str(combo_where.get()) == "current room"
                    and self.last_selected_room is None
                ):
                    error_lbl["text"] = "No current room selected.."
                    error_lbl.grid()
                    return
                self.replace_tiles(
                    str(combo_replace.get().split(" ", 1)[1]),
                    str(combo_replacer.get().split(" ", 1)[1]),
                    str(combo_where.get()),
                )
                win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=4, column=0, columnspan=3, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=5, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Replace", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")

    def replace_rooms(self, replacement_rooms):
        new_selected_room = self.level_list_panel.replace_rooms(replacement_rooms)
        if new_selected_room:
            self.last_selected_room = new_selected_room
            self.room_select(None)

    def replace_tiles(self, tile, new_tile, replace_where):
        if replace_where == "all rooms":
            existing_templates = self.level_list_panel.get_rooms()
            new_templates = []
            for existing_template in existing_templates:
                new_rooms = []
                for existing_room in existing_template.rooms:
                    room_data = []
                    room_name = existing_room.name
                    room_rows = existing_room.rows
                    for row in room_rows:
                        new_row = ""
                        if not str(row).startswith(r"\!"):
                            for replace_code in row:
                                if replace_code == str(tile):
                                    replace_code = str(new_tile)
                                    new_row += str(new_tile)
                                else:
                                    new_row += str(replace_code)
                        else:
                            new_row = str(row)
                        room_data.append(new_row)
                    new_rooms.append(LevelsTreeRoom(room_name, room_data))
                new_templates.append(LevelsTreeTemplate(existing_template.name, new_rooms))
            self.replace_rooms(new_templates)
            self.changes_made()
        else:
            row_count = 0
            for row in self.tiles_meta:
                col_count = 0
                for _ in row:
                    if self.tiles_meta[int(row_count)][int(col_count)] == tile:
                        self.tiles_meta[int(row_count)][int(col_count)] = new_tile
                    col_count = col_count + 1
                row_count = row_count + 1
            self.remember_changes()  # Remember changes made.
            self.room_select(None)

    def clear_canvas(self):
        msg_box = tk.messagebox.askquestion(
            "Clear Canvases?",
            "Completely clear your canvas? This isn't recoverable.",
            icon="warning",
        )
        if msg_box == "yes":
            row_count = 0
            for row in self.tiles_meta:
                col_count = 0
                for _ in row:
                    self.tiles_meta[int(row_count)][int(col_count)] = "0"
                    col_count = col_count + 1
                row_count = row_count + 1
            self.canvas.clear()
            self.canvas.draw_background(self.lvl_biome)
            self.canvas.draw_grid()
            self.remember_changes()  # Remember changes made.

    def room_select(self, _event):  # Loads room when click if not parent node.
        dual_mode = False
        selected_room = self.level_list_panel.get_selected_room()
        if selected_room:
            self.canvas.clear()
            self.canvas.hide_intro()

            self.last_selected_room = selected_room
            current_settings = []
            current_room_tiles = []
            current_settings = []

            for cr_line in selected_room.rows:
                if str(cr_line).startswith(r"\!"):
                    logger.debug("found tag %s", cr_line)
                    current_settings.append(cr_line)
                else:
                    logger.debug("appending %s", cr_line)
                    current_room_tiles.append(str(cr_line))
                    for char in str(cr_line):
                        if str(char) == " ":
                            dual_mode = True


            dual_mode = r"\!dual" in current_settings
            self.level_settings_bar.set_dual(dual_mode)
            self.level_settings_bar.set_flip(r"\!flip" in current_settings)
            self.level_settings_bar.set_purge(r"\!purge" in current_settings)
            self.level_settings_bar.set_only_flip(r"\!onlyflip" in current_settings)
            self.level_settings_bar.set_ignore(r"\!ignore" in current_settings)
            self.level_settings_bar.set_rare(r"\!rare" in current_settings)
            self.level_settings_bar.set_hard(r"\!hard" in current_settings)
            self.level_settings_bar.set_liquid(r"\!liquid" in current_settings)

            rows = len(current_room_tiles)
            cols = len(str(current_room_tiles[0]))

            roomwidth = int(math.ceil(cols / 10))
            if dual_mode:
                roomwidth = int(math.ceil(((cols - 1) / 2) / 10))
            self.canvas.configure_size(roomwidth, int(math.ceil(rows / 8)))

            # Draw lines to fill the size of the level.
            self.canvas.draw_background(self.lvl_biome)
            self.canvas.draw_grid()

            self.canvas.hide_canvas(1, not dual_mode)

            # Create a grid of None to store the references to the tiles.
            self.tiles_meta = [
                [None for _ in range(cols)] for _ in range(rows)
            ]  # meta for tile

            currow = -1
            curcol = 0
            for room_row in current_room_tiles:
                curcol = 0
                currow = currow + 1
                tile_image = None
                logger.debug("Room row: %s", room_row)
                for block in str(room_row):
                    if str(block) != " ":
                        tile_name = ""
                        tiles = [
                            c
                            for c in self.tile_palette_ref_in_use
                            if str(" " + block) in str(c[0])
                        ]
                        if tiles:
                            tile_image = tiles[-1][1]
                            tile_name = str(tiles[-1][0]).split(" ", 1)[0]
                        else:
                            # There's a missing tile id somehow
                            logger.debug("%s Not Found", block)
                        if dual_mode and curcol > int((cols - 1) / 2):
                            x2_coord = int(curcol - ((cols - 1) / 2) - 1)
                            x_coord, y_coord = self.texture_fetcher.adjust_texture_xy(
                                tile_image.width(),
                                tile_image.height(),
                                tile_name,
                            )
                            self.canvas.replace_tile_at(
                                1,
                                currow,
                                x2_coord,
                                tile_image,
                                x_coord,
                                y_coord,
                            )
                            self.tiles_meta[currow][curcol] = block
                        else:
                            x_coord, y_coord = self.texture_fetcher.adjust_texture_xy(
                                tile_image.width(),
                                tile_image.height(),
                                tile_name,
                            )
                            self.canvas.replace_tile_at(
                                0,
                                currow,
                                curcol,
                                tile_image,
                                x_coord,
                                y_coord,
                            )
                            self.tiles_meta[currow][curcol] = block
                    curcol = curcol + 1
        else:
            self.canvas.clear()
            self.canvas.hide_canvas(1, True)
            self.canvas.show_intro()
        self.button_clear["state"] = tk.NORMAL

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

            self.replace_tiles(tile_code, "0", "all rooms")
            logger.debug("Replaced %s in all rooms with air/empty", tile_name)

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
            self.variables_tab.check_dependencies()

    def log_codes_left(self):
        codes = ""
        for code in self.usable_codes:
            codes += str(code)
        logger.debug("%s codes left (%s)", len(self.usable_codes), codes)

    def add_tilecode(
        self,
        tile,
        percent,
        alt_tile,
        palette_panel,
        scale,
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
            # file between processes.
            if alt_tile != "empty":
                new_tile_code += "%" + alt_tile

        tile_image = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(new_tile_code, self.lvl_biome, self.lvl, scale)
        )
        tile_image_picker = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(new_tile_code, self.lvl_biome, self.lvl, 40)
        )

        # Compares tile id to tile ids in palette list.
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
        if palette_panel == self.palette_panel:
            self.variables_tab.check_dependencies()
        return ref_tile

    def update_lvls_path(self, new_path):
        self.reset()
        self.lvls_path = new_path
        self.variables_tab.update_lvls_path(new_path)

    def on_select_file(self, lvl):
        self.reset()
        self.read_lvl_file(lvl)

        if self.last_selected_tab == "Full Level View":
            self.load_full_preview()

    def reset_canvas(self):
        self.canvas.clear()

    def load_packs(self):
        self.reset()
        self.files_tree.load_packs()

    def reset(self):
        logger.debug("Resetting...")
        self.level_list_panel.reset()
        try:
            self.palette_panel.reset()
            self.full_level_preview_canvas.show_intro()
            self.full_level_preview_canvas.clear()
            self.canvas.show_intro()
            self.canvas.clear()
            self.tile_palette_map = {}
            self.tile_palette_ref_in_use = None
            self.lvl = None
            self.lvl_biome = None
            self.full_level_preview_canvas.clear()
            self.reset_save_button()
        except Exception:  # pylint: disable=broad-except
            logger.debug("canvas does not exist yet")