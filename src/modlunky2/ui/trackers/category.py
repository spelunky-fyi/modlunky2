from enum import Enum
import logging
from logging import CRITICAL, WARNING
import tkinter as tk
from tkinter import ttk
from queue import Empty

from PIL import Image, ImageTk

from modlunky2.config import Config
from modlunky2.constants import BASE_DIR

from .common import TrackerWindow, WatcherThread, CommonCommand
from .runstate import RunState, FailedMemoryRead

logger = logging.getLogger("modlunky2")


ICON_PATH = BASE_DIR / "static/images"


class Command(Enum):
    LABEL = "label"


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.ml_config = ml_config
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

    def launch(self):
        color_key = self.ml_config.config_file.tracker_color_key
        self.disable_button()
        CategoryWindow(
            title="Category Tracker",
            color_key=color_key,
            on_close=self.enable_button,
        )

    def enable_button(self):
        self.category_button["state"] = tk.NORMAL

    def disable_button(self):
        self.category_button["state"] = tk.DISABLED


class CategoryWatcherThread(WatcherThread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_total = None
        self.run_state = None

    def initialize(self):
        self.time_total = 0
        self.run_state = RunState(self.proc)

    def get_time_total(self):
        time_total = self.proc.state.time_total
        if time_total is None:
            raise FailedMemoryRead("Failed to read time_total")
        return time_total

    def _poll(self):
        # If we've never been initialized go ahead and do that now.
        if self.time_total is None:
            self.initialize()

        # Check if we've reset, if so, reinitialize
        new_time_total = self.get_time_total()
        if new_time_total < self.time_total:
            self.initialize()
        self.time_total = new_time_total

        self.run_state.update()
        label = self.run_state.get_display()
        self.send(Command.LABEL, label)

    def poll(self):
        try:
            self._poll()
        except FailedMemoryRead as err:
            logger.critical(
                "Failed to read expected memory... (%s). Shutting down.", err
            )
            self.shutdown()


class CategoryWindow(TrackerWindow):

    POLL_INTERVAL = 16

    def __init__(self, *args, **kwargs):
        super().__init__(file_name="category.txt", *args, **kwargs)

        self.watcher_thread = CategoryWatcherThread(self.queue)
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
