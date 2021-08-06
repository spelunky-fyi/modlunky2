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

from modlunky2.mem.state import (
    HudFlags,
    PresenceFlags,
    RunRecapFlags,
    State,
    Theme,
    WinState,
)
from modlunky2.ui.trackers.label import Label, RunLabel
from modlunky2.ui.trackers.runstate import ChainStatus, RunState

# pylint: disable=protected-access,too-many-lines


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
    "player_state,item_set,expected_final_death",
    [
        (CharState.STANDING, set(), False),
        (CharState.DYING, {EntityType.ITEM_POWERUP_ANKH}, False),
        (CharState.DYING, set(), True),
        (CharState.DYING, {EntityType.ITEM_POWERUP_PASTE}, True),
    ],
)
def test_final_death(player_state, item_set, expected_final_death):
    run_state = RunState()
    run_state.update_final_death(player_state, item_set)
    assert run_state.final_death == expected_final_death


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
    run_state.chain_status = chain_status
    run_state.update_has_mounted_tame(theme, poly_mount)

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
    run_state.update_starting_resources(player)
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
    run_state.update_starting_resources(player)

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
    run_state.update_starting_resources(player)

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
    "layer,theme,presence_flags,chain_status,expected_failed_low_if_not_chain,expected_low",
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
    expected_failed_low_if_not_chain,
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
    assert run_state.failed_low_if_not_chain == expected_failed_low_if_not_chain

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


@pytest.mark.parametrize(
    "prev_state,cur_state,prev_item_set,cur_item_set,expected_low",
    [
        (
            CharState.THROWING,
            CharState.STANDING,
            {EntityType.ITEM_LIGHT_ARROW},
            set(),
            False,
        ),
        (
            CharState.STANDING,
            CharState.THROWING,
            set(),
            {EntityType.ITEM_LIGHT_ARROW},
            False,
        ),
        (
            CharState.THROWING,
            CharState.STANDING,
            {EntityType.ITEM_WOODEN_ARROW},
            set(),
            True,
        ),
        (
            CharState.STANDING,
            CharState.THROWING,
            set(),
            {EntityType.ITEM_WOODEN_ARROW},
            True,
        ),
        # Sometimes the throwing state was a while ago
        (CharState.THROWING, CharState.STANDING, set(), set(), True),
    ],
)
def test_attacked_with_throwables(
    prev_state, cur_state, prev_item_set, cur_item_set, expected_low
):
    run_state = RunState()
    run_state.update_attacked_with_throwables(
        prev_state, cur_state, prev_item_set, cur_item_set
    )

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "item_type, property_name",
    [
        (EntityType.ITEM_POWERUP_UDJATEYE, "had_udjat_eye"),
        (EntityType.ITEM_POWERUP_CROWN, "had_world2_chain_headwear"),
        (EntityType.ITEM_POWERUP_HEDJET, "had_world2_chain_headwear"),
        (EntityType.ITEM_POWERUP_ANKH, "had_ankh"),
        (EntityType.ITEM_EXCALIBUR, "held_world4_chain_item"),
        (EntityType.ITEM_SCEPTER, "held_world4_chain_item"),
        (EntityType.ITEM_POWERUP_TABLETOFDESTINY, "had_tablet_of_destiny"),
        (EntityType.ITEM_USHABTI, "held_ushabti"),
        (EntityType.ITEM_HOUYIBOW, "hou_yis_bow"),
    ],
)
def test_chain(item_type, property_name):
    run_state = RunState()
    assert run_state.__getattribute__(property_name) is False
    run_state.update_chain({item_type})
    assert run_state.__getattribute__(property_name) is True


@pytest.mark.parametrize(
    "world,theme,expected_world2_theme,expected_world4_theme",
    [
        (2, Theme.JUNGLE, Theme.JUNGLE, None),
        (2, Theme.VOLCANA, Theme.VOLCANA, None),
        (4, Theme.TEMPLE, None, Theme.TEMPLE),
        # CoG and Duat imply we went Temple
        (4, Theme.CITY_OF_GOLD, None, Theme.TEMPLE),
        (4, Theme.DUAT, None, Theme.TEMPLE),
        (4, Theme.TIDE_POOL, None, Theme.TIDE_POOL),
        # Abzu implies we went Tide Pool
        (4, Theme.ABZU, None, Theme.TIDE_POOL),
    ],
)
def test_world_themes_state(world, theme, expected_world2_theme, expected_world4_theme):
    run_state = RunState()
    run_state.update_world_themes(world, theme)
    assert run_state.world2_theme == expected_world2_theme
    assert run_state.world4_theme == expected_world4_theme


