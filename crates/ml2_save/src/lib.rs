//! Spelunky 2 `savegame.sav` reader and writer.
//!
//! The game keeps one save file in its install directory. It holds the
//! journal, the lifetime player profile, the last run, the camp stickers,
//! the arena rules and the Cosmic Ocean constellation, wrapped in a
//! two-byte format version and a trailing CRC32.
//!
//! # Editing model
//!
//! [`SaveFile`] keeps the file's bytes verbatim and reads and writes fields
//! in place. It deliberately does *not* deserialize into a struct and
//! re-serialize on the way out.
//!
//! That matters because the format is only partly understood. Over a
//! kilobyte of every save is unmapped padding, and the arena ruleset block
//! changes size between save versions. Round-tripping through a struct
//! would mean inventing values for all of it. Editing in place means an
//! untouched byte stays exactly as the game wrote it, so writing a save
//! back after changing nothing produces the identical file, and changing
//! one field cannot disturb a field nobody has decoded yet.
//!
//! ```no_run
//! # fn main() -> Result<(), ml2_save::SaveError> {
//! let mut save = ml2_save::SaveFile::read("savegame.sav")?;
//! save.set_plays(save.plays() + 1);
//! save.write("savegame.sav")?;
//! # Ok(())
//! # }
//! ```
//!
//! # Checksum
//!
//! The trailing `u32` is the bitwise complement of the CRC32 of everything
//! between the version header and the checksum itself. [`SaveFile::write`]
//! and [`SaveFile::to_bytes`] recompute it, so a save edited through this
//! crate is always internally consistent.

use std::path::Path;

pub mod constellation;
pub mod data;
pub mod layout;
pub mod stats;
mod summary;

pub use constellation::{Constellation, ConstellationLine, ConstellationStar};
pub use layout::{Layout, Tail};
pub use stats::{CategoryStats, CharacterStat, EntryStat, SaveStats, ThemeStat};
pub use summary::{
    JournalProgress, LastRun, ProgressComparison, SaveSummary, StatDelta, WorldDeaths,
};

/// Anything that can go wrong reading or writing a save.
#[derive(Debug, thiserror::Error)]
pub enum SaveError {
    #[error("failed to read {path}: {source}")]
    Read {
        path: String,
        #[source]
        source: std::io::Error,
    },
    #[error("failed to write {path}: {source}")]
    Write {
        path: String,
        #[source]
        source: std::io::Error,
    },
    #[error("not a Spelunky 2 save: {len} bytes is too short (expected at least {min})")]
    TooShort { len: usize, min: usize },
    #[error(
        "save version {version} has an unexpected length of {len} bytes; this build \
         does not know how to lay it out"
    )]
    UnsupportedLayout { len: usize, version: u16 },
    #[error(
        "save checksum does not match: file says {stored:#010x}, contents give \
         {computed:#010x}"
    )]
    ChecksumMismatch { stored: u32, computed: u32 },
    #[error(
        "this build cannot locate the constellation in a {len}-byte save of \
         version {version}, so it will not risk writing over the wrong bytes"
    )]
    ConstellationUnavailable { version: u16, len: usize },
    #[error("{what} index {index} is out of range (0..{count})")]
    IndexOutOfRange {
        what: &'static str,
        index: usize,
        count: usize,
    },
    #[error("{what} is not valid: {detail}")]
    InvalidValue {
        what: &'static str,
        detail: &'static str,
    },
}

/// Result alias for this crate.
pub type Result<T> = std::result::Result<T, SaveError>;

/// The five journal sections that carry per-entry discovery flags.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum JournalCategory {
    Places,
    Bestiary,
    People,
    Items,
    Traps,
}

impl JournalCategory {
    /// Every category, in the order the game stores them.
    pub const ALL: [JournalCategory; 5] = [
        JournalCategory::Places,
        JournalCategory::Bestiary,
        JournalCategory::People,
        JournalCategory::Items,
        JournalCategory::Traps,
    ];

    /// The discovery-flag range for this category.
    const fn range(self) -> layout::Range {
        match self {
            JournalCategory::Places => layout::PLACES,
            JournalCategory::Bestiary => layout::BESTIARY,
            JournalCategory::People => layout::PEOPLE,
            JournalCategory::Items => layout::ITEMS,
            JournalCategory::Traps => layout::TRAPS,
        }
    }

    /// How many entries the category has.
    pub const fn count(self) -> usize {
        self.range().len
    }

    /// Display name, for a heading or a legend.
    pub const fn label(self) -> &'static str {
        match self {
            JournalCategory::Places => "Places",
            JournalCategory::Bestiary => "Bestiary",
            JournalCategory::People => "People",
            JournalCategory::Items => "Items",
            JournalCategory::Traps => "Traps",
        }
    }

    /// Lower-case identifier, matching the wire format.
    pub const fn as_str(self) -> &'static str {
        match self {
            JournalCategory::Places => "places",
            JournalCategory::Bestiary => "bestiary",
            JournalCategory::People => "people",
            JournalCategory::Items => "items",
            JournalCategory::Traps => "traps",
        }
    }
}

/// The two journal categories that also count kills.
///
/// Places, items and traps are only ever discovered or not. Monsters and
/// people additionally record how many you have killed and how many times
/// each has killed you, in two parallel arrays the same length as the
/// category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KillTable {
    Bestiary,
    People,
}

impl KillTable {
    /// Both tables, in the order the game stores them.
    pub const ALL: [KillTable; 2] = [KillTable::Bestiary, KillTable::People];

    /// The journal category these counts belong to.
    pub const fn category(self) -> JournalCategory {
        match self {
            KillTable::Bestiary => JournalCategory::Bestiary,
            KillTable::People => JournalCategory::People,
        }
    }

