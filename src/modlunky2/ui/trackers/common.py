from abc import ABC, abstractmethod
from enum import Enum
import logging
import threading
import time
import tkinter as tk
from queue import Empty, Queue
from tkinter import PhotoImage
from typing import Any, Dict, Generic, Optional, TypeVar

from modlunky2.config import DATA_DIR, CommonTrackerConfig
from modlunky2.constants import BASE_DIR
from modlunky2.mem import FeedcodeNotFound, find_spelunky2_pid, Spel2Process
from modlunky2.mem.memrauder.model import ScalarCValueConstructionError
from modlunky2.utils import tb_info

logger = logging.getLogger("modlunky2")

TRACKERS_DIR = DATA_DIR / "trackers"


class CommonCommand(Enum):
    CONFIG = "config"
    TRACKER_DATA = "tracker-data"
    DIE = "die"
    WAIT = "wait"


class WindowKey(Enum):
    DISPLAY_STRING = "display-string"


ConfigType = TypeVar("ConfigType", bound=CommonTrackerConfig)


class Tracker(ABC, Generic[ConfigType]):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def poll(self, proc: Spel2Process, config: ConfigType) -> Optional[Dict[str, Any]]:
        pass


class WatcherThread(threading.Thread, Generic[ConfigType]):
    POLL_INTERVAL = 0.016
    ATTACH_INTERVAL = 1.0

    def __init__(
        self,
        recv_queue: Queue,
        send_queue: Queue,
        tracker: Tracker[ConfigType],
        config: ConfigType,
    ):
        super().__init__()
        self.shut_down = False
        self.recv_queue = recv_queue
        self.send_queue = send_queue
        self.tracker = tracker
        self.config = config

        self.proc = None

    def run(self):
        try:
            self._run()
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed in thread: %s", tb_info())

    def poll(self):
        try:
            data = self.tracker.poll(self.proc, self.config)
            if data is None:
                self.shutdown()
            else:
                self.send(CommonCommand.TRACKER_DATA, data)
        except (FeedcodeNotFound, ScalarCValueConstructionError):
            # These exceptions are likely transient
            return
        except Exception:  # pylint: disable=broad-except
            # If the game is no longer running, we assume that caused the failure
            if self.proc.running():
                logger.critical("Unexpected Exception while polling: %s", tb_info())
                self.shutdown()

    def shutdown(self):
        self.shut_down = True

    def send(self, command: CommonCommand, data):
        self.send_queue.put({"command": command, "data": data})

    def die(self, message):
        self.send(CommonCommand.DIE, message)

    def wait(self):
        self.proc = None
        self.send(CommonCommand.WAIT, None)

    def _attach(self):
        pid = find_spelunky2_pid()
        if pid is None:
            # This is fine, we'll try again later
            return False

        proc = Spel2Process.from_pid(pid)
        if proc is None:
            self.die("Failed to open handle to Spel2.exe")
            return False

        try:
            proc.get_state()
        except (FeedcodeNotFound, ScalarCValueConstructionError):
            # Game might still be starting, we should try again
            return False

        self.proc = proc
        self.tracker.initialize()
        return True

    def _run(self):
        shutting_down = False
        if not self._attach():
            self.wait()

        while True:
            if not shutting_down and self.shut_down:
                shutting_down = True
                break

            interval = self.POLL_INTERVAL
            if self.proc is None:
                if not self._attach():
                    interval = self.ATTACH_INTERVAL
            elif self.proc.running():
                self.poll()
            else:
                self.wait()
                interval = self.ATTACH_INTERVAL

            time.sleep(interval)

        logger.info("Stopped watching process memory")


class TrackerWindow(tk.Toplevel, Generic[ConfigType]):
    POLL_INTERVAL = 16

    def __init__(
        self,
        title,
        on_close,
        file_name: str,
        tracker: Tracker,
        config: ConfigType,
        *args,
        color_key="#ff00ff",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.attributes("-topmost", "true")
        self.on_close = on_close
        self.recv_queue = Queue()
        self.send_queue = Queue()
        self.watcher_thread = WatcherThread(
            recv_queue=self.send_queue,
            send_queue=self.recv_queue,
            tracker=tracker,
            config=config,
        )
        self.color_key = color_key

        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.iconphoto(False, self.icon_png)

        self.configure(bg=color_key)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.title(title)

        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(label="Close", command=self.destroy)
        self.bind("<Button-3>", self.do_context_menu)

        self.focus_force()
        self.lift()

        self._offsetx = 0
        self._offsety = 0
        self.bind("<Button-1>", self.clickwin)
        self.bind("<B1-Motion>", self.dragwin)

        font = tk.font.Font(family="Helvitica", size=42, weight="bold")

        self.text = "Connecting..."
        self.label = tk.Label(
            self, text=self.text, bg=self.color_key, fg="white", font=font
        )
        self.label.columnconfigure(0, weight=1)
        self.label.rowconfigure(0, weight=1)
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        TRACKERS_DIR.mkdir(parents=True, exist_ok=True)
        self.text_file = TRACKERS_DIR / file_name
        with self.text_file.open("w") as handle:
            handle.write(self.text)

        self.watcher_thread.start()
        self.after(self.POLL_INTERVAL, self.after_watcher_thread)

    def dragwin(self, _event):
        x_coord = self.winfo_pointerx() - self._offsetx
        y_coord = self.winfo_pointery() - self._offsety
        self.geometry(f"+{x_coord}+{y_coord}")

    def clickwin(self, event):
        self._offsetx = event.x
        self._offsety = event.y

    def do_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def update_text(self, new_text):
        if new_text == self.text:
            return
        self.text = new_text
        self.label.configure(text=self.text)
        with self.text_file.open("w") as handle:
            handle.write(new_text)

    def shut_down(self, level, message):
        logger.log(level, "%s", message)
        self.destroy()

    def destroy(self) -> None:
        with self.text_file.open("w") as handle:
            handle.write("Not running")
        return super().destroy()

    def after_watcher_thread(self):
        schedule_again = True
        try:
            while True:
                if self.watcher_thread and not self.watcher_thread.is_alive():
                    self.shut_down(logging.WARNING, "Thread went away. Closing window.")
                    schedule_again = False

                try:
                    msg = self.recv_queue.get_nowait()
                except Empty:
                    break

                if msg["command"] == CommonCommand.DIE:
                    schedule_again = False
                    self.shut_down(logging.CRITICAL, msg["data"])
                elif msg["command"] == CommonCommand.WAIT:
                    self.update_text("Waiting for game...")
                elif msg["command"] == CommonCommand.TRACKER_DATA:
                    self.update_text(msg["data"][WindowKey.DISPLAY_STRING])

        finally:
            if schedule_again:
                self.after(self.POLL_INTERVAL, self.after_watcher_thread)

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()
