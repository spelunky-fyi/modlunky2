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
    Screen,
    Theme,
    WinState,
)
from modlunky2.ui.trackers.label import Label, RunLabel


logger = logging.getLogger("modlunky2")


class FailedMemoryRead(Exception):
    """Failed to read memory from Spelunky2 process."""


class RunState:
    def __init__(self, proc: Spel2Process, always_show_modifiers=False):
        self._proc = proc
        self.always_show_modifiers = always_show_modifiers
        self.run_label = RunLabel()
        self._old_classic_text = None
        self._old_new_text = None

        self.world = 0
        self.level = 0
        self.theme = 0
        self.screen = Screen.UNKNOWN
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

        # Moon Challenge Mattock is okay if you're going CO
        self.mc_has_swung_mattock = False

        # Chain
        self.is_chain: Optional[bool] = None  # None if not yet, False if failed chain
        self.hou_yis_bow = False
        self.has_chain_powerup = False
        self.had_udjat_eye = False
        self.had_world2_chain_headwear = False
        self.had_ankh = False
        self.held_world4_chain_item = False
        self.had_tablet_of_destiny = False
        self.held_ushabti = False

        self.world2_theme = None
        self.world4_theme = None

    def update_pacifist(self, run_recap_flags):
        if not self.pacifist:
            return

        self.pacifist = bool(run_recap_flags & RunRecapFlags.PACIFIST)
        if not self.pacifist:
            self.run_label.discard(Label.PACIFIST)

    def update_no_gold(self, run_recap_flags):
        if not self.no_gold:
            return

        self.no_gold = bool(run_recap_flags & RunRecapFlags.NO_GOLD)
        if not self.no_gold:
            self.run_label.discard(Label.NO_GOLD)

    def update_no_tp(self):
        if not self.no_tp:
            return

        for item_type in self.player_item_types:
            if item_type in TELEPORT_ENTITIES:
                self.no_tp = False
                self.run_label.discard(Label.NO_TELEPORTER)
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
                self.run_label.add(Label.EGGPLANT)
                return

    def update_score_items(self):
        for item_type in self.player_item_types:
            if item_type in [
                EntityType.ITEM_PLASMACANNON,
                EntityType.ITEM_POWERUP_TRUECROWN,
            ]:
                self.is_score_run = True
                self.run_label.add(Label.SCORE)

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
        screen = self.get_critical_state("screen")
        win_state = self.get_critical_state("win_state")

        if (world, level) != (self.world, self.level):
            self.level_started = True
        else:
            self.level_started = False

        self.world = world
        self.level = level
        self.theme = theme
        # Cope with weird screen value during shutdown
        try:
            self.screen = Screen(screen)
        except ValueError:
            self.screen = Screen.UNKNOWN
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
            if not self.is_chain:
                self.run_label.discard(Label.LOW)
            return

        if entity_type in MOUNTS:
            mount = player_overlay.as_mount()
            if mount.is_tamed:
                self.has_mounted_tame = True
                self.fail_low()

    def update_starting_resources(self, player: Player, inventory: Inventory):
        if not self.is_low_percent:
            return

        health = player.health
        if health is not None:

            if (
                health > self.health and self.player_state != CharState.DYING
            ) or health > 4:
                self.increased_starting_items = True
                self.fail_low()
            self.health = health

        bombs = inventory.bombs
        if bombs is not None:
            if bombs > self.bombs or bombs > 4:
                self.increased_starting_items = True
                self.fail_low()
            self.bombs = bombs

        ropes = inventory.ropes
        if ropes is not None:
            if ropes > self.level_start_ropes or ropes > 4:
                self.increased_starting_items = True
                self.fail_low()
            self.ropes = ropes

    def update_status_effects(self):
        if not self.is_low_percent:
            return

        # Logical effects disappear sometimes...
        if self.player_state in {
            CharState.ENTERING,
            CharState.LOADING,
            CharState.EXITING,
        }:
            return

        is_poisoned = False
        is_cursed = False

        for item_type in self.player_item_types:
            if item_type == EntityType.LOGICAL_POISONED_EFFECT:
                is_poisoned = True
            elif item_type == EntityType.LOGICAL_CURSED_EFFECT:
                is_cursed = True

        if self.poisoned and not is_poisoned and self.player_state != CharState.DYING:
            self.cured_status = True
            self.fail_low()

        if self.cursed and not is_cursed and self.player_state != CharState.DYING:
            self.cured_status = True
            self.fail_low()

        self.poisoned = is_poisoned
        self.cursed = is_cursed

    def update_had_clover(self, hud_flags: HudFlags):
        if not self.is_low_percent:
            return

        self.had_clover = bool(hud_flags & HudFlags.HAVE_CLOVER)
        if self.had_clover:
            self.fail_low()

    def update_wore_backpack(self):
        if EntityType.ITEM_JETPACK in self.player_item_types:
            self.run_label.discard(Label.NO_JETPACK)

        if not self.is_low_percent:
            return

        for item_type in self.player_item_types:
            if item_type in BACKPACKS:
                self.wore_backpack = True
                self.fail_low()
                return

    def update_held_shield(self):
        if not self.is_low_percent:
            return

        for item_type in self.player_item_types:
            if item_type in SHIELDS:
                self.held_shield = True
                self.fail_low()
                return

    def update_has_chain_powerup(self):
        if self.has_chain_powerup:
            return

        for item_type in self.player_item_types:
            if item_type in CHAIN_POWERUP_ENTITIES:
                self.has_chain_powerup = True
                self.failed_low_if_not_chain = True

        if self.is_chain:
            return

        # Fail low if we've failed the chain and pick up a non-starting powerup
        for item_type in self.player_item_types:
            if item_type in {
                EntityType.ITEM_POWERUP_ANKH,
                EntityType.ITEM_POWERUP_TABLETOFDESTINY,
            }:
                self.fail_low()

    def update_has_non_chain_powerup(self):
        if not self.is_low_percent:
            return

        for item_type in self.player_item_types:
            if item_type in NON_CHAIN_POWERUP_ENTITIES:
                self.has_non_chain_powerup = True
                self.fail_low()
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
                    if not self.is_chain:
                        self.run_label.discard(Label.LOW)
                    continue

                if (
                    item_type == EntityType.ITEM_MATTOCK
                    and layer == Layer.BACK
                    and presence_flags & PresenceFlags.MOON_CHALLENGE
                ):
                    self.mc_has_swung_mattock = True
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
                            continue

                    # Hundun
                    if (self.world, self.level) == (7, 4):
                        continue

                self.attacked_with = True
                self.fail_low()
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
                self.fail_low()
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

    def update_world_themes(self):
        if self.world not in [2, 4]:
            return

        if self.theme in [Theme.JUNGLE, Theme.VOLCANA]:
            self.world2_theme = self.theme
        elif self.theme in [Theme.TEMPLE, Theme.CITY_OF_GOLD, Theme.DUAT]:
            self.world4_theme = Theme.TEMPLE
            if self.is_chain:
                self.run_label.add(Label.DUAT)
        elif self.theme in [Theme.TIDE_POOL, Theme.ABZU]:
            self.world4_theme = Theme.TIDE_POOL
            if self.is_chain:
                self.run_label.add(Label.ABZU)

        if self.world2_theme is Theme.JUNGLE and self.world4_theme is Theme.TEMPLE:
            self.run_label.add(Label.JUNGLE_TEMPLE)

        if self.world is Theme.SUNKEN_CITY:
            self.run_label.set_terminus(Label.SUNKEN_CITY)

    def update_terminus(self):
        terminus = Label.ANY
        if self.theme is Theme.COSMIC_OCEAN:
            terminus = Label.COSMIC_OCEAN
        elif self.player_state == CharState.DYING:
            terminus = Label.DEATH
        elif self.win_state is WinState.TIAMAT:
            terminus = Label.ANY
        elif self.hou_yis_bow and self.win_state is not WinState.HUNDUN:
            terminus = Label.COSMIC_OCEAN
        elif (
            self.had_ankh
            or self.is_chain
            or self.world == 7
            or self.win_state is WinState.HUNDUN
        ):
            terminus = Label.SUNKEN_CITY

        if terminus is Label.COSMIC_OCEAN:
            self.run_label.discard(Label.NO_CO)
        else:
            self.run_label.add(Label.NO_CO)
        self.run_label.set_terminus(terminus)

    def update_is_chain(self):
        if self.is_chain is False:
            return

        if self.is_chain is None:
            if any([self.had_udjat_eye, self.had_world2_chain_headwear]):
                self.start_chain()

        if self.world == 3:
            if not self.had_world2_chain_headwear:
                self.fail_chain()

        elif self.world == 4:
            if not all([self.had_world2_chain_headwear, self.had_ankh]):
                self.fail_chain()

            if self.theme == Theme.TIDE_POOL:
                # Didn't go to Abzu
                if self.level == 4:
                    self.fail_chain()

                # Didn't pick up excalibur
                if self.level > 2 and not self.held_world4_chain_item:
                    self.fail_chain()

            elif self.theme == Theme.TEMPLE:
                # Didn't go to City of Gold or Duat
                if self.level in (3, 4):
                    self.fail_chain()

                # Didn't pick up scepter
                if self.level > 1 and not self.held_world4_chain_item:
                    self.fail_chain()

        elif self.world == 5:
            if not all(
                [
                    self.had_world2_chain_headwear,
                    self.had_ankh,
                    self.held_world4_chain_item,
                    self.had_tablet_of_destiny,
                ]
            ):
                self.fail_chain()

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
                self.fail_chain()

        if self.win_state is WinState.TIAMAT:
            self.fail_chain()

    def start_chain(self):
        self.is_chain = True
        self.run_label.add(Label.CHAIN)

    def fail_chain(self):
        self.is_chain = False
        self.run_label.discard(Label.CHAIN)
        self.is_low_percent = False
        self.run_label.discard(Label.LOW)

    def fail_low(self):
        self.is_low_percent = False
        self.run_label.discard(Label.LOW)

    def update_on_level_start(self):
        if not self.level_started:
            return

        self.update_world_themes()

        self.level_start_ropes = self.ropes
        if self.theme == Theme.DUAT:
            self.health = 4

        if self.theme == Theme.OLMEC:
            if self.mc_has_swung_mattock and not self.hou_yis_bow:
                self.fail_low()

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

        self.update_terminus()

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

    def get_plain_low_percent(self):
        themes = (self.world2_theme, self.world4_theme)
        if themes[0] == Theme.JUNGLE and themes[1] != Theme.TIDE_POOL:
            return "Low% Jungle/Temple"

        return "Low%"

    def get_low_category(self):
        if self.win_state == WinState.TIAMAT:
            return self.get_plain_low_percent()

        if self.hou_yis_bow and self.win_state != WinState.HUNDUN:
            if self.is_chain:
                return "Chain Low% Cosmic Ocean"
            else:
                return "Low% Cosmic Ocean"

        if self.is_chain:
            if self.world4_theme is None:
                return "Chain Low% Sunken City"
            elif self.world4_theme == Theme.TIDE_POOL:
                return "Chain Low% Abzu"
            elif self.world4_theme == Theme.TEMPLE:
                return "Chain Low% Duat"

        if self.world >= 7 or self.win_state == WinState.HUNDUN:
            return "Low% Sunken City"

        return self.get_plain_low_percent()

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
            if self.world4_theme is None:
                return "Chain Sunken City%"
            elif self.world4_theme == Theme.TIDE_POOL:
                return "Sunken City% Abzu"
            elif self.world4_theme == Theme.TEMPLE:
                return "Sunken City% Duat"

        if self.world >= 7 or self.win_state == WinState.HUNDUN:
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
        if self.always_show_modifiers:
            return True

        if self.screen == Screen.SCORES:
            return True

        if self.world > 1:
            return True

        if self.level > 2:
            return True

        if self.player_state == CharState.DYING:
            return True

        return False

    def get_display(self):
        classic_text = (
            self.get_score_display() if self.is_score_run else self.get_speed_display()
        )
        new_text = self.run_label.text(not self.should_show_modifiers())

        # Only log a warning when text changes.
        if classic_text != new_text and (
            classic_text != self._old_classic_text or new_text != self._old_new_text
        ):
            logger.warning(
                "Category text differs. Classic '%s' vs New '%s'",
                classic_text,
                new_text,
            )

        self._old_classic_text = classic_text
        self._old_new_text = new_text
        return classic_text

    def get_score_display(self):
        if self.win_state in [WinState.TIAMAT, WinState.HUNDUN]:
            return "Score No CO"

        if self.hou_yis_waddler:
            return "Score"

        return "Score No CO"

    def get_speed_display(self):
        out = []

        if self.should_show_modifiers():
            if self.pacifist:
                out.append("Pacifist")

            if self.no_gold:
                out.append("No Gold")

            if self.no_tp and not self.is_low_category():
                out.append("No TP")

        out.append(self.get_category())

        if self.eggplant:
            out.append("Eggplant")

        return " ".join(out)
