from enum import Enum
import logging
from logging import CRITICAL, WARNING
import tkinter as tk
from tkinter import ttk
from queue import Empty

from modlunky2.config import Config
from modlunky2.mem import Spel2Process
from modlunky2.mem.state import RunRecapFlags

from .common import Tracker, TrackerWindow, WatcherThread, CommonCommand

logger = logging.getLogger("modlunky2")


class Command(Enum):
    IS_PACIFIST = "is_pacifist"


class PacifistButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.pacifist_button = ttk.Button(
            self,
            text="Pacifist",
            command=self.launch,
        )
        self.pacifist_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.show_kill_count = tk.BooleanVar()
        self.show_kill_count.set(self.modlunky_config.trackers.pacifist.show_kill_count)
        self.show_kill_count_checkbox = ttk.Checkbutton(
            self,
            text="Show Kill Count",
            variable=self.show_kill_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_kill_count,
        )
        self.show_kill_count_checkbox.grid(row=0, column=1, pady=5, padx=5, sticky="nw")

    def toggle_show_kill_count(self):
        self.modlunky_config.trackers.pacifist.show_kill_count = (
            self.show_kill_count.get()
        )
        self.modlunky_config.save()

    def launch(self):
        color_key = self.modlunky_config.tracker_color_key
        self.disable_button()
        self.window = PacifistWindow(
            title="Pacifist Tracker",
            show_kill_count=self.show_kill_count.get(),
            color_key=color_key,
            on_close=self.window_closed,
        )

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.pacifist_button.winfo_exists():
            self.pacifist_button["state"] = tk.NORMAL

    def disable_button(self):
        self.pacifist_button["state"] = tk.DISABLED


class PacifistTracker(Tracker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kills_total = 0

    def initialize(self):
        self.kills_total = 0

    def poll(self, proc: Spel2Process):
        game_state = proc.get_state()
        if game_state is None:
            return None

        run_recap_flags = game_state.run_recap_flags

        player = None
        if game_state.items is not None:
            player = game_state.items.players[0]
        if player is not None and player.inventory is not None:
            self.kills_total = player.inventory.kills_total

        is_pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)
        return {Command.IS_PACIFIST: (is_pacifist, self.kills_total)}


class PacifistWindow(TrackerWindow):
    def __init__(self, *args, show_kill_count=False, **kwargs):
        super().__init__(file_name="pacifist.txt", *args, **kwargs)

        self.show_kill_count = show_kill_count
        self.watcher_thread = WatcherThread(
            recv_queue=self.send_queue,
            send_queue=self.recv_queue,
            tracker=PacifistTracker(),
        )
        self.watcher_thread.start()
        self.after(100, self.after_watcher_thread)

    def get_text(self, is_pacifist, kills_total):
        if is_pacifist:
            return "Pacifist"

        if self.show_kill_count:
            return f"MURDERED {kills_total}!"

        return "MURDERER!"

    def after_watcher_thread(self):
        schedule_again = True
        try:
            while True:
                if self.watcher_thread and not self.watcher_thread.is_alive():
                    self.shut_down(WARNING, "Thread went away. Closing window.")
                    schedule_again = False

                try:
                    msg = self.recv_queue.get_nowait()
                except Empty:
                    break

                if msg["command"] == CommonCommand.DIE:
                    schedule_again = False
                    self.shut_down(CRITICAL, msg["data"])
                elif msg["command"] == CommonCommand.WAIT:
                    self.update_text("Waiting for game...")
                elif msg["command"] == CommonCommand.TRACKER_DATA:
                    (is_pacifist, kills_total) = msg["data"][Command.IS_PACIFIST]
                    new_text = self.get_text(is_pacifist, kills_total)
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
