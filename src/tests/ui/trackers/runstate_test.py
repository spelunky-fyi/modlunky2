import pytest
from modlunky2.mem.entities import (
    CharState,
    EntityDBEntry,
    EntityType,
    Inventory,
    Layer,
    Mount,
    Player,
)
from modlunky2.mem.memrauder.model import MemContext, PolyPointer

from modlunky2.mem.state import HudFlags, PresenceFlags, RunRecapFlags, Theme
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
    assert run_state.health == cur_health

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

    assert run_state.bombs == cur_bombs

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

    assert run_state.ropes == cur_ropes

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "player_state,prev_poisoned,item_set,expected_poisoned,expected_low",
    [
        (CharState.STANDING, False, {EntityType.LOGICAL_POISONED_EFFECT}, True, True),
        (CharState.STANDING, True, {EntityType.LOGICAL_POISONED_EFFECT}, True, True),
        (CharState.STANDING, True, set(), False, False),
        (CharState.DYING, True, set(), False, True),
        # We should skip checks during weird states
        (CharState.ENTERING, True, set(), True, True),
        (CharState.EXITING, True, set(), True, True),
        (CharState.LOADING, True, set(), True, True),
    ],
)
def test_status_effects_poisoned(
    player_state, prev_poisoned, item_set, expected_poisoned, expected_low
):
    run_state = RunState()
    run_state.poisoned = prev_poisoned

    run_state.update_status_effects(player_state, item_set)
    assert run_state.poisoned == expected_poisoned

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "player_state,prev_cursed,item_set,expected_cursed,expected_low",
    [
        (CharState.STANDING, False, {EntityType.LOGICAL_CURSED_EFFECT}, True, True),
        (CharState.STANDING, True, {EntityType.LOGICAL_CURSED_EFFECT}, True, True),
        (CharState.STANDING, True, set(), False, False),
        (CharState.DYING, True, set(), False, True),
        # We should skip checks during weird states
        (CharState.ENTERING, True, set(), True, True),
        (CharState.EXITING, True, set(), True, True),
        (CharState.LOADING, True, set(), True, True),
    ],
)
def test_status_effects_cursed(
    player_state, prev_cursed, item_set, expected_cursed, expected_low
):
    run_state = RunState()
    run_state.cursed = prev_cursed

    run_state.update_status_effects(player_state, item_set)
    assert run_state.cursed == expected_cursed

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "hud_flags,expected_low",
    [
        (HudFlags.HAVE_CLOVER, False),
        (0, True),
        (~HudFlags.HAVE_CLOVER, True),
    ],
)
def test_had_clover(hud_flags, expected_low):
    run_state = RunState()
    run_state.update_had_clover(hud_flags)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "item_set,expected_no_jp,expected_low",
    [
        ({EntityType.ITEM_JETPACK}, False, False),
        # We exercise the most popular backpacks
        ({EntityType.ITEM_HOVERPACK}, True, False),
        ({EntityType.ITEM_VLADS_CAPE}, True, False),
        ({EntityType.ITEM_TELEPORTER_BACKPACK}, True, False),
        # Not a backpack
        ({EntityType.ITEM_SHOTGUN}, True, True),
        (set(), True, True),
    ],
)
def test_wore_backpack(item_set, expected_no_jp, expected_low):
    run_state = RunState()
    run_state.update_wore_backpack(item_set)

    is_no_jp = Label.NO_JETPACK in run_state.run_label._set
    assert is_no_jp == expected_no_jp

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "item_set,expected_low",
    [
        ({EntityType.ITEM_METAL_SHIELD}, False),
        ({EntityType.ITEM_WOODEN_SHIELD}, False),
        # Just holding a camera is OK
        ({EntityType.ITEM_CAMERA}, True),
        (set(), True),
    ],
)
def test_held_shield(item_set, expected_low):
    run_state = RunState()
    run_state.update_held_shield(item_set)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "chain_status,item_set,expected_failed_low_if_not_chain,expected_low",
    [
        # All of  these are fine while the chain is in-progress
        (ChainStatus.IN_PROGRESS, {EntityType.ITEM_POWERUP_UDJATEYE}, True, True),
        (ChainStatus.IN_PROGRESS, {EntityType.ITEM_POWERUP_CROWN}, True, True),
        (ChainStatus.IN_PROGRESS, {EntityType.ITEM_POWERUP_HEDJET}, True, True),
        # Starting points are OK even if we haven't updated chain status
        (ChainStatus.UNSTARTED, {EntityType.ITEM_POWERUP_UDJATEYE}, True, True),
        (ChainStatus.UNSTARTED, {EntityType.ITEM_POWERUP_CROWN}, True, True),
        (ChainStatus.UNSTARTED, {EntityType.ITEM_POWERUP_HEDJET}, True, True),
        # If it's not a starting point for the chain, and chain isn't in progress, we should fail immediately
        (ChainStatus.UNSTARTED, {EntityType.ITEM_POWERUP_ANKH}, True, False),
        (ChainStatus.UNSTARTED, {EntityType.ITEM_POWERUP_TABLETOFDESTINY}, True, False),
        (ChainStatus.FAILED, {EntityType.ITEM_POWERUP_ANKH}, True, False),
        (ChainStatus.FAILED, {EntityType.ITEM_POWERUP_TABLETOFDESTINY}, True, False),
    ],
)
def test_has_chain_powerup(
    chain_status, item_set, expected_failed_low_if_not_chain, expected_low
):
    run_state = RunState()
    run_state.update_has_chain_powerup(chain_status, item_set)
    assert run_state.failed_low_if_not_chain == expected_failed_low_if_not_chain

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "item_set,expected_low",
    [
        # Exercise the most common power-ups
        ({EntityType.ITEM_POWERUP_COMPASS}, False),
        ({EntityType.ITEM_POWERUP_PARACHUTE}, False),
        ({EntityType.ITEM_POWERUP_SKELETON_KEY}, False),
        ({EntityType.ITEM_POWERUP_SPIKE_SHOES}, False),
        ({EntityType.ITEM_POWERUP_SPRING_SHOES}, False),
        # Having more than one isn't OK eithere
        (
            {EntityType.ITEM_POWERUP_PARACHUTE, EntityType.ITEM_POWERUP_SPRING_SHOES},
            False,
        ),
        # Just holding the arrow of light is OK
        ({EntityType.ITEM_LIGHT_ARROW}, True),
        (set(), True),
    ],
)
def test_has_non_chain_powerup(item_set, expected_low):
    run_state = RunState()
    run_state.update_has_non_chain_powerup(item_set)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "prev_state,cur_state,item_set,expected_low",
    [
        (CharState.STANDING, CharState.ATTACKING, {EntityType.ITEM_BOOMERANG}, False),
        (CharState.ATTACKING, CharState.STANDING, {EntityType.ITEM_BOOMERANG}, False),
        # Holding things is OK
        (CharState.JUMPING, CharState.CLIMBING, {EntityType.ITEM_BOOMERANG}, True),
        # Rocks are OK
        (CharState.JUMPING, CharState.CLIMBING, {EntityType.ITEM_ROCK}, True),
        (CharState.STANDING, CharState.ATTACKING, {EntityType.ITEM_ROCK}, True),
        (CharState.ATTACKING, CharState.STANDING, {EntityType.ITEM_ROCK}, True),
        # Using the whip is OK
        (CharState.JUMPING, CharState.CLIMBING, set(), True),
        (CharState.STANDING, CharState.ATTACKING, set(), True),
        (CharState.ATTACKING, CharState.STANDING, set(), True),
    ],
)
def test_attacked_with_simple(prev_state, cur_state, item_set, expected_low):
    # These shouldn't be location sensitive
    layer = Layer.FRONT
    world = 2
    level = 2
    theme = Theme.JUNGLE
    presence_flags = 0
    run_state = RunState()
    run_state.chain_status = ChainStatus.IN_PROGRESS
    run_state.update_attacked_with(
        prev_state, cur_state, layer, world, level, theme, presence_flags, item_set
    )

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "layer,theme,presence_flags,chain_status,expected_lc_has_swung_excalibur,expected_low",
    [
        # Not OK to swing in Tide Pool, regardless of chain or presence
        (
            Layer.FRONT,
            Theme.TIDE_POOL,
            PresenceFlags.STAR_CHALLENGE,
            ChainStatus.UNSTARTED,
            False,
            False,
        ),
        (
            Layer.BACK,
            Theme.TIDE_POOL,
            PresenceFlags.STAR_CHALLENGE,
            ChainStatus.IN_PROGRESS,
            False,
            False,
        ),
        (
            Layer.FRONT,
            Theme.TIDE_POOL,
            0,
            ChainStatus.IN_PROGRESS,
            False,
            False,
        ),
        (
            Layer.BACK,
            Theme.TIDE_POOL,
            0,
            ChainStatus.FAILED,
            False,
            False,
        ),
        # OK in Abzu only if chain is in progress
        (
            Layer.FRONT,
            Theme.ABZU,
            0,
            ChainStatus.IN_PROGRESS,
            True,
            True,
        ),
        (
            Layer.BACK,
            Theme.ABZU,
            0,
            ChainStatus.IN_PROGRESS,
            True,
            True,
        ),
        (
            Layer.FRONT,
            Theme.ABZU,
            0,
            ChainStatus.UNSTARTED,
            True,
            False,
        ),
        (
            Layer.BACK,
            Theme.ABZU,
            0,
            ChainStatus.FAILED,
            True,
            False,
        ),
        # Not OK later areas
        (
            Layer.FRONT,
            Theme.ICE_CAVES,
            ChainStatus.FAILED,
            0,
            False,
            False,
        ),
        (
            Layer.BACK,
            Theme.NEO_BABYLON,
            0,
            ChainStatus.IN_PROGRESS,
            False,
            False,
        ),
    ],
)
def test_attacked_with_excalibur(
    layer,
    theme,
    presence_flags,
    chain_status,
    expected_lc_has_swung_excalibur,
    expected_low,
):
    prev_state = CharState.PUSHING
    cur_state = CharState.ATTACKING
    item_set = {EntityType.ITEM_EXCALIBUR}
    # These should vary with theme, but there's already a lot of params
    world = 4
    level = 2
    run_state = RunState()
    run_state.chain_status = chain_status
    run_state.update_attacked_with(
        prev_state, cur_state, layer, world, level, theme, presence_flags, item_set
    )

    # We only expect these to be set together
    assert run_state.failed_low_if_not_chain == expected_lc_has_swung_excalibur
    assert run_state.lc_has_swung_excalibur == expected_lc_has_swung_excalibur

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "layer,theme,presence_flags,expected_low",
    [
        # Front layer isn't OK with moon challenge
        (
            Layer.FRONT,
            Theme.VOLCANA,
            PresenceFlags.MOON_CHALLENGE,
            False,
        ),
        (
            Layer.FRONT,
            Theme.JUNGLE,
            PresenceFlags.MOON_CHALLENGE,
            False,
        ),
        # In moon challenge is OK
        (
            Layer.BACK,
            Theme.VOLCANA,
            PresenceFlags.MOON_CHALLENGE,
            True,
        ),
        (
            Layer.BACK,
            Theme.JUNGLE,
            PresenceFlags.MOON_CHALLENGE,
            True,
        ),
        # Not OK to swing in back layer w/o moon challenge
        (
            Layer.BACK,
            Theme.VOLCANA,
            0,
            False,
        ),
        (
            Layer.BACK,
            Theme.JUNGLE,
            0,
            False,
        ),
        # Some places moon challenge can't spawn
        (
            Layer.FRONT,
            Theme.DWELLING,
            0,
            False,
        ),
        (
            Layer.BACK,
            Theme.OLMEC,
            0,
            False,
        ),
    ],
)
def test_attacked_with_mattock(layer, theme, presence_flags, expected_low):
    prev_state = CharState.PUSHING
    cur_state = CharState.ATTACKING
    item_set = {EntityType.ITEM_MATTOCK}
    # These should vary with theme, but there's already a lot of params
    world = 2
    level = 2
    run_state = RunState()
    run_state.update_attacked_with(
        prev_state, cur_state, layer, world, level, theme, presence_flags, item_set
    )

    # We only expect this to be set when we're still low%
    assert run_state.mc_has_swung_mattock == expected_low

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "layer,world,level,presence_flags,expected_low",
    [
        # Places where back layer is allowed
        (Layer.BACK, 2, 3, PresenceFlags.MOON_CHALLENGE, True),
        (Layer.BACK, 3, 1, 0, True),
        (Layer.BACK, 5, 1, 0, True),
        (Layer.BACK, 7, 1, 0, True),
        (Layer.BACK, 7, 2, PresenceFlags.SUN_CHALLENGE, True),
        # Front layer isn't OK just because back layer would be
        (Layer.FRONT, 2, 3, PresenceFlags.MOON_CHALLENGE, False),
        (Layer.FRONT, 3, 1, 0, False),
        (Layer.FRONT, 5, 1, 0, False),
        (Layer.FRONT, 7, 1, 0, False),
        (Layer.FRONT, 7, 2, PresenceFlags.SUN_CHALLENGE, False),
        # Hundun is OK
        (Layer.FRONT, 7, 4, 0, True),
        # CO isn't OK
        (Layer.FRONT, 7, 5, 0, False),
    ],
)
def test_attacked_with_hou_yi(layer, world, level, presence_flags, expected_low):
    prev_state = CharState.JUMPING
    cur_state = CharState.ATTACKING
    item_set = {EntityType.ITEM_HOUYIBOW}
    # This should vary with world+level, but there's already a lot of params
    theme = Theme.DWELLING
    run_state = RunState()
    run_state.update_attacked_with(
        prev_state, cur_state, layer, world, level, theme, presence_flags, item_set
    )

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low
