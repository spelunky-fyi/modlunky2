import time
import logging
import tkinter as tk
from tkinter import PhotoImage, ttk
from multiprocessing import Queue

from modlunky2.constants import BASE_DIR, IS_EXE
from modlunky2.updater import self_update
from modlunky2.version import current_version, latest_version

from .tasks import TaskManager, PING_INTERVAL
from .config import ConfigTab
from .extract import ExtractTab
from .levels import LevelsTab
from .pack import PackTab
from .widgets import ConsoleWindow
from .logs import QueueHandler, register_queue_handler

logger = logging.getLogger("modlunky2")


MIN_WIDTH = 1280
MIN_HEIGHT = 900


class ModlunkyUI:
    def __init__(self, config, data_dir):
        self.config = config
        self.data_dir = data_dir

        self.current_version = current_version()
        self.latest_version = latest_version()

        if IS_EXE:
            if self.latest_version is None or self.current_version is None:
                self.needs_update = False
            else:
                self.needs_update = self.current_version < self.latest_version
        else:
            self.needs_update = False

        self._shutdown_handlers = []
        self._shutting_down = False

        self.log_queue = Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        register_queue_handler(self.queue_handler)
        self.task_manager = TaskManager(self.log_queue)

        self.root = tk.Tk(className="Modlunky2")  # Equilux Black
        self.root.title("Modlunky 2")
        self.root.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        # self.root.resizable(False, False)
        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.root.iconphoto(False, self.icon_png)

        if self.needs_update:
            update_frame = ttk.LabelFrame(self.root, text="Modlunky2 Update Available")
            update_frame.grid(row=0, column=0, sticky="nswe")
            update_frame.columnconfigure(0, weight=1)
            update_frame.rowconfigure(0, weight=1)

            update_button = tk.Button(
                update_frame,
                text="Update Now!",
                command=self.update,
                bg="#bfbfbf",
                font="sans 12 bold",
            )
            update_button.grid(column=0, row=0, sticky="nswe")

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.tabs = {}
        self.tab_control = ttk.Notebook(self.root)

        self.register_tab(
            "Pack Assets",
            PackTab(
                tab_control=self.tab_control,
                config=config,
                task_manager=self.task_manager,
            ),
        )
        self.register_tab(
            "Extract Assets",
            ExtractTab(
                tab_control=self.tab_control,
                config=config,
                task_manager=self.task_manager,
            ),
        )
        self.register_tab(
            "Level Editor",
            LevelsTab(
                tab_control=self.tab_control,
                config=config,
            ),
        )

        self.register_tab(
            "Config",
            ConfigTab(
                tab_control=self.tab_control,
                config=config,
            ),
        )

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.tab_control.grid(column=0, row=1, padx=2, pady=(4, 0), sticky="nsew")

        self.console_frame = ttk.LabelFrame(self.root, text="Console")
        self.console_frame.grid(row=2, column=0, padx=5, pady=(5, 0), sticky="nswe")
        self.console_frame.columnconfigure(0, weight=1)
        self.console_frame.rowconfigure(0, weight=1)

        self.console = ConsoleWindow(self.queue_handler, self.console_frame)
        self.console.grid(column=0, row=0, padx=2, pady=2, sticky="ew")

        self.version_label = tk.Label(
            self.root, text=f"v{self.current_version}", font="Helvitica 9 italic"
        )
        self.version_label.grid(column=0, row=3, padx=5, sticky="e")

        self.task_manager.start_process()
        self.last_ping = time.time()
        self.root.after(100, self.after_cb)

    def after_cb(self):
        if not self.task_manager.is_alive():
            # Worker process went away but we're shutting down so just return
            if self._shutting_down:
                return

            # Worker process went away unexpectedly... Restart it.
            logger.critical("Worker process went away... Restarting it.")
            self.task_manager.start_process()
            self.root.after(100, self.after_cb)
            return

        # Send regular pings so the worker process knows
        # we're still alive.
        now = time.time()
        if now - self.last_ping > PING_INTERVAL:
            self.last_ping = now
            self.task_manager.ping()

        while True:
            msg = self.task_manager.receive_message()
            if msg is None:
                self.root.after(100, self.after_cb)
                return

            self.task_manager.dispatch(msg)

    def update(self):
        try:
            self_update()
            self.quit()
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to update...")

    def on_tab_change(self, event):
        tab = event.widget.tab("current")["text"]
        self.tabs[tab].on_load()

    def register_tab(self, name, obj):
        self.tabs[name] = obj
        self.tab_control.add(obj, text=name)

    def quit(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        logger.info("Shutting Down.")
        for handler in self._shutdown_handlers:
            handler()

        self.task_manager.quit()
        self.root.quit()
        self.root.destroy()

    def register_shutdown_handler(self, func):
        self._shutdown_handlers.append(func)

    def mainloop(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit()
