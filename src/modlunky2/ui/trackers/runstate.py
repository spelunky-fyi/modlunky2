from dataclasses import dataclass
import logging
from typing import List, Optional, Set, Tuple

from modlunky2.mem.entities import (
    BACKPACKS,
    CharState,
    Entity,
    EntityType,
    Inventory,
    LOW_BANNED_ATTACKABLES,
    LOW_BANNED_THROWABLES,
    Layer,
    LightEmitter,
    MOUNTS,
    Mount,
    Movable,
    NON_CHAIN_POWERUP_ENTITIES,
    Player,
    SHIELDS,
    TELEPORT_ENTITIES,
)
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.memrauder.msvc import UnorderedMap
from modlunky2.mem.state import (
    HudFlags,
    LoadingState,
    PresenceFlags,
    RunRecapFlags,
    Screen,
    State,
    Theme,
    WinState,
)
from modlunky2.category.chain.common import ChainStatus
from modlunky2.category.chain.sunken import AbzuChain, DuatChain
from modlunky2.category.chain.cosmic import CosmicOceanChain
from modlunky2.category.chain.eggplant import EggplantChain
from modlunky2.ui.trackers.label import Label, RunLabel


logger = logging.getLogger("modlunky2")


@dataclass(frozen=True)
class PlayerMotion:
    position_x: float
    position_y: float
    velocity_x: float
    velocity_y: float

    def extrapolate(self, num_frames) -> Tuple[float, float]:
        # pylint: disable=invalid-name
        x = self.position_x + self.velocity_x * num_frames
        y = self.position_y + self.velocity_y * num_frames
        return (x, y)


