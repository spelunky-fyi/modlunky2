from operator import ne
import pytest
from modlunky2.category.chain.testing import FakeStepper
from modlunky2.mem.entities import (
    CharState,
    Entity,
    EntityDBEntry,
    EntityType,
    Illumination,
    Inventory,
    Layer,
    LightEmitter,
    Mount,
    Movable,
    Player,
)
from modlunky2.mem.memrauder.model import MemContext, PolyPointer
from modlunky2.mem.state import (
    HudFlags,
    PresenceFlags,
    RunRecapFlags,
    Screen,
    State,
    Theme,
    WinState,
)
from modlunky2.mem.testing import (
    EntityMapBuilder,
    poly_pointer_no_mem,
    trivial_poly_entities,
)
from modlunky2.ui.trackers.label import Label, RunLabel
from modlunky2.ui.trackers.runstate import (
    ChainStatus,
    PlayerMotion,
    RunState,
    time_to_frames,
)

# pylint: disable=protected-access,too-many-lines


@pytest.mark.parametrize(
    "label,recap_flag,method",
    [
        (Label.PACIFIST, RunRecapFlags.PACIFIST, RunState.update_pacifist),
        (Label.NO_GOLD, RunRecapFlags.NO_GOLD, RunState.update_no_gold),
        (Label.NO, RunRecapFlags.NO_GOLD, RunState.update_no_gold),
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
    "item_set,prev_item_set,expected_could_tp",
    [
        ({EntityType.ITEM_TELEPORTER}, set(), True),
        # Telepack may have exploded
        (set(), {EntityType.ITEM_TELEPORTER_BACKPACK}, True),
        ({EntityType.ITEM_POWERUP_COMPASS}, set(), False),
        (set(), set(), False),
    ],
)
def test_could_tp_items(item_set, prev_item_set, expected_could_tp):
    run_state = RunState()
    assert run_state.could_tp(Player(), item_set, prev_item_set) == expected_could_tp


@pytest.mark.parametrize(
    "mount_type,expected_could_tp",
    [
        (EntityType.MOUNT_QILIN, False),
        (EntityType.MOUNT_AXOLOTL, True),
    ],
)
def test_could_tp_mount(mount_type, expected_could_tp):
    mount = Mount(type=EntityDBEntry(id=mount_type))
    poly_mount = PolyPointer(101, mount, MemContext())
    player = Player(overlay=poly_mount)

    run_state = RunState()
    assert run_state.could_tp(player, set(), set()) == expected_could_tp


def test_compute_player_motion_wo_overlay():
    player = Player(position_x=5, position_y=7, velocity_x=-1, velocity_y=-3)
    expected_motion = PlayerMotion(
        position_x=5, position_y=7, velocity_x=-1, velocity_y=-3
    )
    run_state = RunState()
    assert run_state.compute_player_motion(player) == expected_motion


def test_compute_player_motion_mount():
    mount = Mount(
        type=EntityDBEntry(id=EntityType.MOUNT_TURKEY),
        position_x=18,
        position_y=13,
        velocity_x=-2,
        velocity_y=-7,
    )
    poly_mount = PolyPointer(101, mount, MemContext())
    player = Player(
        position_x=5, position_y=7, velocity_x=-1, velocity_y=-3, overlay=poly_mount
    )
    expected_motion = PlayerMotion(
        position_x=18, position_y=13, velocity_x=-2, velocity_y=-7
    )
    run_state = RunState()
    assert run_state.compute_player_motion(player) == expected_motion


def test_compute_player_motion_active_floor():
    elevator = Movable(
        type=EntityDBEntry(id=EntityType.ACTIVEFLOOR_ELEVATOR),
        position_x=0.5,
        position_y=0.7,
        velocity_x=-0.1,
        velocity_y=-0.3,
    )
    poly_elevator = PolyPointer(101, elevator, MemContext())
    player = Player(
        position_x=5, position_y=7, velocity_x=-1, velocity_y=-3, overlay=poly_elevator
    )
    expected_motion = PlayerMotion(
        position_x=5.5, position_y=7.7, velocity_x=-1.1, velocity_y=-3.3
    )
    run_state = RunState()
    assert run_state.compute_player_motion(player) == expected_motion


def test_compute_player_motion_mount_and_active_floor():
    elevator = Movable(
        type=EntityDBEntry(id=EntityType.ACTIVEFLOOR_ELEVATOR),
        position_x=0.5,
        position_y=0.7,
        velocity_x=-0.1,
        velocity_y=-0.3,
    )
    poly_elevator = PolyPointer(101, elevator, MemContext())
    # Turkey on an elevator
    mount = Mount(
        type=EntityDBEntry(id=EntityType.MOUNT_TURKEY),
        position_x=18,
        position_y=13,
        velocity_x=-2,
        velocity_y=-7,
        overlay=poly_elevator,
    )
    poly_mount = PolyPointer(102, mount, MemContext())
    player = Player(
        position_x=5, position_y=7, velocity_x=-1, velocity_y=-3, overlay=poly_mount
    )
    expected_motion = PlayerMotion(
        position_x=18.5, position_y=13.7, velocity_x=-2.1, velocity_y=-7.3
    )
    run_state = RunState()
    assert run_state.compute_player_motion(player) == expected_motion


@pytest.mark.parametrize(
    "player_x,player_y,player_vx,player_vy,idle_counter,shadow_x,shadow_y,expected_no_tp",
    [
        (5, 8, 0, 0, 0, 5.1, 8.2, False),
        (10.5, 1.5, 0.2, 0.3, 1, 10, 1, False),
        (19.5, 9.5, 0.2, 0.3, 3, 18.5, 8.5, False),
        (1, 2, 0, 0, 0, 7, 9, True),
        (11.5, 3.5, 0.2, 0.3, 2, 11, 2, True),
        (13.5, 3.5, 0.3, 0.2, 2, 13, 4, True),
        (1, 2, 0, 0, 0, 7, 9, True),
    ],
)
def test_no_tp(
    player_x,
    player_y,
    player_vx,
    player_vy,
    idle_counter,
    shadow_x,
    shadow_y,
    expected_no_tp,
):
    fx_shadow_type = EntityDBEntry(id=EntityType.FX_TELEPORTSHADOW)
    new_entities = []
    src_shadow = LightEmitter(
        type=fx_shadow_type, idle_counter=idle_counter, emitted_light=Illumination()
    )
    new_entities.append(poly_pointer_no_mem(src_shadow))

    dest_illumination = Illumination(light_pos_x=shadow_x, light_pos_y=shadow_y)
    dest_shadow = LightEmitter(
        type=fx_shadow_type, idle_counter=idle_counter, emitted_light=dest_illumination
    )
    new_entities.append(poly_pointer_no_mem(dest_shadow))

    player = Player(
        position_x=player_x,
        position_y=player_y,
        velocity_x=player_vx,
        velocity_y=player_vy,
    )
    item_set = {EntityType.ITEM_TELEPORTER_BACKPACK}
    prev_item_set = set()

    run_state = RunState()
    run_state.new_entities = new_entities
    run_state.update_no_tp(player, item_set, prev_item_set)

    is_no_tp = Label.NO_TELEPORTER in run_state.run_label._set
    assert is_no_tp == expected_no_tp


@pytest.mark.parametrize(
    "item_set,expected_score",
    [
        ({EntityType.ITEM_POWERUP_EGGPLANTCROWN}, False),
        ({EntityType.ITEM_PLASMACANNON}, True),
        ({EntityType.ITEM_PLASMACANNON}, True),
        (set(), False),
        (set(), False),
    ],
)
def test_score_items(item_set, expected_score):
    run_state = RunState()
    run_state.update_score_items(item_set)

    is_score = Label.SCORE in run_state.run_label._set
    assert is_score == expected_score


@pytest.mark.parametrize(
    "level_started,theme,world_start,level_start,expected_ice_caves",
    [
        (False, Theme.ICE_CAVES, 5, 1, False),
        (True, Theme.NEO_BABYLON, 5, 1, False),
        (True, Theme.ICE_CAVES, 1, 1, False),
        (True, Theme.ICE_CAVES, 5, 1, True),
    ],
)
def test_ice_caves(level_started, theme, world_start, level_start, expected_ice_caves):
    game_state = State(theme=theme, world_start=world_start, level_start=level_start)

    run_state = RunState()
    run_state.level_started = level_started
    run_state.update_ice_caves(game_state)

    is_ice_caves = Label.ICE_CAVES_SHORTCUT in run_state.run_label._set
    assert is_ice_caves == expected_ice_caves


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
    run_state.sunken_chain_status = chain_status
    run_state.update_has_mounted_tame(theme, poly_mount)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "char_state,prev_health,cur_health,expected_low,expected_no",
    [
        (CharState.STANDING, 4, 4, True, True),
        (CharState.STANDING, 2, 1, True, False),
        (CharState.STANDING, 3, 1, True, False),
        (CharState.DYING, 1, 4, True, True),
        (CharState.STANDING, 1, 2, False, False),
        (CharState.STANDING, 2, 4, False, False),
        (CharState.STANDING, 5, 5, False, False),
    ],
)
def test_starting_resources_health(
    char_state, prev_health, cur_health, expected_low, expected_no
):
    run_state = RunState()
    run_state.health = prev_health

    player = Player(state=char_state, health=cur_health)
    run_state.update_starting_resources(player, WinState.NO_WIN)
    assert run_state.health == cur_health

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low

    is_no = Label.NO in run_state.run_label._set
    assert is_no == expected_no


