//! Category tracker core. On every game-state tick, RunState:
//!
//! - Advances the four quest-chain steppers (Abzu, Duat, Cosmic,
//!   Eggplant).
//! - Runs ~25 update_* methods that mutate a `RunLabel` based on
//!   current + previous player inventory, health/bombs/ropes, mount
//!   ownership, cursed/poisoned state, chain progress, terminus
//!   inference, etc.
//! - Produces a display string via `get_display(screen, config)`.
//!
//! Comments preserve the rationale-per-branch for each detector.
//!
//! ## Entity-delta detectors
//!
//! Detectors include ghost spawn, rope deploy, and TP shadow. Pairs
//! of `FX_TELEPORTSHADOW` entities are downcast to `LightEmitter` at
//! spawn, player motion is collapsed through the overlay chain, and
//! detected TP events discard the `NoTeleporter` label using a
//! 0.5-tile tolerance.

use crate::chain::{ChainStatus, ChainStepper};
use crate::chain_impl::inputs::{ChainInputs, PlayerMotion, PlayerSnapshot};
use crate::chain_impl::{cosmic, eggplant, sunken};
use crate::entity::{
    BACKPACKS, CharState, EntityType, LOW_BANNED_ATTACKABLES, LOW_BANNED_THROWABLES, Layer, MOUNTS,
    NON_CHAIN_POWERUP_ENTITIES, SHIELDS,
};
use crate::entity_types as et;
use crate::enums::{LoadingState, Screen, Theme, WinState};
use crate::flags::{HudFlags, PresenceFlags, RunRecapFlags};
use crate::label::{Label, RunLabel, SaveableCategory};

/// Category tracker's runtime state. Owned by whichever caller drives
/// the tracker (typically the tauri-side TrackerTask); `update(...)`
/// is called every ~16 ms with a fresh `ChainInputs` and
/// `get_display(...)` renders the current label to a string.
pub struct RunState {
    pub run_label: RunLabel,

    // Field visibility: `pub(crate)` on fields the `#[cfg(test)]` block
    // in `ml2_trackers/src/lib.rs` mutates directly to set up test
    // states. Encapsulation is preserved outside the crate boundary,
    // but the test seam is exposed within it.
    pub(crate) world: u8,
    pub(crate) level: u8,
    pub(crate) level_started: bool,

    pub(crate) player_item_types: std::collections::HashSet<EntityType>,
    pub(crate) player_last_item_types: std::collections::HashSet<EntityType>,

    pub(crate) final_death: bool,

    pub(crate) health: i8,
    pub(crate) bombs: u8,
    pub(crate) ropes: u8,
    pub(crate) level_start_ropes: u8,

    pub(crate) poisoned: bool,
    pub(crate) cursed: bool,

    is_score_run: bool,

    pub(crate) ghost_spawned: bool,
    pub(crate) is_low_percent: bool,

    pub(crate) failed_low_if_not_chain: bool,

    pub(crate) mc_has_swung_mattock: bool,

    pub(crate) had_ankh: bool,
    pub(crate) sunken_chain_status: ChainStatus,

    pub(crate) clone_gun_wo_cosmic: bool,

    pub(crate) world2_theme: Option<Theme>,
    pub(crate) world4_theme: Option<Theme>,

    pub(crate) abzu_stepper: ChainStepper<ChainInputs>,
    pub(crate) duat_stepper: ChainStepper<ChainInputs>,
    pub(crate) cosmic_stepper: ChainStepper<ChainInputs>,
    pub(crate) eggplant_stepper: ChainStepper<ChainInputs>,

    /// Last tick's `state.next_entity_uid`. UIDs in
    /// `(prev_next_uid..cur_next_uid)` were spawned this tick. None
    /// on first frame + on any tick that jumped through a non-Level
    /// screen (where the delta would sweep in the whole level's
    /// initial spawn burst).
    pub(crate) prev_next_uid: Option<u32>,
    /// EntityTypes that appeared this tick. Populated in `update()`
    /// via the entity-delta walk; consumed by the low% detectors
    /// (ghost spawn, rope deploy). Cleared each frame.
    pub(crate) new_entity_types: std::collections::HashSet<EntityType>,
    /// Every FX_TELEPORTSHADOW that spawned this tick, decoded into
    /// (idle_counter, light_pos_x, light_pos_y). Game emits these in
    /// pairs; TP shadow detection pairs consecutive entries and
    /// compares to the extrapolated player position.
    pub(crate) new_teleport_shadows: Vec<TeleportShadowSnap>,
}

