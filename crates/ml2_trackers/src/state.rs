//! `State`: the root object every tracker reads from. Only the subset
//! actually consumed by the six trackers is decoded for now; more
//! fields can be added as needed. Offsets are stable across game
//! versions except when Blitworks bumps them, at which point the
//! drift surfaces via either bogus enum reads (BadEnum error) or
//! transcript replay.

use ml2_mem::{MemStruct, Pointer, Spel2Process};

use crate::entity::{EntityType, Items};
use crate::entity_map::UidEntityMap;
use crate::enums::{LoadingState, Screen, Theme, WinState};
use crate::flags::{HudFlags, PresenceFlags, QuestFlags, RunRecapFlags};

/// Distance from the feedcode marker to the start of the `State`
/// object. The marker sits five bytes into a struct that precedes
/// State by 0x5F bytes.
pub const FEEDCODE_TO_STATE_OFFSET: u64 = 0x5F;

/// Level configuration state hanging off the pointer at
/// `State::theme_info`. Currently used only for CO tracker's sub-theme
/// address; other fields can be added in follow-ups.
#[derive(Debug, MemStruct)]
pub struct ThemeInfo {
    #[offset(0x10)]
    pub sub_theme_address: u64,
}

#[derive(Debug, MemStruct)]
pub struct State {
    #[offset(0x08)]
    pub screen_last: Screen,
    #[offset(0x0C)]
    pub screen: Screen,
    #[offset(0x10)]
    pub screen_next: Screen,
    #[offset(0x14)]
    pub loading: LoadingState,
    #[offset(0x38)]
    pub quest_flags: QuestFlags,

    /// Non-positive during a run; total spent at shops + stolen by
    /// leprechauns. Turns positive on victory when the bonus lands.
    #[offset(0x58)]
    pub money_shop_total: i32,

    #[offset(0x5C)]
    pub world_start: u8,
    #[offset(0x5D)]
    pub level_start: u8,
    #[offset(0x5E)]
    pub theme_start: Theme,

    /// In-run elapsed time in game ticks (60 Hz).
    #[offset(0x64)]
    pub time_total: u32,

    #[offset(0x68)]
    pub world: u8,
    #[offset(0x69)]
    pub world_next: u8,
    #[offset(0x6A)]
    pub level: u8,
    #[offset(0x6B)]
    pub level_next: u8,

    /// Pointer to ThemeInfo. Null on menu / camp; non-null once a level
    /// is loaded. Follow with `theme_info.load(process)`.
    #[offset(0x6C)]
    pub theme_info: Pointer<ThemeInfo>,

    #[offset(0x74)]
    pub theme: Theme,
    #[offset(0x75)]
    pub theme_next: Theme,
    #[offset(0x76)]
    pub win_state: WinState,

    /// Total levels traversed this run. Distinct from `level` (in-area
    /// level number); kept 0-based to match the exe.
    #[offset(0x83)]
    pub level_count: u8,

    /// Fixed 99-slot array of EntityType IDs currently deposited in
    /// Waddler's storage room. Zero slots are empty. Wire layout: 99
    /// contiguous u32 entries starting at 0x8C.
    #[offset(0x8C)]
    pub waddler_storage: [EntityType; 99],

    /// Timers all in game ticks. Level tick resets on transition;
    /// last_level snapshots the previous level's total on transition;
    /// tutorial is the standalone tutorial timer.
    #[offset(0xA40)]
    pub time_last_level: u32,
    #[offset(0xA44)]
    pub time_level: u32,
    #[offset(0xA48)]
    pub time_tutorial: u32,

    #[offset(0xA34)]
    pub run_recap_flags: RunRecapFlags,
    #[offset(0xA50)]
    pub hud_flags: HudFlags,
    #[offset(0xA54)]
    pub presence_flags: PresenceFlags,

    /// Next entity UID the game will assign. Comparing consecutive
    /// values yields how many entities spawned since the last tick
    /// (used by RunState to find TP shadows, deployed ropes, ghost
    /// spawn, etc).
    #[offset(0x12E0)]
    pub next_entity_uid: u32,

    /// Pointer to the four-player Items block. Null until a run
    /// starts; walk `items.players[0]` for the primary player.
    #[offset(0x12F0)]
    pub items: Pointer<Items>,

    /// Robin Hood open-addressing hashmap keyed by entity UID. Used
    /// by chains to walk companions + look up items on the fly.
    #[offset(0x1348)]
    pub instance_id_to_pointer: UidEntityMap,

    #[offset(0x13A0)]
    pub time_startup: u32,
}

impl State {
    /// Attach to the running game, scan for the feedcode marker, read
    /// State at `feedcode - 0x5F`. Errors surface the same variants
    /// they do lower down (NotAttached / FeedcodeMissing / Read).
    pub fn read_current(process: &Spel2Process) -> ml2_mem::Result<Self> {
        let feedcode = process.get_feedcode()?;
        let base = feedcode - FEEDCODE_TO_STATE_OFFSET;
        <Self as MemStruct>::read_from(process, base)
    }
}