    /// How many entries the table has.
    pub const fn count(self) -> usize {
        self.category().count()
    }

    /// Lower-case identifier, matching the wire format.
    pub const fn as_str(self) -> &'static str {
        self.category().as_str()
    }

    /// Range of "times the player killed this".
    const fn killed_range(self) -> layout::Range {
        match self {
            KillTable::Bestiary => layout::BESTIARY_KILLED,
            KillTable::People => layout::PEOPLE_KILLED,
        }
    }

    /// Range of "times this killed the player".
    const fn killed_by_range(self) -> layout::Range {
        match self {
            KillTable::Bestiary => layout::BESTIARY_KILLED_BY,
            KillTable::People => layout::PEOPLE_KILLED_BY,
        }
    }
}

/// Generates the plain get/set pairs for scalar fields at fixed offsets.
///
/// These are all the same three lines with a different type and offset, and
/// there are two dozen of them; writing them out by hand buries the handful
/// of accessors that actually do something.
macro_rules! accessors {
    ($(
        $(#[$meta:meta])*
        $get:ident / $set:ident : $ty:ident @ $offset:expr
    ),* $(,)?) => {
        $(
            $(#[$meta])*
            pub fn $get(&self) -> $ty {
                accessors!(@read self, $ty, $offset)
            }

            #[doc = concat!("Sets [`Self::", stringify!($get), "`].")]
            pub fn $set(&mut self, value: $ty) {
                accessors!(@write self, $ty, $offset, value)
            }
        )*
    };
    (@read $self:ident, u8, $offset:expr) => { $self.read_u8($offset) };
    (@read $self:ident, u32, $offset:expr) => { $self.read_u32($offset) };
    (@read $self:ident, i32, $offset:expr) => { $self.read_i32($offset) };
    (@read $self:ident, i64, $offset:expr) => { $self.read_i64($offset) };
    (@read $self:ident, f32, $offset:expr) => { $self.read_f32($offset) };
    (@read $self:ident, bool, $offset:expr) => { $self.read_bool($offset) };
    (@write $self:ident, u8, $offset:expr, $v:expr) => { $self.write_u8($offset, $v) };
    (@write $self:ident, u32, $offset:expr, $v:expr) => { $self.write_u32($offset, $v) };
    (@write $self:ident, i32, $offset:expr, $v:expr) => { $self.write_i32($offset, $v) };
    (@write $self:ident, i64, $offset:expr, $v:expr) => { $self.write_i64($offset, $v) };
    (@write $self:ident, f32, $offset:expr, $v:expr) => { $self.write_f32($offset, $v) };
    (@write $self:ident, bool, $offset:expr, $v:expr) => { $self.write_bool($offset, $v) };
}

/// A save file, held as its own bytes.
///
/// Construct one with [`SaveFile::read`] or [`SaveFile::parse`]. Field
/// accessors read and write the underlying buffer directly; nothing is
/// cached, so a getter always reflects the last setter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SaveFile {
    bytes: Vec<u8>,
    layout: Layout,
}

impl SaveFile {
    /// Reads and parses a save from disk.
    pub fn read(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        let bytes = std::fs::read(path).map_err(|source| SaveError::Read {
            path: path.display().to_string(),
            source,
        })?;
        Self::parse(bytes)
    }

    /// Parses a save from bytes, requiring the checksum to match.
    ///
    /// A mismatch means the file was truncated, hand-edited without fixing
    /// the CRC, or is not a save at all. Use [`SaveFile::parse_unchecked`]
    /// to load one anyway, which is how a corrupted save can still be
    /// inspected before being thrown away.
    pub fn parse(bytes: Vec<u8>) -> Result<Self> {
        let save = Self::parse_unchecked(bytes)?;
        let stored = save.stored_checksum();
        let computed = save.computed_checksum();
        if stored != computed {
            return Err(SaveError::ChecksumMismatch { stored, computed });
        }
        Ok(save)
    }

    /// Parses a save without verifying the checksum.
    pub fn parse_unchecked(bytes: Vec<u8>) -> Result<Self> {
        if bytes.len() < layout::MIN_FILE_LEN {
            return Err(SaveError::TooShort {
                len: bytes.len(),
                min: layout::MIN_FILE_LEN,
            });
        }
        let version = u16::from_le_bytes([bytes[0], bytes[1]]);
        let layout = Layout::derive(bytes.len(), version).ok_or(SaveError::UnsupportedLayout {
            len: bytes.len(),
            version,
        })?;
        Ok(Self { bytes, layout })
    }

    /// Serializes the save, recomputing the checksum.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = self.bytes.clone();
        let crc = self.computed_checksum();
        let at = self.layout.crc();
        out[at..at + 4].copy_from_slice(&crc.to_le_bytes());
        out
    }

    /// Writes the save to disk, recomputing the checksum.
    ///
    /// This truncates and rewrites in one go. Callers that care about not
    /// destroying the previous contents on a partial write should write to
    /// a temporary path and rename.
    pub fn write(&self, path: impl AsRef<Path>) -> Result<()> {
        let path = path.as_ref();
        std::fs::write(path, self.to_bytes()).map_err(|source| SaveError::Write {
            path: path.display().to_string(),
            source,
        })
    }

    /// The file's raw bytes, with whatever checksum they were parsed with.
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// Where this file's version-dependent blocks are.
    pub fn layout(&self) -> Layout {
        self.layout
    }

    /// The save-format version from the file header.
    pub fn version(&self) -> u16 {
        self.read_u16(layout::VERSION)
    }

    /// The checksum stored in the file.
    pub fn stored_checksum(&self) -> u32 {
        self.read_u32(self.layout.crc())
    }

    /// The checksum the file's current contents imply.
    ///
    /// The game stores the complement of the CRC32 over the body, that is
    /// everything after the version header and before the checksum.
    pub fn computed_checksum(&self) -> u32 {
        let body = &self.bytes[layout::VERSION_LEN..self.layout.crc()];
        !crc32fast::hash(body)
    }

    /// Whether the stored checksum matches the contents.
    pub fn checksum_valid(&self) -> bool {
        self.stored_checksum() == self.computed_checksum()
    }

    // -- journal ----------------------------------------------------------

    /// Whether entry `index` of `category` has been discovered.
    pub fn discovered(&self, category: JournalCategory, index: usize) -> Result<bool> {
        let range = category.range();
        Self::check_index(category.as_str(), index, range.len)?;
        Ok(self.bytes[range.start + index] != 0)
    }

    /// Sets whether entry `index` of `category` has been discovered.
    pub fn set_discovered(
        &mut self,
        category: JournalCategory,
        index: usize,
        value: bool,
    ) -> Result<()> {
        let range = category.range();
        Self::check_index(category.as_str(), index, range.len)?;
        self.bytes[range.start + index] = u8::from(value);
        Ok(())
    }

    /// How many entries of `category` have been discovered.
    pub fn discovered_count(&self, category: JournalCategory) -> usize {
        let range = category.range();
        self.bytes[range.start..range.end()]
            .iter()
            .filter(|b| **b != 0)
            .count()
    }

    /// Times the player has killed each bestiary entry.
    pub fn bestiary_killed(&self) -> Vec<i32> {
        self.read_i32_array(layout::BESTIARY_KILLED)
    }

    /// Times each bestiary entry has killed the player.
    pub fn bestiary_killed_by(&self) -> Vec<i32> {
        self.read_i32_array(layout::BESTIARY_KILLED_BY)
    }

    /// Times the player has killed each person.
    pub fn people_killed(&self) -> Vec<i32> {
        self.read_i32_array(layout::PEOPLE_KILLED)
    }

    /// Times each person has killed the player.
    pub fn people_killed_by(&self) -> Vec<i32> {
        self.read_i32_array(layout::PEOPLE_KILLED_BY)
    }

    /// Times the player has killed entry `index` of `table`.
    pub fn killed(&self, table: KillTable, index: usize) -> Result<i32> {
        Self::check_index(table.as_str(), index, table.count())?;
        Ok(self.read_i32(table.killed_range().start + index * 4))
    }

    /// Sets [`Self::killed`].
    pub fn set_killed(&mut self, table: KillTable, index: usize, value: i32) -> Result<()> {
        Self::check_index(table.as_str(), index, table.count())?;
        self.write_i32(table.killed_range().start + index * 4, value);
        Ok(())
    }

    /// Times entry `index` of `table` has killed the player.
    pub fn killed_by(&self, table: KillTable, index: usize) -> Result<i32> {
        Self::check_index(table.as_str(), index, table.count())?;
        Ok(self.read_i32(table.killed_by_range().start + index * 4))
    }

    /// Sets [`Self::killed_by`].
    pub fn set_killed_by(&mut self, table: KillTable, index: usize, value: i32) -> Result<()> {
        Self::check_index(table.as_str(), index, table.count())?;
        self.write_i32(table.killed_by_range().start + index * 4, value);
        Ok(())
    }

    // -- unlocks ----------------------------------------------------------

    /// Bit mask of unlocked playable characters.
    pub fn character_mask(&self) -> u32 {
        self.read_u32(layout::CHARACTERS)
    }

    /// Replaces the unlocked-character mask.
    pub fn set_character_mask(&mut self, mask: u32) {
        self.write_u32(layout::CHARACTERS, mask);
    }

    /// Whether character `index` (0..20) is unlocked.
    pub fn character_unlocked(&self, index: usize) -> Result<bool> {
        Self::check_index("character", index, data::CHARACTER_COUNT)?;
        Ok(self.character_mask() & (1 << index) != 0)
    }

    /// Locks or unlocks character `index` (0..20).
    pub fn set_character_unlocked(&mut self, index: usize, value: bool) -> Result<()> {
        Self::check_index("character", index, data::CHARACTER_COUNT)?;
        let mask = self.character_mask();
        let bit = 1u32 << index;
        self.set_character_mask(if value { mask | bit } else { mask & !bit });
        Ok(())
    }

    /// How many playable characters are unlocked.
    pub fn characters_unlocked(&self) -> u32 {
        (self.character_mask() & data::CHARACTER_MASK_ALL).count_ones()
    }

    /// Camp tutorial progress, 0..=4.
    pub fn tutorial_state(&self) -> u8 {
        self.bytes[layout::TUTORIAL_STATE]
    }

    /// Sets camp tutorial progress.
    pub fn set_tutorial_state(&mut self, value: u8) {
        self.bytes[layout::TUTORIAL_STATE] = value;
    }

    /// Terra quest / shortcut progress, 0..=10.
    pub fn shortcuts(&self) -> u8 {
        self.bytes[layout::SHORTCUTS]
    }

    /// Sets Terra quest / shortcut progress.
    pub fn set_shortcuts(&mut self, value: u8) {
        self.bytes[layout::SHORTCUTS] = value;
    }

    // -- profile ----------------------------------------------------------

    accessors! {
        /// Total runs started.
        plays / set_plays: i32 @ layout::PLAYS,
        /// Total deaths.
        deaths / set_deaths: i32 @ layout::DEATHS,
        /// Normal-ending wins.
        wins_normal / set_wins_normal: i32 @ layout::WINS_NORMAL,
        /// Hard-ending wins.
        wins_hard / set_wins_hard: i32 @ layout::WINS_HARD,
        /// Cosmic Ocean wins.
        wins_special / set_wins_special: i32 @ layout::WINS_SPECIAL,
        /// Lifetime money collected.
        score_total / set_score_total: i64 @ layout::SCORE_TOTAL,
        /// Best single-run money.
        score_top / set_score_top: i32 @ layout::SCORE_TOP,
        /// Total frames played.
        time_total / set_time_total: i64 @ layout::TIME_TOTAL,
        /// Best completion time in frames.
        time_best / set_time_best: i32 @ layout::TIME_BEST,
        /// Frames spent in the tutorial.
        time_tutorial / set_time_tutorial: i32 @ layout::TIME_TUTORIAL,
        /// Money held at the end of the last run.
        score_last / set_score_last: u32 @ layout::SCORE_LAST,
        /// Length of the last run in frames.
        time_last / set_time_last: u32 @ layout::TIME_LAST,
        /// Deepest world reached; Cosmic Ocean reports as 8.
        deepest_area / set_deepest_area: u8 @ layout::DEEPEST_AREA,
        /// Deepest level within [`SaveFile::deepest_area`].
        deepest_level / set_deepest_level: u8 @ layout::DEEPEST_LEVEL,
        /// World the last run ended in.
        world_last / set_world_last: u8 @ layout::WORLD_LAST,
        /// Level the last run ended in.
        level_last / set_level_last: u8 @ layout::LEVEL_LAST,
        /// Theme the last run ended in.
        theme_last / set_theme_last: u8 @ layout::THEME_LAST,
        /// Beat the game the normal way.
        completed_normal / set_completed_normal: bool @ layout::COMPLETED_NORMAL,
        /// Beat the game without shortcuts.
        completed_ironman / set_completed_ironman: bool @ layout::COMPLETED_IRONMAN,
        /// Beat the hard ending.
        completed_hard / set_completed_hard: bool @ layout::COMPLETED_HARD,
        /// Whether the profile screen has been opened.
        profile_seen / set_profile_seen: bool @ layout::PROFILE_SEEN,
        /// Whether seeded runs are unlocked.
        seeded_unlocked / set_seeded_unlocked: bool @ layout::SEEDED_UNLOCKED,
    }

    /// Deaths per playable character.
    pub fn character_deaths(&self) -> Vec<i32> {
        self.read_i32_array(layout::CHARACTER_DEATHS)
    }

    /// Sets the death count for one playable character.
    pub fn set_character_deaths(&mut self, index: usize, value: i32) -> Result<()> {
        Self::check_index("characters", index, data::CHARACTER_COUNT)?;
        self.write_i32(layout::CHARACTER_DEATHS.start + index * 4, value);
        Ok(())
    }

    /// The date of the last daily challenge played, as the game writes
    /// it: eight ASCII digits, `YYYYMMDD`.
    ///
    /// `None` when the field is empty or holds something that is not a
    /// date, which is what a save that has never played a daily looks
    /// like.
    pub fn last_daily(&self) -> Option<String> {
        let r = layout::LAST_DAILY;
        let raw = &self.bytes[r.start..r.end()];
        if !raw.iter().all(u8::is_ascii_digit) {
            return None;
        }
        let text = std::str::from_utf8(raw).ok()?;
        Some(text.to_owned())
    }

    /// Replaces the date of the last daily challenge played.
    ///
    /// `None` clears the field. A value that is not eight ASCII digits is
    /// refused: the game reads these bytes as a date, and writing
    /// something else there is how you get a save it will not open.
    pub fn set_last_daily(&mut self, value: Option<&str>) -> Result<()> {
        let r = layout::LAST_DAILY;
        match value {
            None => self.bytes[r.start..r.end()].fill(0),
            Some(text) => {
                if text.len() != r.len || !text.bytes().all(|b| b.is_ascii_digit()) {
                    return Err(SaveError::InvalidValue {
                        what: "last daily",
                        detail: "must be eight digits, YYYYMMDD",
                    });
                }
                self.bytes[r.start..r.end()].copy_from_slice(text.as_bytes());
            }
        }
        Ok(())
    }

    /// Rescue counts for Monty, Percy and Poochi.
    pub fn pets_rescued(&self) -> [u8; 3] {
        let r = layout::PETS_RESCUED;
        [
            self.bytes[r.start],
            self.bytes[r.start + 1],
            self.bytes[r.start + 2],
        ]
    }

    /// Sets the rescue counts for Monty, Percy and Poochi.
    pub fn set_pets_rescued(&mut self, value: [u8; 3]) {
        let r = layout::PETS_RESCUED;
        self.bytes[r.start..r.start + 3].copy_from_slice(&value);
    }

    /// Per-theme completion flags, indexed by 1-based theme id.
    pub fn completed_themes(&self) -> Vec<bool> {
        let r = layout::COMPLETED_THEMES;
        self.bytes[r.start..r.end()]
            .iter()
            .map(|b| *b != 0)
            .collect()
    }

    /// Sets one theme's completion flag, by 1-based theme id.
    pub fn set_theme_completed(&mut self, id: usize, value: bool) -> Result<()> {
        let r = layout::COMPLETED_THEMES;
        Self::check_index("themes", id, r.len)?;
        self.bytes[r.start + id] = u8::from(value);
        Ok(())
    }

    /// Deaths in `world` (1..=8) at `level` (1-based).
    ///
    /// Both are numbered the way a player would say them, so `deaths_at(1,
    /// 4)` is the Dwelling's last level and `deaths_at(8, 98)` is deep in
    /// the Cosmic Ocean.
    pub fn deaths_at(&self, world: usize, level: usize) -> Result<u32> {
        let offset = self.deathcount_offset(world, level)?;
        Ok(self.read_u32(offset))
    }

    /// Sets the death count for one world and level.
    pub fn set_deaths_at(&mut self, world: usize, level: usize, value: u32) -> Result<()> {
        let offset = self.deathcount_offset(world, level)?;
        self.write_u32(offset, value);
        Ok(())
    }

    /// Death counts for every level of `world` (1..=8), starting at level 1.
    ///
    /// The row is trimmed, because only a handful of the 255 slots are
    /// ever written and the zeroes would swamp any chart of it. The length
    /// is the world's usual level count, extended if the save records a
    /// death past that. Real saves do: a v26 file has three deaths at 7-5,
    /// one level further than Sunken City is supposed to go. Trimming to
    /// the nominal count would quietly drop them, so the data wins.
    pub fn deaths_in_world(&self, world: usize) -> Result<Vec<u32>> {
        Self::check_world(world)?;
        let nominal = data::WORLD_LEVEL_COUNTS[world - 1];
        let mut levels: Vec<u32> = (1..layout::DEATHCOUNT_COLUMNS)
            .map(|level| self.deaths_at(world, level))
            .collect::<Result<_>>()?;
        let last_death = levels.iter().rposition(|deaths| *deaths > 0);
        let len = match last_death {
            Some(index) => nominal.max(index + 1),
            None => nominal,
        };
        levels.truncate(len);
        Ok(levels)
    }

    /// Total deaths in `world` (1..=8), across every level of it.
    pub fn deaths_in_world_total(&self, world: usize) -> Result<u32> {
        Ok(self.deaths_in_world(world)?.iter().sum())
    }

    /// Sum of the whole death histogram.
    ///
    /// This should equal [`SaveFile::deaths`]. It is worth comparing the
    /// two when validating a save: they are written independently by the
    /// game, so a mismatch means something has edited one and not the
    /// other.
    pub fn deathcount_total(&self) -> u64 {
        let r = layout::DEATHCOUNT_PER_LEVEL;
        (0..r.count32())
            .map(|i| u64::from(self.read_u32(r.start + i * 4)))
            .sum()
    }

    /// Levels are 1-based, and column 0 of each row is unused because
    /// there is no level 0.
    fn deathcount_offset(&self, world: usize, level: usize) -> Result<usize> {
        Self::check_world(world)?;
        if level == 0 || level >= layout::DEATHCOUNT_COLUMNS {
            return Err(SaveError::IndexOutOfRange {
                what: "level",
                index: level,
                count: layout::DEATHCOUNT_COLUMNS,
            });
        }
        Ok(layout::DEATHCOUNT_PER_LEVEL.start
            + ((world - 1) * layout::DEATHCOUNT_COLUMNS + level) * 4)
    }

    /// Worlds are 1-based everywhere in this API, so the check has to
    /// reject 0 as well as anything past the last row.
    fn check_world(world: usize) -> Result<()> {
        if world == 0 || world > layout::DEATHCOUNT_WORLD_COUNT {
            return Err(SaveError::IndexOutOfRange {
                what: "world",
                index: world,
                count: layout::DEATHCOUNT_WORLD_COUNT + 1,
            });
        }
        Ok(())
    }

    // -- camp -------------------------------------------------------------

    /// Entity type of each camp sticker.
    pub fn stickers(&self) -> Vec<u32> {
        self.read_u32_array(layout::STICKERS)
    }

    /// Replaces the camp stickers.
    ///
    /// Takes up to twenty entity types and zero-fills the rest, since the
    /// game reads a zero as an empty slot.
    pub fn set_stickers(&mut self, values: &[u32]) -> Result<()> {
        let r = layout::STICKERS;
        if values.len() > r.count32() {
            return Err(SaveError::InvalidValue {
                what: "stickers",
                detail: "at most twenty",
            });
        }
        for slot in 0..r.count32() {
            self.write_u32(r.start + slot * 4, values.get(slot).copied().unwrap_or(0));
        }
        Ok(())
    }

    /// Character index chosen for each of the four player slots.
    pub fn players(&self) -> [u8; 4] {
        let r = layout::PLAYERS;
        [
            self.bytes[r.start],
            self.bytes[r.start + 1],
            self.bytes[r.start + 2],
            self.bytes[r.start + 3],
        ]
    }

    /// Sets the character chosen for each of the four player slots.
    pub fn set_players(&mut self, value: [u8; 4]) -> Result<()> {
        if let Some(bad) = value
            .iter()
            .copied()
            .find(|index| usize::from(*index) >= data::CHARACTER_COUNT)
        {
            return Err(SaveError::IndexOutOfRange {
                what: "players",
                index: usize::from(bad),
                count: data::CHARACTER_COUNT,
            });
        }
        let r = layout::PLAYERS;
        self.bytes[r.start..r.start + 4].copy_from_slice(&value);
        Ok(())
    }

    // -- primitives -------------------------------------------------------
    //
    // Every fixed offset above was bounds-checked when the layout was
    // derived at parse time, so these can index directly. The array
    // helpers stay private for the same reason: they trust their range.

    fn read_u16(&self, at: usize) -> u16 {
        u16::from_le_bytes(self.bytes[at..at + 2].try_into().expect("2 bytes"))
    }

    pub(crate) fn read_u32(&self, at: usize) -> u32 {
        u32::from_le_bytes(self.bytes[at..at + 4].try_into().expect("4 bytes"))
    }

    pub(crate) fn write_u32(&mut self, at: usize, value: u32) {
        self.bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
    }

    pub(crate) fn read_i32(&self, at: usize) -> i32 {
        self.read_u32(at) as i32
    }

    pub(crate) fn write_i32(&mut self, at: usize, value: i32) {
        self.write_u32(at, value as u32);
    }

    pub(crate) fn read_i64(&self, at: usize) -> i64 {
        i64::from_le_bytes(self.bytes[at..at + 8].try_into().expect("8 bytes"))
    }

    pub(crate) fn write_i64(&mut self, at: usize, value: i64) {
        self.bytes[at..at + 8].copy_from_slice(&value.to_le_bytes());
    }

    pub(crate) fn read_f32(&self, at: usize) -> f32 {
        f32::from_le_bytes(self.bytes[at..at + 4].try_into().expect("4 bytes"))
    }

    pub(crate) fn write_f32(&mut self, at: usize, value: f32) {
        self.bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
    }

    pub(crate) fn read_u8(&self, at: usize) -> u8 {
        self.bytes[at]
    }

    pub(crate) fn write_u8(&mut self, at: usize, value: u8) {
        self.bytes[at] = value;
    }

    pub(crate) fn read_bool(&self, at: usize) -> bool {
        self.bytes[at] != 0
    }

    pub(crate) fn write_bool(&mut self, at: usize, value: bool) {
        self.bytes[at] = u8::from(value);
    }

    fn read_i32_array(&self, range: layout::Range) -> Vec<i32> {
        (0..range.count32())
            .map(|i| self.read_i32(range.start + i * 4))
            .collect()
    }

    fn read_u32_array(&self, range: layout::Range) -> Vec<u32> {
        (0..range.count32())
            .map(|i| self.read_u32(range.start + i * 4))
            .collect()
    }

    fn check_index(what: &'static str, index: usize, count: usize) -> Result<()> {
        if index >= count {
            return Err(SaveError::IndexOutOfRange { what, index, count });
        }
        Ok(())
    }
}

