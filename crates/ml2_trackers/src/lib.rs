//! `ml2_trackers`: Spelunky 2 game-state model and tracker business
//! logic. Sits on top of `ml2_mem` (raw process reads + type traits)
//! and produces the typed data trackers turn into display strings.
//!
//! Layers land in dependency order:
//! - `enums` / `flags`: small building blocks: Screen, Theme, WinState,
//!   RunRecapFlags, etc. Each carries a MemType impl so the State
//!   struct can use them as field types directly.
//! - `state`: the root `State` struct + a `read_current(process)`
//!   entry point that scans feedcode and reads State off it.
//! - (later) `inventory`, `entities`, `chains`, `runstate`, per-tracker
//!   modules.
//!
//! Nothing here uses Tauri or serde on purpose; consumers stitch this
//! into the trackers server + UI in the tauri app.

pub mod arena_state;
pub mod chain;
pub mod chain_impl;
pub mod entity;
pub mod entity_map;
pub mod entity_types;
pub mod enums;
pub mod flags;
pub mod label;
pub mod runstate;
pub mod state;
pub mod tracker;

#[cfg(test)]
pub mod testing;

pub use chain::{ChainStatus, ChainStepResult, ChainStepper, Step};
pub use entity::{
    BACKPACKS, CHAIN_POWERUP_ENTITIES, CharState, DIAMOND, Entity, EntityDBEntry, EntityReduced,
    EntityType, GEMS, Illumination, Inventory, Items, LOW_BANNED_ATTACKABLES,
    LOW_BANNED_THROWABLES, Layer, LightEmitter, MOUNTS, Mount, Movable, NON_CHAIN_POWERUP_ENTITIES,
    Player, SHIELDS, TELEPORT_ENTITIES,
};
pub use entity_map::{EntityHandle, RobinHoodTableEntry, UidEntityMap};
pub use enums::{LoadingState, Screen, Theme, WinState};
pub use flags::{HudFlags, PresenceFlags, QuestFlags, RunRecapFlags};
pub use label::{Label, LabelMetadata, RunLabel, RunLabelError, SaveableCategory};
pub use state::{FEEDCODE_TO_STATE_OFFSET, State, ThemeInfo};

#[cfg(test)]
mod tests {
    use super::*;
    use ml2_mem::{MemStruct, MockProcess};

    /// Places a State-shaped buffer at address 0 in a MockProcess. Only
    /// the specific offsets under test are filled; every other byte
    /// stays zero, which decodes to Screen::Logo / Theme::BeforeFirstRun
    /// / etc, all valid discriminants.
    #[test]
    fn state_waddler_storage_and_map_fields_decode() {
        // Plants waddler storage slots + a UidEntityMap header. Just
        // proves the offsets line up now that State grew a few big
        // trailing fields.
        let mut data = vec![0u8; 0x1500];
        // waddler slot 0 = ITEM_HOUYIBOW
        data[0x8C..0x90].copy_from_slice(&entity_types::ITEM_HOUYIBOW.0.to_le_bytes());
        // waddler slot 2 = ITEM_DIAMOND
        data[0x8C + 8..0x8C + 12].copy_from_slice(&entity_types::ITEM_DIAMOND.0.to_le_bytes());
        // items pointer = 0 (no run yet).
        // UidEntityMap header at 0x1348: mask, table_ptr.
        data[0x1348..0x1350].copy_from_slice(&0xFFu64.to_le_bytes());
        data[0x1350..0x1358].copy_from_slice(&0x2000u64.to_le_bytes());
        let proc = ml2_mem::MockProcess { data: &data };
        let state = <State as ml2_mem::MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(state.waddler_storage[0], entity_types::ITEM_HOUYIBOW);
        assert_eq!(state.waddler_storage[2], entity_types::ITEM_DIAMOND);
        assert_eq!(state.waddler_storage[1].0, 0); // untouched slot
        assert!(state.items.is_null());
        assert_eq!(state.instance_id_to_pointer.mask, 0xFF);
        assert_eq!(state.instance_id_to_pointer.table_ptr, 0x2000);
    }

    #[test]
    fn state_decodes_from_mock_bytes() {
        let mut data = vec![0u8; 0x2000];
        // Screen at 0x0C = Camp (11).
        data[0x0C..0x10].copy_from_slice(&11i32.to_le_bytes());
        // Theme at 0x74 = TidePool (5).
        data[0x74] = 5;
        // world/level.
        data[0x68] = 4;
        data[0x6A] = 2;
        // time_total at 0x64.
        data[0x64..0x68].copy_from_slice(&360u32.to_le_bytes());
        // win_state at 0x76 = Tiamat (1).
        data[0x76] = 1i8 as u8;
        // Set PACIFIST (bit 0) + LIKED_PETS (bit 11) in run_recap_flags at 0xA34.
        let recap: u32 = (1 << 0) | (1 << 11);
        data[0xA34..0xA38].copy_from_slice(&recap.to_le_bytes());

        let proc = MockProcess { data: &data };
        let state = <State as MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(state.screen, Screen::Camp);
        assert_eq!(state.theme, Theme::TidePool);
        assert_eq!(state.world, 4);
        assert_eq!(state.level, 2);
        assert_eq!(state.time_total, 360);
        assert_eq!(state.win_state, WinState::Tiamat);
        assert!(state.run_recap_flags.contains(RunRecapFlags::PACIFIST));
        assert!(state.run_recap_flags.contains(RunRecapFlags::LIKED_PETS));
        assert!(!state.run_recap_flags.contains(RunRecapFlags::DIED));
    }

    // RunLabel: render string cases from speedrun-category
    // conventions. Each test names the run shape and asserts the
    // rendered string.

    #[test]
    fn run_label_defaults_render_no_percent() {
        // Fresh run walks the full pipeline. NoCo drops via
        // ONLY_SHOW_WITH (needs Score, absent). No hides NoGold. No%
        // (priority 5) beats Low, hiding Low and everything Low would
        // hide. Any drops via NoGold->Any / Pacifist->Any hides.
        let rl = RunLabel::new();
        assert_eq!(rl.text(false, &[]), "Pacifist No%");
    }

    #[test]
    fn run_label_score_swallows_everything_but_no_co() {
        let mut rl = RunLabel::new();
        rl.set_terminus(Label::CosmicOcean).unwrap();
        rl.add(Label::Score).unwrap();
        // With Score, only Score + NoCo (which is a start) are visible.
        // Score comes before NoCo in declaration order.
        assert_eq!(rl.text(false, &[]), "Score No CO");
    }

    #[test]
    fn run_label_terminus_transition_swaps_label() {
        let mut rl = RunLabel::new();
        assert!(rl.contains(Label::Any));
        rl.set_terminus(Label::Death).unwrap();
        assert!(!rl.contains(Label::Any));
        assert!(rl.contains(Label::Death));
    }

    #[test]
    fn run_label_rejects_non_add_ok_label() {
        let mut rl = RunLabel::new();
        // NoJetpack is start=true so add_ok defaults to false.
        assert!(matches!(
            rl.add(Label::NoJetpack),
            Err(RunLabelError::NotAddOk(Label::NoJetpack))
        ));
    }

    #[test]
    fn run_label_rejects_discarding_terminus() {
        let mut rl = RunLabel::new();
        assert!(matches!(
            rl.discard(&[Label::Any]),
            Err(RunLabelError::DiscardedTerminus(Label::Any))
        ));
    }

    #[test]
    fn run_label_hide_early_drops_start_flag_labels() {
        // hide_early=true removes NoJetpack/NoTeleporter/NoGold/Pacifist
        // (start=true implies hide_early=true unless overridden). NoCo
        // still drops via ONLY_SHOW_WITH. Any drops via Low->Any hide.
        // Result: just "No%".
        let rl = RunLabel::new();
        assert_eq!(rl.text(true, &[]), "No%");
    }

    #[test]
    fn run_label_mutex_terminus_check() {
        // Building a RunLabel with two termini should reject.
        let starting: std::collections::BTreeSet<Label> =
            [Label::Any, Label::Death].into_iter().collect();
        assert!(matches!(
            RunLabel::with_starting(starting),
            Err(RunLabelError::WrongTerminusCount { found: 2 })
        ));
    }

    #[test]
    fn run_label_excluded_categories_dropped() {
        let rl = RunLabel::new();
        // Excluding "No" (SaveableCategory::No) removes it from vis,
        // so the previously-hidden Low% re-emerges. NoCo still drops
        // via ONLY_SHOW_WITH. Low hides NoTeleporter/NoJetpack/Any.
        assert_eq!(
            rl.text(false, &[SaveableCategory::No]),
            "No Gold Pacifist Low%"
        );
    }

    // Chain FSM: transitions through unstarted -> in_progress ->
    // failed against a synthetic context, plus the "no re-entering
    // the initial step" invariant.

    fn step_a(ctx: &TestCtx) -> ChainStepResult<TestCtx> {
        if ctx.advance {
            ChainStepResult::in_progress(step_b)
        } else {
            ChainStepResult::unstarted()
        }
    }

    fn step_b(ctx: &TestCtx) -> ChainStepResult<TestCtx> {
        if ctx.fail {
            ChainStepResult::failed()
        } else {
            ChainStepResult::in_progress(step_b)
        }
    }

    struct TestCtx {
        advance: bool,
        fail: bool,
    }

    #[test]
    fn chain_starts_unstarted_and_advances() {
        let mut chain = ChainStepper::new("test", step_a);
        assert_eq!(chain.last_status(), ChainStatus::Unstarted);
        let ctx = TestCtx {
            advance: false,
            fail: false,
        };
        assert_eq!(chain.evaluate(&ctx), ChainStatus::Unstarted);
        let ctx = TestCtx {
            advance: true,
            fail: false,
        };
        assert_eq!(chain.evaluate(&ctx), ChainStatus::InProgress);
        assert_eq!(chain.last_status(), ChainStatus::InProgress);
    }

    #[test]
    fn chain_sticks_in_failed() {
        let mut chain = ChainStepper::new("test", step_a);
        chain.evaluate(&TestCtx {
            advance: true,
            fail: false,
        });
        chain.evaluate(&TestCtx {
            advance: true,
            fail: true,
        });
        assert_eq!(chain.last_status(), ChainStatus::Failed);
        // Once failed, subsequent evaluates return Failed without
        // invoking any step.
        assert_eq!(
            chain.evaluate(&TestCtx {
                advance: false,
                fail: false,
            }),
            ChainStatus::Failed
        );
    }

    fn step_loops_back(_ctx: &TestCtx) -> ChainStepResult<TestCtx> {
        // Wrongly names step_looping_start as its next step. Should
        // panic when reached after leaving unstarted.
        ChainStepResult::in_progress(step_looping_start)
    }

    fn step_looping_start(_ctx: &TestCtx) -> ChainStepResult<TestCtx> {
        ChainStepResult::in_progress(step_loops_back)
    }

    #[test]
    #[should_panic(expected = "InProgress with the initial step")]
    fn chain_rejects_reentering_initial_step() {
        let mut chain = ChainStepper::new("loop", step_looping_start);
        let ctx = TestCtx {
            advance: false,
            fail: false,
        };
        // First evaluate leaves Unstarted -> InProgress(step_loops_back).
        chain.evaluate(&ctx);
        // Second evaluate: step_loops_back names step_looping_start as
        // its next step, which equals the initial. Panics.
        chain.evaluate(&ctx);
    }

    // Entity constants: quick sanity that the codegen'd table
    // matched cross-references. If entities.json ever renames one of
    // the tracker-critical entities these would fail.

    #[test]
    fn entity_constants_present() {
        assert_ne!(entity_types::MOUNT_TURKEY.0, 0);
        assert_ne!(entity_types::ITEM_DIAMOND.0, 0);
        assert_ne!(entity_types::ITEM_POWERUP_UDJATEYE.0, 0);
        assert_eq!(entity_types::DEFAULT_TYPE_ID.0, 0);
    }

    #[test]
    fn entity_sets_contain_expected_members() {
        assert!(MOUNTS.contains(&entity_types::MOUNT_TURKEY));
        assert!(BACKPACKS.contains(&entity_types::ITEM_JETPACK));
        assert!(GEMS.contains(&entity_types::ITEM_DIAMOND));
        assert_eq!(DIAMOND, entity_types::ITEM_DIAMOND);
        assert!(!MOUNTS.contains(&entity_types::ITEM_DIAMOND));
    }

    #[test]
    fn player_struct_decodes() {
        // Plants type pointer + inventory pointer + uid + companion
        // child at their offsets, reads back through the MemStruct
        // derive. Just enough to prove the composed struct decode
        // works end-to-end.
        let mut data = vec![0u8; 0x200];
        // type_ pointer at 0x08 -> 0
        data[0x08..0x10].copy_from_slice(&0u64.to_le_bytes());
        data[0x38..0x3C].copy_from_slice(&42u32.to_le_bytes());
        data[0x140..0x148].copy_from_slice(&0u64.to_le_bytes());
        data[0x150..0x154].copy_from_slice(&7i32.to_le_bytes());
        let proc = ml2_mem::MockProcess { data: &data };
        let player = <Player as ml2_mem::MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(player.uid, 42);
        assert_eq!(player.linked_companion_child, 7);
        assert!(player.type_.is_null());
        assert!(player.inventory.is_null());
    }

    // UidEntityMap: bit-for-bit hasher + Robin Hood lookup.

    // Same `lowbias32` used by `UidEntityMap::find_addr`; the fixture
    // module owns the shared copy so tests and the fixture builder
    // stay bit-identical.
    use testing::lowbias32;

    /// Sanity that the hasher is deterministic + non-degenerate. The
    /// find_addr tests below are the effective bit-for-bit check:
    /// they compute the key with this same function that the map
    /// stores into the table, so a mismatch breaks the fixture.
    #[test]
    fn lowbias32_is_deterministic() {
        assert_eq!(lowbias32(1), lowbias32(1));
        assert_ne!(lowbias32(1), lowbias32(2));
        assert_ne!(lowbias32(43), 0);
    }

    /// Build a table with capacity `cap` (must be power of two),
    /// place one entry keyed by `hashed_key` at the given index, plant
    /// a fake entity at the given `entity_addr`, and return a
    /// MockProcess-ready buffer + a UidEntityMap that reads from it.
    ///
    /// The mock lays out:
    /// - offset 0..16:   UidEntityMap { mask, table_ptr }
    /// - offset 32..:    table (16 bytes * cap)
    /// - `entity_addr..`: Entity fields (uid at 0x38)
    fn build_map_with_one_entry(
        cap: u64,
        index: u64,
        hashed_key: u32,
        entity_addr: u64,
        entity_uid: u32,
    ) -> (Vec<u8>, UidEntityMap) {
        let table_ptr = 32u64;
        let entry_size = 16u64;
        let table_end = table_ptr + cap * entry_size;
        let end = (entity_addr as usize + 0x100).max(table_end as usize);
        let mut data = vec![0u8; end];
        // Header.
        data[0..8].copy_from_slice(&(cap - 1).to_le_bytes());
        data[8..16].copy_from_slice(&table_ptr.to_le_bytes());
        // Entry.
        let entry_start = table_ptr as usize + index as usize * 16;
        data[entry_start..entry_start + 4].copy_from_slice(&hashed_key.to_le_bytes());
        data[entry_start + 8..entry_start + 16].copy_from_slice(&entity_addr.to_le_bytes());
        // Entity: only the uid field matters for the .get() cross-check.
        // Entity layout has uid at 0x38.
        data[entity_addr as usize + 0x38..entity_addr as usize + 0x3C]
            .copy_from_slice(&entity_uid.to_le_bytes());
        let map = UidEntityMap {
            mask: cap - 1,
            table_ptr,
        };
        (data, map)
    }

    #[test]
    fn uid_map_get_finds_entry_at_home_bucket() {
        // Cap 16, uid=42. Entry lives at hash % cap.
        let uid = 42i32;
        let hashed = lowbias32(uid as u32 + 1);
        let cap = 16u64;
        let index = (hashed as u64) & (cap - 1);
        let entity_addr = 0x200u64;
        let (data, map) = build_map_with_one_entry(cap, index, hashed, entity_addr, uid as u32);
        let proc = ml2_mem::MockProcess { data: &data };
        let handle = map.get(&proc, uid).unwrap().expect("hit");
        assert_eq!(handle.addr, entity_addr);
        assert_eq!(handle.entity.uid, uid as u32);
    }

    #[test]
    fn uid_map_get_miss_on_empty_slot() {
        // Empty table -> every slot has hashed_key == 0 -> immediate miss.
        let cap = 16u64;
        let table_ptr = 32u64;
        let mut data = vec![0u8; 512];
        data[0..8].copy_from_slice(&(cap - 1).to_le_bytes());
        data[8..16].copy_from_slice(&table_ptr.to_le_bytes());
        let map = UidEntityMap {
            mask: cap - 1,
            table_ptr,
        };
        let proc = ml2_mem::MockProcess { data: &data };
        assert!(map.get(&proc, 7).unwrap().is_none());
    }

    #[test]
    fn uid_map_get_null_table_returns_none() {
        let map = UidEntityMap {
            mask: 0xFFFF,
            table_ptr: 0,
        };
        let data = vec![0u8; 8];
        let proc = ml2_mem::MockProcess { data: &data };
        assert!(map.get(&proc, 5).unwrap().is_none());
    }

