//! The three concrete quest chains + the shared `ChainInputs` snapshot
//! they all consume. RunState (later) builds `ChainInputs` from the
//! live process once per tick and evaluates every chain against it.

pub mod cosmic;
pub mod eggplant;
pub mod inputs;
pub mod sunken;

pub use inputs::{ChainInputs, StateSnapshot};
