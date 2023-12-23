from dataclasses import dataclass
import io
import logging
import math
import os
import os.path
from pathlib import Path
from PIL import Image, ImageTk
import pyperclip
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkMessageBox
from typing import List, Optional

from modlunky2.levels import LevelFile
from modlunky2.levels.level_templates import (
    Chunk,
    LevelTemplate,
    LevelTemplates,
    TemplateSetting,
)
from modlunky2.levels.tile_codes import VALID_TILE_CODES, TileCode, TileCodes, ShortCode
from modlunky2.ui.levels.shared.biomes import Biomes
from modlunky2.ui.levels.shared.files_tree import FilesTree, PACK_LIST_TYPE, LEVEL_TYPE
from modlunky2.ui.levels.shared.make_backup import make_backup
from modlunky2.ui.levels.shared.multi_canvas_container import (
    MultiCanvasContainer,
    CanvasIndex,
)
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import Setroom, MatchedSetroom
from modlunky2.ui.levels.vanilla_levels.dual_util import make_dual, remove_dual
from modlunky2.ui.levels.vanilla_levels.level_list_panel import LevelListPanel
from modlunky2.ui.levels.vanilla_levels.level_settings_bar import LevelSettingsBar
from modlunky2.ui.levels.vanilla_levels.multi_room.multi_room_editor_tab import (
    MultiRoomEditorTab,
)
from modlunky2.ui.levels.vanilla_levels.rules.rules_tab import RulesTab
from modlunky2.ui.levels.vanilla_levels.vanilla_types import (
    RoomInstance,
    RoomTemplate,
    MatchedSetroomTemplate,
)
from modlunky2.ui.levels.vanilla_levels.variables.level_dependencies import (
    LevelDependencies,
)
from modlunky2.ui.levels.vanilla_levels.variables.variables_tab import VariablesTab
from modlunky2.ui.widgets import PopupWindow
from modlunky2.utils import tb_info

logger = logging.getLogger(__name__)


class LAYER:
    FRONT = 0
    BACK = 1


@dataclass
class RoomType:
    name: str
    x_size: int
    y_size: int


