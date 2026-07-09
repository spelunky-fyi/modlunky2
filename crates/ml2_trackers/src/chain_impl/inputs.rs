//! `ChainInputs`: precomputed, lifetime-free snapshot of everything
//! the chain step functions actually query. Building this once per
//! evaluation tick lets chain steps be plain `fn(&ChainInputs) ->
//! ChainStepResult<ChainInputs>`, no lifetimes threaded through the
//! FSM machinery, no per-step process reads.
//!
//! The alternative shape (chains hold a `&State + &dyn ReadProcess`
//! context) fights Rust's fn-pointer type system because fn pointers
//! can't carry generic lifetime parameters through a `Step<C>` alias.
//! Precomputing is also nicer for testing: chains can be unit-tested
//! against a hand-built `ChainInputs` without any process at all.

use std::collections::HashSet;

use ml2_mem::{MemType, ReadProcess};

use crate::entity::{CharState, EntityDBEntry, EntityType, Layer, Player};
use crate::enums::{Screen, Theme, WinState};
use crate::flags::{HudFlags, PresenceFlags, QuestFlags, RunRecapFlags};
use crate::state::State;

/// Snapshot of just the `State` fields chains consult. Owned + Copy so
/// chain step functions can pattern-match on it without touching the
/// borrow checker.
#[derive(Debug, Clone, Copy)]
pub struct StateSnapshot {
    pub screen: Screen,
    pub screen_last: Screen,
    pub screen_next: Screen,
    pub world: u8,
    pub level: u8,
    pub world_start: u8,
    pub level_start: u8,
    pub theme: Theme,
    pub theme_start: Theme,
    pub win_state: WinState,
    pub run_recap_flags: RunRecapFlags,
    pub hud_flags: HudFlags,
    pub quest_flags: QuestFlags,
    pub presence_flags: PresenceFlags,
    pub level_count: u8,
    pub time_total: u32,
    pub time_level: u32,
    pub time_last_level: u32,
    pub time_tutorial: u32,
    /// Signed on the wire because shop losses + leprechaun theft push
    /// it negative during a run; on victory a bonus lands on top.
    pub money_shop_total: i32,
    pub next_entity_uid: u32,
    pub loading: crate::enums::LoadingState,
    /// Monotonically-increasing frame counter since the game process
    /// launched. Used by TimerTracker for the "session" timer.
    pub time_startup: u32,
}

impl StateSnapshot {
    pub fn from_state(state: &State) -> Self {
        Self {
            screen: state.screen,
            screen_last: state.screen_last,
            screen_next: state.screen_next,
            world: state.world,
            level: state.level,
            world_start: state.world_start,
            level_start: state.level_start,
            theme: state.theme,
            theme_start: state.theme_start,
            win_state: state.win_state,
            run_recap_flags: state.run_recap_flags,
            hud_flags: state.hud_flags,
            quest_flags: state.quest_flags,
            presence_flags: state.presence_flags,
            level_count: state.level_count,
            time_total: state.time_total,
            time_level: state.time_level,
            time_last_level: state.time_last_level,
            time_tutorial: state.time_tutorial,
            money_shop_total: state.money_shop_total,
            next_entity_uid: state.next_entity_uid,
            loading: state.loading,
            time_startup: state.time_startup,
        }
    }

    pub fn world_level(&self) -> (u8, u8) {
        (self.world, self.level)
    }
}

