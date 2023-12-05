import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from modlunky2.config import Config, GemTrackerConfig
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process

from modlunky2.mem.entities import GEMS, DIAMOND
from modlunky2.mem.state import Theme, WinState

from modlunky2.ui.trackers.common import (
    Tracker,
    TrackerWindow,
    WindowData,
)

logger = logging.getLogger(__name__)


ICON_PATH = BASE_DIR / "static/images"


class GemModifiers(ttk.LabelFrame):
    def __init__(self, parent, gem_tracker_config: GemTrackerConfig, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.gem_tracker_config = gem_tracker_config

        self.show_total_gem_count = tk.BooleanVar()
        self.show_total_gem_count.set(self.gem_tracker_config.show_total_gem_count)
        self.show_gem_count_checkbox = ttk.Checkbutton(
            self,
            text="Total Gem Count",
            variable=self.show_total_gem_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_total_gem_count,
        )
        self.show_gem_count_checkbox.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        self.show_colored_gem_count = tk.BooleanVar()
        self.show_colored_gem_count.set(self.gem_tracker_config.show_colored_gem_count)
        self.show_colored_gem_count_checkbox = ttk.Checkbutton(
            self,
            text="Colored Gem Count",
            variable=self.show_colored_gem_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_colored_gem_count,
        )
        self.show_colored_gem_count_checkbox.grid(
            row=0, column=2, pady=5, padx=5, sticky="w"
        )

        self.show_diamond_count = tk.BooleanVar()
        self.show_diamond_count.set(self.gem_tracker_config.show_diamond_count)
        self.show_diamond_count_checkbox = ttk.Checkbutton(
            self,
            text="Diamond Count",
            variable=self.show_diamond_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_diamond_count,
        )
        self.show_diamond_count_checkbox.grid(
            row=0, column=3, pady=5, padx=5, sticky="w"
        )

        # Yems are gems that should have been ghosted (colorful gems picked up on non-boss-levels)
        self.show_yem_count = tk.BooleanVar()
        self.show_yem_count.set(self.gem_tracker_config.show_yem_count)
        self.show_yem_count_checkbox = ttk.Checkbutton(
            self,
            text="Yem Count",
            variable=self.show_yem_count,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_yem_count,
        )
        self.show_yem_count_checkbox.grid(row=0, column=4, pady=5, padx=5, sticky="w")

        self.show_diamond_percentage = tk.BooleanVar()
        self.show_diamond_percentage.set(
            self.gem_tracker_config.show_diamond_percentage
        )
        self.show_diamond_percentage_checkbox = ttk.Checkbutton(
            self,
            text="Diamond Percentage",
            variable=self.show_diamond_percentage,
            onvalue=True,
            offvalue=False,
            command=self.toggle_show_diamond_percentage,
        )
        self.show_diamond_percentage_checkbox.grid(
            row=0, column=5, pady=5, padx=5, sticky="w"
        )

    def toggle_show_total_gem_count(self):
        self.gem_tracker_config.show_total_gem_count = self.show_total_gem_count.get()
        self.parent.config_update_callback()

    def toggle_show_colored_gem_count(self):
        self.gem_tracker_config.show_colored_gem_count = (
            self.show_colored_gem_count.get()
        )
        self.parent.config_update_callback()

    def toggle_show_diamond_count(self):
        self.gem_tracker_config.show_diamond_count = self.show_diamond_count.get()
        self.parent.config_update_callback()

    def toggle_show_yem_count(self):
        self.gem_tracker_config.show_yem_count = self.show_yem_count.get()
        self.parent.config_update_callback()

    def toggle_show_diamond_percentage(self):
        self.gem_tracker_config.show_diamond_percentage = (
            self.show_diamond_percentage.get()
        )
        self.parent.config_update_callback()


class GemButtons(ttk.Frame):
    def __init__(self, parent, modlunky_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config
        self.columnconfigure(0, weight=1, minsize=200)
        self.columnconfigure(1, weight=10000)
        self.rowconfigure(0, minsize=60)
        self.window = None

        self.gem_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "gem.png").resize((24, 24), Image.Resampling.LANCZOS)
        )

        self.gem_button = ttk.Button(
            self,
            text="Gem",
            image=self.gem_icon,
            compound="left",
            command=self.launch,
            width=1,
        )
        self.gem_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

        self.modifiers = GemModifiers(
            self, self.modlunky_config.trackers.gem, text="Gem Tracker Options"
        )
        self.modifiers.grid(row=0, column=1, pady=5, padx=5, sticky="nswe")

    def launch(self):
        self.disable_button()
        self.window = TrackerWindow(
            title="Gem Tracker",
            color_key=self.modlunky_config.tracker_color_key,
            font_size=self.modlunky_config.tracker_font_size,
            font_family=self.modlunky_config.tracker_font_family,
            on_close=self.window_closed,
            file_name="gem.txt",
            tracker=GemTracker(),
            config=self.modlunky_config.trackers.gem,
        )

    def config_update_callback(self):
        self.modlunky_config.save()
        if self.window:
            self.window.update_config(self.modlunky_config.trackers.gem)

    def window_closed(self):
        self.window = None
        # If we're in the midst of destroy() the button might not exist
        if self.gem_button.winfo_exists():
            self.gem_button["state"] = tk.NORMAL

    def disable_button(self):
        self.gem_button["state"] = tk.DISABLED


