//! Eggplant chain.
//!
//! Longer FSM: collect the eggplant, carry it to 5-1, hand it to the
//! Eggplant Child, guide the child through 7-1, visit Eggplant World,
//! collect the Eggplant Crown. Once the crown is in-hand the run
//! can't fall out of chain again.

use crate::chain::{ChainStepResult, ChainStepper};
use crate::chain_impl::inputs::ChainInputs;
use crate::entity_types as et;
use crate::enums::{Screen, Theme};

pub fn make_stepper() -> ChainStepper<ChainInputs> {
    ChainStepper::new("EggplantChain", collect_eggplant)
}

pub(crate) fn collect_eggplant(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_EGGPLANT) {
        return ChainStepResult::in_progress(carry_eggplant_to_51);
    }
    // The eggplant child can be picked up in world 5 even without
    // hand-carrying the eggplant (co-op edge case).
    if ctx.state.world == 5 && ctx.some_companion_is(et::CHAR_EGGPLANT_CHILD) {
        return ChainStepResult::in_progress(guide_eggplant_child_to_71);
    }
    // A companion may have grabbed the eggplant during the transition.
    if ctx.state.screen == Screen::LevelTransition && ctx.some_companion_has_item(et::ITEM_EGGPLANT)
    {
        return ChainStepResult::in_progress(carry_eggplant_to_51);
    }
    if ctx.state.world > 5 {
        return ChainStepResult::failed();
    }
    ChainStepResult::unstarted()
}

pub(crate) fn carry_eggplant_to_51(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.state.world > 4 {
        return ChainStepResult::in_progress(collect_eggplant_child);
    }
    if ctx.state.screen != Screen::LevelTransition {
        return ChainStepResult::in_progress(carry_eggplant_to_51);
    }
    if ctx.player_items.contains(&et::ITEM_EGGPLANT)
        || ctx.waddler_contains(et::ITEM_EGGPLANT)
        || ctx.some_companion_has_item(et::ITEM_EGGPLANT)
    {
        return ChainStepResult::in_progress(carry_eggplant_to_51);
    }
    // Dropped the eggplant. Player can grab another this run, reset.
    ChainStepResult::unstarted()
}

pub(crate) fn collect_eggplant_child(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.some_companion_is(et::CHAR_EGGPLANT_CHILD) {
        return ChainStepResult::in_progress(guide_eggplant_child_to_71);
    }
    if ctx.state.world > 5 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_eggplant_child)
}

pub(crate) fn guide_eggplant_child_to_71(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    let wl = ctx.state.world_level();
    if wl > (7, 1) {
        return ChainStepResult::in_progress(visit_eggplant_world);
    }
    if ctx.state.screen != Screen::LevelTransition {
        return ChainStepResult::in_progress(guide_eggplant_child_to_71);
    }
    // The child is transferred off-screen during the 7-1 transition,
    // so its absence there specifically doesn't fail the chain.
    if wl == (7, 1) {
        return ChainStepResult::in_progress(visit_eggplant_world);
    }
    if ctx.some_companion_is(et::CHAR_EGGPLANT_CHILD) {
        return ChainStepResult::in_progress(guide_eggplant_child_to_71);
    }
    ChainStepResult::failed()
}

pub(crate) fn visit_eggplant_world(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.state.theme == Theme::EggplantWorld {
        return ChainStepResult::in_progress(collect_eggplant_crown);
    }
    if ctx.state.world_level() > (7, 1) {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(visit_eggplant_world)
}

pub(crate) fn collect_eggplant_crown(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_EGGPLANTCROWN) {
        return ChainStepResult::in_progress(success);
    }
    if ctx.state.world_level() > (7, 2) {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_eggplant_crown)
}

pub(crate) fn success(_ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Once the crown lands the chain can't fail. Perpetual
    // InProgress(success) is the fixed point.
    ChainStepResult::in_progress(success)
}
