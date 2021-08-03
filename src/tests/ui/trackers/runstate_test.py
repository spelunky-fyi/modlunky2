import pytest
from modlunky2.mem.entities import (
    CharState,
    EntityDBEntry,
    EntityType,
    Inventory,
    Mount,
    Player,
)
from modlunky2.mem.memrauder.model import MemContext, PolyPointer

from modlunky2.mem.state import RunRecapFlags, Theme
from modlunky2.ui.trackers.label import Label
from modlunky2.ui.trackers.runstate import ChainStatus, RunState

# pylint: disable=protected-access


@pytest.mark.parametrize(
    "label,recap_flag,method",
    [
        (Label.PACIFIST, RunRecapFlags.PACIFIST, RunState.update_pacifist),
        (Label.NO_GOLD, RunRecapFlags.NO_GOLD, RunState.update_no_gold),
    ],
)
def test_run_recap(label, recap_flag, method):
    run_state = RunState()
    method(run_state, recap_flag)
    assert label in run_state.run_label._set

    run_state = RunState()
    method(run_state, RunRecapFlags(0))
    assert label not in run_state.run_label._set


@pytest.mark.parametrize(
    "item_set,expected_no_tp",
    [
        ({EntityType.ITEM_TELEPORTER}, False),
        ({EntityType.ITEM_POWERUP_COMPASS}, True),
        (set(), True),
    ],
)
def test_no_tp(item_set, expected_no_tp):
    run_state = RunState()
    run_state.update_no_tp(item_set)
    is_no_tp = Label.NO_TELEPORTER in run_state.run_label._set
    assert is_no_tp == expected_no_tp


@pytest.mark.parametrize(
    "world,item_set,expected_eggplant",
    [
        # Eggplant crown can only be collected in Sunken City
        (7, {EntityType.ITEM_POWERUP_EGGPLANTCROWN}, True),
        (6, set(), False),
        (7, set(), False),
        (8, set(), False),
    ],
)
def test_eggplant(world, item_set, expected_eggplant):
    run_state = RunState()
    run_state.update_eggplant(world, item_set)
    is_eggplant = Label.EGGPLANT in run_state.run_label._set
    assert is_eggplant == expected_eggplant


@pytest.mark.parametrize(
    "world,item_set,expected_score,expected_hou_yi",
    [
        (7, {EntityType.ITEM_POWERUP_EGGPLANTCROWN}, False, False),
        (3, {EntityType.ITEM_HOUYIBOW}, False, True),
        (2, {EntityType.ITEM_HOUYIBOW}, False, False),
        (1, {EntityType.ITEM_PLASMACANNON}, True, False),
        (5, {EntityType.ITEM_PLASMACANNON}, True, False),
        (1, set(), False, False),
        (6, set(), False, False),
    ],
)
def test_score_items(world, item_set, expected_score, expected_hou_yi):
    run_state = RunState()
    run_state.update_score_items(world, item_set)

    is_score = Label.SCORE in run_state.run_label._set
    assert is_score == expected_score

    assert run_state.hou_yis_waddler == expected_hou_yi


@pytest.mark.parametrize(
    "chain_status,theme,mount_type,mount_tamed,expected_low",
    [
        # Mounting Qilin in Neo-Bab is never allowed
        (ChainStatus.UNSTARTED, Theme.NEO_BABYLON, EntityType.MOUNT_QILIN, True, False),
        (
            ChainStatus.IN_PROGRESS,
            Theme.NEO_BABYLON,
            EntityType.MOUNT_QILIN,
            True,
            False,
        ),
        (ChainStatus.FAILED, Theme.NEO_BABYLON, EntityType.MOUNT_QILIN, True, False),
        # Mounting Qilin in Tiamat's Lair is only OK during quest chain
        (ChainStatus.UNSTARTED, Theme.TIAMAT, EntityType.MOUNT_QILIN, True, False),
        (ChainStatus.IN_PROGRESS, Theme.TIAMAT, EntityType.MOUNT_QILIN, True, True),
        (ChainStatus.FAILED, Theme.TIAMAT, EntityType.MOUNT_QILIN, True, False),
        # Mounting tamed turkeys is never OK
        (ChainStatus.UNSTARTED, Theme.TIDE_POOL, EntityType.MOUNT_TURKEY, True, False),
        (ChainStatus.IN_PROGRESS, Theme.TEMPLE, EntityType.MOUNT_TURKEY, True, False),
        (ChainStatus.FAILED, Theme.JUNGLE, EntityType.MOUNT_TURKEY, True, False),
        # Mounting untamed turkeys is always OK
        (ChainStatus.UNSTARTED, Theme.DWELLING, EntityType.MOUNT_TURKEY, False, True),
        (ChainStatus.IN_PROGRESS, Theme.VOLCANA, EntityType.MOUNT_TURKEY, False, True),
        (ChainStatus.FAILED, Theme.NEO_BABYLON, EntityType.MOUNT_TURKEY, False, True),
        # Not being on a mount is OK
        (ChainStatus.UNSTARTED, Theme.HUNDUN, None, False, True),
        (ChainStatus.IN_PROGRESS, Theme.COSMIC_OCEAN, None, False, True),
        (ChainStatus.FAILED, Theme.JUNGLE, None, False, True),
    ],
)
def test_has_mounted_tame(chain_status, theme, mount_type, mount_tamed, expected_low):
    mount = Mount(type=EntityDBEntry(id=mount_type), is_tamed=mount_tamed)
    poly_mount = PolyPointer(101, mount, MemContext())

    run_state = RunState()
    run_state.update_has_mounted_tame(chain_status, theme, poly_mount)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "char_state,prev_health,cur_health,expected_low",
    [
        (CharState.STANDING, 4, 4, True),
        (CharState.STANDING, 2, 1, True),
        (CharState.STANDING, 3, 1, True),
        (CharState.DYING, 1, 4, True),
        (CharState.STANDING, 1, 2, False),
        (CharState.STANDING, 2, 4, False),
        (CharState.STANDING, 5, 5, False),
    ],
)
def test_starting_resources_health(char_state, prev_health, cur_health, expected_low):
    run_state = RunState()
    run_state.health = prev_health

    player = Player(state=char_state, health=cur_health)
    run_state.update_starting_resources(player, char_state, player.inventory)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "prev_bombs,cur_bombs,expected_low",
    [
        (4, 4, True),
        (4, 3, True),
        (3, 1, True),
        (7, 7, False),
        (1, 4, False),
    ],
)
def test_starting_resources_bombs(prev_bombs, cur_bombs, expected_low):
    run_state = RunState()
    run_state.bombs = prev_bombs

    inventory = Inventory(bombs=cur_bombs)
    player = Player(inventory=inventory)
    run_state.update_starting_resources(player, player.state, inventory)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "level_start_ropes,prev_ropes,cur_ropes,expected_low",
    [
        (4, 4, 4, True),
        (4, 4, 3, True),
        (3, 3, 1, True),
        (3, 2, 3, True),
        (7, 7, 7, False),
        (1, 1, 4, False),
    ],
)
def test_starting_resources_ropes(
    level_start_ropes, prev_ropes, cur_ropes, expected_low
):
    run_state = RunState()
    run_state.level_start_ropes = level_start_ropes
    run_state.ropes = prev_ropes

    inventory = Inventory(ropes=cur_ropes)
    player = Player(inventory=inventory)
    run_state.update_starting_resources(player, player.state, inventory)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low