@pytest.mark.parametrize(
    "world,theme,world2_theme,chain_status,starting_labels,expected_jt,expected_abzu,expected_duat",
    [
        # Volcana has no labels associated with it
        (
            2,
            Theme.VOLCANA,
            None,
            ChainStatus.UNSTARTED,
            {Label.ANY},
            False,
            False,
            False,
        ),
        # We eagerly assume J/T regardless of quest chain
        (2, Theme.JUNGLE, None, ChainStatus.UNSTARTED, {Label.ANY}, True, False, False),
        (
            2,
            Theme.JUNGLE,
            Theme.JUNGLE,
            ChainStatus.UNSTARTED,
            {Label.ANY},
            True,
            False,
            False,
        ),
        (
            2,
            Theme.JUNGLE,
            Theme.JUNGLE,
            ChainStatus.IN_PROGRESS,
            {Label.SUNKEN_CITY},
            True,
            False,
            False,
        ),
        # We actually went J/T. Duat depends on quest chain
        (
            4,
            Theme.TEMPLE,
            Theme.JUNGLE,
            ChainStatus.UNSTARTED,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            True,
            False,
            False,
        ),
        (
            4,
            Theme.TEMPLE,
            Theme.JUNGLE,
            ChainStatus.IN_PROGRESS,
            {Label.JUNGLE_TEMPLE, Label.SUNKEN_CITY},
            True,
            False,
            True,
        ),
        (
            4,
            Theme.TEMPLE,
            Theme.JUNGLE,
            ChainStatus.FAILED,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            True,
            False,
            False,
        ),
        # Since we went Volcana, we're only eligible for Duat
        (
            4,
            Theme.TEMPLE,
            Theme.VOLCANA,
            ChainStatus.UNSTARTED,
            {Label.ANY},
            False,
            False,
            False,
        ),
        (
            4,
            Theme.TEMPLE,
            Theme.VOLCANA,
            ChainStatus.IN_PROGRESS,
            {Label.SUNKEN_CITY},
            False,
            False,
            True,
        ),
        (
            4,
            Theme.TEMPLE,
            Theme.VOLCANA,
            ChainStatus.FAILED,
            {Label.ANY},
            False,
            False,
            False,
        ),
        # Since we went Volcana, we're only eligible for Abzu
        (
            4,
            Theme.TIDE_POOL,
            Theme.VOLCANA,
            ChainStatus.UNSTARTED,
            {Label.ANY},
            False,
            False,
            False,
        ),
        (
            4,
            Theme.TIDE_POOL,
            Theme.VOLCANA,
            ChainStatus.IN_PROGRESS,
            {Label.SUNKEN_CITY},
            False,
            True,
            False,
        ),
        (
            4,
            Theme.TIDE_POOL,
            Theme.VOLCANA,
            ChainStatus.FAILED,
            {Label.ANY},
            False,
            False,
            False,
        ),
        # We went Jungle, but J/T is now impossible. Abzu depends on quest chain
        (
            4,
            Theme.TIDE_POOL,
            Theme.JUNGLE,
            ChainStatus.UNSTARTED,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            False,
            False,
            False,
        ),
        (
            4,
            Theme.TIDE_POOL,
            Theme.JUNGLE,
            ChainStatus.IN_PROGRESS,
            {Label.JUNGLE_TEMPLE, Label.SUNKEN_CITY},
            False,
            True,
            False,
        ),
        (
            4,
            Theme.TIDE_POOL,
            Theme.JUNGLE,
            ChainStatus.FAILED,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            False,
            False,
            False,
        ),
    ],
)
def test_world_themes_label(
    world,
    theme,
    world2_theme,
    chain_status,
    starting_labels,
    expected_jt,
    expected_abzu,
    expected_duat,
):
    run_state = RunState()
    run_state.run_label = RunLabel(starting=starting_labels)
    run_state.world2_theme = world2_theme
    run_state.chain_status = chain_status
    run_state.update_world_themes(world, theme)

    is_jt = Label.JUNGLE_TEMPLE in run_state.run_label._set
    assert is_jt == expected_jt

    is_abzu = Label.ABZU in run_state.run_label._set
    assert is_abzu == expected_abzu

    is_duat = Label.DUAT in run_state.run_label._set
    assert is_duat == expected_duat


