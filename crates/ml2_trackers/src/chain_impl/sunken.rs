//! Sunken chain.
//!
//! Two variants: Abzu (Tide Pool -> Abzu, requires Excalibur) and
//! Duat (Temple -> Duat, requires Scepter + Ankh + City of Gold).
//!
//! Every `Step<C>` is a bare fn pointer with no way to carry
//! chain-instance state, so each variant gets its own module of step
//! functions. Shared steps (`collect_eye_or_headwear`,
//! `collect_headwear`, `collect_ankh`, `visit_world44_theme`,
//! `collect_tablet`, `carry_ushabti_to_63`, `win_via_hundun_or_co`)
//! are duplicated across the two modules. Total duplication is ~120
//! LOC and much cleaner than threading a runtime dispatch through a
//! function-pointer FSM. The variant modules only differ in the
//! themes they check and which world-4 item step they transition to.

pub mod abzu;
pub mod duat;