@pytest.mark.parametrize(
    "prev_bombs,cur_bombs,expected_low,expected_no",
    [
        (4, 4, True, True),
        (4, 3, True, False),
        (3, 1, True, False),
        (7, 7, False, False),
        (1, 4, False, False),
    ],
)
def test_starting_resources_bombs(prev_bombs, cur_bombs, expected_low, expected_no):
    run_state = RunState()
    run_state.bombs = prev_bombs

    inventory = Inventory(bombs=cur_bombs)
    player = Player(inventory=inventory)
    run_state.update_starting_resources(player, WinState.NO_WIN)

    assert run_state.bombs == cur_bombs

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low

    is_no = Label.NO in run_state.run_label._set
    assert is_no == expected_no


@pytest.mark.parametrize(
    "level_start_ropes,prev_ropes,cur_ropes,win_state,expected_low,expected_no",
    [
        (4, 4, 4, WinState.NO_WIN, True, True),
        # This rope loss might be temporary
        (4, 4, 3, WinState.NO_WIN, True, True),
        # This rope loss is permanent
        (4, 4, 3, WinState.TIAMAT, True, False),
        (3, 3, 1, WinState.NO_WIN, True, True),
        (3, 2, 3, WinState.NO_WIN, True, True),
        (7, 7, 7, WinState.NO_WIN, False, False),
        (1, 1, 4, WinState.NO_WIN, False, False),
    ],
)
def test_starting_resources_ropes(
    level_start_ropes, prev_ropes, cur_ropes, win_state, expected_low, expected_no
):
    run_state = RunState()
    run_state.level_start_ropes = level_start_ropes
    run_state.ropes = prev_ropes

    inventory = Inventory(ropes=cur_ropes)
    player = Player(inventory=inventory)
    run_state.update_starting_resources(player, win_state)

    assert run_state.ropes == cur_ropes

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low

    is_no = Label.NO in run_state.run_label._set
    assert is_no == expected_no


