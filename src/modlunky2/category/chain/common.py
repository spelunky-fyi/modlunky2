from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Callable, Generator, Optional, Set

from modlunky2.mem.entities import Entity, EntityType, Player
from modlunky2.mem.memrauder.model import PolyPointer
from modlunky2.mem.state import State

logger = logging.getLogger("modlunky2")

# Status of the quest chain.
# The properties are for convenience in 'if' condition
class ChainStatus(IntEnum):
    # The chain is waiting for the player to perform its first step
    UNSTARTED = 0
    # The chain is at some step beyond its first
    IN_PROGRESS = 1
    # The chain was failed. Progress is impossible
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


# A function which evalutes a single 'step' in a chain, based on current game state.
# See ChainStepper for more details
ChainStepEvaluator = Callable[[State, Set[EntityType]], "ChainStepResult"]


@dataclass(frozen=True)
class ChainStepResult:
    status: ChainStatus
    # next_step should only be set for IN_PROGRESS
    next_step: Optional[ChainStepEvaluator] = None

    def __post_init__(self):
        if not self.status.in_progress and self.next_step is not None:
            raise ValueError(
                f"status {self.status.name} requires next_step to be None, got {self.next_step}"
            )

        if not self.status.in_progress:
            return

        if self.next_step is None:
            raise ValueError(f"status {self.status.name} requires next_step to be set")
        if not callable(self.next_step):
            raise ValueError(
                f"status {self.status.name} requires next_step to be callable"
            )

    def __str__(self) -> str:
        if self.next_step is None:
            return f"{self.status.name}"

        step_name = self.next_step.__name__
        return f"{self.status.name}, {step_name}"


# A simple finite state machine for quest chains.
# Generally, transitions may occur on each call to evaluate(),
# which returns the new status.
#
# The first call to evaluate will use the initial_step.
# Later calls will depend on the previous result:
# * If it was UNSTARTED, the initial_step will be used
# * If it was IN_PROGRESS, the previously-returned next_step will be used
# * If it was FAILED, no step will be evaluated and the result is FAILED
#
# Notably:
# * Chains can be reset by returning UNSTARTED status
# * Once a chain has failed, it will remain in that state indefinitely
# * It's an error to return IN_PROGRESS status with the initial_step
# * Chains are allowed to branch, loop, etc.
class ChainStepper:
    def __init__(self, name: str, initial_step: ChainStepEvaluator):
        self._name = name
        self._initial_step = initial_step
        self._last_result = ChainStepResult(ChainStatus.UNSTARTED)

        if not callable(initial_step):
            raise ValueError(f"initial_step ({initial_step}) isn't callable")

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

        if result.status.in_progress and result.next_step == self._initial_step:
            raise ValueError(
                f"step {step.__name__} returned IN_PROGRESS with the initial step ({self._initial_step.__name__})"
            )

        if self._last_result != result:
            logger.debug("chain %s: %s -> %s", self._name, self._last_result, result)

        self._last_result = result
        return result.status

    # The status of the last call to evaluate().
    # If it hasn't been called yet, this will be UNSTARTED
    @property
    def last_status(self) -> ChainStatus:
        return self._last_result.status


# Convenience methods for chain steps
class ChainMixin:
    @staticmethod
    def unstarted():
        return ChainStepResult(ChainStatus.UNSTARTED)

    @staticmethod
    def in_progress(next_step: ChainStepEvaluator):
        return ChainStepResult(ChainStatus.IN_PROGRESS, next_step)

    @staticmethod
    def failed():
        return ChainStepResult(ChainStatus.FAILED)

    # TODO move companion stuff somewhere more sensible

    # Generator function for companions linked to the player.
    # Yields a PolyPointer to support downcasting, and guarantees the pointer value is present
    @staticmethod
    def companions(game_state: State) -> Generator[PolyPointer[Entity], None, None]:
        cur_hand_uid = game_state.items.players[0].linked_companion_child

        while cur_hand_uid != 0:
            cur_hand = game_state.instance_id_to_pointer.get(cur_hand_uid)
            if cur_hand is None:
                return

            yield cur_hand

            cur_hand = cur_hand.as_poly_type(Player)
            if cur_hand is None:
                return
            cur_hand_uid = cur_hand.value.linked_companion_child

    # Returns true if a companion has an item of the correct type.
    # Notably, this doesn't examine holding_uid (e.g. the arrow that's loaded in a bow)
    @staticmethod
    def some_companion_has_item(game_state: State, item_type: EntityType) -> bool:
        for companion in ChainMixin.companions(game_state):
            companion_items = companion.value.items
            if companion_items is None:
                continue

            for item_uid in companion_items:
                item = game_state.instance_id_to_pointer.get(item_uid)
                if item is None:
                    continue
                if item.value.type.id is item_type:
                    return True

        return False

    @staticmethod
    def some_companion_is(game_state: State, companion_type: EntityType) -> bool:
        for companion in ChainMixin.companions(game_state):
            if companion.value.type is None:
                continue

            if companion.value.type.id is companion_type:
                return True

        return False
