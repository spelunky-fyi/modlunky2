//! Bitflag game-state fields.
//!
//! Uses the `bitflags` crate for ergonomic set operations and prints,
//! plus a small hand-rolled `MemType + MemLayout` impl per struct so
//! they compose into `MemStruct`-derived containers. Reads use
//! `from_bits_retain` so a game update adding new flag bits doesn't
//! panic; unknown bits are preserved and callers can log them if they
//! care.

use bitflags::bitflags;
use ml2_mem::{MemLayout, MemType, ReadProcess, Result};

macro_rules! impl_mem_bitflags {
    ($ty:ty, $repr:ty) => {
        impl MemType for $ty {
            fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
                let raw = <$repr as MemType>::read_from(process, addr)?;
                Ok(Self::from_bits_retain(raw))
            }
        }
        impl MemLayout for $ty {
            const SIZE: usize = <$repr as MemLayout>::SIZE;
        }
    };
}

bitflags! {
    /// Recap-screen flags set as a run progresses; determines pacifist /
    /// no-gold / eggplant / ending-type badges. Bit indices match the
    /// game's exe (bit 0 = pacifist, bit 20 = died).
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub struct RunRecapFlags: u32 {
        const PACIFIST         = 1 << 0;
        const VEGAN            = 1 << 1;
        const VEGETARIAN       = 1 << 2;
        const PETTY_CRIMINAL   = 1 << 3;
        const WANTED_CRIMINAL  = 1 << 4;
        const CRIME_LORD       = 1 << 5;
        const KING             = 1 << 6;
        const QUEEN            = 1 << 7;
        const FOOL             = 1 << 8;
        const EGGPLANT         = 1 << 9;
        const NO_GOLD          = 1 << 10;
        const LIKED_PETS       = 1 << 11;
        const LOVED_PETS       = 1 << 12;
        const TOOK_DAMAGE      = 1 << 13;
        const USED_ANKH        = 1 << 14;
        const KILLED_KINGU     = 1 << 15;
        const KILLED_OSIRIS    = 1 << 16;
        const NORMAL_ENDING    = 1 << 17;
        const HARD_ENDING      = 1 << 18;
        const SPECIAL_ENDING   = 1 << 19;
        const DIED             = 1 << 20;
    }
}

bitflags! {
    /// HUD state flags; the tracker cares about ALLOW_PAUSE (indicates
    /// active run) and HAVE_CLOVER (score-attack tracking).
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub struct HudFlags: u32 {
        const UPBEAT_DWELLING_MUSIC     = 1 << 0;
        const RUNNING_TUTORIAL_SPEEDRUN = 1 << 2;
        const ALLOW_PAUSE               = 1 << 19;
        const HAVE_CLOVER               = 1 << 22;
    }
}

bitflags! {
    /// Quest-completion flags; drives the CO chain gate on the Category
    /// tracker.
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub struct QuestFlags: u32 {
        const MOON_CHALLENGE = 1 << 24;
        const STAR_CHALLENGE = 1 << 25;
        const SUN_CHALLENGE  = 1 << 26;
    }
}

bitflags! {
    /// Currently-active challenge flags (screen presence, not quest
    /// completion). Distinct from QuestFlags; different bits and
    /// semantics.
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub struct PresenceFlags: u32 {
        const MOON_CHALLENGE = 1 << 8;
        const STAR_CHALLENGE = 1 << 9;
        const SUN_CHALLENGE  = 1 << 10;
    }
}

impl_mem_bitflags!(RunRecapFlags, u32);
impl_mem_bitflags!(HudFlags, u32);
impl_mem_bitflags!(QuestFlags, u32);
impl_mem_bitflags!(PresenceFlags, u32);
