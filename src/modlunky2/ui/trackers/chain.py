from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Any, Callable, Optional, Set

from modlunky2.mem.entities import EntityType
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


class CommonChain(ABC):
    @property
    @abstractmethod
    def world4_step(self):
        pass

    def eye_or_headwear(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStepResult:
        if (
            EntityType.ITEM_POWERUP_HEDJET in player_item_types
            or EntityType.ITEM_POWERUP_CROWN in player_item_types
        ):
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.ankh)

        if EntityType.ITEM_POWERUP_UDJATEYE in player_item_types:
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.eye_or_headwear)

        if game_state.world > 2:
            return ChainStepResult(ChainStatus.FAILED)

        return ChainStepResult(ChainStatus.UNSTARTED)

    def ankh(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_ANKH in player_item_types:
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.world4_step)

        if game_state.world > 3:
            return ChainStepResult(ChainStatus.FAILED)

        return ChainStepResult(ChainStatus.IN_PROGRESS, self.ankh)

    def tablet_of_destiny(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_TABLETOFDESTINY in player_item_types:
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.ushabti)

        if game_state.world > 5:
            return ChainStepResult(ChainStatus.FAILED)

        return ChainStepResult(ChainStatus.IN_PROGRESS, self.tablet_of_destiny)

    def ushabti(self, game_state: State, player_item_types: Set[EntityType]):
        if (game_state.world, game_state.level) < (
            6,
            2,
        ) or game_state.screen is not Screen.LEVEL_TRANSITION:
            return ChainStepResult(ChainStatus.IN_PROGRESS)

        if EntityType.ITEM_USHABTI in player_item_types:
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.non_tiamat_win)

        return ChainStepResult(ChainStatus.FAILED)

    def non_tiamat_win(self, game_state: State, _: Set[EntityType]):
        if game_state is WinState.TIAMAT:
            return ChainStepResult(ChainStatus.FAILED)

        return ChainStepResult(ChainStatus.IN_PROGRESS, self.non_tiamat_win)


class AbzuChain(CommonChain):
    @property
    def world4_step(self):
        return self.excalibur

    def excalibur(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EXCALIBUR in player_item_types:
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.abzu)

        world_level = (game_state.world, game_state.level)
        if world_level > (4, 2):
            return ChainStepResult(ChainStatus.FAILED)

    def abzu(self, game_state: State, _: Set[EntityType]):
        if game_state.world > 4:
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.tablet_of_destiny)

        if (game_state.world, game_state.level) != (4, 4):
            return ChainStepResult(ChainStatus.IN_PROGRESS, self.abzu)

        if game_state.theme != Theme.ABZU:
            return ChainStepResult(ChainStatus.FAILED)
