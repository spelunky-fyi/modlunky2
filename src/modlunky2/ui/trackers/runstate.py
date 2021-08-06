from enum import IntEnum
import logging
from typing import Set

from modlunky2.mem.entities import (
    BACKPACKS,
    CHAIN_POWERUP_ENTITIES,
    CharState,
    Entity,
    EntityType,
    Inventory,
    LOW_BANNED_ATTACKABLES,
    LOW_BANNED_THROWABLES,
    Layer,
    MOUNTS,
    Mount,
    NON_CHAIN_POWERUP_ENTITIES,
    Player,
    SHIELDS,
    TELEPORT_ENTITIES,
)
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.memrauder.msvc import UnorderedMap
from modlunky2.mem.state import (
    HudFlags,
    PresenceFlags,
    RunRecapFlags,
    Screen,
    State,
    Theme,
    WinState,
)
from modlunky2.ui.trackers.label import Label, RunLabel


logger = logging.getLogger("modlunky2")


# Status of the Abzu/Duat quest chain.
# The properties are for convenience in 'if' conditions.
class ChainStatus(IntEnum):
    UNSTARTED = 0
    IN_PROGRESS = 1
    FAILED = 2

    @property
    def unstarted(self):
        return self is ChainStatus.UNSTARTED

    @property
    def in_progress(self):
        return self is ChainStatus.IN_PROGRESS

    @property
    def failed(self):
        return self is ChainStatus.FAILED


