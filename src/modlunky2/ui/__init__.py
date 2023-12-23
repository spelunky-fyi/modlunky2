import logging
import sys
import threading
import time
import tkinter as tk
import traceback
from tkinter import PhotoImage, ttk
from multiprocessing import Queue

import tkinterDnD

from modlunky2.constants import BASE_DIR, IS_EXE
from modlunky2.updater import self_update
from modlunky2.version import current_version, latest_version
from modlunky2.config import Config, MIN_WIDTH, MIN_HEIGHT
from modlunky2.utils import is_windows, tb_info, temp_chdir

from modlunky2.ui.tasks import TaskManager, PING_INTERVAL
from modlunky2.ui.settings import SettingsTab
from modlunky2.ui.extract import ExtractTab
from modlunky2.ui.levels.tab import LevelsTab
from modlunky2.ui.play import PlayTab
from modlunky2.ui.overlunky import OverlunkyTab
from modlunky2.ui.pack import PackTab
from modlunky2.ui.widgets import ConsoleWindow
from modlunky2.ui.install import InstallTab
from modlunky2.ui.logs import QueueHandler, register_queue_handler
from modlunky2.ui.error import ErrorTab
from modlunky2.ui.websocket import WebSocketThread

if is_windows():
    from modlunky2.ui.trackers import TrackersTab
if not IS_EXE:
    import pip_api


logger = logging.getLogger(__name__)
update_lock = threading.Lock()


TAB_KEYS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]


def exception_logger(type_, value, traceb):
    exc = traceback.format_exception(type_, value, traceb)
    logger.critical("Unhandled Exception: %s", "".join(exc).strip())


def update_start(_call, launcher_exe):
    self_update(launcher_exe)


def check_for_latest(call):
    logger.debug("Checking for latest Modlunky version")
    acquired = update_lock.acquire(blocking=False)
    if not acquired:
        logger.warning(
            "Attempted to check for new modlunky while another task is running..."
        )
        return

    modlunky_latest_version = None
    try:
        modlunky_latest_version = latest_version()
    finally:
        update_lock.release()

    call("modlunky2:latest_version", modlunky_latest_version=modlunky_latest_version)