@pytest.mark.parametrize(
    "player_state,prev_poisoned,item_set,expected_poisoned,expected_low",
    [
        (CharState.STANDING, False, {EntityType.LOGICAL_POISONED_EFFECT}, True, True),
        (CharState.STANDING, True, {EntityType.LOGICAL_POISONED_EFFECT}, True, True),
        (CharState.STANDING, True, set(), False, False),
        (CharState.DYING, True, set(), False, True),
        # We should skip checks during weird states
        (CharState.ENTERING, True, set(), True, True),
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
    "time_level,hud_flags,ghost_spawned,cursed,expected_low",
    [
        # No clover
        (time_to_frames(1, 0), 0, False, False, True),
        (time_to_frames(4, 0), 0, False, False, True),
        (time_to_frames(4, 0), ~HudFlags.HAVE_CLOVER, False, False, True),
        # Not cursed
        (time_to_frames(2, 45), HudFlags.HAVE_CLOVER, False, False, True),
        (time_to_frames(4, 0), HudFlags.HAVE_CLOVER, False, False, False),
        # Cursed
        (time_to_frames(2, 15), HudFlags.HAVE_CLOVER, False, True, True),
        (time_to_frames(2, 45), HudFlags.HAVE_CLOVER, False, True, False),
        # Ghost already spawned
        (time_to_frames(4, 0), HudFlags.HAVE_CLOVER, True, False, True),
        (time_to_frames(4, 0), HudFlags.HAVE_CLOVER, True, True, True),
    ],
)
def test_had_clover_time(time_level, hud_flags, ghost_spawned, cursed, expected_low):
    run_state = RunState()
    run_state.ghost_spawned = ghost_spawned
    run_state.cursed = cursed
    run_state.update_had_clover(time_level, hud_flags)

    is_low = Label.LOW in run_state.run_label._set
    assert is_low == expected_low


@pytest.mark.parametrize(
    "level_started,ghost_spawned,new_entities,expected_ghost_spawned",
    [
        # Nothing changed
        (False, False, [], False),
        (False, True, [], True),
        # Reset at start of level
        (True, True, [], False),
        (True, False, [], False),
        # If we see a ghost, it's spawned
        (False, False, [EntityType.MONS_GHOST], True),
        (False, True, [EntityType.MONS_GHOST], True),
        (True, False, [EntityType.MONS_GHOST], True),
        (True, True, [EntityType.MONS_GHOST], True),
    ],
)
@pytest.mark.parametrize(
    "time_level", [time_to_frames(0, 0), time_to_frames(1, 0), time_to_frames(5, 0)]
)
@pytest.mark.parametrize("hud_flags", [0, HudFlags.HAVE_CLOVER])
def test_had_clover_ghost_spawned(
    time_level,
    hud_flags,
    level_started,
    ghost_spawned,
    new_entities,
    expected_ghost_spawned,
):
    time_level = time_to_frames(0, 0)
    hud_flags = 0
    run_state = RunState()
    run_state.level_started = level_started
    run_state.ghost_spawned = ghost_spawned
    run_state.new_entities = trivial_poly_entities(new_entities)
    run_state.update_had_clover(time_level, hud_flags)

    assert run_state.ghost_spawned == expected_ghost_spawned


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
    "chain_status,item_set,expected_had_ankh,expected_low",
    [
        # These are fine while chain is in-progress
        (ChainStatus.IN_PROGRESS, {EntityType.ITEM_POWERUP_ANKH}, True, True),
        (
            ChainStatus.IN_PROGRESS,
            {EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            False,
            True,
        ),
        # If a chain isn't in progress, we should fail immediately
        (ChainStatus.UNSTARTED, {EntityType.ITEM_POWERUP_ANKH}, True, False),
        (
            ChainStatus.UNSTARTED,
            {EntityType.ITEM_POWERUP_TABLETOFDESTINY},
            False,
            False,
        ),
        (ChainStatus.FAILED, {EntityType.ITEM_POWERUP_ANKH}, True, False),
        (ChainStatus.FAILED, {EntityType.ITEM_POWERUP_TABLETOFDESTINY}, False, False),
    ],
)
def test_has_chain_powerup(chain_status, item_set, expected_had_ankh, expected_low):
    run_state = RunState()
    run_state.sunken_chain_status = chain_status
    run_state.update_has_chain_powerup(item_set)

    assert run_state.had_ankh == expected_had_ankh

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
        # Having more than one isn't OK either
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
    "prev_state,cur_state,prev_item_set,item_set,expected_low",
    [
        (
            CharState.STANDING,
            CharState.ATTACKING,
            {EntityType.ITEM_BOOMERANG},
            {},
            False,
        ),
        (
            CharState.ATTACKING,
            CharState.STANDING,
            {},
            {EntityType.ITEM_BOOMERANG},
            False,
        ),
        # Holding things is OK
        (
            CharState.JUMPING,
            CharState.CLIMBING,
            {EntityType.ITEM_BOOMERANG},
            {EntityType.ITEM_BOOMERANG},
            True,
        ),
        # Using the whip is OK
        (CharState.JUMPING, CharState.CLIMBING, set(), set(), True),
        (CharState.STANDING, CharState.ATTACKING, set(), set(), True),
        (CharState.ATTACKING, CharState.STANDING, set(), set(), True),
    ],
)
def test_attacked_with_simple(
    prev_state, cur_state, item_set, prev_item_set, expected_low
):
    # These shouldn't be location sensitive
    layer = Layer.FRONT
    world = 2
    level = 2
    theme = Theme.JUNGLE
    presence_flags = 0
    run_state = RunState()
    run_state.sunken_chain_status = ChainStatus.IN_PROGRESS
    run_state.update_attacked_with(
        prev_state,
        cur_state,
        layer,
        world,
        level,
        theme,
        presence_flags,
        item_set,
        prev_item_set,
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
    run_state.sunken_chain_status = chain_status
    run_state.update_attacked_with(
        prev_state,
        cur_state,
        layer,
        world,
        level,
        theme,
        presence_flags,
        item_set,
        item_set,
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
        prev_state,
        cur_state,
        layer,
        world,
        level,
        theme,
        presence_flags,
        item_set,
        item_set,
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
        prev_state,
        cur_state,
        layer,
        world,
        level,
        theme,
        presence_flags,
        item_set,
        item_set,
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
            True,
        ),
        (
            CharState.STANDING,
            CharState.THROWING,
            set(),
            {EntityType.ITEM_LIGHT_ARROW},
            True,
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
    "world,theme,world2_theme,starting_labels,expected_label,",
    [
        # Volcana "plain" and V/T
        (2, Theme.VOLCANA, None, {Label.ANY}, None),
        (2, Theme.TIDE_POOL, Theme.VOLCANA, {Label.ANY}, None),
        (2, Theme.TEMPLE, Theme.VOLCANA, {Label.ANY}, Label.VOLCANA_TEMPLE),
        # We eagerly assume J/T
        (2, Theme.JUNGLE, None, {Label.ANY}, Label.JUNGLE_TEMPLE),
        (
            2,
            Theme.JUNGLE,
            Theme.JUNGLE,
            {Label.ANY},
            Label.JUNGLE_TEMPLE,
        ),
        (
            2,
            Theme.JUNGLE,
            Theme.JUNGLE,
            {Label.SUNKEN_CITY},
            Label.JUNGLE_TEMPLE,
        ),
        # We actually went J/T
        (
            4,
            Theme.TEMPLE,
            Theme.JUNGLE,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            Label.JUNGLE_TEMPLE,
        ),
        (
            4,
            Theme.TEMPLE,
            Theme.JUNGLE,
            {Label.JUNGLE_TEMPLE, Label.SUNKEN_CITY},
            Label.JUNGLE_TEMPLE,
        ),
        (
            4,
            Theme.TEMPLE,
            Theme.JUNGLE,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            Label.JUNGLE_TEMPLE,
        ),
        # We went Jungle, but J/T is now impossible
        (
            4,
            Theme.TIDE_POOL,
            Theme.JUNGLE,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            None,
        ),
        (
            4,
            Theme.TIDE_POOL,
            Theme.JUNGLE,
            {Label.JUNGLE_TEMPLE, Label.SUNKEN_CITY},
            None,
        ),
        (
            4,
            Theme.TIDE_POOL,
            Theme.JUNGLE,
            {Label.JUNGLE_TEMPLE, Label.ANY},
            None,
        ),
    ],
)
def test_world_themes_label(
    world,
    theme,
    world2_theme,
    starting_labels,
    expected_label,
):
    run_state = RunState()
    run_state.run_label = RunLabel(starting=starting_labels)
    run_state.world2_theme = world2_theme
    run_state.update_world_themes(world, theme)

    if expected_label is Label.JUNGLE_TEMPLE:
        assert Label.JUNGLE_TEMPLE in run_state.run_label._set
    if expected_label is Label.VOLCANA_TEMPLE:
        assert Label.VOLCANA_TEMPLE in run_state.run_label._set
    if expected_label is None:
        assert Label.JUNGLE_TEMPLE not in run_state.run_label._set
        assert Label.VOLCANA_TEMPLE not in run_state.run_label._set


@pytest.mark.parametrize(
    "world,win_state,final_death,had_ankh,sunken_status,eggplant_status,cosmic_status,expected_terminus",
    [
        (
            2,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.ANY,
        ),
        (
            1,
            WinState.NO_WIN,
            True,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.DEATH,
        ),
        (
            3,
            WinState.NO_WIN,
            False,  # final_death
            True,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.SUNKEN_CITY,
        ),
        (
            2,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.IN_PROGRESS,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.SUNKEN_CITY,
        ),
        (
            1,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.IN_PROGRESS,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.SUNKEN_CITY,
        ),
        (
            2,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.IN_PROGRESS,  # cosmic_status
            Label.COSMIC_OCEAN,
        ),
        # We're in Sunken City, so we must be doing Sunken City
        (
            7,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.FAILED,  # sunken_status
            ChainStatus.IN_PROGRESS,  # eggplant_status
            ChainStatus.FAILED,  # cosmic_status
            Label.SUNKEN_CITY,
        ),
        (
            7,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.FAILED,  # sunken_status
            ChainStatus.FAILED,  # eggplant_status
            ChainStatus.FAILED,  # cosmic_status
            Label.SUNKEN_CITY,
        ),
        # We won via Hundun, so this is a SC run.
        # Note that world is set to 1 on the moon/victory screen
        (
            1,
            WinState.HUNDUN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.FAILED,  # sunken_status
            ChainStatus.IN_PROGRESS,  # eggplant_status
            ChainStatus.FAILED,  # cosmic_status
            Label.SUNKEN_CITY,
        ),
        # Cosmic Ocean has priority over Sunken City, even in SC
        (
            7,
            WinState.NO_WIN,
            True,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.IN_PROGRESS,  # cosmic_status
            Label.COSMIC_OCEAN,
        ),
        # We won via Cosmic Ocean. This must be CO
        (
            8,
            WinState.COSMIC_OCEAN,
            True,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.IN_PROGRESS,  # cosmic_status
            Label.COSMIC_OCEAN,
        ),
        # Cosmic Ocean has priority over Death
        (
            2,
            WinState.NO_WIN,
            True,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.IN_PROGRESS,  # cosmic_status
            Label.COSMIC_OCEAN,
        ),
        # Cosmic Ocean has priority over Death
        (
            3,
            WinState.NO_WIN,
            False,  # final_death
            False,  # had_ankh
            ChainStatus.IN_PROGRESS,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.IN_PROGRESS,  # cosmic_status
            Label.COSMIC_OCEAN,
        ),
        # Death has priority over Sunken City
        (
            2,
            WinState.NO_WIN,
            True,  # final_death
            False,  # had_ankh
            ChainStatus.IN_PROGRESS,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.DEATH,
        ),
        # Death has priority over Any%
        (
            2,
            WinState.NO_WIN,
            True,  # final_death
            False,  # had_ankh
            ChainStatus.UNSTARTED,  # sunken_status
            ChainStatus.UNSTARTED,  # eggplant_status
            ChainStatus.UNSTARTED,  # cosmic_status
            Label.DEATH,
        ),
    ],
)
def test_update_terminus(
    world,
    win_state,
    final_death,
    had_ankh,
    sunken_status,
    eggplant_status,
    cosmic_status,
    expected_terminus,
):
    run_state = RunState()
    run_state.final_death = final_death
    run_state.had_ankh = had_ankh
    run_state.sunken_chain_status = sunken_status
    run_state.eggplant_stepper = FakeStepper(eggplant_status)
    run_state.cosmic_stepper = FakeStepper(cosmic_status)

    game_state = State(world=world, win_state=win_state)
    run_state.update_terminus(game_state)

    assert run_state.run_label._terminus == expected_terminus


@pytest.mark.parametrize(
    "abzu_chain_status,duat_chain_status,expected_abzu,expected_duat,expected_sunken_chain_status",
    [
        (
            ChainStatus.UNSTARTED,
            ChainStatus.UNSTARTED,
            False,
            False,
            ChainStatus.UNSTARTED,
        ),
        (
            ChainStatus.IN_PROGRESS,
            ChainStatus.IN_PROGRESS,
            False,
            False,
            ChainStatus.IN_PROGRESS,
        ),
        (
            ChainStatus.IN_PROGRESS,
            ChainStatus.FAILED,
            True,
            False,
            ChainStatus.IN_PROGRESS,
        ),
        (
            ChainStatus.FAILED,
            ChainStatus.IN_PROGRESS,
            False,
            True,
            ChainStatus.IN_PROGRESS,
        ),
        (ChainStatus.FAILED, ChainStatus.FAILED, False, False, ChainStatus.FAILED),
    ],
)
def test_is_chain(
    abzu_chain_status,
    duat_chain_status,
    expected_abzu,
    expected_duat,
    expected_sunken_chain_status,
):
    run_state = RunState()
    run_state.abzu_stepper = FakeStepper(abzu_chain_status)
    run_state.duat_stepper = FakeStepper(duat_chain_status)
    run_state.update_is_chain()

    is_abzu = Label.ABZU in run_state.run_label._set
    assert is_abzu == expected_abzu

    is_duat = Label.DUAT in run_state.run_label._set
    assert is_duat == expected_duat

    assert run_state.sunken_chain_status == expected_sunken_chain_status

    is_chain = Label.CHAIN in run_state.run_label._set
    assert is_chain == expected_sunken_chain_status.in_progress


@pytest.mark.parametrize(
    "item_set,cosmic_status,expected_clone_gun_wo_cosmic,expected_millionaire",
    [
        (set(), ChainStatus.UNSTARTED, False, False),
        (set(), ChainStatus.IN_PROGRESS, False, False),
        ({EntityType.ITEM_CLONEGUN}, ChainStatus.IN_PROGRESS, False, False),
        ({EntityType.ITEM_CLONEGUN}, ChainStatus.FAILED, True, True),
    ],
)
def test_millionaire_clone_gun_wo_bow(
    item_set, cosmic_status, expected_clone_gun_wo_cosmic, expected_millionaire
):
    run_state = RunState()
    run_state.cosmic_stepper = FakeStepper(cosmic_status)
    run_state.update_millionaire(State(), Inventory(), item_set)

    assert run_state.clone_gun_wo_cosmic == expected_clone_gun_wo_cosmic

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
    run_state.clone_gun_wo_cosmic = clone_gun_wo_bow
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
    "new_entity_types,theme,expected_no",
    [
        ([], Theme.DWELLING, True),
        ([EntityType.ITEM_ROPE], Theme.JUNGLE, True),
        ([EntityType.ITEM_CLIMBABLE_ROPE], Theme.TEMPLE, False),
        # Duat is exempt from this check
        ([EntityType.ITEM_CLIMBABLE_ROPE], Theme.DUAT, True),
    ],
)
def test_rope_deployed(new_entity_types, theme, expected_no):
    run_state = RunState()
    run_state.new_entities = trivial_poly_entities(new_entity_types)

    run_state.update_rope_deployed(theme)

    is_no = Label.NO in run_state.run_label._set
    assert is_no == expected_no


