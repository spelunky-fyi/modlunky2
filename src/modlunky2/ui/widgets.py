import os
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

        self.tooltip = None
        self.label = None

    def on_enter(self, event):
        self.tooltip = tk.Toplevel()
        self.tooltip.overrideredirect(True)
        self.tooltip.geometry(f"+{event.x_root+15}+{event.y_root+10}")

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


class ScrollableFrame(ttk.LabelFrame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=0, column=0, sticky="nswe")

        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollbar.grid(row=0, column=1, sticky="nse")
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Enter>", self._bind_to_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_from_mousewheel)

    def _on_mousewheel(self, event):
        scroll_dir = None
        if event.num == 5 or event.delta == -120:
            scroll_dir = 1
        elif event.num == 4 or event.delta == 120:
            scroll_dir = -1

        if scroll_dir is None:
            return

        # If the scrollbar is max size don't bother scrolling
        if self.scrollbar.get() == (0.0, 1.0):
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


class ToggledFrame(tk.Frame):
    def __init__(self, parent, text, *args, **options):
        tk.Frame.__init__(self, parent, *args, **options)

        self.show = tk.IntVar()
        self.show.set(0)

        self.title_frame = ttk.Frame(self)
        self.title_frame.pack(fill="x", expand=1)

        ttk.Label(self.title_frame, text=text).pack(side="left", fill="x", expand=1)

        self.toggle_button = ttk.Checkbutton(
            self.title_frame,
            width=2,
            text="+",
            command=self.toggle,
            variable=self.show,
            style="Toolbutton",
        )
        self.toggle_button.pack(side="left")

        self.sub_frame = tk.Frame(self, relief="sunken", borderwidth=1)

    def toggle(self):
        if bool(self.show.get()):
            self.sub_frame.pack(fill="x", expand=1)
            self.toggle_button.configure(text="-")
        else:
            self.sub_frame.forget()
            self.toggle_button.configure(text="+")
