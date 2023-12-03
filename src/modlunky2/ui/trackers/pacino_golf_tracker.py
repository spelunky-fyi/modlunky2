import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.config import Config, PacinoGolfTrackerConfig
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process
from modlunky2.mem.state import WinState

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowData,
)

logger = logging.getLogger(__name__)


ICON_PATH = BASE_DIR / "static/images"


"""
Issues:
    - Basecamp shows 8 strokes because you have 0 bombs/ropes
    - Treasure collected in previous levels is not counted if the tracker wasn't open at the time
    - When the player stops existing, the tracker doesn't update (e.g. when getting crushed)
    - The tracker does not check for Low% violations
    => The tracker info is only correct if:
        1) The run is Low%,
        2) The player is alive, and
        3) The tracker was open since the first level

Pacifist issues:
    - You can violate pacifist without a kill, thereby not gaining a stroke (Red Skeleton, Skull)
    - You can get a kill without violating pacifist, thereby gaining a stroke when you should (Hundun)
"""


class PacinoGolfModifiers(ttk.LabelFrame):
    def __init__(
        self,
        parent,
        pacino_golf_tracker_config: PacinoGolfTrackerConfig,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.pacino_golf_tracker_config = pacino_golf_tracker_config

        self.show_total_strokes = tk.BooleanVar()
        self.show_total_strokes.set(self.pacino_golf_tracker_config.show_total_strokes)
        self.show_total_strokes_checkbox = ttk.Checkbutton(
            self,
            text="Total Strokes",
            variable=self.show_total_strokes,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_total_strokes,
        )
        self.show_total_strokes_checkbox.grid(
            row=0, column=1, pady=5, padx=5, sticky="w"
        )

        self.show_resource_strokes = tk.BooleanVar()
        self.show_resource_strokes.set(
            self.pacino_golf_tracker_config.show_resource_strokes
        )
        self.show_resource_strokes_checkbox = ttk.Checkbutton(
            self,
            text="Resource Strokes",
            variable=self.show_resource_strokes,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_resource_strokes,
        )
        self.show_resource_strokes_checkbox.grid(
            row=0, column=2, pady=5, padx=5, sticky="w"
        )

        self.show_treasure_strokes = tk.BooleanVar()
        self.show_treasure_strokes.set(
            self.pacino_golf_tracker_config.show_treasure_strokes
        )
        self.show_treasure_strokes_checkbox = ttk.Checkbutton(
            self,
            text="Treasure Strokes",
            variable=self.show_treasure_strokes,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_treasure_strokes,
        )
        self.show_treasure_strokes_checkbox.grid(
            row=0, column=3, pady=5, padx=5, sticky="w"
        )

        self.show_pacifist_strokes = tk.BooleanVar()
        self.show_pacifist_strokes.set(
            self.pacino_golf_tracker_config.show_pacifist_strokes
        )
        self.show_pacifist_strokes_checkbox = ttk.Checkbutton(
            self,
            text="Pacifist Strokes",
            variable=self.show_pacifist_strokes,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_pacifist_strokes,
        )
        self.show_pacifist_strokes_checkbox.grid(
            row=0, column=4, pady=5, padx=5, sticky="w"
        )

    def toggle_show_total_strokes(self):
        self.pacino_golf_tracker_config.show_total_strokes = (
            self.show_total_strokes.get()
        )
        self.parent.config_update_callback()

    def toggle_show_resource_strokes(self):
        self.pacino_golf_tracker_config.show_resource_strokes = (
            self.show_resource_strokes.get()
        )
        self.parent.config_update_callback()

    def toggle_show_treasure_strokes(self):
        self.pacino_golf_tracker_config.show_treasure_strokes = (
            self.show_treasure_strokes.get()
        )
        self.parent.config_update_callback()

    def toggle_show_pacifist_strokes(self):
        self.pacino_golf_tracker_config.show_pacifist_strokes = (
            self.show_pacifist_strokes.get()
        )
        self.parent.config_update_callback()


class PacinoGolfButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1, minsize=200)
        self.columnconfigure(1, weight=10000)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.golf_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "golf.png").resize(
                (24, 24), Image.Resampling.LANCZOS
            )
        )

        self.golf_button = ttk.Button(
            self,
            text=r"Pacifist No% Golf",
            image=self.golf_icon,
            compound="left",
            command=self.launch,
            width=1,
        )
        self.golf_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.modifiers = PacinoGolfModifiers(
            self,
            self.modlunky_config.trackers.pacino_golf,
            text=r"Pacifino Golf Tracker",
        )
        self.modifiers.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

    def launch(self):
        self.disable_button()
        self.window = TrackerWindow(
            title=r"Pacifist No% Golf Strokes",
            color_key=self.modlunky_config.tracker_color_key,
            font_size=self.modlunky_config.tracker_font_size,
            font_family=self.modlunky_config.tracker_font_family,
            on_close=self.window_closed,
            file_name="pacino_golf.txt",
            tracker=PacinoGolfTracker(),
            config=self.modlunky_config.trackers.pacino_golf,
        )

    def config_update_callback(self):
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.pacino_golf)

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.golf_button.winfo_exists():
            self.golf_button["state"] = tk.NORMAL

    def disable_button(self):
        self.golf_button["state"] = tk.DISABLED


class PacinoGolfTracker(Tracker[PacinoGolfTrackerConfig, WindowData]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_strokes = 0
        self.resource_strokes = 0
        self.treasure_strokes = 0
        self.treasure_strokes_level = 0
        self.pacifist_strokes = 0

        self.world = 0
        self.level = 0

    def initialize(self):
        self.total_strokes = 0
        self.resource_strokes = 0
        self.treasure_strokes = 0
        self.treasure_strokes_level = 0
        self.pacifist_strokes = 0

        self.world = 0
        self.level = 0

    def poll(self, proc: Spel2Process, config: PacinoGolfTrackerConfig) -> WindowData:
        game_state = proc.get_state()
        if game_state is None:
            return None

        world = game_state.world
        level = game_state.level

        # Save treasure strokes on level change
        if world != self.world or level != self.level:
            self.world = world
            self.level = level
            self.treasure_strokes += self.treasure_strokes_level
            self.treasure_strokes_level = 0

        # Reset strokes on restart
        if (
            world == game_state.world_start
            and level == game_state.level_start
            and game_state.win_state is WinState.NO_WIN
        ):
            self.treasure_strokes = 0

        # Count strokes
        if game_state.items is not None:
            player = game_state.items.players[0]
            if player is not None and player.inventory is not None:
                self.resource_strokes = (
                    (4 - player.health)
                    + (4 - player.inventory.bombs)
                    + (4 - player.inventory.ropes)
                )
                collected_money = player.inventory.collected_money
                self.treasure_strokes_level = sum(
                    [1 for x in collected_money if x != 0]
                )
                self.pacifist_strokes = player.inventory.kills_total

        self.total_strokes = (
            self.resource_strokes
            + self.treasure_strokes
            + self.treasure_strokes_level
            + self.pacifist_strokes
        )

        label = self.get_text(config)
        return WindowData(label)

    def get_text(self, config: PacinoGolfTrackerConfig):
        out = []
        if config.show_total_strokes:
            out.append(f"Strokes: {self.total_strokes}")
        if config.show_resource_strokes:
            out.append(f"Resources used: {self.resource_strokes}")
        if config.show_treasure_strokes:
            out.append(f"Treasure: {self.treasure_strokes+self.treasure_strokes_level}")
        if config.show_pacifist_strokes:
            out.append(f"Kills: {self.pacifist_strokes}")
        return "\n".join(out)