@pytest.mark.parametrize(
    "world,win_state,final_death,had_ankh,chain_status,expected_terminus",
    [
        (1, WinState.NO_WIN, False, False, ChainStatus.UNSTARTED, Label.ANY),
        (1, WinState.NO_WIN, True, False, ChainStatus.UNSTARTED, Label.DEATH),
        (2, WinState.NO_WIN, False, False, ChainStatus.IN_PROGRESS, Label.SUNKEN_CITY),
        (4, WinState.NO_WIN, False, False, ChainStatus.UNSTARTED, Label.ANY),
        # If you have the anhk, it means Sunken City%
        (4, WinState.NO_WIN, False, True, ChainStatus.UNSTARTED, Label.SUNKEN_CITY),
        (4, WinState.NO_WIN, False, True, ChainStatus.IN_PROGRESS, Label.SUNKEN_CITY),
        (4, WinState.NO_WIN, False, True, ChainStatus.FAILED, Label.SUNKEN_CITY),
        # Tried for chain, but failed before getting the ankh means falling back to Any%
        (4, WinState.NO_WIN, False, False, ChainStatus.FAILED, Label.ANY),
        # Died before Sunken City means Death%
        (4, WinState.NO_WIN, True, True, ChainStatus.IN_PROGRESS, Label.DEATH),
        # If you're in Sunken City
        (7, WinState.NO_WIN, False, False, ChainStatus.UNSTARTED, Label.SUNKEN_CITY),
        (7, WinState.NO_WIN, False, True, ChainStatus.FAILED, Label.SUNKEN_CITY),
        # Tiamat win means Any%
        (6, WinState.TIAMAT, False, False, ChainStatus.UNSTARTED, Label.ANY),
        (6, WinState.TIAMAT, False, True, ChainStatus.UNSTARTED, Label.ANY),
        (6, WinState.TIAMAT, False, True, ChainStatus.IN_PROGRESS, Label.ANY),
        (6, WinState.TIAMAT, False, True, ChainStatus.FAILED, Label.ANY),
        # ... even if you're on the score screen
        (1, WinState.TIAMAT, False, False, ChainStatus.UNSTARTED, Label.ANY),
        # Hundun win means Sunken City%
        (6, WinState.HUNDUN, False, False, ChainStatus.UNSTARTED, Label.SUNKEN_CITY),
        (6, WinState.HUNDUN, False, True, ChainStatus.UNSTARTED, Label.SUNKEN_CITY),
        (6, WinState.HUNDUN, False, True, ChainStatus.IN_PROGRESS, Label.SUNKEN_CITY),
        (6, WinState.HUNDUN, False, True, ChainStatus.FAILED, Label.SUNKEN_CITY),
        # ... even if you're on the score screen
        (1, WinState.HUNDUN, False, False, ChainStatus.UNSTARTED, Label.SUNKEN_CITY),
    ],
)
def test_update_terminus_non_co(
    world, win_state, final_death, had_ankh, chain_status, expected_terminus
):
    run_state = RunState()
    run_state.final_death = final_death
    run_state.had_ankh = had_ankh
    run_state.chain_status = chain_status

    theme = Theme.TIDE_POOL
    run_state.update_terminus(world, theme, win_state)

    assert Label.NO_CO in run_state.run_label._set
    assert run_state.run_label._terminus == expected_terminus


