from typing import Iterable, Set
import pytest
from modlunky2.mem.entities import EntityType, Player

from modlunky2.mem.state import Items, Screen, State, Theme, WinState
from modlunky2.ui.trackers.chain import (
    AbzuChain,
    ChainMixin,
    ChainStatus,
    ChainStepEvaluator,
    ChainStepResult,
    ChainStepper,
    CommonSunkenChain,
    CosmicOceanChain,
    DuatChain,
)
from modlunky2.mem.testing import EntityMapBuilder


def make_player_with_hh_items(
    entity_map: EntityMapBuilder, hh_item_types: Iterable[EntityType]
):
    hh_item_ids = entity_map.add_trivial_entities(hh_item_types)
    hh_id = entity_map.add_entity(Player(items=hh_item_ids))

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

    def loopy_in_progress(self, _unused1: State, _unused2: Set[EntityType]):
        return self.in_progress(self.loopy_in_progress)

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
        ("loopy_in_progress", ChainStatus.IN_PROGRESS),
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


class MinimalCommonChain(CommonSunkenChain):
    world41_theme = Theme.TIDE_POOL
    world44_theme = Theme.ABZU

    @property
    def world4_item_step(self) -> ChainStepEvaluator:
        return self.fake_world4_step

    def fake_world4_step(self, _unused1: State, _unused2: Set[EntityType]):
        return self.in_progress(self.visit_world44_theme)


