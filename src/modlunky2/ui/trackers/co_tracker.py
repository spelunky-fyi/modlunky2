import logging
from collections import Counter

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from modlunky2.config import Config, COTrackerConfig
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process

from modlunky2.mem.state import Theme

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowData,
)

logger = logging.getLogger(__name__)


ICON_PATH = BASE_DIR / "static/images"


class COTrackerModifiers(ttk.LabelFrame):
    def __init__(self, parent, co_tracker_config: COTrackerConfig, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.co_tracker_config = co_tracker_config

        self.THEME_NAME_STYLES = {
            "Full theme names": {
                Theme.DWELLING: "Dwelling",
                Theme.JUNGLE: "Jungle",
                Theme.VOLCANA: "Volcana",
                Theme.TIDE_POOL: "Tide Pool",
                Theme.TEMPLE: "Temple",
                Theme.ICE_CAVES: "Ice Caves",
                Theme.NEO_BABYLON: "Neo Babylon",
                Theme.SUNKEN_CITY: "Sunken City",
            },
            "Short theme names": {
                Theme.DWELLING: "Dwelling",
                Theme.JUNGLE: "Jungle",
                Theme.VOLCANA: "Volcana",
                Theme.TIDE_POOL: "TidePool",
                Theme.TEMPLE: "Temple",
                Theme.ICE_CAVES: "IceCaves",
                Theme.NEO_BABYLON: "NeoBab",
                Theme.SUNKEN_CITY: "Sunken",
            },
            "Two-letter theme names": {
                Theme.DWELLING: "DW",
                Theme.JUNGLE: "JU",
                Theme.VOLCANA: "VO",
                Theme.TIDE_POOL: "TP",
                Theme.TEMPLE: "TE",
                Theme.ICE_CAVES: "IC",
                Theme.NEO_BABYLON: "NB",
                Theme.SUNKEN_CITY: "SC",
            },
            "No theme names": None,
        }

        # Set theme_names in config based on theme_name_style
        self.co_tracker_config.theme_names = self.THEME_NAME_STYLES.get(
            self.co_tracker_config.theme_name_style, None
        )

        # Theme name style
        self.theme_name_style = tk.StringVar()
        self.theme_name_style.set(self.co_tracker_config.theme_name_style)
        self.theme_name_combobox = ttk.Combobox(
            self,
            textvariable=self.theme_name_style,
            values=list(self.THEME_NAME_STYLES.keys()),
            state="readonly",
        )
        self.theme_name_combobox.bind(
            "<<ComboboxSelected>>", self.update_theme_name_style
        )
        self.theme_name_combobox.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        # Show run stats
        self.show_run_stats = tk.BooleanVar()
        self.show_run_stats.set(self.co_tracker_config.show_run_stats)
        self.run_stats_checkbox = ttk.Checkbutton(
            self,
            text="Show Run Stats",
            variable=self.show_run_stats,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_run_stats,
        )
        self.run_stats_checkbox.grid(row=0, column=2, pady=5, padx=5, sticky="w")

        # Show session stats
        self.show_session_stats = tk.BooleanVar()
        self.show_session_stats.set(self.co_tracker_config.show_session_stats)
        self.session_stats_checkbox = ttk.Checkbutton(
            self,
            text="Show Session Stats",
            variable=self.show_session_stats,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_session_stats,
        )
        self.session_stats_checkbox.grid(row=0, column=3, pady=5, padx=5, sticky="w")

        # Show header
        self.show_header = tk.BooleanVar()
        self.show_header.set(self.co_tracker_config.show_header)
        self.header_checkbox = ttk.Checkbutton(
            self,
            text="Show Header",
            variable=self.show_header,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_header,
        )
        self.header_checkbox.grid(row=0, column=4, pady=5, padx=5, sticky="w")

    def update_theme_name_style(self, event=None):
        name_style = self.theme_name_style.get()
        self.co_tracker_config.theme_name_style = name_style
        self.co_tracker_config.theme_names = self.THEME_NAME_STYLES.get(
            name_style, None
        )
        self.parent.config_update_callback()

    def toggle_show_run_stats(self):
        self.co_tracker_config.show_run_stats = self.show_run_stats.get()
        self.parent.config_update_callback()

    def toggle_show_session_stats(self):
        self.co_tracker_config.show_session_stats = self.show_session_stats.get()
        self.parent.config_update_callback()

    def toggle_show_header(self):
        self.co_tracker_config.show_header = self.show_header.get()
        self.parent.config_update_callback()


class COTrackerButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1, minsize=200)
        self.columnconfigure(1, weight=10000)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.co_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "orb.png").resize((24, 24), Image.Resampling.LANCZOS)
        )

        self.co_button = ttk.Button(
            self,
            text="CO Tracker",
            image=self.co_icon,
            compound="left",
            command=self.launch,
            width=1,
        )
        self.co_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.modifiers = COTrackerModifiers(
            self,
            self.modlunky_config.trackers.co_tracker,
            text="CO Tracker Options",
        )
        self.modifiers.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

    def launch(self):
        self.disable_button()
        self.window = TrackerWindow(
            title="CO Tracker",
            color_key=self.modlunky_config.tracker_color_key,
            font_size=self.modlunky_config.tracker_font_size,
            font_family=self.modlunky_config.tracker_font_family,
            on_close=self.window_closed,
            file_name="co.txt",
            tracker=COTracker(),
            config=self.modlunky_config.trackers.co_tracker,
        )

    def config_update_callback(self):
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.co_tracker)

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.co_button.winfo_exists():
            self.co_button["state"] = tk.NORMAL

    def disable_button(self):
        self.co_button["state"] = tk.DISABLED


