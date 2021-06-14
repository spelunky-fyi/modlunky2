import logging
import subprocess
import time
import threading
import os
import tkinter as tk
from tkinter import ttk, PhotoImage

from PIL import Image, ImageTk

from modlunky2.constants import BASE_DIR, IS_EXE
from modlunky2.ui.widgets import Tab
from modlunky2.utils import is_windows, tb_info

logger = logging.getLogger("modlunky2")


ICON_PATH = BASE_DIR / "static/images"


def tail_file(file_handle, log_func):
    for line in file_handle:
        log_func(line.strip())


def s99_client_path():
    if IS_EXE:
        client_dir = BASE_DIR
    else:
        client_dir = BASE_DIR / "../../dist"

    if is_windows():
        return client_dir / "s99-client.exe"

    return client_dir / "s99-client"


class S99Client(threading.Thread):
    def __init__(
        self,
        exe_path,
        api_token,
    ):
        super().__init__()
        self.select_timeout = 0.1
        self.shut_down = False
        self.exe_path = exe_path
        self.api_token = api_token

    def run(self):
        try:
            self._run()
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed in client thread: %s", tb_info())

    def _run(self):
        if not self.api_token:
            logger.warning("No API Token...")
            return

        if not self.exe_path.exists():
            logger.warning("No exe found...")
            return

        env = os.environ.copy()
        env["SFYI_API_TOKEN"] = self.api_token

        logger.info("Launching S99 Client")
        cmd = [f"{self.exe_path}"]

        client_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env,
        )

        shutting_down = False
        stdout_logger = threading.Thread(
            target=tail_file, args=(client_proc.stdout, logger.info)
        )
        stdout_logger.start()
        stderr_logger = threading.Thread(
            target=tail_file, args=(client_proc.stderr, logger.warning)
        )
        stderr_logger.start()

        while True:
            if not shutting_down and self.shut_down:
                shutting_down = True
                client_proc.kill()
                break

            if client_proc.poll():
                break

            time.sleep(0.1)

        stdout_logger.join()
        stderr_logger.join()
        logger.info("Client closed.")


class S99Tab(Tab):
    def __init__(self, tab_control, modlunky_config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.s99_frame = ttk.LabelFrame(self, text="Spelunky 99")
        self.s99_frame.grid(sticky="nsew")

        self.s99_frame.rowconfigure(0, minsize=20)
        self.s99_frame.rowconfigure(1, weight=0)
        self.s99_frame.rowconfigure(2, weight=1)
        self.s99_frame.rowconfigure(3, weight=0)
        self.s99_frame.rowconfigure(4, minsize=60)
        self.s99_frame.columnconfigure(0, weight=1)

        self.help_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "help.png").resize((24, 24), Image.ANTIALIAS)
        )

        self.header_frame = ttk.Frame(self.s99_frame)
        self.header_frame.grid(row=0, column=0, sticky="nswe")
        self.header_frame.rowconfigure(0, weight=1)
        self.header_frame.columnconfigure(0, weight=1)

        ttk.Label(
            self.header_frame,
            text=(
                "Spelunky 99 is currently in closed beta but will be available soon."
            ),
            anchor="center",
            justify="center",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, sticky="nwe", pady=(5, 5), padx=(10, 10))
        ttk.Button(
            self.header_frame,
            padding=1,
            image=self.help_icon,
            command=self.show_help,
        ).grid(row=0, column=1, padx=5, pady=5, sticky="e")

        ttk.Separator(self.s99_frame).grid(row=1, column=0, sticky="ew")

        self.background_img = PhotoImage(
            file=BASE_DIR / "static/images/montyfication.png"
        )
        self.s99_logo = PhotoImage(file=BASE_DIR / "static/images/99logo.png")

        self.style = ttk.Style()
        background = self.style.lookup("TFrame", "background")
        self.canvas = tk.Canvas(self.s99_frame, bg=background)
        self.canvas.grid(row=2, column=0, columnspan=2, pady=5, padx=5, sticky="snew")
        self.canvas.create_image(0, 0, anchor="nw", image=self.background_img)
        self.canvas.create_image(1920, 0, anchor="nw", image=self.background_img)
        self.canvas.create_image(1920 * 2, 0, anchor="nw", image=self.background_img)
        self.canvas.create_image(15, 15, anchor="nw", image=self.s99_logo)

        ttk.Separator(self.s99_frame).grid(row=3, column=0, sticky="ew")
        self.button_frame = ttk.Frame(self.s99_frame)
        self.button_frame.grid(row=4, column=0, sticky="nswe")
        self.button_frame.rowconfigure(0, weight=1)
        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.columnconfigure(1, weight=1)

        self.button_connect = ttk.Button(
            self.button_frame,
            text="Connect",
            command=self.connect,
            state=tk.DISABLED,
            style="Thicc.TButton",
        )
        self.button_connect.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.button_disconnect = ttk.Button(
            self.button_frame,
            text="Disconnect",
            command=self.disconnect,
            state=tk.DISABLED,
            style="Thicc.TButton",
        )
        self.button_disconnect.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

        self.client_thread = None
        self.after(1000, self.after_client_thread)
        self.render_buttons()

    @property
    def client_path(self):
        return s99_client_path()

    def show_help(self):
        # TODO: TopLevel with message below + credits:
        #   jeremyhay - creating spelunky 99
        #   logo - jackhaswifi + spudley
        #   splash - greeni porchini
        # ttk.Label(
        #     self.s99_frame,
        #     text=(
        #         "Beta User Instructions:\n\n"
        #         "* Click Connect and verify that the log shows you're receiving messages.\n"
        #         "* Download the mod pack per provided instructions.\n"
        #         "* Select the Spelunky 99 Mod on the Playlunky tab and hit Play!\n\n\n"
        #         "Note: Make sure you have an API token configured in the Settings tab."
        #     ),
        #     anchor="center",
        # ).grid(row=2, column=0, sticky="nwe", ipady=30, padx=(10, 10))
        logger.info("todo")

    def render_buttons(self):
        api_token = self.modlunky_config.config_file.spelunky_fyi_api_token

        if not api_token:
            self.disable_connect_button()
            self.disable_disconnect_button()
            return

        if self.client_thread is None:
            self.enable_connect_button()
            self.disable_disconnect_button()
        else:
            self.enable_connect_button()
            self.disable_disconnect_button()

    def after_client_thread(self):
        try:
            if self.client_thread is None:
                return

            if self.client_thread.is_alive():
                return

            # Process was running but has since exited.
            self.client_thread = None
            self.render_buttons()
        finally:
            self.after(1000, self.after_client_thread)

    def enable_connect_button(self):
        self.button_connect["state"] = tk.NORMAL

    def disable_connect_button(self):
        self.button_connect["state"] = tk.DISABLED

    def enable_disconnect_button(self):
        self.button_disconnect["state"] = tk.NORMAL

    def disable_disconnect_button(self):
        self.button_disconnect["state"] = tk.DISABLED

    def disconnect(self):
        if self.client_thread:
            self.client_thread.shut_down = True
        self.render_buttons()

    def connect(self):
        self.disable_connect_button()
        self.enable_disconnect_button()

        api_token = self.modlunky_config.config_file.spelunky_fyi_api_token
        self.client_thread = S99Client(self.client_path, api_token)
        self.client_thread.start()

    def client_closed(self):
        self.enable_connect_button()
        self.disable_disconnect_button()

    def destroy(self) -> None:
        self.disconnect()
        return super().destroy()
