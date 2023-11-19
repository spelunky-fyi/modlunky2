import logging
import math
import tkinter as tk
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

from modlunky2.ui.levels.shared.biomes import BIOME


logger = logging.getLogger(__name__)


class LevelCanvas(tk.Canvas):
    def __init__(
        self, parent, textures_dir, zoom_level, on_click, on_pull_tile, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.textures_dir = textures_dir
        self.zoom_level = zoom_level

        self.on_pull_tile = on_pull_tile
        self.on_click = on_click

        self.tile_images = []
        self.grid_hidden = False
        self.rooms_hidden = False
        self.grid_lines = []
        self.room_lines = []

        self.cached_bgs = {}

        self.width = 0
        self.height = 0

        if on_pull_tile:
            shift_down = False

            def holding_shift(_):
                nonlocal shift_down
                if shift_down:
                    return
                shift_down = True
                self.config(cursor="pencil")

            def shift_up(_):
                nonlocal shift_down
                if not shift_down:
                    return
                shift_down = False
                self.config(cursor="")

            self.bind_all("<KeyPress-Shift_L>", holding_shift, add="+")
            self.bind_all("<KeyPress-Shift_R>", holding_shift, add="+")
            self.bind_all("<KeyRelease-Shift_L>", shift_up, add="+")

            # Click actions performed when holding shift to select the tile at the cursor's
            # location.
            self.bind("<Shift-Button-1>", self.shift_click)
            self.bind("<Shift-Button-3>", self.shift_click)
            self.bind("<Shift-B1-Motion>", lambda event: None)
            self.bind("<Shift-B3-Motion>", lambda event: None)

        if on_click:
            # Click actions performed when the shift key is not down to "draw" the currently
            # selected tile at the cursor's position.
            self.bind("<Button-1>", self.click)
            self.bind("<B1-Motion>", self.click)
            self.bind("<Button-3>", self.click)
            self.bind("<B3-Motion>", self.click)

    def click(self, event):
        is_primary = event.num == 1 or event.state & 0x0100 == 0x0100
        column = int(event.x // self.zoom_level)
        row = int(event.y // self.zoom_level)
        if column < 0 or event.x > int(self["width"]):
            return
        if row < 0 or event.y > int(self["height"]):
            return

        self.on_click(row, column, is_primary)

    def shift_click(self, event):
        is_primary = event.num == 1
        column = int(event.x // self.zoom_level)
        row = int(event.y // self.zoom_level)
        if column < 0 or event.x > int(self["width"]):
            return
        if row < 0 or event.y > int(self["height"]):
            return

        self.on_pull_tile(row, column, is_primary)

    def set_zoom(self, zoom_level):
        self.zoom_level = zoom_level
        self.cached_bgs = {}

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

    def configure_size(self, width, height):
        self.width = width
        self.height = height
        self["width"] = (self.zoom_level * width) - 3
        self["height"] = (self.zoom_level * height) - 3
        self.tile_images = [[None for _ in range(width)] for _ in range(height)]

    def draw_background(self, theme):
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

    def draw_grid(self):
        self.grid_lines = [
            self.create_line(
                i * self.zoom_level,
                0,
                i * self.zoom_level,
                self.height * self.zoom_level,
                fill="#F0F0F0",
            )
            for i in range(0, self.width + 2)
        ] + [
            self.create_line(
                0,
                i * self.zoom_level,
                self.zoom_level * (self.width + 2),
                i * self.zoom_level,
                fill="#F0F0F0",
            )
            for i in range(0, self.height)
        ]
        self.hide_grid_lines(self.grid_hidden)

    def draw_room_grid(self):
        self.room_lines = [
            self.create_line(
                i * 10 * self.zoom_level,
                0,
                i * 10 * self.zoom_level,
                self.height * self.zoom_level,
                fill="#30F030",
            )
            for i in range(0, int(self.width / 10))
        ] + [
            # for i in range(0, rows * 8):
            self.create_line(
                0,
                i * 8 * self.zoom_level,
                self.zoom_level * self.width,
                i * 8 * self.zoom_level,
                fill="#30F030",
            )
            for i in range(0, int(self.height / 8))
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
        # self.tile_images = []
        # self.grid_lines = []
        # self.room_lines = []

    # Path to the background image that will be shown behind the grid.
    def background_for_theme(self, theme):
        def background_file(theme):
            if theme == BIOME.DWELLING:
                return "bg_cave.png"
            elif theme == BIOME.TIDE_POOL:
                return "bg_tidepool.png"
            elif theme == BIOME.NEO_BABYLON:
                return "bg_babylon.png"
            elif theme == BIOME.JUNGLE:
                return "bg_jungle.png"
            elif theme == BIOME.TEMPLE:
                return "bg_temple.png"
            elif theme == BIOME.SUNKEN_CITY:
                return "bg_sunken.png"
            elif theme == BIOME.CITY_OF_GOLD:
                return "bg_gold.png"
            elif theme == BIOME.DUAT:
                return "bg_temple.png"
            elif theme == BIOME.EGGPLANT_WORLD:
                return "bg_eggplant.png"
            elif theme == BIOME.ICE_CAVES:
                return "bg_ice.png"
            elif theme == BIOME.OLMEC:
                return "bg_stone.png"
            elif theme == BIOME.VOLCANA:
                return "bg_volcano.png"
            return "bg_cave.png"

        return self.textures_dir / background_file(theme)
