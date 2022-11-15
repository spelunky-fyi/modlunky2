import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog
from urllib.parse import urljoin

from modlunky2.config import CACHE_DIR, CONFIG_DIR, DATA_DIR, Config, guess_install_dir
from modlunky2.ui.widgets import Entry, Link, PopupWindow, Tab
from modlunky2.utils import open_directory

logger = logging.getLogger(__name__)


class Theme(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config: Config):
        super().__init__(parent, text="Theme")
        self.modlunky_config = modlunky_config

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        note_label = ttk.Label(
            self,
            text=(
                "Note: Themes are are work in progress and don't fully refresh "
                "until you've restart the application."
            ),
        )
        note_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        self.style = ttk.Style(self)

        self.selected_var = tk.StringVar(value=modlunky_config.theme)
        self.selected_dropdown = ttk.OptionMenu(
            self,
            self.selected_var,
            self.selected_var.get(),
            *sorted(self.winfo_toplevel().call("ttk::themes")),
            command=self.set_theme,
        )
        self.selected_dropdown.grid(
            row=1, column=0, pady=(5, 5), padx=(5, 5), sticky="ew"
        )
        self.reset_button = ttk.Button(self, text="Reset", command=self.reset)
        self.reset_button.grid(row=1, column=1, pady=(5, 5), padx=(5, 5), sticky="ew")

    def reset(self):
        self.selected_var.set(self.winfo_toplevel().default_theme)
        self.set_theme(self.selected_var.get())

    def set_theme(self, selected):
        self.style.theme_use(selected)
        self.winfo_toplevel().event_generate("<<ThemeChange>>", when="now")
        self.modlunky_config.theme = selected
        self.modlunky_config.save()


class InstallDir(ttk.LabelFrame):
    def __init__(self, parent, tab_control, modlunky_config: Config):
        super().__init__(parent, text="Install Directory")
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        install_dir_label = ttk.Label(
            self, text="The directory where Spelunky 2 is installed"
        )
        install_dir_label.grid(
            row=0, column=0, padx=5, pady=(2, 0), columnspan=3, sticky="w"
        )

        self.install_dir_var = tk.StringVar(value=self.modlunky_config.install_dir)
        install_dir_entry = ttk.Entry(
            self,
            textvariable=self.install_dir_var,
            state=tk.DISABLED,
            width=80,
        )
        install_dir_entry.grid(
            row=1, column=0, padx=10, pady=10, columnspan=3, sticky="nsew"
        )

        install_dir_browse = ttk.Button(
            self, text="Browse", command=self.browse_install_dir
        )
        install_dir_browse.grid(row=2, column=0, pady=5, padx=5, sticky="nsew")

        install_dir_lucky = ttk.Button(
            self, text="I'm Feeling Lucky", command=self.feeling_lucky
        )
        install_dir_lucky.grid(row=2, column=1, pady=5, padx=5, sticky="nsew")

        install_dir_clear = ttk.Button(
            self, text="Clear", command=self.clear_install_dir
        )
        install_dir_clear.grid(row=2, column=2, pady=5, padx=5, sticky="nsew")

    def browse_install_dir(self):
        install_dir = self.install_dir_var.get()
        directory = filedialog.askdirectory(initialdir=install_dir)
        if directory:
            self.install_dir_var.set(directory)
            self.modlunky_config.install_dir = Path(directory)
            self.modlunky_config.save()
            for i in range(0, 5):
                self.tab_control.tab(i, state="normal")

    def feeling_lucky(self):
        install_dir = guess_install_dir(self.modlunky_config.exe_dir)
        if install_dir:
            self.install_dir_var.set(str(install_dir))
            self.modlunky_config.install_dir = install_dir
            self.modlunky_config.save()
            for i in range(0, 5):
                self.tab_control.tab(i, state="normal")

    def clear_install_dir(self):
        self.install_dir_var.set("")
        self.modlunky_config.install_dir = None
        self.modlunky_config.save()
        logger.critical("You must go to the Settings and set the Install Directory!")
        for i in range(0, 5):
            self.tab_control.tab(i, state="disabled")


