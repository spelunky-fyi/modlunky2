import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.config import Config, PacinoGolfTrackerConfig
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process
from modlunky2.mem.state import Theme, WinState

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowData,
)
from modlunky2.ui.trackers.runstate import RunState

logger = logging.getLogger(__name__)


ICON_PATH = BASE_DIR / "static/images"


"""
Notes:
    - The tracker does not work in multiplayer
    - Treasure collected in levels where the tracker wasn't open is not counted

Pacifist issues:
    - You can violate pacifist without a kill, thereby not gaining a stroke when you should (Red Skeleton, Witch Doctor Skull)
    - You can get a kill without violating pacifist, thereby gaining a stroke when you shouldn't (Hundun)
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
            text=r"Pacino Golf Tracker Options",
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

        self.bombs = 4
        self.ropes = 4

        self.time_total = None
        self.run_state = None
        self.is_low = True

    def initialize(self):
        self.total_strokes = 0
        self.resource_strokes = 0
        self.treasure_strokes = 0
        self.treasure_strokes_level = 0
        self.pacifist_strokes = 0

        self.world = 0
        self.level = 0

        self.bombs = 4
        self.ropes = 4

        self.time_total = 0
        self.run_state = RunState()
        self.is_low = True

    def poll(self, proc: Spel2Process, config: PacinoGolfTrackerConfig) -> WindowData:
        game_state = proc.get_state()
        if game_state is None:
            return None

        # Check if we've reset, if so, reinitialize
        new_time_total = game_state.time_total
        if new_time_total < self.time_total:
            self.initialize()
        self.time_total = new_time_total

        # Update run state and check low%
        self.run_state.update(game_state)
        self.is_low = self.run_state.is_low_percent

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
            # Counts resources (health, bombs, ropes) (only works in singleplayer)
            resources_used = 0
            if game_state.theme not in [Theme.BEFORE_FIRST_RUN, Theme.BASE_CAMP]:
                player = game_state.items.players[0]
                STARTING_RESOURCES = 12
                if player is not None:
                    self.bombs = player.inventory.bombs
                    self.ropes = player.inventory.ropes
                    resources_used = (
                        STARTING_RESOURCES - self.bombs - self.ropes - player.health
                    )
                else:
                    resources_used = STARTING_RESOURCES - self.bombs - self.ropes - 0

            # Counts treasure and kills (works in co-op)
            treasure_collected = 0
            kills = 0
            for inventory in game_state.items.player_inventory:
                if inventory is not None:
                    treasure_collected += sum(
                        [1 for x in inventory.collected_money if x != 0]
                    )
                    kills += inventory.kills_total

            self.resource_strokes = resources_used
            self.treasure_strokes_level = treasure_collected
            self.pacifist_strokes = kills

        self.total_strokes = (
            self.resource_strokes
            + (self.treasure_strokes + self.treasure_strokes_level)
            + self.pacifist_strokes
        )

        label = self.get_text(config)
        return WindowData(label)

    def get_text(self, config: PacinoGolfTrackerConfig):
        out = []
        if config.show_total_strokes:
            if self.is_low:
                out.append(f"Strokes: {self.total_strokes}")
            else:
                out.append(f"Strokes: ∞")
        if config.show_resource_strokes:
            out.append(f"Resources used: {self.resource_strokes}")
        if config.show_treasure_strokes:
            out.append(f"Treasure: {self.treasure_strokes+self.treasure_strokes_level}")
        if config.show_pacifist_strokes:
            out.append(f"Kills: {self.pacifist_strokes}")
        return "\n".join(out)
