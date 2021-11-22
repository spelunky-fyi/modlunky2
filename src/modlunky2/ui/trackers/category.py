from enum import Enum
import logging
from logging import CRITICAL, WARNING
import tkinter as tk
from tkinter import ttk
from queue import Empty

from PIL import Image, ImageTk

from modlunky2.config import Config
from modlunky2.constants import BASE_DIR

from modlunky2.ui.trackers.common import TrackerWindow, WatcherThread, CommonCommand
from modlunky2.ui.trackers.runstate import RunState

logger = logging.getLogger("modlunky2")


ICON_PATH = BASE_DIR / "static/images"


class Command(Enum):
    LABEL = "label"


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)

        self.cat_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "cat2.png").resize((24, 24), Image.ANTIALIAS)
        )

        self.category_button = ttk.Button(
            self,
            image=self.cat_icon,
            text="Category",
            compound="left",
            command=self.launch,
        )
        self.category_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.always_show_modifiers = tk.BooleanVar()
        self.always_show_modifiers.set(
            modlunky_config.trackers.category.always_show_modifiers
        )
        self.always_show_modifiers_checkbox = ttk.Checkbutton(
            self,
            text="Always Show Modifiers",
            variable=self.always_show_modifiers,
            onvalue=True,
            offvalue=False,
            command=self.toggle_always_show_modifiers,
        )
        self.always_show_modifiers_checkbox.grid(
            row=0, column=1, pady=5, padx=5, sticky="nw"
        )

    def toggle_always_show_modifiers(self):
        self.modlunky_config.trackers.category.always_show_modifiers = (
            self.always_show_modifiers.get()
        )
        self.modlunky_config.save()

    def launch(self):
        color_key = self.modlunky_config.tracker_color_key
        self.disable_button()
        CategoryWindow(
            title="Category Tracker",
            color_key=color_key,
            on_close=self.enable_button,
            always_show_modifiers=self.always_show_modifiers.get(),
        )

    def enable_button(self):
        # If we're in the midst of destroy() the button might not exist
        if self.category_button.winfo_exists():
            self.category_button["state"] = tk.NORMAL

    def disable_button(self):
        self.category_button["state"] = tk.DISABLED


class CategoryWatcherThread(WatcherThread):
    def __init__(self, *args, always_show_modifiers=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_total = None
        self.run_state = None
        self.always_show_modifiers = always_show_modifiers

    def initialize(self):
        self.time_total = 0
        self.run_state = RunState(
            always_show_modifiers=self.always_show_modifiers,
        )

    def poll(self):
        game_state = self.proc.get_state()
        if game_state is None:
            self.shutdown()
            return
        # Check if we've reset, if so, reinitialize
        new_time_total = game_state.time_total
        if new_time_total < self.time_total:
            self.initialize()
        self.time_total = new_time_total

        self.run_state.update(game_state)
        label = self.run_state.get_display(game_state.screen)
        self.send(Command.LABEL, label)


class CategoryWindow(TrackerWindow):

    POLL_INTERVAL = 16

    def __init__(self, *args, always_show_modifiers=False, **kwargs):
        super().__init__(file_name="category.txt", *args, **kwargs)

        self.watcher_thread = CategoryWatcherThread(
            self.queue,
            always_show_modifiers=always_show_modifiers,
        )
        self.watcher_thread.start()
        self.after(self.POLL_INTERVAL, self.after_watcher_thread)

    def after_watcher_thread(self):
        schedule_again = True
        try:
            while True:
                if self.watcher_thread and not self.watcher_thread.is_alive():
                    self.shut_down(WARNING, "Thread went away. Closing window.")
                    schedule_again = False

                try:
                    msg = self.queue.get_nowait()
                except Empty:
                    break

                if msg["command"] == CommonCommand.DIE:
                    schedule_again = False
                    self.shut_down(CRITICAL, msg["data"])
                elif msg["command"] == CommonCommand.WAIT:
                    self.update_text("Waiting for game...")
                elif msg["command"] == Command.LABEL:
                    self.update_text(msg["data"])

        finally:
            if schedule_again:
                self.after(self.POLL_INTERVAL, self.after_watcher_thread)

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()
