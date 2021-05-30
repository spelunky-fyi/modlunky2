import logging
import time
import threading
import tkinter as tk
from queue import Queue, Empty
from tkinter import PhotoImage, ttk


from modlunky2.constants import BASE_DIR
from modlunky2.ui.widgets import Tab
from modlunky2.utils import tb_info
from modlunky2.winmem import find_spelunky2_pid, Spel2Process

logger = logging.getLogger("modlunky2")


class PacifistWindow(tk.Toplevel):
    def __init__(self, on_close, *args, **kwargs):
        super().__init__(*args, **kwargs)
        chroma_key = "#ff00ff"
        self.attributes("-topmost", "true")
        self.on_close = on_close
        self.queue = Queue()

        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.iconphoto(False, self.icon_png)

        self.configure(bg=chroma_key)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        font = tk.font.Font(family="Helvitica", size=42, weight="bold")
        self.label = tk.Label(
            self, text="Connecting...", bg=chroma_key, fg="white", font=font
        )
        self.label.columnconfigure(0, weight=1)
        self.label.rowconfigure(0, weight=1)
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.title("Pacifist Tracker")

        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(label="Close", command=self.destroy)
        self.bind("<Button-3>", self.do_context_menu)

        # self.overrideredirect(True)
        self.focus_force()
        self.lift()

        self._offsetx = 0
        self._offsety = 0
        self.bind("<Button-1>", self.clickwin)
        self.bind("<B1-Motion>", self.dragwin)

        self.watcher_thread = WatcherThread(self.queue)
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

    def dragwin(self, _event):
        x_coord = self.winfo_pointerx() - self._offsetx
        y_coord = self.winfo_pointery() - self._offsety
        self.geometry("+{x}+{y}".format(x=x_coord, y=y_coord))

    def clickwin(self, event):
        self._offsetx = event.x
        self._offsety = event.y

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()

    def do_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()


class WatcherThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.shut_down = False
        self.queue: Queue = queue

    def run(self):
        try:
            self._run()
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed in thread: %s", tb_info())

    def _run(self):
        shutting_down = False

        pid = find_spelunky2_pid()
        if pid is None:
            self.queue.put(
                {"command": "die", "data": "Failed to find running Spel2.exe"}
            )
            return

        proc = Spel2Process.from_pid(pid)
        if proc is None:
            self.queue.put(
                {"command": "die", "data": "Failed to open handle to Spel2.exe"}
            )
            return

        feedcode = None
        for page in proc.memory_pages():
            result = proc.find_in_page(page, b"\x00\xde\xc0\xed\xfe")
            if result:
                feedcode = result
                break

        if feedcode is None:
            self.queue.put(
                {
                    "command": "die",
                    "data": "Failed to open handle to expected array of bytes",
                }
            )
            return

        journal_flags_addr = feedcode + 0x995
        while True:
            if not shutting_down and self.shut_down:
                shutting_down = True
                break

            journal_flags = proc.read_u32(journal_flags_addr)
            if journal_flags is None:
                self.queue.put(
                    {
                        "command": "die",
                        "data": "Failed to read expected address...",
                    }
                )
                return

            is_pacifist = bool(journal_flags & 1)
            self.queue.put({"command": "is_pacifist", "data": is_pacifist})
            time.sleep(0.1)

        logger.info("Stopped watching process memory")


class TrackersTab(Tab):
    def __init__(self, tab_control, modlunky_config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.modlunky_config = modlunky_config

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.trackers_frame = ttk.LabelFrame(self, text="Trackers")
        self.trackers_frame.grid(sticky="nsew")

        self.trackers_frame.rowconfigure(1, minsize=60)
        self.trackers_frame.rowconfigure(2, weight=1)
        self.trackers_frame.columnconfigure(0, weight=1)

        self.button_pacifist = ttk.Button(
            self.trackers_frame,
            text="Pacifist",
            command=self.pacifist,
            state=tk.DISABLED,
        )
        self.button_pacifist.grid(row=1, column=0, pady=5, padx=5, sticky="nswe")

        self.watcher_thread = None
        self.render_buttons()

    def render_buttons(self):
        if self.watcher_thread is None:
            self.enable_pacifist_button()
        else:
            self.enable_pacifist_button()

    def enable_pacifist_button(self):
        self.button_pacifist["state"] = tk.NORMAL

    def disable_pacifist_button(self):
        self.button_pacifist["state"] = tk.DISABLED

    def pacifist(self):
        self.disable_pacifist_button()
        PacifistWindow(on_close=self.on_pacifist_close)

    def on_pacifist_close(self):
        self.enable_pacifist_button()