    #[test]
    fn uid_map_get_negative_uid_sentinel_returns_none() {
        let map = UidEntityMap {
            mask: 0xF,
            table_ptr: 32,
        };
        let data = vec![0u8; 512];
        let proc = ml2_mem::MockProcess { data: &data };
        // -1 is the game's null-uid sentinel; must return None
        // without even touching the table.
        assert!(map.get(&proc, -1).unwrap().is_none());
    }

    #[test]
    fn uid_map_get_uid_mismatch_returns_none() {
        // Plant an entry keyed for uid=10 but stash an entity whose
        // uid field says 99. The get() call must reject the mismatch
        // rather than returning bogus data.
        let uid = 10i32;
        let hashed = lowbias32(uid as u32 + 1);
        let cap = 16u64;
        let index = (hashed as u64) & (cap - 1);
        let entity_addr = 0x200u64;
        let (data, map) = build_map_with_one_entry(cap, index, hashed, entity_addr, 99);
        let proc = ml2_mem::MockProcess { data: &data };
        assert!(map.get(&proc, uid).unwrap().is_none());
    }

    // Concrete chain transitions. Each test builds a stub
    // ChainInputs, runs a few evaluate() calls, and asserts the
    // resulting ChainStatus. Covers the primary happy path + the
    // most common failure branch for each chain.

    use chain_impl::inputs::{ChainInputs, StateSnapshot};

    /// Minimal "empty" snapshot used as a starting point that
    /// individual tests then mutate. Every field defaults to a value
    /// that's safe (no active run, all counters zero).
    fn empty_snapshot() -> StateSnapshot {
        StateSnapshot {
            screen: Screen::Level,
            screen_last: Screen::Level,
            screen_next: Screen::Level,
            world: 1,
            level: 1,
            world_start: 1,
            level_start: 1,
            theme: Theme::Dwelling,
            theme_start: Theme::Dwelling,
            win_state: WinState::NoWin,
            run_recap_flags: RunRecapFlags::empty(),
            hud_flags: HudFlags::empty(),
            quest_flags: QuestFlags::empty(),
            presence_flags: PresenceFlags::empty(),
            level_count: 0,
            time_total: 0,
            time_level: 0,
            time_last_level: 0,
            time_tutorial: 0,
            time_startup: 0,
            money_shop_total: 0,
            next_entity_uid: 0,
            loading: LoadingState::NotLoading,
        }
    }