/// A single TP shadow decoded off the FX_TELEPORTSHADOW entity that
/// just spawned. `idle_counter` doubles as the frame offset from
/// spawn to the game's teleport-effect firing; RunState uses that to
/// backtrack the player's position for comparison.
#[derive(Debug, Clone, Copy)]
pub(crate) struct TeleportShadowSnap {
    pub(crate) idle_counter: u32,
    pub(crate) light_pos_x: f32,
    pub(crate) light_pos_y: f32,
}

/// Category-tracker config surface the display uses. Field names use
/// kebab-case in JSON so an existing `modlunky2.json` round-trips
/// without losing Category-tracker settings the user already picked.
/// `serde(default)` on each field means a missing entry falls back to
/// `Default`.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "kebab-case", default)]
pub struct CategoryTrackerConfig {
    pub always_show_modifiers: bool,
    pub excluded_categories: Vec<SaveableCategory>,
}

impl Default for RunState {
    fn default() -> Self {
        Self::new()
    }
}

impl RunState {
    pub fn new() -> Self {
        Self {
            run_label: RunLabel::new(),
            world: 0,
            level: 0,
            level_started: false,
            player_item_types: Default::default(),
            player_last_item_types: Default::default(),
            final_death: false,
            health: 4,
            bombs: 4,
            ropes: 4,
            level_start_ropes: 4,
            poisoned: false,
            cursed: false,
            is_score_run: false,
            ghost_spawned: false,
            is_low_percent: true,
            failed_low_if_not_chain: false,
            mc_has_swung_mattock: false,
            had_ankh: false,
            sunken_chain_status: ChainStatus::Unstarted,
            clone_gun_wo_cosmic: false,
            world2_theme: None,
            world4_theme: None,
            abzu_stepper: sunken::abzu::make_stepper(),
            duat_stepper: sunken::duat::make_stepper(),
            cosmic_stepper: cosmic::make_stepper(),
            eggplant_stepper: eggplant::make_stepper(),
            prev_next_uid: None,
            new_entity_types: std::collections::HashSet::new(),
            new_teleport_shadows: Vec::new(),
        }
    }

    // ---------------------------------------------------------------
    // Update entry point
    // ---------------------------------------------------------------