class GemTracker(Tracker[GemTrackerConfig, WindowData]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gems_total = 0
        self.gems_level = 0
        self.diamonds_total = 0
        self.diamonds_level = 0
        self.yems_total = 0
        self.yems_level = 0

        self.world = 0
        self.level = 0

    def initialize(self):
        self.gems_total = 0
        self.gems_level = 0
        self.diamonds_total = 0
        self.diamonds_level = 0
        self.yems_total = 0
        self.yems_level = 0

        self.world = 0
        self.level = 0

    def poll(self, proc: Spel2Process, config: GemTrackerConfig) -> WindowData:
        game_state = proc.get_state()
        if game_state is None:
            return None

        level_has_ghost = game_state.theme not in [
            Theme.BASE_CAMP,
            Theme.OLMEC,
            Theme.ABZU,
            Theme.DUAT,
            Theme.TIAMAT,
            Theme.EGGPLANT_WORLD,
            Theme.HUNDUN,
            Theme.COSMIC_OCEAN,
        ]

        world = game_state.world
        level = game_state.level

        # On level change
        if (
            world != self.world or level != self.level
        ) and game_state.theme != Theme.BASE_CAMP:
            # Update world and level
            self.world = world
            self.level = level

            # Add gems from previous level to total
            self.gems_total += self.gems_level
            self.diamonds_total += self.diamonds_level
            self.yems_total += self.yems_level

            # Reset gems for new level (without this, tracker will be wrong for first frame of new level)
            self.gems_level = 0
            self.diamonds_level = 0
            self.yems_level = 0

        # Reset gem count on restart
        if (
            world == game_state.world_start
            and level == game_state.level_start
            and game_state.win_state is WinState.NO_WIN
        ):
            self.gems_total = 0
            self.diamonds_total = 0
            self.yems_total = 0

        # Count gems in current level
        if game_state.items is not None:
            gems = 0
            diamonds = 0
            yems = 0

            for inventory in game_state.items.player_inventory:
                if inventory is not None:
                    collected_money = inventory.collected_money
                    for entity in collected_money:
                        if entity in GEMS:
                            gems += 1
                            if entity == DIAMOND:
                                diamonds += 1
                            elif level_has_ghost:
                                yems += 1

            self.gems_level = gems
            self.diamonds_level = diamonds
            self.yems_level = yems

        label = self.get_text(config)
        return WindowData(label)

    def get_text(self, config: GemTrackerConfig):
        gems = self.gems_total + self.gems_level
        diamonds = self.diamonds_total + self.diamonds_level
        yems = self.yems_total + self.yems_level
        out = []
        if config.show_total_gem_count:
            out.append(f"{'Total gems': >13}: {gems : <4}")
        if config.show_colored_gem_count:
            out.append(f"{'Colorful gems': >13}: {gems-diamonds: <4}")
        if config.show_diamond_count:
            out.append(f"{'Diamonds': >13}: {diamonds: <4}")
        if config.show_yem_count:
            out.append(f"{'Yems': >13}: {yems: <4}")
        if config.show_diamond_percentage:
            diamond_rate = (
                str(
                    round(diamonds / (yems + diamonds) * 100)
                    if (yems + diamonds) > 0
                    else 0
                )
                + "%"
            )
            out.append(f"{'Diamond rate': >13}: {diamond_rate: <4}")

        return "\n".join(out)
