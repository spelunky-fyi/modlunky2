from typing import Iterable, Set
import pytest
from modlunky2.mem.entities import EntityDBEntry, EntityType, Player

from modlunky2.mem.state import State
from modlunky2.category.chain.common import (
    ChainMixin,
    ChainStatus,
    ChainStepResult,
    ChainStepper,
)
from modlunky2.mem.testing import EntityMapBuilder


def make_player_with_hh_items(
    entity_map: EntityMapBuilder, hh_item_types: Iterable[EntityType]
):
    hh_item_ids = entity_map.add_trivial_entities(hh_item_types)
    hh_id = entity_map.add_entity(Player(items=hh_item_ids))

    return Player(linked_companion_child=hh_id)


def make_player_with_hh_type(entity_map: EntityMapBuilder, hh_type: EntityType):
    hh_entity_db = EntityDBEntry(id=hh_type)
    hh_entity = Player(type=hh_entity_db)
    hh_id = entity_map.add_entity(hh_entity)

    return Player(linked_companion_child=hh_id)


def fake_chain_step():
    pass


@pytest.mark.parametrize(
    "status,next_step,msg_pattern",
    [
        (ChainStatus.UNSTARTED, fake_chain_step, "next_step to be None"),
        (ChainStatus.IN_PROGRESS, None, "next_step to be set"),
        (ChainStatus.IN_PROGRESS, dict(), "next_step to be callable"),
        (ChainStatus.FAILED, fake_chain_step, "next_step to be None"),
    ],
)
def test_chain_step_result_validation(status, next_step, msg_pattern):
    with pytest.raises(ValueError, match=msg_pattern):
        ChainStepResult(status, next_step)


class TestChain(ChainMixin):
    def still_unstarted(self, _unused1: State, _unused2: Set[EntityType]):
        return self.unstarted()

    def total_fail(self, _unused1: State, _unused2: Set[EntityType]):
        return self.failed()

    def step1_to_fail(self, _unused1: State, _unused2: Set[EntityType]):
        return self.in_progress(self.step2_to_fail)

    def step2_to_fail(self, _unused1: State, _unused2: Set[EntityType]):
        return self.failed()

    def step1_to_unstarted(self, _unused1: State, _unused2: Set[EntityType]):
        return self.in_progress(self.step2_to_unstarted)

    def step2_to_unstarted(self, _unused1: State, _unused2: Set[EntityType]):
        return self.unstarted()


@pytest.mark.parametrize(
    "initial_step_name,expected_status",
    [
        ("still_unstarted", ChainStatus.UNSTARTED),
        ("total_fail", ChainStatus.FAILED),
    ],
)
def test_chain_stepper_single(initial_step_name, expected_status):
    test_chain = TestChain()
    initial_step = getattr(test_chain, initial_step_name)
    stepper = ChainStepper("test", initial_step)

    status = stepper.evaluate(State(), set())
    assert status == expected_status


def test_chain_stepper_multi_progress():
    test_chain = TestChain()
    stepper = ChainStepper("test", test_chain.step1_to_fail)

    status = stepper.evaluate(State(), set())
    assert status == ChainStatus.IN_PROGRESS

    status = stepper.evaluate(State(), set())
    assert status == ChainStatus.FAILED

    # Should still be failed
    status = stepper.evaluate(State(), set())
    assert status == ChainStatus.FAILED


def test_chain_stepper_multi_unstarted():
    test_chain = TestChain()
    stepper = ChainStepper("test", test_chain.step1_to_unstarted)

    status = stepper.evaluate(State(), set())
    assert status == ChainStatus.IN_PROGRESS

    status = stepper.evaluate(State(), set())
    assert status == ChainStatus.UNSTARTED

    # Should restart
    status = stepper.evaluate(State(), set())
    assert status == ChainStatus.IN_PROGRESS
