from dataclasses import dataclass
from enum import Enum
import logging
import math
import random
import tkinter as tk
from PIL import Image, ImageDraw, ImageEnhance, ImageTk
from typing import List

from modlunky2.constants import BASE_DIR
from modlunky2.mem.state import Theme
from modlunky2.ui.levels.shared.biomes import BIOME


logger = logging.getLogger(__name__)


@dataclass
class GridRoom:
    row: int
    column: int
    width: int
    height: int


class CANVAS_MODE(Enum):
    DRAW = 1
    SELECT = 2
    FILL = 3
    MOVE = 4


@dataclass
class SelectRect:
    x0: int
    y0: int
    x1: int
    y1: int


@dataclass
class TileIndex:
    x: int
    y: int


@dataclass
class Pos:
    x: int
    y: int


@dataclass
class Selection:
    pos: SelectRect
    rect: int
    first_tile: TileIndex
    last_tile: TileIndex


@dataclass
class MoveTile:
    index: TileIndex
    image: int
    bg: int


@dataclass
class ActiveMove:
    tiles: List[MoveTile]
    start_pos: Pos
    last_event_pos: Pos
    grabbing_selections: bool


class LevelCanvas(tk.Canvas):
    def __init__(
        self,
        parent,
        textures_dir,
        zoom_level,
        on_click,
        on_pull_tile,
        on_fill,
        on_fill_type,
        on_move,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.textures_dir = textures_dir
        self.zoom_level = zoom_level

        self.on_pull_tile = on_pull_tile
        self.on_click = on_click
        self.on_fill = on_fill
        self.on_fill_type = on_fill_type
        self.on_move = on_move

        self.mode = CANVAS_MODE.DRAW

        self.tile_images = []
        self.grid_hidden = False
        self.rooms_hidden = False
        self.grid_lines = []
        self.room_lines = []

        self.cached_bgs = {}
        self.cached_bg_overs = {}
        self.cached_co_bgs = {}
        self.cached_co_bg_imgs = []
        self.cached_cosmos_img = None
        self.co_bg_locations = [(11, 6, 40, 1)]
        for _ in range(30):
            x = random.uniform(0, 80)
            y = random.uniform(0, 120)
            rotation = random.uniform(0, 360)
            size = random.uniform(0.75, 1.25)
            self.co_bg_locations.append((x, y, rotation, size))

        self.width = 0
        self.height = 0

        self.shift_down = False

        def holding_shift(_):
            if self.shift_down:
                return
            self.shift_down = True

            if self.mode == CANVAS_MODE.DRAW:
                self.config(cursor="pencil")

        def shift_up(_):
            if not self.shift_down:
                return
            self.shift_down = False
            if self.mode == CANVAS_MODE.DRAW:
                self.config(cursor="")

        self.bind_all("<KeyPress-Shift_L>", holding_shift, add="+")
        self.bind_all("<KeyPress-Shift_R>", holding_shift, add="+")
        self.bind_all("<KeyRelease-Shift_L>", shift_up, add="+")

        self.space_down = False

        def holding_space(_):
            self.space_down = True

        def space_up(_):
            self.space_down = False

        self.bind_all("<KeyPress- >", holding_space, add="+")
        self.bind_all("<KeyRelease- >", space_up, add="+")

        self.select_rects = []
        self.current_select_rect = None
        if on_fill and on_fill_type:
            # Click actions performed when selecting a region.
            self.bind("<Button-1>", self.select_click, add="+")
            self.bind("<B1-Motion>", self.select_drag, add="+")
            self.bind("<ButtonRelease-1>", self.select_release, add="+")
            self.bind("<Shift-Button-1>", self.select_click, add="+")
            self.bind("<Shift-B1-Motion>", self.select_drag, add="+")
            self.bind("<Shift-ButtonRelease-1>", self.select_release, add="+")
            self.bind_all("<Escape>", self.cancel_select, add="+")

            self.bind("<Button-1>", self.click_fill, add="+")
            self.bind("<Button-3>", self.click_fill, add="+")

        self.active_move = None
        if on_move:
            # Click actions performed when selecting a region.
            self.bind("<Button-1>", self.move_click, add="+")
            self.bind("<B1-Motion>", self.move_drag, add="+")
            self.bind("<ButtonRelease-1>", self.move_release, add="+")
            self.bind("<Shift-Button-1>", self.move_click, add="+")
            self.bind("<Shift-B1-Motion>", self.move_drag, add="+")
            self.bind("<Shift-ButtonRelease-1>", self.move_release, add="+")
            self.bind_all("<Escape>", self.cancel_move, add="+")

        if on_pull_tile:
            # Click actions performed when holding shift to select the tile at the cursor's
            # location.
            self.bind("<Shift-Button-1>", self.shift_click, add="+")
            self.bind("<Shift-Button-3>", self.shift_click, add="+")
            self.bind("<Shift-B1-Motion>", lambda event: None, add="+")
            self.bind("<Shift-B3-Motion>", lambda event: None, add="+")

        if on_click:
            # Click actions performed when the shift key is not down to "draw" the currently
            # selected tile at the cursor's position.
            self.bind("<Button-1>", self.click, add="+")
            self.bind("<B1-Motion>", self.click, add="+")
            self.bind("<Button-3>", self.click, add="+")
            self.bind("<B3-Motion>", self.click, add="+")

    def set_mode(self, mode):
        self.mode = mode
        if self.shift_down and (
            self.mode == CANVAS_MODE.DRAW or self.mode == CANVAS_MODE.FILL
        ):
            self.config(cursor="pencil")
        elif mode == CANVAS_MODE.FILL:
            self.config(cursor="spraycan")
        elif mode == CANVAS_MODE.SELECT:
            self.config(cursor="cross")
        elif mode == CANVAS_MODE.MOVE:
            self.config(cursor="fleur")
        else:
            self.config(cursor="")

    def pos_in_selection(self, row, column):
        for selection in self.select_rects:
            first_tile = selection.first_tile
            last_tile = selection.last_tile
            if not first_tile or not last_tile:
                continue
            if (
                column >= first_tile.x
                and column <= last_tile.x
                and row >= first_tile.y
                and row <= last_tile.y
            ):
                return True

        return False

    def click(self, event):
        if self.mode != CANVAS_MODE.DRAW:
            return
        self.clear_selections()
        is_primary = event.num == 1 or event.state & 0x0100 == 0x0100
        column = int(event.x // self.zoom_level)
        row = int(event.y // self.zoom_level)
        if column < 0 or event.x > int(self["width"]):
            return
        if row < 0 or event.y > int(self["height"]):
            return

        self.on_click(row, column, is_primary)

    def shift_click(self, event):
        if self.mode == CANVAS_MODE.DRAW or self.mode == CANVAS_MODE.FILL:
            is_primary = event.num == 1
            column = int(event.x // self.zoom_level)
            row = int(event.y // self.zoom_level)
            if column < 0 or event.x > int(self["width"]):
                return
            if row < 0 or event.y > int(self["height"]):
                return

            self.on_pull_tile(row, column, is_primary)

    def click_fill(self, event):
        if self.mode != CANVAS_MODE.FILL:
            return
        is_primary = event.num == 1 or event.state & 0x0100 == 0x0100
        column = int(event.x // self.zoom_level)
        row = int(event.y // self.zoom_level)
        if column < 0 or event.x > int(self["width"]):
            return
        if row < 0 or event.y > int(self["height"]):
            return

        tiles = []

        if len(self.select_rects) > 0:
            if not self.pos_in_selection(row, column):
                return
            for c in range(self.width):
                for r in range(self.height):
                    if self.pos_in_selection(r, c):
                        tiles.append(TileIndex(x=c, y=r))
            self.on_fill(tiles, is_primary)
        elif self.on_fill_type:
            self.on_fill_type(row, column, is_primary)

    def update_selection_tiles(self, selection):
        pos = selection.pos
        minposx = min(pos.x0, pos.x1)
        maxposx = max(pos.x0, pos.x1)
        minposy = min(pos.y0, pos.y1)
        maxposy = max(pos.y0, pos.y1)
        minx = minposx // self.zoom_level
        maxx = maxposx // self.zoom_level
        miny = minposy // self.zoom_level
        maxy = maxposy // self.zoom_level

        if (
            (minx < 0 and maxx < 0)
            or (minx >= self.width and maxx >= self.width)
            or (miny < 0 and maxy < 0)
            or (miny >= self.height and maxy >= self.height)
        ):
            min_tile = None
            max_tile = None
        elif (maxposx - minposx < 2) and (maxposy - minposy < 2):
            min_tile = None
            max_tile = None
        else:
            if minx < 0:
                minx = 0
            if maxx < 0:
                maxx = 0
            if miny < 0:
                miny = 0
            if maxy < 0:
                maxy = 0
            if minx >= self.width:
                minx = self.width - 1
            if maxx >= self.width:
                maxx = self.width - 1
            if miny >= self.height:
                miny = self.height - 1
            if maxy >= self.height:
                maxy = self.height - 1

            min_tile = TileIndex(minx, miny)
            max_tile = TileIndex(maxx, maxy)

        selection.first_tile = min_tile
        selection.last_tile = max_tile

    def clear_selections(self):
        for rect in self.select_rects:
            self.delete(rect.rect)
            self.select_rects = []

    def bring_selections_to_front(self):
        for rect in self.select_rects:
            self.tag_raise(rect.rect)

    def select_click(self, event):
        if self.mode != CANVAS_MODE.SELECT:
            return
        select_coords = SelectRect(event.x, event.y, event.x, event.y)
        if not self.shift_down:
            self.clear_selections()

        rect = self.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#F0F0F0",
            fill="#F0F0F0",
            width=2,
            stipple="gray12",
            state="normal",
        )

        self.current_select_rect = Selection(select_coords, rect, None, None)
        self.select_rects.append(self.current_select_rect)
        self.update_selection_tiles(self.current_select_rect)

    def select_drag(self, event):
        if self.mode != CANVAS_MODE.SELECT:
            return
        if self.current_select_rect == None:
            return

        pos = self.current_select_rect.pos
        if self.space_down:
            diffx, diffy = event.x - pos.x1, event.y - pos.y1
            pos.x0 += diffx
            pos.y0 += diffy
        # else:
        pos.x1 = event.x
        pos.y1 = event.y

        self.coords(self.current_select_rect.rect, pos.x0, pos.y0, pos.x1, pos.y1)
        self.update_selection_tiles(self.current_select_rect)

    def select_release(self, event):
        if self.mode != CANVAS_MODE.SELECT:
            return

        if self.current_select_rect == None:
            return

        pos = self.current_select_rect.pos
        first_tile = self.current_select_rect.first_tile
        last_tile = self.current_select_rect.last_tile

        if first_tile is None or last_tile is None:
            self.delete(self.current_select_rect.rect)
            self.select_rects.remove(self.current_select_rect)
        else:
            pos.x0, pos.y0 = (
                first_tile.x * self.zoom_level,
                first_tile.y * self.zoom_level,
            )
            pos.x1, pos.y1 = (last_tile.x + 1) * self.zoom_level - 1, (
                last_tile.y + 1
            ) * self.zoom_level - 1
            self.coords(self.current_select_rect.rect, pos.x0, pos.y0, pos.x1, pos.y1)

        self.current_select_rect = None

    def cancel_select(self, event):
        if self.mode != CANVAS_MODE.SELECT:
            return
        if self.current_select_rect == None:
            return

        self.delete(self.current_select_rect.rect)
        self.select_rects.remove(self.current_select_rect)
        self.current_select_rect = None

    def move_click(self, event):
        if self.mode != CANVAS_MODE.MOVE:
            return

        column = int(event.x // self.zoom_level)
        row = int(event.y // self.zoom_level)
        if column < 0 or event.x > int(self["width"]):
            return
        if row < 0 or event.y > int(self["height"]):
            return

        tiles = []

        grabbing_selections = False
        if len(self.select_rects) > 0 and self.pos_in_selection(row, column):
            grabbing_selections = True
            for c in range(self.width):
                for r in range(self.height):
                    if self.pos_in_selection(r, c):
                        image = self.tile_images[r][c]

                        tiles.append(MoveTile(TileIndex(x=c, y=r), image, None))
            for tile in tiles:
                self.tag_raise(tile.image)
        else:
            rectangle = self.create_rectangle(
                column * self.zoom_level,
                row * self.zoom_level,
                (column + 1) * self.zoom_level,
                (row + 1) * self.zoom_level,
                fill="#343434",
                outline="white",
                width=0,
                state="normal",
            )
            image = self.tile_images[row][column]
            self.tag_raise(image)
            tiles = [MoveTile(TileIndex(x=column, y=row), image, rectangle)]

        if len(tiles) == 0:
            return

        pos = Pos(event.x, event.y)
        self.active_move = ActiveMove(tiles, pos, pos, grabbing_selections)

        self.bring_selections_to_front()

    def move_drag(self, event):
        if self.mode != CANVAS_MODE.MOVE:
            return

        if self.active_move is None:
            return

        last_pos = self.active_move.last_event_pos
        new_pos = Pos(event.x, event.y)
        self.active_move.last_event_pos = new_pos
        distx = new_pos.x - last_pos.x
        disty = new_pos.y - last_pos.y
        for tile in self.active_move.tiles:
            if tile.bg:
                self.move(tile.bg, distx, disty)
            self.move(tile.image, distx, disty)

        if self.active_move.grabbing_selections:
            for selection in self.select_rects:
                self.move(selection.rect, distx, disty)

    def move_release(self, event):
        if self.mode != CANVAS_MODE.MOVE:
            return

        if self.active_move is None:
            return

        last_pos = self.active_move.last_event_pos
        start_pos = self.active_move.start_pos

        distx, disty = start_pos.x - last_pos.x, start_pos.y - last_pos.y
        for tile in self.active_move.tiles:
            self.move(tile.image, distx, disty)
            if tile.bg:
                self.delete(tile.bg)

        tiles = [tile.index for tile in self.active_move.tiles]

        dist_x = last_pos.x // self.zoom_level - start_pos.x // self.zoom_level
        dist_y = last_pos.y // self.zoom_level - start_pos.y // self.zoom_level

        if self.active_move.grabbing_selections:
            for selection in self.select_rects:
                pos = selection.pos
                pos.x0 += dist_x * self.zoom_level
                pos.x1 += dist_x * self.zoom_level
                pos.y0 += dist_y * self.zoom_level
                pos.y1 += dist_y * self.zoom_level
                self.coords(selection.rect, pos.x0, pos.y0, pos.x1, pos.y1)
                self.update_selection_tiles(selection)

        self.on_move(tiles, dist_x, dist_y)

    def cancel_move(self, event):
        if self.mode != CANVAS_MODE.MOVE:
            return

        if self.active_move is None:
            return

        last_pos = self.active_move.last_event_pos
        start_pos = self.active_move.start_pos
        distx, disty = start_pos.x - last_pos.x, start_pos.y - last_pos.y
        for tile in self.active_move.tiles:
            self.move(tile.image, distx, disty)
            if tile.bg:
                self.delete(tile.bg)

        if self.active_move.grabbing_selections:
            for selection in self.select_rects:
                self.move(selection.rect, distx, disty)
        self.active_move = None

    def set_zoom(self, zoom_level):
        self.zoom_level = zoom_level
        self.cached_bgs = {}
        self.cached_bg_overs = {}
        self.cached_co_bgs = {}
        self.cached_co_bg_imgs = []
        self.cached_cosmos_img = None

    def replace_tile_at(self, row, column, image, offset_x=0, offset_y=0):
        if len(self.tile_images) <= row or len(self.tile_images[row]) <= column:
            logger.debug("Attempted to draw tile outside of the range of the canvas.")
            return
        curr_img = self.tile_images[row][column]
        if curr_img:
            self.delete(curr_img)
        self.tile_images[row][column] = self.create_image(
            column * self.zoom_level - offset_x,
            row * self.zoom_level - offset_y,
            image=image,
            anchor="nw",
        )

        self.bring_selections_to_front()

    def configure_size(self, width, height):
        self.width = width
        self.height = height
        self["width"] = (self.zoom_level * width) - 3
        self["height"] = (self.zoom_level * height) - 3
        self.tile_images = [[None for _ in range(width)] for _ in range(height)]

    def draw_background(self, theme, subtheme):
        self.cached_co_bg_imgs = []
        if theme == Theme.COSMIC_OCEAN:
            self.create_rectangle(
                0,
                0,
                self.zoom_level * self.width,
                self.zoom_level * self.height,
                fill="#000000",
                state="normal",
            )

            cosmos_bg = self.cached_cosmos_img
            if not cosmos_bg:
                img = Image.open(BASE_DIR / "static/images/cosmos.png").convert("RGBA")
                img = img.resize(
                    (
                        round(1194 * self.zoom_level / 30),
                        round(697 * self.zoom_level / 30),
                    ),
                    Image.BILINEAR,
                )
                enhancer = ImageEnhance.Brightness(img)
                im_output = enhancer.enhance(1.0)
                cosmos_bg = ImageTk.PhotoImage(im_output)
                self.cached_cosmos_img = cosmos_bg

            for x in range(0, 1 + int(math.ceil(self.width / 10 / 4))):
                for y in range(0, 1 + int(math.ceil(self.height / 8 / 3))):
                    self.create_image(
                        x * self.zoom_level * 10 * 4
                        - (((y ^ 8) * 8) % 30) * self.zoom_level,
                        y * self.zoom_level * 8 * 3,
                        image=cosmos_bg,
                        anchor="nw",
                    )

            bg = self.cached_co_bgs.get(subtheme)
            if not bg:
                background = self.co_background_for_subtheme(subtheme)
                background = background.resize(
                    (self.zoom_level * 8, self.zoom_level * 8), Image.BILINEAR
                )

                enhancer = ImageEnhance.Brightness(background)
                im_output = enhancer.enhance(1.0)
                bg = im_output
                self.cached_co_bgs[subtheme] = bg

            for x, y, rotation, size in self.co_bg_locations:
                if x - 5 > self.width or y - 5 > self.height:
                    # Don't attempt drawing if no part will be visible.
                    continue
                scaled_bg = bg.resize(
                    (
                        round(self.zoom_level * 8 * size),
                        round(self.zoom_level * 8 * size),
                    ),
                    Image.BILINEAR,
                )
                rotated_bg = scaled_bg.rotate(rotation, expand=True)
                bg_img = ImageTk.PhotoImage(rotated_bg)
                self.cached_co_bg_imgs.append(bg_img)
                self.create_image(
                    x * self.zoom_level,
                    y * self.zoom_level,
                    image=bg_img,
                    anchor="center",
                )

        else:
            bg_img = self.cached_bgs.get(theme)
            if not bg_img:
                background = self.background_for_theme(theme)
                image = Image.open(background).convert("RGBA")
                image = image.resize(
                    (self.zoom_level * 10, self.zoom_level * 8), Image.BILINEAR
                )
                enhancer = ImageEnhance.Brightness(image)
                im_output = enhancer.enhance(1.0)
                bg_img = ImageTk.PhotoImage(im_output)
                self.cached_bgs[theme] = bg_img

            for x in range(0, int(math.ceil(self.width / 10))):
                for y in range(0, int(math.ceil(self.height / 8))):
                    self.create_image(
                        x * self.zoom_level * 10,
                        y * self.zoom_level * 8,
                        image=bg_img,
                        anchor="nw",
                    )

    def draw_background_over_room(self, theme, subtheme, row, col):
        if theme == Theme.COSMIC_OCEAN and subtheme is not None:
            # Do not show special CO tiles in this context.
            theme = subtheme
        bg_img = self.cached_bg_overs.get(theme)
        if not bg_img:
            background = self.background_for_theme(theme)
            image = Image.open(background).convert("RGBA")
            image = image.resize(
                (self.zoom_level * 10, self.zoom_level * 8), Image.BILINEAR
            )
            enhancer = ImageEnhance.Brightness(image)
            im_output = enhancer.enhance(0.2)
            bg_img = ImageTk.PhotoImage(im_output)
            self.cached_bg_overs[theme] = bg_img

        self.create_image(
            col * self.zoom_level * 10,
            row * self.zoom_level * 8,
            image=bg_img,
            anchor="nw",
        )

    def draw_grid(self, width=1):
        self.grid_lines = [
            self.create_line(
                i * self.zoom_level,
                0,
                i * self.zoom_level,
                self.height * self.zoom_level,
                fill="#F0F0F0",
                width=width,
            )
            for i in range(0, self.width + 2)
        ] + [
            self.create_line(
                0,
                i * self.zoom_level - 1,
                self.zoom_level * (self.width + 2),
                i * self.zoom_level,
                fill="#F0F0F0",
                width=width,
            )
            for i in range(0, self.height)
        ]
        self.hide_grid_lines(self.grid_hidden)

    def draw_room_grid(self, width=1, special_room_sizes: GridRoom = None):
        def create_room_boundary_box(row, col, w, h):
            return self.create_rectangle(
                col * 10 * self.zoom_level,
                row * 8 * self.zoom_level,
                (col + w) * 10 * self.zoom_level - 1 + (width - 1),
                (row + h) * 8 * self.zoom_level - 1 + (width - 1),
                outline="#30F030",
                width=width,
            )

        if special_room_sizes is not None:
            self.room_lines = [
                create_room_boundary_box(r.row, r.column, r.width, r.height)
                for r in special_room_sizes
            ]
        else:
            self.room_lines = [
                create_room_boundary_box(row, col, 1, 1)
                for row in range(0, int(self.height / 8))
                for col in range(0, int(self.width / 10))
            ]
        self.hide_room_lines(self.rooms_hidden)

    def hide_grid_lines(self, hide):
        self.grid_hidden = hide
        for grid_line in self.grid_lines:
            self.itemconfig(grid_line, state=("hidden" if hide else "normal"))

    def hide_room_lines(self, hide):
        self.rooms_hidden = hide
        for room_line in self.room_lines:
            self.itemconfig(room_line, state=("hidden" if hide else "normal"))

    def clear(self):
        self.delete("all")
        self.clear_selections()
        self.tile_images = []
        self.grid_lines = []
        self.room_lines = []

    # Path to the background image that will be shown behind the grid.
    def background_for_theme(self, theme):
        def background_file(theme):
            if theme == Theme.DWELLING:
                return "bg_cave.png"
            elif theme == Theme.TIDE_POOL or theme == Theme.ABZU:
                return "bg_tidepool.png"
            elif theme == Theme.NEO_BABYLON or theme == Theme.NEO_BABYLON:
                return "bg_babylon.png"
            elif theme == Theme.JUNGLE:
                return "bg_jungle.png"
            elif theme == Theme.TEMPLE or theme == Theme.DUAT:
                return "bg_temple.png"
            elif theme == Theme.SUNKEN_CITY or theme == Theme.HUNDUN:
                return "bg_sunken.png"
            elif theme == Theme.CITY_OF_GOLD:
                return "bg_gold.png"
            elif theme == Theme.EGGPLANT_WORLD:
                return "bg_eggplant.png"
            elif theme == Theme.ICE_CAVES:
                return "bg_ice.png"
            elif theme == Theme.OLMEC:
                return "bg_stone.png"
            elif theme == Theme.VOLCANA:
                return "bg_volcano.png"
            return "bg_cave.png"

        return self.textures_dir / background_file(theme)

    def co_background_for_subtheme(self, subtheme):
        file = self.textures_dir / "deco_cosmic.png"

        def coords(subtheme):
            if subtheme == Theme.DWELLING:
                return (0, 0)
            elif subtheme == Theme.JUNGLE or subtheme == Theme.OLMEC:
                return (0, 1)
            elif subtheme == Theme.VOLCANA:
                return (0, 2)
            elif (
                subtheme == Theme.TIDE_POOL
                or subtheme == Theme.ABZU
                or subtheme == Theme.TIAMAT
            ):
                return (0, 3)
            elif (
                subtheme == Theme.TEMPLE
                or subtheme == Theme.DUAT
                or subtheme == Theme.CITY_OF_GOLD
            ):
                return (1, 0)
            elif subtheme == Theme.ICE_CAVES:
                return (1, 1)
            elif subtheme == Theme.NEO_BABYLON:
                return (1, 2)
            elif subtheme == Theme.SUNKEN_CITY or subtheme == Theme.HUNDUN:
                return (1, 3)
            return (0, 0)

        TEXTURE_SIZE = 512
        image = Image.open(file).convert("RGBA")
        row, column = coords(subtheme)
        bbox = (
            column * TEXTURE_SIZE,
            row * TEXTURE_SIZE,
            (column + 1) * TEXTURE_SIZE,
            (row + 1) * TEXTURE_SIZE,
        )
        return image.crop(bbox)
