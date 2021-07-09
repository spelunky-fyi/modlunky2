from enum import Enum
import logging
import threading
import time
import tkinter as tk
from queue import Queue
from tkinter import PhotoImage

from modlunky2.config import DATA_DIR
from modlunky2.constants import BASE_DIR
from modlunky2.mem import find_spelunky2_pid, Spel2Process
from modlunky2.utils import tb_info

logger = logging.getLogger("modlunky2")

TRACKERS_DIR = DATA_DIR / "trackers"


class CommonCommand(Enum):
    DIE = "die"
    WAIT = "wait"


class WatcherThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.shut_down = False
        self.queue: Queue = queue

        self.proc = None

    def run(self):
        try:
            self._run()
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed in thread: %s", tb_info())

    def initialize(self):
        raise NotImplementedError()

    def poll(self):
        raise NotImplementedError()

    def _really_poll(self):
        try:
            self.poll()
        except Exception:  # pylint: disable=broad-except
            # If the game is no longer running, we assume that caused the failure
            if self.proc.running():
                logger.critical("Unexpected Exception while polling: %s", tb_info())
                self.shutdown()

    def shutdown(self):
        self.shut_down = True

    def send(self, command: CommonCommand, data):
        self.queue.put({"command": command, "data": data})

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

        if proc.get_feedcode() is None:
            # Game might still be starting, we should try again
            return False

        if proc.state is None:
            self.die("Failed to open handle to expected array of bytes")
            return False

        self.proc = proc
        self.initialize()
        return True

    def _run(self):
        shutting_down = False
        if not self._attach():
            self.wait()

        while True:
            if not shutting_down and self.shut_down:
                shutting_down = True
                break

            if self.proc is None:
                self._attach()
            elif self.proc.running():
                self._really_poll()
            else:
                self.wait()
                self._attach()

            time.sleep(0.1)

        logger.info("Stopped watching process memory")


class TrackerWindow(tk.Toplevel):
    def __init__(
        self, title, on_close, file_name, *args, color_key="#ff00ff", **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.attributes("-topmost", "true")
        self.on_close = on_close
        self.queue = Queue()
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

    def dragwin(self, _event):
        x_coord = self.winfo_pointerx() - self._offsetx
        y_coord = self.winfo_pointery() - self._offsety
        self.geometry("+{x}+{y}".format(x=x_coord, y=y_coord))

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
