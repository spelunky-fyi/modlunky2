//! Abzu variant of the sunken chain. Route: Udjat Eye -> Hedjet/Crown
//! -> Ankh -> Tide Pool 4-1 -> Excalibur -> Abzu 4-4 -> Tablet of
//! Destiny -> Ushabti to 6-3 -> Hundun / CO.

use crate::chain::{ChainStepResult, ChainStepper};
use crate::chain_impl::inputs::ChainInputs;
use crate::entity_types as et;
use crate::enums::{Screen, Theme, WinState};

pub fn make_stepper() -> ChainStepper<ChainInputs> {
    ChainStepper::new("AbzuChain", collect_eye_or_headwear)
}

pub(crate) fn collect_eye_or_headwear(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_UDJATEYE) {
        return ChainStepResult::in_progress(collect_headwear);
    }
    if ctx.player_items.contains(&et::ITEM_POWERUP_HEDJET)
        || ctx.player_items.contains(&et::ITEM_POWERUP_CROWN)
    {
        return ChainStepResult::in_progress(collect_ankh);
    }
    if ctx.state.world > 2 {
        return ChainStepResult::failed();
    }
    ChainStepResult::unstarted()
}

pub(crate) fn collect_headwear(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_HEDJET)
        || ctx.player_items.contains(&et::ITEM_POWERUP_CROWN)
    {
        return ChainStepResult::in_progress(collect_ankh);
    }
    if ctx.state.world > 2 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_headwear)
}

pub(crate) fn collect_ankh(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_ANKH) {
        return ChainStepResult::in_progress(visit_world41_theme);
    }
    if ctx.state.world > 3 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_ankh)
}

pub(crate) fn visit_world41_theme(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Abzu: world41 theme is Tide Pool.
    if ctx.state.theme == Theme::TidePool {
        return ChainStepResult::in_progress(collect_excalibur);
    }
    if ctx.state.world > 3 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(visit_world41_theme)
}

pub(crate) fn collect_excalibur(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_EXCALIBUR) {
        return ChainStepResult::in_progress(visit_world44_theme);
    }
    if ctx.state.world_level() > (4, 2) {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_excalibur)
}

pub(crate) fn visit_world44_theme(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Abzu: world44 theme is Abzu.
    if ctx.state.theme == Theme::Abzu {
        return ChainStepResult::in_progress(collect_tablet);
    }
    if ctx.state.world_level() > (4, 3) {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(visit_world44_theme)
}

pub(crate) fn collect_tablet(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_TABLETOFDESTINY) {
        return ChainStepResult::in_progress(carry_ushabti_to_63);
    }
    if ctx.state.world > 4 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_tablet)
}

pub(crate) fn carry_ushabti_to_63(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    let wls = (ctx.state.world, ctx.state.level, ctx.state.screen);
    if wls != (6, 2, Screen::LevelTransition) {
        return ChainStepResult::in_progress(carry_ushabti_to_63);
    }
    if ctx.player_items.contains(&et::ITEM_USHABTI) || ctx.some_companion_has_item(et::ITEM_USHABTI)
    {
        return ChainStepResult::in_progress(win_via_hundun_or_co);
    }
    ChainStepResult::failed()
}

pub(crate) fn win_via_hundun_or_co(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.state.win_state == WinState::Tiamat {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(win_via_hundun_or_co)
}
