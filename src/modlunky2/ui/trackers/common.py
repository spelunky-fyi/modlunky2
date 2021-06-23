from enum import Enum
import logging
import threading
import time
import tkinter as tk
from queue import Queue
from tkinter import PhotoImage

from modlunky2.constants import BASE_DIR
from modlunky2.mem import find_spelunky2_pid, Spel2Process
from modlunky2.utils import tb_info

logger = logging.getLogger("modlunky2")


class CommonCommand(Enum):
    DIE = "die"


class WatcherThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.shut_down = False
        self.queue: Queue = queue

        self.proc = None
        self.state = None

    def run(self):
        try:
            self._run()
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed in thread: %s", tb_info())

    def poll(self):
        raise NotImplementedError()

    def _really_poll(self):
        try:
            self.poll()
        except Exception:  # pylint: disable=broad-except
            logger.critical("Unexpected Exception while polling: %s", tb_info())
            self.shutdown()

    def shutdown(self):
        self.shut_down = True

    def send(self, command: CommonCommand, data):
        self.queue.put({"command": command, "data": data})

    def die(self, message):
        self.send(CommonCommand.DIE, message)

    def _run(self):
        shutting_down = False

        pid = find_spelunky2_pid()
        if pid is None:
            self.die("Failed to find running Spel2.exe")
            return

        self.proc = Spel2Process.from_pid(pid)
        if self.proc is None:
            self.die("Failed to open handle to Spel2.exe")
            return

        if self.proc.state is None:
            self.die("Failed to open handle to expected array of bytes")
            return

        while True:
            if not shutting_down and self.shut_down:
                shutting_down = True
                break

            self._really_poll()
            time.sleep(0.1)

        logger.info("Stopped watching process memory")


class TrackerWindow(tk.Toplevel):
    def __init__(self, title, on_close, *args, color_key="#ff00ff", **kwargs):
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