@pytest.mark.parametrize(
    "world,theme,hou_yis_waddler,final_death,chain_status,expected_terminus",
    [
        # No bow here means no CO, regardless of chain
        (3, Theme.OLMEC, False, False, ChainStatus.UNSTARTED, Label.ANY),
        (3, Theme.OLMEC, False, False, ChainStatus.IN_PROGRESS, Label.SUNKEN_CITY),
        (3, Theme.OLMEC, False, False, ChainStatus.FAILED, Label.ANY),
        # Having the bow here means CO, regardless of chain
        (3, Theme.OLMEC, True, False, ChainStatus.IN_PROGRESS, Label.COSMIC_OCEAN),
        (3, Theme.OLMEC, True, False, ChainStatus.FAILED, Label.COSMIC_OCEAN),
        # ... but not if we're dead
        (3, Theme.OLMEC, True, True, ChainStatus.FAILED, Label.DEATH),
        # Same cases, checking for SC oddness
        (7, Theme.OLMEC, True, False, ChainStatus.IN_PROGRESS, Label.COSMIC_OCEAN),
        (7, Theme.OLMEC, True, False, ChainStatus.FAILED, Label.COSMIC_OCEAN),
        (7, Theme.OLMEC, True, True, ChainStatus.FAILED, Label.DEATH),
        # Being in CO implies CO, even if we're dead
        (7, Theme.COSMIC_OCEAN, True, False, ChainStatus.UNSTARTED, Label.COSMIC_OCEAN),
        (7, Theme.COSMIC_OCEAN, True, True, ChainStatus.UNSTARTED, Label.COSMIC_OCEAN),
    ],
)
def test_update_terminus_score_co(
    world, theme, hou_yis_waddler, chain_status, final_death, expected_terminus
):
    run_state = RunState()
    run_state.chain_status = chain_status
    run_state.final_death = final_death
    run_state.hou_yis_waddler = hou_yis_waddler
    run_state.hou_yis_bow = True
    run_state.is_score_run = True

    win_state = WinState.NO_WIN
    run_state.update_terminus(world, theme, win_state)

    assert run_state.run_label._terminus == expected_terminus


@pytest.mark.parametrize(
    # All of these cases assume we picked up the bow
    "world,theme,final_death,had_ankh,chain_status,expected_terminus",
    [
        # Having the bow here means CO, regardless of chain
        (3, Theme.OLMEC, False, False, ChainStatus.UNSTARTED, Label.COSMIC_OCEAN),
        (3, Theme.OLMEC, False, False, ChainStatus.IN_PROGRESS, Label.COSMIC_OCEAN),
        (3, Theme.OLMEC, False, True, ChainStatus.IN_PROGRESS, Label.COSMIC_OCEAN),
        (3, Theme.OLMEC, False, False, ChainStatus.FAILED, Label.COSMIC_OCEAN),
        # ... but not if we're dead
        (3, Theme.OLMEC, True, False, ChainStatus.UNSTARTED, Label.DEATH),
        (3, Theme.OLMEC, True, True, ChainStatus.FAILED, Label.DEATH),
        # Similar cases, checking for SC oddness
        (7, Theme.SUNKEN_CITY, False, False, ChainStatus.UNSTARTED, Label.COSMIC_OCEAN),
        (7, Theme.SUNKEN_CITY, False, False, ChainStatus.FAILED, Label.COSMIC_OCEAN),
        (
            7,
            Theme.SUNKEN_CITY,
            False,
            True,
            ChainStatus.IN_PROGRESS,
            Label.COSMIC_OCEAN,
        ),
        (7, Theme.SUNKEN_CITY, False, False, ChainStatus.FAILED, Label.COSMIC_OCEAN),
        (7, Theme.SUNKEN_CITY, True, False, ChainStatus.UNSTARTED, Label.DEATH),
        (7, Theme.SUNKEN_CITY, True, True, ChainStatus.IN_PROGRESS, Label.DEATH),
        # Being in CO implies CO, even if we're dead
        (7, Theme.COSMIC_OCEAN, True, False, ChainStatus.UNSTARTED, Label.COSMIC_OCEAN),
        (
            7,
            Theme.COSMIC_OCEAN,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            Label.COSMIC_OCEAN,
        ),
    ],
)
def test_update_terminus_speed_co(
    world, theme, had_ankh, chain_status, final_death, expected_terminus
):
    run_state = RunState()
    run_state.had_ankh = had_ankh
    run_state.chain_status = chain_status
    run_state.final_death = final_death
    run_state.hou_yis_bow = True

    win_state = WinState.NO_WIN
    run_state.update_terminus(world, theme, win_state)

    assert run_state.run_label._terminus == expected_terminus


