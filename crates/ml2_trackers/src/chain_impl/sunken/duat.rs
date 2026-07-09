//! Duat variant of the sunken chain. Route: Udjat Eye -> Hedjet/Crown
//! -> Ankh -> Temple 4-1 -> carry Scepter into 4-2 -> City of Gold ->
//! keep Ankh -> Duat 4-4 -> Tablet -> Ushabti to 6-3 -> Hundun / CO.
//!
//! Diverges from Abzu at the world-4 item step: Duat needs an
//! elaborate scepter-carry / ankh-keep sequence (Duat is only
//! reachable by sacrificing at City of Gold's altar) where Abzu just
//! needs Excalibur pulled from the stone.

use crate::chain::{ChainStepResult, ChainStepper};
use crate::chain_impl::inputs::ChainInputs;
use crate::entity::CharState;
use crate::entity_types as et;
use crate::enums::{Screen, Theme, WinState};

pub fn make_stepper() -> ChainStepper<ChainInputs> {
    ChainStepper::new("DuatChain", collect_eye_or_headwear)
}

fn collect_eye_or_headwear(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
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

fn collect_headwear(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
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

fn collect_ankh(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_ANKH) {
        return ChainStepResult::in_progress(visit_world41_theme);
    }
    if ctx.state.world > 3 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_ankh)
}

fn visit_world41_theme(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Duat: world41 theme is Temple.
    if ctx.state.theme == Theme::Temple {
        return ChainStepResult::in_progress(carry_scepter_to_42);
    }
    if ctx.state.world > 3 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(visit_world41_theme)
}

pub(crate) fn carry_scepter_to_42(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Ankh is a hard requirement to even reach Duat; dropping it fails
    // the chain.
    if !ctx.player_items.contains(&et::ITEM_POWERUP_ANKH) {
        return ChainStepResult::failed();
    }
    // Once past 4-2 (i.e. at CoG in 4-3), skip to the CoG step.
    if ctx.state.world_level() > (4, 2) {
        return ChainStepResult::in_progress(visit_city_of_gold);
    }
    // Scepter must be carried through the 4-1 -> 4-2 transition
    // specifically.
    let wls = (ctx.state.world, ctx.state.level, ctx.state.screen);
    if wls != (4, 1, Screen::LevelTransition) {
        return ChainStepResult::in_progress(carry_scepter_to_42);
    }
    if ctx.player_items.contains(&et::ITEM_SCEPTER) || ctx.some_companion_has_item(et::ITEM_SCEPTER)
    {
        return ChainStepResult::in_progress(visit_city_of_gold);
    }
    ChainStepResult::failed()
}

pub(crate) fn visit_city_of_gold(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if !ctx.player_items.contains(&et::ITEM_POWERUP_ANKH) {
        return ChainStepResult::failed();
    }
    if ctx.state.theme == Theme::CityOfGold {
        return ChainStepResult::in_progress(keep_ankh);
    }
    if ctx.state.world_level() > (4, 2) {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(visit_city_of_gold)
}

pub(crate) fn keep_ankh(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    // Once past 4-3 in CoG the run is headed for Duat; there's no
    // player instance during the sacrifice transition, so defer the
    // theme check to 4-4.
    if ctx.state.world_level() > (4, 3) {
        return ChainStepResult::in_progress(visit_world44_theme);
    }
    // Sacrifice destroys the player briefly; the player_state is
    // None or Stunned during those frames, skip the Ankh check
    // then. Only fail on lost-Ankh when the player is up and not
    // stunned.
    let player_stunned = matches!(ctx.player0_char_state, Some(CharState::Stunned));
    if ctx.player0_char_state.is_some()
        && !player_stunned
        && !ctx.player_items.contains(&et::ITEM_POWERUP_ANKH)
    {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(keep_ankh)
}

pub(crate) fn visit_world44_theme(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.state.theme == Theme::Duat {
        return ChainStepResult::in_progress(collect_tablet);
    }
    if ctx.state.world_level() > (4, 3) {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(visit_world44_theme)
}

fn collect_tablet(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.player_items.contains(&et::ITEM_POWERUP_TABLETOFDESTINY) {
        return ChainStepResult::in_progress(carry_ushabti_to_63);
    }
    if ctx.state.world > 4 {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(collect_tablet)
}

fn carry_ushabti_to_63(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
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

fn win_via_hundun_or_co(ctx: &ChainInputs) -> ChainStepResult<ChainInputs> {
    if ctx.state.win_state == WinState::Tiamat {
        return ChainStepResult::failed();
    }
    ChainStepResult::in_progress(win_via_hundun_or_co)
}