/// Player 0's important fields snapshotted from the process. RunState
/// keeps this owned so subsequent method calls don't need process
/// references.
#[derive(Debug, Clone, Copy)]
pub struct PlayerSnapshot {
    pub health: i8,
    pub state: CharState,
    pub last_state: CharState,
    pub layer: u8,
    pub position_x: f32,
    pub position_y: f32,
    pub velocity_x: f32,
    pub velocity_y: f32,
    pub inventory: InventorySnapshot,
    /// Present when the player is holding / mounted on something. The
    /// full overlay chain is only walked lazily when RunState needs
    /// TP-shadow motion tracking; this snapshot carries just the
    /// top-level type + is-mount hint.
    pub overlay_type: Option<EntityType>,
    /// True iff the overlay is a mount AND that mount is tamed. Used
    /// by low% for the "riding a tamed mount fails low%" check.
    pub overlay_tamed_mount: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct InventorySnapshot {
    pub money: u32,
    pub bombs: u8,
    pub ropes: u8,
    pub kills_total: u32,
    pub collected_money_total: u32,
    pub cursed: bool,
}

impl PlayerSnapshot {
    pub fn layer_enum(&self) -> Layer {
        if self.layer == 0 {
            Layer::Front
        } else {
            Layer::Back
        }
    }
}

/// Player position + velocity after collapsing the overlay chain
/// (mount, active floor, etc). TP-shadow detection extrapolates from
/// this back to the frame the shadow spawned to compare positions.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PlayerMotion {
    pub position_x: f32,
    pub position_y: f32,
    pub velocity_x: f32,
    pub velocity_y: f32,
}

impl PlayerMotion {
    /// Linear extrapolation `num_frames` from the current position.
    /// Negative values project backwards; TP shadow detection uses
    /// `-shadow.idle_counter` to reach the shadow's spawn frame.
    pub fn extrapolate(&self, num_frames: f32) -> (f32, f32) {
        (
            self.position_x + self.velocity_x * num_frames,
            self.position_y + self.velocity_y * num_frames,
        )
    }
}

/// Precomputed inputs for a single chain evaluation. Chains read only
/// what's here; the RunState builder is the single place that reaches
/// into the process to fill it in.
#[derive(Debug, Clone)]
pub struct ChainInputs {
    pub state: StateSnapshot,
    /// Fixed 99-slot waddler storage. Kept as a `HashSet` so
    /// `.contains()` is O(1) even though the source array is small.
    pub waddler_storage: HashSet<EntityType>,
    /// Items player 0 currently carries (Inventory + held item). Union
    /// of the player's `items` vector plus the `holding_uid` target if
    /// present.
    pub player_items: HashSet<EntityType>,
    /// Every EntityType any companion currently holds. Precomputed so
    /// `some_companion_has_item(X)` is a set membership test.
    pub companion_held_items: HashSet<EntityType>,
    /// Type IDs of the companions themselves. `some_companion_is(X)`
    /// is a set membership test.
    pub companion_types: HashSet<EntityType>,
    /// Player 0's CharState when readable; None means the player
    /// pointer was null or the read failed. Chains use this for the
    /// "player-stunned" edge case in Duat's keep-ankh step.
    pub player0_char_state: Option<crate::entity::CharState>,
    /// Full player 0 snapshot when a run is active. RunState reads
    /// bombs/ropes/health/state/etc from here rather than the raw
    /// State (which doesn't hold Player fields directly).
    pub player0: Option<PlayerSnapshot>,
    /// Sum of `kills_total` across every player's inventory (the
    /// inline `Items.player_inventory[0..4]` block), so the Pacifist
    /// tracker reports co-op kill counts correctly and not just
    /// player 1's.
    pub all_players_kills_total: u32,
    /// Every non-zero `collected_money` entry across every player's
    /// inventory, flattened. The Gem tracker classifies each into
    /// diamond / colored / yem buckets; the Golf tracker just counts.
    /// Empty when Items hasn't been loaded yet this tick.
    pub all_players_collected_money: Vec<u32>,
    /// Copy of the game's UID -> Entity table header. RunState uses
    /// this together with `state.next_entity_uid` (from prev tick to
    /// current) to walk the entity-delta list without needing the
    /// tick task to hand off state manually.
    pub entity_map: crate::entity_map::UidEntityMap,
    /// Player 0 collapsed through its overlay chain (mounts, active
    /// floors) so TP-shadow detection can extrapolate backwards
    /// without re-walking pointers each frame. None when player 0
    /// isn't loaded (menus, torn read).
    pub player_motion: Option<PlayerMotion>,
    /// `state.theme_info.sub_theme_address` if theme_info is non-null
    /// and readable, else None. CO tracker looks this up in its
    /// address-to-theme LUT to identify each CO sub-theme.
    pub theme_info_sub_theme_address: Option<u64>,
}