class COTracker(Tracker[COTrackerConfig, WindowData]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initialize()

    THEMES = {
        2: Theme.DWELLING,
        3: Theme.JUNGLE,
        4: Theme.VOLCANA,
        6: Theme.TIDE_POOL,
        7: Theme.TEMPLE,
        8: Theme.ICE_CAVES,
        9: Theme.NEO_BABYLON,
        10: Theme.SUNKEN_CITY,
    }

    def initialize(self):
        self.world = 0
        self.level = 0
        self.get_theme_by_address = None
        self.session_stats = Counter()
        self.run_stats = Counter()

    def add_theme_to_stats(self, theme: Theme):
        """
        Increase counter for the given theme
        """
        self.session_stats[theme] += 1
        self.run_stats[theme] += 1

    def get_address_to_theme_function(self, proc: Spel2Process):
        """
        Reads in the memory addresses of the ThemeInfos and
        returns a function that converts a memory address into a string of the theme
        """

        def get_value_at_address(address: int) -> str:
            SIZE = 8  # In bytes
            value = proc.read_memory(address, SIZE)
            return value[::-1].hex()

        feedcode = proc.get_feedcode()
        OFFSET_TO_LEVEL_GEN = 0xD7631
        LEVEL_GEN_START = feedcode + OFFSET_TO_LEVEL_GEN
        THEME_BYTE_SIZE = 0x8

        ADDRESS_TO_THEME = {
            get_value_at_address(LEVEL_GEN_START + i * THEME_BYTE_SIZE): self.THEMES[i]
            for i in self.THEMES
        }

        def get_theme_by_address(address: int) -> Theme:
            return ADDRESS_TO_THEME.get(f"{address:016x}", Theme.BEFORE_FIRST_RUN)

        return get_theme_by_address

    @staticmethod
    def get_stats_str(theme_count: Counter[Theme, int], theme: Theme) -> str:
        """
        Returns a string of length 9 (unless the count has 3 digits or more)
        Example: " 2  (25%)"
        """
        count = theme_count[theme]
        total_count = theme_count.total()
        percentage_str = f"{f'({count/total_count if total_count > 0 else 0:.0%})':>6}"
        return f"{count:>2} {percentage_str}"

    def get_display_str(self, config: COTrackerConfig) -> str:
        """
        Returns the string to be displayed based on the current stats and all the settings
        """
        theme_names = config.theme_names
        max_theme_name_length = (
            max(map(len, theme_names.values())) if theme_names is not None else 0
        )

        if config.show_header:
            header = (
                [" " * (max_theme_name_length + 1)] if theme_names is not None else []
            )
            if config.show_run_stats:
                header.append(f"{'Run':^9}")
            if config.show_session_stats:
                header.append(f"{'Session':^9}")
            header_str = " ".join(header) + "\n"
        else:
            header_str = ""

        stats_lines = []
        for theme in self.THEMES.values():
            stats_line = []
            if theme_names is not None:
                stats_line.append(f"{theme_names[theme]:>{max_theme_name_length}}:")
            if config.show_run_stats:
                stats_line.append(self.get_stats_str(self.run_stats, theme))
            if config.show_session_stats:
                stats_line.append(self.get_stats_str(self.session_stats, theme))
            stats_lines.append(" ".join(stats_line))

        return header_str + "\n".join(stats_lines)

    def poll(self, proc: Spel2Process, config: COTrackerConfig) -> WindowData:
        game_state = proc.get_state()
        if game_state is None:
            return None

        if self.get_theme_by_address is None:
            self.get_theme_by_address = self.get_address_to_theme_function(proc)

        world = game_state.world
        level = game_state.level

        # On level change
        if world != self.world or level != self.level:
            # Update world and level
            self.world = world
            self.level = level

            # If CO, increment theme counter
            if game_state.theme == Theme.COSMIC_OCEAN and level < 99:
                sub_theme = self.get_theme_by_address(
                    game_state.theme_info.sub_theme_address
                )
                self.add_theme_to_stats(sub_theme)

            # If starting world or basecamp, reset run stats
            if (
                world == game_state.world_start and level == game_state.level_start
            ) or game_state.theme == Theme.BASE_CAMP:
                self.run_stats.clear()

        label = self.get_display_str(config)
        return WindowData(label)
