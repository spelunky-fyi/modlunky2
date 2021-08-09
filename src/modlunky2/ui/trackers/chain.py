from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Any, Callable, Generator, Optional, Set

from modlunky2.mem.entities import Entity, EntityType, Player
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.state import Screen, State, Theme, WinState

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


ChainStepEvaluator = Callable[[Any, State, Set[EntityType]], "ChainStepResult"]


@dataclass(frozen=True)
class ChainStepResult:
    status: ChainStatus
    # next_step should only be set for IN_PROGRESS
    next_step: Optional[ChainStepEvaluator] = None

    def __post_init__(self):
        if self.status.in_progress and self.next_step is None:
            raise ValueError(f"status {self.status.name} requires next_step to be set")

        if not self.status.in_progress and self.next_step is not None:
            raise ValueError(
                f"status {self.status.name} requires next_step to None, got {self.next_step}"
            )

    def __str__(self) -> str:
        if self.next_step is None:
            return f"{self.status.name}"
        step_name = self.next_step.__name__
        class_name = type(self.next_step.__self__).__name__
        return f"{self.status.name}, {class_name}.{step_name}"


class ChainStepper:
    def __init__(self, initial_step: ChainStepEvaluator):
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

        result: ChainStepResult = step(game_state, player_item_types)

        if self.last_result != result:
            logger.info("chain %s -> %s", self.last_result, result)

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
            if companion.value.type.id is companion_type:
                return True

        return False


