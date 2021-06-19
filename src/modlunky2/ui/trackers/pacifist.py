import logging
import tkinter as tk
from tkinter import ttk
from queue import Empty

from modlunky2.config import Config
from modlunky2.mem.state import RunRecapFlags

from .common import TrackerWindow, WatcherThread

logger = logging.getLogger("modlunky2")


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
        chroma_key = self.ml_config.config_file.tracker_chroma_key
        self.disable_button()
        PacifistWindow(
            title="Pacifist Tracker",
            chroma_key=chroma_key,
            on_close=self.enable_button,
        )

    def enable_button(self):
        self.pacifist_button["state"] = tk.NORMAL

    def disable_button(self):
        self.pacifist_button["state"] = tk.DISABLED


class PacifistWatcherThread(WatcherThread):
    def poll(self):
        run_recap_flags = self.proc.state.run_recap_flags()
        if run_recap_flags is None:
            self.queue.put(
                {
                    "command": "die",
                    "data": "Failed to read expected address...",
                }
            )
            return False

        is_pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)
        self.queue.put({"command": "is_pacifist", "data": is_pacifist})

        return True


class PacifistWindow(TrackerWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        font = tk.font.Font(family="Helvitica", size=42, weight="bold")
        self.label = tk.Label(
            self, text="Connecting...", bg=self.chroma_key, fg="white", font=font
        )
        self.label.columnconfigure(0, weight=1)
        self.label.rowconfigure(0, weight=1)
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.watcher_thread = PacifistWatcherThread(self.queue)
        self.watcher_thread.start()
        self.after(100, self.after_watcher_thread)

    def after_watcher_thread(self):
        try:
            while True:
                try:
                    msg = self.queue.get_nowait()
                except Empty:
                    break

                if msg["command"] == "die":
                    logger.critical("%s", msg["data"])
                    self.destroy()
                elif msg["command"] == "is_pacifist":
                    is_pacifist = msg["data"]
                    if is_pacifist:
                        self.label.configure(text="Pacifist")
                    else:
                        self.label.configure(text="MURDERER!")
        finally:
            self.after(100, self.after_watcher_thread)

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()
