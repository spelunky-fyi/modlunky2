from enum import Enum
import logging
import tkinter as tk
from tkinter import ttk
from queue import Empty
from typing import Optional, Set

from PIL import Image, ImageTk

from modlunky2.config import Config
from modlunky2.constants import BASE_DIR
from modlunky2.mem import Spel2Process
from modlunky2.mem.entities import (
    BACKPACKS,
    CHAIN_POWERUP_ENTITIES,
    CharState,
    EntityType,
    Inventory,
    LOW_BANNED_ATTACKABLES,
    LOW_BANNED_THROWABLES,
    Layer,
    MOUNTS,
    NON_CHAIN_POWERUP_ENTITIES,
    Player,
    SHIELDS,
    TELEPORT_ENTITIES,
)
from modlunky2.mem.state import (
    HudFlags,
    PresenceFlags,
    RunRecapFlags,
    Theme,
)

from .common import TrackerWindow, WatcherThread, CommonCommand

logger = logging.getLogger("modlunky2")


ICON_PATH = BASE_DIR / "static/images"


class Command(Enum):
    LABEL = "label"


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.ml_config = ml_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)

        self.cat_icon = ImageTk.PhotoImage(
            Image.open(ICON_PATH / "cat2.png").resize((24, 24), Image.ANTIALIAS)
        )

        self.category_button = ttk.Button(
            self,
            image=self.cat_icon,
            text="Category",
            compound="left",
            command=self.launch,
        )
        self.category_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

    def launch(self):
        color_key = self.ml_config.config_file.tracker_color_key
        self.disable_button()
        CategoryWindow(
            title="Category Tracker",
            color_key=color_key,
            on_close=self.enable_button,
        )

    def enable_button(self):
        self.category_button["state"] = tk.NORMAL

    def disable_button(self):
        self.category_button["state"] = tk.DISABLED


class FailedMemoryRead(Exception):
    """Failed to read memory from Spelunky2 process."""