impl ChainInputs {
    /// Convenience wrapper: `if inputs.some_companion_has_item(X)`.
    pub fn some_companion_has_item(&self, item: EntityType) -> bool {
        self.companion_held_items.contains(&item)
    }

    pub fn some_companion_is(&self, ty: EntityType) -> bool {
        self.companion_types.contains(&ty)
    }

    pub fn waddler_contains(&self, item: EntityType) -> bool {
        self.waddler_storage.contains(&item)
    }

    /// Builds a `ChainInputs` from a live process attached to the
    /// running game. Every sub-read that fails degrades to "not
    /// present" rather than propagating an error, so a torn read
    /// mid-frame doesn't kill the tracker.
    pub fn from_process(state: &State, process: &dyn ReadProcess) -> Self {
        let state_snap = StateSnapshot::from_state(state);
        let waddler_storage: HashSet<EntityType> = state
            .waddler_storage
            .iter()
            .copied()
            .filter(|e| e.0 != 0)
            .collect();

        // Load Items + player 0. If any of these fail (typically
        // "not in a run yet"), return a snapshot with empty
        // companion sets and None player state; chains will simply
        // stay Unstarted.
        let Some(items) = state.items.load(process).ok().flatten() else {
            return Self {
                state: state_snap,
                waddler_storage,
                player_items: HashSet::new(),
                companion_held_items: HashSet::new(),
                companion_types: HashSet::new(),
                player0_char_state: None,
                player0: None,
                all_players_kills_total: 0,
                all_players_collected_money: Vec::new(),
                entity_map: state.instance_id_to_pointer,
                player_motion: None,
                theme_info_sub_theme_address: sub_theme_addr(state, process),
            };
        };
        // Inline inventories were loaded as part of `items`. Sum
        // across all four so downstream Pacifist logic works in
        // co-op.
        let all_players_kills_total: u32 = items
            .player_inventory
            .iter()
            .map(|inv| inv.kills_total)
            .sum();
        // Flatten every player's `collected_money` array; drop empty
        // slots so downstream trackers just iterate real entries.
        let all_players_collected_money: Vec<u32> = items
            .player_inventory
            .iter()
            .flat_map(|inv| inv.collected_money.iter().copied())
            .filter(|id| *id != 0)
            .collect();
        let Some(player) = items.players[0].load(process).ok().flatten() else {
            return Self {
                state: state_snap,
                waddler_storage,
                player_items: HashSet::new(),
                companion_held_items: HashSet::new(),
                companion_types: HashSet::new(),
                player0_char_state: None,
                player0: None,
                all_players_kills_total,
                all_players_collected_money,
                entity_map: state.instance_id_to_pointer,
                player_motion: None,
                theme_info_sub_theme_address: sub_theme_addr(state, process),
            };
        };

        // Player 0's own inventory items + held item.
        let mut player_items: HashSet<EntityType> = HashSet::new();
        for uid in player.items.load(process).unwrap_or_default() {
            if let Some(id) = load_entity_type_id(process, state, uid as i32) {
                player_items.insert(id);
            }
        }
        if player.holding_uid >= 0
            && let Some(id) = load_entity_type_id(process, state, player.holding_uid)
        {
            player_items.insert(id);
        }

        let (companion_types, companion_held_items) = walk_companion_chain(
            process,
            &state.instance_id_to_pointer,
            player.linked_companion_child,
        );

        // Load inventory. Torn read = leave the player snapshot None.
        let player0_snap = if let Some(inv) = player.inventory.load(process).ok().flatten() {
            // Overlay: peek at the top-level overlay type + tamed
            // mount flag. Full compute_player_motion walk deferred
            // to whenever RunState grows TP shadow detection.
            let (overlay_type, overlay_tamed_mount) = if player.overlay.is_null() {
                (None, false)
            } else {
                let overlay_type = player
                    .overlay
                    .load_base(process)
                    .ok()
                    .flatten()
                    .and_then(|ent| ent.type_.load(process).ok().flatten())
                    .map(|db: EntityDBEntry| db.id);
                let tamed = if let Some(ty) = overlay_type {
                    if crate::entity::MOUNTS.contains(&ty) {
                        player
                            .overlay
                            .load_as::<crate::entity::Mount>(process)
                            .ok()
                            .flatten()
                            .map(|m| m.is_tamed)
                            .unwrap_or(false)
                    } else {
                        false
                    }
                } else {
                    false
                };
                (overlay_type, tamed)
            };
            Some(PlayerSnapshot {
                health: player.health,
                state: player.state,
                last_state: player.last_state,
                layer: player.layer,
                position_x: player.position_x,
                position_y: player.position_y,
                velocity_x: player.velocity_x,
                velocity_y: player.velocity_y,
                inventory: InventorySnapshot {
                    money: inv.money,
                    bombs: inv.bombs,
                    ropes: inv.ropes,
                    kills_total: inv.kills_total,
                    collected_money_total: inv.collected_money_total,
                    cursed: inv.cursed,
                },
                overlay_type,
                overlay_tamed_mount,
            })
        } else {
            None
        };

        let player_motion = Some(compute_player_motion(process, &player));

        Self {
            state: state_snap,
            waddler_storage,
            player_items,
            companion_held_items,
            companion_types,
            player0_char_state: Some(player.state),
            player0: player0_snap,
            all_players_kills_total,
            all_players_collected_money,
            entity_map: state.instance_id_to_pointer,
            player_motion,
            theme_info_sub_theme_address: sub_theme_addr(state, process),
        }
    }