class ModlunkyUI:
    CHECK_LATEST_INTERVAL = 1000 * 30 * 60

    def __init__(self, modlunky_config: Config, log_level=logging.INFO):
        logger.debug("Initializing UI")
        self.modlunky_config = modlunky_config

        self.current_version = current_version()
        self.latest_version = None
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

        self.task_manager.register_task(
            "modlunky2:check_for_latest",
            check_for_latest,
            True,
        )
        self.task_manager.register_handler(
            "modlunky2:latest_version", self.handle_modlunky_latest_version
        )

        self.root = tkinterDnD.Tk(className="Modlunky2")

        self.load_themes()
        style = ttk.Style(self.root)
        self.root.default_theme = style.theme_use()
        valid_themes = self.root.call("ttk::themes")

        self.root.title("Modlunky 2")
        self.root.geometry(modlunky_config.geometry)
        self.last_geometry = modlunky_config.geometry
        self.root.bind("<Configure>", self.handle_resize)
        if modlunky_config.theme and modlunky_config.theme in valid_themes:
            style.theme_use(modlunky_config.theme)
        self.root.event_add("<<ThemeChange>>", "None")

        style.configure(
            "ModList.TCheckbutton",
            font=("Segoe UI", 12, "bold"),
            # TODO: dynamic sizing for larger windows
            wraplength="640",
        )
        style.configure("Update.TButton", font="sans 12 bold")
        style.configure("TOptionMenu", anchor="w")
        style.configure("Link.TLabel", foreground="royal blue")
        style.configure(
            "Thicc.TButton",
            font=("Arial", 16, "bold"),
        )

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

        # Handle shutting down cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        # self.root.bind("<Escape>", self.quit)

        self.tabs = {}
        self.tab_control = ttk.Notebook(self.top_frame, onfiledrop=self.drop)

        logger.debug("Registering Tabs")
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
        if self.modlunky_config.show_packing:
            self.register_tab(
                "Pack Assets (Deprecated)",
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
        if is_windows():
            self.register_tab(
                "Trackers",
                TrackersTab,
                tab_control=self.tab_control,
                ml_config=modlunky_config,
            )
        self.register_tab(
            "Settings",
            SettingsTab,
            tab_control=self.tab_control,
            modlunky_config=modlunky_config,
        )

        if not modlunky_config.install_dir:
            logger.critical(
                "You must go to the Settings and set the Install Directory to use modlunky2!"
            )
            for i in range(0, 5):
                self.tab_control.tab(i, state="disabled")

        self.select_last_tab()
        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.tab_control.grid(column=0, row=1, padx=2, pady=(4, 0), sticky="nsew")

        self.console_frame = ttk.LabelFrame(self.top_frame, text="Console")
        self.console_frame.columnconfigure(0, weight=1)
        self.console_frame.rowconfigure(0, weight=1)

        self.console = ConsoleWindow(self.queue_handler, self.console_frame)
        self.console.grid(column=0, row=0, padx=2, pady=2, sticky="ew")

        self.version_label = ttk.Label(
            self.top_frame, text=f"v{self.current_version}", font="Helvetica 9 italic"
        )
        self.version_label.grid(column=0, row=3, padx=5, sticky="e")

        self.ws_thread = None
        self.task_manager.start_process()
        self.last_ping = time.time()
        self.root.after(100, self.after_task_manager)
        self.root.after(1000, self.after_ws_thread)
        self.root.after(1000, self.after_record_win)
        self.check_for_updates()
        self.check_requirements()

    def drop(self, event):
        self.tab_control.select(1)
        self.tabs["Install Mods"].local_install.drop_file(event.data)

    def check_for_updates(self):
        if self.needs_update:
            return

        self.task_manager.call("modlunky2:check_for_latest")
        self.root.after(self.CHECK_LATEST_INTERVAL, self.check_for_updates)

    @staticmethod
    def check_requirements():
        # Only check requirements in dev environments
        if IS_EXE:
            return

        all_req_files = [
            "requirements.txt",
            "requirements-dev.txt",
        ]
        if is_windows():
            all_req_files.append("requirements-win.txt")

        installed = pip_api.installed_distributions()
        missing_req_files = set()
        for req_file in all_req_files:
            requirements = pip_api.parse_requirements(req_file)

            for req in requirements.values():
                if req.name not in installed:
                    missing_req_files.add(req_file)
                    logger.warning("Missing required package '%s'", req.name)
                    continue

                installed_ver = installed[req.name].version
                if req.specifier.contains(installed_ver):
                    continue
                missing_req_files.add(req_file)
                logger.warning(
                    "Installed version of '%s' is %s, doesen't meet %s",
                    req.name,
                    installed_ver,
                    req.specifier,
                )

        if not missing_req_files:
            return
        r_args = "  ".join([f"-r {r}" for r in missing_req_files])
        logger.warning(
            "Some requirements aren't met. Run pip install --upgrade %s",
            r_args,
        )

    def handle_modlunky_latest_version(self, modlunky_latest_version):
        if not IS_EXE:
            return

        if modlunky_latest_version is None:
            self.needs_update = False
            return
        self.latest_version = modlunky_latest_version

        if self.current_version is None:
            self.needs_update = False
            return

        self.needs_update = self.current_version < self.latest_version
        if self.needs_update:
            self.update_frame.grid(row=0, column=0, sticky="nswe")
            self.update_button.grid(column=0, row=0, sticky="nswe")

    def after_ws_thread(self):
        try:
            token = self.modlunky_config.spelunky_fyi_api_token
            if token is None:
                return

            if self.ws_thread is not None and self.ws_thread.is_alive():
                return

            logger.debug("Starting websocket thread")
            self.ws_thread = WebSocketThread(self.modlunky_config, self.task_manager)
            self.ws_thread.start()
        finally:
            self.root.after(1000, self.after_ws_thread)

    def after_record_win(self):
        self.root.after(1000, self.after_record_win)
        if self.modlunky_config.geometry != self.last_geometry:
            self.modlunky_config.geometry = self.last_geometry
            self.modlunky_config.dirty = True

        if self.modlunky_config.dirty:
            logger.debug("Saving config")
            self.modlunky_config.save()

    def after_task_manager(self):
        if not self.task_manager.is_alive():
            # Worker process went away but we're shutting down so just return
            if self._shutting_down:
                return

            # Worker process went away unexpectedly... Restart it.
            logger.critical("Worker process went away... Restarting it.")
            self.task_manager.start_process()
            self.root.after(100, self.after_task_manager)
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
                self.root.after(100, self.after_task_manager)
                return

            self.root.after_idle(self.task_manager.dispatch, msg)

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

        self.task_manager.call(
            "modlunky2:update_start", launcher_exe=self.modlunky_config.launcher_exe
        )

    def update_complete(self):
        self.quit()

    def select_last_tab(self):
        last_tab = self.tabs.get(self.modlunky_config.last_tab)
        if last_tab is None:
            return
        self.tab_control.select(last_tab)

    def on_tab_change(self, event):
        tab_name = event.widget.tab("current")["text"]
        tab = self.tabs[tab_name]
        if tab.show_console:
            self.render_console()
        else:
            self.forget_console()

        self.modlunky_config.last_tab = tab_name
        self.modlunky_config.save()
        tab.on_load()

    def render_console(self):
        self.console_frame.grid(row=2, column=0, padx=5, pady=(5, 0), sticky="nswe")

    def forget_console(self):
        self.console_frame.grid_forget()

    def register_tab(self, name, cls, **kwargs):
        logger.debug("Registering Tab %s", repr(name))

        try:
            obj = cls(**kwargs)
        except Exception:  # pylint: disable=broad-except
            obj = ErrorTab(tab_control=self.tab_control)
            logger.critical("Failed to register tab %s: %s", name, tb_info())

        num_tabs = len(self.tabs)
        if num_tabs < len(TAB_KEYS):
            self.root.bind(
                f"<Control-Key-{TAB_KEYS[num_tabs]}>",
                lambda _e: self.tab_control.select(obj),
            )

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