    /// A read-anything-returns-empty process for tests that call
    /// `RunState::update`. `update` only touches the process on Level
    /// screens with a live entity delta, and every test that uses
    /// this uses the empty snapshot where next_entity_uid == 0, so the
    /// entity walk never actually reads. The stub is here to satisfy
    /// the signature.
    fn empty_process() -> ml2_mem::MockProcess<'static> {
        ml2_mem::MockProcess { data: &[] }
    }

    // Cosmic.
    //
    // Each step function is called directly (they're `pub(crate)` in
    // `chain_impl::cosmic`) so the tests target one FSM transition at
    // a time. The step-identity check compares `result.next_step`'s fn
    // pointer against the expected function.

    use chain_impl::cosmic;

    /// Given a step result the caller expected to advance to some
    /// named step, panic with a helpful message if the fn pointer
    /// doesn't match. Rust fn pointers compare by address; each
    /// concrete step has exactly one address.
    fn assert_next_step_is(
        result: &chain::ChainStepResult<ChainInputs>,
        expected: chain::Step<ChainInputs>,
        label: &str,
    ) {
        let next = result
            .next_step
            .expect("in-progress result must have next_step");
        assert_eq!(
            next as usize, expected as usize,
            "expected next step to be {label}",
        );
    }

    // collect_bow: 4 cases.
    #[test]
    fn cosmic_collect_bow_world1_empty_stays_unstarted() {
        let inputs = ChainInputs::stub(empty_snapshot());
        let result = cosmic::collect_bow(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn cosmic_collect_bow_world2_empty_stays_unstarted() {
        let mut snap = empty_snapshot();
        snap.world = 2;
        let inputs = ChainInputs::stub(snap);
        let result = cosmic::collect_bow(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn cosmic_collect_bow_world2_with_bow_advances() {
        let mut snap = empty_snapshot();
        snap.world = 2;
        let mut inputs = ChainInputs::stub(snap);
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::collect_bow(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::carry_bow_to_hundun, "carry_bow_to_hundun");
    }
    #[test]
    fn cosmic_collect_bow_world3_empty_fails() {
        let mut snap = empty_snapshot();
        snap.world = 3;
        let inputs = ChainInputs::stub(snap);
        let result = cosmic::collect_bow(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // carry_bow_to_hundun: 9 cases. Covers the player / hired-hand /
    // Waddler-stash matrix at the 2-3 transition, the past-Waddler
    // cutoff at 7-2, the advance to `win_via_co` at 7-3, and the
    // WinState-invalidates and SCORES-in-base-camp fail branches.
    fn carry_bow_snap(world: u8, level: u8, screen: Screen, win_state: WinState) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.screen = screen;
        snap.win_state = win_state;
        snap
    }
    #[test]
    fn cosmic_carry_bow_w2l3_transition_player_holds_bow_stays() {
        let mut inputs = ChainInputs::stub(carry_bow_snap(
            2,
            3,
            Screen::LevelTransition,
            WinState::NoWin,
        ));
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::carry_bow_to_hundun, "carry_bow_to_hundun");
    }
    #[test]
    fn cosmic_carry_bow_w2l3_transition_nobody_holds_bow_fails() {
        let inputs = ChainInputs::stub(carry_bow_snap(
            2,
            3,
            Screen::LevelTransition,
            WinState::NoWin,
        ));
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn cosmic_carry_bow_w2l3_transition_companion_holds_bow_stays() {
        let mut inputs = ChainInputs::stub(carry_bow_snap(
            2,
            3,
            Screen::LevelTransition,
            WinState::NoWin,
        ));
        inputs
            .companion_held_items
            .insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::carry_bow_to_hundun, "carry_bow_to_hundun");
    }
    #[test]
    fn cosmic_carry_bow_w3l1_waddler_stash_stays() {
        let mut inputs = ChainInputs::stub(carry_bow_snap(
            3,
            1,
            Screen::LevelTransition,
            WinState::NoWin,
        ));
        inputs.waddler_storage.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::carry_bow_to_hundun, "carry_bow_to_hundun");
    }
    #[test]
    fn cosmic_carry_bow_w7l2_waddler_stash_past_cutoff_fails() {
        // Waddler stash only counts before world 7; past 7-1 the bow
        // has to be on the player or a companion.
        let mut inputs = ChainInputs::stub(carry_bow_snap(
            7,
            2,
            Screen::LevelTransition,
            WinState::NoWin,
        ));
        inputs.waddler_storage.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn cosmic_carry_bow_w7l3_player_holds_bow_stays() {
        // At 7-3 the step returns `carry_bow_to_hundun`: the transition
        // FROM 7-3 to 7-4 still reads `world_level == (7, 3)`, so the
        // `> (7, 3)` advance gate hasn't fired yet. The w7l4 case below
        // covers the transition that actually advances.
        let mut inputs = ChainInputs::stub(carry_bow_snap(
            7,
            3,
            Screen::LevelTransition,
            WinState::NoWin,
        ));
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::carry_bow_to_hundun, "carry_bow_to_hundun");
    }
    #[test]
    fn cosmic_carry_bow_w7l4_player_holds_bow_advances_to_win_via_co() {
        // Once past 7-3, the `world_level > (7, 3)` gate fires and
        // advances regardless of screen or held items, the CO stack
        // has begun.
        let mut inputs = ChainInputs::stub(carry_bow_snap(7, 4, Screen::Level, WinState::NoWin));
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::win_via_co, "win_via_co");
    }
    #[test]
    fn cosmic_carry_bow_ending_tiamat_win_fails() {
        // Any non-NoWin at this step is a different ending firing;
        // Tiamat win-state means the run hit the Tiamat ending, not CO.
        let mut inputs = ChainInputs::stub(carry_bow_snap(6, 4, Screen::Ending, WinState::Tiamat));
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn cosmic_carry_bow_ending_hundun_win_fails() {
        let mut inputs = ChainInputs::stub(carry_bow_snap(7, 4, Screen::Ending, WinState::Hundun));
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn cosmic_carry_bow_scores_in_base_camp_fails() {
        // Base camp scores after any run; the Tiamat WinState is what
        // arrived on-screen, but the run is over.
        let mut inputs = ChainInputs::stub(carry_bow_snap(1, 1, Screen::Scores, WinState::Tiamat));
        inputs.player_items.insert(entity_types::ITEM_HOUYIBOW);
        let result = cosmic::carry_bow_to_hundun(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // win_via_co: 4 cases.
    fn win_via_co_snap(win_state: WinState) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.win_state = win_state;
        snap
    }
    #[test]
    fn cosmic_win_via_co_no_win_stays_in_progress() {
        let inputs = ChainInputs::stub(win_via_co_snap(WinState::NoWin));
        let result = cosmic::win_via_co(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::win_via_co, "win_via_co");
    }
    #[test]
    fn cosmic_win_via_co_tiamat_fails() {
        let inputs = ChainInputs::stub(win_via_co_snap(WinState::Tiamat));
        let result = cosmic::win_via_co(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn cosmic_win_via_co_hundun_fails() {
        let inputs = ChainInputs::stub(win_via_co_snap(WinState::Hundun));
        let result = cosmic::win_via_co(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn cosmic_win_via_co_cosmic_ocean_stays_in_progress() {
        let inputs = ChainInputs::stub(win_via_co_snap(WinState::CosmicOcean));
        let result = cosmic::win_via_co(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, cosmic::win_via_co, "win_via_co");
    }

    // Eggplant.
    //
    // Same per-step direct-call pattern as Cosmic above. Uses
    // `companion_held_items` for held-item lookups and
    // `companion_types` for companion-type lookups (both HashSets on
    // `ChainInputs`).

    use chain_impl::eggplant;

    // collect_eggplant_item: 7 cases.
    fn eggplant_snap(world: u8, screen: Screen) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.screen = screen;
        snap
    }
    #[test]
    fn eggplant_collect_w1_empty_stays_unstarted() {
        let inputs = ChainInputs::stub(eggplant_snap(1, Screen::Level));
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn eggplant_collect_w1_player_holds_eggplant_advances() {
        let mut inputs = ChainInputs::stub(eggplant_snap(1, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_collect_w1_level_companion_holds_eggplant_stays_unstarted() {
        // Companion pickups only count during a level transition.
        let mut inputs = ChainInputs::stub(eggplant_snap(1, Screen::Level));
        inputs
            .companion_held_items
            .insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn eggplant_collect_w1_transition_companion_holds_eggplant_advances() {
        let mut inputs = ChainInputs::stub(eggplant_snap(1, Screen::LevelTransition));
        inputs
            .companion_held_items
            .insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_collect_w5_empty_stays_unstarted() {
        // Past bug: chain would start just because the player entered 5-1.
        let inputs = ChainInputs::stub(eggplant_snap(5, Screen::Level));
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn eggplant_collect_w5_last_chance_eggplant_advances() {
        let mut inputs = ChainInputs::stub(eggplant_snap(5, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_collect_w6_empty_fails() {
        let inputs = ChainInputs::stub(eggplant_snap(6, Screen::Level));
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // collect_eggplant_skip.
    #[test]
    fn eggplant_collect_w5_child_companion_advances_to_guide_step() {
        // Co-op edge case: the eggplant child can be picked up in
        // world 5 even without hand-carrying the eggplant.
        let mut inputs = ChainInputs::stub(eggplant_snap(5, Screen::Level));
        inputs
            .companion_types
            .insert(entity_types::CHAR_EGGPLANT_CHILD);
        let result = eggplant::collect_eggplant(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::guide_eggplant_child_to_71,
            "guide_eggplant_child_to_71",
        );
    }

    // carry_eggplant_to_51: 6 cases.
    #[test]
    fn eggplant_carry_w1_level_empty_stays() {
        // Within a level, whether the eggplant is on someone doesn't
        // matter; the check only fires at transitions.
        let inputs = ChainInputs::stub(eggplant_snap(1, Screen::Level));
        let result = eggplant::carry_eggplant_to_51(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_carry_w1_transition_player_holds_stays() {
        let mut inputs = ChainInputs::stub(eggplant_snap(1, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::carry_eggplant_to_51(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_carry_w1_transition_companion_holds_stays() {
        let mut inputs = ChainInputs::stub(eggplant_snap(1, Screen::LevelTransition));
        inputs
            .companion_held_items
            .insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::carry_eggplant_to_51(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_carry_w3_transition_waddler_stash_stays() {
        let mut inputs = ChainInputs::stub(eggplant_snap(3, Screen::LevelTransition));
        inputs.waddler_storage.insert(entity_types::ITEM_EGGPLANT);
        let result = eggplant::carry_eggplant_to_51(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::carry_eggplant_to_51,
            "carry_eggplant_to_51",
        );
    }
    #[test]
    fn eggplant_carry_w3_transition_lost_eggplant_resets_chain() {
        // Nobody's carrying at a mid-run transition, chain resets to
        // Unstarted; player can grab another this run.
        let inputs = ChainInputs::stub(eggplant_snap(3, Screen::LevelTransition));
        let result = eggplant::carry_eggplant_to_51(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn eggplant_carry_w5_level_advances_to_collect_child() {
        // Past world 4, hand off to the child-collection step
        // regardless of screen.
        let inputs = ChainInputs::stub(eggplant_snap(5, Screen::Level));
        let result = eggplant::carry_eggplant_to_51(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::collect_eggplant_child,
            "collect_eggplant_child",
        );
    }

    // collect_eggplant_child: 3 cases.
    #[test]
    fn eggplant_collect_child_w5_hiredhand_stays() {
        let mut inputs = ChainInputs::stub(eggplant_snap(5, Screen::Level));
        inputs.companion_types.insert(entity_types::CHAR_HIREDHAND);
        let result = eggplant::collect_eggplant_child(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::collect_eggplant_child,
            "collect_eggplant_child",
        );
    }
    #[test]
    fn eggplant_collect_child_w5_child_advances() {
        let mut inputs = ChainInputs::stub(eggplant_snap(5, Screen::Level));
        inputs
            .companion_types
            .insert(entity_types::CHAR_EGGPLANT_CHILD);
        let result = eggplant::collect_eggplant_child(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::guide_eggplant_child_to_71,
            "guide_eggplant_child_to_71",
        );
    }
    #[test]
    fn eggplant_collect_child_w6_hiredhand_fails() {
        // Past world 5 without a child companion = missed the pickup.
        let mut inputs = ChainInputs::stub(eggplant_snap(6, Screen::Level));
        inputs.companion_types.insert(entity_types::CHAR_HIREDHAND);
        let result = eggplant::collect_eggplant_child(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // guide_eggplant_child_to_71: 6 cases.
    fn eggplant_guide_snap(world: u8, level: u8, screen: Screen) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.screen = screen;
        snap
    }
    #[test]
    fn eggplant_guide_w5l1_level_child_stays() {
        let mut inputs = ChainInputs::stub(eggplant_guide_snap(5, 1, Screen::Level));
        inputs
            .companion_types
            .insert(entity_types::CHAR_EGGPLANT_CHILD);
        let result = eggplant::guide_eggplant_child_to_71(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::guide_eggplant_child_to_71,
            "guide_eggplant_child_to_71",
        );
    }
    #[test]
    fn eggplant_guide_w6l1_level_hiredhand_stays_until_transition() {
        let mut inputs = ChainInputs::stub(eggplant_guide_snap(6, 1, Screen::Level));
        inputs.companion_types.insert(entity_types::CHAR_HIREDHAND);
        let result = eggplant::guide_eggplant_child_to_71(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::guide_eggplant_child_to_71,
            "guide_eggplant_child_to_71",
        );
    }
    #[test]
    fn eggplant_guide_w6l1_transition_hiredhand_fails() {
        // At a mid-run transition without the child companion, the
        // child has been lost.
        let mut inputs = ChainInputs::stub(eggplant_guide_snap(6, 1, Screen::LevelTransition));
        inputs.companion_types.insert(entity_types::CHAR_HIREDHAND);
        let result = eggplant::guide_eggplant_child_to_71(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn eggplant_guide_w6l1_transition_child_stays() {
        let mut inputs = ChainInputs::stub(eggplant_guide_snap(6, 1, Screen::LevelTransition));
        inputs
            .companion_types
            .insert(entity_types::CHAR_EGGPLANT_CHILD);
        let result = eggplant::guide_eggplant_child_to_71(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::guide_eggplant_child_to_71,
            "guide_eggplant_child_to_71",
        );
    }
    #[test]
    fn eggplant_guide_w7l1_transition_hiredhand_advances() {
        // At the 7-1 transition specifically the child gets transferred
        // to the statue off-screen, the HIREDHAND companion type is
        // fine because the child left frame legitimately.
        let mut inputs = ChainInputs::stub(eggplant_guide_snap(7, 1, Screen::LevelTransition));
        inputs.companion_types.insert(entity_types::CHAR_HIREDHAND);
        let result = eggplant::guide_eggplant_child_to_71(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::visit_eggplant_world,
            "visit_eggplant_world",
        );
    }
    #[test]
    fn eggplant_guide_w7l2_hiredhand_advances_to_visit_eggplant_world() {
        // Past 7-1 the child is expected to already be at the statue;
        // the chain moves on regardless of what's still following.
        let mut inputs = ChainInputs::stub(eggplant_guide_snap(7, 2, Screen::Level));
        inputs.companion_types.insert(entity_types::CHAR_HIREDHAND);
        let result = eggplant::guide_eggplant_child_to_71(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::visit_eggplant_world,
            "visit_eggplant_world",
        );
    }

    // visit_eggplant_world: 3 cases.
    fn eggplant_visit_snap(world: u8, level: u8, theme: Theme) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.theme = theme;
        snap
    }
    #[test]
    fn eggplant_visit_w7l1_sunken_city_stays() {
        let inputs = ChainInputs::stub(eggplant_visit_snap(7, 1, Theme::SunkenCity));
        let result = eggplant::visit_eggplant_world(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::visit_eggplant_world,
            "visit_eggplant_world",
        );
    }
    #[test]
    fn eggplant_visit_w7l2_sunken_city_fails() {
        // Missed the eggplant-world entry.
        let inputs = ChainInputs::stub(eggplant_visit_snap(7, 2, Theme::SunkenCity));
        let result = eggplant::visit_eggplant_world(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn eggplant_visit_w7l2_eggplant_world_advances() {
        let inputs = ChainInputs::stub(eggplant_visit_snap(7, 2, Theme::EggplantWorld));
        let result = eggplant::visit_eggplant_world(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::collect_eggplant_crown,
            "collect_eggplant_crown",
        );
    }

    // collect_eggplant_crown: 3 cases.
    fn eggplant_crown_snap(world: u8, level: u8) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap
    }
    #[test]
    fn eggplant_crown_w7l2_no_crown_stays() {
        let inputs = ChainInputs::stub(eggplant_crown_snap(7, 2));
        let result = eggplant::collect_eggplant_crown(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(
            &result,
            eggplant::collect_eggplant_crown,
            "collect_eggplant_crown",
        );
    }
    #[test]
    fn eggplant_crown_w7l2_with_crown_advances_to_success() {
        let mut inputs = ChainInputs::stub(eggplant_crown_snap(7, 2));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_EGGPLANTCROWN);
        let result = eggplant::collect_eggplant_crown(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, eggplant::success, "success");
    }
    #[test]
    fn eggplant_crown_w7l3_no_crown_fails() {
        // Past 7-2 without the crown = missed pickup.
        let inputs = ChainInputs::stub(eggplant_crown_snap(7, 3));
        let result = eggplant::collect_eggplant_crown(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // Sunken (Abzu / Duat).
    //
    // The two variants don't share code (see the comment atop
    // `chain_impl/sunken.rs`), so the shared behavior is tested
    // against `abzu` and only duat-specific tests
    // (`carry_scepter_to_42`, `visit_city_of_gold`, `keep_ankh`)
    // run against `duat`. `collect_excalibur` is abzu-specific.

    use chain_impl::sunken::{abzu, duat};

    fn sunken_snap(world: u8) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap
    }

    // collect_eye_or_headwear: 6 cases.
    #[test]
    fn sunken_collect_eye_or_headwear_w1_empty_stays_unstarted() {
        let inputs = ChainInputs::stub(sunken_snap(1));
        let result = abzu::collect_eye_or_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn sunken_collect_eye_or_headwear_w1_udjat_eye_advances() {
        let mut inputs = ChainInputs::stub(sunken_snap(1));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_UDJATEYE);
        let result = abzu::collect_eye_or_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_headwear, "collect_headwear");
    }
    #[test]
    fn sunken_collect_eye_or_headwear_w2_empty_stays_unstarted() {
        let inputs = ChainInputs::stub(sunken_snap(2));
        let result = abzu::collect_eye_or_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::Unstarted);
    }
    #[test]
    fn sunken_collect_eye_or_headwear_w2_crown_advances_to_ankh() {
        let mut inputs = ChainInputs::stub(sunken_snap(2));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_eye_or_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_ankh, "collect_ankh");
    }
    #[test]
    fn sunken_collect_eye_or_headwear_w2_hedjet_advances_to_ankh() {
        let mut inputs = ChainInputs::stub(sunken_snap(2));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_HEDJET);
        let result = abzu::collect_eye_or_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_ankh, "collect_ankh");
    }
    #[test]
    fn sunken_collect_eye_or_headwear_w3_empty_fails() {
        let inputs = ChainInputs::stub(sunken_snap(3));
        let result = abzu::collect_eye_or_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // collect_headwear: 5 cases.
    #[test]
    fn sunken_collect_headwear_w1_udjat_only_stays() {
        let mut inputs = ChainInputs::stub(sunken_snap(1));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_UDJATEYE);
        let result = abzu::collect_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_headwear, "collect_headwear");
    }
    #[test]
    fn sunken_collect_headwear_w2_udjat_only_stays() {
        let mut inputs = ChainInputs::stub(sunken_snap(2));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_UDJATEYE);
        let result = abzu::collect_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_headwear, "collect_headwear");
    }
    #[test]
    fn sunken_collect_headwear_w2_udjat_plus_crown_advances() {
        let mut inputs = ChainInputs::stub(sunken_snap(2));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_UDJATEYE);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_ankh, "collect_ankh");
    }
    #[test]
    fn sunken_collect_headwear_w2_udjat_plus_hedjet_advances() {
        let mut inputs = ChainInputs::stub(sunken_snap(2));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_UDJATEYE);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_HEDJET);
        let result = abzu::collect_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_ankh, "collect_ankh");
    }
    #[test]
    fn sunken_collect_headwear_w3_only_udjat_fails() {
        let mut inputs = ChainInputs::stub(sunken_snap(3));
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_UDJATEYE);
        let result = abzu::collect_headwear(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // collect_ankh: 4 cases.
    #[test]
    fn sunken_collect_ankh_w3_crown_only_stays() {
        let mut inputs = ChainInputs::stub(sunken_snap(3));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_ankh, "collect_ankh");
    }
    #[test]
    fn sunken_collect_ankh_w3_with_ankh_advances() {
        let mut inputs = ChainInputs::stub(sunken_snap(3));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = abzu::collect_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::visit_world41_theme, "visit_world41_theme");
    }
    #[test]
    fn sunken_collect_ankh_w4_empty_fails() {
        let inputs = ChainInputs::stub(sunken_snap(4));
        let result = abzu::collect_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn sunken_collect_ankh_w4_crown_no_ankh_fails() {
        let mut inputs = ChainInputs::stub(sunken_snap(4));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // visit_world41_theme: 3 cases.
    fn sunken_visit41_snap(world: u8, theme: Theme) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.theme = theme;
        snap
    }
    #[test]
    fn sunken_visit_world41_w3_olmec_stays() {
        let inputs = ChainInputs::stub(sunken_visit41_snap(3, Theme::Olmec));
        let result = abzu::visit_world41_theme(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::visit_world41_theme, "visit_world41_theme");
    }
    #[test]
    fn sunken_visit_world41_w4_temple_fails_for_abzu() {
        // Abzu wants TidePool; Temple is Duat's world-4-1.
        let inputs = ChainInputs::stub(sunken_visit41_snap(4, Theme::Temple));
        let result = abzu::visit_world41_theme(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn sunken_visit_world41_w4_tide_pool_advances_for_abzu() {
        // The abzu chain advances to `collect_excalibur` when
        // world41 = TidePool.
        let inputs = ChainInputs::stub(sunken_visit41_snap(4, Theme::TidePool));
        let result = abzu::visit_world41_theme(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_excalibur, "collect_excalibur");
    }

    // visit_world44_theme: 4 cases.
    fn sunken_visit44_snap(world: u8, level: u8, theme: Theme) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.theme = theme;
        snap
    }
    #[test]
    fn sunken_visit_world44_w4l2_tide_pool_stays() {
        let inputs = ChainInputs::stub(sunken_visit44_snap(4, 2, Theme::TidePool));
        let result = abzu::visit_world44_theme(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::visit_world44_theme, "visit_world44_theme");
    }
    #[test]
    fn sunken_visit_world44_w4l3_tide_pool_stays() {
        let inputs = ChainInputs::stub(sunken_visit44_snap(4, 3, Theme::TidePool));
        let result = abzu::visit_world44_theme(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::visit_world44_theme, "visit_world44_theme");
    }
    #[test]
    fn sunken_visit_world44_w4l4_tide_pool_fails() {
        let inputs = ChainInputs::stub(sunken_visit44_snap(4, 4, Theme::TidePool));
        let result = abzu::visit_world44_theme(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn sunken_visit_world44_w4l4_abzu_advances() {
        let inputs = ChainInputs::stub(sunken_visit44_snap(4, 4, Theme::Abzu));
        let result = abzu::visit_world44_theme(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_tablet, "collect_tablet");
    }

    // collect_tablet: 3 cases.
    #[test]
    fn sunken_collect_tablet_w4_crown_only_stays() {
        let mut inputs = ChainInputs::stub(sunken_snap(4));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_tablet(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_tablet, "collect_tablet");
    }
    #[test]
    fn sunken_collect_tablet_w4_with_tablet_advances() {
        let mut inputs = ChainInputs::stub(sunken_snap(4));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        let result = abzu::collect_tablet(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::carry_ushabti_to_63, "carry_ushabti_to_63");
    }
    #[test]
    fn sunken_collect_tablet_w5_no_tablet_fails() {
        let mut inputs = ChainInputs::stub(sunken_snap(5));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_tablet(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // carry_ushabti_to_63: 6 cases.
    fn sunken_ushabti_snap(world: u8, level: u8, screen: Screen) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.screen = screen;
        snap
    }
    #[test]
    fn sunken_carry_ushabti_w4l4_level_stays() {
        let mut inputs = ChainInputs::stub(sunken_ushabti_snap(4, 4, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        let result = abzu::carry_ushabti_to_63(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::carry_ushabti_to_63, "carry_ushabti_to_63");
    }
    #[test]
    fn sunken_carry_ushabti_w6l1_transition_stays() {
        let mut inputs = ChainInputs::stub(sunken_ushabti_snap(6, 1, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        let result = abzu::carry_ushabti_to_63(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::carry_ushabti_to_63, "carry_ushabti_to_63");
    }
    #[test]
    fn sunken_carry_ushabti_w6l2_level_stays() {
        let mut inputs = ChainInputs::stub(sunken_ushabti_snap(6, 2, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        let result = abzu::carry_ushabti_to_63(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::carry_ushabti_to_63, "carry_ushabti_to_63");
    }
    #[test]
    fn sunken_carry_ushabti_w6l2_transition_no_ushabti_fails() {
        // At the 6-2 -> 6-3 transition without ushabti = missed pickup.
        let mut inputs = ChainInputs::stub(sunken_ushabti_snap(6, 2, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        let result = abzu::carry_ushabti_to_63(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn sunken_carry_ushabti_w6l2_transition_player_has_ushabti_advances() {
        let mut inputs = ChainInputs::stub(sunken_ushabti_snap(6, 2, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        inputs.player_items.insert(entity_types::ITEM_USHABTI);
        let result = abzu::carry_ushabti_to_63(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::win_via_hundun_or_co, "win_via_hundun_or_co");
    }
    #[test]
    fn sunken_carry_ushabti_w6l2_transition_companion_has_ushabti_advances() {
        let mut inputs = ChainInputs::stub(sunken_ushabti_snap(6, 2, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs
            .player_items
            .insert(entity_types::ITEM_POWERUP_TABLETOFDESTINY);
        inputs
            .companion_held_items
            .insert(entity_types::ITEM_USHABTI);
        let result = abzu::carry_ushabti_to_63(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::win_via_hundun_or_co, "win_via_hundun_or_co");
    }

    // win_via_hundun_or_co: 4 cases.
    fn sunken_win_snap(win_state: WinState) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.win_state = win_state;
        snap
    }
    #[test]
    fn sunken_win_via_hundun_or_co_no_win_stays() {
        let inputs = ChainInputs::stub(sunken_win_snap(WinState::NoWin));
        let result = abzu::win_via_hundun_or_co(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::win_via_hundun_or_co, "win_via_hundun_or_co");
    }
    #[test]
    fn sunken_win_via_hundun_or_co_tiamat_fails() {
        // Only Tiamat fails; Hundun / CO are legitimate sunken endings.
        let inputs = ChainInputs::stub(sunken_win_snap(WinState::Tiamat));
        let result = abzu::win_via_hundun_or_co(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn sunken_win_via_hundun_or_co_hundun_stays() {
        let inputs = ChainInputs::stub(sunken_win_snap(WinState::Hundun));
        let result = abzu::win_via_hundun_or_co(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::win_via_hundun_or_co, "win_via_hundun_or_co");
    }
    #[test]
    fn sunken_win_via_hundun_or_co_cosmic_ocean_stays() {
        let inputs = ChainInputs::stub(sunken_win_snap(WinState::CosmicOcean));
        let result = abzu::win_via_hundun_or_co(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::win_via_hundun_or_co, "win_via_hundun_or_co");
    }

    // Abzu-specific: collect_excalibur, 5 cases.
    fn abzu_excalibur_snap(world: u8, level: u8) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap
    }
    #[test]
    fn abzu_collect_excalibur_w3l1_no_excalibur_stays() {
        let mut inputs = ChainInputs::stub(abzu_excalibur_snap(3, 1));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = abzu::collect_excalibur(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_excalibur, "collect_excalibur");
    }
    #[test]
    fn abzu_collect_excalibur_w4l1_losing_ankh_is_ok() {
        // Once past world 3 the Ankh has done its job, losing it
        // doesn't fail the chain.
        let mut inputs = ChainInputs::stub(abzu_excalibur_snap(4, 1));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = abzu::collect_excalibur(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_excalibur, "collect_excalibur");
    }
    #[test]
    fn abzu_collect_excalibur_w4l2_no_excalibur_stays() {
        let mut inputs = ChainInputs::stub(abzu_excalibur_snap(4, 2));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = abzu::collect_excalibur(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::collect_excalibur, "collect_excalibur");
    }
    #[test]
    fn abzu_collect_excalibur_w4l2_with_excalibur_advances() {
        let mut inputs = ChainInputs::stub(abzu_excalibur_snap(4, 2));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        inputs.player_items.insert(entity_types::ITEM_EXCALIBUR);
        let result = abzu::collect_excalibur(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, abzu::visit_world44_theme, "visit_world44_theme");
    }
    #[test]
    fn abzu_collect_excalibur_w4l3_no_excalibur_fails() {
        let mut inputs = ChainInputs::stub(abzu_excalibur_snap(4, 3));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = abzu::collect_excalibur(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }

    // Duat-specific: carry_scepter_to_42, 8 cases.
    fn duat_scepter_snap(world: u8, level: u8, screen: Screen) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.screen = screen;
        snap
    }
    #[test]
    fn duat_carry_scepter_w3l1_level_no_scepter_stays() {
        let mut inputs = ChainInputs::stub(duat_scepter_snap(3, 1, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::carry_scepter_to_42, "carry_scepter_to_42");
    }
    #[test]
    fn duat_carry_scepter_w4l1_level_no_scepter_stays() {
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 1, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::carry_scepter_to_42, "carry_scepter_to_42");
    }
    #[test]
    fn duat_carry_scepter_w4l1_no_ankh_fails() {
        // Ankh is a hard requirement to even reach Duat.
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 1, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn duat_carry_scepter_w4l1_level_with_scepter_stays() {
        // Scepter check only fires at the specific 4-1 transition,
        // so a mid-level pickup still stays at the same step.
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 1, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        inputs.player_items.insert(entity_types::ITEM_SCEPTER);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::carry_scepter_to_42, "carry_scepter_to_42");
    }
    #[test]
    fn duat_carry_scepter_w4l1_transition_no_scepter_fails() {
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 1, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn duat_carry_scepter_w4l1_transition_player_has_scepter_advances() {
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 1, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        inputs.player_items.insert(entity_types::ITEM_SCEPTER);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::visit_city_of_gold, "visit_city_of_gold");
    }
    #[test]
    fn duat_carry_scepter_w4l1_transition_companion_has_scepter_advances() {
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 1, Screen::LevelTransition));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        inputs
            .companion_held_items
            .insert(entity_types::ITEM_SCEPTER);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::visit_city_of_gold, "visit_city_of_gold");
    }
    #[test]
    fn duat_carry_scepter_w4l3_scepter_moot_advances_to_cog() {
        // Past 4-2 the scepter has already done its job (or wasn't
        // needed); jump straight to the CoG step.
        let mut inputs = ChainInputs::stub(duat_scepter_snap(4, 3, Screen::Level));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::carry_scepter_to_42(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::visit_city_of_gold, "visit_city_of_gold");
    }

    // Duat-specific: visit_city_of_gold, 4 cases.
    fn duat_cog_snap(world: u8, level: u8, theme: Theme) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap.theme = theme;
        snap
    }
    #[test]
    fn duat_visit_cog_w4l2_temple_stays() {
        let mut inputs = ChainInputs::stub(duat_cog_snap(4, 2, Theme::Temple));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::visit_city_of_gold(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::visit_city_of_gold, "visit_city_of_gold");
    }
    #[test]
    fn duat_visit_cog_w4l2_temple_no_ankh_fails() {
        // Reaching Duat requires the Ankh survives to the CoG altar.
        let inputs = ChainInputs::stub(duat_cog_snap(4, 2, Theme::Temple));
        let result = duat::visit_city_of_gold(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn duat_visit_cog_w4l3_temple_fails() {
        let mut inputs = ChainInputs::stub(duat_cog_snap(4, 3, Theme::Temple));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::visit_city_of_gold(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn duat_visit_cog_w4l3_city_of_gold_advances_to_keep_ankh() {
        let mut inputs = ChainInputs::stub(duat_cog_snap(4, 3, Theme::CityOfGold));
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::visit_city_of_gold(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::keep_ankh, "keep_ankh");
    }

    // Duat-specific: keep_ankh, 5 cases. The player-state matrix
    // is the load-bearing set: stunned player without Ankh must stay
    // in-progress (they're mid-altar), sacrifice frame
    // (`player0_char_state == None`) must stay in-progress, and past
    // 4-3 skip forward regardless.
    fn duat_keep_ankh_snap(world: u8, level: u8) -> StateSnapshot {
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.level = level;
        snap
    }
    #[test]
    fn duat_keep_ankh_w4l3_ankh_kept_stays() {
        let mut inputs = ChainInputs::stub(duat_keep_ankh_snap(4, 3));
        inputs.player0_char_state = Some(CharState::Standing);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_ANKH);
        let result = duat::keep_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::keep_ankh, "keep_ankh");
    }
    #[test]
    fn duat_keep_ankh_w4l3_standing_no_ankh_fails() {
        // Player up and not stunned + no ankh = ankh was used too
        // early; can't reach Duat.
        let mut inputs = ChainInputs::stub(duat_keep_ankh_snap(4, 3));
        inputs.player0_char_state = Some(CharState::Standing);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = duat::keep_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::Failed);
    }
    #[test]
    fn duat_keep_ankh_w4l3_stunned_no_ankh_stays() {
        // Mid-altar: stunned skips the ankh check.
        let mut inputs = ChainInputs::stub(duat_keep_ankh_snap(4, 3));
        inputs.player0_char_state = Some(CharState::Stunned);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = duat::keep_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::keep_ankh, "keep_ankh");
    }
    #[test]
    fn duat_keep_ankh_w4l3_no_player_sacrifice_frame_stays() {
        // Sacrifice destroys the player briefly; `player0_char_state`
        // is None and the ankh check is skipped.
        let inputs = ChainInputs::stub(duat_keep_ankh_snap(4, 3));
        let result = duat::keep_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::keep_ankh, "keep_ankh");
    }
    #[test]
    fn duat_keep_ankh_w4l4_advances_regardless() {
        // Past 4-3 the run is headed for Duat; the ankh has done its
        // job.
        let mut inputs = ChainInputs::stub(duat_keep_ankh_snap(4, 4));
        inputs.player0_char_state = Some(CharState::Standing);
        inputs.player_items.insert(entity_types::ITEM_POWERUP_CROWN);
        let result = duat::keep_ankh(&inputs);
        assert_eq!(result.status, ChainStatus::InProgress);
        assert_next_step_is(&result, duat::visit_world44_theme, "visit_world44_theme");
    }

    // RunState: primary category rendering paths.

    use runstate::{CategoryTrackerConfig, RunState};

    fn make_runstate_at(theme: Theme, world: u8, level: u8) -> (RunState, ChainInputs) {
        let mut snap = empty_snapshot();
        snap.theme = theme;
        snap.world = world;
        snap.level = level;
        let inputs = ChainInputs::stub(snap);
        (RunState::new(), inputs)
    }

    #[test]
    fn runstate_default_render_shows_no_percent() {
        // Fresh RunState + fresh inputs = default RunLabel output.
        // update() early-returns without a player, so state and label
        // stay at their initial values. On the SCORES screen hide_early
        // is bypassed, yielding the same string RunLabel produces on
        // its own.
        let (rs, _inputs) = make_runstate_at(Theme::Dwelling, 1, 1);
        let cfg = CategoryTrackerConfig {
            always_show_modifiers: true,
            excluded_categories: vec![],
        };
        // Screen::Scores or always_show_modifiers=true both flip on
        // full render; either satisfies the check.
        assert_eq!(rs.get_display(Screen::Scores, &cfg), "Pacifist No%");
    }

    #[test]
    fn runstate_hide_early_matches_run_label() {
        let (rs, _inputs) = make_runstate_at(Theme::Dwelling, 1, 1);
        let cfg = CategoryTrackerConfig {
            always_show_modifiers: false,
            excluded_categories: vec![],
        };
        // Early in a run (world 1, level 1, no death), should_show
        // returns false; RunLabel renders with hide_early=true.
        assert_eq!(rs.get_display(Screen::Level, &cfg), "No%");
    }

    #[test]
    fn runstate_pacifist_drops_when_flag_missing() {
        let (mut rs, mut inputs) = make_runstate_at(Theme::Dwelling, 3, 1);
        // Simulate a kill: clear PACIFIST from run_recap_flags.
        inputs.state.run_recap_flags = RunRecapFlags::empty();
        // Populate player0 so update() doesn't early-return.
        inputs.player0 = Some(chain_impl::inputs::PlayerSnapshot {
            health: 4,
            state: entity::CharState::Standing,
            last_state: entity::CharState::Standing,
            layer: 0,
            position_x: 0.0,
            position_y: 0.0,
            velocity_x: 0.0,
            velocity_y: 0.0,
            inventory: chain_impl::inputs::InventorySnapshot {
                money: 0,
                bombs: 4,
                ropes: 4,
                kills_total: 0,
                collected_money_total: 0,
                cursed: false,
            },
            overlay_type: None,
            overlay_tamed_mount: false,
        });
        rs.update(&inputs, &empty_process());
        assert!(!rs.run_label.contains(Label::Pacifist));
    }

    #[test]
    fn runstate_score_run_when_holding_plasma_cannon() {
        let (mut rs, mut inputs) = make_runstate_at(Theme::Dwelling, 3, 1);
        inputs.player0 = Some(chain_impl::inputs::PlayerSnapshot {
            health: 4,
            state: entity::CharState::Standing,
            last_state: entity::CharState::Standing,
            layer: 0,
            position_x: 0.0,
            position_y: 0.0,
            velocity_x: 0.0,
            velocity_y: 0.0,
            inventory: chain_impl::inputs::InventorySnapshot {
                money: 0,
                bombs: 4,
                ropes: 4,
                kills_total: 0,
                collected_money_total: 0,
                cursed: false,
            },
            overlay_type: None,
            overlay_tamed_mount: false,
        });
        inputs.player_items.insert(entity_types::ITEM_PLASMACANNON);
        rs.update(&inputs, &empty_process());
        assert!(rs.run_label.contains(Label::Score));
    }

    // RunState update methods.
    //
    // All of these directly poke `pub(crate)` fields on `RunState` /
    // `ChainInputs` and call one specific `update_*` method.
    // FakeStepper equivalence goes through
    // `ChainStepper::set_last_status_for_test`.

    use chain::ChainStatus;
    use chain_impl::inputs::{InventorySnapshot, PlayerSnapshot};
    use entity::CharState;

    /// Player at level start with 4 health, 4 bombs, 4 ropes, no
    /// modifiers. Individual tests mutate the fields they care about.
    fn default_player() -> PlayerSnapshot {
        PlayerSnapshot {
            health: 4,
            state: CharState::Standing,
            last_state: CharState::Standing,
            layer: 0,
            position_x: 0.0,
            position_y: 0.0,
            velocity_x: 0.0,
            velocity_y: 0.0,
            inventory: InventorySnapshot {
                money: 0,
                bombs: 4,
                ropes: 4,
                kills_total: 0,
                collected_money_total: 0,
                cursed: false,
            },
            overlay_type: None,
            overlay_tamed_mount: false,
        }
    }

    // final_death: 4 cases.
    #[test]
    fn runstate_final_death_standing_stays_false() {
        let mut rs = RunState::new();
        rs.update_final_death(CharState::Standing, &Default::default());
        assert!(!rs.final_death);
    }
    #[test]
    fn runstate_final_death_dying_with_ankh_stays_false() {
        let mut rs = RunState::new();
        let mut items = std::collections::HashSet::new();
        items.insert(entity_types::ITEM_POWERUP_ANKH);
        rs.update_final_death(CharState::Dying, &items);
        assert!(!rs.final_death);
    }
    #[test]
    fn runstate_final_death_dying_no_ankh_sets_final() {
        let mut rs = RunState::new();
        rs.update_final_death(CharState::Dying, &Default::default());
        assert!(rs.final_death);
    }
    #[test]
    fn runstate_final_death_dying_with_paste_sets_final() {
        // Paste isn't Ankh, so it doesn't save the run.
        let mut rs = RunState::new();
        let mut items = std::collections::HashSet::new();
        items.insert(entity_types::ITEM_POWERUP_PASTE);
        rs.update_final_death(CharState::Dying, &items);
        assert!(rs.final_death);
    }

    // starting_resources_health: 7 cases.
    fn assert_low_no(rs: &RunState, expected_low: bool, expected_no: bool) {
        assert_eq!(
            rs.run_label.contains(Label::Low),
            expected_low,
            "Label::Low"
        );
        assert_eq!(rs.run_label.contains(Label::No), expected_no, "Label::No");
    }
    #[test]
    fn runstate_starting_health_standing_4_to_4_stays_both() {
        let mut rs = RunState::new();
        rs.health = 4;
        let mut player = default_player();
        player.state = CharState::Standing;
        player.health = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_eq!(rs.health, 4);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_health_standing_2_to_1_drops_no() {
        let mut rs = RunState::new();
        rs.health = 2;
        let mut player = default_player();
        player.health = 1;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_eq!(rs.health, 1);
        assert_low_no(&rs, true, false);
    }
    #[test]
    fn runstate_starting_health_standing_3_to_1_drops_no() {
        let mut rs = RunState::new();
        rs.health = 3;
        let mut player = default_player();
        player.health = 1;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, true, false);
    }
    #[test]
    fn runstate_starting_health_dying_1_to_4_stays_both() {
        // Dying doesn't count as a health gain.
        let mut rs = RunState::new();
        rs.health = 1;
        let mut player = default_player();
        player.state = CharState::Dying;
        player.health = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_eq!(rs.health, 4);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_health_standing_1_to_2_fails_low() {
        let mut rs = RunState::new();
        rs.health = 1;
        let mut player = default_player();
        player.health = 2;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }
    #[test]
    fn runstate_starting_health_standing_2_to_4_fails_low() {
        let mut rs = RunState::new();
        rs.health = 2;
        let mut player = default_player();
        player.health = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }
    #[test]
    fn runstate_starting_health_5_to_5_fails_low() {
        // Health above 4 always fails Low (natural cap), even if it
        // didn't strictly increase.
        let mut rs = RunState::new();
        rs.health = 5;
        let mut player = default_player();
        player.health = 5;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }

    // starting_resources_bombs: 5 cases.
    #[test]
    fn runstate_starting_bombs_4_to_4_stays_both() {
        let mut rs = RunState::new();
        rs.bombs = 4;
        let mut player = default_player();
        player.inventory.bombs = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_eq!(rs.bombs, 4);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_bombs_4_to_3_drops_no() {
        let mut rs = RunState::new();
        rs.bombs = 4;
        let mut player = default_player();
        player.inventory.bombs = 3;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, true, false);
    }
    #[test]
    fn runstate_starting_bombs_3_to_1_drops_no() {
        let mut rs = RunState::new();
        rs.bombs = 3;
        let mut player = default_player();
        player.inventory.bombs = 1;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, true, false);
    }
    #[test]
    fn runstate_starting_bombs_7_to_7_fails_low() {
        // Bombs above 4 always fail Low.
        let mut rs = RunState::new();
        rs.bombs = 7;
        let mut player = default_player();
        player.inventory.bombs = 7;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }
    #[test]
    fn runstate_starting_bombs_1_to_4_fails_low() {
        // Gained bombs = Low fail.
        let mut rs = RunState::new();
        rs.bombs = 1;
        let mut player = default_player();
        player.inventory.bombs = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }

    // starting_resources_ropes: 7 cases.
    #[test]
    fn runstate_starting_ropes_lsr4_4_to_4_no_win_stays_both() {
        let mut rs = RunState::new();
        rs.level_start_ropes = 4;
        rs.ropes = 4;
        let mut player = default_player();
        player.inventory.ropes = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_eq!(rs.ropes, 4);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_ropes_lsr4_4_to_3_no_win_stays_both() {
        // Rope loss during the run is potentially temporary, so
        // don't drop No until the win screen.
        let mut rs = RunState::new();
        rs.level_start_ropes = 4;
        rs.ropes = 4;
        let mut player = default_player();
        player.inventory.ropes = 3;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_ropes_lsr4_4_to_3_tiamat_drops_no() {
        // Post-win rope loss is permanent, the run is over.
        let mut rs = RunState::new();
        rs.level_start_ropes = 4;
        rs.ropes = 4;
        let mut player = default_player();
        player.inventory.ropes = 3;
        rs.update_starting_resources(&player, WinState::Tiamat);
        assert_low_no(&rs, true, false);
    }
    #[test]
    fn runstate_starting_ropes_lsr3_3_to_1_no_win_stays_both() {
        let mut rs = RunState::new();
        rs.level_start_ropes = 3;
        rs.ropes = 3;
        let mut player = default_player();
        player.inventory.ropes = 1;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_ropes_lsr3_2_to_3_no_win_stays_both() {
        // Refilling ropes below level_start_ropes is fine.
        let mut rs = RunState::new();
        rs.level_start_ropes = 3;
        rs.ropes = 2;
        let mut player = default_player();
        player.inventory.ropes = 3;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, true, true);
    }
    #[test]
    fn runstate_starting_ropes_lsr7_7_to_7_fails_low() {
        // Ropes above 4 always fail low, even if level_start_ropes
        // was also above 4.
        let mut rs = RunState::new();
        rs.level_start_ropes = 7;
        rs.ropes = 7;
        let mut player = default_player();
        player.inventory.ropes = 7;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }
    #[test]
    fn runstate_starting_ropes_lsr1_1_to_4_fails_low() {
        let mut rs = RunState::new();
        rs.level_start_ropes = 1;
        rs.ropes = 1;
        let mut player = default_player();
        player.inventory.ropes = 4;
        rs.update_starting_resources(&player, WinState::NoWin);
        assert_low_no(&rs, false, false);
    }

    // status_effects_poisoned: 6 cases.
    #[test]
    fn runstate_status_poisoned_new_poison_stays_low() {
        let mut rs = RunState::new();
        rs.poisoned = false;
        let mut items = std::collections::HashSet::new();
        items.insert(entity_types::LOGICAL_POISONED_EFFECT);
        rs.update_status_effects(CharState::Standing, &items);
        assert!(rs.poisoned);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_poisoned_ongoing_poison_stays_low() {
        let mut rs = RunState::new();
        rs.poisoned = true;
        let mut items = std::collections::HashSet::new();
        items.insert(entity_types::LOGICAL_POISONED_EFFECT);
        rs.update_status_effects(CharState::Standing, &items);
        assert!(rs.poisoned);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_poisoned_recovered_while_standing_fails_low() {
        // Losing poison outside of death = it wore off, which means
        // low% wasn't preserved.
        let mut rs = RunState::new();
        rs.poisoned = true;
        rs.update_status_effects(CharState::Standing, &Default::default());
        assert!(!rs.poisoned);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_poisoned_recovered_while_dying_stays_low() {
        // Dying clears the effect and doesn't invalidate low%.
        let mut rs = RunState::new();
        rs.poisoned = true;
        rs.update_status_effects(CharState::Dying, &Default::default());
        assert!(!rs.poisoned);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_poisoned_skipped_while_entering() {
        // ENTERING / LOADING skip the check entirely.
        let mut rs = RunState::new();
        rs.poisoned = true;
        rs.update_status_effects(CharState::Entering, &Default::default());
        assert!(rs.poisoned);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_poisoned_skipped_while_loading() {
        let mut rs = RunState::new();
        rs.poisoned = true;
        rs.update_status_effects(CharState::Loading, &Default::default());
        assert!(rs.poisoned);
        assert!(rs.run_label.contains(Label::Low));
    }

    // status_effects_cursed: 6 cases.
    #[test]
    fn runstate_status_cursed_new_curse_stays_low() {
        let mut rs = RunState::new();
        rs.cursed = false;
        let mut items = std::collections::HashSet::new();
        items.insert(entity_types::LOGICAL_CURSED_EFFECT);
        rs.update_status_effects(CharState::Standing, &items);
        assert!(rs.cursed);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_cursed_ongoing_curse_stays_low() {
        let mut rs = RunState::new();
        rs.cursed = true;
        let mut items = std::collections::HashSet::new();
        items.insert(entity_types::LOGICAL_CURSED_EFFECT);
        rs.update_status_effects(CharState::Standing, &items);
        assert!(rs.cursed);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_cursed_recovered_while_standing_fails_low() {
        let mut rs = RunState::new();
        rs.cursed = true;
        rs.update_status_effects(CharState::Standing, &Default::default());
        assert!(!rs.cursed);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_cursed_recovered_while_dying_stays_low() {
        let mut rs = RunState::new();
        rs.cursed = true;
        rs.update_status_effects(CharState::Dying, &Default::default());
        assert!(!rs.cursed);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_cursed_skipped_while_entering() {
        let mut rs = RunState::new();
        rs.cursed = true;
        rs.update_status_effects(CharState::Entering, &Default::default());
        assert!(rs.cursed);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_status_cursed_skipped_while_loading() {
        let mut rs = RunState::new();
        rs.cursed = true;
        rs.update_status_effects(CharState::Loading, &Default::default());
        assert!(rs.cursed);
        assert!(rs.run_label.contains(Label::Low));
    }

    // had_clover_time: 9 cases.
    fn t2f(m: u32, s: u32) -> u32 {
        runstate::time_to_frames(m, s)
    }
    #[test]
    fn runstate_had_clover_no_clover_no_flag_short_time_stays_low() {
        let mut rs = RunState::new();
        rs.update_had_clover(t2f(1, 0), HudFlags::empty());
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_no_clover_no_flag_long_time_stays_low() {
        // Without HAVE_CLOVER, elapsed time is irrelevant.
        let mut rs = RunState::new();
        rs.update_had_clover(t2f(4, 0), HudFlags::empty());
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_flag_absent_bitmask_stays_low() {
        // ~HAVE_CLOVER (every flag except HAVE_CLOVER) behaves the same
        // as empty; the check gate is
        // `!hud_flags.contains(HAVE_CLOVER)`.
        let mut rs = RunState::new();
        rs.update_had_clover(t2f(4, 0), !HudFlags::HAVE_CLOVER);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_not_cursed_under_threshold_stays_low() {
        let mut rs = RunState::new();
        rs.cursed = false;
        rs.update_had_clover(t2f(2, 45), HudFlags::HAVE_CLOVER);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_not_cursed_past_threshold_fails_low() {
        // 3:00 is the normal fail time; a little margin means
        // t2f(4, 0) is well past it.
        let mut rs = RunState::new();
        rs.cursed = false;
        rs.update_had_clover(t2f(4, 0), HudFlags::HAVE_CLOVER);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_cursed_under_threshold_stays_low() {
        // Cursed threshold is 2:30 (minus margin), so 2:15 is safe.
        let mut rs = RunState::new();
        rs.cursed = true;
        rs.update_had_clover(t2f(2, 15), HudFlags::HAVE_CLOVER);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_cursed_past_threshold_fails_low() {
        let mut rs = RunState::new();
        rs.cursed = true;
        rs.update_had_clover(t2f(2, 45), HudFlags::HAVE_CLOVER);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_ghost_already_spawned_stays_low_normal() {
        // Ghost ate the clover; time-based fail no longer applies.
        let mut rs = RunState::new();
        rs.ghost_spawned = true;
        rs.update_had_clover(t2f(4, 0), HudFlags::HAVE_CLOVER);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_had_clover_ghost_already_spawned_stays_low_cursed() {
        let mut rs = RunState::new();
        rs.ghost_spawned = true;
        rs.cursed = true;
        rs.update_had_clover(t2f(4, 0), HudFlags::HAVE_CLOVER);
        assert!(rs.run_label.contains(Label::Low));
    }

    // update_terminus: 16 cases. Forces `sunken_chain_status` +
    // `eggplant_stepper`/`cosmic_stepper.last_status` via
    // `ChainStepper::set_last_status_for_test` and checks
    // `run_state.run_label.terminus()`.
    fn run_terminus_case(
        world: u8,
        win_state: WinState,
        final_death: bool,
        had_ankh: bool,
        sunken: ChainStatus,
        eggplant: ChainStatus,
        cosmic: ChainStatus,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.final_death = final_death;
        rs.had_ankh = had_ankh;
        rs.sunken_chain_status = sunken;
        rs.eggplant_stepper.set_last_status_for_test(eggplant);
        rs.cosmic_stepper.set_last_status_for_test(cosmic);
        let mut snap = empty_snapshot();
        snap.world = world;
        snap.win_state = win_state;
        let inputs = ChainInputs::stub(snap);
        rs.update_terminus(&inputs);
        rs
    }
    #[test]
    fn runstate_terminus_default_w2_unstarted_all_any() {
        let rs = run_terminus_case(
            2,
            WinState::NoWin,
            false,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::Any);
    }
    #[test]
    fn runstate_terminus_final_death_w1_death() {
        let rs = run_terminus_case(
            1,
            WinState::NoWin,
            true,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::Death);
    }
    #[test]
    fn runstate_terminus_had_ankh_w3_sunken() {
        let rs = run_terminus_case(
            3,
            WinState::NoWin,
            false,
            true,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::SunkenCity);
    }
    #[test]
    fn runstate_terminus_sunken_in_progress_w2_sunken() {
        let rs = run_terminus_case(
            2,
            WinState::NoWin,
            false,
            false,
            ChainStatus::InProgress,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::SunkenCity);
    }
    #[test]
    fn runstate_terminus_eggplant_in_progress_w1_sunken() {
        let rs = run_terminus_case(
            1,
            WinState::NoWin,
            false,
            false,
            ChainStatus::Unstarted,
            ChainStatus::InProgress,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::SunkenCity);
    }
    #[test]
    fn runstate_terminus_cosmic_in_progress_w2_cosmic() {
        let rs = run_terminus_case(
            2,
            WinState::NoWin,
            false,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::InProgress,
        );
        assert_eq!(rs.run_label.terminus(), Label::CosmicOcean);
    }
    #[test]
    fn runstate_terminus_w7_forces_sunken_even_all_failed() {
        // In world 7 the run must be doing Sunken City.
        let rs = run_terminus_case(
            7,
            WinState::NoWin,
            false,
            false,
            ChainStatus::Failed,
            ChainStatus::InProgress,
            ChainStatus::Failed,
        );
        assert_eq!(rs.run_label.terminus(), Label::SunkenCity);
    }
    #[test]
    fn runstate_terminus_w7_all_failed_still_sunken() {
        let rs = run_terminus_case(
            7,
            WinState::NoWin,
            false,
            false,
            ChainStatus::Failed,
            ChainStatus::Failed,
            ChainStatus::Failed,
        );
        assert_eq!(rs.run_label.terminus(), Label::SunkenCity);
    }
    #[test]
    fn runstate_terminus_hundun_win_is_sunken() {
        // Post-Hundun world is set to 1 (moon screen) but the win
        // state alone marks this as SC.
        let rs = run_terminus_case(
            1,
            WinState::Hundun,
            false,
            false,
            ChainStatus::Failed,
            ChainStatus::InProgress,
            ChainStatus::Failed,
        );
        assert_eq!(rs.run_label.terminus(), Label::SunkenCity);
    }
    #[test]
    fn runstate_terminus_cosmic_beats_sunken_even_in_w7() {
        let rs = run_terminus_case(
            7,
            WinState::NoWin,
            true,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::InProgress,
        );
        assert_eq!(rs.run_label.terminus(), Label::CosmicOcean);
    }
    #[test]
    fn runstate_terminus_cosmic_win_is_cosmic() {
        let rs = run_terminus_case(
            8,
            WinState::CosmicOcean,
            true,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::InProgress,
        );
        assert_eq!(rs.run_label.terminus(), Label::CosmicOcean);
    }
    #[test]
    fn runstate_terminus_cosmic_beats_death() {
        let rs = run_terminus_case(
            2,
            WinState::NoWin,
            true,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::InProgress,
        );
        assert_eq!(rs.run_label.terminus(), Label::CosmicOcean);
    }
    #[test]
    fn runstate_terminus_cosmic_beats_sunken_via_status() {
        let rs = run_terminus_case(
            3,
            WinState::NoWin,
            false,
            false,
            ChainStatus::InProgress,
            ChainStatus::Unstarted,
            ChainStatus::InProgress,
        );
        assert_eq!(rs.run_label.terminus(), Label::CosmicOcean);
    }
    #[test]
    fn runstate_terminus_death_beats_sunken_via_status() {
        let rs = run_terminus_case(
            2,
            WinState::NoWin,
            true,
            false,
            ChainStatus::InProgress,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::Death);
    }
    #[test]
    fn runstate_terminus_death_beats_any() {
        let rs = run_terminus_case(
            2,
            WinState::NoWin,
            true,
            false,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
            ChainStatus::Unstarted,
        );
        assert_eq!(rs.run_label.terminus(), Label::Death);
    }

    // is_chain: 5 cases.
    fn run_is_chain_case(abzu: ChainStatus, duat: ChainStatus) -> (RunState, bool, bool, bool) {
        let mut rs = RunState::new();
        rs.abzu_stepper.set_last_status_for_test(abzu);
        rs.duat_stepper.set_last_status_for_test(duat);
        rs.update_is_chain();
        let has_abzu = rs.run_label.contains(Label::Abzu);
        let has_duat = rs.run_label.contains(Label::Duat);
        let has_chain = rs.run_label.contains(Label::Chain);
        (rs, has_abzu, has_duat, has_chain)
    }
    #[test]
    fn runstate_is_chain_both_unstarted() {
        let (rs, abzu, duat, chain) =
            run_is_chain_case(ChainStatus::Unstarted, ChainStatus::Unstarted);
        assert!(!abzu);
        assert!(!duat);
        assert!(!chain);
        assert_eq!(rs.sunken_chain_status, ChainStatus::Unstarted);
    }
    #[test]
    fn runstate_is_chain_both_in_progress() {
        // Both in-progress: Chain label but neither Abzu nor Duat
        // (the run could still resolve to either).
        let (rs, abzu, duat, chain) =
            run_is_chain_case(ChainStatus::InProgress, ChainStatus::InProgress);
        assert!(!abzu);
        assert!(!duat);
        assert!(chain);
        assert_eq!(rs.sunken_chain_status, ChainStatus::InProgress);
    }
    #[test]
    fn runstate_is_chain_abzu_only() {
        let (rs, abzu, duat, chain) =
            run_is_chain_case(ChainStatus::InProgress, ChainStatus::Failed);
        assert!(abzu);
        assert!(!duat);
        assert!(chain);
        assert_eq!(rs.sunken_chain_status, ChainStatus::InProgress);
    }
    #[test]
    fn runstate_is_chain_duat_only() {
        let (rs, abzu, duat, chain) =
            run_is_chain_case(ChainStatus::Failed, ChainStatus::InProgress);
        assert!(!abzu);
        assert!(duat);
        assert!(chain);
        assert_eq!(rs.sunken_chain_status, ChainStatus::InProgress);
    }
    #[test]
    fn runstate_is_chain_both_failed() {
        let (rs, abzu, duat, chain) = run_is_chain_case(ChainStatus::Failed, ChainStatus::Failed);
        assert!(!abzu);
        assert!(!duat);
        assert!(!chain);
        assert_eq!(rs.sunken_chain_status, ChainStatus::Failed);
    }

    // millionaire_clone_gun_wo_bow: 4 cases.
    fn run_millionaire_clone_gun_case(has_clone_gun: bool, cosmic: ChainStatus) -> RunState {
        let mut rs = RunState::new();
        rs.cosmic_stepper.set_last_status_for_test(cosmic);
        let inputs = ChainInputs::stub(empty_snapshot());
        let player = default_player();
        let mut items = std::collections::HashSet::new();
        if has_clone_gun {
            items.insert(entity_types::ITEM_CLONEGUN);
        }
        rs.update_millionaire(&inputs, &player, &items);
        rs
    }
    #[test]
    fn runstate_millionaire_clone_gun_no_item_unstarted() {
        let rs = run_millionaire_clone_gun_case(false, ChainStatus::Unstarted);
        assert!(!rs.clone_gun_wo_cosmic);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_no_item_in_progress() {
        let rs = run_millionaire_clone_gun_case(false, ChainStatus::InProgress);
        assert!(!rs.clone_gun_wo_cosmic);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_in_progress_no_bonus() {
        // Cosmic chain still open: clone gun doesn't grant
        // millionaire yet (they might still finish CO).
        let rs = run_millionaire_clone_gun_case(true, ChainStatus::InProgress);
        assert!(!rs.clone_gun_wo_cosmic);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_failed_grants_bonus() {
        // Once cosmic fails, clone gun means the run is heading
        // straight for the millionaire cash-out.
        let rs = run_millionaire_clone_gun_case(true, ChainStatus::Failed);
        assert!(rs.clone_gun_wo_cosmic);
        assert!(rs.run_label.contains(Label::Millionaire));
    }

    // millionaire: 15 cases. Reads inventory via `player.inventory`.
    // `money_shop_total` is `i32` on the wire; the sign carries
    // "went into debt" info that clone_gun_wo_cosmic uses to still
    // grant the label pre-win.
    fn run_millionaire_case(
        money_shop_total: i32,
        win_state: WinState,
        money: u32,
        collected_money_total: u32,
        clone_gun_wo_bow: bool,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.clone_gun_wo_cosmic = clone_gun_wo_bow;
        if clone_gun_wo_bow {
            // Simulate a previous update tick that added Millionaire;
            // the current tick then decides whether to keep or drop it.
            let _ = rs.run_label.add(Label::Millionaire);
        }
        let mut snap = empty_snapshot();
        snap.money_shop_total = money_shop_total;
        snap.win_state = win_state;
        let inputs = ChainInputs::stub(snap);
        let mut player = default_player();
        player.inventory.money = money;
        player.inventory.collected_money_total = collected_money_total;
        rs.update_millionaire(&inputs, &player, &Default::default());
        rs
    }
    #[test]
    fn runstate_millionaire_zero_money_no_win() {
        let rs = run_millionaire_case(0, WinState::NoWin, 0, 0, false);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_900k_money_no_win() {
        let rs = run_millionaire_case(0, WinState::NoWin, 900_000, 0, false);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_899k999_plus_1_hits_threshold() {
        let rs = run_millionaire_case(0, WinState::NoWin, 899_999, 1, false);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_1_plus_899k999_hits_threshold() {
        let rs = run_millionaire_case(0, WinState::NoWin, 1, 899_999, false);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_neg_shop_zero_money_no_win() {
        // -$2,500 shop spend + $0 money = -$2,500 net, below threshold.
        let rs = run_millionaire_case(-2_500, WinState::NoWin, 0, 0, false);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_neg_shop_900k010_below_threshold() {
        // 900,010 minus 2,500 = 897,510, under threshold.
        let rs = run_millionaire_case(-2_500, WinState::NoWin, 900_000, 10, false);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_neg_shop_900k_plus_2500_hits_threshold() {
        // 900,000 + 2,500 - 2,500 = 900,000.
        let rs = run_millionaire_case(-2_500, WinState::NoWin, 900_000, 2_500, false);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_zero_money_no_win_preserves() {
        // Clone-gun path: label stays regardless of money before win.
        let rs = run_millionaire_case(0, WinState::NoWin, 0, 0, true);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_at_threshold_no_win_preserves() {
        let rs = run_millionaire_case(0, WinState::NoWin, 900_000, 0, true);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_neg_shop_no_win_preserves() {
        // Even at net-$895k, clone_gun_wo_cosmic keeps the label
        // until the win state arrives.
        let rs = run_millionaire_case(-5_000, WinState::NoWin, 900_000, 0, true);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_zero_shop_900k_tiamat() {
        // Post-win Tiamat: statue bonus not yet applied, but 900k
        // alone already qualifies.
        let rs = run_millionaire_case(0, WinState::Tiamat, 900_000, 0, false);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_bonus_shop_900k_tiamat() {
        // Post-win with the completion bonus already applied.
        let rs = run_millionaire_case(100_000, WinState::Tiamat, 900_000, 0, false);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_below_threshold_tiamat_fails() {
        // Winning invalidates the clone-gun free pass, actual money
        // must clear threshold.
        let rs = run_millionaire_case(0, WinState::Tiamat, 899_999, 0, true);
        assert!(!rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_at_threshold_tiamat_keeps() {
        let rs = run_millionaire_case(0, WinState::Tiamat, 900_000, 0, true);
        assert!(rs.run_label.contains(Label::Millionaire));
    }
    #[test]
    fn runstate_millionaire_clone_gun_bonus_shop_tiamat_keeps() {
        let rs = run_millionaire_case(100_000, WinState::Tiamat, 900_000, 0, true);
        assert!(rs.run_label.contains(Label::Millionaire));
    }

    // has_mounted_tame: 15 cases. `PlayerSnapshot` carries
    // `overlay_type` + `overlay_tamed_mount`, so tests set those
    // directly.
    fn run_mounted_tame_case(
        chain: ChainStatus,
        theme: Theme,
        overlay: Option<EntityType>,
        tamed: bool,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.sunken_chain_status = chain;
        let mut player = default_player();
        player.overlay_type = overlay;
        player.overlay_tamed_mount = tamed;
        rs.update_has_mounted_tame(theme, &player);
        rs
    }
    // Mounting Qilin in Neo-Bab is never allowed.
    #[test]
    fn runstate_mounted_qilin_neobab_unstarted_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::Unstarted,
            Theme::NeoBabylon,
            Some(entity_types::MOUNT_QILIN),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_qilin_neobab_in_progress_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::InProgress,
            Theme::NeoBabylon,
            Some(entity_types::MOUNT_QILIN),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_qilin_neobab_failed_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::Failed,
            Theme::NeoBabylon,
            Some(entity_types::MOUNT_QILIN),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    // Mounting Qilin in Tiamat's Lair is chain-only OK.
    #[test]
    fn runstate_mounted_qilin_tiamat_unstarted_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::Unstarted,
            Theme::Tiamat,
            Some(entity_types::MOUNT_QILIN),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_qilin_tiamat_in_progress_keeps_low() {
        let rs = run_mounted_tame_case(
            ChainStatus::InProgress,
            Theme::Tiamat,
            Some(entity_types::MOUNT_QILIN),
            true,
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_qilin_tiamat_failed_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::Failed,
            Theme::Tiamat,
            Some(entity_types::MOUNT_QILIN),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    // Tamed turkey is never OK, regardless of theme/chain.
    #[test]
    fn runstate_mounted_tamed_turkey_tidepool_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::Unstarted,
            Theme::TidePool,
            Some(entity_types::MOUNT_TURKEY),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_tamed_turkey_temple_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::InProgress,
            Theme::Temple,
            Some(entity_types::MOUNT_TURKEY),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_tamed_turkey_jungle_fails() {
        let rs = run_mounted_tame_case(
            ChainStatus::Failed,
            Theme::Jungle,
            Some(entity_types::MOUNT_TURKEY),
            true,
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    // Untamed turkey (found in level, not yet tamed) is always OK.
    #[test]
    fn runstate_mounted_untamed_turkey_dwelling_keeps_low() {
        let rs = run_mounted_tame_case(
            ChainStatus::Unstarted,
            Theme::Dwelling,
            Some(entity_types::MOUNT_TURKEY),
            false,
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_untamed_turkey_volcana_keeps_low() {
        let rs = run_mounted_tame_case(
            ChainStatus::InProgress,
            Theme::Volcana,
            Some(entity_types::MOUNT_TURKEY),
            false,
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_untamed_turkey_neobab_keeps_low() {
        let rs = run_mounted_tame_case(
            ChainStatus::Failed,
            Theme::NeoBabylon,
            Some(entity_types::MOUNT_TURKEY),
            false,
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    // No mount at all is always OK.
    #[test]
    fn runstate_mounted_none_hundun_keeps_low() {
        let rs = run_mounted_tame_case(ChainStatus::Unstarted, Theme::Hundun, None, false);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_none_cosmic_ocean_keeps_low() {
        let rs = run_mounted_tame_case(ChainStatus::InProgress, Theme::CosmicOcean, None, false);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_mounted_none_jungle_keeps_low() {
        let rs = run_mounted_tame_case(ChainStatus::Failed, Theme::Jungle, None, false);
        assert!(rs.run_label.contains(Label::Low));
    }

    // Shared helper for update_attacked_with tests. `held` = current
    // items, `prev_held` = last-tick items.
    #[allow(clippy::too_many_arguments)]
    fn run_attacked_with_case(
        prev_state: CharState,
        cur_state: CharState,
        layer: Layer,
        world: u8,
        level: u8,
        theme: Theme,
        presence: PresenceFlags,
        chain: ChainStatus,
        held: &std::collections::HashSet<EntityType>,
        prev_held: &std::collections::HashSet<EntityType>,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.sunken_chain_status = chain;
        rs.update_attacked_with(
            prev_state, cur_state, layer, world, level, theme, presence, held, prev_held,
        );
        rs
    }

    fn item_set<const N: usize>(items: [EntityType; N]) -> std::collections::HashSet<EntityType> {
        items.into_iter().collect()
    }

    // attacked_with_simple: 6 cases. Theme/world/level/presence held
    // constant, only state + boomerang transitions vary. Uses
    // IN_PROGRESS chain so Excalibur wouldn't interfere; only
    // boomerang is exercised here.
    fn simple_case(
        prev_state: CharState,
        cur_state: CharState,
        held: &std::collections::HashSet<EntityType>,
        prev_held: &std::collections::HashSet<EntityType>,
    ) -> RunState {
        run_attacked_with_case(
            prev_state,
            cur_state,
            Layer::Front,
            2,
            2,
            Theme::Jungle,
            PresenceFlags::empty(),
            ChainStatus::InProgress,
            held,
            prev_held,
        )
    }
    #[test]
    fn runstate_attacked_simple_standing_to_attack_lost_boomerang_fails() {
        // Held boomerang last tick, now empty, just started attacking:
        // boomerang throw = failed low%.
        let rs = simple_case(
            CharState::Standing,
            CharState::Attacking,
            &item_set([]),
            &item_set([entity_types::ITEM_BOOMERANG]),
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_simple_attack_to_standing_regained_boomerang_fails() {
        // Was attacking last tick, now holding boomerang: loop trips
        // the LOW_BANNED_ATTACKABLES branch on the current inventory.
        let rs = simple_case(
            CharState::Attacking,
            CharState::Standing,
            &item_set([entity_types::ITEM_BOOMERANG]),
            &item_set([]),
        );
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_simple_holding_boomerang_no_transition_keeps_low() {
        // Jumping to climbing while holding boomerang the whole time
        // (no attack started/ended) is fine.
        let rs = simple_case(
            CharState::Jumping,
            CharState::Climbing,
            &item_set([entity_types::ITEM_BOOMERANG]),
            &item_set([entity_types::ITEM_BOOMERANG]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    // Whip attacks (empty inventory) are OK across all three transitions.
    #[test]
    fn runstate_attacked_simple_whip_jump_to_climb_keeps_low() {
        let rs = simple_case(
            CharState::Jumping,
            CharState::Climbing,
            &item_set([]),
            &item_set([]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_simple_whip_start_attack_keeps_low() {
        let rs = simple_case(
            CharState::Standing,
            CharState::Attacking,
            &item_set([]),
            &item_set([]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_simple_whip_end_attack_keeps_low() {
        let rs = simple_case(
            CharState::Attacking,
            CharState::Standing,
            &item_set([]),
            &item_set([]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }

    // attacked_with_excalibur: 10 cases. Excalibur is Abzu-chain-only
    // OK; anywhere else it fails immediately. Verifies
    // `failed_low_if_not_chain` gets set in the Abzu-theme branch
    // even when the run fails.
    fn excalibur_case(
        layer: Layer,
        theme: Theme,
        presence: PresenceFlags,
        chain: ChainStatus,
    ) -> RunState {
        let held = item_set([entity_types::ITEM_EXCALIBUR]);
        run_attacked_with_case(
            CharState::Pushing,
            CharState::Attacking,
            layer,
            4,
            2,
            theme,
            presence,
            chain,
            &held,
            &held,
        )
    }
    // Not OK in Tide Pool regardless of chain or challenge.
    #[test]
    fn runstate_attacked_excalibur_tidepool_front_star_unstarted_fails() {
        let rs = excalibur_case(
            Layer::Front,
            Theme::TidePool,
            PresenceFlags::STAR_CHALLENGE,
            ChainStatus::Unstarted,
        );
        assert!(!rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_excalibur_tidepool_back_star_in_progress_fails() {
        let rs = excalibur_case(
            Layer::Back,
            Theme::TidePool,
            PresenceFlags::STAR_CHALLENGE,
            ChainStatus::InProgress,
        );
        assert!(!rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_excalibur_tidepool_front_no_presence_in_progress_fails() {
        let rs = excalibur_case(
            Layer::Front,
            Theme::TidePool,
            PresenceFlags::empty(),
            ChainStatus::InProgress,
        );
        assert!(!rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_excalibur_tidepool_back_no_presence_failed_fails() {
        let rs = excalibur_case(
            Layer::Back,
            Theme::TidePool,
            PresenceFlags::empty(),
            ChainStatus::Failed,
        );
        assert!(!rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    // Abzu + in-progress chain: OK, and failed_low_if_not_chain set.
    #[test]
    fn runstate_attacked_excalibur_abzu_front_in_progress_keeps_low() {
        let rs = excalibur_case(
            Layer::Front,
            Theme::Abzu,
            PresenceFlags::empty(),
            ChainStatus::InProgress,
        );
        assert!(rs.failed_low_if_not_chain);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_excalibur_abzu_back_in_progress_keeps_low() {
        let rs = excalibur_case(
            Layer::Back,
            Theme::Abzu,
            PresenceFlags::empty(),
            ChainStatus::InProgress,
        );
        assert!(rs.failed_low_if_not_chain);
        assert!(rs.run_label.contains(Label::Low));
    }
    // Abzu without chain progress: flag still gets set, run fails.
    #[test]
    fn runstate_attacked_excalibur_abzu_front_unstarted_fails() {
        let rs = excalibur_case(
            Layer::Front,
            Theme::Abzu,
            PresenceFlags::empty(),
            ChainStatus::Unstarted,
        );
        assert!(rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_excalibur_abzu_back_failed_fails() {
        let rs = excalibur_case(
            Layer::Back,
            Theme::Abzu,
            PresenceFlags::empty(),
            ChainStatus::Failed,
        );
        assert!(rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    // Later-area themes: no exemption regardless of layer/chain.
    #[test]
    fn runstate_attacked_excalibur_ice_caves_fails() {
        // Effective input: Layer::Front, Theme::IceCaves, no chain,
        // no presence.
        let rs = excalibur_case(
            Layer::Front,
            Theme::IceCaves,
            PresenceFlags::empty(),
            ChainStatus::Unstarted,
        );
        assert!(!rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_excalibur_neobab_in_progress_fails() {
        let rs = excalibur_case(
            Layer::Back,
            Theme::NeoBabylon,
            PresenceFlags::empty(),
            ChainStatus::InProgress,
        );
        assert!(!rs.failed_low_if_not_chain);
        assert!(!rs.run_label.contains(Label::Low));
    }

    // attacked_with_mattock: 8 cases. Mattock is only OK in Moon
    // Challenge back layer. When it's OK, `mc_has_swung_mattock` gets
    // set alongside keeping Low.
    fn mattock_case(layer: Layer, theme: Theme, presence: PresenceFlags) -> RunState {
        let held = item_set([entity_types::ITEM_MATTOCK]);
        run_attacked_with_case(
            CharState::Pushing,
            CharState::Attacking,
            layer,
            2,
            2,
            theme,
            presence,
            ChainStatus::Unstarted,
            &held,
            &held,
        )
    }
    #[test]
    fn runstate_attacked_mattock_front_volcana_moon_fails() {
        let rs = mattock_case(Layer::Front, Theme::Volcana, PresenceFlags::MOON_CHALLENGE);
        assert!(!rs.mc_has_swung_mattock);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_front_jungle_moon_fails() {
        let rs = mattock_case(Layer::Front, Theme::Jungle, PresenceFlags::MOON_CHALLENGE);
        assert!(!rs.mc_has_swung_mattock);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_back_volcana_moon_keeps_low() {
        let rs = mattock_case(Layer::Back, Theme::Volcana, PresenceFlags::MOON_CHALLENGE);
        assert!(rs.mc_has_swung_mattock);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_back_jungle_moon_keeps_low() {
        let rs = mattock_case(Layer::Back, Theme::Jungle, PresenceFlags::MOON_CHALLENGE);
        assert!(rs.mc_has_swung_mattock);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_back_volcana_no_presence_fails() {
        let rs = mattock_case(Layer::Back, Theme::Volcana, PresenceFlags::empty());
        assert!(!rs.mc_has_swung_mattock);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_back_jungle_no_presence_fails() {
        let rs = mattock_case(Layer::Back, Theme::Jungle, PresenceFlags::empty());
        assert!(!rs.mc_has_swung_mattock);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_front_dwelling_no_presence_fails() {
        let rs = mattock_case(Layer::Front, Theme::Dwelling, PresenceFlags::empty());
        assert!(!rs.mc_has_swung_mattock);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_mattock_back_olmec_no_presence_fails() {
        let rs = mattock_case(Layer::Back, Theme::Olmec, PresenceFlags::empty());
        assert!(!rs.mc_has_swung_mattock);
        assert!(!rs.run_label.contains(Label::Low));
    }

    // attacked_with_hou_yi: 12 cases. Hou Yi bow is OK in back-layer
    // challenges, in Waddler levels (3-1, 5-1, 7-1), and against
    // Hundun (7-4). Anywhere else fails.
    fn hou_yi_case(layer: Layer, world: u8, level: u8, presence: PresenceFlags) -> RunState {
        let held = item_set([entity_types::ITEM_HOUYIBOW]);
        run_attacked_with_case(
            CharState::Jumping,
            CharState::Attacking,
            layer,
            world,
            level,
            Theme::Dwelling,
            presence,
            ChainStatus::Unstarted,
            &held,
            &held,
        )
    }
    // Back-layer allowances.
    #[test]
    fn runstate_attacked_hou_yi_back_2_3_moon_keeps_low() {
        let rs = hou_yi_case(Layer::Back, 2, 3, PresenceFlags::MOON_CHALLENGE);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_back_3_1_waddler_keeps_low() {
        let rs = hou_yi_case(Layer::Back, 3, 1, PresenceFlags::empty());
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_back_5_1_waddler_keeps_low() {
        let rs = hou_yi_case(Layer::Back, 5, 1, PresenceFlags::empty());
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_back_7_1_waddler_keeps_low() {
        let rs = hou_yi_case(Layer::Back, 7, 1, PresenceFlags::empty());
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_back_7_2_sun_keeps_low() {
        let rs = hou_yi_case(Layer::Back, 7, 2, PresenceFlags::SUN_CHALLENGE);
        assert!(rs.run_label.contains(Label::Low));
    }
    // Front-layer in the same spots: not OK.
    #[test]
    fn runstate_attacked_hou_yi_front_2_3_moon_fails() {
        let rs = hou_yi_case(Layer::Front, 2, 3, PresenceFlags::MOON_CHALLENGE);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_front_3_1_fails() {
        let rs = hou_yi_case(Layer::Front, 3, 1, PresenceFlags::empty());
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_front_5_1_fails() {
        let rs = hou_yi_case(Layer::Front, 5, 1, PresenceFlags::empty());
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_front_7_1_fails() {
        let rs = hou_yi_case(Layer::Front, 7, 1, PresenceFlags::empty());
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_hou_yi_front_7_2_sun_fails() {
        let rs = hou_yi_case(Layer::Front, 7, 2, PresenceFlags::SUN_CHALLENGE);
        assert!(!rs.run_label.contains(Label::Low));
    }
    // Hundun (7-4) is OK regardless of layer.
    #[test]
    fn runstate_attacked_hou_yi_front_7_4_hundun_keeps_low() {
        let rs = hou_yi_case(Layer::Front, 7, 4, PresenceFlags::empty());
        assert!(rs.run_label.contains(Label::Low));
    }
    // CO (7-5+) is not.
    #[test]
    fn runstate_attacked_hou_yi_front_7_5_co_fails() {
        let rs = hou_yi_case(Layer::Front, 7, 5, PresenceFlags::empty());
        assert!(!rs.run_label.contains(Label::Low));
    }

    // attacked_with_throwables: 5 cases. Arrows of Light and wooden
    // arrows count as throwables; wielding them and entering Throwing
    // state fails Low. Whip-only (no items) still exercises the state
    // check.
    fn throwables_case(
        prev_state: CharState,
        cur_state: CharState,
        prev_held: &std::collections::HashSet<EntityType>,
        cur_held: &std::collections::HashSet<EntityType>,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.update_attacked_with_throwables(cur_state, prev_state, prev_held, cur_held);
        rs
    }
    #[test]
    fn runstate_attacked_throwables_light_arrow_prev_keeps_low() {
        let rs = throwables_case(
            CharState::Throwing,
            CharState::Standing,
            &item_set([entity_types::ITEM_LIGHT_ARROW]),
            &item_set([]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_throwables_light_arrow_cur_keeps_low() {
        let rs = throwables_case(
            CharState::Standing,
            CharState::Throwing,
            &item_set([]),
            &item_set([entity_types::ITEM_LIGHT_ARROW]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_throwables_wooden_arrow_prev_keeps_low() {
        let rs = throwables_case(
            CharState::Throwing,
            CharState::Standing,
            &item_set([entity_types::ITEM_WOODEN_ARROW]),
            &item_set([]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_throwables_wooden_arrow_cur_keeps_low() {
        let rs = throwables_case(
            CharState::Standing,
            CharState::Throwing,
            &item_set([]),
            &item_set([entity_types::ITEM_WOODEN_ARROW]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_attacked_throwables_empty_hands_after_throw_keeps_low() {
        // Was Throwing last tick with nothing detectable in-hand: no
        // banned throwable found, no failure.
        let rs = throwables_case(
            CharState::Throwing,
            CharState::Standing,
            &item_set([]),
            &item_set([]),
        );
        assert!(rs.run_label.contains(Label::Low));
    }

    // run_recap: 3 param cases x 2 flag states. Covers three
    // (label, flag, method) triples; each triple asserts both "flag
    // present preserves the label" and "flag missing discards it".
    // Split into six named tests so a failure names the specific
    // flag/method combo.
    #[test]
    fn runstate_run_recap_pacifist_flag_set_preserves() {
        let mut rs = RunState::new();
        rs.update_pacifist(RunRecapFlags::PACIFIST);
        assert!(rs.run_label.contains(Label::Pacifist));
    }
    #[test]
    fn runstate_run_recap_pacifist_flag_unset_discards() {
        let mut rs = RunState::new();
        rs.update_pacifist(RunRecapFlags::empty());
        assert!(!rs.run_label.contains(Label::Pacifist));
    }
    #[test]
    fn runstate_run_recap_no_gold_flag_set_preserves() {
        let mut rs = RunState::new();
        rs.update_no_gold(RunRecapFlags::NO_GOLD);
        assert!(rs.run_label.contains(Label::NoGold));
    }
    #[test]
    fn runstate_run_recap_no_gold_flag_unset_discards() {
        let mut rs = RunState::new();
        rs.update_no_gold(RunRecapFlags::empty());
        assert!(!rs.run_label.contains(Label::NoGold));
    }
    #[test]
    fn runstate_run_recap_no_label_flag_set_preserves() {
        // update_no_gold co-discards NoGold + No when the flag is
        // missing, so setting the flag also keeps Label::No alive.
        let mut rs = RunState::new();
        rs.update_no_gold(RunRecapFlags::NO_GOLD);
        assert!(rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_run_recap_no_label_flag_unset_discards() {
        let mut rs = RunState::new();
        rs.update_no_gold(RunRecapFlags::empty());
        assert!(!rs.run_label.contains(Label::No));
    }

    // score_items: 4 cases. Plasma cannon or True Crown flips the
    // Score label; anything else stays non-Score.
    fn score_items_case(items: &std::collections::HashSet<EntityType>) -> RunState {
        let mut rs = RunState::new();
        rs.update_score_items(items);
        rs
    }
    #[test]
    fn runstate_score_items_eggplant_crown_not_score() {
        let rs = score_items_case(&item_set([entity_types::ITEM_POWERUP_EGGPLANTCROWN]));
        assert!(!rs.run_label.contains(Label::Score));
    }
    #[test]
    fn runstate_score_items_plasma_cannon_scores() {
        let rs = score_items_case(&item_set([entity_types::ITEM_PLASMACANNON]));
        assert!(rs.run_label.contains(Label::Score));
    }
    #[test]
    fn runstate_score_items_true_crown_scores() {
        let rs = score_items_case(&item_set([entity_types::ITEM_POWERUP_TRUECROWN]));
        assert!(rs.run_label.contains(Label::Score));
    }
    #[test]
    fn runstate_score_items_empty_not_score() {
        let rs = score_items_case(&item_set([]));
        assert!(!rs.run_label.contains(Label::Score));
    }

    // true_crown: 4 cases. Only True Crown itself flips the label,
    // unlike update_score_items where plasma cannon also counts.
    fn true_crown_case(items: &std::collections::HashSet<EntityType>) -> RunState {
        let mut rs = RunState::new();
        rs.update_true_crown(items);
        rs
    }
    #[test]
    fn runstate_true_crown_eggplant_crown_no_label() {
        let rs = true_crown_case(&item_set([entity_types::ITEM_POWERUP_EGGPLANTCROWN]));
        assert!(!rs.run_label.contains(Label::TrueCrown));
    }
    #[test]
    fn runstate_true_crown_plasma_cannon_no_label() {
        let rs = true_crown_case(&item_set([entity_types::ITEM_PLASMACANNON]));
        assert!(!rs.run_label.contains(Label::TrueCrown));
    }
    #[test]
    fn runstate_true_crown_adds_label() {
        let rs = true_crown_case(&item_set([entity_types::ITEM_POWERUP_TRUECROWN]));
        assert!(rs.run_label.contains(Label::TrueCrown));
    }
    #[test]
    fn runstate_true_crown_empty_no_label() {
        let rs = true_crown_case(&item_set([]));
        assert!(!rs.run_label.contains(Label::TrueCrown));
    }

    // ice_caves: 4 cases. update_ice_caves takes a `&ChainInputs`;
    // reach the relevant fields via `empty_snapshot()` + field poke,
    // then wrap in `ChainInputs::stub`.
    fn ice_caves_case(
        level_started: bool,
        theme: Theme,
        world_start: u8,
        level_start: u8,
    ) -> RunState {
        let mut snap = empty_snapshot();
        snap.theme = theme;
        snap.world_start = world_start;
        snap.level_start = level_start;
        let inputs = ChainInputs::stub(snap);
        let mut rs = RunState::new();
        rs.level_started = level_started;
        rs.update_ice_caves(&inputs);
        rs
    }
    #[test]
    fn runstate_ice_caves_not_started_no_label() {
        let rs = ice_caves_case(false, Theme::IceCaves, 5, 1);
        assert!(!rs.run_label.contains(Label::IceCavesShortcut));
    }
    #[test]
    fn runstate_ice_caves_neo_bab_theme_no_label() {
        let rs = ice_caves_case(true, Theme::NeoBabylon, 5, 1);
        assert!(!rs.run_label.contains(Label::IceCavesShortcut));
    }
    #[test]
    fn runstate_ice_caves_started_at_1_1_no_label() {
        let rs = ice_caves_case(true, Theme::IceCaves, 1, 1);
        assert!(!rs.run_label.contains(Label::IceCavesShortcut));
    }
    #[test]
    fn runstate_ice_caves_started_at_5_1_adds_label() {
        let rs = ice_caves_case(true, Theme::IceCaves, 5, 1);
        assert!(rs.run_label.contains(Label::IceCavesShortcut));
    }

    // wore_backpack: 6 cases. Two orthogonal effects: JETPACK
    // specifically drops NoJetpack; any BACKPACKS member drops Low.
    fn wore_backpack_case(items: &std::collections::HashSet<EntityType>) -> RunState {
        let mut rs = RunState::new();
        rs.update_wore_backpack(items);
        rs
    }
    #[test]
    fn runstate_wore_backpack_jetpack_drops_no_jp_and_low() {
        let rs = wore_backpack_case(&item_set([entity_types::ITEM_JETPACK]));
        assert!(!rs.run_label.contains(Label::NoJetpack));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_wore_backpack_hoverpack_keeps_no_jp_drops_low() {
        let rs = wore_backpack_case(&item_set([entity_types::ITEM_HOVERPACK]));
        assert!(rs.run_label.contains(Label::NoJetpack));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_wore_backpack_vlads_cape_keeps_no_jp_drops_low() {
        let rs = wore_backpack_case(&item_set([entity_types::ITEM_VLADS_CAPE]));
        assert!(rs.run_label.contains(Label::NoJetpack));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_wore_backpack_teleporter_backpack_keeps_no_jp_drops_low() {
        let rs = wore_backpack_case(&item_set([entity_types::ITEM_TELEPORTER_BACKPACK]));
        assert!(rs.run_label.contains(Label::NoJetpack));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_wore_backpack_shotgun_keeps_both() {
        let rs = wore_backpack_case(&item_set([entity_types::ITEM_SHOTGUN]));
        assert!(rs.run_label.contains(Label::NoJetpack));
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_wore_backpack_empty_keeps_both() {
        let rs = wore_backpack_case(&item_set([]));
        assert!(rs.run_label.contains(Label::NoJetpack));
        assert!(rs.run_label.contains(Label::Low));
    }

    // held_shield: 4 cases. Any SHIELDS entry fails Low; camera
    // (an unrelated held item) doesn't.
    fn held_shield_case(items: &std::collections::HashSet<EntityType>) -> RunState {
        let mut rs = RunState::new();
        rs.update_held_shield(items);
        rs
    }
    #[test]
    fn runstate_held_shield_metal_fails_low() {
        let rs = held_shield_case(&item_set([entity_types::ITEM_METAL_SHIELD]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_held_shield_wooden_fails_low() {
        let rs = held_shield_case(&item_set([entity_types::ITEM_WOODEN_SHIELD]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_held_shield_camera_keeps_low() {
        let rs = held_shield_case(&item_set([entity_types::ITEM_CAMERA]));
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_held_shield_empty_keeps_low() {
        let rs = held_shield_case(&item_set([]));
        assert!(rs.run_label.contains(Label::Low));
    }

    // has_chain_powerup: 6 cases. Ankh always flips `had_ankh`;
    // Ankh/Tablet fail Low iff the sunken chain isn't in-progress.
    fn has_chain_powerup_case(
        chain: ChainStatus,
        items: &std::collections::HashSet<EntityType>,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.sunken_chain_status = chain;
        rs.update_has_chain_powerup(items);
        rs
    }
    #[test]
    fn runstate_has_chain_powerup_in_progress_ankh_keeps_low_marks_ankh() {
        let rs = has_chain_powerup_case(
            ChainStatus::InProgress,
            &item_set([entity_types::ITEM_POWERUP_ANKH]),
        );
        assert!(rs.had_ankh);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_has_chain_powerup_in_progress_tablet_keeps_low_no_ankh() {
        let rs = has_chain_powerup_case(
            ChainStatus::InProgress,
            &item_set([entity_types::ITEM_POWERUP_TABLETOFDESTINY]),
        );
        assert!(!rs.had_ankh);
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_has_chain_powerup_unstarted_ankh_fails_low_marks_ankh() {
        let rs = has_chain_powerup_case(
            ChainStatus::Unstarted,
            &item_set([entity_types::ITEM_POWERUP_ANKH]),
        );
        assert!(rs.had_ankh);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_has_chain_powerup_unstarted_tablet_fails_low_no_ankh() {
        let rs = has_chain_powerup_case(
            ChainStatus::Unstarted,
            &item_set([entity_types::ITEM_POWERUP_TABLETOFDESTINY]),
        );
        assert!(!rs.had_ankh);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_has_chain_powerup_failed_ankh_fails_low_marks_ankh() {
        let rs = has_chain_powerup_case(
            ChainStatus::Failed,
            &item_set([entity_types::ITEM_POWERUP_ANKH]),
        );
        assert!(rs.had_ankh);
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_has_chain_powerup_failed_tablet_fails_low_no_ankh() {
        let rs = has_chain_powerup_case(
            ChainStatus::Failed,
            &item_set([entity_types::ITEM_POWERUP_TABLETOFDESTINY]),
        );
        assert!(!rs.had_ankh);
        assert!(!rs.run_label.contains(Label::Low));
    }

    // has_non_chain_powerup: 8 cases. Any NON_CHAIN_POWERUP_ENTITIES
    // member fails Low, including when multiple are held; light arrow
    // (a throwable) and empty hands don't.
    fn non_chain_powerup_case(items: &std::collections::HashSet<EntityType>) -> RunState {
        let mut rs = RunState::new();
        rs.update_has_non_chain_powerup(items);
        rs
    }
    #[test]
    fn runstate_non_chain_powerup_compass_fails_low() {
        let rs = non_chain_powerup_case(&item_set([entity_types::ITEM_POWERUP_COMPASS]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_parachute_fails_low() {
        let rs = non_chain_powerup_case(&item_set([entity_types::ITEM_POWERUP_PARACHUTE]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_skeleton_key_fails_low() {
        let rs = non_chain_powerup_case(&item_set([entity_types::ITEM_POWERUP_SKELETON_KEY]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_spike_shoes_fails_low() {
        let rs = non_chain_powerup_case(&item_set([entity_types::ITEM_POWERUP_SPIKE_SHOES]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_spring_shoes_fails_low() {
        let rs = non_chain_powerup_case(&item_set([entity_types::ITEM_POWERUP_SPRING_SHOES]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_multiple_fails_low() {
        let rs = non_chain_powerup_case(&item_set([
            entity_types::ITEM_POWERUP_PARACHUTE,
            entity_types::ITEM_POWERUP_SPRING_SHOES,
        ]));
        assert!(!rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_light_arrow_keeps_low() {
        let rs = non_chain_powerup_case(&item_set([entity_types::ITEM_LIGHT_ARROW]));
        assert!(rs.run_label.contains(Label::Low));
    }
    #[test]
    fn runstate_non_chain_powerup_empty_keeps_low() {
        let rs = non_chain_powerup_case(&item_set([]));
        assert!(rs.run_label.contains(Label::Low));
    }

    // on_level_start_state: 5 cases. Snapshots `level_start_ropes`
    // from the fresh player, drops No if starting with <4 ropes, and
    // clamps health to 4 on entering Duat (the CoG-sacrifice health
    // reset).
    fn on_level_start_case(world: u8, theme: Theme, ropes: u8, prev_health: i8) -> RunState {
        let mut rs = RunState::new();
        rs.level_started = true;
        rs.health = prev_health;
        rs.update_on_level_start(world, theme, ropes);
        rs
    }
    #[test]
    fn runstate_on_level_start_jungle_4_ropes_keeps_no() {
        let rs = on_level_start_case(2, Theme::Jungle, 4, 4);
        assert_eq!(rs.level_start_ropes, 4);
        assert_eq!(rs.health, 4);
        assert!(rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_on_level_start_volcana_2_ropes_drops_no() {
        let rs = on_level_start_case(2, Theme::Volcana, 2, 3);
        assert_eq!(rs.level_start_ropes, 2);
        assert_eq!(rs.health, 3);
        assert!(!rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_on_level_start_duat_prev_2_clamps_to_4() {
        let rs = on_level_start_case(4, Theme::Duat, 5, 2);
        assert_eq!(rs.level_start_ropes, 5);
        assert_eq!(rs.health, 4);
        assert!(rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_on_level_start_duat_prev_4_stays_4() {
        let rs = on_level_start_case(4, Theme::Duat, 5, 4);
        assert_eq!(rs.level_start_ropes, 5);
        assert_eq!(rs.health, 4);
        assert!(rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_on_level_start_duat_prev_10_clamps_to_4() {
        let rs = on_level_start_case(4, Theme::Duat, 5, 10);
        assert_eq!(rs.level_start_ropes, 5);
        assert_eq!(rs.health, 4);
        assert!(rs.run_label.contains(Label::No));
    }

    // Entity-delta pipeline tests.
    //
    // RunState tests that depend on `new_entity_types` +
    // `new_teleport_shadows`. Two flavors:
    //   - Direct-poke tests (rope-deploy, ghost-spawn, TP shadow):
    //     just inject into the fields. Fields are pre-extracted into
    //     narrow representations upstream.
    //   - new_entities: exercises `compute_new_entities` end to end
    //     via `EntityMapBuilder`, a Robin Hood table builder.

    use chain_impl::inputs::PlayerMotion;
    use runstate::TeleportShadowSnap;
    use testing::EntityMapBuilder;

    // could_tp_items: 4 cases. Any teleporter-family item in either
    // the current or last inventory makes `could_tp` true.
    fn could_tp_items_case(
        held: &std::collections::HashSet<EntityType>,
        prev_held: &std::collections::HashSet<EntityType>,
    ) -> bool {
        let rs = RunState::new();
        rs.could_tp(&default_player(), held, prev_held)
    }
    #[test]
    fn runstate_could_tp_teleporter_now() {
        assert!(could_tp_items_case(
            &item_set([entity_types::ITEM_TELEPORTER]),
            &item_set([]),
        ));
    }
    #[test]
    fn runstate_could_tp_teleporter_backpack_last_tick() {
        // Telepack may have exploded, leaving the item set empty this
        // tick; still counts.
        assert!(could_tp_items_case(
            &item_set([]),
            &item_set([entity_types::ITEM_TELEPORTER_BACKPACK]),
        ));
    }
    #[test]
    fn runstate_could_tp_unrelated_powerup_false() {
        assert!(!could_tp_items_case(
            &item_set([entity_types::ITEM_POWERUP_COMPASS]),
            &item_set([]),
        ));
    }
    #[test]
    fn runstate_could_tp_empty_hands_false() {
        assert!(!could_tp_items_case(&item_set([]), &item_set([])));
    }

    // could_tp_mount: 2 cases. Axolotl mount teleports on command,
    // so an equipped axolotl also flips `could_tp` even without a
    // teleporter item.
    fn could_tp_mount_case(mount: EntityType) -> bool {
        let rs = RunState::new();
        let mut player = default_player();
        player.overlay_type = Some(mount);
        rs.could_tp(&player, &item_set([]), &item_set([]))
    }
    #[test]
    fn runstate_could_tp_qilin_false() {
        assert!(!could_tp_mount_case(entity_types::MOUNT_QILIN));
    }
    #[test]
    fn runstate_could_tp_axolotl_true() {
        assert!(could_tp_mount_case(entity_types::MOUNT_AXOLOTL));
    }

    // had_clover_ghost_spawned: 8 cases. Time-level and hud-flag
    // are overridden inside the function body, so the effective test
    // surface is just the 8 rows.
    fn ghost_spawn_case(
        level_started: bool,
        ghost_spawned: bool,
        new_entities: &[EntityType],
    ) -> bool {
        let mut rs = RunState::new();
        rs.level_started = level_started;
        rs.ghost_spawned = ghost_spawned;
        for &t in new_entities {
            rs.new_entity_types.insert(t);
        }
        rs.update_had_clover(t2f(0, 0), HudFlags::empty());
        rs.ghost_spawned
    }
    #[test]
    fn runstate_ghost_spawn_no_reset_no_ghost_stays_false() {
        assert!(!ghost_spawn_case(false, false, &[]));
    }
    #[test]
    fn runstate_ghost_spawn_no_reset_prev_ghost_stays_true() {
        assert!(ghost_spawn_case(false, true, &[]));
    }
    #[test]
    fn runstate_ghost_spawn_level_reset_prev_true_flips_false() {
        assert!(!ghost_spawn_case(true, true, &[]));
    }
    #[test]
    fn runstate_ghost_spawn_level_reset_prev_false_stays_false() {
        assert!(!ghost_spawn_case(true, false, &[]));
    }
    #[test]
    fn runstate_ghost_spawn_no_reset_ghost_appears_flips_true() {
        assert!(ghost_spawn_case(false, false, &[entity_types::MONS_GHOST]));
    }
    #[test]
    fn runstate_ghost_spawn_no_reset_ghost_appears_stays_true() {
        assert!(ghost_spawn_case(false, true, &[entity_types::MONS_GHOST]));
    }
    #[test]
    fn runstate_ghost_spawn_level_reset_ghost_appears_flips_true() {
        // Reset drops to false, then MONS_GHOST scan flips it back on.
        assert!(ghost_spawn_case(true, false, &[entity_types::MONS_GHOST]));
    }
    #[test]
    fn runstate_ghost_spawn_level_reset_and_ghost_stays_true() {
        assert!(ghost_spawn_case(true, true, &[entity_types::MONS_GHOST]));
    }

    // rope_deployed: 4 cases. Only ITEM_CLIMBABLE_ROPE (the post-embed
    // state) drops No%, and only outside Duat.
    fn rope_deployed_case(new_entities: &[EntityType], theme: Theme) -> RunState {
        let mut rs = RunState::new();
        for &t in new_entities {
            rs.new_entity_types.insert(t);
        }
        rs.update_rope_deployed(theme);
        rs
    }
    #[test]
    fn runstate_rope_deployed_empty_keeps_no() {
        let rs = rope_deployed_case(&[], Theme::Dwelling);
        assert!(rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_rope_deployed_uncocked_rope_keeps_no() {
        // ITEM_ROPE is the still-in-inventory / thrown state; only
        // CLIMBABLE_ROPE (after the embed) counts as deployed.
        let rs = rope_deployed_case(&[entity_types::ITEM_ROPE], Theme::Jungle);
        assert!(rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_rope_deployed_climbable_rope_drops_no() {
        let rs = rope_deployed_case(&[entity_types::ITEM_CLIMBABLE_ROPE], Theme::Temple);
        assert!(!rs.run_label.contains(Label::No));
    }
    #[test]
    fn runstate_rope_deployed_climbable_rope_in_duat_exempt() {
        // Duat bombs can revert climb ropes to ITEM_ROPE, so the
        // deploy check is skipped there.
        let rs = rope_deployed_case(&[entity_types::ITEM_CLIMBABLE_ROPE], Theme::Duat);
        assert!(rs.run_label.contains(Label::No));
    }

    // no_tp: 7 cases. Fields are pre-extracted into
    // `TeleportShadowSnap`, so the tests inject the pair directly.
    // Same idle_counter both sides (torn-read guard) plus the src
    // shadow's Illumination is zero (empty), representing a default
    // Illumination on the src LightEmitter.
    #[allow(clippy::too_many_arguments)]
    fn no_tp_case(
        player_x: f32,
        player_y: f32,
        player_vx: f32,
        player_vy: f32,
        idle_counter: u32,
        shadow_x: f32,
        shadow_y: f32,
    ) -> RunState {
        let mut rs = RunState::new();
        rs.new_teleport_shadows.push(TeleportShadowSnap {
            idle_counter,
            light_pos_x: 0.0,
            light_pos_y: 0.0,
        });
        rs.new_teleport_shadows.push(TeleportShadowSnap {
            idle_counter,
            light_pos_x: shadow_x,
            light_pos_y: shadow_y,
        });
        let mut player = default_player();
        player.position_x = player_x;
        player.position_y = player_y;
        player.velocity_x = player_vx;
        player.velocity_y = player_vy;
        let motion = PlayerMotion {
            position_x: player_x,
            position_y: player_y,
            velocity_x: player_vx,
            velocity_y: player_vy,
        };
        let items = item_set([entity_types::ITEM_TELEPORTER_BACKPACK]);
        let prev = item_set([]);
        rs.update_no_tp(&player, &items, &prev, Some(motion));
        rs
    }
    #[test]
    fn runstate_no_tp_stationary_shadow_close_matches_discards() {
        let rs = no_tp_case(5.0, 8.0, 0.0, 0.0, 0, 5.1, 8.2);
        assert!(!rs.run_label.contains(Label::NoTeleporter));
    }
    #[test]
    fn runstate_no_tp_moving_back_1_frame_matches_discards() {
        let rs = no_tp_case(10.5, 1.5, 0.2, 0.3, 1, 10.0, 1.0);
        assert!(!rs.run_label.contains(Label::NoTeleporter));
    }
    #[test]
    fn runstate_no_tp_moving_back_3_frames_matches_discards() {
        let rs = no_tp_case(19.5, 9.5, 0.2, 0.3, 3, 18.5, 8.5);
        assert!(!rs.run_label.contains(Label::NoTeleporter));
    }
    #[test]
    fn runstate_no_tp_stationary_shadow_far_keeps_label() {
        let rs = no_tp_case(1.0, 2.0, 0.0, 0.0, 0, 7.0, 9.0);
        assert!(rs.run_label.contains(Label::NoTeleporter));
    }
    #[test]
    fn runstate_no_tp_moving_back_2_frames_x_miss_keeps() {
        let rs = no_tp_case(11.5, 3.5, 0.2, 0.3, 2, 11.0, 2.0);
        assert!(rs.run_label.contains(Label::NoTeleporter));
    }
    #[test]
    fn runstate_no_tp_moving_back_2_frames_y_miss_keeps() {
        let rs = no_tp_case(13.5, 3.5, 0.3, 0.2, 2, 13.0, 4.0);
        assert!(rs.run_label.contains(Label::NoTeleporter));
    }
    #[test]
    fn runstate_no_tp_stationary_far_keeps_dup() {
        // Duplicate of the (1,2,0,0,0,7,9,True) row, given its own
        // name so the test count matches expectations.
        let rs = no_tp_case(1.0, 2.0, 0.0, 0.0, 0, 7.0, 9.0);
        assert!(rs.run_label.contains(Label::NoTeleporter));
    }

    // new_entities: 5 cases. End-to-end walk of the UidEntityMap via
    // `compute_new_entities`. Results dedupe into a HashSet, so the
    // "2x WOODEN_ARROW" case becomes "set contains WOODEN_ARROW".
    fn new_entities_case(
        screen: Screen,
        level_started: bool,
        entity_types: &[EntityType],
    ) -> RunState {
        let mut builder = EntityMapBuilder::new();
        let mut rs = RunState::new();
        rs.level_started = level_started;
        rs.prev_next_uid = Some(builder.next_uid());
        builder.add_trivial_entities(entity_types);
        let mut snap = empty_snapshot();
        snap.screen = screen;
        snap.next_entity_uid = builder.next_uid();
        let mut inputs = ChainInputs::stub(snap);
        inputs.entity_map = builder.to_map();
        let proc = ml2_mem::MockProcess {
            data: builder.buffer(),
        };
        rs.compute_new_entities(&inputs, &proc);
        rs
    }
    #[test]
    fn runstate_new_entities_single_webgun_collected() {
        let rs = new_entities_case(Screen::Level, false, &[entity_types::ITEM_WEBGUN]);
        assert!(rs.new_entity_types.contains(&entity_types::ITEM_WEBGUN));
        assert_eq!(rs.new_entity_types.len(), 1);
    }
    #[test]
    fn runstate_new_entities_two_distinct_collected() {
        let rs = new_entities_case(
            Screen::Level,
            false,
            &[entity_types::ITEM_JETPACK, entity_types::ITEM_TELEPORTER],
        );
        assert!(rs.new_entity_types.contains(&entity_types::ITEM_JETPACK));
        assert!(rs.new_entity_types.contains(&entity_types::ITEM_TELEPORTER));
        assert_eq!(rs.new_entity_types.len(), 2);
    }
    #[test]
    fn runstate_new_entities_duplicates_collapse_to_set() {
        // Duplicates collapse into a single set entry.
        let rs = new_entities_case(
            Screen::Level,
            false,
            &[
                entity_types::ITEM_WOODEN_ARROW,
                entity_types::ITEM_WOODEN_ARROW,
            ],
        );
        assert!(
            rs.new_entity_types
                .contains(&entity_types::ITEM_WOODEN_ARROW)
        );
        assert_eq!(rs.new_entity_types.len(), 1);
    }
    #[test]
    fn runstate_new_entities_level_started_skips_scan() {
        // level_started: early return; the pending entity delta is
        // dropped (the game just spawned the whole level's initial
        // burst on this tick).
        let rs = new_entities_case(Screen::Level, true, &[entity_types::FX_TELEPORTSHADOW]);
        assert!(rs.new_entity_types.is_empty());
        assert!(rs.new_teleport_shadows.is_empty());
    }
    #[test]
    fn runstate_new_entities_non_level_screen_skips_scan() {
        let rs = new_entities_case(
            Screen::LevelTransition,
            false,
            &[entity_types::CHAR_HIREDHAND],
        );
        assert!(rs.new_entity_types.is_empty());
        assert!(rs.new_teleport_shadows.is_empty());
    }

    // world_themes_state: 7 cases. update_world_themes writes to
    // world2_theme when the world-2 theme arrives, world4_theme when
    // world-4 does; CoG/Duat imply Temple, Abzu implies TidePool.
    fn world_themes_state_case(world: u8, theme: Theme) -> RunState {
        let mut rs = RunState::new();
        rs.update_world_themes(world, theme);
        rs
    }
    #[test]
    fn runstate_world_themes_state_2_jungle_sets_world2() {
        let rs = world_themes_state_case(2, Theme::Jungle);
        assert_eq!(rs.world2_theme, Some(Theme::Jungle));
        assert_eq!(rs.world4_theme, None);
    }
    #[test]
    fn runstate_world_themes_state_2_volcana_sets_world2() {
        let rs = world_themes_state_case(2, Theme::Volcana);
        assert_eq!(rs.world2_theme, Some(Theme::Volcana));
        assert_eq!(rs.world4_theme, None);
    }
    #[test]
    fn runstate_world_themes_state_4_temple_sets_world4_temple() {
        let rs = world_themes_state_case(4, Theme::Temple);
        assert_eq!(rs.world2_theme, None);
        assert_eq!(rs.world4_theme, Some(Theme::Temple));
    }
    #[test]
    fn runstate_world_themes_state_4_cog_implies_temple() {
        let rs = world_themes_state_case(4, Theme::CityOfGold);
        assert_eq!(rs.world2_theme, None);
        assert_eq!(rs.world4_theme, Some(Theme::Temple));
    }
    #[test]
    fn runstate_world_themes_state_4_duat_implies_temple() {
        let rs = world_themes_state_case(4, Theme::Duat);
        assert_eq!(rs.world2_theme, None);
        assert_eq!(rs.world4_theme, Some(Theme::Temple));
    }
    #[test]
    fn runstate_world_themes_state_4_tidepool_sets_world4_tidepool() {
        let rs = world_themes_state_case(4, Theme::TidePool);
        assert_eq!(rs.world2_theme, None);
        assert_eq!(rs.world4_theme, Some(Theme::TidePool));
    }
    #[test]
    fn runstate_world_themes_state_4_abzu_implies_tidepool() {
        let rs = world_themes_state_case(4, Theme::Abzu);
        assert_eq!(rs.world2_theme, None);
        assert_eq!(rs.world4_theme, Some(Theme::TidePool));
    }

    // world_themes_label: 12 cases. Same update_world_themes but
    // examined via the run_label side effect: Volcana+Temple adds
    // VolcanaTemple; Jungle with a not-yet-known or Temple world-4
    // adds JungleTemple; anything that lands on a non-Temple world-4
    // with world-2 Jungle discards JungleTemple.
    fn world_themes_label_case(
        world: u8,
        theme: Theme,
        world2_theme: Option<Theme>,
        starting: &[Label],
    ) -> RunState {
        let mut rs = RunState::new();
        rs.run_label = RunLabel::with_starting(starting.iter().copied().collect()).unwrap();
        rs.world2_theme = world2_theme;
        rs.update_world_themes(world, theme);
        rs
    }
    // "Volcana plain" and V/T
    #[test]
    fn runstate_world_themes_label_2_volcana_no_prior_no_extra() {
        let rs = world_themes_label_case(2, Theme::Volcana, None, &[Label::Any]);
        assert!(!rs.run_label.contains(Label::VolcanaTemple));
        assert!(!rs.run_label.contains(Label::JungleTemple));
    }
    #[test]
    fn runstate_world_themes_label_2_tidepool_after_volcana_no_extra() {
        let rs = world_themes_label_case(2, Theme::TidePool, Some(Theme::Volcana), &[Label::Any]);
        assert!(!rs.run_label.contains(Label::VolcanaTemple));
        assert!(!rs.run_label.contains(Label::JungleTemple));
    }
    #[test]
    fn runstate_world_themes_label_2_temple_after_volcana_adds_vt() {
        let rs = world_themes_label_case(2, Theme::Temple, Some(Theme::Volcana), &[Label::Any]);
        assert!(rs.run_label.contains(Label::VolcanaTemple));
    }
    // Eager J/T assumption
    #[test]
    fn runstate_world_themes_label_2_jungle_no_prior_adds_jt() {
        let rs = world_themes_label_case(2, Theme::Jungle, None, &[Label::Any]);
        assert!(rs.run_label.contains(Label::JungleTemple));
    }
    #[test]
    fn runstate_world_themes_label_2_jungle_after_jungle_any_terminus_adds_jt() {
        let rs = world_themes_label_case(2, Theme::Jungle, Some(Theme::Jungle), &[Label::Any]);
        assert!(rs.run_label.contains(Label::JungleTemple));
    }
    #[test]
    fn runstate_world_themes_label_2_jungle_after_jungle_sc_terminus_adds_jt() {
        let rs =
            world_themes_label_case(2, Theme::Jungle, Some(Theme::Jungle), &[Label::SunkenCity]);
        assert!(rs.run_label.contains(Label::JungleTemple));
    }
    // Actually went J/T
    #[test]
    fn runstate_world_themes_label_4_temple_after_jungle_jt_any_keeps_jt() {
        let rs = world_themes_label_case(
            4,
            Theme::Temple,
            Some(Theme::Jungle),
            &[Label::JungleTemple, Label::Any],
        );
        assert!(rs.run_label.contains(Label::JungleTemple));
    }
    #[test]
    fn runstate_world_themes_label_4_temple_after_jungle_jt_sc_keeps_jt() {
        let rs = world_themes_label_case(
            4,
            Theme::Temple,
            Some(Theme::Jungle),
            &[Label::JungleTemple, Label::SunkenCity],
        );
        assert!(rs.run_label.contains(Label::JungleTemple));
    }
    #[test]
    fn runstate_world_themes_label_4_temple_after_jungle_jt_any_keeps_jt_dup() {
        // Duplicate of the JT+Any row inside the "actually went J/T"
        // block, kept as a separate test to preserve the count.
        let rs = world_themes_label_case(
            4,
            Theme::Temple,
            Some(Theme::Jungle),
            &[Label::JungleTemple, Label::Any],
        );
        assert!(rs.run_label.contains(Label::JungleTemple));
    }
    // Went Jungle but J/T is now impossible (world-4 landed on TidePool)
    #[test]
    fn runstate_world_themes_label_4_tidepool_after_jungle_jt_any_drops_jt() {
        let rs = world_themes_label_case(
            4,
            Theme::TidePool,
            Some(Theme::Jungle),
            &[Label::JungleTemple, Label::Any],
        );
        assert!(!rs.run_label.contains(Label::JungleTemple));
        assert!(!rs.run_label.contains(Label::VolcanaTemple));
    }
    #[test]
    fn runstate_world_themes_label_4_tidepool_after_jungle_jt_sc_drops_jt() {
        let rs = world_themes_label_case(
            4,
            Theme::TidePool,
            Some(Theme::Jungle),
            &[Label::JungleTemple, Label::SunkenCity],
        );
        assert!(!rs.run_label.contains(Label::JungleTemple));
        assert!(!rs.run_label.contains(Label::VolcanaTemple));
    }
    #[test]
    fn runstate_world_themes_label_4_tidepool_after_jungle_jt_any_drops_jt_dup() {
        // Second duplicate: same "went Jungle then TidePool" outcome
        // as the JT+Any row above.
        let rs = world_themes_label_case(
            4,
            Theme::TidePool,
            Some(Theme::Jungle),
            &[Label::JungleTemple, Label::Any],
        );
        assert!(!rs.run_label.contains(Label::JungleTemple));
        assert!(!rs.run_label.contains(Label::VolcanaTemple));
    }

    #[test]
    fn bad_screen_discriminant_errors() {
        let mut data = vec![0u8; 0x2000];
        // 99 is not a valid Screen; expect BadEnum.
        data[0x0C..0x10].copy_from_slice(&99i32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let err = <State as MemStruct>::read_from(&proc, 0).unwrap_err();
        match err {
            ml2_mem::MemError::BadEnum { ty, value } => {
                assert_eq!(ty, "Screen");
                assert_eq!(value, 99);
            }
            other => panic!("expected BadEnum, got {other:?}"),
        }
    }
}