    /// Advance the runstate one frame. Silent early-returns: nothing
    /// to do while the game is loading, when there's no items block,
    /// or when player 0 / its inventory can't be read.
    ///
    /// `process` is the game handle being read this tick. RunState
    /// needs it (in addition to `inputs`) so it can resolve UIDs from
    /// the entity delta into their EntityType, which drives ghost +
    /// rope + TP shadow detection.
    pub fn update(&mut self, inputs: &ChainInputs, process: &dyn ml2_mem::ReadProcess) {
        if !matches!(inputs.state.loading, LoadingState::NotLoading) {
            return;
        }
        let Some(player) = inputs.player0 else {
            return;
        };

        let run_recap_flags = inputs.state.run_recap_flags;
        let hud_flags = inputs.state.hud_flags;
        let presence_flags = inputs.state.presence_flags;

        self.update_global_state(inputs);
        self.update_on_level_start(inputs.state.world, inputs.state.theme, self.ropes);
        // update_player_item_types is folded into ChainInputs::from_process,
        // but the "last" set is rotated here so subsequent update_*
        // methods see the correct diff.
        self.player_last_item_types = std::mem::take(&mut self.player_item_types);
        self.player_item_types = inputs.player_items.clone();
        // Clone the item sets locally so the update_* methods can
        // still take `&mut self`. Sets are ~10-50 EntityTypes; the
        // per-frame clone is cheap relative to the process reads
        // that built them.
        let cur_items = self.player_item_types.clone();
        let prev_items = self.player_last_item_types.clone();

        self.update_final_death(player.state, &cur_items);
        // Populate `new_entity_types` from the delta since last tick.
        // Called after update_global_state (which sets level_started)
        // so the level-entry burst that would otherwise sweep in
        // every floor tile + treasure spawn gets skipped.
        self.compute_new_entities(inputs, process);

        self.update_score_items(&cur_items);
        self.update_ice_caves(inputs);

        // Advance every chain against the current inputs. Uses each
        // stepper's fn-pointer FSM directly; no allocation.
        self.abzu_stepper.evaluate(inputs);
        self.duat_stepper.evaluate(inputs);
        self.cosmic_stepper.evaluate(inputs);
        self.eggplant_stepper.evaluate(inputs);

        // Modifiers.
        self.update_pacifist(run_recap_flags);
        self.update_no_gold(run_recap_flags);
        self.update_no_tp(&player, &cur_items, &prev_items, inputs.player_motion);
        self.update_eggplant();
        self.update_true_crown(&cur_items);
        self.update_low_cosmic();

        // Category criteria.
        self.update_has_mounted_tame(inputs.state.theme, &player);
        self.update_starting_resources(&player, inputs.state.win_state);
        self.update_status_effects(player.state, &cur_items);
        self.update_had_clover(inputs.state.time_level, hud_flags);
        self.update_wore_backpack(&cur_items);
        self.update_held_shield(&cur_items);
        self.update_has_non_chain_powerup(&cur_items);
        self.update_attacked_with(
            player.last_state,
            player.state,
            player.layer_enum(),
            inputs.state.world,
            self.level,
            inputs.state.theme,
            presence_flags,
            &cur_items,
            &prev_items,
        );
        self.update_attacked_with_throwables(
            player.last_state,
            player.state,
            &prev_items,
            &cur_items,
        );

        // Chain / terminus / trailing checks.
        self.update_has_chain_powerup(&cur_items);
        self.update_is_chain();

        self.update_rope_deployed(inputs.state.theme);
        self.update_millionaire(inputs, &player, &cur_items);

        self.update_terminus(inputs);
    }

    // ---------------------------------------------------------------
    // The 20+ update_* methods.
    // ---------------------------------------------------------------

    pub(crate) fn update_pacifist(&mut self, run_recap_flags: RunRecapFlags) {
        if !run_recap_flags.contains(RunRecapFlags::PACIFIST) {
            let _ = self.run_label.discard(&[Label::Pacifist]);
        }
    }

    pub(crate) fn update_no_gold(&mut self, run_recap_flags: RunRecapFlags) {
        if !run_recap_flags.contains(RunRecapFlags::NO_GOLD) {
            let _ = self.run_label.discard(&[Label::NoGold, Label::No]);
        }
    }

    /// TP shadow detection. Walks `FX_TELEPORTSHADOW` entities that
    /// spawned this tick (captured in `new_teleport_shadows`), pairs
    /// consecutive entries, projects the player backwards by the
    /// shadow's idle_counter frames, and discards `Label::NoTeleporter`
    /// when a shadow position matches the extrapolated player.
    pub(crate) fn update_no_tp(
        &mut self,
        player: &PlayerSnapshot,
        player_item_set: &std::collections::HashSet<EntityType>,
        prev_player_item_set: &std::collections::HashSet<EntityType>,
        player_motion: Option<PlayerMotion>,
    ) {
        // Cheap early-out: if the player couldn't have TP'd this
        // tick, skip the shadow scan entirely.
        if !self.could_tp(player, player_item_set, prev_player_item_set) {
            return;
        }

        // Game emits shadows in pairs of 2 (prev pos + cur pos).
        let shadows = &self.new_teleport_shadows;
        if shadows.len() < 2 {
            return;
        }
        let Some(motion) = player_motion else {
            return;
        };

        // Position tolerance. Game snaps to a grid, but idle_counter
        // rounding + a moving-object velocity produces sub-tile
        // drift; 0.5 tiles is the empirical threshold.
        const X_TOL: f32 = 0.5;
        const Y_TOL: f32 = 0.5;

        // Pair consecutive shadows. If `shadows.len()` is odd, drop
        // the trailing one (torn read mid-pair).
        for pair in shadows.chunks_exact(2) {
            let prev_shadow = pair[0];
            let cur_shadow = pair[1];
            // Torn read guard: both shadows in a pair must share the
            // same idle_counter or skip the pair. Prefer false
            // negative over false positive.
            if prev_shadow.idle_counter != cur_shadow.idle_counter {
                continue;
            }
            let (x, y) = motion.extrapolate(-(cur_shadow.idle_counter as f32));
            let dx = x - cur_shadow.light_pos_x;
            let dy = y - cur_shadow.light_pos_y;
            if dx.abs() < X_TOL && dy.abs() < Y_TOL {
                let _ = self.run_label.discard(&[Label::NoTeleporter]);
            }
        }
    }