class RunState:
    def __init__(self, proc: Spel2Process):
        self._proc = proc

        self.world = 0
        self.level = 0
        self.theme = 0
        self.level_started = False

        self.player_state: Optional[CharState] = None
        self.player_last_state: Optional[CharState] = None
        self.player_item_types: Set[EntityType] = set()
        self.player_last_item_types: Set[EntityType] = set()

        self.health = 4
        self.bombs = 4
        self.ropes = 4
        self.level_start_ropes = 4

        self.poisoned = False
        self.cursed = False

        # Run Modifiers
        self.pacifist = True
        self.no_gold = True
        self.no_tp = True

        # There are a lot of checks associated with low%
        # if any are violated then don't bother checking them
        self.is_low_percent = True

        # Low%
        self.has_mounted_tame = False
        self.increased_starting_items = False
        self.cured_status = False
        self.had_clover = False
        self.wore_backpack = False
        self.held_shield = False
        self.has_non_chain_powerup = False
        self.attacked_with = False

        # Other category specifiers
        self.chain_powerups = set()
        self.hou_yis_bow = False
        self.chain_theme = None

    def update_pacifist(self, run_recap_flags):
        if not self.pacifist:
            return

        self.pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)

    def update_no_gold(self, run_recap_flags):
        if not self.no_gold:
            return

        self.no_gold = bool(run_recap_flags & RunRecapFlags.NO_GOLD)

    def update_no_tp(self):
        if not self.no_tp:
            return

        for item_type in self.player_item_types:
            if item_type in TELEPORT_ENTITIES:
                self.no_tp = False
                return

    def get_critical_state(self, var):
        result = getattr(self._proc.state, var)
        if result is None:
            raise FailedMemoryRead(f"Failed to read critical state for {var}")
        return result

    def update_global_state(self):
        world = self.get_critical_state("world")
        level = self.get_critical_state("level")
        theme = self.get_critical_state("theme")

        if (world, level) != (self.world, self.level):
            self.level_started = True
        else:
            self.level_started = False

        self.world = world
        self.level = level
        self.theme = theme

    def update_has_mounted_tame(self, player_overlay):
        if not self.is_low_percent:
            return

        if not player_overlay:
            return

        entity_type: EntityType = player_overlay.type.id
        # Allowed to ride tamed qilin in tiamats
        if self.theme == Theme.TIAMAT and entity_type == EntityType.MOUNT_QILIN:
            return

        if entity_type in MOUNTS:
            mount = player_overlay.as_mount()
            if mount.is_tamed:
                self.has_mounted_tame = True
                self.is_low_percent = False

    def update_starting_resources(self, player: Player, inventory: Inventory):
        if not self.is_low_percent:
            return

        health = player.health
        if health is not None:

            if (
                health > self.health and self.player_state != CharState.DYING
            ) or health > 4:
                self.increased_starting_items = True
                self.is_low_percent = False
            self.health = health

        bombs = inventory.bombs
        if bombs is not None:
            if bombs > self.bombs or bombs > 4:
                self.increased_starting_items = True
                self.is_low_percent = False
            self.bombs = bombs

        ropes = inventory.ropes
        if ropes is not None:
            if ropes > self.level_start_ropes or ropes > 4:
                self.increased_starting_items = True
                self.is_low_percent = False
            self.ropes = ropes

    def update_status_effects(self):
        if not self.is_low_percent:
            return

        is_poisoned = False
        is_cursed = False

        for item_type in self.player_item_types:
            if item_type == EntityType.LOGICAL_POISONED_EFFECT:
                is_poisoned = True
            elif item_type == EntityType.LOGICAL_CURSED_EFFECT:
                is_cursed = True

        if self.poisoned and not is_poisoned:
            self.cured_status = True
            self.is_low_percent = False

        if self.cursed and not is_cursed:
            self.cured_status = True
            self.is_low_percent = False

        self.poisoned = is_poisoned
        self.cursed = is_cursed

    def update_had_clover(self, hud_flags: HudFlags):
        if not self.is_low_percent:
            return

        self.had_clover = bool(hud_flags & HudFlags.HAVE_CLOVER)
        if self.had_clover:
            self.is_low_percent = False

    def update_wore_backpack(self):
        if not self.is_low_percent:
            return

        for item_type in self.player_item_types:
            if item_type in BACKPACKS:
                self.wore_backpack = True
                self.is_low_percent = False
                return

    def update_held_shield(self):
        if not self.is_low_percent:
            return

        for item_type in self.player_item_types:
            if item_type in SHIELDS:
                self.held_shield = True
                self.is_low_percent = False
                return

    def update_has_non_chain_powerup(self):
        if not self.is_low_percent:
            return

        for item_type in self.player_item_types:
            if item_type in NON_CHAIN_POWERUP_ENTITIES:
                self.has_non_chain_powerup = True
                self.is_low_percent = False
                return

    def update_attacked_with(self, layer: Layer, presence_flags: PresenceFlags):
        if not self.is_low_percent:
            return

        if (
            self.player_state != CharState.ATTACKING
            and self.player_last_state != CharState.ATTACKING
        ):
            return

        for item_type in self.player_item_types:
            if item_type in LOW_BANNED_ATTACKABLES:
                if item_type == EntityType.ITEM_EXCALIBUR and self.theme == Theme.ABZU:
                    continue

                if (
                    item_type == EntityType.ITEM_MATTOCK
                    and layer == Layer.BACK
                    and presence_flags & PresenceFlags.MOON_CHALLENGE
                ):
                    continue

                if item_type == EntityType.ITEM_HOUYIBOW:
                    if layer == Layer.BACK:
                        # Moon challenge
                        if presence_flags & PresenceFlags.MOON_CHALLENGE:
                            continue

                        # Sun Challenge
                        if presence_flags & PresenceFlags.SUN_CHALLENGE:
                            continue

                        # Waddler
                        if (self.world, self.level) in [(3, 1), (5, 1), (7, 1)]:
                            continue

                    # Hundun
                    if (self.world, self.level) == (7, 4):
                        continue

                self.attacked_with = True
                self.is_low_percent = False
                return

    def update_attacked_with_throwables(self):
        if not self.is_low_percent:
            return

        if (
            self.player_state != CharState.THROWING
            and self.player_last_state != CharState.THROWING
        ):
            return

        for item_type in self.player_item_types | self.player_last_item_types:
            if item_type in LOW_BANNED_THROWABLES:
                self.attacked_with = True
                self.is_low_percent = False
                return

    def update_chain(self):
        for item_type in self.player_item_types:
            if item_type in CHAIN_POWERUP_ENTITIES:
                self.chain_powerups.add(item_type)
            elif item_type == EntityType.ITEM_HOUYIBOW:
                self.hou_yis_bow = True

        if self.theme in [Theme.TEMPLE, Theme.CITY_OF_GOLD, Theme.DUAT]:
            self.chain_theme = Theme.TEMPLE
        elif self.theme in [Theme.TIDE_POOL, Theme.ABZU]:
            self.chain_theme = Theme.TIDE_POOL

    def update_on_level_start(self):
        if not self.level_started:
            return

        self.level_start_ropes = self.ropes
        if self.theme == Theme.DUAT:
            self.health = 4

    def update(self):
        player = self._proc.state.players[0]
        if player is None:
            return

        inventory = player.inventory
        state = player.state
        last_state = player.last_state
        layer = player.layer

        if not all(var is not None for var in [inventory, state, last_state, layer]):
            return

        self.player_state = state
        self.player_last_state = last_state

        run_recap_flags = self.get_critical_state("run_recap_flags")
        hud_flags = self.get_critical_state("hud_flags")
        presence_flags = self.get_critical_state("presence_flags")
        self.update_global_state()
        self.update_on_level_start()
        self.update_player_item_types(player)

        # Check Modifiers
        self.update_pacifist(run_recap_flags)
        self.update_no_gold(run_recap_flags)
        self.update_no_tp()

        # Check Category Criteria
        overlay = player.overlay

        # Low%
        self.update_has_mounted_tame(overlay)
        self.update_starting_resources(player, inventory)
        self.update_status_effects()
        self.update_had_clover(hud_flags)
        self.update_wore_backpack()
        self.update_held_shield()
        self.update_has_non_chain_powerup()
        self.update_attacked_with(layer, presence_flags)
        self.update_attacked_with_throwables()

        # Other Category Specifiers
        self.update_chain()

    def update_player_item_types(self, player: Player):
        item_types = set()
        entity_map = self._proc.state.uid_to_entity
        for item in player.items:
            entity = entity_map.get(item)
            if entity is None:
                continue

            entity_type = entity.type
            if entity_type is None:
                continue

            entity_type = entity_type.entity_type
            if entity_type is not None:
                item_types.add(entity_type)

        self.player_last_item_types = self.player_item_types
        self.player_item_types = item_types

    def get_low_category(self):
        if self.hou_yis_bow:
            if self.chain_powerups:
                return "Chain Low% Cosmic Ocean"
            else:
                return "Low% Cosmic Ocean"

        if self.chain_powerups:
            if self.chain_theme is None:
                return "Chain Low% Sunken City"
            elif self.chain_theme == Theme.TIDE_POOL:
                return "Chain Low% Abzu"
            elif self.chain_theme == Theme.TEMPLE:
                return "Chain Low% Duat"

        if self.world >= 7:
            return "Low% Sunken City"

        return "Low%"

    def get_any_category(self):
        if self.hou_yis_bow:
            return "Cosmic Ocean%"

        if (
            EntityType.ITEM_POWERUP_ANKH in self.chain_powerups
            and len(self.chain_powerups) == 1
        ):
            return "Sunken City%"

        if self.chain_powerups:
            if self.chain_theme is None:
                return "Chain Sunken City%"
            elif self.chain_theme == Theme.TIDE_POOL:
                return "Sunken City% Abzu"
            elif self.chain_theme == Theme.TEMPLE:
                return "Sunken City% Duat"

        if self.world >= 7:
            return "Sunken City%"

        return "Any%"

    def get_category(self):
        if self.player_state == CharState.DYING:
            return "Death%"

        if self.is_low_percent:
            return self.get_low_category()

        return self.get_any_category()

    def should_show_modifiers(self):
        if self.world > 1:
            return True

        if self.level > 2:
            return True

        if self.player_state == CharState.DYING:
            return True

        return False

    def get_display(self):
        out = []

        if self.should_show_modifiers():
            if self.pacifist:
                out.append("Pacifist")

            if self.no_gold:
                out.append("No Gold")

            if self.no_tp and (
                not self.is_low_percent or self.player_state == CharState.DYING
            ):
                out.append("No TP")

        out.append(self.get_category())

        return " ".join(out)