class FYISettings(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config: Config):
        super().__init__(parent, text="spelunky.fyi Settings")
        self.modlunky_config = modlunky_config

        self.update_text = "Update Token"
        self.add_text = "Add Token"

        self.token_button = ttk.Button(self, text=self.add_text, command=self.set_token)
        if self.modlunky_config.spelunky_fyi_api_token:
            self.token_button.configure(text=self.update_text)
        self.token_button.grid(row=0, column=0, pady=(5, 5), padx=(5, 5), sticky="w")

    def set_token(self):
        win = PopupWindow("API Token", self.modlunky_config)
        win.columnconfigure(1, minsize=500)

        url = urljoin(self.modlunky_config.spelunky_fyi_root, "accounts/settings/")
        link = Link(win, url, text="Get API Token Here", anchor="center")
        link.grid(row=0, column=0, columnspan=2, padx=2, pady=2)
        label = ttk.Label(win, text="API Token: ")
        entry = Entry(win)
        if self.modlunky_config.spelunky_fyi_api_token:
            entry.insert(0, self.modlunky_config.spelunky_fyi_api_token)
        label.grid(row=1, column=0, padx=2, pady=2, sticky="nse")
        entry.grid(row=1, column=1, padx=2, pady=2, sticky="nsew")

        def update_then_destroy():
            try:
                api_token = entry.get().strip()
                if not api_token:
                    self.modlunky_config.spelunky_fyi_api_token = None
                    self.token_button.configure(text=self.add_text)
                else:
                    self.modlunky_config.spelunky_fyi_api_token = api_token
                    self.token_button.configure(text=self.update_text)
                self.modlunky_config.save()
            finally:
                win.destroy()

        separator = ttk.Separator(win)
        separator.grid(row=4, column=0, columnspan=3, pady=5, sticky="nsew")

        buttons = ttk.Frame(win)
        buttons.grid(row=5, column=0, columnspan=2, sticky="nsew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ok_button = ttk.Button(buttons, text="Ok", command=update_then_destroy)
        ok_button.grid(row=0, column=0, pady=5, sticky="nsew")

        cancel_button = ttk.Button(buttons, text="Cancel", command=win.destroy)
        cancel_button.grid(row=0, column=1, pady=5, sticky="nsew")


class UserDirectories(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config):
        super().__init__(parent, text="User Directories")
        self.modlunky_config = modlunky_config

        ttk.Button(self, text="Cache", command=lambda: open_directory(CACHE_DIR)).grid(
            row=0, column=0, pady=(5, 5), padx=(5, 5), sticky="w"
        )
        ttk.Button(self, text="Data", command=lambda: open_directory(DATA_DIR)).grid(
            row=0, column=1, pady=(5, 5), padx=(5, 5), sticky="w"
        )
        ttk.Button(
            self, text="Config", command=lambda: open_directory(CONFIG_DIR)
        ).grid(row=0, column=2, pady=(5, 5), padx=(5, 5), sticky="w")
        ttk.Button(
            self,
            text="Install Dir",
            command=lambda: open_directory(self.modlunky_config.install_dir),
        ).grid(row=0, column=3, pady=(5, 5), padx=(5, 5), sticky="w")


class Flags(ttk.LabelFrame):
    def __init__(self, parent, modlunky_config: Config):
        super().__init__(parent, text="Flags")
        self.modlunky_config = modlunky_config

        self.show_packing = tk.BooleanVar()
        self.show_packing.set(self.modlunky_config.show_packing)
        self.show_packing_checkbox = ttk.Checkbutton(
            self,
            text="Show Packing Tab (Deprecated)",
            variable=self.show_packing,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_packing,
        )
        self.show_packing_checkbox.grid(row=0, column=1, pady=5, padx=5, sticky="nw")

    def toggle_show_packing(self):
        self.modlunky_config.show_packing = self.show_packing.get()
        self.modlunky_config.save()


class SettingsTab(Tab):
    def __init__(self, tab_control, modlunky_config: Config, *args, **kwargs):
        super().__init__(tab_control, *args, **kwargs)
        self.tab_control = tab_control
        self.modlunky_config = modlunky_config

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        config_frame = ttk.LabelFrame(self, text="Config")
        config_frame.columnconfigure(0, weight=1)
        config_frame.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        install_dir_frame = InstallDir(config_frame, tab_control, modlunky_config)
        install_dir_frame.grid(row=0, column=0, pady=5, padx=5, sticky="new")

        theme_frame = Theme(config_frame, modlunky_config)
        theme_frame.grid(row=1, column=0, pady=5, padx=5, sticky="new")

        api_token_frame = FYISettings(config_frame, modlunky_config)
        api_token_frame.grid(row=2, column=0, pady=5, padx=5, sticky="new")

        UserDirectories(config_frame, modlunky_config).grid(
            row=3, column=0, pady=5, padx=5, sticky="nswe"
        )

        Flags(config_frame, modlunky_config).grid(
            row=4, column=0, pady=5, padx=5, sticky="nswe"
        )