@pytest.mark.parametrize(
    "world,item_set,expected_status,expected_step_name",
    [
        (1, set(), ChainStatus.UNSTARTED, None),
        (
            1,
            {EntityType.ITEM_POWERUP_UDJATEYE},
            ChainStatus.IN_PROGRESS,
            "collect_eye_or_headwear",
        ),
        (2, set(), ChainStatus.UNSTARTED, None),
        (2, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.IN_PROGRESS, "collect_ankh"),
        (
            2,
            {EntityType.ITEM_POWERUP_UDJATEYE, EntityType.ITEM_POWERUP_HEDJET},
            ChainStatus.IN_PROGRESS,
            "collect_ankh",
        ),
        (3, set(), ChainStatus.FAILED, None),
        (3, {EntityType.ITEM_POWERUP_HEDJET}, ChainStatus.IN_PROGRESS, "collect_ankh"),
    ],
)
def test_collect_eye_or_headwear(world, item_set, expected_status, expected_step_name):
    fake_chain = MinimalCommonChain()
    game_state = State(world=world)
    result = fake_chain.collect_eye_or_headwear(game_state, item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,item_set,expected_status,expected_step_name",
    [
        (3, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.IN_PROGRESS, "collect_ankh"),
        (
            3,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "visit_world41_theme",
        ),
        (4, set(), ChainStatus.FAILED, None),
        (4, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.FAILED, None),
    ],
)
def test_collect_ankh(world, item_set, expected_status, expected_step_name):
    fake_chain = MinimalCommonChain()
    game_state = State(world=world)
    result = fake_chain.collect_ankh(game_state, item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,theme,expected_status,expected_step_name",
    [
        (3, Theme.OLMEC, ChainStatus.IN_PROGRESS, "visit_world41_theme"),
        (4, Theme.TEMPLE, ChainStatus.FAILED, None),
        (4, Theme.TIDE_POOL, ChainStatus.IN_PROGRESS, "fake_world4_step"),
    ],
)
def test_visit_world41_theme(world, theme, expected_status, expected_step_name):
    fake_chain = MinimalCommonChain()
    game_state = State(world=world, theme=theme)
    result = fake_chain.visit_world41_theme(game_state, set())

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,theme,expected_status,expected_step_name",
    [
        (4, 2, Theme.TIDE_POOL, ChainStatus.IN_PROGRESS, "visit_world44_theme"),
        (4, 3, Theme.TIDE_POOL, ChainStatus.IN_PROGRESS, "visit_world44_theme"),
        (4, 4, Theme.TIDE_POOL, ChainStatus.FAILED, None),
        (4, 4, Theme.ABZU, ChainStatus.IN_PROGRESS, "collect_tablet"),
    ],
)
def test_visit_world44_theme(world, level, theme, expected_status, expected_step_name):
    fake_chain = MinimalCommonChain()
    game_state = State(world=world, level=level, theme=theme)
    result = fake_chain.visit_world44_theme(game_state, set())

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
            "collect_tablet",
        ),
        (
            4,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            ChainStatus.IN_PROGRESS,
            "carry_ushabti_to_63",
        ),
        (5, {EntityType.ITEM_POWERUP_CROWN}, ChainStatus.FAILED, None),
    ],
)
def test_collect_tablet(world, item_set, expected_status, expected_step_name):
    fake_chain = MinimalCommonChain()
    game_state = State(world=world)
    result = fake_chain.collect_tablet(game_state, item_set)

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
            "carry_ushabti_to_63",
        ),
        (
            6,
            1,
            Screen.LEVEL_TRANSITION,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_ushabti_to_63",
        ),
        (
            6,
            2,
            Screen.LEVEL,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_ushabti_to_63",
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
            "win_via_hundun_or_co",
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
            "win_via_hundun_or_co",
        ),
    ],
)
def test_carry_ushabti_to_63(
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

    fake_chain = MinimalCommonChain()
    result = fake_chain.carry_ushabti_to_63(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "win_state,expected_status,expected_step_name",
    [
        (WinState.NO_WIN, ChainStatus.IN_PROGRESS, "win_via_hundun_or_co"),
        (WinState.TIAMAT, ChainStatus.FAILED, None),
        (WinState.HUNDUN, ChainStatus.IN_PROGRESS, "win_via_hundun_or_co"),
        (WinState.COSMIC_OCEAN, ChainStatus.IN_PROGRESS, "win_via_hundun_or_co"),
    ],
)
def test_win_via_hundun_or_co(win_state, expected_status, expected_step_name):
    game_state = State(win_state=win_state)
    fake_chain = MinimalCommonChain()
    result = fake_chain.win_via_hundun_or_co(game_state, set())

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,player_item_set,expected_status,expected_step_name",
    [
        (
            3,
            1,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "collect_excalibur",
        ),
        # Losing Ankh is OK
        (
            4,
            1,
            {EntityType.ITEM_POWERUP_CROWN},
            ChainStatus.IN_PROGRESS,
            "collect_excalibur",
        ),
        (
            4,
            2,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "collect_excalibur",
        ),
        (
            4,
            2,
            {
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_ANKH,
                EntityType.ITEM_EXCALIBUR,
            },
            ChainStatus.IN_PROGRESS,
            "visit_world44_theme",
        ),
        (
            4,
            3,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.FAILED,
            None,
        ),
    ],
)
def test_collect_excalibur(
    world, level, player_item_set, expected_status, expected_step_name
):
    abzu_chain = AbzuChain()
    game_state = State(world=world, level=level)
    result = abzu_chain.collect_excalibur(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,screen,player_item_set,hh_item_set,expected_status,expected_step_name",
    [
        (
            3,
            1,
            Screen.LEVEL,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_scepter_to_42",
        ),
        (
            4,
            1,
            Screen.LEVEL,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_scepter_to_42",
        ),
        # Can't reach Duat without Ankh
        (
            4,
            1,
            Screen.LEVEL,
            {EntityType.ITEM_POWERUP_CROWN},
            set(),
            ChainStatus.FAILED,
            None,
        ),
        (
            4,
            1,
            Screen.LEVEL,
            {
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_ANKH,
                EntityType.ITEM_SCEPTER,
            },
            set(),
            ChainStatus.IN_PROGRESS,
            "carry_scepter_to_42",
        ),
        (
            4,
            1,
            Screen.LEVEL_TRANSITION,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            set(),
            ChainStatus.FAILED,
            None,
        ),
        (
            4,
            1,
            Screen.LEVEL_TRANSITION,
            {
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_ANKH,
                EntityType.ITEM_SCEPTER,
            },
            set(),
            ChainStatus.IN_PROGRESS,
            "visit_city_of_gold",
        ),
        (
            4,
            1,
            Screen.LEVEL_TRANSITION,
            {
                EntityType.ITEM_POWERUP_CROWN,
                EntityType.ITEM_POWERUP_ANKH,
            },
            {EntityType.ITEM_SCEPTER},
            ChainStatus.IN_PROGRESS,
            "visit_city_of_gold",
        ),
    ],
)
def test_carry_scepter_to_42(
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

    duat_chain = DuatChain()
    result = duat_chain.carry_scepter_to_42(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,theme,player_item_set,expected_status,expected_step_name",
    [
        (
            4,
            2,
            Theme.TEMPLE,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "visit_city_of_gold",
        ),
        # Can't reach Duat without Ankh
        (
            4,
            2,
            Theme.TEMPLE,
            set(),
            ChainStatus.FAILED,
            None,
        ),
        (
            4,
            3,
            Theme.TEMPLE,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.FAILED,
            None,
        ),
        (
            4,
            3,
            Theme.CITY_OF_GOLD,
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "keep_ankh",
        ),
    ],
)
def test_visit_city_of_gold(
    world, level, theme, player_item_set, expected_status, expected_step_name
):
    game_state = State(
        world=world,
        level=level,
        theme=theme,
    )

    duat_chain = DuatChain()
    result = duat_chain.visit_city_of_gold(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


@pytest.mark.parametrize(
    "world,level,screen,player,player_item_set,expected_status,expected_step_name",
    [
        (
            4,
            3,
            Screen.LEVEL,
            Player(),
            {EntityType.ITEM_POWERUP_CROWN, EntityType.ITEM_POWERUP_ANKH},
            ChainStatus.IN_PROGRESS,
            "keep_ankh",
        ),
        # No Ankh, no Duat
        (
            4,
            3,
            Screen.LEVEL,
            Player(),
            {EntityType.ITEM_POWERUP_CROWN},
            ChainStatus.FAILED,
            None,
        ),
        # No player, we assume this is due to sacrifice
        (
            4,
            3,
            Screen.LEVEL,
            None,
            set(),
            ChainStatus.IN_PROGRESS,
            "keep_ankh",
        ),
        (
            4,
            3,
            Screen.LEVEL_TRANSITION,
            Player(),
            {EntityType.ITEM_POWERUP_CROWN},
            ChainStatus.IN_PROGRESS,
            "visit_world44_theme",
        ),
    ],
)
def test_keep_ankh(
    world, level, screen, player, player_item_set, expected_status, expected_step_name
):
    game_state = State(
        world=world,
        level=level,
        screen=screen,
        items=Items(players=(player,)),
    )

    duat_chain = DuatChain()
    result = duat_chain.keep_ankh(game_state, player_item_set)

    assert result.status == expected_status
    if expected_status.in_progress:
        assert result.next_step.__name__ == expected_step_name


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