class CategoryWatcherThread(WatcherThread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_total = None
        self.run_state = None

    def initialize(self):
        self.time_total = 0
        self.run_state = RunState(self.proc)

    def get_time_total(self):
        time_total = self.proc.state.time_total
        if time_total is None:
            raise FailedMemoryRead("Failed to read time_total")
        return time_total

    def _poll(self):
        # If we've never been initialized go ahead and do that now.
        if self.time_total is None:
            self.initialize()

        # Check if we've reset, if so, reinitialize
        new_time_total = self.get_time_total()
        if new_time_total < self.time_total:
            self.initialize()
        self.time_total = new_time_total

        self.run_state.update()
        label = self.run_state.get_display()
        self.send(Command.LABEL, label)

    def poll(self):
        try:
            self._poll()
        except FailedMemoryRead as err:
            logger.critical(
                "Failed to read expected memory... (%s). Shutting down.", err
            )
            self.shutdown()


class CategoryWindow(TrackerWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        font = tk.font.Font(family="Helvitica", size=42, weight="bold")

        self.label = tk.Label(
            self, text="Connecting...", bg=self.color_key, fg="white", font=font
        )
        self.label.columnconfigure(0, weight=1)
        self.label.rowconfigure(0, weight=1)
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.watcher_thread = CategoryWatcherThread(self.queue)
        self.watcher_thread.start()
        self.after(100, self.after_watcher_thread)

    def after_watcher_thread(self):
        schedule_again = True
        try:
            while True:
                if self.watcher_thread and not self.watcher_thread.is_alive():
                    logger.warning("Thread went away. Closing window.")
                    schedule_again = False
                    self.destroy()

                try:
                    msg = self.queue.get_nowait()
                except Empty:
                    break

                if msg["command"] == CommonCommand.DIE:
                    logger.critical("%s", msg["data"])
                    schedule_again = False
                    self.destroy()
                elif msg["command"] == Command.LABEL:
                    self.label.configure(text=msg["data"])

        finally:
            if schedule_again:
                self.after(100, self.after_watcher_thread)

    def destroy(self):
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.shut_down = True

        if self.on_close:
            self.on_close()

        super().destroy()
