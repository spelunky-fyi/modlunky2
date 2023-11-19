import tkinter as tk
from tkinter import ttk

from modlunky2.ui.levels.shared.level_canvas import LevelCanvas
from modlunky2.utils import is_windows


class MultiCanvasContainer(tk.Frame):
    def __init__(
        self,
        parent,
        textures_dir,
        canvas_titles,
        zoom_level,
        on_click=None,
        on_shiftclick=None,
        intro_text=None,
        side_by_side=False,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)

        self.on_click = on_click
        self.on_shiftclick = on_shiftclick
        self.side_by_side = side_by_side

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        scrollable_canvas = tk.Canvas(self, bg="#292929")
        scrollable_canvas.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="news")
        scrollable_canvas.columnconfigure(0, weight=1)
        scrollable_canvas.rowconfigure(0, weight=1)

        scrollable_frame = tk.Frame(scrollable_canvas, bg="#343434")
        scrollable_frame.grid(row=0, column=0, sticky="nswe")

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
        canvas_gaps = side_by_side and len(canvas_titles) - 1 or 1
        for column in range(canvas_gaps):
            scrollable_frame.columnconfigure((column + 1) * 2, minsize=50)
        scrollable_frame.columnconfigure(
            (canvas_gaps + 1) * 2, minsize=int(int(width) / 2)
        )
        scrollable_frame.rowconfigure(0, minsize=int(int(height) / 2))
        scrollable_frame.rowconfigure(1, weight=1)
        scrollable_frame.rowconfigure(2, minsize=100)
        scrollable_frame.rowconfigure(4, minsize=int(int(height) / 2))

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

        switches_container = tk.Frame(self, bg="#343434")
        switches_container.grid(row=0, column=0, sticky="nw")
        self.switches_container = switches_container

        self.canvases = []
        self.labels = []
        self.radio_buttons = []
        self.hidden_canvases = []

        # Buttons to switch the active layer.
        switch_variable = tk.StringVar()
        self.switch_variable = switch_variable

        def switch_layer():
            nonlocal switch_variable
            layer = switch_variable.get()
            for index, canvas in enumerate(self.canvases):
                if index == int(layer):
                    canvas.grid()
                else:
                    canvas.grid_remove()

        for index, canvas_title in enumerate(canvas_titles):
            new_canvas = LevelCanvas(
                scrollable_frame,
                textures_dir,
                zoom_level,
                on_click
                and (
                    lambda row, column, is_primary, i=index: self.on_click(
                        i, row, column, is_primary
                    )
                ),
                on_shiftclick
                and (
                    lambda row, column, is_primary, i=index: self.on_shiftclick(
                        i, row, column, is_primary
                    )
                ),
                bg="#343434",
            )
            new_canvas.grid(row=1, column=(side_by_side and (index * 2) or 0) + 1)
            if index != 0 and not side_by_side:
                new_canvas.grid_remove()
            self.canvases.append(new_canvas)

            if len(canvas_titles) > 1:
                if side_by_side:
                    label = tk.Label(
                        scrollable_frame,
                        text=canvas_title,
                        fg="white",
                        bg="#343434",
                    )
                    label.grid(row=2, column=index * 2 + 1, sticky="news")
                    # label.grid_remove()
                    self.labels.append(label)
                else:
                    switch_button = tk.Radiobutton(
                        switches_container,
                        text=canvas_title,
                        variable=switch_variable,
                        indicatoron=False,
                        value=str(index),
                        width=max(len(canvas_title), 10),
                        command=switch_layer,
                    )
                    self.radio_buttons.append(switch_button)

                    switch_button.grid(column=index, row=0, sticky="new")

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
        # If the scrollbar is max size don't bother scrolling
        if scrollbar.get() == (0.0, 1.0):
            return

        canvas.yview_scroll(scroll_dir, "units")

    def _scroll_horizontal(self, scroll_dir, scrollbar, canvas):
        # If the scrollbar is max size don't bother scrolling
        if scrollbar.get() == (0.0, 1.0):
            return

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
        self.canvases[index].replace_tile_at(row, column, image, offset_x, offset_y)

    def configure_size(self, width, height):
        for canvas in self.canvases:
            canvas.configure_size(width, height)

    def set_zoom(self, zoom_level):
        for canvas in self.canvases:
            canvas.set_zoom(zoom_level)

    def clear(self):
        for canvas in self.canvases:
            canvas.clear()

    def hide_grid_lines(self, hide_grid_lines):
        for canvas in self.canvases:
            canvas.hide_grid_lines(hide_grid_lines)

    def hide_room_lines(self, hide_room_lines):
        for canvas in self.canvases:
            canvas.hide_room_lines(hide_room_lines)

    def draw_background(self, theme):
        for canvas in self.canvases:
            canvas.draw_background(theme)

    def draw_background_over_room(self, canvas_index, theme, row, col):
        self.canvases[canvas_index].draw_background_over_room(theme, row, col)

    def draw_grid(self, width=None):
        for canvas in self.canvases:
            canvas.draw_grid(width)

    def draw_room_grid(self, width=None):
        for canvas in self.canvases:
            canvas.draw_room_grid(width)

    def show_intro(self):
        if self.intro:
            self.intro.grid()

    def hide_intro(self):
        if self.intro:
            self.intro.grid_remove()

    def hide_canvas(self, canvas_index, hide):
        if hide:
            if canvas_index in self.hidden_canvases:
                return
            self.hidden_canvases.append(canvas_index)
            selected_canvas = int(self.switch_variable.get())

            self.canvases[canvas_index].grid_remove()
            if self.side_by_side:
                self.labels[canvas_index].grid_remove()

                if len(self.hidden_canvases) >= len(self.canvases) - 1:
                    for label in self.labels:
                        label.grid_remove()
            else:
                self.radio_buttons[canvas_index].grid_remove()
                if canvas_index == selected_canvas:
                    for ind, canv in enumerate(self.canvases):
                        if ind != canvas_index and not ind in self.hidden_canvases:
                            canv.grid()
                            self.switch_variable.set(str(ind))
                            break
                if len(self.hidden_canvases) >= len(self.canvases) - 1:
                    self.switches_container.grid_remove()

        elif self.side_by_side:
            if not canvas_index in self.hidden_canvases:
                return
            self.hidden_canvases.remove(canvas_index)
            self.canvases[canvas_index].grid()
            self.labels[canvas_index].grid()
            if len(self.hidden_canvases) < len(self.canvases) - 1:
                for index, label in enumerate(self.labels):
                    if not index in self.hidden_canvases:
                        label.grid()
        else:
            if not canvas_index in self.hidden_canvases:
                return
            self.hidden_canvases.remove(canvas_index)
            if len(self.canvases) - len(self.hidden_canvases) == 1:
                self.canvaes[canvas_index].grid()

            self.radio_buttons[canvas_index].grid()
            if len(self.hidden_canvases) < len(self.canvases) - 1:
                self.switches_container.grid()