    /// Fast reject for `update_no_tp`. TP is only possible when the
    /// player currently holds a teleporter (or held one last tick and
    /// dropped it) OR is riding an axolotl (which teleports on
    /// command).
    pub(crate) fn could_tp(
        &self,
        player: &PlayerSnapshot,
        player_item_set: &std::collections::HashSet<EntityType>,
        prev_player_item_set: &std::collections::HashSet<EntityType>,
    ) -> bool {
        for ty in crate::entity::TELEPORT_ENTITIES.iter() {
            if player_item_set.contains(ty) || prev_player_item_set.contains(ty) {
                return true;
            }
        }
        player.overlay_type == Some(et::MOUNT_AXOLOTL)
    }

    fn update_eggplant(&mut self) {
        if self.eggplant_stepper.last_status().is_in_progress() {
            let _ = self.run_label.add(Label::Eggplant);
        } else {
            let _ = self.run_label.discard(&[Label::Eggplant]);
        }
    }

    pub(crate) fn update_true_crown(
        &mut self,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if player_item_types.contains(&et::ITEM_POWERUP_TRUECROWN) {
            let _ = self.run_label.add(Label::TrueCrown);
        }
    }

    fn update_low_cosmic(&mut self) {
        if self.cosmic_stepper.last_status().is_failed() && self.mc_has_swung_mattock {
            self.fail_low();
        }
    }

    pub(crate) fn update_ice_caves(&mut self, inputs: &ChainInputs) {
        if !self.level_started {
            return;
        }
        if inputs.state.theme != Theme::IceCaves {
            return;
        }
        if (inputs.state.world_start, inputs.state.level_start) != (5, 1) {
            return;
        }
        let _ = self.run_label.add(Label::IceCavesShortcut);
    }

    pub(crate) fn update_score_items(
        &mut self,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        for &item_type in player_item_types {
            if item_type == et::ITEM_PLASMACANNON || item_type == et::ITEM_POWERUP_TRUECROWN {
                self.is_score_run = true;
                let _ = self.run_label.add(Label::Score);
            }
        }
    }

    fn update_global_state(&mut self, inputs: &ChainInputs) {
        let world = inputs.state.world;
        let level = inputs.state.level;
        self.level_started = (world, level) != (self.world, self.level);
        self.world = world;
        self.level = level;
    }

    pub(crate) fn update_final_death(
        &mut self,
        player_state: CharState,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if self.final_death {
            return;
        }
        if matches!(player_state, CharState::Dying)
            && !player_item_types.contains(&et::ITEM_POWERUP_ANKH)
        {
            self.final_death = true;
        }
    }

    pub(crate) fn update_has_mounted_tame(&mut self, theme: Theme, player: &PlayerSnapshot) {
        if !self.is_low_percent {
            return;
        }
        let Some(entity_type) = player.overlay_type else {
            return;
        };
        // Riding a tamed qilin in Tiamat's Throne is chain-only OK.
        if theme == Theme::Tiamat && entity_type == et::MOUNT_QILIN {
            self.failed_low_if_not_chain = true;
            if !self.sunken_chain_status.is_in_progress() {
                self.fail_low();
            }
            return;
        }
        if MOUNTS.contains(&entity_type) && player.overlay_tamed_mount {
            self.fail_low();
        }
    }

    pub(crate) fn update_starting_resources(
        &mut self,
        player: &PlayerSnapshot,
        win_state: WinState,
    ) {
        if !self.is_low_percent {
            return;
        }
        let health = player.health;
        if (health > self.health && player.state != CharState::Dying) || health > 4 {
            self.fail_low();
        }
        if health < 4 {
            let _ = self.run_label.discard(&[Label::No]);
        }
        self.health = health;

        let bombs = player.inventory.bombs;
        if bombs > self.bombs || bombs > 4 {
            self.fail_low();
        }
        if bombs < 4 {
            let _ = self.run_label.discard(&[Label::No]);
        }
        self.bombs = bombs;

        let ropes = player.inventory.ropes;
        if ropes > self.level_start_ropes || ropes > 4 {
            self.fail_low();
        }
        // Post-win rope check: leftover ropes still count against No%.
        if win_state != WinState::NoWin && ropes < 4 {
            let _ = self.run_label.discard(&[Label::No]);
        }
        self.ropes = ropes;
    }

