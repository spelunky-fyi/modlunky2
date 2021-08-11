from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Any, Callable, Generator, Optional, Set

from modlunky2.mem.entities import Entity, EntityType, Player
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.state import Screen, State, Theme, WinState

logger = logging.getLogger("modlunky2")

# Status of the quest chain.
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


ChainStepEvaluator = Callable[[Any, State, Set[EntityType]], "ChainStepResult"]


@dataclass(frozen=True)
class ChainStepResult:
    status: ChainStatus
    # next_step should only be set for IN_PROGRESS
    next_step: Optional[ChainStepEvaluator] = None

    def __post_init__(self):
        if self.status.in_progress:
            if self.next_step is None:
                raise ValueError(
                    f"status {self.status.name} requires next_step to be set"
                )
            if not callable(self.next_step):
                raise ValueError(
                    f"status {self.status.name} requires next_step to be callable"
                )

        if not self.status.in_progress and self.next_step is not None:
            raise ValueError(
                f"status {self.status.name} requires next_step to be None, got {self.next_step}"
            )

    def __str__(self) -> str:
        if self.next_step is None:
            return f"{self.status.name}"
        step_name = self.next_step.__name__
        return f"{self.status.name}, {step_name}"


class ChainStepper:
    def __init__(self, name: str, initial_step: ChainStepEvaluator):
        self.name = name
        self.initial_step = initial_step
        self.last_result = ChainStepResult(ChainStatus.UNSTARTED)

    def evaluate(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStatus:
        if self.last_result.status.failed:
            return ChainStatus.FAILED

        if self.last_result.status.unstarted:
            step = self.initial_step
        else:
            step = self.last_result.next_step

        result = step(game_state, player_item_types)

        if self.last_result != result:
            logger.info("chain %s: %s -> %s", self.name, self.last_result, result)

        self.last_result = result
        return result.status


class ChainMixin:
    def unstarted(self):
        return ChainStepResult(ChainStatus.UNSTARTED)

    def in_progress(self, next_step: ChainStepEvaluator):
        return ChainStepResult(ChainStatus.IN_PROGRESS, next_step)

    def failed(self):
        return ChainStepResult(ChainStatus.FAILED)

    # TODO move companion stuff somewhere more sensible

    def companions(
        self, game_state: State
    ) -> Generator[PolyPointer[Entity], None, None]:
        cur_hand_uid = game_state.items.players[0].linked_companion_child

        while cur_hand_uid != 0:
            cur_hand = game_state.instance_id_to_pointer.get(cur_hand_uid)
            if cur_hand is None or not cur_hand.present():
                return

            yield cur_hand

            cur_hand = cur_hand.as_poly_type(Player)
            if not cur_hand.present():
                return
            cur_hand_uid = cur_hand.value.linked_companion_child

    def some_companion_has_item(self, game_state: State, item_type: EntityType) -> bool:
        for companion in self.companions(game_state):
            companion_items = companion.value.items
            if companion_items is None:
                continue

            for item_uid in companion_items:
                item = game_state.instance_id_to_pointer.get(item_uid)
                if item is None or not item.present():
                    continue
                if item.value.type.id is item_type:
                    return True

        return False

    def some_companion_is(self, game_state: State, companion_type: EntityType) -> bool:
        for companion in self.companions(game_state):
            if companion.value.type is None:
                continue

            if companion.value.type.id is companion_type:
                return True

        return False


class CommonSunkenChain(ChainMixin, ABC):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls.__name__, cls().collect_eye_or_headwear)

    @property
    @abstractmethod
    def world41_theme(self) -> Theme:
        pass

    @property
    @abstractmethod
    def world44_theme(self) -> Theme:
        pass

    @property
    @abstractmethod
    def world4_item_step(self) -> ChainStepEvaluator:
        pass

    def collect_eye_or_headwear(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStepResult:
        if (
            EntityType.ITEM_POWERUP_HEDJET in player_item_types
            or EntityType.ITEM_POWERUP_CROWN in player_item_types
        ):
            return self.in_progress(self.collect_ankh)

        if EntityType.ITEM_POWERUP_UDJATEYE in player_item_types:
            return self.in_progress(self.collect_eye_or_headwear)

        if game_state.world > 2:
            return self.failed()

        return self.unstarted()

    def collect_ankh(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_ANKH in player_item_types:
            return self.in_progress(self.visit_world41_theme)

        if game_state.world > 3:
            return self.failed()

        return self.in_progress(self.collect_ankh)

    def visit_world41_theme(self, game_state: State, _: Set[EntityType]):
        if game_state.theme == self.world41_theme:
            return self.in_progress(self.world4_item_step)

        if game_state.world > 3:
            return self.failed()

        return self.in_progress(self.visit_world41_theme)

    def visit_world44_theme(self, game_state: State, _: Set[EntityType]):
        if game_state.theme == self.world44_theme:
            return self.in_progress(self.collect_tablet)

        if (game_state.world, game_state.level) > (4, 3):
            return self.failed()

        return self.in_progress(self.visit_world44_theme)

    def collect_tablet(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_TABLETOFDESTINY in player_item_types:
            return self.in_progress(self.carry_ushabti_to_63)

        if game_state.world > 4:
            return self.failed()

        return self.in_progress(self.collect_tablet)

    def carry_ushabti_to_63(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen != (6, 2, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.carry_ushabti_to_63)

        if (
            EntityType.ITEM_USHABTI in player_item_types
            or self.some_companion_has_item(game_state, EntityType.ITEM_USHABTI)
        ):
            return self.in_progress(self.win_via_hundun_or_co)

        return self.failed()

    def win_via_hundun_or_co(self, game_state: State, _: Set[EntityType]):
        if game_state.win_state is WinState.TIAMAT:
            return self.failed()

        return self.in_progress(self.win_via_hundun_or_co)


class AbzuChain(CommonSunkenChain):
    world41_theme = Theme.TIDE_POOL
    world44_theme = Theme.ABZU

    @property
    def world4_item_step(self):
        return self.collect_excalibur

    def collect_excalibur(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EXCALIBUR in player_item_types:
            return self.in_progress(self.visit_world44_theme)

        world_level = (game_state.world, game_state.level)
        if world_level > (4, 2):
            return self.failed()

        return self.in_progress(self.collect_excalibur)


class DuatChain(CommonSunkenChain):
    world41_theme = Theme.TEMPLE
    world44_theme = Theme.DUAT

    @property
    def world4_item_step(self):
        return self.carry_scepter_to_42

    def carry_scepter_to_42(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        # The ankh is required to reach Duat
        if EntityType.ITEM_POWERUP_ANKH not in player_item_types:
            return self.failed()

        # Scepter must be carried into 4, 2
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen != (4, 1, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.carry_scepter_to_42)

        if (
            EntityType.ITEM_SCEPTER in player_item_types
            or self.some_companion_has_item(game_state, EntityType.ITEM_SCEPTER)
        ):
            return self.in_progress(self.visit_city_of_gold)

        return self.failed()

    def visit_city_of_gold(self, game_state: State, player_item_types: Set[EntityType]):
        # The ankh is required to reach Duat
        if EntityType.ITEM_POWERUP_ANKH not in player_item_types:
            return self.failed()

        if game_state.theme is Theme.CITY_OF_GOLD:
            return self.in_progress(self.keep_ankh)

        if (game_state.world, game_state.level) > (4, 2):
            return self.failed()

        return self.in_progress(self.visit_city_of_gold)

    def keep_ankh(self, game_state: State, player_item_types: Set[EntityType]):
        # We won't have the Ankh on our way to Duat
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen == (4, 3, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.visit_world44_theme)

        # The player is destroyed when sacrificed
        if game_state.items.players[0] is None:
            return self.in_progress(self.keep_ankh)

        if EntityType.ITEM_POWERUP_ANKH not in player_item_types:
            return self.failed()

        return self.in_progress(self.keep_ankh)


class CosmicOceanChain(ChainMixin):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls.__name__, cls().collect_bow)

    def collect_bow(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_HOUYIBOW in player_item_types:
            return self.in_progress(self.carry_bow_to_hundun)

        if game_state.world > 2:
            return self.failed()

        return self.unstarted()

    def carry_bow_to_hundun(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        if game_state.win_state is not WinState.NO_WIN:
            return self.failed()

        world_level = (game_state.world, game_state.level)
        if world_level > (7, 3):
            return self.in_progress(self.win_via_co)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.carry_bow_to_hundun)

        if (
            EntityType.ITEM_HOUYIBOW in player_item_types
        ) or self.some_companion_has_item(game_state, EntityType.ITEM_HOUYIBOW):
            return self.in_progress(self.carry_bow_to_hundun)

        if world_level < (7, 1) and (
            EntityType.ITEM_HOUYIBOW in game_state.waddler_storage
        ):
            return self.in_progress(self.carry_bow_to_hundun)

        return self.failed()

    def win_via_co(self, game_state: State, _: Set[EntityType]):
        if game_state.win_state in (WinState.NO_WIN, WinState.COSMIC_OCEAN):
            return self.in_progress(self.win_via_co)

        return self.failed()


class EggplantChain(ChainMixin):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls.__name__, cls().collect_eggplant)

    def collect_eggplant(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EGGPLANT in player_item_types:
            return self.in_progress(self.carry_eggplant_to_51)

        # It's possible to collect the child without the eggplant
        if game_state.world == 5 and self.some_companion_is(
            game_state, EntityType.CHAR_EGGPLANT_CHILD
        ):
            return self.in_progress(self.guide_eggplant_child_to_71)

        # It's possible a companion collected the eggplant
        if (
            game_state.screen is Screen.LEVEL_TRANSITION
            and self.some_companion_has_item(game_state, EntityType.ITEM_EGGPLANT)
        ):
            return self.in_progress(self.carry_eggplant_to_51)

        if game_state.world > 5:
            return self.failed()

        return self.unstarted()

    def carry_eggplant_to_51(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        if game_state.world > 4:
            return self.in_progress(self.collect_eggplant_child)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.carry_eggplant_to_51)

        if (
            EntityType.ITEM_EGGPLANT in player_item_types
            or EntityType.ITEM_EGGPLANT in game_state.waddler_storage
            or self.some_companion_has_item(game_state, EntityType.ITEM_EGGPLANT)
        ):
            return self.in_progress(self.carry_eggplant_to_51)

        # We can get another eggplant
        return self.unstarted()

    def collect_eggplant_child(self, game_state: State, _: Set[EntityType]):
        if self.some_companion_is(game_state, EntityType.CHAR_EGGPLANT_CHILD):
            return self.in_progress(self.guide_eggplant_child_to_71)

        if game_state.world > 5:
            return self.failed()

        return self.in_progress(self.collect_eggplant_child)

    def guide_eggplant_child_to_71(self, game_state: State, _: Set[EntityType]):
        world_level = (game_state.world, game_state.level)
        if world_level > (7, 1):
            return self.in_progress(self.eggplant_world)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.guide_eggplant_child_to_71)

        # We won't have the child during the 7-1 transition
        if world_level == (7, 1):
            return self.in_progress(self.eggplant_world)

        if self.some_companion_is(game_state, EntityType.CHAR_EGGPLANT_CHILD):
            return self.in_progress(self.guide_eggplant_child_to_71)

        return self.failed()

    def eggplant_world(self, game_state: State, _: Set[EntityType]):
        if game_state.theme is Theme.EGGPLANT_WORLD:
            return self.in_progress(self.eggplant_crown)

        if (game_state.world, game_state.level) > (7, 1):
            return self.failed()

        return self.in_progress(self.eggplant_world)

    def eggplant_crown(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_EGGPLANTCROWN in player_item_types:
            return self.in_progress(self.success)

        if (game_state.world, game_state.level) > (7, 2):
            return self.failed()

        return self.in_progress(self.eggplant_crown)

    def success(self, _unused1: State, _unused2: Set[EntityType]):
        # Eggplant can't fail once you have the crown
        return self.in_progress(self.success)
