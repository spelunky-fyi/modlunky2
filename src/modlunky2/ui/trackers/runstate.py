import logging
from typing import Optional, Set

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
    WinState,
)


logger = logging.getLogger("modlunky2")


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
        self.win_state: WinState = WinState.UNKNOWN

        self.health = 4
        self.bombs = 4
        self.ropes = 4
        self.level_start_ropes = 4

        self.poisoned = False
        self.cursed = False

        # Score
        self.is_score_run = False
        self.hou_yis_waddler = False

        # Run Modifiers
        self.pacifist = True
        self.no_gold = True
        self.no_tp = True
        self.eggplant = False

        # Low%
        self.is_low_percent = True
        self.has_mounted_tame = False
        self.increased_starting_items = False
        self.cured_status = False
        self.had_clover = False
        self.wore_backpack = False
        self.held_shield = False
        self.has_non_chain_powerup = False
        self.attacked_with = False

        # Low% if Chain
        self.failed_low_if_not_chain = False
        self.lc_has_mounted_qilin = False
        self.lc_has_swung_excalibur = False
        self.lc_has_fired_hou_yis_bow = False
        self.lc_has_swung_mattock = False

        # Chain
        self.is_chain: Optional[bool] = None  # None if not yet, False if failed chain
        self.hou_yis_bow = False
        self.chain_theme = None
        self.has_chain_powerup = False
        self.had_udjat_eye = False
        self.had_world2_chain_headwear = False
        self.had_ankh = False
        self.held_world4_chain_item = False
        self.had_tablet_of_destiny = False
        self.held_ushabti = False

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

    def update_eggplant(self):
        if self.eggplant:
            return

        # TODO: Remove if we ever add a better heuristic
        if self.world < 7:
            return

        for item_type in self.player_item_types:
            if item_type == EntityType.ITEM_POWERUP_EGGPLANTCROWN:
                self.eggplant = True
                return

    def update_score_items(self):
        for item_type in self.player_item_types:
            if item_type in [
                EntityType.ITEM_PLASMACANNON,
                EntityType.ITEM_POWERUP_TRUECROWN,
            ]:
                self.is_score_run = True

            elif item_type == EntityType.ITEM_HOUYIBOW and self.world >= 3:
                self.hou_yis_waddler = True

    def get_critical_state(self, var):
        result = getattr(self._proc.state, var)
        if result is None:
            raise FailedMemoryRead(f"Failed to read critical state for {var}")
        return result

    def update_global_state(self):
        world = self.get_critical_state("world")
        level = self.get_critical_state("level")
        theme = self.get_critical_state("theme")
        win_state = self.get_critical_state("win_state")

        if (world, level) != (self.world, self.level):
            self.level_started = True
        else:
            self.level_started = False

        self.world = world
        self.level = level
        self.theme = theme
        self.win_state = win_state

    def update_has_mounted_tame(self, player_overlay):
        if not self.is_low_percent:
            return

        if not player_overlay:
            return

        entity_type: EntityType = player_overlay.type.id
        # Allowed to ride tamed qilin in tiamats
        if self.theme == Theme.TIAMAT and entity_type == EntityType.MOUNT_QILIN:
            self.lc_has_mounted_qilin = True
            self.failed_low_if_not_chain = True
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

    def update_has_chain_powerup(self):
        if self.has_chain_powerup:
            return

        for item_type in self.player_item_types:
            if item_type in CHAIN_POWERUP_ENTITIES:
                self.has_chain_powerup = True
                self.failed_low_if_not_chain = True
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
                    self.lc_has_swung_excalibur = True
                    self.failed_low_if_not_chain = True
                    continue

                if (
                    item_type == EntityType.ITEM_MATTOCK
                    and layer == Layer.BACK
                    and presence_flags & PresenceFlags.MOON_CHALLENGE
                ):
                    self.lc_has_swung_mattock = True
                    self.failed_low_if_not_chain = True
                    continue

                if item_type == EntityType.ITEM_HOUYIBOW:
                    if layer == Layer.BACK:
                        if (
                            # Moon challenge
                            (presence_flags & PresenceFlags.MOON_CHALLENGE)
                            or
                            # Sun Challenge
                            (presence_flags & PresenceFlags.SUN_CHALLENGE)
                            or
                            # Waddler
                            ((self.world, self.level) in [(3, 1), (5, 1), (7, 1)])
                        ):
                            self.lc_has_fired_hou_yis_bow = True
                            self.failed_low_if_not_chain = True
                            continue

                    # Hundun
                    if (self.world, self.level) == (7, 4):
                        self.lc_has_fired_hou_yis_bow = True
                        self.failed_low_if_not_chain = True
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
        if self.is_chain is False:
            return

        for item_type in self.player_item_types:
            if item_type == EntityType.ITEM_POWERUP_UDJATEYE:
                self.had_udjat_eye = True
            elif item_type in [
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_HEDJET,
            ]:
                self.had_world2_chain_headwear = True
            elif item_type == EntityType.ITEM_POWERUP_ANKH:
                self.had_ankh = True
            elif item_type in [EntityType.ITEM_EXCALIBUR, EntityType.ITEM_SCEPTER]:
                self.held_world4_chain_item = True
            elif item_type == EntityType.ITEM_POWERUP_TABLETOFDESTINY:
                self.had_tablet_of_destiny = True
            elif item_type == EntityType.ITEM_USHABTI:
                self.held_ushabti = True
            elif item_type == EntityType.ITEM_HOUYIBOW:
                self.hou_yis_bow = True

        if self.theme in [Theme.TEMPLE, Theme.CITY_OF_GOLD, Theme.DUAT]:
            self.chain_theme = Theme.TEMPLE
        elif self.theme in [Theme.TIDE_POOL, Theme.ABZU]:
            self.chain_theme = Theme.TIDE_POOL

    def update_is_chain(self):
        if self.is_chain is False:
            return

        if self.is_chain is None:
            if any([self.had_udjat_eye, self.had_world2_chain_headwear]):
                self.is_chain = True

        if self.world == 3:
            if not self.had_world2_chain_headwear:
                self.is_chain = False

        elif self.world == 4:
            if not all([self.had_world2_chain_headwear, self.had_ankh]):
                self.is_chain = False

            if self.theme == Theme.TIDE_POOL:
                # Didn't go to Abzu
                if self.level == 4:
                    self.is_chain = False

                # Didn't pick up excalibur
                if self.level > 2 and not self.held_world4_chain_item:
                    self.is_chain = False

            elif self.theme == Theme.TEMPLE:
                # Didn't go to City of Gold or Duat
                if self.level in (3, 4):
                    self.is_chain = False

                # Didn't pick up scepter
                if self.level > 1 and not self.held_world4_chain_item:
                    self.is_chain = False

        elif self.world == 5:
            if not all(
                [
                    self.had_world2_chain_headwear,
                    self.had_ankh,
                    self.held_world4_chain_item,
                    self.had_tablet_of_destiny,
                ]
            ):
                self.is_chain = False

        elif self.world == 6 and self.level > 2:
            if not all(
                [
                    self.had_world2_chain_headwear,
                    self.had_ankh,
                    self.held_world4_chain_item,
                    self.had_tablet_of_destiny,
                    self.held_ushabti,
                ]
            ):
                self.is_chain = False

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

        self.update_score_items()

        # Check Modifiers
        self.update_pacifist(run_recap_flags)
        self.update_no_gold(run_recap_flags)
        self.update_no_tp()
        self.update_eggplant()

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

        # Chain
        self.update_chain()
        self.update_has_chain_powerup()
        self.update_is_chain()

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
        if self.win_state == WinState.TIAMAT:
            return "Low%"

        if self.hou_yis_bow and self.win_state != WinState.HUNDUN:
            if self.is_chain:
                return "Chain Low% Cosmic Ocean"
            else:
                return "Low% Cosmic Ocean"

        if self.is_chain:
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

        if self.win_state == WinState.TIAMAT:
            return "Any%"

        if self.hou_yis_bow and self.win_state != WinState.HUNDUN:
            return "Cosmic Ocean%"

        if self.had_ankh and not any(
            [self.had_udjat_eye, self.had_world2_chain_headwear]
        ):
            return "Sunken City%"

        if self.is_chain:
            if self.chain_theme is None:
                return "Chain Sunken City%"
            elif self.chain_theme == Theme.TIDE_POOL:
                return "Sunken City% Abzu"
            elif self.chain_theme == Theme.TEMPLE:
                return "Sunken City% Duat"

        if self.world >= 7:
            return "Sunken City%"

        return "Any%"

    def is_low_category(self):
        # Failed hard requirements of low%
        if not self.is_low_percent:
            return False

        # Failed chain requirements while not being chain
        if not self.is_chain and self.failed_low_if_not_chain:
            return False

        # Chain run but exited at Tiamat
        if self.is_chain and self.win_state == WinState.TIAMAT:
            return False

        return True

    def get_category(self):
        if self.player_state == CharState.DYING:
            return "Death%"

        if self.is_low_category():
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
        if self.is_score_run:
            return self.get_score_display()

        return self.get_speed_display()

    def get_score_display(self):
        if self.win_state in [WinState.TIAMAT, WinState.HUNDUN]:
            return "Score NO CO"

        if self.hou_yis_waddler:
            return "Score"

        return "Score NO CO"

    def get_speed_display(self):
        out = []

        if self.should_show_modifiers():
            if self.pacifist:
                out.append("Pacifist")

            if self.no_gold:
                out.append("No Gold")

            if self.no_tp and not self.is_low_category():
                out.append("No TP")

        if self.eggplant:
            out.append("Eggplant")

        out.append(self.get_category())

        return " ".join(out)