    pub(crate) fn update_status_effects(
        &mut self,
        player_state: CharState,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if !self.is_low_percent {
            return;
        }
        if matches!(player_state, CharState::Entering | CharState::Loading) {
            return;
        }

        let is_poisoned = player_item_types.contains(&et::LOGICAL_POISONED_EFFECT);
        let is_cursed = player_item_types.contains(&et::LOGICAL_CURSED_EFFECT);

        if self.poisoned && !is_poisoned && player_state != CharState::Dying {
            self.fail_low();
        }
        if self.cursed && !is_cursed && player_state != CharState::Dying {
            self.fail_low();
        }
        self.poisoned = is_poisoned;
        self.cursed = is_cursed;
    }

    pub(crate) fn update_had_clover(&mut self, time_level: u32, hud_flags: HudFlags) {
        if !self.is_low_percent {
            return;
        }
        if self.level_started {
            self.ghost_spawned = false;
        }
        // Any MONS_GHOST spawn this tick means the "held clover past
        // the time threshold" check should stop failing low%. The
        // ghost eats the clover a few frames before it becomes
        // visible; this flag latches to avoid oscillating at the
        // boundary.
        if self.new_entity_types.contains(&et::MONS_GHOST) {
            self.ghost_spawned = true;
        }
        if self.ghost_spawned {
            return;
        }
        if !hud_flags.contains(HudFlags::HAVE_CLOVER) {
            return;
        }
        // Ghost eats the clover a few frames before spawning; check
        // slightly early so the fail window doesn't get missed.
        let frame_margin = 5u32;
        let normal_time = time_to_frames(3, 0).saturating_sub(frame_margin);
        let cursed_time = time_to_frames(2, 30).saturating_sub(frame_margin);
        if self.cursed && time_level >= cursed_time {
            self.fail_low();
        }
        if time_level >= normal_time {
            self.fail_low();
        }
    }

    pub(crate) fn update_wore_backpack(
        &mut self,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if player_item_types.contains(&et::ITEM_JETPACK) {
            let _ = self.run_label.discard(&[Label::NoJetpack]);
        }
        if !self.is_low_percent {
            return;
        }
        for &item_type in player_item_types {
            if BACKPACKS.contains(&item_type) {
                self.fail_low();
                return;
            }
        }
    }

    pub(crate) fn update_held_shield(
        &mut self,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if !self.is_low_percent {
            return;
        }
        for &item_type in player_item_types {
            if SHIELDS.contains(&item_type) {
                self.fail_low();
                return;
            }
        }
    }

    pub(crate) fn update_has_chain_powerup(
        &mut self,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if player_item_types.contains(&et::ITEM_POWERUP_ANKH) {
            self.had_ankh = true;
        }
        if self.sunken_chain_status.is_in_progress() {
            return;
        }
        // Chain failed: picking up chain-only powerups fails low%.
        for &item_type in player_item_types {
            if item_type == et::ITEM_POWERUP_ANKH || item_type == et::ITEM_POWERUP_TABLETOFDESTINY {
                self.fail_low();
            }
        }
    }

