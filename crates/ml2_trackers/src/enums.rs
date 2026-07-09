//! Game-state enums. Each enum has an explicit i32 (or u8)
//! discriminant matching the exe's numeric values; the `MemEnum`
//! derive plants a reader that errors with `MemError::BadEnum` if the
//! game ever sends an unknown value (typically a game update adding a
//! new variant).

use ml2_mem::MemEnum;

#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, MemEnum)]
pub enum Screen {
    Unknown = -1,
    Logo = 0,
    Intro = 1,
    Prologue = 2,
    Title = 3,
    MainMenu = 4,
    Options = 5,
    Unknown1 = 6,
    Leaderboards = 7,
    SeedInput = 8,
    CharacterSelect = 9,
    TeamSelect = 10,
    Camp = 11,
    Level = 12,
    LevelTransition = 13,
    Death = 14,
    Spaceship = 15,
    Ending = 16,
    Credits = 17,
    Scores = 18,
    Constellation = 19,
    Recap = 20,
    ArenaMenu = 21,
    Unknown2 = 22,
    Unknown3 = 23,
    Unknown4 = 24,
    ArenaIntro = 25,
    ArenaMatch = 26,
    ArenaScores = 27,
    LoadingOnline = 28,
    Lobby = 29,
}

#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, MemEnum)]
pub enum Theme {
    BeforeFirstRun = 0,
    Dwelling = 1,
    Jungle = 2,
    Volcana = 3,
    Olmec = 4,
    TidePool = 5,
    Temple = 6,
    IceCaves = 7,
    NeoBabylon = 8,
    SunkenCity = 9,
    CosmicOcean = 10,
    CityOfGold = 11,
    Duat = 12,
    Abzu = 13,
    Tiamat = 14,
    EggplantWorld = 15,
    Hundun = 16,
    BaseCamp = 17,
    Arena = 18,
}

#[repr(i8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, MemEnum)]
pub enum WinState {
    Unknown = -1,
    NoWin = 0,
    Tiamat = 1,
    Hundun = 2,
    CosmicOcean = 3,
}

#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, MemEnum)]
pub enum LoadingState {
    NotLoading = 0,
    Start = 1,
    Loading = 2,
    End = 3,
}
