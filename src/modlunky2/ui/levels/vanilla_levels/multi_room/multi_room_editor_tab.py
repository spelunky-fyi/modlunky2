from dataclasses import dataclass
import math
from PIL import Image, ImageTk
import random
import tkinter as tk
from tkinter import ttk

from modlunky2.config import Config
from modlunky2.levels.level_templates import TemplateSetting
from modlunky2.ui.levels.shared.level_canvas import GridRoom
from modlunky2.ui.levels.shared.multi_canvas_container import (
    MultiCanvasContainer,
    CanvasIndex,
)
from modlunky2.ui.levels.shared.palette_panel import PalettePanel
from modlunky2.ui.levels.shared.setrooms import Setroom, MatchedSetroom
from modlunky2.ui.levels.vanilla_levels.multi_room.options_panel import OptionsPanel
from modlunky2.ui.levels.vanilla_levels.multi_room.reversed_rooms import REVERSED_ROOMS
from modlunky2.ui.levels.vanilla_levels.multi_room.room_map import (
    find_roommap,
    get_template_draw_item,
    RoomMap,
)
from modlunky2.ui.levels.vanilla_levels.multi_room.template_draw_item import (
    TemplateDrawItem,
)
from modlunky2.ui.levels.vanilla_levels.vanilla_types import (
    RoomInstance,
    RoomTemplate,
    MatchedSetroomTemplate,
)
from modlunky2.ui.widgets import PopupWindow


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
        on_use_dependency_tile,
        on_modify_room,
        on_change_filetree,
        on_add_room,
        on_duplicate_room,
        on_rename_room,
        on_delete_room,
        on_create_template,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.texture_fetcher = texture_fetcher
        self.textures_dir = textures_dir

        self.on_add_tilecode = on_add_tilecode
        self.on_delete_tilecode = on_delete_tilecode
        self.on_select_palette_tile = on_select_palette_tile
        self.on_modify_room = on_modify_room
        self.on_change_filetree = on_change_filetree
        self.on_add_room = on_add_room
        self.on_duplicate_room = on_duplicate_room
        self.on_rename_room = on_rename_room
        self.on_delete_room = on_delete_room
        self.on_create_template = on_create_template

        self.lvl = None
        self.lvl_biome = None
        self.tile_palette_map = {}
        self.tile_image_map = {}
        self.room_templates = []
        self.template_draw_map = []
        self.default_draw_map = None
        self.reverse_layers = True

        self.zoom_level = 30  # Sensible default.

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
            [],
            self.zoom_level,
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
        side_panel_hide_button.grid(column=1, row=0, sticky="new")
        self.side_panel_hide_button = side_panel_hide_button

        side_panel_tab_control = ttk.Notebook(side_panel)
        side_panel_tab_control.grid(row=0, column=0, sticky="news")

        self.palette_panel = PalettePanel(
            side_panel_tab_control,
            self.delete_tilecode,
            self.add_tilecode,
            self.palette_selected_tile,
            on_use_dependency_tile,
            self.texture_fetcher,
            self.texture_fetcher.sprite_fetcher,
        )
        self.options_panel = OptionsPanel(
            side_panel_tab_control,
            modlunky_config,
            self.zoom_level,
            self.hide_grid_lines,
            self.hide_room_lines,
            self.__update_zoom_internal,
            self.use_roommap_at,
            self.change_template_at,
            self.clear_template_at,
            self.create_new_template,
            self.change_room_at,
            self.select_random_room,
            self.room_setting_change_at,
            self.duplicate_room,
            self.rename_room,
            self.delete_room,
            self.toggle_reverse_layers,
        )
        side_panel_tab_control.add(self.palette_panel, text="Tiles")
        side_panel_tab_control.add(self.options_panel, text="Settings")

    def image_for_tile_code(self, tile_code):
        tile_name = self.tile_palette_map[tile_code][0].split(" ", 2)[0]

        if tile_name in self.tile_image_map:
            return self.tile_image_map[tile_name]

        new_tile_image = ImageTk.PhotoImage(
            self.texture_fetcher.get_texture(
                tile_name, self.lvl_biome, self.lvl, self.zoom_level
            )
        )

        self.tile_image_map[tile_name] = new_tile_image
        return new_tile_image

    def use_roommap_at(self, index, fresh=False):
        if self.lvl is None:
            return

        def template_draw_map_for_roommap(room_map):
            def get_template_draw_item_named(template_name):
                if template_name is None:
                    return None
                for index, template in enumerate(self.room_templates):
                    if template_name == template.name:
                        return get_template_draw_item(template, index)

                return None

            mappy = []
            for segment in room_map.segments:
                mappy.append(
                    RoomMap(
                        segment.name,
                        [
                            [
                                get_template_draw_item_named(template_name)
                                for template_name in row
                            ]
                            for row in segment.templates
                        ],
                    )
                )
            return mappy

        room_maps = self.modlunky_config.custom_room_maps.get(self.lvl)
        if index is None or index == -1 or index >= len(room_maps):
            self.template_draw_map = self.default_draw_map
        else:
            self.template_draw_map = template_draw_map_for_roommap(room_maps[index])

        self.canvas.grid_remove()

        self.canvas = MultiCanvasContainer(
            self.editor_container,
            self.textures_dir,
            ["Foreground", "Background"],
            [room.name for room in self.template_draw_map],
            self.zoom_level,
            self.canvas_click,
            self.canvas_shiftclick,
            intro_text="Select a level file to begin viewing",
            vertical=True,
        )
        self.canvas.grid(row=0, column=0, columnspan=3, rowspan=2, sticky="news")
        self.side_panel_hide_button.tkraise()
        self.canvas.show_intro()
        self.canvas.clear()
        self.show_intro()

        self.options_panel.reset()
        self.options_panel.set_lvl(self.lvl)
        self.options_panel.set_templates(self.template_draw_map, self.room_templates)
        self.draw_canvas(fresh)

    def open_lvl(self, lvl, biome, tile_palette_map, room_templates):
        self.lvl = lvl
        self.lvl_biome = biome
        self.tile_palette_map = tile_palette_map
        self.tile_image_map = {}
        self.room_templates = room_templates

        self.default_draw_map = find_roommap(room_templates)
        # self.template_draw_map = find_roommap(room_templates)

        self.use_roommap_at(
            self.modlunky_config.default_custom_room_maps.get(self.lvl), True
        )

    def redraw(self):
        self.canvas.clear()
        self.show_intro()
        self.draw_canvas(False)

    def toggle_reverse_layers(self, reverse):
        self.reverse_layers = reverse
        self.redraw()

    def update_templates(self, templates=None):
        # if templates is not None:
        #     self.room_templates = templates
        self.options_panel.set_templates(self.template_draw_map, self.room_templates)

    def hide_grid_lines(self, hide_grid_lines):
        self.canvas.hide_grid_lines(hide_grid_lines)

    def hide_room_lines(self, hide_room_lines):
        self.canvas.hide_room_lines(hide_room_lines)

    def update_zoom_level(self, zoom):
        self.options_panel.update_zoom_level(zoom)
        self.__set_zoom(zoom)

    def __update_zoom_internal(self, zoom):
        self.__set_zoom(zoom)

    def __set_zoom(self, zoom):
        self.zoom_level = zoom
        self.canvas.set_zoom(zoom)
        self.tile_image_map = {}
        self.redraw()

    def __get_chunk_for_template_draw_item(
        self, template, template_index, map_index, row, column
    ):
        chunk_index = None
        if len(template.rooms) == 0:
            return None, None
        valid_rooms = [
            index
            for index, room in enumerate(template.rooms)
            if TemplateSetting.IGNORE not in room.settings
        ]

        if row is not None and column is not None:
            for i in valid_rooms:
                room_used = False
                for m, draw_map in enumerate(self.template_draw_map):
                    for r, room_row in enumerate(draw_map.rooms):
                        for c, room in enumerate(room_row):
                            if room is None:
                                continue
                            if r == row and c == column and m == map_index:
                                continue
                            if (
                                room.template_index == template_index
                                and room.room_index == i
                            ):
                                room_used = True
                                break
                        if room_used:
                            break

                if not room_used:
                    chunk_index = i
                    break

        if chunk_index is None:
            if len(valid_rooms) > 0:
                chunk_index = valid_rooms[0]
            else:
                return None, None

        chunk = template.rooms[chunk_index]
        return chunk_index, chunk

    def __get_template_draw_item(
        self, template, template_index, map_index, row, column
    ):
        chunk_index, chunk = self.__get_chunk_for_template_draw_item(
            template, template_index, map_index, row, column
        )
        if chunk is None or len(chunk.front) == 0:
            return None
        return TemplateDrawItem(
            template,
            template_index,
            chunk,
            chunk_index,
            int(math.ceil(len(chunk.front[0]) / 10)),
            int(math.ceil(len(chunk.front) / 8)),
        )

    def change_template_at(self, map_index, row, col, template, template_index):
        template_draw_item = self.__get_template_draw_item(
            template, template_index, map_index, row, col
        )
        if template_draw_item:
            if template_draw_item.width_in_rooms + col > 10:
                win = PopupWindow("Cannot use this room template", self.modlunky_config)
                lbl = ttk.Label(
                    win,
                    text="Using this template here will result in the map exceeding the maximum width.",
                )
                lbl.grid(row=0, column=0)

                ok_button = ttk.Button(win, text="OK", command=win.destroy)
                ok_button.grid(row=1, column=0, pady=5, sticky="news")
                return

            overlaps_room = False
            for row_offset in range(template_draw_item.height_in_rooms):
                for col_offset in range(template_draw_item.width_in_rooms):
                    if row_offset == 0 and col_offset == 0:
                        continue
                    (
                        template,
                        overlapping_row,
                        overlapping_column,
                    ) = self.template_item_at(
                        map_index, row + row_offset, col + col_offset
                    )
                    if template is not None and (
                        overlapping_row != row or overlapping_column != col
                    ):
                        overlaps_room = True

            def update_template():
                def expand_to_height_if_necessary(room_map, height):
                    if len(room_map) < height:
                        for _ in range(height - len(room_map)):
                            if len(room_map) == 0:
                                room_map.append([None])
                            else:
                                room_map.append([None for _ in range(len(room_map[0]))])

                def expand_to_width_if_necessary(room_map, width):
                    for row in room_map:
                        if len(row) < width:
                            for _ in range(width - len(row)):
                                row.append(None)

                expand_to_height_if_necessary(
                    self.template_draw_map[map_index].rooms,
                    row + template_draw_item.height_in_rooms,
                )
                expand_to_width_if_necessary(
                    self.template_draw_map[map_index].rooms,
                    col + template_draw_item.width_in_rooms,
                )
                for row_offset in range(template_draw_item.height_in_rooms):
                    for col_offset in range(template_draw_item.width_in_rooms):
                        if row_offset == 0 and col_offset == 0:
                            continue
                        _, overlapping_row, overlapping_column = self.template_item_at(
                            map_index, row + row_offset, col + col_offset
                        )
                        if overlapping_row is None or overlapping_column is None:
                            continue
                        self.template_draw_map[map_index].rooms[overlapping_row][
                            overlapping_column
                        ] = None

                self.template_draw_map[map_index].rooms[row][col] = template_draw_item
                while len(self.template_draw_map[map_index].rooms) > 0:
                    has_room = False
                    r = len(self.template_draw_map[map_index].rooms) - 1
                    for c in range(len(self.template_draw_map[map_index].rooms[r])):
                        t, _, _ = self.template_item_at(map_index, r, c)
                        if t is not None:
                            has_room = True
                            break
                    if has_room:
                        break

                    self.template_draw_map[map_index].rooms.pop()

                while (
                    len(self.template_draw_map[map_index].rooms) > 0
                    and len(self.template_draw_map[map_index].rooms[0]) > 0
                ):
                    has_room = False
                    for r in range(len(self.template_draw_map[map_index].rooms)):
                        c = len(self.template_draw_map[map_index].rooms[r]) - 1
                        t, _, _ = self.template_item_at(map_index, r, c)
                        if t is not None:
                            has_room = True
                            break
                    if has_room:
                        break

                    for r in self.template_draw_map[map_index].rooms:
                        r.pop()

                self.options_panel.set_templates(
                    self.template_draw_map, self.room_templates
                )
                self.redraw()

            if overlaps_room:
                win = PopupWindow("Warning", self.modlunky_config)

                def update_then_destroy():
                    update_template()
                    win.destroy()

                lbl = ttk.Label(
                    win,
                    text="Using this template here will remove some other templates.",
                )
                lbl.grid(row=0, column=0)
                lbl2 = ttk.Label(win, text="Proceed anyway?")
                lbl2.grid(row=1, column=0)

                separator = ttk.Separator(win)
                separator.grid(row=2, column=0, columnspan=3, pady=5, sticky="news")

                buttons = ttk.Frame(win)
                buttons.grid(row=3, column=0, columnspan=2, sticky="news")
                buttons.columnconfigure(0, weight=1)
                buttons.columnconfigure(1, weight=1)

                ok_button = ttk.Button(
                    buttons, text="Proceed", command=update_then_destroy
                )
                ok_button.grid(row=0, column=0, pady=5, sticky="news")

                cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
                cancel_button.grid(row=0, column=1, pady=5, sticky="news")

            else:
                update_template()

    def clear_template_at(self, map_index, row, col):
        current_map = self.template_draw_map[map_index].rooms
        current_map[row][col] = None

        while len(current_map) > 0:
            has_room = False
            r = len(current_map) - 1
            for c in range(len(current_map[r])):
                t, _, _ = self.template_item_at(map_index, r, c)
                if t is not None:
                    has_room = True
                    break
            if has_room:
                break

            current_map.pop()

        while len(current_map) > 0 and len(current_map[0]) > 0:
            has_room = False
            for r in range(len(current_map)):
                c = len(current_map[r]) - 1
                t, _, _ = self.template_item_at(map_index, r, c)
                if t is not None:
                    has_room = True
                    break
            if has_room:
                break

            for r in current_map:
                r.pop()

        self.options_panel.set_templates(self.template_draw_map, self.room_templates)
        self.redraw()

    def create_new_template(self, name, comment, width, height):
        return self.on_create_template(name, comment, width, height)

    def select_random_room(self, map_index=None, row=None, col=None):
        def select_random_room_at(mi, r, c):
            template_item = self.template_draw_map[mi].rooms[r][c]
            if template_item is None:
                return

            valid_rooms = [
                index
                for index, room in enumerate(template_item.template.rooms)
                if TemplateSetting.IGNORE not in room.settings
            ]

            if len(valid_rooms) == 0:
                return

            chunk_index = random.choice(valid_rooms)
            chunk = template_item.template.rooms[chunk_index]

            if chunk is not None:
                template_item.room_index = chunk_index
                template_item.room_chunk = chunk

        if map_index is None or row is None or col is None:
            for mi, tmap in enumerate(self.template_draw_map):
                for r, row in enumerate(tmap.rooms):
                    for c, room in enumerate(row):
                        select_random_room_at(mi, r, c)
        else:
            select_random_room_at(map_index, row, col)

        self.options_panel.set_templates(self.template_draw_map, self.room_templates)
        self.redraw()

    def change_room_at(self, room_index, map_index, row, col):
        template_item = self.template_draw_map[map_index].rooms[row][col]

        if template_item is None:
            return

        if room_index >= len(template_item.template.rooms):
            win = PopupWindow("Add Room", self.modlunky_config)

            lbl = ttk.Label(
                win,
                text="Create a new room in " + template_item.template.name + ".",
            )
            lbl.grid(row=0, column=0)

            values_frame = tk.Frame(win)
            values_frame.grid(row=1, column=0, sticky="nw")

            name_label = tk.Label(values_frame, text="Name: ")
            name_label.grid(row=0, column=0, sticky="ne", pady=2)

            name_entry = tk.Entry(values_frame)
            name_entry.grid(row=0, column=1, sticky="new", pady=2)

            separator = ttk.Separator(win)
            separator.grid(row=2, column=0, columnspan=3, pady=5, sticky="news")

            buttons = ttk.Frame(win)
            buttons.grid(row=3, column=0, columnspan=2, sticky="news")
            buttons.columnconfigure(0, weight=1)
            buttons.columnconfigure(1, weight=1)

            def insert_then_destroy():
                name = name_entry.get()
                new_room = self.on_add_room(
                    template_item.template_index, None if name == "" else name
                )

                template_item.room_index = room_index
                template_item.room_chunk = new_room

                self.options_panel.set_templates(
                    self.template_draw_map, self.room_templates
                )
                self.redraw()
                win.destroy()

            ok_button = ttk.Button(buttons, text="Create", command=insert_then_destroy)
            ok_button.grid(row=0, column=0, pady=5, sticky="news")

            cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
            cancel_button.grid(row=0, column=1, pady=5, sticky="news")

            return

        template_item.room_index = room_index
        template_item.room_chunk = template_item.template.rooms[room_index]

        self.options_panel.set_templates(self.template_draw_map, self.room_templates)
        self.redraw()

    def duplicate_room(self, map_index, row, col):
        template_item = self.template_draw_map[map_index].rooms[row][col]
        new_room = self.on_duplicate_room(
            template_item.template_index, template_item.room_index
        )

        template_item.room_index = len(template_item.template.rooms) - 1
        template_item.room_chunk = new_room

        self.options_panel.set_templates(self.template_draw_map, self.room_templates)
        self.redraw()

        self.on_change_filetree()

    def rename_room(self, map_index, row, col):
        win = PopupWindow("Edit Name", self.modlunky_config)

        template_item = self.template_draw_map[map_index].rooms[row][col]

        item_name = ""
        item_name = template_item.room_chunk.name or ""

        col1_lbl = ttk.Label(win, text="Name: ")
        col1_ent = ttk.Entry(win)
        col1_ent.insert(0, item_name)  # Default to rooms current name
        col1_lbl.grid(row=0, column=0, padx=2, pady=2, sticky="nse")
        col1_ent.grid(row=0, column=1, padx=2, pady=2, sticky="news")

        def update_then_destroy():
            if col1_ent.get() != "":
                self.on_rename_room(
                    template_item.template_index,
                    template_item.room_index,
                    col1_ent.get(),
                )
                self.options_panel.set_templates(
                    self.template_draw_map, self.room_templates
                )

                self.on_change_filetree()

                win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=1, column=0, columnspan=2, pady=5, sticky="news")

        buttons = ttk.Frame(win)
        buttons.grid(row=2, column=0, columnspan=2, sticky="news")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Rename", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="news")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="news")

    def delete_room(self, map_index, row, col):
        template_item = self.template_draw_map[map_index].rooms[row][col]

        win = PopupWindow("Delete Room", self.modlunky_config)

        def delete_then_destroy():
            self.on_delete_room(template_item.template_index, template_item.room_index)

            self.on_change_filetree()

            win.destroy()

        lbl2 = ttk.Label(win, text="Are you sure you want to delete this room?")
        lbl2.grid(row=0, column=0)

        separator = ttk.Separator(win)
        separator.grid(row=1, column=0, columnspan=3, pady=5, sticky="news")

        buttons = ttk.Frame(win)
        buttons.grid(row=2, column=0, columnspan=2, sticky="news")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Delete", command=delete_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="news")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="news")

    def room_setting_change_at(self, setting, value, map_index, row, col):
        template_item = self.template_draw_map[map_index].rooms[row][col]

        if template_item is None:
            return

        room = template_item.room_chunk
        if value and not setting in room.settings:
            room.settings.append(setting)
        elif not value and setting in room.settings:
            room.settings.remove(setting)

        self.on_modify_room(template_item)
        if setting == TemplateSetting.DUAL or setting == TemplateSetting.ONLYFLIP:
            self.redraw()

    def populate_tilecode_palette(self, tile_palette, suggestions, dependency_tiles):
        self.palette_panel.update_with_palette(
            tile_palette,
            suggestions,
            dependency_tiles,
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

    def room_was_deleted(self, template_index, chunk_index):
        replaced = False
        for map_index, template_map in enumerate(self.template_draw_map):
            for row, template_row in enumerate(template_map.rooms):
                for col, template in enumerate(template_row):
                    if template is None:
                        continue
                    if (
                        template.template_index == template_index
                        and template.room_index == chunk_index
                    ):
                        new_draw_item = self.__get_template_draw_item(
                            template.template, template_index, map_index, row, col
                        )
                        template_row[col] = new_draw_item
                        replaced = True
                    elif (
                        template.template_index == template_index
                        and template.room_index > chunk_index
                    ):
                        template.room_index -= 1
        if replaced:
            self.options_panel.set_templates(
                self.template_draw_map, self.room_templates
            )
            self.redraw()

    def canvas_click(self, canvas_index, row, column, is_primary):
        room_row, room_col = row // 8, column // 10
        template_draw_item, room_row, room_col = self.template_item_at(
            canvas_index.canvas_index, room_row, room_col
        )

        if template_draw_item is None:
            # Do not draw on empty room.
            return

        chunk = template_draw_item.room_chunk

        backlayer_canvas = 1
        if self.reverse_layers and template_draw_item.template.name in REVERSED_ROOMS:
            backlayer_canvas = 0

        if (
            canvas_index.tab_index == backlayer_canvas
            and TemplateSetting.DUAL not in chunk.settings
        ):
            # Do not draw on backlayer of non-dual room.
            return

        tile_name, tile_code = self.palette_panel.selected_tile(is_primary)
        x_offset, y_offset = self.offset_for_tile(tile_name, tile_code, self.zoom_level)

        layers = [chunk.front, chunk.back]
        if self.reverse_layers and template_draw_item.template.name in REVERSED_ROOMS:
            layers = [chunk.back, chunk.front]
        layer = layers[canvas_index.tab_index]
        tile_row = row - room_row * 8
        tile_col = column - room_col * 10
        data_tile_col = tile_col
        if TemplateSetting.ONLYFLIP in chunk.settings:
            data_tile_col = template_draw_item.width_in_rooms * 10 - 1 - tile_col
        layer[tile_row][data_tile_col] = tile_code
        self.on_modify_room(template_draw_item)

        for map_index, template_map in enumerate(self.template_draw_map):
            for r, room_rows in enumerate(template_map.rooms):
                for c, other_template_draw_item in enumerate(room_rows):
                    if other_template_draw_item is None:
                        continue
                    if (
                        template_draw_item.template_index
                        == other_template_draw_item.template_index
                        and template_draw_item.room_index
                        == other_template_draw_item.room_index
                    ):
                        self.canvas.replace_tile_at(
                            CanvasIndex(canvas_index.tab_index, map_index),
                            tile_row + r * 8,
                            tile_col + c * 10,
                            self.image_for_tile_code(tile_code),
                            x_offset,
                            y_offset,
                        )

    def canvas_shiftclick(self, canvas_index, row, column, is_primary):
        room_row, room_col = row // 8, column // 10
        template_draw_item, room_row, room_col = self.template_item_at(
            canvas_index.canvas_index, room_row, room_col
        )

        if template_draw_item is None:
            # Do not attempt to pull tile from empty room.
            return

        chunk = template_draw_item.room_chunk

        backlayer_canvas = 1
        if self.reverse_layers and template_draw_item.template.name in REVERSED_ROOMS:
            backlayer_canvas = 0

        if (
            canvas_index.tab_index == backlayer_canvas
            and TemplateSetting.DUAL not in chunk.settings
        ):
            # Do not attempt to pull tile from backlayer of non-dual room.
            return

        layers = [chunk.front, chunk.back]
        if self.reverse_layers and template_draw_item.template.name in REVERSED_ROOMS:
            layers = [chunk.back, chunk.front]
        layer = layers[canvas_index.tab_index]
        tile_row = row - room_row * 8
        tile_col = column - room_col * 10
        if TemplateSetting.ONLYFLIP in chunk.settings:
            tile_col = template_draw_item.width_in_rooms * 10 - 1 - tile_col

        tile_code = layer[tile_row][tile_col]
        tile = self.tile_palette_map[tile_code]

        self.palette_panel.select_tile(tile[0], tile[2], is_primary)
        self.on_select_palette_tile(tile[0], tile[2], is_primary)

    # Looks up the expected offset type and tile image size and computes the offset of the tile's anchor in the grid.
    def offset_for_tile(self, tile_name, tile_code, tile_size):
        img = self.image_for_tile_code(tile_code)
        if img:
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

    def draw_canvas(self, fresh):
        if len(self.template_draw_map) == 0:
            return

        self.canvas.clear()
        self.hide_intro()
        for map_index, draw_map in enumerate(self.template_draw_map):
            draw_rooms = draw_map.rooms
            if len(draw_rooms) == 0:
                continue
            if len(draw_rooms[0]) == 0:
                continue
            height = len(draw_rooms)
            width = len(draw_rooms[0])

            self.canvas.configure_size(
                width * 10, height * 8, CanvasIndex(0, map_index)
            )
            self.canvas.configure_size(
                width * 10, height * 8, CanvasIndex(1, map_index)
            )

            self.canvas.draw_background(self.lvl_biome, CanvasIndex(0, map_index))
            self.canvas.draw_background(self.lvl_biome, CanvasIndex(1, map_index))
            self.canvas.draw_grid(index=CanvasIndex(0, map_index))
            self.canvas.draw_grid(index=CanvasIndex(1, map_index))

            grid_sizes = []
            for room_row_index, room_row in enumerate(draw_rooms):
                for room_column_index, template_draw_item in enumerate(room_row):
                    if template_draw_item is None:
                        continue
                    grid_sizes.append(
                        GridRoom(
                            room_row_index,
                            room_column_index,
                            template_draw_item.width_in_rooms,
                            template_draw_item.height_in_rooms,
                        )
                    )

            # self.canvas.draw_room_grid(2, [grid_sizes])
            self.canvas.draw_canvas_room_grid(CanvasIndex(0, map_index), 2, grid_sizes)
            self.canvas.draw_canvas_room_grid(CanvasIndex(1, map_index), 2, grid_sizes)

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
                        # tile_image = tilecode[1]
                        tile_image = self.image_for_tile_code(tile)
                        x_offset, y_offset = self.texture_fetcher.adjust_texture_xy(
                            tile_image.width(),
                            tile_image.height(),
                            tile_name,
                            self.zoom_level,
                        )
                        self.canvas.replace_tile_at(
                            canvas_index,
                            row_index + chunk_start_y,
                            tile_index + chunk_start_x,
                            tile_image,
                            x_offset,
                            y_offset,
                        )

            for room_row_index, room_row in enumerate(draw_rooms):
                for room_column_index, template_draw_item in enumerate(room_row):
                    if template_draw_item:
                        chunk = template_draw_item.room_chunk
                        front = chunk.front
                        back = chunk.back
                        frontlayer_canvas = 0
                        backlayer_canvas = 1
                        if (
                            self.reverse_layers
                            and template_draw_item.template.name in REVERSED_ROOMS
                        ):
                            frontlayer_canvas = 1
                            backlayer_canvas = 0
                        if TemplateSetting.ONLYFLIP in chunk.settings:
                            front = list(map(lambda row: row[::-1], front))
                            back = list(map(lambda row: row[::-1], back))
                        draw_chunk(
                            CanvasIndex(frontlayer_canvas, map_index),
                            room_column_index * 10,
                            room_row_index * 8,
                            front,
                        )
                        if TemplateSetting.DUAL in chunk.settings:
                            draw_chunk(
                                CanvasIndex(backlayer_canvas, map_index),
                                room_column_index * 10,
                                room_row_index * 8,
                                back,
                            )
                        else:
                            for r in range(template_draw_item.height_in_rooms):
                                for c in range(template_draw_item.width_in_rooms):
                                    self.canvas.draw_background_over_room(
                                        CanvasIndex(backlayer_canvas, map_index),
                                        self.lvl_biome,
                                        room_row_index + r,
                                        room_column_index + c,
                                    )
                    else:
                        template, _, _ = self.template_item_at(
                            map_index, room_row_index, room_column_index
                        )
                        if template is None:
                            self.canvas.draw_background_over_room(
                                CanvasIndex(0, map_index),
                                self.lvl_biome,
                                room_row_index,
                                room_column_index,
                            )
                            self.canvas.draw_background_over_room(
                                CanvasIndex(1, map_index),
                                self.lvl_biome,
                                room_row_index,
                                room_column_index,
                            )

        self.canvas.update_scroll_region(fresh)

    def template_item_at(self, map_index, row, col):
        for room_row_index, room_row in enumerate(
            self.template_draw_map[map_index].rooms
        ):
            if room_row_index > row:
                return None, None, None
            for room_column_index, template_draw_item in enumerate(room_row):
                if room_column_index > col:
                    break
                if template_draw_item is None:
                    continue
                if (
                    room_row_index + template_draw_item.height_in_rooms - 1 >= row
                    and room_column_index + template_draw_item.width_in_rooms - 1 >= col
                ):
                    return template_draw_item, room_row_index, room_column_index

        return None, None, None
