from enum import Enum
import logging
import tkinter as tk
from tkinter import ttk
from queue import Empty

from win32process import ReadProcessMemory

from modlunky2.config import Config
from modlunky2.mem import Spel2Process
from modlunky2.mem.entities import (
    EntityType,
    Inventory,
    MOUNTS,
    Player,
    TELEPORT_ENTITIES,
)
from modlunky2.mem.state import HudFlags, RunRecapFlags

from .common import TrackerWindow, WatcherThread, CommonCommand

logger = logging.getLogger("modlunky2")


class Command(Enum):
    LABEL = "label"


class CategoryButtons(ttk.Frame):
    def __init__(self, parent, ml_config: Config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.ml_config = ml_config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, minsize=60)

        self.category_button = ttk.Button(
            self,
            text="Category",
            command=self.launch,
        )
        self.category_button.grid(row=0, column=0, pady=5, padx=5, sticky="nswe")

    def launch(self):
        chroma_key = self.ml_config.config_file.tracker_chroma_key
        self.disable_button()
        CategoryWindow(
            title="Category Tracker",
            chroma_key=chroma_key,
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

        self.health = 4
        self.bombs = 4
        self.ropes = 4

        self.poisoned = False
        self.cursed = False

        # Run Modifiers
        self.pacifist = True
        self.no_gold = True
        self.no_tp = True

        # Category Criteria
        self.has_mounted_tame = False
        self.increased_starting_items = False
        self.cured_status = False
        self.had_clover = False

    def update_pacifist(self, run_recap_flags):
        self.pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)

    def update_no_gold(self, run_recap_flags):
        self.no_gold = bool(run_recap_flags & RunRecapFlags.NO_GOLD)

    def update_no_tp(self, item_types):
        for item_type in item_types:
            if item_type in TELEPORT_ENTITIES:
                self.no_tp = False
                return

    def update_has_mounted_tame(self, player_overlay):
        if not player_overlay:
            return

        if player_overlay.type.id in MOUNTS:
            mount = player_overlay.as_mount()
            if mount.is_tamed:
                self.has_mounted_tame = True

    def get_critical_state(self, var):
        result = getattr(self._proc.state, var)
        if result is None:
            raise ReadProcessMemory(f"Failed to read critical state for {var}")
        return result

    def update_global_state(self):
        self.world = self.get_critical_state("world")
        self.level = self.get_critical_state("level")
        self.theme = self.get_critical_state("theme")

    def update_starting_resources(self, player: Player, inventory: Inventory):
        health = player.health
        if health is not None:
            if health > self.health:
                self.increased_starting_items = True
            self.health = health

        bombs = inventory.bombs
        if bombs is not None:
            if bombs > self.bombs:
                self.increased_starting_items = True
            self.bombs = bombs

        ropes = inventory.ropes
        if ropes is not None:
            if ropes > self.ropes:
                delta = ropes - self.ropes
                # Increasing ropes by less than rope pile means
                # you're likely picking up a single rope you dropped
                # which is allowed.
                if delta > 3:
                    self.increased_starting_items = True
            self.ropes = ropes

    def update_status_effects(self, item_types):
        is_poisoned = False
        is_cursed = False

        for item_type in item_types:
            if item_type == EntityType.LOGICAL_POISONED_EFFECT:
                is_poisoned = True
            elif item_type == EntityType.LOGICAL_CURSED_EFFECT:
                is_cursed = True

        if self.poisoned and not is_poisoned:
            self.cured_status = True

        if self.cursed and not is_cursed:
            self.cured_status = True

        self.poisoned = is_poisoned
        self.cursed = is_cursed

    def update_had_clover(self, hud_flags: HudFlags):
        self.had_clover = bool(hud_flags & HudFlags.HAVE_CLOVER)

    def update(self):
        self.update_global_state()
        run_recap_flags = self.get_critical_state("run_recap_flags")
        hud_flags = self.get_critical_state("hud_flags")

        player = self._proc.state.players[0]
        inventory = player.inventory

        if player is None or inventory is None:
            return
        item_types = self.get_player_item_types(player)
        self.update_starting_resources(player, inventory)
        self.update_status_effects(item_types)

        if not self.had_clover:
            self.update_had_clover(hud_flags)

        # Check Modifiers
        if self.pacifist:
            self.update_pacifist(run_recap_flags)

        if self.no_gold:
            self.update_no_gold(run_recap_flags)

        if self.no_tp:
            self.update_no_tp(item_types)

        # Check Category Criteria
        overlay = player.overlay
        if overlay and not self.has_mounted_tame:
            self.update_has_mounted_tame(overlay)

    def get_player_item_types(self, player: Player):
        item_types = set()
        entity_map = self._proc.state.uid_to_entity
        for item in player.items:
            entity_type = entity_map.get(item).type.entity_type
            if entity_type is not None:
                item_types.add(entity_type)
        return item_types

    def is_low_percent(self):
        if self.has_mounted_tame:
            return False

        if self.increased_starting_items:
            return False

        if self.cured_status:
            return False

        if self.had_clover:
            return False

        return True

    def get_category(self):
        if self.is_low_percent():
            return "Low%"

        return "Any%"

    def should_show_modifiers(self):
        if self.world > 1:
            return True

        if self.level > 2:
            return True

        return False

    def get_display(self):
        out = []

        if self.should_show_modifiers():
            if self.pacifist:
                out.append("Pacifist")

            if self.no_gold:
                out.append("No Gold")

            if not self.is_low_percent() and self.no_tp:
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
            self, text="Connecting...", bg=self.chroma_key, fg="white", font=font
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
