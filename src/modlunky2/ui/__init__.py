import time
import sys
import logging
import traceback
import tkinter as tk
from tkinter import PhotoImage, ttk
from multiprocessing import Queue

from modlunky2.constants import BASE_DIR, IS_EXE
from modlunky2.updater import self_update
from modlunky2.version import current_version, latest_version
from modlunky2.config import MIN_WIDTH, MIN_HEIGHT
from modlunky2.utils import tb_info, temp_chdir

from .tasks import TaskManager, PING_INTERVAL
from .config import ConfigTab
from .extract import ExtractTab
from .levels import LevelsTab
from .play import PlayTab
from .overlunky import OverlunkyTab
from .pack import PackTab
from .widgets import ConsoleWindow
from .install import InstallTab
from .logs import QueueHandler, register_queue_handler
from .error import ErrorTab

logger = logging.getLogger("modlunky2")


def exception_logger(type_, value, traceb):
    exc = traceback.format_exception(type_, value, traceb)
    logger.critical("Unhandled Exception: %s", "".join(exc).strip())


def update_start(_call):
    self_update()


class ModlunkyUI:
    def __init__(self, modlunky_config, log_level=logging.INFO):
        self.modlunky_config = modlunky_config

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
        register_queue_handler(self.queue_handler, log_level)
        self.task_manager = TaskManager(self.log_queue, log_level)
        self.task_manager.register_task(
            "modlunky2:update_start",
            update_start,
            True,
            on_complete="modlunky2:update_complete",
        )
        self.task_manager.register_handler(
            "modlunky2:update_complete", self.update_complete
        )

        self.root = tk.Tk(className="Modlunky2")
        self.load_themes()
        style = ttk.Style(self.root)
        self.root.default_theme = style.theme_use()
        valid_themes = self.root.call("ttk::themes")

        self.root.title("Modlunky 2")
        self.root.geometry(modlunky_config.config_file.geometry)
        self.last_geometry = modlunky_config.config_file.geometry
        self.root.bind("<Configure>", self.handle_resize)
        if (
            modlunky_config.config_file.theme
            and modlunky_config.config_file.theme in valid_themes
        ):
            style.theme_use(modlunky_config.config_file.theme)
        self.root.event_add("<<ThemeChange>>", "None")

        style.configure(
            "ModList.TCheckbutton",
            font=("Segoe UI", 12, "bold"),
            # TODO: dynamic sizing for larger windows
            wraplength="640",
        )
        style.configure("Update.TButton", bg="#bfbfbf", font="sans 12 bold")
        style.configure("TOptionMenu", anchor="w")

        default_background = style.lookup("TFrame", "background")
        self.root.configure(bg=default_background)

        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.icon_png = PhotoImage(file=BASE_DIR / "static/images/icon.png")
        self.root.iconphoto(False, self.icon_png)

        sys.excepthook = exception_logger
        self.root.report_callback_exception = exception_logger

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.top_frame = ttk.Frame(self.root)
        self.top_frame.grid(row=0, column=0, sticky="nsew")

        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_rowconfigure(0, weight=0)
        self.top_frame.grid_rowconfigure(1, weight=1)
        self.top_frame.grid_rowconfigure(2, weight=0)

        self.update_frame = ttk.LabelFrame(
            self.top_frame, text="Modlunky2 Update Available"
        )
        self.update_frame.columnconfigure(0, weight=1)
        self.update_frame.rowconfigure(0, weight=1)

        self.update_button = ttk.Button(
            self.update_frame,
            text="Update Now!",
            command=self.update,
            style="Update.TButton",
        )

        if self.needs_update:
            self.update_frame.grid(row=0, column=0, sticky="nswe")
            self.update_button.grid(column=0, row=0, sticky="nswe")

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<Escape>", self.quit)

        self.tabs = {}
        self.tab_control = ttk.Notebook(self.top_frame)

        self.register_tab(
            "Playlunky",
            PlayTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
            task_manager=self.task_manager,
        )
        self.register_tab(
            "Install Mods",
            InstallTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
            task_manager=self.task_manager,
        )
        self.register_tab(
            "Overlunky",
            OverlunkyTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
            task_manager=self.task_manager,
        )
        self.register_tab(
            "Extract Assets",
            ExtractTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
            task_manager=self.task_manager,
        )
        self.register_tab(
            "Pack Assets",
            PackTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
            task_manager=self.task_manager,
        )
        self.register_tab(
            "Level Editor",
            LevelsTab,
            tab_control=self.tab_control,
            modlunky_ui=self,
            modlunky_config=modlunky_config,
        )
        self.register_tab(
            "Config",
            ConfigTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
        )

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.tab_control.grid(column=0, row=1, padx=2, pady=(4, 0), sticky="nsew")

        self.console_frame = ttk.LabelFrame(self.top_frame, text="Console")
        self.console_frame.columnconfigure(0, weight=1)
        self.console_frame.rowconfigure(0, weight=1)

        self.console = ConsoleWindow(self.queue_handler, self.console_frame)
        self.console.grid(column=0, row=0, padx=2, pady=2, sticky="ew")

        self.version_label = ttk.Label(
            self.top_frame, text=f"v{self.current_version}", font="Helvitica 9 italic"
        )
        self.version_label.grid(column=0, row=3, padx=5, sticky="e")

        self.task_manager.start_process()
        self.last_ping = time.time()
        self.root.after(100, self.after_cb)
        self.root.after(1000, self.after_record_win)

    def after_record_win(self):
        self.root.after(1000, self.after_record_win)
        if self.modlunky_config.config_file.geometry != self.last_geometry:
            self.modlunky_config.config_file.geometry = self.last_geometry
            self.modlunky_config.config_file.dirty = True

        if self.modlunky_config.config_file.dirty:
            logger.debug("Saving config")
            self.modlunky_config.config_file.save()

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

    def handle_resize(self, event):
        if not isinstance(event.widget, tk.Tk):
            return
        self.last_geometry = self.root.geometry()

    def update(self):
        self.update_button["state"] = tk.DISABLED
        self.tab_control.grid_forget()
        label = ttk.Label(
            self.top_frame,
            text="Update in progress...",
            anchor=tk.CENTER,
            font="sans 12 bold",
        )
        label.grid(column=0, row=1, padx=10, pady=10, sticky="nsew")

        self.task_manager.call("modlunky2:update_start")

    def update_complete(self):
        self.quit()

    def on_tab_change(self, event):
        tab_name = event.widget.tab("current")["text"]
        tab = self.tabs[tab_name]
        if tab.show_console:
            self.render_console()
        else:
            self.forget_console()
        tab.on_load()

    def render_console(self):
        self.console_frame.grid(row=2, column=0, padx=5, pady=(5, 0), sticky="nswe")

    def forget_console(self):
        self.console_frame.grid_forget()

    def register_tab(self, name, cls, **kwargs):
        try:
            obj = cls(**kwargs)
        except Exception:  # pylint: disable=broad-except
            obj = ErrorTab(tab_control=self.tab_control)
            logger.critical("Failed to register tab %s: %s", name, tb_info())

        self.tabs[name] = obj
        self.tab_control.add(obj, text=name)

    def tabs_needing_save(self):
        needs_save = []
        for tab_name, tab in self.tabs.items():
            if tab.save_needed:
                needs_save.append(tab_name)
        return needs_save

    def should_close(self, needs_save):
        tabs = ", ".join(needs_save)
        msg_box = tk.messagebox.askquestion(
            "Close Modlunky2?",
            (
                f"You have some tabs ({tabs}) with unsaved changes.\n"
                "Are you sure you want to exit without saving?"
            ),
            icon="warning",
        )
        return msg_box == "yes"

    def quit(self, _event=None):
        if self._shutting_down:
            return

        needs_save = self.tabs_needing_save()
        should_close = True
        if needs_save:
            should_close = self.should_close(needs_save)

        if not should_close:
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

    def load_themes(self):
        static_dir = BASE_DIR / "static"
        themes_dir = static_dir / "themes"
        with temp_chdir(static_dir):
            self.root.call("lappend", "auto_path", f"[{themes_dir}]")
            self.root.eval("source themes/pkgIndex.tcl")