class CommonSunkenChain(ChainMixin, ABC):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls().eye_or_headwear)

    @property
    @abstractmethod
    def world4_1_theme(self) -> Theme:
        pass

    @property
    @abstractmethod
    def world4_4_theme(self) -> Theme:
        pass

    @property
    @abstractmethod
    def world4_step(self) -> ChainStepEvaluator:
        pass

    def eye_or_headwear(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStepResult:
        if (
            EntityType.ITEM_POWERUP_HEDJET in player_item_types
            or EntityType.ITEM_POWERUP_CROWN in player_item_types
        ):
            return self.in_progress(self.ankh)

        if EntityType.ITEM_POWERUP_UDJATEYE in player_item_types:
            return self.in_progress(self.eye_or_headwear)

        if game_state.world > 2:
            return self.failed()

        return self.unstarted()

    def ankh(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_ANKH in player_item_types:
            return self.in_progress(self.world4_1_theme_check)

        if game_state.world > 3:
            return self.failed()

        return self.in_progress(self.ankh)

    def world4_1_theme_check(self, game_state: State, _: Set[EntityType]):
        if game_state.theme == self.world4_1_theme:
            return self.in_progress(self.world4_step)

        if game_state.world > 3:
            return self.failed()

        return self.in_progress(self.world4_1_theme_check)

    def world4_4_theme_check(self, game_state: State, _: Set[EntityType]):
        if game_state.theme == self.world4_4_theme:
            return self.in_progress(self.tablet_of_destiny)

        if (game_state.world, game_state.level) > (4, 3):
            return self.failed()

        return self.in_progress(self.world4_4_theme_check)

    def tablet_of_destiny(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_TABLETOFDESTINY in player_item_types:
            return self.in_progress(self.ushabti)

        if game_state.world > 4:
            return self.failed()

        return self.in_progress(self.tablet_of_destiny)

    def ushabti(self, game_state: State, player_item_types: Set[EntityType]):
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen != (6, 2, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.ushabti)

        if (
            EntityType.ITEM_USHABTI in player_item_types
            or self.some_companion_has_item(game_state, EntityType.ITEM_USHABTI)
        ):
            return self.in_progress(self.non_tiamat_win)

        return self.failed()

    def non_tiamat_win(self, game_state: State, _: Set[EntityType]):
        if game_state is WinState.TIAMAT:
            return self.failed()

        return self.in_progress(self.non_tiamat_win)


class AbzuChain(CommonSunkenChain):
    world4_1_theme = Theme.TIDE_POOL
    world4_4_theme = Theme.ABZU

    @property
    def world4_step(self):
        return self.excalibur

    def excalibur(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EXCALIBUR in player_item_types:
            return self.in_progress(self.world4_4_theme_check)

        world_level = (game_state.world, game_state.level)
        if world_level > (4, 2):
            return self.failed()

        return self.in_progress(self.excalibur)


class DuatChain(CommonSunkenChain):
    world4_1_theme = Theme.TEMPLE
    world4_4_theme = Theme.DUAT

    @property
    def world4_step(self):
        return self.scepter

    def scepter(self, game_state: State, player_item_types: Set[EntityType]):
        # Scepter must be carried into 4, 2
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen != (4, 1, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.scepter)

        if (
            EntityType.ITEM_SCEPTER in player_item_types
            or self.some_companion_has_item(game_state, EntityType.ITEM_SCEPTER)
        ):
            return self.in_progress(self.city_of_gold)

        return self.failed()

    def city_of_gold(self, game_state: State, _: Set[EntityType]):
        if game_state.theme is Theme.CITY_OF_GOLD:
            return self.in_progress(self.world4_4_theme_check)

        if (game_state.world, game_state.level) > (4, 3):
            return self.failed()

        return self.in_progress(self.city_of_gold)


class CosmicOceanChain(ChainMixin):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls().pick_up_bow)

    def pick_up_bow(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_HOUYIBOW in player_item_types:
            return self.in_progress(self.still_have_bow)

        if game_state.world > 2:
            return self.failed()

        return self.unstarted()

    def still_have_bow(self, game_state: State, player_item_types: Set[EntityType]):
        if game_state.win_state is not WinState.NO_WIN:
            return self.failed()

        world_level = (game_state.world, game_state.level)
        if world_level > (7, 3):
            return self.in_progress(self.co_win)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.still_have_bow)

        if (
            EntityType.ITEM_HOUYIBOW in player_item_types
        ) or self.some_companion_has_item(game_state, EntityType.ITEM_HOUYIBOW):
            return self.in_progress(self.still_have_bow)

        if world_level < (7, 1) and (
            EntityType.ITEM_HOUYIBOW in game_state.waddler_storage
        ):
            return self.in_progress(self.still_have_bow)

        return self.failed()

    def co_win(self, game_state: State, _: Set[EntityType]):
        if game_state.win_state in (WinState.NO_WIN, WinState.COSMIC_OCEAN):
            return self.in_progress(self.co_win)

        return self.failed()


class EggplantChain(ChainMixin):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls().pick_up_eggplant)

    def pick_up_eggplant(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EGGPLANT in player_item_types:
            return self.in_progress(self.still_have_eggplant)

        if game_state.world > 4:
            return self.in_progress(self.collect_eggplant_child)

        # We can get another eggplant
        return self.unstarted()

    def still_have_eggplant(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        if game_state.world > 4:
            return self.in_progress(self.collect_eggplant_child)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.still_have_eggplant)

        if (
            EntityType.ITEM_EGGPLANT in player_item_types
            or EntityType.ITEM_EGGPLANT in game_state.waddler_storage
            or self.some_companion_has_item(game_state, EntityType.ITEM_EGGPLANT)
        ):
            return self.in_progress(self.still_have_eggplant)

        # We can get another eggplant
        return self.unstarted()

    def collect_eggplant_child(self, game_state: State, _: Set[EntityType]):
        if self.some_companion_is(game_state, EntityType.CHAR_EGGPLANT_CHILD):
            return self.in_progress(self.still_have_eggplant_child)

        if game_state.world > 5:
            return self.failed()

        return self.in_progress(self.collect_eggplant_child)

    def still_have_eggplant_child(self, game_state: State, _: Set[EntityType]):
        world_level = (game_state.world, game_state.level)
        if world_level > (7, 1):
            return self.in_progress(self.eggplant_world)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.still_have_eggplant_child)

        # We won't have the child during the 7-1 transition
        if world_level == (7, 1):
            return self.in_progress(self.eggplant_world)

        if self.some_companion_is(game_state, EntityType.CHAR_EGGPLANT_CHILD):
            return self.in_progress(self.still_have_eggplant_child)

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