@pytest.mark.parametrize(
    "world,had_udjat_eye,had_world2_chain_headwear,prev_chain_status,expected_chain_status",
    [
        # World 1
        (1, False, False, ChainStatus.UNSTARTED, ChainStatus.UNSTARTED),
        (1, True, False, ChainStatus.UNSTARTED, ChainStatus.IN_PROGRESS),
        # World 2, various points
        (2, False, False, ChainStatus.UNSTARTED, ChainStatus.UNSTARTED),
        (2, False, True, ChainStatus.UNSTARTED, ChainStatus.IN_PROGRESS),
        (2, True, False, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
        (2, True, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
        # Check start of Olmec
        (3, False, False, ChainStatus.UNSTARTED, ChainStatus.FAILED),
        (3, False, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
        (3, True, False, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (3, True, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
    ],
)
def test_is_chain_pre_world4(
    world,
    had_udjat_eye,
    had_world2_chain_headwear,
    prev_chain_status,
    expected_chain_status,
):
    run_state = RunState()
    run_state.had_udjat_eye = had_udjat_eye
    run_state.had_world2_chain_headwear = had_world2_chain_headwear
    run_state.chain_status = prev_chain_status

    level = 1  # bogus, but we don't look at it here
    theme = Theme.DWELLING  # bogus, but we don't look at it here
    win_state = WinState.NO_WIN
    run_state.update_is_chain(world, level, theme, win_state)

    assert run_state.chain_status == expected_chain_status


@pytest.mark.parametrize(
    # These tests focus on transitions. Once we've established a steady failed state, we stop bothering
    "theme,level,had_ankh,held_world4_chain_item,prev_chain_status,expected_chain_status",
    [
        # Level 1 depends on Ankh
        (Theme.TIDE_POOL, 1, False, False, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (
            Theme.TIDE_POOL,
            1,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # Level 2 might have collected Excalibur or not
        (Theme.TIDE_POOL, 2, False, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (
            Theme.TIDE_POOL,
            2,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        (
            Theme.TIDE_POOL,
            2,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # Level 3 depends on Excalibur
        (Theme.TIDE_POOL, 3, True, False, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (
            Theme.TIDE_POOL,
            3,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # Level 4 depends on Abzu
        (Theme.TIDE_POOL, 4, True, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (Theme.TIDE_POOL, 4, True, True, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (Theme.ABZU, 4, True, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
    ],
)
def test_is_chain_tide_pool(
    theme,
    level,
    had_ankh,
    held_world4_chain_item,
    prev_chain_status,
    expected_chain_status,
):
    run_state = RunState()
    run_state.had_udjat_eye = False
    run_state.had_world2_chain_headwear = True
    run_state.had_ankh = had_ankh
    run_state.held_world4_chain_item = held_world4_chain_item
    run_state.chain_status = prev_chain_status

    world = 4
    win_state = WinState.NO_WIN
    run_state.update_is_chain(world, level, theme, win_state)

    assert run_state.chain_status == expected_chain_status


@pytest.mark.parametrize(
    # These tests focus on transitions. Once we've established a steady failed state, we stop bothering
    "theme,level,had_ankh,held_world4_chain_item,prev_chain_status,expected_chain_status",
    [
        # Level 1 depends on Ankh. Might have collected the scepter or not
        (Theme.TEMPLE, 1, False, False, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (
            Theme.TEMPLE,
            1,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        (Theme.TEMPLE, 1, True, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
        # Level 2 depends on scepter
        (Theme.TEMPLE, 2, False, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (Theme.TEMPLE, 2, True, False, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (Theme.TEMPLE, 2, True, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
        # Level 3 depends on CoG
        (Theme.TEMPLE, 3, True, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (Theme.TEMPLE, 3, True, True, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (
            Theme.CITY_OF_GOLD,
            3,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # Level 4 depends on Duat
        (Theme.TEMPLE, 4, True, True, ChainStatus.FAILED, ChainStatus.FAILED),
        (Theme.TEMPLE, 4, True, True, ChainStatus.IN_PROGRESS, ChainStatus.FAILED),
        (Theme.DUAT, 4, True, True, ChainStatus.IN_PROGRESS, ChainStatus.IN_PROGRESS),
    ],
)
def test_is_chain_temple(
    theme,
    level,
    had_ankh,
    held_world4_chain_item,
    prev_chain_status,
    expected_chain_status,
):
    run_state = RunState()
    run_state.had_udjat_eye = False
    run_state.had_world2_chain_headwear = True
    run_state.had_ankh = had_ankh
    run_state.held_world4_chain_item = held_world4_chain_item
    run_state.chain_status = prev_chain_status

    world = 4
    win_state = WinState.NO_WIN
    run_state.update_is_chain(world, level, theme, win_state)

    assert run_state.chain_status == expected_chain_status


@pytest.mark.parametrize(
    # These tests focus on transitions. Once we've established a steady failed state, we stop bothering
    "world,level,win_state,had_tablet_of_destiny,held_ushabti,prev_chain_status,expected_chain_status",
    [
        # Ice Caves depends on Tablet
        (5, 1, WinState.NO_WIN, False, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (
            5,
            1,
            WinState.NO_WIN,
            False,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.FAILED,
        ),
        (
            5,
            1,
            WinState.NO_WIN,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # 6-1 is steady
        (6, 1, WinState.NO_WIN, False, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (
            6,
            1,
            WinState.NO_WIN,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # 6-2 may or may not have collected Ushabti
        (
            6,
            2,
            WinState.NO_WIN,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        (
            6,
            2,
            WinState.NO_WIN,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # 6-3 depends on Ushabti
        (
            6,
            3,
            WinState.NO_WIN,
            True,
            False,
            ChainStatus.IN_PROGRESS,
            ChainStatus.FAILED,
        ),
        (
            6,
            3,
            WinState.NO_WIN,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # 6-4 depends on win-state
        (6, 4, WinState.NO_WIN, True, False, ChainStatus.FAILED, ChainStatus.FAILED),
        (
            6,
            4,
            WinState.TIAMAT,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.FAILED,
        ),
        (
            6,
            4,
            WinState.NO_WIN,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
        # 7-1 onward should be steady-state
        (
            7,
            1,
            WinState.NO_WIN,
            True,
            True,
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
        ),
    ],
)
def test_is_chain_post_world4(
    world,
    level,
    win_state,
    had_tablet_of_destiny,
    held_ushabti,
    prev_chain_status,
    expected_chain_status,
):
    run_state = RunState()
    run_state.had_udjat_eye = False
    run_state.had_world2_chain_headwear = True
    run_state.had_ankh = True
    run_state.held_world4_chain_item = True
    run_state.had_tablet_of_destiny = had_tablet_of_destiny
    run_state.held_ushabti = held_ushabti
    run_state.chain_status = prev_chain_status

    theme = Theme.ICE_CAVES  # bogus, but we don't look at it
    run_state.update_is_chain(world, level, theme, win_state)

    assert run_state.chain_status == expected_chain_status


@pytest.mark.parametrize(
    "item_set,hou_yis_bow,expectd_clone_gun_wo_bow,expected_millionaire",
    [
        (set(), False, False, False),
        (set(), True, False, False),
        ({EntityType.ITEM_CLONEGUN}, True, False, False),
        ({EntityType.ITEM_CLONEGUN}, False, True, True),
    ],
)
def test_millionaire_clone_gun_wo_bow(
    item_set, hou_yis_bow, expectd_clone_gun_wo_bow, expected_millionaire
):
    run_state = RunState()
    run_state.hou_yis_bow = hou_yis_bow
    run_state.update_millionaire(State(), Inventory(), item_set)

    assert run_state.clone_gun_wo_bow == expectd_clone_gun_wo_bow

    is_millionaire = Label.MILLIONAIRE in run_state.run_label._set
    assert is_millionaire == expected_millionaire


@pytest.mark.parametrize(
    "money_shop_total,win_state,money,collected_money_total,clone_gun_wo_bow,expected_millionaire",
    [
        # Varying amounts of money collected
        (0, WinState.NO_WIN, 0, 0, False, False),
        (0, WinState.NO_WIN, 900_000, 0, False, True),
        (0, WinState.NO_WIN, 899_999, 1, False, True),
        (0, WinState.NO_WIN, 1, 899_999, False, True),
        # Bought something
        (-2_500, WinState.NO_WIN, 0, 0, False, False),
        (-2_500, WinState.NO_WIN, 900_000, 10, False, False),
        (-2_500, WinState.NO_WIN, 900_000, 2_500, False, True),
        # With the clone gun, money amounts don't matter before winning
        (0, WinState.NO_WIN, 0, 0, True, True),
        (0, WinState.NO_WIN, 900_000, 0, True, True),
        (-5_000, WinState.NO_WIN, 900_000, 0, True, True),
        # Before statue drops on score screen we don't have the bonus, and that's OK
        (0, WinState.TIAMAT, 900_000, 0, False, True),
        (100_000, WinState.TIAMAT, 900_000, 0, False, True),
        # Winning make the clone gun irrelevant
        (0, WinState.TIAMAT, 899_999, 0, True, False),
        (0, WinState.TIAMAT, 900_000, 0, True, True),
        (100_000, WinState.TIAMAT, 900_000, 0, True, True),
    ],
)
def test_millionaire_(
    money_shop_total,
    win_state,
    money,
    collected_money_total,
    clone_gun_wo_bow,
    expected_millionaire,
):
    run_state = RunState()
    run_state.clone_gun_wo_bow = clone_gun_wo_bow
    if clone_gun_wo_bow:
        # This would have been added on a previous update
        run_state.run_label.add(Label.MILLIONAIRE)

    game_state = State(money_shop_total=money_shop_total, win_state=win_state)
    inventory = Inventory(money=money, collected_money_total=collected_money_total)
    item_set = set()
    run_state.update_millionaire(game_state, inventory, item_set)

    is_millionaire = Label.MILLIONAIRE in run_state.run_label._set
    assert is_millionaire == expected_millionaire


@pytest.mark.parametrize(
    "world,theme,ropes,prev_health,expected_level_start_ropes,expected_health",
    [
        # Level start ropes
        (2, Theme.JUNGLE, 4, 4, 4, 4),
        (2, Theme.VOLCANA, 2, 3, 2, 3),
        # Duat health adjustment
        (4, Theme.DUAT, 5, 2, 5, 4),
        (4, Theme.DUAT, 5, 4, 5, 4),
        (4, Theme.DUAT, 5, 10, 5, 4),
    ],
)
def test_on_level_start_state(
    world, theme, ropes, prev_health, expected_level_start_ropes, expected_health
):
    run_state = RunState()
    run_state.level_started = True
    run_state.health = prev_health

    run_state.update_on_level_start(world, theme, ropes)

    assert run_state.level_start_ropes == expected_level_start_ropes
    assert run_state.health == expected_health


@pytest.mark.parametrize(
    "world,theme,mc_has_swung_mattock,hou_yis_bow,expected_low",
    [
        # Bow isn't needed in world 2
        (2, Theme.VOLCANA, False, False, True),
        (2, Theme.VOLCANA, True, False, True),
        (2, Theme.VOLCANA, True, True, True),
        # Bow required if mattock was swung in Moon Challenge
        (3, Theme.OLMEC, False, False, True),
        (3, Theme.OLMEC, True, False, False),
        (3, Theme.OLMEC, True, True, True),
    ],
)
def test_on_level_start_low(
    world, theme, mc_has_swung_mattock, hou_yis_bow, expected_low
):
    run_state = RunState()
    run_state.level_started = True
    run_state.mc_has_swung_mattock = mc_has_swung_mattock
    run_state.hou_yis_bow = hou_yis_bow

    ropes = 4
    run_state.update_on_level_start(world, theme, ropes)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low