    pub(crate) fn update_has_non_chain_powerup(
        &mut self,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if !self.is_low_percent {
            return;
        }
        for &item_type in player_item_types {
            if NON_CHAIN_POWERUP_ENTITIES.contains(&item_type) {
                self.fail_low();
                return;
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    pub(crate) fn update_attacked_with(
        &mut self,
        last_state: CharState,
        state: CharState,
        layer: Layer,
        world: u8,
        level: u8,
        theme: Theme,
        presence_flags: PresenceFlags,
        player_item_types: &std::collections::HashSet<EntityType>,
        prev_player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if !self.is_low_percent {
            return;
        }
        if state != CharState::Attacking && last_state != CharState::Attacking {
            return;
        }
        // Boomerang leaves the inventory the instant you throw it, so
        // "used to have boomerang, no longer have it, just started
        // attacking" = boomerang throw and failed low%.
        if last_state != CharState::Attacking
            && prev_player_item_types.contains(&et::ITEM_BOOMERANG)
            && !player_item_types.contains(&et::ITEM_BOOMERANG)
        {
            self.fail_low();
        }

        for &item_type in player_item_types {
            if !LOW_BANNED_ATTACKABLES.contains(&item_type) {
                continue;
            }
            // Excalibur is Abzu-chain OK.
            if item_type == et::ITEM_EXCALIBUR && theme == Theme::Abzu {
                self.failed_low_if_not_chain = true;
                if !self.sunken_chain_status.is_in_progress() {
                    self.fail_low();
                }
                continue;
            }
            // Mattock is OK in Moon Challenge back layer.
            if item_type == et::ITEM_MATTOCK
                && matches!(layer, Layer::Back)
                && presence_flags.contains(PresenceFlags::MOON_CHALLENGE)
            {
                self.mc_has_swung_mattock = true;
                continue;
            }
            if item_type == et::ITEM_HOUYIBOW {
                // Hou Yi bow is OK in challenges, in Waddler levels,
                // and against Hundun.
                if matches!(layer, Layer::Back) {
                    let in_challenge = presence_flags.contains(PresenceFlags::MOON_CHALLENGE)
                        || presence_flags.contains(PresenceFlags::SUN_CHALLENGE);
                    let waddler_level = matches!((world, level), (3, 1) | (5, 1) | (7, 1));
                    if in_challenge || waddler_level {
                        continue;
                    }
                }
                if (world, level) == (7, 4) {
                    continue;
                }
            }
            self.fail_low();
            return;
        }
    }

    pub(crate) fn update_attacked_with_throwables(
        &mut self,
        player_state: CharState,
        player_last_state: CharState,
        player_last_item_types: &std::collections::HashSet<EntityType>,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        if !self.is_low_percent {
            return;
        }
        if player_state != CharState::Throwing && player_last_state != CharState::Throwing {
            return;
        }
        for &item_type in player_item_types.union(player_last_item_types) {
            if LOW_BANNED_THROWABLES.contains(&item_type) {
                self.fail_low();
                return;
            }
        }
    }

    pub(crate) fn update_world_themes(&mut self, world: u8, theme: Theme) {
        if world != 2 && world != 4 {
            return;
        }
        if theme == Theme::Jungle || theme == Theme::Volcana {
            self.world2_theme = Some(theme);
        } else if theme == Theme::Temple || theme == Theme::CityOfGold || theme == Theme::Duat {
            self.world4_theme = Some(Theme::Temple);
        } else if theme == Theme::TidePool || theme == Theme::Abzu {
            self.world4_theme = Some(Theme::TidePool);
        }

        if self.world2_theme == Some(Theme::Volcana) && self.world4_theme == Some(Theme::Temple) {
            let _ = self.run_label.add(Label::VolcanaTemple);
        }

        let jungle_temple_ok = matches!(self.world4_theme, None | Some(Theme::Temple));
        if self.world2_theme == Some(Theme::Jungle) && jungle_temple_ok {
            let _ = self.run_label.add(Label::JungleTemple);
        } else {
            let _ = self.run_label.discard(&[Label::JungleTemple]);
        }
    }

    pub(crate) fn update_terminus(&mut self, inputs: &ChainInputs) {
        let terminus = if self.cosmic_stepper.last_status().is_in_progress()
            || inputs.state.win_state == WinState::CosmicOcean
        {
            Label::CosmicOcean
        } else if self.final_death {
            Label::Death
        } else if inputs.state.world == 7
            || inputs.state.win_state == WinState::Hundun
            || self.had_ankh
            || self.sunken_chain_status.is_in_progress()
            || self.eggplant_stepper.last_status().is_in_progress()
        {
            Label::SunkenCity
        } else {
            Label::Any
        };

        if terminus == Label::CosmicOcean {
            let _ = self.run_label.discard(&[Label::NoCo]);
        } else {
            let _ = self.run_label.add(Label::NoCo);
        }
        let _ = self.run_label.set_terminus(terminus);
    }

    pub(crate) fn update_is_chain(&mut self) {
        if self.sunken_chain_status.is_failed() {
            return;
        }
        let abzu = self.abzu_stepper.last_status();
        let duat = self.duat_stepper.last_status();

        // Both should either be unstarted or not. Keep the invariant
        // as a debug assert so a chain-start bug surfaces during
        // development while the tracker never panics in production.
        debug_assert!(
            abzu.is_unstarted() == duat.is_unstarted(),
            "abzu/duat unstarted mismatch: abzu={abzu:?} duat={duat:?}"
        );

        if abzu.is_unstarted() {
            self.sunken_chain_status = ChainStatus::Unstarted;
            return;
        }

        if abzu.is_in_progress() || duat.is_in_progress() {
            let _ = self.run_label.add(Label::Chain);
            self.sunken_chain_status = ChainStatus::InProgress;
            // Starting a chain invalidates plain Low%.
            self.failed_low_if_not_chain = true;
        }
        if abzu.is_in_progress() && !duat.is_in_progress() {
            let _ = self.run_label.add(Label::Abzu);
        }
        if duat.is_in_progress() && !abzu.is_in_progress() {
            let _ = self.run_label.add(Label::Duat);
        }
        if !(abzu.is_failed() && duat.is_failed()) {
            return;
        }
        // Both chains failed: chain terminus failed, drop labels.
        self.sunken_chain_status = ChainStatus::Failed;
        let _ = self
            .run_label
            .discard(&[Label::Chain, Label::Abzu, Label::Duat]);
        if self.failed_low_if_not_chain {
            self.fail_low();
        }
    }

    pub(crate) fn update_millionaire(
        &mut self,
        inputs: &ChainInputs,
        player: &PlayerSnapshot,
        player_item_types: &std::collections::HashSet<EntityType>,
    ) {
        let collected_this_level = player.inventory.money as i64;
        let collected_prev_levels = player.inventory.collected_money_total as i64;
        let shop_and_bonus = inputs.state.money_shop_total as i64;
        let net_score = collected_this_level + collected_prev_levels + shop_and_bonus;

        // Category needs a completion + $100K bonus.
        if net_score >= 900_000 {
            let _ = self.run_label.add(Label::Millionaire);
        }
        // Drop millionaire when either lost money OR bought the clone
        // gun (which paths toward the completion bonus) but ended a
        // non-victory run below threshold.
        if net_score < 900_000
            && (!self.clone_gun_wo_cosmic || inputs.state.win_state != WinState::NoWin)
        {
            let _ = self.run_label.discard(&[Label::Millionaire]);
        }
        if self.clone_gun_wo_cosmic || self.cosmic_stepper.last_status().is_in_progress() {
            return;
        }
        if player_item_types.contains(&et::ITEM_CLONEGUN) {
            self.clone_gun_wo_cosmic = true;
            let _ = self.run_label.add(Label::Millionaire);
        }
    }

    /// Scan `new_entity_types` for `ITEM_CLIMBABLE_ROPE` (the state
    /// a fired rope enters after it lands on the wall) and discard
    /// `Label::No` when one appears. Duat is skipped because ropes
    /// there can revert to `ITEM_ROPE` when the anchor wall is
    /// bombed; a false positive there would incorrectly fail No%.
    pub(crate) fn update_rope_deployed(&mut self, theme: Theme) {
        if theme == Theme::Duat {
            return;
        }
        if self.new_entity_types.contains(&et::ITEM_CLIMBABLE_ROPE) {
            let _ = self.run_label.discard(&[Label::No]);
        }
    }

    /// Walk the UIDs the game spawned since last tick and resolve
    /// each to an `EntityType`. Only runs on Level screens; the
    /// level-entry burst is skipped by resetting `prev_next_uid`
    /// whenever `level_started` is true. Fills `self.new_entity_types`
    /// for consumption by the ghost-spawn + rope-deploy detectors.
    pub(crate) fn compute_new_entities(
        &mut self,
        inputs: &ChainInputs,
        process: &dyn ml2_mem::ReadProcess,
    ) {
        self.new_entity_types.clear();
        self.new_teleport_shadows.clear();
        if !matches!(inputs.state.screen, Screen::Level) {
            return;
        }
        let cur = inputs.state.next_entity_uid;
        if self.level_started {
            self.prev_next_uid = Some(cur);
            return;
        }
        let Some(prev) = self.prev_next_uid else {
            self.prev_next_uid = Some(cur);
            return;
        };
        // If the game recycled UIDs backwards (shouldn't happen; guard
        // against a torn read serving a bogus value that would panic
        // the range).
        if cur < prev {
            self.prev_next_uid = Some(cur);
            return;
        }
        for uid in prev..cur {
            let Ok(Some(handle)) = inputs.entity_map.get(process, uid as i32) else {
                continue;
            };
            let Some(db) = handle.entity.type_.load(process).ok().flatten() else {
                continue;
            };
            self.new_entity_types.insert(db.id);
            // FX_TELEPORTSHADOW carries the destination the game will
            // TP the player to. Downcast the entity as LightEmitter to
            // pull idle_counter + Illumination position.
            if db.id == et::FX_TELEPORTSHADOW
                && let Some(snap) = read_shadow_snapshot(process, handle.addr)
            {
                self.new_teleport_shadows.push(snap);
            }
        }
        self.prev_next_uid = Some(cur);
    }

    fn fail_low(&mut self) {
        self.is_low_percent = false;
        let _ = self.run_label.discard(&[Label::Low, Label::No]);
    }

    pub(crate) fn update_on_level_start(&mut self, world: u8, theme: Theme, ropes: u8) {
        if !self.level_started {
            return;
        }
        self.update_world_themes(world, theme);
        self.level_start_ropes = ropes;
        if ropes < 4 {
            let _ = self.run_label.discard(&[Label::No]);
        }
        if theme == Theme::Duat {
            // Sacrifice at CoG lands the player in Duat with fresh
            // resources; reset the trackers' baselines so Low% doesn't
            // fail on the (illusory) health increase.
            self.health = 4;
            self.poisoned = false;
            self.cursed = false;
        }
    }

    // ---------------------------------------------------------------
    // Display.
    // ---------------------------------------------------------------

    fn should_show_modifiers(&self, screen: Screen, always_show_modifiers: bool) -> bool {
        if always_show_modifiers {
            return true;
        }
        if screen == Screen::Scores {
            return true;
        }
        if self.world > 1 {
            return true;
        }
        if self.level > 2 {
            return true;
        }
        if self.final_death {
            return true;
        }
        false
    }

    /// Render the current label to a display string. `screen` comes
    /// from the live state; `config` holds user preferences from the
    /// tracker config panel.
    pub fn get_display(&self, screen: Screen, config: &CategoryTrackerConfig) -> String {
        let hide_early = !self.should_show_modifiers(screen, config.always_show_modifiers);
        self.run_label.text(hide_early, &config.excluded_categories)
    }

    /// True once the player has died past-the-point-of-recovery (no
    /// ankh present at time of death). Used by the CategoryTracker
    /// wrapper to signal end-of-run styling to the OBS front-end.
    pub fn is_final_death(&self) -> bool {
        self.final_death
    }

    /// True while the run still qualifies as low%. Used by the Pacino
    /// Golf tracker: strokes lock to infinity once low% breaks.
    pub fn is_low_percent(&self) -> bool {
        self.is_low_percent
    }
}

/// Converts an mm:ss time to game frames (60 Hz).
pub(crate) fn time_to_frames(minutes: u32, seconds: u32) -> u32 {
    seconds * 60 + minutes * 60 * 60
}

/// Downcast an FX_TELEPORTSHADOW entity at `addr` to LightEmitter and
/// snapshot the fields TP detection needs. Returns None on any read
/// failure or a null Illumination pointer (torn read during spawn).
fn read_shadow_snapshot(
    process: &dyn ml2_mem::ReadProcess,
    addr: u64,
) -> Option<TeleportShadowSnap> {
    let emitter =
        <crate::entity::LightEmitter as ml2_mem::MemType>::read_from(process, addr).ok()?;
    let illum = emitter.emitted_light.load(process).ok().flatten()?;
    Some(TeleportShadowSnap {
        idle_counter: emitter.idle_counter,
        light_pos_x: illum.light_pos_x,
        light_pos_y: illum.light_pos_y,
    })
}
