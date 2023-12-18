from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from typing import List

from modlunky2.ui.levels.shared.level_canvas import LevelCanvas, GridRoom
from modlunky2.utils import is_windows


@dataclass
class CanvasIndex:
    tab_index: int
    canvas_index: int


class MultiCanvasContainer(tk.Frame):
    def __init__(
        self,
        parent,
        textures_dir,
        tab_titles,
        canvas_titles,
        zoom_level,
        on_click=None,
        on_shiftclick=None,
        intro_text=None,
        vertical=False,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.on_click = on_click
        self.on_shiftclick = on_shiftclick

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        if tab_titles is None or len(tab_titles) == 0:
            tab_titles = [""]
        if canvas_titles is None or len(canvas_titles) == 0:
            canvas_titles = [""]

        scrollable_canvas = tk.Canvas(self, bg="#292929")
        scrollable_canvas.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="news")
        scrollable_canvas.columnconfigure(0, weight=1)
        scrollable_canvas.rowconfigure(0, weight=1)

        scrollable_frame = tk.Frame(scrollable_canvas, bg="#343434")
        scrollable_frame.grid(row=0, column=0, sticky="nswe")
        self.scrollable_frame = scrollable_frame

        width = scrollable_canvas.winfo_screenwidth()
        height = scrollable_canvas.winfo_screenheight()
        scrollable_canvas.create_window(
            (width, height),
            window=scrollable_frame,
            anchor="center",
        )
        scrollable_canvas["width"] = width
        scrollable_canvas["height"] = height

        scrollable_frame.columnconfigure(0, minsize=int(int(width) / 2))
        scrollable_frame.columnconfigure(1, weight=1)
        canvas_gaps = len(canvas_titles) - 1
        for column in range(canvas_gaps):
            if vertical:
                scrollable_frame.rowconfigure((column + 1) * 2, minsize=50)
            else:
                scrollable_frame.columnconfigure((column + 1) * 2, minsize=50)
        scrollable_frame.columnconfigure(
            (canvas_gaps + 1) * 2 if not vertical else 4, minsize=int(int(width) / 2)
        )
        scrollable_frame.rowconfigure(0, minsize=int(int(height) / 2))
        scrollable_frame.rowconfigure(1, weight=1)
        if not vertical:
            scrollable_frame.rowconfigure(2, minsize=100)
        if vertical:
            scrollable_frame.rowconfigure((canvas_gaps + 1) * 2, minsize=50)
        scrollable_frame.rowconfigure(
            (canvas_gaps + 1) * 2 + 1 if vertical else 4, minsize=int(int(height) / 2)
        )

        # Scroll bars for scrolling the canvases.
        hbar = ttk.Scrollbar(self, orient="horizontal", command=scrollable_canvas.xview)
        hbar.grid(row=0, column=0, columnspan=7, rowspan=2, sticky="swe")
        vbar = ttk.Scrollbar(self, orient="vertical", command=scrollable_canvas.yview)
        vbar.grid(row=0, column=0, columnspan=8, rowspan=2, sticky="nse")

        # Bindings to allow scrolling with the mouse.
        scrollable_canvas.bind(
            "<Enter>",
            lambda event: self._bind_to_mousewheel(
                event, hbar, vbar, scrollable_canvas
            ),
        )
        scrollable_canvas.bind(
            "<Leave>",
            lambda event: self._unbind_from_mousewheel(event, scrollable_canvas),
        )
        scrollable_frame.bind(
            "<Configure>",
            lambda e: scrollable_canvas.configure(
                scrollregion=scrollable_canvas.bbox("all")
            ),
        )

        scrollable_canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.scrollable_canvas = scrollable_canvas

        switches_container = tk.Frame(self, bg="#343434")
        switches_container.grid(row=0, column=0, sticky="nw")
        self.switches_container = switches_container

        self.canvases = []
        self.labels = []
        self.radio_buttons = []
        self.hidden_tabs = []
        self.hidden_canvases = []

        # Buttons to switch the active layer.
        switch_variable = tk.StringVar()
        self.switch_variable = switch_variable

        def switch_layer():
            nonlocal switch_variable
            layer = switch_variable.get()
            for tab_index, tab_of_canvases in enumerate(self.canvases):
                if tab_index == int(layer):
                    for canvas in tab_of_canvases:
                        canvas.grid()
                else:
                    for canvas in tab_of_canvases:
                        canvas.grid_remove()

        for tab_index, tab_title in enumerate(tab_titles):
            tab_canvases = []
            self.canvases.append(tab_canvases)
            for index, canvas_title in enumerate(canvas_titles):
                new_canvas = LevelCanvas(
                    scrollable_frame,
                    textures_dir,
                    zoom_level,
                    on_click
                    and (
                        lambda row, column, is_primary, i=CanvasIndex(
                            tab_index, index
                        ): self.on_click(i, row, column, is_primary)
                    ),
                    on_shiftclick
                    and (
                        lambda row, column, is_primary, i=CanvasIndex(
                            tab_index, index
                        ): self.on_shiftclick(i, row, column, is_primary)
                    ),
                    bg="#343434",
                )
                if vertical:
                    new_canvas.grid(row=index * 2 + 1, column=1, sticky="sw")
                else:
                    new_canvas.grid(row=1, column=index * 2 + 1, sticky="sw")
                if tab_index != 0:
                    new_canvas.grid_remove()
                tab_canvases.append(new_canvas)

                if len(canvas_titles) > 1:
                    label = tk.Label(
                        scrollable_frame,
                        text=canvas_title,
                        fg="white",
                        bg="#343434",
                    )
                    if vertical:
                        label.grid(row=(index + 1) * 2, column=1, sticky="nw")
                    else:
                        label.grid(row=2, column=index * 2 + 1, sticky="news")
                    # label.grid_remove()
                    self.labels.append(label)

            if len(tab_titles) > 1:
                switch_button = tk.Radiobutton(
                    switches_container,
                    text=tab_title,
                    variable=switch_variable,
                    indicatoron=False,
                    value=str(tab_index),
                    width=max(len(tab_title), 10),
                    command=switch_layer,
                )
                self.radio_buttons.append(switch_button)

                switch_button.grid(column=tab_index, row=0, sticky="new")

        switch_variable.set("0")

        if intro_text:
            # This intro frame covers the editor while there is no level selected with a hint message.
            self.intro = tk.Frame(self, bg="#343434")
            self.intro.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="news")

            intro_label = tk.Label(
                self.intro,
                text=intro_text,
                font=("Arial", 45),
                bg="#343434",
                fg="white",
                wraplength=600,
            )
            intro_label.place(relx=0.5, rely=0.5, anchor="center")

    def update_scroll_region(self):
        self.scrollable_canvas.update_idletasks()
        self.scrollable_canvas.config(scrollregion=self.scrollable_frame.bbox("all"))

        self.scrollable_canvas.xview_moveto(.5)
        self.scrollable_canvas.yview_moveto(.2)

    def _on_mousewheel(self, event, hbar, vbar, canvas):
        scroll_dir = None
        if event.num == 5 or event.delta == -120:
            scroll_dir = 1
        elif event.num == 4 or event.delta == 120:
            scroll_dir = -1

        if scroll_dir is None:
            return

        if event.state & (1 << 0):  # Shift / Horizontal Scroll
            self._scroll_horizontal(scroll_dir, hbar, canvas)
        else:
            self._scroll_vertical(scroll_dir, vbar, canvas)

    def _scroll_vertical(self, scroll_dir, scrollbar, canvas):
        canvas.yview_scroll(scroll_dir, "units")

    def _scroll_horizontal(self, scroll_dir, scrollbar, canvas):
        canvas.xview_scroll(scroll_dir, "units")

    def _bind_to_mousewheel(self, _event, hbar, vbar, canvas):
        if is_windows():
            canvas.bind_all(
                "<MouseWheel>",
                lambda event: self._on_mousewheel(event, hbar, vbar, canvas),
            )
        else:
            canvas.bind_all(
                "<Button-4>",
                lambda event: self._on_mousewheel(event, hbar, vbar, canvas),
            )
            canvas.bind_all(
                "<Button-5>",
                lambda event: self._on_mousewheel(event, hbar, vbar, canvas),
            )

    def _unbind_from_mousewheel(self, _event, canvas):
        if is_windows():
            canvas.unbind_all("<MouseWheel>")
        else:
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

    def replace_tile_at(self, index, row, column, image, offset_x=0, offset_y=0):
        self.canvases[index.tab_index][index.canvas_index].replace_tile_at(
            row, column, image, offset_x, offset_y
        )

    def configure_size(self, width, height, index=None):
        if index is None:
            for tab_of_canvases in self.canvases:
                for canvas in tab_of_canvases:
                    canvas.configure_size(width, height)
        else:
            self.canvases[index.tab_index][index.canvas_index].configure_size(
                width, height
            )

    def set_zoom(self, zoom_level):
        for tab_of_canvases in self.canvases:
            for canvas in tab_of_canvases:
                canvas.set_zoom(zoom_level)

    def clear(self):
        for tab_of_canvases in self.canvases:
            for canvas in tab_of_canvases:
                canvas.clear()

    def hide_grid_lines(self, hide_grid_lines):
        for tab_of_canvases in self.canvases:
            for canvas in tab_of_canvases:
                canvas.hide_grid_lines(hide_grid_lines)

    def hide_room_lines(self, hide_room_lines):
        for tab_of_canvases in self.canvases:
            for canvas in tab_of_canvases:
                canvas.hide_room_lines(hide_room_lines)

    def draw_background(self, theme, index=None):
        if index is None:
            for tab_of_canvases in self.canvases:
                for canvas in tab_of_canvases:
                    canvas.draw_background(theme)
        else:
            self.canvases[index.tab_index][index.canvas_index].draw_background(theme)

    def draw_background_over_room(self, index, theme, row, col):
        self.canvases[index.tab_index][index.canvas_index].draw_background_over_room(
            theme, row, col
        )

    def draw_grid(self, width=None, index=None):
        if index is None:
            for tab_of_canvases in self.canvases:
                for canvas in tab_of_canvases:
                    canvas.draw_grid(width)
        else:
            self.canvases[index.tab_index][index.canvas_index].draw_grid(width)

    def draw_room_grid(self, width=1, special_room_sizes: List[GridRoom] = None):
        for tab_of_canvases in self.canvases:
            for canvas_index, canvas in enumerate(tab_of_canvases):
                canvas.draw_room_grid(
                    width,
                    None
                    if special_room_sizes is None
                    else special_room_sizes[canvas_index],
                )

    def draw_canvas_room_grid(
        self, canvas_index, width=1, special_room_sizes: GridRoom = None
    ):
        canvas = self.canvases[canvas_index.tab_index][canvas_index.canvas_index]
        canvas.draw_room_grid(width, special_room_sizes)

    def show_intro(self):
        if self.intro:
            self.intro.grid()

    def hide_intro(self):
        if self.intro:
            self.intro.grid_remove()

    def hide_tab(self, tab_index, hide):
        if hide:
            if tab_index in self.hidden_tabs:
                return
            self.hidden_tabs.append(tab_index)
            selected_tab = int(self.switch_variable.get())

            for canvas in self.canvases[tab_index]:
                canvas.grid_remove()

            self.radio_buttons[tab_index].grid_remove()
            if tab_index == selected_tab:
                for ind, tab_of_canvases in enumerate(self.canvases):
                    if ind != tab_index and ind not in self.hidden_tabs:
                        for canvas in tab_of_canvases:
                            canvas.grid()
                            self.switch_variable.set(str(ind))
                            break
            if len(self.hidden_tabs) >= len(self.canvases) - 1:
                self.switches_container.grid_remove()
        else:
            if tab_index not in self.hidden_tabs:
                return
            self.hidden_tabs.remove(tab_index)
            if len(self.canvases) - len(self.hidden_tabs) == 1:
                for canvas in self.canvases[tab_index]:
                    canvas.grid()
            self.radio_buttons[tab_index].grid()
            if len(self.hidden_tabs) < len(self.canvases) - 1:
                self.switches_container.grid()

    def hide_canvas(self, canvas_index, hide):
        if hide:
            if canvas_index in self.hidden_canvases:
                return
            self.hidden_canvases.append(canvas_index)

            for canvases in self.canvases:
                canvases[canvas_index].grid_remove()

            self.labels[canvas_index].grid_remove()

            if len(self.hidden_canvases) >= len(self.labels) - 1:
                for label in self.labels:
                    label.grid_remove()

        else:
            if canvas_index not in self.hidden_canvases:
                return
            self.hidden_canvases.remove(canvas_index)
            for canvases in self.canvases:
                canvases[canvas_index].grid()
            self.labels[canvas_index].grid()
            if len(self.hidden_canvases) < len(self.labels) - 1:
                for index, label in enumerate(self.labels):
                    if not index in self.hidden_canvases:
                        label.grid()