class RunState:
    def __init__(self, always_show_modifiers=False):
        self.always_show_modifiers = always_show_modifiers
        self.run_label = RunLabel()

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
        self.is_score_run = False

        # Low%
        self.is_low_percent = True

        # Low% if Chain
        self.failed_low_if_not_chain = False

        # Moon Challenge Mattock is okay if you're going CO
        self.mc_has_swung_mattock = False

        # Chain
        self.had_ankh = False
        # Combined status of Abzu and Duat
        self.sunken_chain_status = ChainStatus.UNSTARTED

        # Millionaire
        self.clone_gun_wo_cosmic = False

        self.world2_theme = None
        self.world4_theme = None

        # Quest chains
        self.abzu_stepper = AbzuChain.make_stepper()
        self.duat_stepper = DuatChain.make_stepper()
        self.cosmic_stepper = CosmicOceanChain.make_stepper()
        self.eggplant_stepper = EggplantChain.make_stepper()

        self.prev_next_uid: Optional[int] = None

    def update_pacifist(self, run_recap_flags):
        if not bool(run_recap_flags & RunRecapFlags.PACIFIST):
            self.run_label.discard(Label.PACIFIST)

    def update_no_gold(self, run_recap_flags):
        if not bool(run_recap_flags & RunRecapFlags.NO_GOLD):
            self.run_label.discard(Label.NO_GOLD, Label.NO)

    def update_no_tp(
        self,
        game_state: State,
        player: Player,
        player_item_set: Set[EntityType],
        prev_player_item_set: Set[EntityType],
    ):
        prev_next_uid = self.prev_next_uid
        self.prev_next_uid = game_state.next_entity_uid
        # At the start of a level, all entities (including floors, treasure, etc.) spawn.
        # Also, the player doesn't gain control for ~600ms anyway
        if self.level_started:
            return

        # This is an optimization to skip scanning when the player couldn't have teleported
        if not self.could_tp(player, player_item_set, prev_player_item_set):
            return

        found_shadows: List[LightEmitter] = []
        for entity_uid in range(prev_next_uid, game_state.next_entity_uid):
            entity_poly = game_state.instance_id_to_pointer.get(entity_uid)
            if entity_poly is None or not entity_poly.present():
                continue
            entity = entity_poly.value
            if entity.type is None:
                continue
            if entity.type.id is not EntityType.FX_TELEPORTSHADOW:
                continue
            # Now that we know it's the right type, downcast
            entity = entity_poly.as_type(LightEmitter)
            if entity is None:
                continue
            if entity.emitted_light is None:
                continue

            found_shadows.append(entity)

        # We need pairs to work with
        num_shadows = len(found_shadows)
        if num_shadows < 2:
            return

        shadow_pairs: List[Tuple[LightEmitter, LightEmitter]] = []
        for i in range(0, num_shadows, 2):
            shadow_pairs.append((found_shadows[i], found_shadows[i + 1]))

        motion = self.compute_player_motion(player)

        # We know the lower ID corresponds to prev position
        for prev_shadow, cur_shadow in shadow_pairs:
            # The only way this can happen is if we read memory in the middle of creating a pair.
            # We prefer a false negative here
            if prev_shadow.idle_counter != cur_shadow.idle_counter:
                continue
            # We now know idle_counter is equal
            x, y = motion.extrapolate(  # pylint: disable=invalid-name
                -cur_shadow.idle_counter
            )
            delta_x = x - cur_shadow.emitted_light.light_pos_x
            delta_y = y - cur_shadow.emitted_light.light_pos_y
            logger.debug("TP shadow deltas %.3f, %.3f", delta_x, delta_y)

            # We might want to make these different because:
            # 1) Uncertainty in Y axis is higher, due to ground/edges
            # 2) Enemies only TP along X axis (modulo up-by-3 rule)
            x_tol = 0.5
            y_tol = 0.5
            if abs(delta_x) < x_tol and abs(delta_y) < y_tol:
                self.run_label.discard(Label.NO_TELEPORTER)

    def could_tp(
        self,
        player: Player,
        player_item_set: Set[EntityType],
        prev_player_item_set: Set[EntityType],
    ):
        if not TELEPORT_ENTITIES.isdisjoint(player_item_set):
            return True
        if not TELEPORT_ENTITIES.isdisjoint(prev_player_item_set):
            return True

        if not player.overlay.present():
            return False

        overlay = player.overlay.value
        if overlay.type is None:
            return False

        return overlay.type.id is EntityType.MOUNT_AXOLOTL

    def compute_player_motion(self, player: Player):
        player_x = player.position_x
        player_y = player.position_y
        player_vx = player.velocity_x
        player_vy = player.velocity_y

        # We use a loop to handle player on a mount on an active floor
        overlay_poly = player.overlay
        while overlay_poly.present():
            overlay = overlay_poly.as_type(Movable)
            if overlay is None:
                break
            if overlay.type is not None and overlay.type.id in MOUNTS:
                # If the player is on a mount, its position is used for the TP effect
                player_x = overlay.position_x
                player_y = overlay.position_y
                player_vx = overlay.velocity_x
                player_vy = overlay.velocity_y
            else:
                # If a player/mount is on an active floor, their position and velocity
                # are relative to the active floor's
                player_x += overlay.position_x
                player_y += overlay.position_y
                player_vx += overlay.velocity_x
                player_vy += overlay.velocity_y
            # We have to go deeper
            overlay_poly = overlay.overlay

        return PlayerMotion(
            position_x=player_x,
            position_y=player_y,
            velocity_x=player_vx,
            velocity_y=player_vy,
        )

    def update_eggplant(self):
        if self.eggplant_stepper.last_status.in_progress:
            self.run_label.add(Label.EGGPLANT)
        else:
            self.run_label.discard(Label.EGGPLANT)

    def update_low_cosmic(self):
        if self.cosmic_stepper.last_status.failed and self.mc_has_swung_mattock:
            self.fail_low()

    def update_ice_caves(self, game_state: State):
        # We only want to add this once
        if not self.level_started:
            return
        if game_state.theme is not Theme.ICE_CAVES:
            return
        if (game_state.world_start, game_state.level_start) != (5, 1):
            return
        self.run_label.add(Label.ICE_CAVES_SHORTCUT)

    def update_score_items(self, player_item_types):
        for item_type in player_item_types:
            if item_type in [
                EntityType.ITEM_PLASMACANNON,
                EntityType.ITEM_POWERUP_TRUECROWN,
            ]:
                self.is_score_run = True
                self.run_label.add(Label.SCORE)

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
            if not self.sunken_chain_status.in_progress:
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
        if health < 4:
            self.run_label.discard(Label.NO)
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

        # Logical effects are removed when we enter the exit-door of the level or level transition.
        # They also aren't present while the character is in 'loading' state (once they go through
        # level-transition exit)
        if player_state in {CharState.ENTERING, CharState.LOADING}:
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

    def update_has_chain_powerup(self, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_ANKH in player_item_types:
            self.had_ankh = True

        if self.sunken_chain_status.in_progress:
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
                    if not self.sunken_chain_status.in_progress:
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

    def update_world_themes(self, world: int, theme: Theme):
        if world not in [2, 4]:
            return

        if theme in [Theme.JUNGLE, Theme.VOLCANA]:
            self.world2_theme = theme
        elif theme in [Theme.TEMPLE, Theme.CITY_OF_GOLD, Theme.DUAT]:
            self.world4_theme = Theme.TEMPLE
        elif theme in [Theme.TIDE_POOL, Theme.ABZU]:
            self.world4_theme = Theme.TIDE_POOL

        if self.world2_theme is Theme.JUNGLE and self.world4_theme in {
            None,
            Theme.TEMPLE,
        }:
            self.run_label.add(Label.JUNGLE_TEMPLE)
        else:
            self.run_label.discard(Label.JUNGLE_TEMPLE)

    def update_terminus(self, game_state: State):
        if self.cosmic_stepper.last_status.in_progress:
            terminus = Label.COSMIC_OCEAN
        elif self.final_death:
            terminus = Label.DEATH
        elif (
            game_state.world == 7
            or self.had_ankh
            or self.sunken_chain_status.in_progress
            or self.eggplant_stepper.last_status.in_progress
        ):
            terminus = Label.SUNKEN_CITY
        else:
            terminus = Label.ANY

        if terminus is Label.COSMIC_OCEAN:
            self.run_label.discard(Label.NO_CO)
        else:
            self.run_label.add(Label.NO_CO)
        self.run_label.set_terminus(terminus)

    def update_is_chain(self):
        if self.sunken_chain_status.failed:
            return

        abzu_status = self.abzu_stepper.last_status
        duat_status = self.duat_stepper.last_status

        if abzu_status.unstarted ^ duat_status.unstarted:
            raise ValueError(
                f"Only one of Abzu and Duat is unstarted. Abzu {abzu_status} Duat {duat_status}"
            )

        if abzu_status.unstarted:
            self.sunken_chain_status = ChainStatus.UNSTARTED
            return

        if abzu_status.in_progress or duat_status.in_progress:
            self.run_label.add(Label.CHAIN)
            self.sunken_chain_status = ChainStatus.IN_PROGRESS
            # The ways to start invalidate plain low%
            self.failed_low_if_not_chain = True

        if abzu_status.in_progress and not duat_status.in_progress:
            self.run_label.add(Label.ABZU)

        if duat_status.in_progress and not abzu_status.in_progress:
            self.run_label.add(Label.DUAT)

        if not (abzu_status.failed and duat_status.failed):
            return

        # We've failed both Sunken City chains
        self.sunken_chain_status = ChainStatus.FAILED
        for label in (Label.CHAIN, Label.ABZU, Label.DUAT):
            self.run_label.discard(label)

        if self.failed_low_if_not_chain:
            self.fail_low()

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
        if net_score < 900_000 and (
            not self.clone_gun_wo_cosmic or game_state.win_state is not WinState.NO_WIN
        ):
            self.run_label.discard(Label.MILLIONAIRE)

        if self.clone_gun_wo_cosmic or self.cosmic_stepper.last_status.in_progress:
            return
        # If the clone gun is picked up, without picking up the bow, we assume this is a millionaire attempt.
        if EntityType.ITEM_CLONEGUN in player_item_types:
            self.clone_gun_wo_cosmic = True
            self.run_label.add(Label.MILLIONAIRE)

    def fail_low(self):
        self.is_low_percent = False
        self.run_label.discard(Label.LOW, Label.NO, Label.ICE_CAVES_SHORTCUT)

    def update_on_level_start(self, world: int, theme: Theme, ropes: int):
        if not self.level_started:
            return

        self.update_world_themes(world, theme)

        self.level_start_ropes = ropes
        if theme == Theme.DUAT:
            self.health = 4
            self.poisoned = False
            self.cursed = False

    def update(self, game_state: State):
        if game_state.loading is not LoadingState.NOT_LOADING:
            return
        if game_state.items is None:
            return

        player = game_state.items.players[0]
        if player is None:
            return
        if player.inventory is None:
            return

        run_recap_flags = game_state.run_recap_flags
        hud_flags = game_state.hud_flags
        presence_flags = game_state.presence_flags
        self.update_global_state(game_state)
        self.update_on_level_start(game_state.world, game_state.theme, self.ropes)
        self.update_player_item_types(game_state.instance_id_to_pointer, player)
        self.update_final_death(player.state, self.player_item_types)

        self.update_score_items(self.player_item_types)
        self.update_ice_caves(game_state)

        for stepper in (
            self.abzu_stepper,
            self.duat_stepper,
            self.cosmic_stepper,
            self.eggplant_stepper,
        ):
            stepper.evaluate(game_state, self.player_item_types)

        # Check Modifiers
        self.update_pacifist(run_recap_flags)
        self.update_no_gold(run_recap_flags)
        self.update_no_tp(
            game_state, player, self.player_item_types, self.player_last_item_types
        )
        self.update_eggplant()
        self.update_low_cosmic()

        # Check Category Criteria
        overlay = player.overlay

        # Low%
        self.update_has_mounted_tame(game_state.theme, overlay)
        self.update_starting_resources(player)
        self.update_status_effects(player.state, self.player_item_types)
        self.update_had_clover(hud_flags)
        self.update_wore_backpack(self.player_item_types)
        self.update_held_shield(self.player_item_types)
        self.update_has_non_chain_powerup(self.player_item_types)
        self.update_attacked_with(
            player.last_state,
            player.state,
            player.layer,
            game_state.world,
            self.level,
            game_state.theme,
            presence_flags,
            self.player_item_types,
        )
        self.update_attacked_with_throwables(
            player.last_state,
            player.state,
            self.player_last_item_types,
            self.player_item_types,
        )

        # Chain
        self.update_has_chain_powerup(self.player_item_types)
        self.update_is_chain()

        self.update_millionaire(game_state, player.inventory, self.player_item_types)

        self.update_terminus(game_state)

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
