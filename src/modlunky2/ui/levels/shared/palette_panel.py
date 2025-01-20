import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

from modlunky2.levels.tile_codes import VALID_TILE_CODES
from modlunky2.ui.levels.shared.tile import Tile
from modlunky2.ui.widgets import PopupWindow, ScrollableFrameLegacy, Tab


class NewTilecodeCombobox(ttk.Frame):
    def __init__(self, parent, on_add_tilecode, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.on_add_tilecode = on_add_tilecode

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.selection_container = ttk.Frame(self)
        self.selection_container.grid(row=0, column=0)

        self.combobox_container = ttk.Frame(self.selection_container)
        self.combobox_container.grid(row=1, column=0, sticky="nsw")
        self.combobox = ttk.Combobox(self.combobox_container, height=20, width=50)
        self.combobox.grid(row=0, column=0, sticky="nswe")
        self.combobox_alt = ttk.Combobox(self.combobox_container, height=40, width=23)
        self.combobox_alt.grid(row=0, column=2, sticky="nswe")
        self.combobox_alt["state"] = tk.DISABLED
        self.combobox_alt.grid_remove()

        self.combobox["values"] = sorted(VALID_TILE_CODES, key=str.lower)
        self.combobox_alt["values"] = sorted(VALID_TILE_CODES, key=str.lower)

        self.scale_frame = ttk.Frame(self.selection_container)
        self.scale_frame.columnconfigure(0, weight=1)
        self.scale_frame.grid(row=0, column=0, sticky="nswe")

        self.scale_var = tk.StringVar()
        self.scale_var.set("100")
        self.scale_value_label = ttk.Label(
            self.scale_frame, anchor="center", textvariable=self.scale_var
        )
        self.scale_value_label.grid(row=0, column=0, sticky="ew")
        self.scale = ttk.Scale(
            self.scale_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.update_scale,
        )  # Scale for the percentage of a selected tile.
        self.scale.grid(row=1, column=0, sticky="ew")
        self.scale.set(100)

        self.add_button = tk.Button(
            self, text="Add Tilecode", bg="yellow", command=self.add_tilecode
        )
        self.add_button.grid(row=0, column=1, sticky="news")
        self.disable()

    def update_scale(self, _event):
        new_value = int(float(self.scale.get()))
        self.scale_var.set(str(new_value))
        if new_value == 100:
            self.combobox_alt.grid_remove()
            self.combobox.configure(width=50)
            self.combobox_container.columnconfigure(1, minsize=0)
        else:
            self.combobox.configure(width=23)
            self.combobox_alt.grid()
            self.combobox_container.columnconfigure(1, minsize=1)

    def add_tilecode(self):
        self.on_add_tilecode(
            str(self.combobox.get()),
            str(int(float(self.scale.get()))),
            self.combobox_alt.get(),
        )

    def reset(self):
        self.scale.set(100)
        self.combobox.set("empty")
        self.combobox_alt.set("empty")
        self.disable()

    def disable(self):
        self.scale["state"] = tk.DISABLED
        self.combobox["state"] = tk.DISABLED
        self.combobox_alt["state"] = tk.DISABLED

    def enable(self):
        self.scale["state"] = tk.NORMAL
        self.combobox["state"] = tk.NORMAL
        self.combobox_alt["state"] = tk.NORMAL


class SelectedTilecodeView(ttk.Frame):
    def __init__(
        self, parent, title_prefix, on_delete, sprite_fetcher, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.sprite_fetcher = sprite_fetcher
        self.title_prefix = title_prefix

        self.delete_button = tk.Button(
            self,
            text="Delete",
            bg="red",
            fg="white",
            width=10,
            command=lambda: on_delete(self.tile),
        )

        # Shows selected tile. Important because this is used for more than just user
        # convenience; we can grab the currently used tile here
        self.title_label = ttk.Label(self, text=title_prefix + " empty 0")

        self.tile = None
        self.img_empty = ImageTk.PhotoImage(
            sprite_fetcher.get("empty").resize((40, 40), Image.Resampling.LANCZOS)
        )
        self.img_view = ttk.Label(self, image=self.img_empty, width=50)

        self.img = None

        self.columnconfigure(0, minsize=8)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(4, minsize=10)
        self.delete_button.grid(row=0, column=1, sticky="w", padx=2)
        self.title_label.grid(row=0, column=2, sticky="we")
        self.img_view.grid(row=0, column=3, sticky="e")

        self.reset()

    def select_tile(self, tile):
        self.tile = tile
        self.refresh()

    def refresh(self):
        tile = self.tile
        if tile is None:
            self.title_label["text"] = self.title_prefix
        else:
            self.title_label["text"] = (
                self.title_prefix + " " + tile.name + " " + tile.code
            )
        if tile is not None and tile.image:
            self.img_view["image"] = tile.picker_image
            self.img = tile.picker_image
        else:
            self.img_view["image"] = self.img_empty

    def reset(self, disable=True):
        self.select_tile(Tile("empty", "0", "", self.img_empty, self.img_empty))
        if disable:
            self.disable()

    def enable(self):
        self.delete_button["state"] = tk.NORMAL

    def disable(self):
        self.delete_button["state"] = tk.DISABLED


class PalettePanel(ttk.Frame):
    def __init__(
        self,
        parent,
        on_delete_tilecode,
        on_add_tilecode,
        on_select_tile,
        on_use_dependency_tile,
        texture_fetcher,
        sprite_fetcher,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)

        self.texture_fetcher = texture_fetcher
        self.on_delete_tilecode = on_delete_tilecode
        self.on_add_tilecode = on_add_tilecode
        self.on_select_tile = on_select_tile
        self.on_use_dependency_tile = on_use_dependency_tile

        # The tile palettes are loaded into here as buttons with their image
        # as a tile and text as their value to grab when needed.
        self.palette = ScrollableFrameLegacy(self, text="Tile Palette", width=50)
        self.palette.scrollable_frame["width"] = 50
        self.tile_images = []

        self.primary_tile_view = SelectedTilecodeView(
            self, "Primary Tile:", self.delete_tilecode, sprite_fetcher
        )
        self.secondary_tile_view = SelectedTilecodeView(
            self, "Secondary Tile:", self.delete_tilecode, sprite_fetcher
        )

        self.new_tile_panel = NewTilecodeCombobox(self, on_add_tilecode)

        self.rowconfigure(2, weight=1)
        self.primary_tile_view.grid(row=0, column=0, sticky="we")
        self.secondary_tile_view.grid(row=1, column=0, sticky="we")
        self.palette.grid(row=2, column=0, sticky="swne")
        self.new_tile_panel.grid(row=3, column=0, sticky="swne")

    def delete_tilecode(self, tile):
        deleted = self.on_delete_tilecode(tile)
        if deleted:
            if self.primary_tile_view.tile.code == tile.code:
                self.primary_tile_view.reset(disable=False)
            if self.secondary_tile_view.tile.code == tile.code:
                self.secondary_tile_view.reset(disable=False)

    def update_with_palette(
        self,
        new_palette,
        suggestions,
        dependency_tiles,
        biome,
        floor_biome,
        border_biome,
        lvl,
    ):
        for widget in self.palette.scrollable_frame.winfo_children():
            widget.destroy()

        TILES_PER_ROW = 8

        count_row = 0
        count_col = -1
        self.tile_images = []
        used_tile_names = []

        for tile_keep in new_palette:
            count_col += 1
            if count_col == TILES_PER_ROW:
                count_col = 0
                count_row = count_row + 1

            used_tile_names.append(tile_keep.name)

            self.tile_images.append(tile_keep.picker_image)
            new_tile = tk.Button(
                self.palette.scrollable_frame,
                text=tile_keep.name,
                width=40,
                height=40,
                image=tile_keep.picker_image,
            )
            new_tile.grid(row=count_row, column=count_col)
            new_tile.bind(
                "<Button-1>",
                lambda event, t=tile_keep: self.tile_pick(event, t, True),
            )
            new_tile.bind(
                "<Button-3>",
                lambda event, t=tile_keep: self.tile_pick(event, t, False),
            )

            # Bind first ten tiles to number keys
            tile_index = count_col + (count_row * TILES_PER_ROW) + 1
            if tile_index <= 10:
                self.bind_all(
                    f"{tile_index%10}",
                    lambda event, t=tile_keep: self.tile_pick(event, t, True),
                )
                self.bind_all(
                    f"<Alt-Key-{tile_index%10}>",
                    lambda event, t=tile_keep: self.tile_pick(event, t, False),
                )

        if suggestions and len(suggestions):
            count_col = -1
            self.palette.scrollable_frame.rowconfigure(count_row + 1, minsize=15)
            count_row = count_row + 2
            suggestions_label = ttk.Label(
                self.palette.scrollable_frame, text="Suggested Tiles:"
            )
            suggestions_label.grid(row=count_row, column=0, columnspan=5, sticky="nw")
            count_row = count_row + 1

            for suggestion in suggestions:
                if suggestion in used_tile_names:
                    # Do not suggest a tile that already exists in the palette.
                    continue

                count_col += 1
                if count_col == TILES_PER_ROW:
                    count_col = 0
                    count_row = count_row + 1

                tile_image = ImageTk.PhotoImage(
                    self.texture_fetcher.get_texture(
                        suggestion, biome, floor_biome, border_biome, lvl, 40
                    )
                )
                self.tile_images.append(tile_image)
                new_tile = tk.Button(
                    self.palette.scrollable_frame,
                    text=suggestion,
                    width=40,
                    height=40,
                    image=tile_image,
                )
                new_tile.grid(row=count_row, column=count_col)
                new_tile.bind(
                    "<Button-1>",
                    lambda event, ts=suggestion: self.suggested_tile_pick(event, ts),
                )
                new_tile.bind(
                    "<Button-3>",
                    lambda event, ts=suggestion: self.suggested_tile_pick(event, ts),
                )

        if dependency_tiles and len(dependency_tiles):
            for dependency in dependency_tiles:
                if len(dependency.tiles) == 0:
                    continue
                count_col = -1
                self.palette.scrollable_frame.rowconfigure(count_row + 1, minsize=15)
                count_row += 2
                dependency_label = ttk.Label(
                    self.palette.scrollable_frame, text=str(dependency.name) + ":"
                )
                dependency_label.grid(
                    row=count_row, column=0, columnspan=5, sticky="nw"
                )
                count_row += 1

                for tile in dependency.tiles:
                    count_col += 1
                    if count_col == TILES_PER_ROW:
                        count_col = 0
                        count_row += 1

                    tile_image = tile.picker_image
                    self.tile_images.append(tile_image)

                    new_tile = tk.Button(
                        self.palette.scrollable_frame,
                        text=tile.name,
                        width=40,
                        height=40,
                        image=tile_image,
                    )
                    new_tile.grid(row=count_row, column=count_col)
                    new_tile.bind(
                        "<Button-1>",
                        lambda event, t=tile, d=dependency: self.dependency_tile_pick(
                            event, t, d
                        ),
                    )
                    new_tile.bind(
                        "<Button-3>",
                        lambda event, t=tile, d=dependency: self.dependency_tile_pick(
                            event, t, d
                        ),
                    )

        self.primary_tile_view.enable()
        self.secondary_tile_view.enable()
        self.primary_tile_view.refresh()
        self.secondary_tile_view.refresh()
        self.new_tile_panel.reset()
        self.new_tile_panel.enable()

    def tile_pick(self, event, tile, is_primary):
        if event is not None and isinstance(event.widget, tk.Entry):
            # Do not select a tile when the key was pressed to type into an Entry field.
            return

        self.select_tile(tile, is_primary, True)

    def suggested_tile_pick(self, event, suggested_tile):
        tile = self.on_add_tilecode(suggested_tile, 100, "empty")
        if not tile:
            return
        self.select_tile(tile, event.num == 1, True)

    def dependency_tile_pick(self, event, tile, dependency):
        if self.on_use_dependency_tile:
            new_tile = self.on_use_dependency_tile(tile, dependency)

            self.select_tile(new_tile, event.num == 1, True)

    def select_tile(self, tile, is_primary, tell_delegate=False):
        tile_view = self.primary_tile_view
        if not is_primary:
            tile_view = self.secondary_tile_view
        tile_view.select_tile(tile)

        if tell_delegate and self.on_select_tile:
            self.on_select_tile(tile, is_primary)

    def reset(self):
        for widget in self.palette.scrollable_frame.winfo_children():
            widget.destroy()

        self.primary_tile_view.reset()
        self.secondary_tile_view.reset()
        self.new_tile_panel.reset()

    def selected_tile(self, is_primary):
        return self.primary_tile() if is_primary else self.secondary_tile()

    def primary_tile(self):
        return self.primary_tile_view.tile

    def secondary_tile(self):
        return self.secondary_tile_view.tile
