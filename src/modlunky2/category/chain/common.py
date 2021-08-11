from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Any, Callable, Generator, Optional, Set

from modlunky2.mem.entities import Entity, EntityType, Player
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.state import State

logger = logging.getLogger("modlunky2")

# Status of the quest chain.
# The properties are for convenience in 'if' condition
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
        self._name = name
        self._initial_step = initial_step
        self._last_result = ChainStepResult(ChainStatus.UNSTARTED)

    def evaluate(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStatus:
        if self._last_result.status.failed:
            return ChainStatus.FAILED

        if self._last_result.status.unstarted:
            step = self._initial_step
        else:
            step = self._last_result.next_step

        result = step(game_state, player_item_types)

        if self._last_result != result:
            logger.debug("chain %s: %s -> %s", self._name, self._last_result, result)

        self._last_result = result
        return result.status

    # The status of the last call to evaluate().
    # If it hasn't been calleed yet, this will be UNSTARTED
    @property
    def last_status(self) -> ChainStatus:
        return self._last_result.status


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