    /// Constructs a bare snapshot with the given state fields and
    /// empty companion sets. Convenience for unit-testing chains
    /// against synthetic inputs without touching a process.
    #[cfg(test)]
    pub fn stub(state: StateSnapshot) -> Self {
        Self {
            state,
            waddler_storage: HashSet::new(),
            player_items: HashSet::new(),
            companion_held_items: HashSet::new(),
            companion_types: HashSet::new(),
            player0_char_state: None,
            player0: None,
            all_players_kills_total: 0,
            all_players_collected_money: Vec::new(),
            entity_map: crate::entity_map::UidEntityMap {
                mask: 0,
                table_ptr: 0,
            },
            player_motion: None,
            theme_info_sub_theme_address: None,
        }
    }
}

/// Loads `state.theme_info.sub_theme_address` if the theme_info
/// pointer is non-null and the read succeeds. Returns None on menus
/// / camp where theme_info isn't populated yet, and on torn reads.
fn sub_theme_addr(state: &State, process: &dyn ReadProcess) -> Option<u64> {
    if state.theme_info.is_null() {
        return None;
    }
    state
        .theme_info
        .load(process)
        .ok()
        .flatten()
        .map(|ti| ti.sub_theme_address)
}

/// Walk player 0's linked-companion chain and collect the companions'
/// entity types + the items they hold. Bounded at 256 iterations so a
/// corrupted linked list can't spin the tracker; real chains are at
/// most a handful of pets deep.
///
/// Split out of `ChainInputs::compute` (and typed on `&UidEntityMap`
/// rather than `&State`) so tests can drive it against a synthetic
/// `EntityMapBuilder`-backed process without faking the full State +
/// Items + Player mem layout that sits above it.
pub(crate) fn walk_companion_chain(
    process: &dyn ReadProcess,
    entity_map: &crate::entity_map::UidEntityMap,
    start_uid: i32,
) -> (HashSet<EntityType>, HashSet<EntityType>) {
    let mut companion_types: HashSet<EntityType> = HashSet::new();
    let mut companion_held_items: HashSet<EntityType> = HashSet::new();
    let mut uid = start_uid;
    for _ in 0..256 {
        if uid == 0 {
            break;
        }
        let Ok(Some(handle)) = entity_map.get(process, uid) else {
            break;
        };
        if let Some(id) = handle
            .entity
            .type_
            .load(process)
            .ok()
            .flatten()
            .map(|db: EntityDBEntry| db.id)
        {
            companion_types.insert(id);
        }
        for held_uid in handle.entity.items.load(process).unwrap_or_default() {
            if let Some(id) = load_entity_type_id_from_map(process, entity_map, held_uid as i32) {
                companion_held_items.insert(id);
            }
        }
        // Re-read the companion as a Player to pull its
        // linked_companion_child. The narrowing cast is safe: every
        // companion type shares the Player prefix layout.
        let Ok(next) = <Player as MemType>::read_from(process, handle.addr) else {
            break;
        };
        uid = next.linked_companion_child;
    }
    (companion_types, companion_held_items)
}

