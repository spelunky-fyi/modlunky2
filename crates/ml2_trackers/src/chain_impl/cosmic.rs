//! Cosmic Ocean chain.
//!
//! A short three-step FSM: collect the Hou Yi bow -> keep carrying it
//! all the way to Hundun -> stay alive through the CO stack until a
//! CO win. `chain_impl/inputs.rs` precomputes the companion + waddler
//! queries so every step is a pure function over `ChainInputs`.

use crate::chain::{ChainStepResult, ChainStepper};
use crate::chain_impl::inputs::ChainInputs;
use crate::entity_types as et;
use crate::enums::{Screen, WinState};

pub fn make_stepper() -> ChainStepper<ChainInputs> {
    ChainStepper::new("CosmicOceanChain", collect_bow)
}

pub(crate) fn collect_bow(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_HOUYIBOW) {
        return ChainStepResult::in_progress(carry_bow_to_hundun);
    }
    // Bow lives in the jungle / volcana section (world 2). Past that
    // without picking it up = failure.
    if ctx.state.world > 2 {
        return ChainStepResult::failed();
    }
    ChainStepResult::unstarted()
}

pub(crate) fn carry_bow_to_hundun(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.state.win_state != WinState::NoWin {
        return ChainStepResult::failed();
    }
    let wl = ctx.state.world_level();
    if wl > (7, 3) {
        return ChainStepResult::in_progress(win_via_co);
    }
    if ctx.state.screen != Screen::LevelTransition {
        return ChainStepResult::in_progress(carry_bow_to_hundun);
    }
    if ctx.player_items.contains(&et::ITEM_HOUYIBOW)
        || ctx.some_companion_has_item(et::ITEM_HOUYIBOW)
    {
        return ChainStepResult::in_progress(carry_bow_to_hundun);
    }
    // Bow can be safely stashed in Waddler's storage before world 7
    // and still counts as carried.
    if wl < (7, 1) && ctx.waddler_contains(et::ITEM_HOUYIBOW) {
        return ChainStepResult::in_progress(carry_bow_to_hundun);
    }
    ChainStepResult::failed()
}

pub(crate) fn win_via_co(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Stay in-progress through the CO climb until either the CO win
    // lands or a non-CO win-state comes through (means a different
    // ending fired).
    let ws = ctx.state.win_state;
    if ws == WinState::NoWin || ws == WinState::CosmicOcean {
        return ChainStepResult::in_progress(win_via_co);
    }
    ChainStepResult::failed()
}
