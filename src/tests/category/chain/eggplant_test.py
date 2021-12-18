import pytest

from modlunky2.category.chain.common import ChainStatus
from modlunky2.category.chain.eggplant import EggplantChain
from modlunky2.category.chain.testing import (
    make_player_with_hh_items,
    make_player_with_hh_type,
)
from modlunky2.mem.entities import EntityType
from modlunky2.mem.state import Items, Screen, State, Theme
from modlunky2.mem.testing import EntityMapBuilder


@pytest.mark.parametrize(
    "world,screen,player_item_set,hh_item_set,expected_status,expected_step_name",
    [
        (
            1,
            Screen.LEVEL,
            set(),
            set(),
            ChainStatus.UNSTARTED,
            None,
        ),
        (
            1,
            Screen.LEVEL,
            {EntityType.ITEM_EGGPLANT},
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        # Don't check companions until transition
        (
            1,
            Screen.LEVEL,
            set(),
            {EntityType.ITEM_EGGPLANT},
            ChainStatus.UNSTARTED,
            None,
        ),
        (
            1,
            Screen.LEVEL_TRANSITION,
            set(),
            {EntityType.ITEM_EGGPLANT},
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        # Past bug started chain just because we were in 5-1
        (
            5,
            Screen.LEVEL,
            set(),
            set(),
            ChainStatus.UNSTARTED,
            None,
        ),
        # Last chance eggplant
        (
            5,
            Screen.LEVEL,
            {EntityType.ITEM_EGGPLANT},
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        (
            6,
            Screen.LEVEL,
            set(),
            set(),
            ChainStatus.FAILED,
            None,
        ),
    ],
)
def test_collect_eggplant_item(
    world, screen, player_item_set, hh_item_set, expected_status, expected_step_name
):
    entity_map = EntityMapBuilder()
    player = make_player_with_hh_items(entity_map, hh_item_set)
    game_state = State(
        world=world,
        screen=screen,
        items=Items(players=(player,)),
        instance_id_to_pointer=entity_map.build(),
    )
    eggy_chain = EggplantChain()
    result = eggy_chain.collect_eggplant(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


# Collect the child without ever having an eggplant
def test_collect_eggplant_skip():
    entity_map = EntityMapBuilder()
    player = make_player_with_hh_type(entity_map, EntityType.CHAR_EGGPLANT_CHILD)
    game_state = State(
        world=5,
        items=Items(players=(player,)),
        instance_id_to_pointer=entity_map.build(),
    )
    player_item_set = set()

    eggy_chain = EggplantChain()
    result = eggy_chain.collect_eggplant(game_state, player_item_set)

    assert result.status == ChainStatus.IN_PROGRESS
    assert result.next_step.__name__ == "guide_eggplant_child_to_71"


@pytest.mark.parametrize(
    "world,screen,player_item_set,hh_item_set,waddler_item_set,expected_status,expected_step_name",
    [
        # OK to not have eggplant within a level
        (
            1,
            Screen.LEVEL,
            set(),  # player
            set(),  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        (
            1,
            Screen.LEVEL_TRANSITION,
            {EntityType.ITEM_EGGPLANT},  # player
            set(),  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        (
            1,
            Screen.LEVEL_TRANSITION,
            set(),  # player
            {EntityType.ITEM_EGGPLANT},  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        (
            3,
            Screen.LEVEL_TRANSITION,
            set(),  # player
            set(),  # hh
            {EntityType.ITEM_EGGPLANT},  # waddler
            ChainStatus.IN_PROGRESS,
            "carry_eggplant_to_51",
        ),
        # Lost eggplant resets this chain
        (
            3,
            Screen.LEVEL_TRANSITION,
            set(),  # player
            set(),  # hh
            set(),  # waddler
            ChainStatus.UNSTARTED,
            None,
        ),
        (
            5,
            Screen.LEVEL,
            set(),  # player
            set(),  # hh
            set(),  # waddler
            ChainStatus.IN_PROGRESS,
            "collect_eggplant_child",
        ),
    ],
)
def test_carry_eggplant_to_51(
    world,
    screen,
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
        screen=screen,
        items=Items(players=(player,)),
        waddler_storage=tuple(waddler_item_set),
        instance_id_to_pointer=entity_map.build(),
    )
    eggy_chain = EggplantChain()
    result = eggy_chain.carry_eggplant_to_51(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,hh_type,expected_status,expected_step_name",
    [
        # No child yet
        (
            5,
            EntityType.CHAR_HIREDHAND,
            ChainStatus.IN_PROGRESS,
            "collect_eggplant_child",
        ),
        (
            5,
            EntityType.CHAR_EGGPLANT_CHILD,
            ChainStatus.IN_PROGRESS,
            "guide_eggplant_child_to_71",
        ),
        # Missed the child
        (
            6,
            EntityType.CHAR_HIREDHAND,
            ChainStatus.FAILED,
            None,
        ),
    ],
)
def test_collect_eggplant_child(world, hh_type, expected_status, expected_step_name):
    entity_map = EntityMapBuilder()
    player = make_player_with_hh_type(entity_map, hh_type)
    game_state = State(
        world=world,
        items=Items(players=(player,)),
        instance_id_to_pointer=entity_map.build(),
    )
    player_item_set = set()

    eggy_chain = EggplantChain()
    result = eggy_chain.collect_eggplant_child(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,screen,hh_type,expected_status,expected_step_name",
    [
        (
            5,
            1,
            Screen.LEVEL,
            EntityType.CHAR_EGGPLANT_CHILD,
            ChainStatus.IN_PROGRESS,
            "guide_eggplant_child_to_71",
        ),
        # Don't check until transition
        (
            6,
            1,
            Screen.LEVEL,
            EntityType.CHAR_HIREDHAND,
            ChainStatus.IN_PROGRESS,
            "guide_eggplant_child_to_71",
        ),
        (
            6,
            1,
            Screen.LEVEL_TRANSITION,
            EntityType.CHAR_HIREDHAND,
            ChainStatus.FAILED,
            None,
        ),
        (
            6,
            1,
            Screen.LEVEL_TRANSITION,
            EntityType.CHAR_EGGPLANT_CHILD,
            ChainStatus.IN_PROGRESS,
            "guide_eggplant_child_to_71",
        ),
        # Might have left child at statue
        (
            7,
            1,
            Screen.LEVEL_TRANSITION,
            EntityType.CHAR_HIREDHAND,
            ChainStatus.IN_PROGRESS,
            "visit_eggplant_world",
        ),
        # Missed statue
        (
            7,
            2,
            Screen.LEVEL,
            EntityType.CHAR_HIREDHAND,
            ChainStatus.IN_PROGRESS,
            "visit_eggplant_world",
        ),
    ],
)
def test_guide_eggplant_child_to_71(
    world, level, screen, hh_type, expected_status, expected_step_name
):
    entity_map = EntityMapBuilder()
    player = make_player_with_hh_type(entity_map, hh_type)
    game_state = State(
        world=world,
        level=level,
        screen=screen,
        items=Items(players=(player,)),
        instance_id_to_pointer=entity_map.build(),
    )
    player_item_set = set()

    eggy_chain = EggplantChain()
    result = eggy_chain.guide_eggplant_child_to_71(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,theme,expected_status,expected_step_name",
    [
        (7, 1, Theme.SUNKEN_CITY, ChainStatus.IN_PROGRESS, "visit_eggplant_world"),
        (7, 2, Theme.SUNKEN_CITY, ChainStatus.FAILED, None),
        (7, 2, Theme.EGGPLANT_WORLD, ChainStatus.IN_PROGRESS, "collect_eggplant_crown"),
    ],
)
def test_visit_eggplant_world(world, level, theme, expected_status, expected_step_name):
    game_state = State(
        world=world,
        level=level,
        theme=theme,
    )
    player_item_set = set()

    eggy_chain = EggplantChain()
    result = eggy_chain.visit_eggplant_world(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,player_item_set,expected_status,expected_step_name",
    [
        (7, 2, set(), ChainStatus.IN_PROGRESS, "collect_eggplant_crown"),
        (
            7,
            2,
            {EntityType.ITEM_POWERUP_EGGPLANTCROWN},
            ChainStatus.IN_PROGRESS,
            "success",
        ),
        (7, 3, set(), ChainStatus.FAILED, None),
    ],
)
def test_collect_eggplant_crown(
    world, level, player_item_set, expected_status, expected_step_name
):
    game_state = State(
        world=world,
        level=level,
    )

    eggy_chain = EggplantChain()
    result = eggy_chain.collect_eggplant_crown(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name