class RunState:
    def __init__(self, always_show_modifiers=False):
        self.always_show_modifiers = always_show_modifiers
        self.run_label = RunLabel()

        # TODO only copy stuff from mem.State if we need to know the previous value
        self.world = 0
        self.level = 0
        self.level_started = False

        self.player_item_types: Set[EntityType] = set()
        self.player_last_item_types: Set[EntityType] = set()

        self.final_death = False

        self.health = 4
        self.bombs = 4
        self.ropes = 4
        self.level_start_ropes = 4

        self.poisoned = False
        self.cursed = False

        # Score
        # For score runs, we require the bow to be carried to Olmec before it's CO.
        # This allows moving the bow while mininig the moon challenge.
        self.is_score_run = False
        self.hou_yis_waddler = False

        # Run Modifiers
        self.no_tp = True
        self.eggplant = False

        # Low%
        self.is_low_percent = True

        # Low% if Chain
        self.failed_low_if_not_chain = False

        # Moon Challenge Mattock is okay if you're going CO
        self.mc_has_swung_mattock = False

        # Chain
        self.chain_status = ChainStatus.UNSTARTED
        self.hou_yis_bow = False
        self.has_chain_powerup = False
        self.had_udjat_eye = False
        self.had_world2_chain_headwear = False
        self.had_ankh = False
        self.held_world4_chain_item = False
        self.had_tablet_of_destiny = False
        self.held_ushabti = False

        # Millionaire
        self.clone_gun_wo_bow = False

        self.world2_theme = None
        self.world4_theme = None

    def update_pacifist(self, run_recap_flags):
        if not bool(run_recap_flags & RunRecapFlags.PACIFIST):
            self.run_label.discard(Label.PACIFIST)

    def update_no_gold(self, run_recap_flags):
        if not bool(run_recap_flags & RunRecapFlags.NO_GOLD):
            self.run_label.discard(Label.NO_GOLD)

    def update_no_tp(self, player_item_types):
        if not self.no_tp:
            return

        for item_type in player_item_types:
            if item_type in TELEPORT_ENTITIES:
                self.no_tp = False
                self.run_label.discard(Label.NO_TELEPORTER)
                return

    def update_eggplant(self, world, player_item_types):
        if self.eggplant:
            return

        # TODO: Remove if we ever add a better heuristic
        if world < 7:
            return

        if EntityType.ITEM_POWERUP_EGGPLANTCROWN in player_item_types:
            self.eggplant = True
            self.run_label.add(Label.EGGPLANT)
            return

    def update_score_items(self, world, player_item_types):
        for item_type in player_item_types:
            if item_type in [
                EntityType.ITEM_PLASMACANNON,
                EntityType.ITEM_POWERUP_TRUECROWN,
            ]:
                self.is_score_run = True
                self.run_label.add(Label.SCORE)

            elif item_type == EntityType.ITEM_HOUYIBOW and world >= 3:
                self.hou_yis_waddler = True

    def update_global_state(self, game_state: State):
        world = game_state.world
        level = game_state.level

        if (world, level) != (self.world, self.level):
            self.level_started = True
        else:
            self.level_started = False

        self.world = world
        self.level = level

    def update_final_death(
        self, player_state: CharState, player_item_types: Set[EntityType]
    ):
        if self.final_death:
            return

        if (
            player_state is CharState.DYING
            and EntityType.ITEM_POWERUP_ANKH not in player_item_types
        ):
            self.final_death = True
            return

    def update_has_mounted_tame(
        self,
        theme: Theme,
        player_overlay: PolyPointer[Entity],
    ):
        if not self.is_low_percent:
            return

        if not player_overlay.present():
            return

        entity_type: EntityType = player_overlay.value.type.id
        # Allowed to ride tamed qilin in tiamats
        if theme == Theme.TIAMAT and entity_type == EntityType.MOUNT_QILIN:
            self.failed_low_if_not_chain = True
            if not self.chain_status.in_progress:
                self.fail_low()
            return

        if entity_type in MOUNTS:
            mount = player_overlay.as_type(Mount)
            if mount is not None and mount.is_tamed:
                self.fail_low()

    def update_starting_resources(self, player: Player):
        if not self.is_low_percent:
            return

        health = player.health
        if (health > self.health and player.state != CharState.DYING) or health > 4:
            self.fail_low()
        self.health = health

        bombs = player.inventory.bombs
        if bombs > self.bombs or bombs > 4:
            self.fail_low()
        self.bombs = bombs

        ropes = player.inventory.ropes
        if ropes > self.level_start_ropes or ropes > 4:
            self.fail_low()
        self.ropes = ropes

    def update_status_effects(
        self, player_state: CharState, player_item_types: Set[EntityType]
    ):
        if not self.is_low_percent:
            return

        # Logical effects disappear sometimes...
        if player_state in {
            CharState.ENTERING,
            CharState.LOADING,
            CharState.EXITING,
        }:
            return

        is_poisoned = False
        is_cursed = False

        for item_type in player_item_types:
            if item_type == EntityType.LOGICAL_POISONED_EFFECT:
                is_poisoned = True
            elif item_type == EntityType.LOGICAL_CURSED_EFFECT:
                is_cursed = True

        if self.poisoned and not is_poisoned and player_state != CharState.DYING:
            self.fail_low()

        if self.cursed and not is_cursed and player_state != CharState.DYING:
            self.fail_low()

        self.poisoned = is_poisoned
        self.cursed = is_cursed

    def update_had_clover(self, hud_flags: HudFlags):
        if not self.is_low_percent:
            return

        if bool(hud_flags & HudFlags.HAVE_CLOVER):
            self.fail_low()

    def update_wore_backpack(self, player_item_types: Set[EntityType]):
        if EntityType.ITEM_JETPACK in player_item_types:
            self.run_label.discard(Label.NO_JETPACK)

        if not self.is_low_percent:
            return

        for item_type in player_item_types:
            if item_type in BACKPACKS:
                self.fail_low()
                return

    def update_held_shield(self, player_item_types: Set[EntityType]):
        if not self.is_low_percent:
            return

        for item_type in player_item_types:
            if item_type in SHIELDS:
                self.fail_low()
                return

    def update_has_chain_powerup(
        self, chain_status: ChainStatus, player_item_types: Set[EntityType]
    ):
        if self.has_chain_powerup:
            return

        for item_type in player_item_types:
            if item_type in CHAIN_POWERUP_ENTITIES:
                self.has_chain_powerup = True
                self.failed_low_if_not_chain = True

        if chain_status.in_progress:
            return

        # Fail low if we've failed the chain and pick up a non-starting powerup
        for item_type in player_item_types:
            if item_type in {
                EntityType.ITEM_POWERUP_ANKH,
                EntityType.ITEM_POWERUP_TABLETOFDESTINY,
            }:
                self.fail_low()

    def update_has_non_chain_powerup(self, player_item_types: Set[EntityType]):
        if not self.is_low_percent:
            return

        for item_type in player_item_types:
            if item_type in NON_CHAIN_POWERUP_ENTITIES:
                self.fail_low()
                return

    def update_attacked_with(
        self,
        last_state: CharState,
        state: CharState,
        layer: Layer,
        world: int,
        level: int,
        theme: Theme,
        presence_flags: PresenceFlags,
        player_item_types: Set[EntityType],
    ):
        if not self.is_low_percent:
            return

        if state != CharState.ATTACKING and last_state != CharState.ATTACKING:
            return

        for item_type in player_item_types:
            if item_type in LOW_BANNED_ATTACKABLES:
                if item_type == EntityType.ITEM_EXCALIBUR and theme == Theme.ABZU:
                    self.failed_low_if_not_chain = True
                    if not self.chain_status.in_progress:
                        self.fail_low()
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
                            ((world, level) in [(3, 1), (5, 1), (7, 1)])
                        ):
                            continue

                    # Hundun
                    if (world, level) == (7, 4):
                        continue

                self.fail_low()
                return

    def update_attacked_with_throwables(
        self,
        player_state: CharState,
        player_last_state: CharState,
        player_last_item_types: Set[EntityType],
        player_item_types: Set[EntityType],
    ):
        if not self.is_low_percent:
            return

        if (
            player_state != CharState.THROWING
            and player_last_state != CharState.THROWING
        ):
            return

        for item_type in player_item_types | player_last_item_types:
            if item_type in LOW_BANNED_THROWABLES:
                self.fail_low()
                return

    def update_chain(self, player_item_types: Set[EntityType]):
        if self.chain_status.failed:
            return

        for item_type in player_item_types:
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

    def update_world_themes(self, world: int, theme: Theme):
        if world not in [2, 4]:
            return

        if theme in [Theme.JUNGLE, Theme.VOLCANA]:
            self.world2_theme = theme
        elif theme in [Theme.TEMPLE, Theme.CITY_OF_GOLD, Theme.DUAT]:
            self.world4_theme = Theme.TEMPLE
            if self.chain_status.in_progress:
                self.run_label.add(Label.DUAT)
        elif theme in [Theme.TIDE_POOL, Theme.ABZU]:
            self.world4_theme = Theme.TIDE_POOL
            if self.chain_status.in_progress:
                self.run_label.add(Label.ABZU)

        if self.world2_theme is Theme.JUNGLE and self.world4_theme in {
            None,
            Theme.TEMPLE,
        }:
            self.run_label.add(Label.JUNGLE_TEMPLE)
        else:
            self.run_label.discard(Label.JUNGLE_TEMPLE)

        # TODO delete this code that can't be reached
        if world is Theme.SUNKEN_CITY:
            self.run_label.set_terminus(Label.SUNKEN_CITY)

    def update_terminus(self, world: int, theme: Theme, win_state: WinState):
        terminus = Label.ANY
        if theme is Theme.COSMIC_OCEAN:
            terminus = Label.COSMIC_OCEAN
        elif self.final_death:
            terminus = Label.DEATH
        elif win_state is WinState.TIAMAT:
            terminus = Label.ANY
        elif win_state is WinState.HUNDUN:
            terminus = Label.SUNKEN_CITY
        elif self.hou_yis_waddler:
            terminus = Label.COSMIC_OCEAN
        elif self.hou_yis_bow and not self.is_score_run:
            terminus = Label.COSMIC_OCEAN
        elif self.had_ankh or self.chain_status.in_progress or world == 7:
            terminus = Label.SUNKEN_CITY

        if terminus is Label.COSMIC_OCEAN:
            self.run_label.discard(Label.NO_CO)
        else:
            self.run_label.add(Label.NO_CO)
        self.run_label.set_terminus(terminus)

    def update_is_chain(
        self, world: int, level: int, theme: Theme, win_state: WinState
    ):
        if self.chain_status.failed:
            return

        if self.chain_status.unstarted:
            if any([self.had_udjat_eye, self.had_world2_chain_headwear]):
                self.start_chain()

        if world == 3:
            if not self.had_world2_chain_headwear:
                self.fail_chain()

        elif world == 4:
            if not all([self.had_world2_chain_headwear, self.had_ankh]):
                self.fail_chain()

            if theme == Theme.TIDE_POOL:
                # Didn't go to Abzu
                if level == 4:
                    self.fail_chain()

                # Didn't pick up excalibur
                if level > 2 and not self.held_world4_chain_item:
                    self.fail_chain()

            elif theme == Theme.TEMPLE:
                # Didn't go to City of Gold or Duat
                if level in (3, 4):
                    self.fail_chain()

                # Didn't pick up scepter
                if level > 1 and not self.held_world4_chain_item:
                    self.fail_chain()

        elif world == 5:
            if not all(
                [
                    self.had_world2_chain_headwear,
                    self.had_ankh,
                    self.held_world4_chain_item,
                    self.had_tablet_of_destiny,
                ]
            ):
                self.fail_chain()

        elif world == 6 and level > 2:
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

        if win_state is WinState.TIAMAT:
            self.fail_chain()

    def update_millionaire(
        self,
        game_state: State,
        inventory: Inventory,
        player_item_types: Set[EntityType],
    ):
        collected_this_level = inventory.money
        collected_prev_levels = inventory.collected_money_total
        shop_and_bonus = game_state.money_shop_total
        net_score = collected_this_level + collected_prev_levels + shop_and_bonus

        # The category requires completion, which gives at least a $100K bonus.
        if net_score >= 900_000:
            self.run_label.add(Label.MILLIONAIRE)

        # We drop millionaire if either:
        # * You used to have enough money, but no longer do
        # * You picked up the clone gun, but won without enough money
        # TODO fix clone gun case
        if net_score < 900_000 and (
            not self.clone_gun_wo_bow or game_state.win_state is not WinState.NO_WIN
        ):
            self.run_label.discard(Label.MILLIONAIRE)

        if self.clone_gun_wo_bow or self.hou_yis_bow:
            return
        # If the clone gun is picked up, without picking up the bow, we assume this is a millionaire attempt.
        if EntityType.ITEM_CLONEGUN in player_item_types:
            self.clone_gun_wo_bow = True
            self.run_label.add(Label.MILLIONAIRE)

    def start_chain(self):
        self.chain_status = ChainStatus.IN_PROGRESS
        self.run_label.add(Label.CHAIN)

    def fail_chain(self):
        self.chain_status = ChainStatus.FAILED
        self.run_label.discard(Label.CHAIN)
        if self.failed_low_if_not_chain:
            self.fail_low()

    def fail_low(self):
        self.is_low_percent = False
        self.run_label.discard(Label.LOW)

    def update_on_level_start(self, world: int, theme: Theme, ropes: int):
        if not self.level_started:
            return

        self.update_world_themes(world, theme)

        self.level_start_ropes = ropes
        if theme == Theme.DUAT:
            self.health = 4

        if theme == Theme.OLMEC:
            # TODO fail if we leave the bow behind, or win w/o CO
            if self.mc_has_swung_mattock and not self.hou_yis_bow:
                self.fail_low()

    def update(self, game_state: State):
        if game_state.items is None:
            return
        player = game_state.items.players[0]
        if player is None:
            return

        state = player.state
        last_state = player.last_state
        layer = player.layer

        if player.inventory is None:
            return

        run_recap_flags = game_state.run_recap_flags
        hud_flags = game_state.hud_flags
        presence_flags = game_state.presence_flags
        self.update_global_state(game_state)
        self.update_on_level_start(game_state.world, game_state.theme, self.ropes)
        self.update_player_item_types(game_state.instance_id_to_pointer, player)
        self.update_final_death(state, self.player_item_types)

        self.update_score_items(game_state.world, self.player_item_types)

        # Check Modifiers
        self.update_pacifist(run_recap_flags)
        self.update_no_gold(run_recap_flags)
        self.update_no_tp(self.player_item_types)
        self.update_eggplant(game_state.world, self.player_item_types)

        # Check Category Criteria
        overlay = player.overlay

        # Low%
        self.update_has_mounted_tame(game_state.theme, overlay)
        self.update_starting_resources(player)
        self.update_status_effects(state, self.player_item_types)
        self.update_had_clover(hud_flags)
        self.update_wore_backpack(self.player_item_types)
        self.update_held_shield(self.player_item_types)
        self.update_has_non_chain_powerup(self.player_item_types)
        self.update_attacked_with(
            last_state,
            state,
            layer,
            game_state.world,
            self.level,
            game_state.theme,
            presence_flags,
            self.player_item_types,
        )
        self.update_attacked_with_throwables(
            last_state,
            state,
            self.player_last_item_types,
            self.player_item_types,
        )

        # Chain
        self.update_chain(self.player_item_types)
        self.update_has_chain_powerup(self.chain_status, self.player_item_types)
        self.update_is_chain(
            game_state.world, self.level, game_state.theme, game_state.win_state
        )

        self.update_millionaire(game_state, player.inventory, self.player_item_types)

        self.update_terminus(game_state.world, game_state.theme, game_state.win_state)

    def update_player_item_types(
        self,
        instance_id_to_pointer: UnorderedMap[int, PolyPointer[Entity]],
        player: Player,
    ):
        item_types = set()
        if player.items is None:
            return
        for item in player.items:
            entity_poly = instance_id_to_pointer.get(item)
            if entity_poly is None or not entity_poly.present():
                continue

            entity_type = entity_poly.value.type
            if entity_type is None:
                continue

            item_types.add(entity_type.id)

        self.player_last_item_types = self.player_item_types
        self.player_item_types = item_types

    def should_show_modifiers(self, screen: Screen):
        if self.always_show_modifiers:
            return True

        if screen == Screen.SCORES:
            return True

        if self.world > 1:
            return True

        if self.level > 2:
            return True

        if self.final_death:
            return True

        return False

    def get_display(self, screen: Screen):
        return self.run_label.text(not self.should_show_modifiers(screen))