/// Same as `load_entity_type_id` but takes an already-extracted
/// `&UidEntityMap` so callers not holding a full `&State` can reuse
/// the lookup. Kept private; production code goes through
/// `load_entity_type_id`.
fn load_entity_type_id_from_map(
    process: &dyn ReadProcess,
    entity_map: &crate::entity_map::UidEntityMap,
    uid: i32,
) -> Option<EntityType> {
    let handle = entity_map.get(process, uid).ok().flatten()?;
    let db: EntityDBEntry = handle.entity.type_.load(process).ok().flatten()?;
    Some(db.id)
}

/// Follow an entity UID -> load its base type -> return the EntityDB
/// type ID. None on any lookup / read failure.
fn load_entity_type_id(process: &dyn ReadProcess, state: &State, uid: i32) -> Option<EntityType> {
    let handle = state
        .instance_id_to_pointer
        .get(process, uid)
        .ok()
        .flatten()?;
    let db: EntityDBEntry = handle.entity.type_.load(process).ok().flatten()?;
    Some(db.id)
}

/// Depth cap for the overlay walk in compute_player_motion. Real
/// chains are at most a few frames deep (player on a mount on an
/// active floor); the guard just prevents an infinite loop on a
/// corrupted pointer chain from a torn mid-frame read.
const OVERLAY_WALK_MAX_DEPTH: u32 = 16;

/// Collapse the player's overlay chain into a single PlayerMotion.
/// Mount overlays replace the reported position + velocity (the game
/// applies TP effects at the mount's coords); active floors add
/// (position + velocity are relative to the floor's own motion).
fn compute_player_motion(
    process: &dyn ReadProcess,
    player: &crate::entity::Player,
) -> PlayerMotion {
    let mut position_x = player.position_x;
    let mut position_y = player.position_y;
    let mut velocity_x = player.velocity_x;
    let mut velocity_y = player.velocity_y;

    // Walk the overlay chain via raw addr. PolyPointer<EntityReduced>
    // isn't Copy (the derive requires Base: Copy), so thread the
    // u64 address manually rather than moving the whole PolyPointer.
    let mut overlay_addr = player.overlay.addr;
    for _ in 0..OVERLAY_WALK_MAX_DEPTH {
        if overlay_addr == 0 {
            break;
        }
        let Ok(m) = <crate::entity::Movable as ml2_mem::MemType>::read_from(process, overlay_addr)
        else {
            break;
        };
        let ty_id = m.type_.load(process).ok().flatten().map(|db| db.id);
        let is_mount = ty_id
            .map(|id| crate::entity::MOUNTS.contains(&id))
            .unwrap_or(false);
        if is_mount {
            position_x = m.position_x;
            position_y = m.position_y;
            velocity_x = m.velocity_x;
            velocity_y = m.velocity_y;
        } else {
            position_x += m.position_x;
            position_y += m.position_y;
            velocity_x += m.velocity_x;
            velocity_y += m.velocity_y;
        }
        overlay_addr = m.overlay.addr;
    }

    PlayerMotion {
        position_x,
        position_y,
        velocity_x,
        velocity_y,
    }
}

#[cfg(test)]
mod tests {
    //! Coverage for the companion-walk step of `ChainInputs::from_process`.
    //! The walk lives in its own `walk_companion_chain` fn so it can
    //! be driven with just `EntityMapBuilder` (no State/Items facsimile
    //! needed), keeping the test focused on the linked-list semantics.

