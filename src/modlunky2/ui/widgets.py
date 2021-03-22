import os
import re
from queue import Empty

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


# Adapted from https://beenje.github.io/blog/posts/logging-to-a-tkinter-scrolledtext-widget/
class ConsoleWindow(tk.Frame):
    def __init__(self, queue_handler, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(self, height=7, state="disabled")
        self.scrolled_text.pack(expand=True, fill="both")
        self.scrolled_text.configure(font="TkFixedFont")
        self.scrolled_text.tag_config("INFO", foreground="green")
        self.scrolled_text.tag_config("DEBUG", foreground="gray")
        self.scrolled_text.tag_config("WARNING", foreground="orange")
        self.scrolled_text.tag_config("ERROR", foreground="red")
        self.scrolled_text.tag_config("CRITICAL", foreground="red", underline=1)

        # Create a logging handler using a queue
        self.queue_handler = queue_handler

        # Start polling messages from the queue
        self.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state="normal")
        self.scrolled_text.insert(tk.END, msg + "\n", record.levelname)
        self.scrolled_text.configure(state="disabled")
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.queue_handler.log_queue.get(block=False)
            except Empty:
                break
            else:
                self.display(record)
        self.after(100, self.poll_log_queue)

    def close(self):
        pass


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text

        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)

        self.tooltip = None
        self.label = None

    def set_geometry(self, event):
        root = self.widget.winfo_toplevel()
        screen_width = root.winfo_screenwidth()
        (width, _, _, _) = list(map(int, re.split(r"[x+-]", self.tooltip.geometry())))

        x_coord = event.x_root + 15
        if event.x_root > screen_width * 0.70:
            x_coord = event.x_root - width - 15

        y_coord = event.y_root + 10

        self.tooltip.geometry(f"+{x_coord}+{y_coord}")

    def on_motion(self, event):
        self.set_geometry(event)

    def on_enter(self, event):
        self.tooltip = tk.Toplevel()
        self.tooltip.overrideredirect(True)
        self.set_geometry(event)

        self.label = tk.Label(self.tooltip, text=self.text)
        self.label.pack()

    def on_leave(self, _event):
        self.tooltip.destroy()


class Tab(ttk.Frame):
    """ Base class that all tabs should inherit from."""

    show_console = True
    save_needed = False

    def on_load(self):
        """ Called whenever the tab is loaded."""


# Adapted from https://gist.github.com/JackTheEngineer/81df334f3dcff09fd19e4169dd560c59
class ScrollableFrame(ttk.LabelFrame):
    def __init__(self, parent, *args, **kw):

        super().__init__(parent, *args, **kw)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # create a canvas object and a vertical scrollbar for scrolling it
        self.vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.vscrollbar.grid(row=0, column=1, sticky="nse")

        self.canvas = tk.Canvas(self, yscrollcommand=self.vscrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nswe")
        self.vscrollbar.config(command=self.canvas.yview)

        # reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.interior_id = self.canvas.create_window(
            0, 0, window=self.scrollable_frame, anchor=tk.NW
        )

        self.scrollable_frame.bind("<Configure>", self._configure_interior)
        self.canvas.bind("<Configure>", self._configure_canvas)
        self.canvas.bind("<Enter>", self._bind_to_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_from_mousewheel)

    def _configure_interior(self, _event):
        # update the scrollbars to match the size of the inner frame
        size = (
            self.scrollable_frame.winfo_reqwidth(),
            self.scrollable_frame.winfo_reqheight(),
        )
        self.canvas.config(scrollregion="0 0 %s %s" % size)

        if self.scrollable_frame.winfo_reqwidth() != self.winfo_width():
            # update the canvas's width to fit the inner frame
            self.canvas.config(width=self.scrollable_frame.winfo_reqwidth())

    def _configure_canvas(self, _event):
        if self.scrollable_frame.winfo_reqwidth() != self.winfo_width():
            # update the inner frame's width to fill the canvas
            self.canvas.itemconfigure(self.interior_id, width=self.winfo_width())

    # This can now handle either windows or linux platforms

    def _on_mousewheel(self, event):
        scroll_dir = None
        if event.num == 5 or event.delta == -120:
            scroll_dir = 1
        elif event.num == 4 or event.delta == 120:
            scroll_dir = -1

        if scroll_dir is None:
            return

        # If the scrollbar is max size don't bother scrolling
        if self.vscrollbar.get() == (0.0, 1.0):
            return

        self.canvas.yview_scroll(scroll_dir, "units")

    def _bind_to_mousewheel(self, _event):
        if "nt" in os.name:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else:
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_from_mousewheel(self, _event):
        if "nt" in os.name:
            self.canvas.unbind_all("<MouseWheel>")
        else:
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")


class PopupWindow(ttk.Frame):
    def __init__(self, title, config, *args, **kwargs):
        self.shutting_down = False
        self.win = tk.Toplevel()
        self.config = config

        self.label_frame = ttk.LabelFrame(self.win, text=title)
        self.label_frame.columnconfigure(0, weight=1)
        self.label_frame.rowconfigure(0, weight=1)
        self.label_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        super().__init__(self.label_frame, *args, **kwargs)

        self.win.title(title)
        if "nt" in os.name:
            self.win.attributes("-toolwindow", True)
        else:
            self.win.attributes("-alpha", True)

        main_geometry = tuple(
            map(int, re.split(r"[+x]", self.config.config_file.geometry))
        )

        self.win.geometry(
            "+{}+{}".format(
                main_geometry[2] + 400,
                main_geometry[3] + 200,
            )
        )
        self.win.resizable(False, False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.win.bind("<Escape>", self.on_escape)

    def on_escape(self, _event=None):
        self.destroy()

    def destroy(self):
        # This Frame is a child element of the Toplevel so destroying the
        # toplevel will eventually call this method again which would be
        # infinitely recursive.
        #
        # Track the first time this is called which will propagate the destroy
        # to the Toplevel, afterwords call the super's destroy instead.
        if not self.shutting_down:
            self.shutting_down = True
            self.win.destroy()
            return

        super().destroy()
