//! Arena mode config block. Carries the base offset in `State`,
//! every field offset, and every settings enum with its numeric wire
//! values. Not wired to `State::read_from` today because no consumer
//! needs the arena settings; a future arena tracker decodes with:
//!
//! ```ignore
//! let arena = <ArenaState as MemStruct>::read_from(
//!     process,
//!     state_addr + ARENA_STATE_BASE,
//! )?;
//! ```
//!
//! Preserved as-is so the reverse-engineering that produced the offsets
//! doesn't have to happen again if arena support lands.

use ml2_mem::{MemEnum, MemStruct};

/// Base offset of the `arena_state` block inside `State`.
pub const ARENA_STATE_BASE: u64 = 0x95C;

// ---------------------------------------------------------------------
// Enums (all `#[repr(i8)]` on the wire; the exe stores each as int8).
// ---------------------------------------------------------------------

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaFormat {
    Deathmatch = 0,
    HoldTheIdol = 1,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaRuleset {
    Casual = 0,
    Tournament = 1,
    Joust = 2,
    Frantic = 3,
    Custom = 4,
    Favorite = 5,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaTimer {
    Time0030 = 0,
    Time0100 = 1,
    Time0130 = 2,
    Time0200 = 3,
    Time0230 = 4,
    Time0300 = 5,
    Time0330 = 6,
    Time0400 = 7,
    Time0430 = 8,
    Time0500 = 9,
    Time0530 = 10,
    Time0600 = 11,
    Time0630 = 12,
    Time0700 = 13,
    Time0730 = 14,
    Time0800 = 15,
    Time0830 = 16,
    Time0900 = 17,
    Time0930 = 18,
    Time1000 = 19,
    Infinite = 20,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaTimerEnding {
    RoundEnds = 0,
    DeathMist = 1,
    AlienBlast = 2,
    LooseBombs = 3,
    Ghost = 4,
    Random = 5,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaTimeToWin {
    Seconds10 = 0,
    Seconds20 = 1,
    Seconds30 = 2,
    Seconds40 = 3,
    Seconds50 = 4,
    Seconds60 = 5,
    Seconds70 = 6,
    Seconds80 = 7,
    Seconds90 = 8,
    Seconds99 = 9,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaStunTime {
    X000 = 0,
    X025 = 1,
    X050 = 2,
    X075 = 3,
    X100 = 4,
    X125 = 5,
    X150 = 6,
    X175 = 7,
    X200 = 8,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaMount {
    None = 0,
    Turkey = 1,
    Rockdog = 2,
    Axolotl = 3,
    Random = 4,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaSelect {
    TakeTurns = 0,
    LoserPicks = 1,
    RandomLevel = 2,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaDarkLevelChance {
    None = 0,
    Percent10 = 1,
    Percent50 = 2,
    Always = 3,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaCrateFrequency {
    None = 0,
    Low = 1,
    Medium = 2,
    High = 3,
    VeryHigh = 4,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaWhipDamage {
    Hp0 = 0,
    Hp1 = 1,
    Hp2 = 2,
    Hp3 = 3,
    Hp4 = 4,
    Hp5 = 5,
    Hp10 = 6,
    Hp99 = 7,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, MemEnum)]
pub enum ArenaBreathCooldown {
    None = 0,
    X025 = 1,
    X050 = 2,
    X075 = 3,
    X100 = 4,
    X125 = 5,
    X150 = 6,
    X175 = 7,
    X200 = 8,
    BreathOff = 9,
}

// ---------------------------------------------------------------------
// ArenaState struct. Offsets are declared relative to
// `ARENA_STATE_BASE`, so decoding is a single
// `read_from(&proc, state_addr + ARENA_STATE_BASE)`.
// ---------------------------------------------------------------------

/// Full arena-mode settings block. 40-tuple booleans map to `[bool; 40]`
/// so future consumers can iterate directly without walking a Vec.
#[derive(Debug, Clone, MemStruct)]
pub struct ArenaState {
    #[offset(0x008)]
    pub format: ArenaFormat, // 0x964 in State
    #[offset(0x009)]
    pub ruleset: ArenaRuleset, // 0x965
    #[offset(0x01C)]
    pub timer: ArenaTimer, // 0x978
    #[offset(0x01D)]
    pub timer_ending: ArenaTimerEnding, // 0x979
    #[offset(0x01E)]
    pub wins: u8, // 0x97A
    #[offset(0x01F)]
    pub lives: u8, // 0x97B
    #[offset(0x020)]
    pub time_to_win: ArenaTimeToWin, // 0x97C
    #[offset(0x02A)]
    pub health: u8, // 0x986
    #[offset(0x02B)]
    pub bombs: u8, // 0x987
    #[offset(0x02C)]
    pub ropes: u8, // 0x988
    #[offset(0x02D)]
    pub stun_time: ArenaStunTime, // 0x989
    #[offset(0x02E)]
    pub mount: ArenaMount, // 0x98A
    #[offset(0x02F)]
    pub arena_select: ArenaSelect, // 0x98B
    #[offset(0x030)]
    pub arenas: [bool; 40], // 0x98C..0x9B4
    #[offset(0x058)]
    pub dark_level_chance: ArenaDarkLevelChance, // 0x9B4
    #[offset(0x059)]
    pub crate_frequency: ArenaCrateFrequency, // 0x9B5
    #[offset(0x05A)]
    pub items_enabled: [bool; 40], // 0x9B6..0x9DE
    #[offset(0x082)]
    pub items_in_crate: [bool; 40], // 0x9DE..0xA06
    #[offset(0x0AA)]
    pub held_item: i8, // 0xA06 (ArenaItem stored as i8; -1 = NOTHING)
    #[offset(0x0AB)]
    pub equipped_backitem: i8, // 0xA07 (ArenaItem)
    #[offset(0x0AC)]
    pub equipped_items: [bool; 40], // 0xA08..0xA30
    #[offset(0x0D4)]
    pub whip_damage: ArenaWhipDamage, // 0xA30
    #[offset(0x0D5)]
    pub final_ghost: bool, // 0xA31
    #[offset(0x0D6)]
    pub breath_cooldown: ArenaBreathCooldown, // 0xA32
    #[offset(0x0D7)]
    pub punish_ball: bool, // 0xA33
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn arena_state_base_pins_expected_offset() {
        assert_eq!(ARENA_STATE_BASE, 0x95C);
    }

    #[test]
    fn enum_wire_values_pin_expected_indices() {
        // Spot-check the load-bearing indices: format = 0 means
        // Deathmatch, ruleset = 4 means Custom, etc. If these
        // shift, saved configs render the wrong mode.
        assert_eq!(ArenaFormat::Deathmatch as i8, 0);
        assert_eq!(ArenaFormat::HoldTheIdol as i8, 1);
        assert_eq!(ArenaRuleset::Custom as i8, 4);
        assert_eq!(ArenaMount::Random as i8, 4);
        assert_eq!(ArenaTimer::Infinite as i8, 20);
        assert_eq!(ArenaSelect::RandomLevel as i8, 2);
    }
}