/// Frames per second the game runs at, for turning stored frame counts into
/// wall-clock time.
pub const FRAMES_PER_SECOND: f64 = 60.0;

/// Converts a stored frame count to milliseconds.
pub fn frames_to_millis(frames: i64) -> i64 {
    (frames as f64 * 1000.0 / FRAMES_PER_SECOND).round() as i64
}

/// Converts milliseconds to a frame count, the way the game stores times.
pub fn millis_to_frames(millis: i64) -> i64 {
    (millis as f64 * FRAMES_PER_SECOND / 1000.0) as i64
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    /// Builds an all-zero save of a given size with a valid header and
    /// checksum, for tests that only care about one field.
    ///
    /// Real saves cannot be committed: they are personal files, and the
    /// interesting ones are large. A synthetic buffer exercises the same
    /// offsets, and `tests/real_saves.rs` covers real files when someone
    /// points it at a directory of them.
    pub(crate) fn blank_save(len: usize, version: u16) -> SaveFile {
        let mut bytes = vec![0u8; len];
        bytes[0..2].copy_from_slice(&version.to_le_bytes());
        let mut save = SaveFile::parse_unchecked(bytes).expect("blank save should parse");
        let crc = save.computed_checksum();
        let at = save.layout.crc();
        save.bytes[at..at + 4].copy_from_slice(&crc.to_le_bytes());
        save
    }

    #[test]
    fn blank_saves_are_self_consistent() {
        for (len, version) in [(13726usize, 26u16), (13862, 30)] {
            let save = blank_save(len, version);
            assert!(save.checksum_valid(), "v{version} blank should verify");
            assert_eq!(save.version(), version);
        }
    }

    /// The core invariant of the whole crate: reading a save and writing it
    /// straight back must not change a single byte, including every region
    /// nothing here knows how to decode.
    #[test]
    fn writing_back_an_untouched_save_changes_nothing() {
        let save = blank_save(13862, 30);
        assert_eq!(save.to_bytes(), save.as_bytes());
    }

    /// Editing a field must leave the rest of the file alone. Only the
    /// field's own bytes and the checksum may move.
    #[test]
    fn editing_one_field_touches_only_that_field() {
        let before = blank_save(13862, 30);
        let mut after = before.clone();
        after.set_plays(1234);

        let a = before.to_bytes();
        let b = after.to_bytes();
        let changed: Vec<usize> = (0..a.len()).filter(|i| a[*i] != b[*i]).collect();
        let plays = layout::PLAYS;
        let crc = before.layout().crc();
        for i in &changed {
            assert!(
                (plays..plays + 4).contains(i) || (crc..crc + 4).contains(i),
                "byte {i:#x} changed but is neither the field nor the checksum"
            );
        }
        assert_eq!(after.plays(), 1234);
    }

    /// The two kill tables are parallel to their journal categories, so
    /// an index that is valid for one is valid for the other, and the
    /// last entry must be reachable.
    #[test]
    fn kill_counts_round_trip_at_both_ends() {
        let mut save = blank_save(13862, 30);
        for table in KillTable::ALL {
            let last = table.count() - 1;
            save.set_killed(table, 0, 7).unwrap();
            save.set_killed(table, last, 9).unwrap();
            save.set_killed_by(table, 0, 11).unwrap();
            save.set_killed_by(table, last, 13).unwrap();

            assert_eq!(save.killed(table, 0).unwrap(), 7);
            assert_eq!(save.killed(table, last).unwrap(), 9);
            assert_eq!(save.killed_by(table, 0).unwrap(), 11);
            assert_eq!(save.killed_by(table, last).unwrap(), 13);
            assert!(save.killed(table, table.count()).is_err());
            assert!(save.set_killed(table, table.count(), 1).is_err());
        }
    }

    /// Killed and killed-by are separate arrays. Writing one must not be
    /// visible in the other, which is the failure a wrong offset gives.
    #[test]
    fn the_two_kill_directions_do_not_overlap() {
        let mut save = blank_save(13862, 30);
        save.set_killed(KillTable::Bestiary, 5, 100).unwrap();
        assert_eq!(save.killed_by(KillTable::Bestiary, 5).unwrap(), 0);
        assert_eq!(save.killed(KillTable::People, 5).unwrap(), 0);
        assert_eq!(save.killed_by(KillTable::People, 5).unwrap(), 0);
    }

    #[test]
    fn character_deaths_round_trip() {
        let mut save = blank_save(13862, 30);
        save.set_character_deaths(0, 42).unwrap();
        save.set_character_deaths(data::CHARACTER_COUNT - 1, 7)
            .unwrap();
        let deaths = save.character_deaths();
        assert_eq!(deaths[0], 42);
        assert_eq!(deaths[data::CHARACTER_COUNT - 1], 7);
        assert!(save.set_character_deaths(data::CHARACTER_COUNT, 1).is_err());
    }

    #[test]
    fn pets_and_themes_round_trip() {
        let mut save = blank_save(13862, 30);
        save.set_pets_rescued([3, 0, 9]);
        assert_eq!(save.pets_rescued(), [3, 0, 9]);

        save.set_theme_completed(10, true).unwrap();
        assert!(save.completed_themes()[10]);
        assert!(!save.completed_themes()[9]);
        assert!(save.set_theme_completed(20, true).is_err());
    }

    /// The game reads these eight bytes as a date. Writing anything else
    /// there is how you get a save it will not open, so the setter
    /// refuses rather than trusting its caller.
    #[test]
    fn last_daily_only_accepts_a_date() {
        let mut save = blank_save(13862, 30);
        save.set_last_daily(Some("20260128")).unwrap();
        assert_eq!(save.last_daily().as_deref(), Some("20260128"));

        assert!(save.set_last_daily(Some("2026-01-28")).is_err());
        assert!(save.set_last_daily(Some("2026012")).is_err());
        assert!(save.set_last_daily(Some("not a date")).is_err());
        // The refusals left the good value alone.
        assert_eq!(save.last_daily().as_deref(), Some("20260128"));

        save.set_last_daily(None).unwrap();
        assert_eq!(save.last_daily(), None);
    }

    /// A short list clears the slots it does not fill: the game reads a
    /// zero as "no sticker", so leaving the old tail behind would show
    /// stickers the run did not have.
    #[test]
    fn setting_stickers_clears_the_rest() {
        let mut save = blank_save(13862, 30);
        save.set_stickers(&[199, 539, 541, 543]).unwrap();
        assert_eq!(&save.stickers()[..4], &[199, 539, 541, 543]);
        assert!(save.stickers()[4..].iter().all(|id| *id == 0));

        save.set_stickers(&[211]).unwrap();
        assert_eq!(save.stickers()[0], 211);
        assert!(save.stickers()[1..].iter().all(|id| *id == 0));

        assert!(save.set_stickers(&[1; 21]).is_err());
    }

    /// Writing a full set of stickers must stop at the end of the array.
    ///
    /// The 40 bytes after it are not modelled here, and Overlunky reads
    /// the first of them as the wall-spacing mask. Running past the array
    /// would overwrite it.
    #[test]
    fn stickers_stay_inside_their_array() {
        let mut save = blank_save(13862, 30);
        // Mark the unmodelled bytes between the stickers and the angles.
        let gap = layout::STICKERS.end()..layout::STICKER_ANGLES.start;
        assert_eq!(gap.len(), 40, "the gap this test exists to protect");
        let sentinel: Vec<u8> = (0..gap.len()).map(|i| (i as u8) | 0x80).collect();
        save.bytes[gap.clone()].copy_from_slice(&sentinel);

        save.set_stickers(&[7; 20]).unwrap();

        assert_eq!(save.stickers(), vec![7; 20]);
        assert_eq!(
            &save.bytes[gap],
            &sentinel[..],
            "writing a full set of stickers ran past the array"
        );
        // And twenty is the limit.
        assert!(save.set_stickers(&[1; 21]).is_err());
    }

    #[test]
    fn players_round_trip_and_reject_unknown_characters() {
        let mut save = blank_save(13862, 30);
        save.set_players([5, 14, 16, 6]).unwrap();
        assert_eq!(save.players(), [5, 14, 16, 6]);

        assert!(save.set_players([0, 0, 0, 20]).is_err());
        // The refusal was total: nothing was half-written.
        assert_eq!(save.players(), [5, 14, 16, 6]);
    }

    #[test]
    fn checksum_is_recomputed_on_write() {
        let mut save = blank_save(13862, 30);
        save.set_deaths(99);
        // The in-memory buffer still holds the old checksum...
        assert!(!save.checksum_valid());
        // ...and serializing fixes it.
        let round_tripped = SaveFile::parse(save.to_bytes()).expect("should verify");
        assert_eq!(round_tripped.deaths(), 99);
    }

    #[test]
    fn rejects_a_bad_checksum() {
        let mut bytes = blank_save(13862, 30).to_bytes();
        bytes[layout::PLAYS] ^= 0xff;
        let err = SaveFile::parse(bytes.clone()).unwrap_err();
        assert!(matches!(err, SaveError::ChecksumMismatch { .. }));
        // The lenient path still gets you in, which is how a corrupted
        // save can be inspected before being replaced.
        assert!(SaveFile::parse_unchecked(bytes).is_ok());
    }

    #[test]
    fn rejects_files_that_are_not_saves() {
        assert!(matches!(
            SaveFile::parse(b"not a save".to_vec()).unwrap_err(),
            SaveError::TooShort { .. }
        ));
    }

    #[test]
    fn journal_flags_round_trip() {
        let mut save = blank_save(13862, 30);
        for category in JournalCategory::ALL {
            assert_eq!(save.discovered_count(category), 0);
            save.set_discovered(category, 0, true).unwrap();
            save.set_discovered(category, category.count() - 1, true)
                .unwrap();
            assert!(save.discovered(category, 0).unwrap());
            assert_eq!(save.discovered_count(category), 2);
            assert!(
                save.set_discovered(category, category.count(), true)
                    .is_err()
            );
        }
    }

    /// Each category's flags must not spill into the next one's, which a
    /// wrong length in the offset table would cause.
    #[test]
    fn journal_categories_do_not_bleed_into_each_other() {
        let mut save = blank_save(13862, 30);
        save.set_discovered(JournalCategory::Places, 15, true)
            .unwrap();
        assert_eq!(save.discovered_count(JournalCategory::Bestiary), 0);

        save.set_discovered(JournalCategory::Traps, 0, true)
            .unwrap();
        assert_eq!(save.discovered_count(JournalCategory::Items), 0);
    }

    #[test]
    fn character_unlocks_round_trip() {
        let mut save = blank_save(13862, 30);
        assert_eq!(save.characters_unlocked(), 0);
        save.set_character_unlocked(0, true).unwrap();
        save.set_character_unlocked(19, true).unwrap();
        assert!(save.character_unlocked(19).unwrap());
        assert_eq!(save.characters_unlocked(), 2);
        assert_eq!(save.character_mask(), 0b1000_0000_0000_0000_0001);

        save.set_character_unlocked(0, false).unwrap();
        assert_eq!(save.characters_unlocked(), 1);
        assert!(save.set_character_unlocked(20, true).is_err());
    }

    /// Only the low 20 bits are characters, so junk in the high bits must
    /// not inflate the count.
    #[test]
    fn character_count_ignores_the_high_bits() {
        let mut save = blank_save(13862, 30);
        save.set_character_mask(0xffff_ffff);
        assert_eq!(save.characters_unlocked(), 20);
    }

    #[test]
    fn death_histogram_uses_player_facing_numbering() {
        let mut save = blank_save(13862, 30);
        save.set_deaths_at(1, 4, 7).unwrap();
        assert_eq!(save.deaths_at(1, 4).unwrap(), 7);
        assert_eq!(save.deaths_in_world(1).unwrap(), vec![0, 0, 0, 7]);
        assert_eq!(save.deaths_in_world_total(1).unwrap(), 7);
        assert_eq!(save.deathcount_total(), 7);

        // The two world-8 entries a real save was checked against: one at
        // the deepest depth it recorded, one deep in the Cosmic Ocean.
        save.set_deaths_at(8, 7, 1).unwrap();
        save.set_deaths_at(8, 98, 1).unwrap();
        assert_eq!(save.deaths_at(8, 7).unwrap(), 1);
        assert_eq!(save.deaths_at(8, 98).unwrap(), 1);
        assert_eq!(save.deathcount_total(), 9);
    }

    /// Level N is stored at column N, with column 0 left unused. Checked
    /// against the raw offset so a stray bias cannot creep back in.
    #[test]
    fn death_histogram_column_is_the_level_number() {
        let mut save = blank_save(13862, 30);
        save.set_deaths_at(1, 1, 42).unwrap();
        let start = layout::DEATHCOUNT_PER_LEVEL.start;
        assert_eq!(save.read_u32(start + 4), 42, "level 1 is column 1");
        assert_eq!(save.read_u32(start), 0, "column 0 is never used");
    }

    #[test]
    fn death_histogram_rejects_bad_coordinates() {
        let save = blank_save(13862, 30);
        assert!(save.deaths_at(0, 1).is_err(), "worlds are 1-based");
        assert!(save.deaths_at(9, 1).is_err());
        assert!(save.deaths_at(1, 0).is_err(), "there is no level 0");
        assert!(save.deaths_at(1, 255).is_err());
        assert!(save.deaths_at(8, 99).is_ok());
    }

    #[test]
    fn worlds_do_not_bleed_into_each_other() {
        let mut save = blank_save(13862, 30);
        save.set_deaths_at(2, 1, 5).unwrap();
        assert_eq!(save.deaths_in_world_total(1).unwrap(), 0);
        assert_eq!(save.deaths_in_world_total(3).unwrap(), 0);
        assert_eq!(save.deaths_in_world_total(2).unwrap(), 5);
    }

    #[test]
    fn frame_conversions_round_trip() {
        assert_eq!(frames_to_millis(60), 1000);
        assert_eq!(millis_to_frames(1000), 60);
        assert_eq!(frames_to_millis(0), 0);
    }

    /// An older save has no trailing block and a smaller arena ruleset, so
    /// the fixed fields have to keep working across both shapes.
    #[test]
    fn old_and_new_layouts_share_the_fixed_fields() {
        for (len, version) in [(13726usize, 26u16), (13862, 30)] {
            let mut save = blank_save(len, version);
            save.set_plays(5);
            save.set_deaths_at(3, 1, 2).unwrap();
            save.set_discovered(JournalCategory::Bestiary, 77, true)
                .unwrap();
            assert_eq!(save.plays(), 5);
            assert_eq!(save.deaths_at(3, 1).unwrap(), 2);
            assert_eq!(save.discovered_count(JournalCategory::Bestiary), 1);
            assert!(save.layout().has_constellation());
        }
    }

    /// A tail this build does not recognize must not stop the rest of the
    /// save from being read, and must refuse constellation writes.
    #[test]
    fn unknown_tail_still_reads_the_rest() {
        let mut save = blank_save(13862 + 8, 31);
        assert!(!save.layout().has_constellation());
        save.set_plays(3);
        assert_eq!(save.plays(), 3);
        assert_eq!(save.constellation(), None);
        assert_eq!(save.constellation_star_count(), None);
        assert!(matches!(
            save.set_constellation(&Constellation::default())
                .unwrap_err(),
            SaveError::ConstellationUnavailable { .. }
        ));
    }
}
