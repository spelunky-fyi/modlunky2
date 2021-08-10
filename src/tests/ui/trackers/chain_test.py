from typing import Iterable, Set
import pytest
from modlunky2.mem.entities import EntityType, Player

from modlunky2.mem.state import Items, Screen, State, Theme, WinState
from modlunky2.ui.trackers.chain import (
    ChainStatus,
    ChainStepEvaluator,
    CommonSunkenChain,
)
from modlunky2.mem.testing import EntityMapBuilder


class FakeChain(CommonSunkenChain):
    world4_1_theme = Theme.TIDE_POOL
    world4_4_theme = Theme.ABZU

    @property
    def world4_step(self) -> ChainStepEvaluator:
        return self.fake_world4_step

    def fake_world4_step(self, _unused1: State, _unused2: Set[EntityType]):
        return self.in_progress(self.check_world4_4_theme)


def make_player_with_hh_items(
    entity_map: EntityMapBuilder, hh_item_types: Iterable[EntityType]
):
    hh_item_ids = entity_map.add_trivial_entities(hh_item_types)
    hh_id = entity_map.add_entity(Player(items=hh_item_ids))

    return Player(linked_companion_child=hh_id)


@pytest.mark.parametrize(
    "world,item_set,expected_status,expected_step_name",
    [
        (1, set(), ChainStatus.UNSTARTED, None),
        (
            1,
            {EntityType.ITEM_POWERUP_UDJATEYE},
            ChainStatus.IN_PROGRESS,
            "eye_or_headwear",
        ),
        (2, set(), ChainStatus.UNSTARTED, None),
        (2, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.IN_PROGRESS, "ankh"),
        (
            2,
            {EntityType.ITEM_POWERUP_UDJATEYE, EntityType.ITEM_POWERUP_HEDJET},
            ChainStatus.IN_PROGRESS,
            "ankh",
        ),
        (3, set(), ChainStatus.FAILED, None),
        (3, {EntityType.ITEM_POWERUP_HEDJET}, ChainStatus.IN_PROGRESS, "ankh"),
    ],
)
def test_common_eye_or_headwear(world, item_set, expected_status, expected_step_name):
    fake_chain = FakeChain()
    game_state = State(world=world)
    result = fake_chain.eye_or_headwear(game_state, item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,item_set,expected_status,expected_step_name",
    [
        (3, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.IN_PROGRESS, "ankh"),
        (
            3,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "check_world4_1_theme",
        ),
        (4, set(), ChainStatus.FAILED, None),
        (4, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.FAILED, None),
    ],
)
def test_ankh(world, item_set, expected_status, expected_step_name):
    fake_chain = FakeChain()
    game_state = State(world=world)
    result = fake_chain.ankh(game_state, item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,theme,expected_status,expected_step_name",
    [
        (3, Theme.OLMEC, ChainStatus.IN_PROGRESS, "check_world4_1_theme"),
        (4, Theme.TEMPLE, ChainStatus.FAILED, None),
        (4, Theme.TIDE_POOL, ChainStatus.IN_PROGRESS, "fake_world4_step"),
    ],
)
def test_check_world4_1_theme(world, theme, expected_status, expected_step_name):
    fake_chain = FakeChain()
    game_state = State(world=world, theme=theme)
    result = fake_chain.check_world4_1_theme(game_state, set())

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,theme,expected_status,expected_step_name",
    [
        (4, 2, Theme.TIDE_POOL, ChainStatus.IN_PROGRESS, "check_world4_4_theme"),
        (4, 3, Theme.TIDE_POOL, ChainStatus.IN_PROGRESS, "check_world4_4_theme"),
        (4, 4, Theme.TIDE_POOL, ChainStatus.FAILED, None),
        (4, 4, Theme.ABZU, ChainStatus.IN_PROGRESS, "tablet_of_destiny"),
    ],
)
def test_world4_4_theme_check(world, level, theme, expected_status, expected_step_name):
    fake_chain = FakeChain()
    game_state = State(world=world, level=level, theme=theme)
    result = fake_chain.check_world4_4_theme(game_state, set())

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,item_set,expected_status,expected_step_name",
    [
        (
            4,
            {EntityType.ITEM_POWERUP_CROWN},
            ChainStatus.IN_PROGRESS,
            "tablet_of_destiny",
        ),
        (
            4,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            ChainStatus.IN_PROGRESS,
            "ushabti",
        ),
        (5, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.FAILED, None),
    ],
)
def test_tablet_of_destiny(world, item_set, expected_status, expected_step_name):
    fake_chain = FakeChain()
    game_state = State(world=world)
    result = fake_chain.tablet_of_destiny(game_state, item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,screen,player_item_set,hh_item_set,expected_status,expected_step_name",
    [
        (
            4,
            4,
            Screen.LEVEL,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            set(),
            ChainStatus.IN_PROGRESS,
            "ushabti",
        ),
        (
            6,
            1,
            Screen.LEVEL_TRANSITION,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            set(),
            ChainStatus.IN_PROGRESS,
            "ushabti",
        ),
        (
            6,
            2,
            Screen.LEVEL,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            set(),
            ChainStatus.IN_PROGRESS,
            "ushabti",
        ),
        (
            6,
            2,
            Screen.LEVEL_TRANSITION,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            set(),
            ChainStatus.FAILED,
            None,
        ),
        (
            6,
            2,
            Screen.LEVEL_TRANSITION,
            {
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_TABLETOFDESTINY,
                EntityType.ITEM_USHABTI,
            },
            set(),
            ChainStatus.IN_PROGRESS,
            "non_tiamat_win",
        ),
        (
            6,
            2,
            Screen.LEVEL_TRANSITION,
            {
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_TABLETOFDESTINY,
            },
            {EntityType.ITEM_USHABTI},
            ChainStatus.IN_PROGRESS,
            "non_tiamat_win",
        ),
    ],
)
def test_ushabti(
    world,
    level,
    screen,
    player_item_set,
    hh_item_set,
    expected_status,
    expected_step_name,
):
    entity_map = EntityMapBuilder()
    player = make_player_with_hh_items(entity_map, hh_item_set)
    game_state = State(
        world=world,
        level=level,
        screen=screen,
        items=Items(players=(player,)),
        instance_id_to_pointer=entity_map.build(),
    )

    fake_chain = FakeChain()
    result = fake_chain.ushabti(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "win_state,expected_status,expected_step_name",
    [
        (WinState.NO_WIN, ChainStatus.IN_PROGRESS, "non_tiamat_win"),
        (WinState.TIAMAT, ChainStatus.FAILED, None),
        (WinState.HUNDUN, ChainStatus.IN_PROGRESS, "non_tiamat_win"),
        (WinState.COSMIC_OCEAN, ChainStatus.IN_PROGRESS, "non_tiamat_win"),
    ],
)
def test_non_tiamat_win(win_state, expected_status, expected_step_name):
    game_state = State(win_state=win_state)
    fake_chain = FakeChain()
    result = fake_chain.non_tiamat_win(game_state, set())

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name
