from enum import Enum
import logging
import tkinter as tk
from tkinter import ttk
from queue import Empty

from modlunky2.config import Config
from modlunky2.mem import Spel2Process
from modlunky2.mem.state import RunRecapFlags

from .common import TrackerWindow, WatcherThread, CommonCommand

logger = logging.getLogger("modlunky2")


class Command(Enum):
    LABEL = "label"


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.ml_config = ml_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)

        self.category_button = ttk.Button(
            self,
            text="Category",
            command=self.launch,
        )
        self.category_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

    def launch(self):
        chroma_key = self.ml_config.config_file.tracker_chroma_key
        self.disable_button()
        CategoryWindow(
            title="Category Tracker",
            chroma_key=chroma_key,
            on_close=self.enable_button,
        )

    def enable_button(self):
        self.category_button["state"] = tk.NORMAL

    def disable_button(self):
        self.category_button["state"] = tk.DISABLED


class FailedMemoryRead(Exception):
    """Failed to read memory from Spelunky2 process."""


class ModifierState:
    def __init__(self, proc: Spel2Process):
        self._proc = proc

        self.pacifist = True
        self.no_gold = True
        self.no_tp = True

    def update_pacifist(self, run_recap_flags):
        self.pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)

    def update_no_gold(self, run_recap_flags):
        self.no_gold = bool(run_recap_flags & RunRecapFlags.NO_GOLD)

    def update_no_tp(self):
        pass

    def update(self):
        run_recap_flags = self._proc.state.run_recap_flags()
        if run_recap_flags is None:
            raise FailedMemoryRead("Failed to read run recap flags...")

        if self.pacifist:
            self.update_pacifist(run_recap_flags)

        if self.no_gold:
            self.update_no_gold(run_recap_flags)

        if self.no_tp:
            self.update_no_tp()

    def get_display(self, show_pacifist, show_no_gold, show_no_tp):
        out = []

        if show_no_tp and self.no_tp:
            out.append("No TP")

        if show_pacifist and self.pacifist:
            out.append("Pacifist")

        if show_no_gold and self.no_gold:
            out.append("No Gold")

        return " ".join(out)


class CategoryWatcherThread(WatcherThread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_total = None
        self.modifier_state = None

    def initialize(self):
        self.time_total = 0
        self.modifier_state = ModifierState(self.proc)

    def get_time_total(self):
        time_total = self.proc.state.time_total()
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

        self.modifier_state.update()
        label = self.modifier_state.get_display(True, True, True)
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        font = tk.font.Font(family="Helvitica", size=42, weight="bold")
        self.label = tk.Label(
            self, text="Connecting...", bg=self.chroma_key, fg="white", font=font
        )
        self.label.columnconfigure(0, weight=1)
        self.label.rowconfigure(0, weight=1)
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.watcher_thread = CategoryWatcherThread(self.queue)
        self.watcher_thread.start()
        self.after(100, self.after_watcher_thread)

    def after_watcher_thread(self):
        schedule_again = True
        try:
            while True:
                if self.watcher_thread and not self.watcher_thread.is_alive():
                    logger.warning("Thread went away. Closing window.")
                    schedule_again = False
                    self.destroy()

                try:
                    msg = self.queue.get_nowait()
                except Empty:
                    break

                if msg["command"] == CommonCommand.DIE:
                    logger.critical("%s", msg["data"])
                    schedule_again = False
                    self.destroy()
                elif msg["command"] == Command.LABEL:
                    self.label.configure(text=msg["data"])

        finally:
            if schedule_again:
                self.after(100, self.after_watcher_thread)

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()
