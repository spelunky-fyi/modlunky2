import logging
import tkinter as tk

from queue import Empty

from modlunky2.mem.state import RunRecapFlags

from .common import TrackerWindow, WatcherThread

logger = logging.getLogger("modlunky2")


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