ROOM_TYPES = {
    f"{room_type.name}: {room_type.x_size}x{room_type.y_size}": room_type
    for room_type in [
        RoomType("normal", 10, 8),
        RoomType("machine_wideroom", 20, 8),
        RoomType("machine_tallroom", 10, 16),
        RoomType("machine_bigroom", 20, 16),
        RoomType("coffin_frog", 10, 16),
        RoomType("ghistroom", 5, 5),
        RoomType("feeling", 20, 16),
        RoomType("chunk_ground", 5, 3),
        RoomType("chunk_door", 6, 3),
        RoomType("chunk_air", 5, 3),
        RoomType("cache", 5, 5),
    ]
}
DEFAULT_ROOM_TYPE = "normal"


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

        self.room_has_been_selected = False
        self.save_needed = False
        self.extracts_path = extracts_path
        self.packs_path = packs_path
        self.lvls_path = None

        self.lvl_biome = None
        self.lvl = None
        self.current_selected_room = None
        self.usable_codes = ShortCode.usable_codes()
        self.tile_palette_ref_in_use = []
        self.tile_palette_map = {}
        self.tile_codes = []
        self.template_list = []

        self.mag_full = 30

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

        # Seperates Level Rules and Level Editor into two tabs.
        self.tab_control = ttk.Notebook(self)
        self.tab_control.grid(row=0, column=1, rowspan=3, sticky="nwse")

        self.last_selected_tab = None

        def tab_selected(event):
            selection = event.widget.select()
            tab = event.widget.tab(selection, "text")
            self.last_selected_tab = str(tab)
            if str(tab) == "Full Level View":
                self.load_full_preview()
            if str(tab) == "Full Level Editor":
                self.multi_room_editor_tab.update_templates()
                self.multi_room_editor_tab.redraw()

        self.tab_control.bind("<<NotebookTabChanged>>", tab_selected)

        self.rules_tab = RulesTab(
            self.tab_control, self.modlunky_config, self.changes_made
        )
        self.editor_tab = ttk.Frame(
            self.tab_control
        )  # Tab 2 is the actual level editor.
        self.preview_tab = ttk.Frame(self.tab_control)

        def multiroom_zoom_change(new_zoom):
            self.mag_full = new_zoom
            self.current_value_full.set(new_zoom)

        self.multi_room_editor_tab = MultiRoomEditorTab(
            self.tab_control,
            self.modlunky_config,
            self.texture_fetcher,
            textures_dir,
            self.mag_full,
            multiroom_zoom_change,
            lambda tile, percent, alt_tile: self.add_tilecode(
                tile, percent, alt_tile, self.palette_panel, self.mag
            ),
            self.delete_tilecode,
            self.multiroom_editor_selected_tile,
            self.multiroom_editor_modified_room,
            self.multiroom_editor_changed_filetree,
            self.on_insert_room,
            self.on_duplicate_room,
            self.on_rename_room,
            self.on_delete_room,
        )
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
            self.mag_full = int(self.current_value_full.get())
            self.load_full_preview()
            self.multi_room_editor_tab.update_zoom_level(self.mag_full)

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
        self.slider_zoom_full.set(self.mag_full)
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
            [],
            self.mag_full,
            intro_text="Select a level file to begin viewing",
        )
        self.full_level_preview_canvas.grid(
            row=1, column=0, columnspan=2, rowspan=2, sticky="nw"
        )

        # Level Editor Tab
        self.tab_control.add(self.editor_tab, text="Level Editor")
        self.tab_control.add(self.rules_tab, text="Rules")
        self.tab_control.add(self.multi_room_editor_tab, text="Full Level Editor")
        self.tab_control.add(self.variables_tab, text="Variables (Experimental)")

        self.editor_tab.columnconfigure(0, minsize=200)  # Column 0 = Level List
        self.editor_tab.columnconfigure(1, weight=1)  # Column 1 = Everything Else
        self.editor_tab.rowconfigure(2, weight=1)  # Row 0 = List box / Label

        self.level_list_panel = LevelListPanel(
            self.editor_tab,
            self.changes_made,
            self.reset_canvas,
            self.on_insert_room,
            self.on_delete_room,
            self.on_duplicate_room,
            self.on_copy_room,
            self.on_paste_room,
            self.on_rename_room,
            self.room_select,
            self.modlunky_config,
        )
        self.level_list_panel.grid(row=0, column=0, rowspan=5, sticky="nswe")

        self.mag = 50  # The size of each tiles in the grid; 50 is optimal.

        vanilla_editor_container = tk.Frame(
            self.editor_tab,
            bg="#292929",
        )
        vanilla_editor_container.grid(
            row=0, column=1, rowspan=4, columnspan=8, sticky="news"
        )

        self.canvas = MultiCanvasContainer(
            vanilla_editor_container,
            textures_dir,
            [],
            ["Foreground Area", "Background Area"],
            self.mag,
            self.canvas_click,
            self.canvas_shiftclick,
            intro_text="Select a room to begin editing",
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
                tile, percent, alt_tile, self.palette_panel, self.mag
            ),
            self.palette_selected_tile,
            self.texture_fetcher,
            self.texture_fetcher.sprite_fetcher,
        )
        self.palette_panel.grid(row=0, column=9, rowspan=5, columnspan=4, sticky="nwse")

        # Allow hiding the side panel so more level can be seen.
        side_panel_hidden = False
        side_panel_hide_button = tk.Button(self.editor_tab, text=">>")

        def toggle_panel_hidden():
            nonlocal side_panel_hidden
            side_panel_hidden = not side_panel_hidden
            if side_panel_hidden:
                self.palette_panel.grid_remove()
                side_panel_hide_button.configure(text="<<")
            else:
                self.palette_panel.grid()
                side_panel_hide_button.configure(text=">>")

        side_panel_hide_button.configure(
            command=toggle_panel_hidden,
        )
        side_panel_hide_button.grid(column=7, row=0, sticky="nwe")
        self.editor_tab.columnconfigure(7, minsize=50)
        self.editor_tab.columnconfigure(8, minsize=0)

        self.level_settings_bar = LevelSettingsBar(self.editor_tab, self.setting_flip)
        self.level_settings_bar.grid(row=4, column=1, columnspan=8, sticky="news")

    def read_lvl_file(self, lvl):
        self.current_selected_room = None
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
            levels.append(
                LevelDependencies.loaded_level_file_for_path(
                    dependency, self.lvls_path, self.extracts_path
                )
            )
        levels.append(LevelFile.from_path(Path(lvl_path)))

        level = None
        for level in levels:
            logger.debug("%s loaded.", level.comment)
            level_tilecodes = level.tile_codes.all()

            for tilecode in level_tilecodes:
                tilecode_item = []
                tilecode_item.append(str(tilecode.name) + " " + str(tilecode.value))

                img = self.texture_fetcher.get_texture(
                    tilecode.name, self.lvl_biome, lvl, self.mag
                )
                selection_img = self.texture_fetcher.get_texture(
                    tilecode.name, self.lvl_biome, lvl, 40
                )

                tilecode_item.append(ImageTk.PhotoImage(img))
                tilecode_item.append(ImageTk.PhotoImage(selection_img))

                self.select_palette_tile(tilecode_item, True)
                self.select_palette_tile(tilecode_item, False)

                for i in self.tile_palette_ref_in_use:
                    if str(i[0]).split(" ", 1)[1] == str(tilecode.value):
                        self.tile_palette_ref_in_use.remove(i)

                if tilecode.value in self.usable_codes:
                    self.usable_codes.remove(tilecode.value)

                self.tile_palette_ref_in_use.append(tilecode_item)
                self.tile_palette_map[tilecode.value] = tilecode_item

        # Populate the default tile code for left clicks.
        if "1" in self.tile_palette_map:
            # If there is a "1" tile code, guess it is a good default tile since it is often the floor.
            tile = self.tile_palette_map["1"]
            self.select_palette_tile(tile, True)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there is no "1" tile, just populate with the first tile.
            tile = self.tile_palette_ref_in_use[0]
            self.select_palette_tile(tile, True)
            secondary_backup_index = 1

        # Populate the default tile code for right clicks.
        if "0" in self.tile_palette_map:
            # If there is a "0" tile code, guess it is a good default secondary tile since it is often the empty tile.
            tile = self.tile_palette_map["0"]
            self.select_palette_tile(tile, False)
        elif len(self.tile_palette_ref_in_use) > secondary_backup_index:
            # If there is not a "0" tile code, populate with the second tile code if the
            # primary tile code was populated from the first one.
            tile = self.tile_palette_ref_in_use[secondary_backup_index]
            self.select_palette_tile(tile, False)
        elif len(self.tile_palette_ref_in_use) > 0:
            # If there are only one tile code available, populate both right and
            # left click with it.
            tile = self.tile_palette_ref_in_use[0]
            self.select_palette_tile(tile, False)

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

        self.template_list = []
        for template in level_templates:
            data_rooms = []
            for room in template.chunks:
                data_rooms.append(self.convert_from_chunk(room))
            self.template_list.append(
                RoomTemplate(template.name, template.comment, data_rooms)
            )
        self.level_list_panel.set_rooms(self.template_list)
        self.multi_room_editor_tab.open_lvl(
            self.lvl, self.lvl_biome, self.tile_palette_map, self.template_list
        )

    def load_full_preview(self):
        self.list_preview_tiles_ref = []
        # Sets default level size for levels that might not have a size variable like the challenge levels.
        # 8x8 is what I went with.
        level_height = 8
        level_width = 8

        # mag_full = int(self.slider_zoom_full.get())
        self.full_level_preview_canvas.clear()
        self.full_level_preview_canvas.set_zoom(self.mag_full)

        full_size = None
        if self.files_tree.has_selected_file():
            full_size = self.rules_tab.get_full_size()
            if full_size is not None:
                logger.debug("Size found: %s", full_size)
                level_height = int(full_size.split(", ")[1])
                level_width = int(full_size.split(", ")[0])
            self.full_level_preview_canvas.configure_size(
                level_width * 10, level_height * 8
            )
            self.full_level_preview_canvas.draw_background(self.lvl_biome)
            self.full_level_preview_canvas.draw_grid()
        else:
            self.full_level_preview_canvas.show_intro()
            return

        self.full_level_preview_canvas.hide_intro()

        def get_setrooms():
            setrooms = []
            for room_template in self.template_list:
                matched_template = Setroom.find_vanilla_setroom(room_template.name)
                if not matched_template:
                    continue

                setrooms.append(MatchedSetroomTemplate(room_template, matched_template))
            return setrooms

        for setroom_template in get_setrooms():
            room_x = setroom_template.setroom.coords.x
            room_y = setroom_template.setroom.coords.y

            logger.debug("%s", setroom_template.template.name)
            logger.debug("Room pos: %sx%s", room_x, room_y)

            room_instances = setroom_template.template.rooms
            if len(room_instances) != 0:
                room_instance = room_instances[0]

                for layer_index, layer in enumerate(
                    [room_instance.front, room_instance.back]
                ):
                    for currow, room_row in enumerate(layer):
                        tile_image_full = None
                        logger.debug("Room row: %s", room_row)
                        if TemplateSetting.ONLYFLIP in room_instance.settings:
                            room_row = room_row[::-1]
                        for curcol, tile in enumerate(room_row):
                            tile_name = ""
                            tiles = [
                                c
                                for c in self.tile_palette_ref_in_use
                                if str(" " + tile) in str(c[0])
                            ]
                            if tiles:
                                tile_name = str(tiles[-1][0]).split(" ", 1)[0]
                                new_ref = True
                                for preview_tile_ref in self.list_preview_tiles_ref:
                                    if tile_name == str(preview_tile_ref[0]):
                                        new_ref = False
                                        tile_image_full = preview_tile_ref[1]

                                if new_ref:
                                    tile_ref = []
                                    tile_image = ImageTk.PhotoImage(
                                        ImageTk.getimage(tiles[-1][1])
                                        .resize(
                                            (self.mag_full, self.mag_full),
                                            Image.Resampling.LANCZOS,
                                        )
                                        .convert("RGBA")
                                    )
                                    tile_ref.append(tile_name)
                                    tile_ref.append(tile_image)
                                    self.list_preview_tiles_ref.append(tile_ref)
                                    tile_image_full = self.list_preview_tiles_ref[
                                        len(self.list_preview_tiles_ref) - 1
                                    ][1]
                            else:
                                # There's a missing tile id somehow
                                logger.debug("%s Not Found", tile)

                            self.full_level_preview_canvas.replace_tile_at(
                                CanvasIndex(layer_index, 0),
                                room_y * 8 + currow,
                                room_x * 10 + curcol,
                                tile_image_full,
                                0,
                                0,
                            )

    def populate_tilecode_palette(self):
        self.palette_panel.update_with_palette(
            self.tile_palette_ref_in_use,
            None,
            self.lvl_biome,
            self.lvl,
        )
        self.multi_room_editor_tab.populate_tilecode_palette(
            self.tile_palette_ref_in_use, None
        )

    def palette_selected_tile(self, tile_name, image, is_primary):
        self.multi_room_editor_tab.select_tile(tile_name, image, is_primary)

    def multiroom_editor_selected_tile(self, tile_name, image, is_primary):
        self.palette_panel.select_tile(tile_name, image, is_primary)

    def multiroom_editor_modified_room(self, template_draw_item):
        if template_draw_item.room_chunk == self.current_selected_room:
            self.room_select(None)
        self.changes_made()

    def multiroom_editor_changed_filetree(self):
        self.level_list_panel.reset()
        self.level_list_panel.set_rooms(self.template_list)
        self.room_select(None)

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

    def convert_from_chunk(self, chunk):
        settings = list(map(lambda setting: setting, chunk.settings))

        def map_layer(layer):
            return list(map(lambda line: list(map(lambda tile: tile, line)), layer))

        foreground_tiles = map_layer(chunk.foreground)
        if len(chunk.background) > 0:
            background_tiles = map_layer(chunk.background)
        else:
            background_tiles = [
                ["0" for _ in range(len(row))] for row in foreground_tiles
            ]

        comment = str(chunk.comment).lstrip("/ ").strip()

        return RoomInstance(comment, settings, foreground_tiles, background_tiles)

    def convert_to_chunk(self, room_instance):
        bg = []
        if TemplateSetting.DUAL in room_instance.settings:
            bg = room_instance.back

        return Chunk(
            comment=room_instance.name,
            settings=room_instance.settings,
            foreground=room_instance.front,
            background=bg,
        )

    def get_level_templates(self):
        level_templates = LevelTemplates()

        def convert_level_template(template):
            return LevelTemplate(
                name=template.name,
                comment=template.comment,
                chunks=list(map(self.convert_to_chunk, template.rooms)),
            )

        for template in self.template_list:
            level_templates.set_obj(convert_level_template(template))

        return level_templates

    def save_changes(self):
        if self.save_needed:
            try:
                level_chances = self.rules_tab.get_level_chances()
                level_settings = self.rules_tab.get_level_settings()
                monster_chances = self.rules_tab.get_monster_chances()
                level_templates = self.get_level_templates()

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
                save_path = Path(self.lvls_path / self.files_tree.get_loaded_level())
                loaded_pack = self.files_tree.get_loaded_pack()
                backup_dir = (
                    str(self.packs_path).split("Pack")[0] + "Backups/" + loaded_pack
                )
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

    def setting_flip(self, setting, value):
        if value and not setting in self.current_selected_room.settings:
            self.current_selected_room.settings.append(setting)
        elif not value and setting in self.current_selected_room.settings:
            self.current_selected_room.settings.remove(setting)

        if setting == TemplateSetting.DUAL:
            self.canvas.hide_canvas(1, not value)

        self.changes_made()

    def canvas_click(
        self,
        canvas_index,
        row,
        column,
        is_primary,
    ):
        tile_name, tile_code = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, self.mag)

        self.canvas.replace_tile_at(
            canvas_index,
            row,
            column,
            self.tile_palette_map[tile_code][1],
            x_offset,
            y_offset,
        )

        self.tile_codes[canvas_index.canvas_index][row][column] = tile_code
        self.changes_made()

    def canvas_shiftclick(self, canvas_index, row, column, is_primary):
        tile_code = self.tile_codes[canvas_index.canvas_index][row][column]
        tile = self.tile_palette_map[tile_code]

        self.select_palette_tile(tile, is_primary)

    def select_palette_tile(self, tile, is_primary):
        self.palette_panel.select_tile(tile[0], tile[2], is_primary)
        self.multi_room_editor_tab.select_tile(tile[0], tile[2], is_primary)

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
                    and self.current_selected_room is None
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

    def replace_tiles(self, tile, new_tile, replace_where):
        def replace_room_chunk(room_chunk):
            for layer in room_chunk:
                for row_codes in layer:
                    for column, tile_code in enumerate(row_codes):
                        if tile_code == tile:
                            row_codes[column] = new_tile

        if replace_where == "all rooms":
            for template in self.template_list:
                for room_instance in template.rooms:
                    replace_room_chunk([room_instance.front, room_instance.back])
        else:
            replace_room_chunk(self.tile_codes)
        self.room_select(None)
        self.changes_made()

    def clear_canvas(self):
        msg_box = tk.messagebox.askquestion(
            "Clear Canvases?",
            "Completely clear your canvas? This isn't recoverable.",
            icon="warning",
        )
        if msg_box == "yes":
            for layer in self.tile_codes:
                for row_codes in layer:
                    for column, _ in enumerate(row_codes):
                        row_codes[column] = "0"
            self.canvas.clear()
            self.canvas.draw_background(self.lvl_biome)
            self.canvas.draw_grid()
            self.changes_made()

    def room_select(self, _event):  # Loads room when click if not parent node.
        dual_mode = False
        template_index, room_instance_index = self.level_list_panel.get_selected_room()
        if template_index is not None and room_instance_index is not None:
            self.canvas.clear()
            self.hide_intro()

            selected_room = self.template_list[template_index].rooms[
                room_instance_index
            ]
            self.current_selected_room = selected_room
            current_settings = []

            current_settings = selected_room.settings
            dual_mode = TemplateSetting.DUAL in current_settings
            self.level_settings_bar.set_dual(dual_mode)
            self.level_settings_bar.set_flip(TemplateSetting.FLIP in current_settings)
            self.level_settings_bar.set_purge(TemplateSetting.PURGE in current_settings)
            self.level_settings_bar.set_only_flip(
                TemplateSetting.ONLYFLIP in current_settings
            )
            self.level_settings_bar.set_ignore(
                TemplateSetting.IGNORE in current_settings
            )
            self.level_settings_bar.set_rare(TemplateSetting.RARE in current_settings)
            self.level_settings_bar.set_hard(TemplateSetting.HARD in current_settings)
            self.level_settings_bar.set_liquid(
                TemplateSetting.LIQUID in current_settings
            )

            self.canvas.configure_size(
                len(selected_room.front[0]),
                len(selected_room.front),
            )

            # Draw lines to fill the size of the level.
            self.canvas.draw_background(self.lvl_biome)
            self.canvas.draw_grid()

            self.canvas.hide_canvas(1, not dual_mode)

            self.tile_codes = [
                selected_room.front,
                selected_room.back,
            ]

            for canvas_index, layer_tile_codes in enumerate(self.tile_codes):
                for row_index, row in enumerate(layer_tile_codes):
                    for column_index, tile_code in enumerate(row):
                        tile_name = ""
                        tiles = [
                            c
                            for c in self.tile_palette_ref_in_use
                            if str(" " + tile_code) in str(c[0])
                        ]
                        if tiles:
                            tile_image = tiles[-1][1]
                            tile_name = str(tiles[-1][0]).split(" ", 1)[0]
                        else:
                            # There's a missing tile id somehow
                            logger.debug("%s Not Found", tile_code)
                        x_coord, y_coord = self.texture_fetcher.adjust_texture_xy(
                            tile_image.width(),
                            tile_image.height(),
                            tile_name,
                        )
                        self.canvas.replace_tile_at(
                            CanvasIndex(0, canvas_index),
                            row_index,
                            column_index,
                            tile_image,
                            x_coord,
                            y_coord,
                        )
            self.canvas.update_scroll_region(not self.room_has_been_selected)
            self.room_has_been_selected = True
        else:
            self.canvas.clear()
            self.canvas.hide_canvas(1, True)
            self.show_intro()
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
            self.texture_fetcher.get_texture(
                new_tile_code, self.lvl_biome, self.lvl, scale
            )
        )
        tile_image_picker = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(
                new_tile_code, self.lvl_biome, self.lvl, 40
            )
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

    def on_insert_room(self, parent_index, name=None):
        room_template = self.template_list[parent_index]
        # Set default prompt based on parent name
        roomsize_key = "normal: 10x8"
        parent_room_type = room_template.name
        for room_size_text, room_type in ROOM_TYPES.items():
            if parent_room_type.startswith(room_type.name):
                roomsize_key = room_size_text
                break

        room_type = ROOM_TYPES[roomsize_key]
        front_layer = [
            ["0" for _ in range(room_type.x_size)] for _ in range(room_type.y_size)
        ]
        back_layer = [
            ["0" for _ in range(room_type.x_size)] for _ in range(room_type.y_size)
        ]
        new_room = RoomInstance(name or "new room", [], front_layer, back_layer)
        room_template.rooms.append(new_room)
        self.changes_made()
        return new_room

    def on_duplicate_room(self, parent_index, room_index):
        room_template = self.template_list[parent_index]
        room_instance = room_template.rooms[room_index]
        new_settings = list(map(lambda setting: setting, room_instance.settings))

        def map_layer(layer):
            return [[t for t in row] for row in layer]

        new_room = RoomInstance(
            (room_instance.name or "room") + " COPY",
            new_settings,
            map_layer(room_instance.front),
            map_layer(room_instance.back),
        )
        room_template.rooms.append(new_room)
        self.changes_made()
        return new_room

    def on_delete_room(self, parent_index, room_index):
        room_template = self.template_list[parent_index]
        if room_template.rooms[room_index] == self.current_selected_room:
            self.canvas.clear()
            self.show_intro()
        del room_template.rooms[room_index]
        self.changes_made()
        self.multi_room_editor_tab.room_was_deleted(parent_index, room_index)

    def on_copy_room(self, parent_index, room_index):
        room_template = self.template_list[parent_index]
        room_instance = room_template.rooms[room_index]
        chunk = self.convert_to_chunk(room_instance)
        output = io.StringIO()
        chunk.write(output)
        pyperclip.copy(output.getvalue())
        output.close()

    def on_paste_room(self, parent_index):
        data = pyperclip.paste().encode("utf-8").decode("cp1252")
        if data is not None and len(data) > 0:
            input_text = io.StringIO(initial_value=data)
            chunk = Chunk.parse(input_text)

            room_template = self.template_list[parent_index]
            new_room = self.convert_from_chunk(chunk)
            room_template.rooms.append(new_room)
            self.changes_made()
            return new_room

    def on_rename_room(self, parent_index, room_index, new_name):
        room_template = self.template_list[parent_index]
        room_instance = room_template.rooms[room_index]
        room_instance.name = new_name

    def reset_canvas(self):
        self.canvas.clear()

    def load_packs(self):
        self.reset()
        self.files_tree.load_packs()

    def show_intro(self):
        self.canvas.show_intro()
        self.editor_tab.columnconfigure(8, minsize=0)

    def hide_intro(self):
        self.canvas.hide_intro()
        self.editor_tab.columnconfigure(8, minsize=17)

    def reset(self):
        logger.debug("Resetting...")
        self.level_list_panel.reset()
        try:
            self.palette_panel.reset()
            self.full_level_preview_canvas.show_intro()
            self.full_level_preview_canvas.clear()
            self.show_intro()
            self.canvas.clear()
            self.tile_palette_map = {}
            self.tile_palette_ref_in_use = None
            self.lvl = None
            self.lvl_biome = None
            self.full_level_preview_canvas.clear()
            self.reset_save_button()
        except Exception:  # pylint: disable=broad-except
            logger.debug("canvas does not exist yet")