    use super::walk_companion_chain;
    use crate::entity_types as et;
    use crate::testing::EntityMapBuilder;
    use ml2_mem::MockProcess;

    #[test]
    fn walk_companion_chain_empty_start_returns_empty_sets() {
        // start_uid == 0: no walk, no lookups. Matches a fresh Player
        // with no companion linked.
        let builder = EntityMapBuilder::new();
        let map = builder.to_map();
        let proc = MockProcess {
            data: builder.buffer(),
        };
        let (types, held) = walk_companion_chain(&proc, &map, 0);
        assert!(types.is_empty());
        assert!(held.is_empty());
    }

    #[test]
    fn walk_companion_chain_captures_hh_type() {
        // Main player's linked_companion_child points at an HH with a
        // specific entity_type. Walk should see that type + no held
        // items.
        let mut builder = EntityMapBuilder::new();
        let hh_uid = builder.add_entity_with_hh_items(et::CHAR_HIREDHAND, &[], 0);
        let map = builder.to_map();
        let proc = MockProcess {
            data: builder.buffer(),
        };
        let (types, held) = walk_companion_chain(&proc, &map, hh_uid as i32);
        assert!(types.contains(&et::CHAR_HIREDHAND));
        assert_eq!(types.len(), 1);
        assert!(held.is_empty());
    }

    #[test]
    fn walk_companion_chain_captures_hh_held_items() {
        // HH carrying items in its `items` vector. Walk should see the
        // HH's type AND every held item's type.
        let mut builder = EntityMapBuilder::new();
        let held =
            builder.add_trivial_entities(&[et::ITEM_POWERUP_UDJATEYE, et::ITEM_POWERUP_ANKH]);
        let hh_uid = builder.add_entity_with_hh_items(et::CHAR_HIREDHAND, &held, 0);
        let map = builder.to_map();
        let proc = MockProcess {
            data: builder.buffer(),
        };
        let (types, held_types) = walk_companion_chain(&proc, &map, hh_uid as i32);
        assert!(types.contains(&et::CHAR_HIREDHAND));
        assert!(held_types.contains(&et::ITEM_POWERUP_UDJATEYE));
        assert!(held_types.contains(&et::ITEM_POWERUP_ANKH));
        assert_eq!(held_types.len(), 2);
    }

    #[test]
    fn walk_companion_chain_follows_multi_hop_chain() {
        // Player -> HH1 (holds Ushabti) -> HH2 (holds Scepter). Walk
        // must see BOTH HH types and BOTH items.
        let mut builder = EntityMapBuilder::new();
        let ushabti = builder.add_trivial_entities(&[et::ITEM_USHABTI]);
        let scepter = builder.add_trivial_entities(&[et::ITEM_SCEPTER]);
        // Insert HH2 first so HH1 can link to it.
        let hh2 = builder.add_entity_with_hh_items(et::CHAR_HIREDHAND, &scepter, 0);
        let hh1 = builder.add_entity_with_hh_items(et::CHAR_HIREDHAND, &ushabti, hh2);
        let map = builder.to_map();
        let proc = MockProcess {
            data: builder.buffer(),
        };
        let (types, held) = walk_companion_chain(&proc, &map, hh1 as i32);
        assert!(types.contains(&et::CHAR_HIREDHAND));
        assert!(held.contains(&et::ITEM_USHABTI));
        assert!(held.contains(&et::ITEM_SCEPTER));
    }

    #[test]
    fn walk_companion_chain_stops_at_unknown_uid() {
        // start_uid that doesn't resolve in the map: Ok(None) from
        // `map.get`, break the loop, return empty. Guards against
        // reading garbage when the game's next_entity_uid hasn't been
        // captured yet.
        let builder = EntityMapBuilder::new();
        let map = builder.to_map();
        let proc = MockProcess {
            data: builder.buffer(),
        };
        let (types, held) = walk_companion_chain(&proc, &map, 9999);
        assert!(types.is_empty());
        assert!(held.is_empty());
    }
}
