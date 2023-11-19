from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from modlunky2.config import Config
from modlunky2.levels.level_templates import TemplateSetting
from modlunky2.ui.levels.shared.multi_canvas_container import MultiCanvasContainer
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import Setroom, MatchedSetroom
from modlunky2.ui.levels.vanilla_levels.multi_room.room_map import find_roommap
from modlunky2.ui.levels.vanilla_levels.multi_room.template_draw_item import (
    TemplateDrawItem,
)
from modlunky2.ui.levels.vanilla_levels.vanilla_types import (
    RoomInstance,
    RoomTemplate,
    MatchedSetroomTemplate,
)


class MultiRoomEditorTab(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config: Config,
        texture_fetcher,
        textures_dir,
        on_add_tilecode,
        on_delete_tilecode,
        on_select_palette_tile,
        on_modify_room,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.texture_fetcher = texture_fetcher

        #   self.on_edit_room = on_edit_room
        self.on_add_tilecode = on_add_tilecode
        self.on_delete_tilecode = on_delete_tilecode
        self.on_select_palette_tile = on_select_palette_tile
        self.on_modify_room = on_modify_room

        self.lvl = None
        self.lvl_biome = None
        self.tile_palette_map = {}
        self.room_templates = []
        self.template_draw_map = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # View that contains the canvases to edit the level along with some controls.
        editor_view = tk.Frame(self)
        editor_view.grid(row=0, column=0, sticky="news")
        self.editor_container = editor_view

        editor_view.columnconfigure(0, weight=1)
        editor_view.columnconfigure(2, minsize=0)
        editor_view.columnconfigure(1, minsize=50)
        editor_view.rowconfigure(1, weight=1)

        self.canvas = MultiCanvasContainer(
            editor_view,
            textures_dir,
            ["Foreground", "Background"],
            50,
            self.canvas_click,
            self.canvas_shiftclick,
            intro_text="Select a level file to begin viewing",
        )
        self.canvas.grid(row=0, column=0, columnspan=3, rowspan=2, sticky="news")
        self.canvas.show_intro()

        # Side panel with the tile palette and level settings.
        side_panel = tk.Frame(self)
        side_panel.grid(column=1, row=0, rowspan=2, sticky="news")
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
            self.palette_selected_tile,
            self.texture_fetcher,
            self.texture_fetcher.sprite_fetcher,
        )
        # self.options_panel = OptionsPanel(
        #     side_panel_tab_control,
        #     modlunky_config,
        #     self.zoom_level,
        #     self.select_theme,
        #     self.update_level_size,
        #     self.set_current_save_format,
        #     self.canvas.hide_grid_lines,
        #     self.canvas.hide_room_lines,
        #     self.update_zoom,
        # )
        side_panel_tab_control.add(self.palette_panel, text="Tiles")
        # side_panel_tab_control.add(self.options_panel, text="Settings")

    def open_lvl(self, lvl, biome, tile_palette_map, room_templates):
        self.lvl = lvl
        self.lvl_biome = biome
        self.tile_palette_map = tile_palette_map
        self.room_templates = room_templates

        self.canvas.clear()
        self.show_intro()
        self.template_draw_map = find_roommap(room_templates)
        self.draw_canvas()

    def redraw(self):
        self.canvas.clear()
        self.show_intro()
        self.draw_canvas()

    def populate_tilecode_palette(self, tile_palette, suggestions):
        self.palette_panel.update_with_palette(
            tile_palette,
            suggestions,
            self.lvl_biome,
            self.lvl,
        )

    def palette_selected_tile(self, tile_name, image, is_primary):
        self.on_select_palette_tile(tile_name, image, is_primary)

    def select_tile(self, tile_name, image, is_primary):
        self.palette_panel.select_tile(tile_name, image, is_primary)

    def add_tilecode(self, tile, percent, alt_tile):
        self.on_add_tilecode(tile, percent, alt_tile)

    def delete_tilecode(self, tile_name, tile_code):
        self.on_delete_tilecode(tile_name, tile_code)

    def canvas_click(self, canvas_index, row, column, is_primary):
        tile_name, tile_code = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, 50)

        self.canvas.replace_tile_at(
            canvas_index,
            row,
            column,
            self.tile_palette_map[tile_code][1],
            x_offset,
            y_offset,
        )

        room_row, room_col = row // 8, column // 10
        template_draw_item = self.template_draw_map[room_row][room_col]
        chunk = template_draw_item.room_chunk
        layer = [chunk.front, chunk.back][canvas_index]
        tile_row = row - room_row * 8
        tile_col = column - room_col * 10
        if TemplateSetting.ONLYFLIP in chunk.settings:
            tile_col = 9 - tile_col
        layer[tile_row][tile_col] = tile_code
        self.on_modify_room(template_draw_item)

    def canvas_shiftclick(self, canvas_index, row, column, is_primary):
        room_row, room_col = row // 8, column // 10
        template_draw_item = self.template_draw_map[room_row][room_col]
        chunk = template_draw_item.room_chunk
        layer = [chunk.front, chunk.back][canvas_index]
        tile_row = row - room_row * 8
        tile_col = column - room_col * 10
        if TemplateSetting.ONLYFLIP in chunk.settings:
            tile_col = 9 - tile_col

        tile_code = layer[tile_row][tile_col]
        tile = self.tile_palette_map[tile_code]

        self.palette_panel.select_tile(tile[0], tile[2], is_primary)
        self.on_select_palette_tile(tile[0], tile[2], is_primary)

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile_name, tile_code, tile_size):
        tile_ref = self.tile_palette_map[tile_code]
        if tile_ref:
            img = tile_ref[1]
            return self.texture_fetcher.adjust_texture_xy(
                img.width(), img.height(), tile_name, tile_size
            )

        return 0, 0

    def show_intro(self):
        self.canvas.show_intro()
        self.editor_container.columnconfigure(2, minsize=0)

    def hide_intro(self):
        self.canvas.hide_intro()
        self.editor_container.columnconfigure(2, minsize=17)

    def draw_canvas(self):
        if len(self.template_draw_map) == 0:
            return
        if len(self.template_draw_map[0]) == 0:
            return
        height = len(self.template_draw_map)
        width = len(self.template_draw_map[0])

        self.canvas.clear()
        self.hide_intro()
        self.canvas.configure_size(width * 10, height * 8)

        self.canvas.draw_background(self.lvl_biome)
        self.canvas.draw_grid(2)
        self.canvas.draw_room_grid(2)

        # Draws all of the images of a layer on its canvas, and stores the images in
        # the proper index of tile_images so they can be removed from the grid when
        # replaced with another tile.
        def draw_chunk(canvas_index, chunk_start_x, chunk_start_y, tile_codes):
            for row_index, room_row in enumerate(tile_codes):
                if row_index + chunk_start_y >= height * 8:
                    continue
                for tile_index, tile in enumerate(room_row):
                    if tile_index + chunk_start_x >= width * 10:
                        continue
                    tilecode = self.tile_palette_map[tile]
                    tile_name = tilecode[0].split(" ", 1)[0]
                    tile_image = tilecode[1]
                    x_offset, y_offset = self.texture_fetcher.adjust_texture_xy(
                        tile_image.width(),
                        tile_image.height(),
                        tile_name,
                        50,  # self.zoom_level
                    )
                    self.canvas.replace_tile_at(
                        canvas_index,
                        row_index + chunk_start_y,
                        tile_index + chunk_start_x,
                        tile_image,
                        x_offset,
                        y_offset,
                    )

        for room_row_index, room_row in enumerate(self.template_draw_map):
            for room_column_index, template_draw_item in enumerate(room_row):
                if template_draw_item:
                    chunk = template_draw_item.room_chunk
                    front = chunk.front
                    back = chunk.back
                    if TemplateSetting.ONLYFLIP in chunk.settings:
                        front = list(map(lambda row: row[::-1], front))
                        back = list(map(lambda row: row[::-1], back))
                    draw_chunk(0, room_column_index * 10, room_row_index * 8, front)
                    if TemplateSetting.DUAL in chunk.settings:
                        draw_chunk(1, room_column_index * 10, room_row_index * 8, back)
                    else:
                        self.canvas.draw_background_over_room(1, self.lvl_biome, room_row_index, room_column_index)
                else:
                    self.canvas.draw_background_over_room(0, self.lvl_biome, room_row_index, room_column_index)
                    self.canvas.draw_background_over_room(1, self.lvl_biome, room_row_index, room_column_index)