@pytest.mark.parametrize(
    "screen,level_started,entity_types,expected_entity_types",
    [
        (Screen.LEVEL, False, [EntityType.ITEM_WEBGUN], [EntityType.ITEM_WEBGUN]),
        (
            Screen.LEVEL,
            False,
            [EntityType.ITEM_JETPACK, EntityType.ITEM_TELEPORTER],
            [EntityType.ITEM_JETPACK, EntityType.ITEM_TELEPORTER],
        ),
        (
            Screen.LEVEL,
            False,
            [EntityType.ITEM_WOODEN_ARROW, EntityType.ITEM_WOODEN_ARROW],
            [EntityType.ITEM_WOODEN_ARROW, EntityType.ITEM_WOODEN_ARROW],
        ),
        (Screen.LEVEL, True, [EntityType.FX_TELEPORTSHADOW], []),
        (Screen.LEVEL_TRANSITION, False, [EntityType.CHAR_HIREDHAND], []),
    ],
)
def test_new_entities(screen, level_started, entity_types, expected_entity_types):
    run_state = RunState()
    run_state.level_started = level_started

    fake_entity_db = {}
    for entity_type in entity_types:
        if entity_type not in fake_entity_db:
            fake_entity_db[entity_type] = EntityDBEntry(id=entity_type)

    entity_map = EntityMapBuilder()
    run_state.prev_next_uid = entity_map.next_uid
    entity_map.add_trivial_entities(entity_types)

    game_state = State(
        screen=screen,
        next_entity_uid=entity_map.next_uid,
        instance_id_to_pointer=entity_map.build(),
    )
    run_state.update_new_entities(game_state)

    got_types = [e.value.type.id for e in run_state.new_entities]
    assert got_types == expected_entity_types


@pytest.mark.parametrize(
    "world,theme,ropes,prev_health,expected_level_start_ropes,expected_health,expected_no",
    [
        # Level start ropes
        (2, Theme.JUNGLE, 4, 4, 4, 4, True),
        (2, Theme.VOLCANA, 2, 3, 2, 3, False),
        # Duat health adjustment
        (4, Theme.DUAT, 5, 2, 5, 4, True),
        (4, Theme.DUAT, 5, 4, 5, 4, True),
        (4, Theme.DUAT, 5, 10, 5, 4, True),
    ],
)
def test_on_level_start_state(
    world,
    theme,
    ropes,
    prev_health,
    expected_level_start_ropes,
    expected_health,
    expected_no,
):
    run_state = RunState()
    run_state.level_started = True
    run_state.health = prev_health

    run_state.update_on_level_start(world, theme, ropes)

    assert run_state.level_start_ropes == expected_level_start_ropes
    assert run_state.health == expected_health

    is_no = Label.NO in run_state.run_label._set
    assert is_no == expected_no
