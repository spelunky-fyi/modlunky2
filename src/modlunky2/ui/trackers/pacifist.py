from enum import Enum
import logging
from logging import CRITICAL, WARNING
import tkinter as tk
from tkinter import ttk
from queue import Empty

from modlunky2.config import Config
from modlunky2.mem.state import RunRecapFlags

from .common import TrackerWindow, WatcherThread, CommonCommand

logger = logging.getLogger("modlunky2")


class Command(Enum):
    IS_PACIFIST = "is_pacifist"


class PacifistButtons(ttk.Frame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.ml_config = ml_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)

        self.pacifist_button = ttk.Button(
            self,
            text="Pacifist",
            command=self.launch,
        )
        self.pacifist_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

    def launch(self):
        color_key = self.ml_config.config_file.tracker_color_key
        self.disable_button()
        PacifistWindow(
            title="Pacifist Tracker",
            color_key=color_key,
            on_close=self.enable_button,
        )

    def enable_button(self):
        self.pacifist_button["state"] = tk.NORMAL

    def disable_button(self):
        self.pacifist_button["state"] = tk.DISABLED


class PacifistWatcherThread(WatcherThread):
    def initialize(self):
        #  Nothing to initialize
        return

    def poll(self):
        run_recap_flags = self.proc.state.run_recap_flags
        if run_recap_flags is None:
            self.die("Failed to read expected address...")
            self.shutdown()

        is_pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)
        self.send(Command.IS_PACIFIST, is_pacifist)


class PacifistWindow(TrackerWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(file_name="pacifist.txt", *args, **kwargs)

        self.watcher_thread = PacifistWatcherThread(self.queue)
        self.watcher_thread.start()
        self.after(100, self.after_watcher_thread)

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
                elif msg["command"] == Command.IS_PACIFIST:
                    is_pacifist = msg["data"]
                    new_text = "Pacifist" if is_pacifist else "MURDERER!"
                    self.update_text(new_text)

        finally:
            if schedule_again:
                self.after(100, self.after_watcher_thread)

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()
