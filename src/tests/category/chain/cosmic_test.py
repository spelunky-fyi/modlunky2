import pytest

from modlunky2.category.chain.common import ChainStatus
from modlunky2.category.chain.cosmic import CosmicOceanChain
from modlunky2.category.chain.testing import make_player_with_hh_items
from modlunky2.mem.entities import EntityType
from modlunky2.mem.state import Items, Screen, State, WinState
from modlunky2.mem.testing import EntityMapBuilder


@pytest.mark.parametrize(
    "world,player_item_set,expected_status,expected_step_name",
    [
        (1, set(), ChainStatus.UNSTARTED, None),
        (2, set(), ChainStatus.UNSTARTED, None),
        (2, {EntityType.ITEM_HOUYIBOW}, ChainStatus.IN_PROGRESS, "carry_bow_to_hundun"),
        (3, set(), ChainStatus.FAILED, None),
    ],
)
def test_collect_bow(world, player_item_set, expected_status, expected_step_name):
    game_state = State(world=world)

    co_chain = CosmicOceanChain()
    result = co_chain.collect_bow(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,screen,win_state,player_item_set,hh_item_set,waddler_item_set,expected_status,expected_step_name",
    [
        (
            2,
            3,
            Screen.LEVEL_TRANSITION,
            WinState.NO_WIN,
            {EntityType.ITEM_HOUYIBOW},
            set(),  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_bow_to_hundun",
        ),
        (
            2,
            3,
            Screen.LEVEL_TRANSITION,
            WinState.NO_WIN,
            set(),  # player
            set(),  # hh
            set(),  # waddler
            ChainStatus.FAILED,
            None,
        ),
        (
            2,
            3,
            Screen.LEVEL_TRANSITION,
            WinState.NO_WIN,
            set(),  # playere
            {EntityType.ITEM_HOUYIBOW},  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_bow_to_hundun",
        ),
        (
            3,
            1,
            Screen.LEVEL_TRANSITION,
            WinState.NO_WIN,
            set(),  # player
            set(),  # hh
            {EntityType.ITEM_HOUYIBOW},  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_bow_to_hundun",
        ),
        # Missed Waddler
        (
            7,
            2,
            Screen.LEVEL_TRANSITION,
            WinState.NO_WIN,
            set(),  # player
            set(),  # hh
            {EntityType.ITEM_HOUYIBOW},  # waddler
            ChainStatus.FAILED,
            None,
        ),
        (
            7,
            3,
            Screen.LEVEL_TRANSITION,
            WinState.NO_WIN,
            {EntityType.ITEM_HOUYIBOW},
            set(),  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "win_via_co",
        ),
        (
            6,
            4,
            Screen.ENDING,
            WinState.TIAMAT,
            {EntityType.ITEM_HOUYIBOW},
            set(),  # hh
            set(),  # waddler
            ChainStatus.FAILED,
            None,
        ),
        (
            7,
            4,
            Screen.ENDING,
            WinState.HUNDUN,
            {EntityType.ITEM_HOUYIBOW},
            set(),  # hh
            set(),  # waddler
            ChainStatus.FAILED,
            None,
        ),
        # Score screen is in base camp
        (
            1,
            1,
            Screen.SCORES,
            WinState.TIAMAT,
            {EntityType.ITEM_HOUYIBOW},
            set(),  # hh
            set(),  # waddler
            ChainStatus.FAILED,
            None,
        ),
    ],
)
def carry_bow_to_hundun(
    world,
    level,
    screen,
    win_state,
    player_item_set,
    hh_item_set,
    waddler_item_set,
    expected_status,
    expected_step_name,
):
    entity_map = EntityMapBuilder()
    player = make_player_with_hh_items(entity_map, hh_item_set)
    game_state = State(
        world=world,
        level=level,
        screen=screen,
        win_state=win_state,
        waddler_storage=tuple(waddler_item_set),
        items=Items(players=(player,)),
        instance_id_to_pointer=entity_map.build(),
    )

    co_chain = CosmicOceanChain()
    result = co_chain.carry_bow_to_hundun(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "win_state,expected_status,expected_step_name",
    [
        (WinState.NO_WIN, ChainStatus.IN_PROGRESS, "win_via_co"),
        (WinState.TIAMAT, ChainStatus.FAILED, None),
        (WinState.HUNDUN, ChainStatus.FAILED, None),
        (WinState.COSMIC_OCEAN, ChainStatus.IN_PROGRESS, "win_via_co"),
    ],
)
def test_win_via_co(win_state, expected_status, expected_step_name):
    game_state = State(win_state=win_state)
    player_item_set = set()

    co_chain = CosmicOceanChain()
    result = co_chain.win_via_co(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name
