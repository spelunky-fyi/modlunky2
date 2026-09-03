//! Byte offsets into `savegame.sav`.
//!
//! # How the file is laid out
//!
//! ```text
//! +--------+------------------------------+--------+
//! | u16    | SaveData                     | u32    |
//! | version| (the game's save struct)     | crc32  |
//! +--------+------------------------------+--------+
//!  0        2                              len - 4
//! ```
//!
//! Every offset in this module is a *file* offset, so it already includes
//! the two-byte version header. That matches how the offsets are usually
//! quoted (the spelunky.fyi web save editor uses the same convention) and
//! means an offset can be used against the file bytes without adjustment.
//!
//! # Versions
//!
//! The leading `u16` is a save-format version, not a game version. Files
//! seen in the wild:
//!
//! | version | file size | arena ruleset | constellation | trailing |
//! | ------- | --------- | ------------- | ------------- | -------- |
//! | 25, 26  | 13726     | 128 bytes     | `0x2AFE`      | none     |
//! | 30      | 13862     | 192 bytes     | `0x2B3E`      | 72 bytes |
//!
//! Everything from the journal arrays through [`PLAYERS`] sits at
//! identical offsets in every version seen, verified field by field
//! against real files. Only the tail moves, and it moved in two places at
//! once: between v26 and v30 the arena ruleset grew by 64 bytes *and* a
//! 72-byte block appeared after the constellation. Those two account for
//! the whole 136-byte difference in file size.
//!
//! That last part is why the constellation cannot be found by measuring
//! back from the end of the file. It is the final field in v26 but not in
//! v30. [`Layout`] identifies the tail by its total size instead, which
//! keeps working for a version number nobody has seen as long as the tail
//! itself is one of the shapes below.
//!
//! # Relationship to Overlunky
//!
//! These offsets were derived from Overlunky's in-memory `SaveData`
//! (`src/game_api/savedata.hpp`) and then checked field by field against
//! real save files. Every fixed field matches it exactly, including the
//! 1022-byte gap ahead of [`DEATHCOUNT_PER_LEVEL`] and the 192-byte
//! `SaveGameArenaRuleset`, which is the v30 arena block.
//!
//! The tail is where the file and that struct part company. Saves before
//! v30 store the arena ruleset in 128 bytes rather than 192, so the arena
//! config arrays grew as the game added items, and v30 has 72 bytes after
//! the constellation that the struct does not mention at all. Those 72
//! bytes have stayed zero through everything tried so far, including a
//! full arena session and a Cosmic Ocean completion.

/// Save-format version, the first field in the file.
pub const VERSION: usize = 0x0000;

// ---------------------------------------------------------------------------
// Journal discovery flags. One byte per entry, 0 or 1.
// ---------------------------------------------------------------------------

/// Discovery flags for the 16 journal places.
pub const PLACES: Range = Range::new(0x0002, 16);
/// Discovery flags for the 78 bestiary entries.
pub const BESTIARY: Range = Range::new(0x0012, 78);
/// Discovery flags for the 38 people entries. The first 20 are the playable
/// characters; the rest are NPCs.
pub const PEOPLE: Range = Range::new(0x0060, 38);
/// Discovery flags for the 54 journal items.
pub const ITEMS: Range = Range::new(0x0086, 54);
/// Discovery flags for the 24 journal traps.
pub const TRAPS: Range = Range::new(0x00BC, 24);

/// Frames spent in the tutorial.
pub const TIME_TUTORIAL: usize = 0x00D6;
/// Date string for the last daily challenge played, 8 bytes.
pub const LAST_DAILY: Range = Range::new(0x00DA, 8);
/// The next N times a "journal entry added" popup shows, it lingers for 300
/// frames instead of 180.
pub const SHOW_LONGER_JOURNAL_POPUP_COUNT: usize = 0x00E2;

/// 20-bit mask of unlocked playable characters, bit N for character N.
pub const CHARACTERS: usize = 0x00E6;
/// Camp tutorial progress, 0..=4. Changes the camp layout, camera and
/// lighting: 0 nothing, 1 journal got, 2 key spawned, 3 door unlocked,
/// 4 complete.
pub const TUTORIAL_STATE: usize = 0x00EA;
/// Terra quest / shortcut progress, 0..=10.
pub const SHORTCUTS: usize = 0x00EB;

// ---------------------------------------------------------------------------
// Kill counters. i32 each, parallel to the discovery arrays above.
// ---------------------------------------------------------------------------

/// Times the player has killed each bestiary entry.
///
/// Base and stride confirmed by a short Dwelling run: the only counters
/// that moved were entries 0, 1 and 2, which are Snake, Spider and Bat.
pub const BESTIARY_KILLED: Range = Range::new(0x00EE, 78 * 4);
/// Times each bestiary entry has killed the player.
pub const BESTIARY_KILLED_BY: Range = Range::new(0x0226, 78 * 4);
/// Times the player has killed each person.
pub const PEOPLE_KILLED: Range = Range::new(0x035E, 38 * 4);
/// Times each person has killed the player.
pub const PEOPLE_KILLED_BY: Range = Range::new(0x03F6, 38 * 4);

// ---------------------------------------------------------------------------
// Player profile.
// ---------------------------------------------------------------------------

/// Total runs started.
pub const PLAYS: usize = 0x048E;
/// Total deaths. Equals the sum of [`DEATHCOUNT_PER_LEVEL`].
pub const DEATHS: usize = 0x0492;
/// Normal-ending wins (Olmec / Tiamat).
pub const WINS_NORMAL: usize = 0x0496;
/// Hard-ending wins (Hundun).
pub const WINS_HARD: usize = 0x049A;
/// Special-ending wins (Cosmic Ocean).
pub const WINS_SPECIAL: usize = 0x049E;
/// Lifetime money collected, i64.
pub const SCORE_TOTAL: usize = 0x04A2;
/// Best single-run money, i32.
pub const SCORE_TOP: usize = 0x04AA;
/// Deepest world reached.
///
/// The Cosmic Ocean is stored as world 8 but the game *displays* it as
/// world 7: a save reading 8-99 here shows up as "7-99" on the profile
/// screen. The same goes for the last-run world and for row 7 of the
/// death histogram.
///
/// This crate reports what the file says, and leaves the translation to
/// whatever is displaying it. Normalizing here would mean a value read as
/// 7 and written back as 7 lands in the wrong world, which is exactly the
/// kind of quiet corruption a save editor must not have.
pub const DEEPEST_AREA: usize = 0x04AE;
/// Deepest level within [`DEEPEST_AREA`].
pub const DEEPEST_LEVEL: usize = 0x04AF;

/// Deaths broken down by world and level: 8 worlds of 255 `u32` slots
/// each, at `(world - 1) * 255 + level`.
///
/// This is the most interesting statistic in the file. It is a per-level
/// death histogram, and the game never shows it to you anywhere.
///
/// Rows are worlds, not themes. Row 0 is world 1 and row 7 is the Cosmic
/// Ocean, so world 2 lumps Jungle and Volcana together and nothing in the
/// file says which branch a death happened in. Columns are level numbers
/// as a player would say them, and column 0 is unused because there is no
/// level 0.
///
/// Two independent checks against real saves fix the position of this
/// block. Summing it gives exactly the [`DEATHS`] counter, and in a save
/// whose [`DEEPEST_AREA`] / [`DEEPEST_LEVEL`] read 8-7 the world-8 row has
/// entries at column 7 and column 98, the latter being a Cosmic Ocean
/// death near the end of the run.
pub const DEATHCOUNT_PER_LEVEL: Range = Range::new(0x08AE, 8 * 255 * 4);
/// Number of world rows in [`DEATHCOUNT_PER_LEVEL`].
pub const DEATHCOUNT_WORLD_COUNT: usize = 8;
/// Column slots per world in [`DEATHCOUNT_PER_LEVEL`], so the highest
/// addressable level is one less than this.
pub const DEATHCOUNT_COLUMNS: usize = 255;

/// Total frames played across every run, i64.
pub const TIME_TOTAL: usize = 0x288E;
/// Best completion time in frames, i32.
pub const TIME_BEST: usize = 0x2896;
/// Deaths per playable character, 20 x i32.
pub const CHARACTER_DEATHS: Range = Range::new(0x289A, 20 * 4);
/// Rescue counts for Monty, Percy and Poochi, one byte each.
///
/// The order is confirmed: rescuing a single Monty and diffing moved
/// byte 0 from 199 to 200 and left the other two alone. The game shows
/// these nowhere, so a diff was the only way to check them.
pub const PETS_RESCUED: Range = Range::new(0x28EA, 3);
/// Per-theme completion flags, indexed by 1-based theme id (so slot 0 is
/// unused and slot 19 is the "unknown" theme).
pub const COMPLETED_THEMES: Range = Range::new(0x28ED, 20);

/// Beat the game the normal way.
pub const COMPLETED_NORMAL: usize = 0x2901;
/// Beat the game without using shortcuts.
pub const COMPLETED_IRONMAN: usize = 0x2902;
/// Beat the hard ending.
pub const COMPLETED_HARD: usize = 0x2903;
/// Whether the profile screen has been opened.
pub const PROFILE_SEEN: usize = 0x2904;
/// Whether seeded runs are unlocked.
pub const SEEDED_UNLOCKED: usize = 0x2905;

// ---------------------------------------------------------------------------
// Last game played.
// ---------------------------------------------------------------------------

/// World the last run ended in.
pub const WORLD_LAST: usize = 0x2906;
/// Level the last run ended in.
pub const LEVEL_LAST: usize = 0x2907;
/// Theme the last run ended in.
pub const THEME_LAST: usize = 0x2908;
/// Money held at the end of the last run, u32.
pub const SCORE_LAST: usize = 0x290A;
/// Length of the last run in frames, u32.
pub const TIME_LAST: usize = 0x290E;

// ---------------------------------------------------------------------------
// Camp stickers. Entity types plus their placement on the wall.
//
// Each of the three arrays is followed by 40 bytes this build does not
// model, which is why they sit 120 bytes apart rather than 80. Those
// bytes could equally be ten more elements per array - the strides would
// look identical either way - but Overlunky reads the first of them as a
// mask controlling how the stickers are spaced on the wall.
//
// Twenty is taken as the count because that reading is the safer one. If
// the arrays really hold twenty, writing thirty would zero that mask; if
// they hold thirty, the extra ten are slots the game never fills. Every
// real save has them empty, and collecting every sticker in game yields
// fewer than twenty, so the difference has never been observable.
// `stickers_stay_inside_their_array` pins the boundary.
// ---------------------------------------------------------------------------

/// Entity type of each of the 20 camp stickers, u32 each.
pub const STICKERS: Range = Range::new(0x2912, 20 * 4);
/// Rotation of each sticker in radians, f32 each.
pub const STICKER_ANGLES: Range = Range::new(0x298A, 20 * 4);
/// Vertical offset of each sticker, f32 each.
pub const STICKER_VERT_OFFSETS: Range = Range::new(0x2A02, 20 * 4);
/// Character index chosen for each of the four player slots.
pub const PLAYERS: Range = Range::new(0x2A7A, 4);

/// Start of the arena favorite ruleset. Its length is version dependent,
/// so it is the one block that has to be measured rather than declared;
/// see [`Tail::arena_ruleset`].
///
/// In a v30 save it is 192 bytes and matches Overlunky's
/// `SaveGameArenaRuleset` field for field, with nothing left over. That
/// was confirmed by changing every arena setting in game and diffing:
/// 135 of the 192 bytes moved, and each one landed on the field the
/// struct predicts. In order from the start of the block:
///
/// | offset | type      | field                                   |
/// | ------ | --------- | --------------------------------------- |
/// | +0     | `u8` x2   | unknown                                 |
/// | +2     | `u8`      | timer                                   |
/// | +3     | `u8`      | timer_ending                            |
/// | +4     | `u8`      | wins                                    |
/// | +5     | `u8`      | lives                                   |
/// | +6     | `u8` x2   | unknown                                 |
/// | +8     | `u16` x4  | unused; copied from the in-memory struct |
/// | +16    | `u8`      | health                                  |
/// | +17    | `u8`      | bombs                                   |
/// | +18    | `u8`      | ropes                                   |
/// | +19    | `u8`      | stun_time                               |
/// | +20    | `u8`      | mount                                   |
/// | +21    | `u8`      | arena_select                            |
/// | +22    | `bool` x40| which arenas are in rotation            |
/// | +62    | `u8`      | dark_level_chance                       |
/// | +63    | `u8`      | crate_frequency                         |
/// | +64    | `bool` x40| items enabled                           |
/// | +104   | `bool` x40| items that appear in crates             |
/// | +144   | `i8`      | held_item, -1 for none                  |
/// | +145   | `i8`      | equipped_backitem, -1 for none          |
/// | +146   | `bool` x40| equipped items                          |
/// | +186   | `u8`      | whip_damage                             |
/// | +187   | `bool`    | final_ghost                             |
/// | +188   | `u8`      | breath_cooldown                         |
/// | +189   | `bool`    | punish_ball                             |
/// | +190   | `u8` x2   | padding; holds stale bytes, leave alone |
///
/// Worth knowing: the game writes these settings to the save but does not
/// appear to read them back into its own arena settings screen, which
/// reverts to defaults. So the block persists reliably even though the
/// game acts as though it does not.
///
/// Nothing here is exposed yet. The offsets are recorded so the editor
/// does not have to rediscover them.
pub const ARENA_RULESET_START: usize = 0x2A7E;
/// Size of the arena ruleset in a v30 save, and the size Overlunky's
/// struct computes to.
pub const ARENA_RULESET_LEN_V30: usize = 192;

// ---------------------------------------------------------------------------
// Constellation. Always the final field before the CRC.
// ---------------------------------------------------------------------------

/// `u8` star count, three unknown bytes, then the star array.
pub const CONSTELLATION_HEADER_LEN: usize = 4;
/// Stars stored, whether or not they are all in use.
pub const CONSTELLATION_MAX_STARS: usize = 45;
/// Size of one [`ConstellationStar`](crate::ConstellationStar) on disk:
/// a `u32` type, eleven `f32`s, two `bool` rings, two padding bytes and a
/// trailing `u32`.
pub const CONSTELLATION_STAR_LEN: usize = 4 + 11 * 4 + 2 + 2 + 4;
/// Lines stored. Only 44 are needed to connect 45 stars; the game reserves
/// room for far more, seemingly so a line can be drawn twice to brighten it.
pub const CONSTELLATION_MAX_LINES: usize = 90;
/// Each line is a pair of zero-based star indices.
pub const CONSTELLATION_LINE_LEN: usize = 2;

/// Total on-disk size of the constellation block: header, stars, `f32`
/// scale, `u8` line count, lines, three padding bytes, `f32` line tint.
pub const CONSTELLATION_LEN: usize = CONSTELLATION_HEADER_LEN
    + CONSTELLATION_MAX_STARS * CONSTELLATION_STAR_LEN
    + 4
    + 1
    + CONSTELLATION_MAX_LINES * CONSTELLATION_LINE_LEN
    + 3
    + 4;

/// Length of the trailing CRC field.
pub const CRC_LEN: usize = 4;
/// Length of the leading version field.
pub const VERSION_LEN: usize = 2;

/// The shapes the region after [`PLAYERS`] is known to take.
///
/// Each entry is `(arena ruleset length, trailing length)`. The
/// constellation sits between the two, so an entry fully describes the
/// tail. Matching on the region's total size rather than on the version
/// number means a save version that never changed its tail still parses,
/// and one that did is rejected instead of being read at the wrong offset.
const KNOWN_TAILS: [(usize, usize); 2] = [
    // v25 and v26: the constellation is the last field in the file.
    (128, 0),
    // v30: the arena ruleset grew by 64 bytes and 72 bytes of something
    // new appeared after the constellation.
    (192, 72),
];

/// Smallest file that can hold everything this module knows how to read.
/// Anything shorter is rejected rather than read out of bounds.
pub const MIN_FILE_LEN: usize = ARENA_RULESET_START + 128 + CONSTELLATION_LEN + CRC_LEN;

/// A contiguous run of bytes at a fixed offset.
///
/// Carrying the length alongside the offset lets callers slice without
/// restating the array sizes, and lets the bounds check happen in one place.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Range {
    /// File offset of the first byte.
    pub start: usize,
    /// Number of bytes.
    pub len: usize,
}

impl Range {
    /// Declares a range. `const` so the offsets above stay compile-time.
    pub const fn new(start: usize, len: usize) -> Self {
        Self { start, len }
    }

    /// One past the last byte.
    pub const fn end(&self) -> usize {
        self.start + self.len
    }

    /// Number of `u32`/`i32`/`f32` elements, for the ranges that hold them.
    pub const fn count32(&self) -> usize {
        self.len / 4
    }
}

/// Where one particular file puts the blocks that move between versions.
///
/// Everything before [`ARENA_RULESET_START`] is at a fixed offset and is
/// always readable. The tail is not, so [`Layout::tail`] is optional: a
/// file whose tail this build does not recognize still parses, and still
/// exposes the journal, the profile and the death histogram. Only the
/// constellation goes missing, which is much better than reading it from
/// the wrong place and writing a corrupted save back.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Layout {
    /// Total file length in bytes.
    pub file_len: usize,
    /// The save-format version from the file header.
    pub version: u16,
    /// The version-dependent tail, if its shape is recognized.
    pub tail: Option<Tail>,
}

/// The part of the file whose layout depends on the save version.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Tail {
    /// The arena favorite ruleset block.
    pub arena_ruleset: Range,
    /// The constellation block.
    pub constellation: Range,
    /// Whatever follows the constellation. Empty before v30; 72 bytes of
    /// undecoded data after it.
    pub trailing: Range,
}

impl Layout {
    /// Derives the layout of a file of `file_len` bytes declaring `version`.
    ///
    /// Returns `None` only when the file is too short to hold the fixed
    /// fields, which is the signal that it is not a save at all. An
    /// unrecognized tail is not fatal; it just leaves [`Layout::tail`]
    /// empty.
    pub fn derive(file_len: usize, version: u16) -> Option<Self> {
        if file_len < MIN_FILE_LEN {
            return None;
        }
        let body_end = file_len - CRC_LEN;
        let region = body_end.checked_sub(ARENA_RULESET_START)?;
        let tail = KNOWN_TAILS
            .iter()
            .find(|(arena, trailing)| arena + CONSTELLATION_LEN + trailing == region)
            .map(|(arena, trailing)| {
                let constellation_start = ARENA_RULESET_START + arena;
                Tail {
                    arena_ruleset: Range::new(ARENA_RULESET_START, *arena),
                    constellation: Range::new(constellation_start, CONSTELLATION_LEN),
                    trailing: Range::new(constellation_start + CONSTELLATION_LEN, *trailing),
                }
            });
        Some(Self {
            file_len,
            version,
            tail,
        })
    }

    /// Offset of the trailing CRC.
    pub const fn crc(&self) -> usize {
        self.file_len - CRC_LEN
    }

    /// Whether this build can locate the constellation in this file.
    pub const fn has_constellation(&self) -> bool {
        self.tail.is_some()
    }

    /// The constellation block, if it could be located.
    pub const fn constellation(&self) -> Option<Range> {
        match self.tail {
            Some(tail) => Some(tail.constellation),
            None => None,
        }
    }
}

impl Tail {
    /// Offset of the `f32` constellation scale, which follows the stars.
    pub const fn constellation_scale(&self) -> usize {
        self.constellation.start
            + CONSTELLATION_HEADER_LEN
            + CONSTELLATION_MAX_STARS * CONSTELLATION_STAR_LEN
    }

    /// Offset of the `u8` line count.
    pub const fn constellation_line_count(&self) -> usize {
        self.constellation_scale() + 4
    }

    /// Offset of the first line pair.
    pub const fn constellation_lines(&self) -> usize {
        self.constellation_line_count() + 1
    }

    /// Offset of the `f32` line tint. Zero draws the usual white lines;
    /// the game raises it toward 1.0 as NPC kills climb, turning the lines
    /// pink and then deep red.
    pub const fn constellation_line_red_intensity(&self) -> usize {
        self.constellation_lines() + CONSTELLATION_MAX_LINES * CONSTELLATION_LINE_LEN + 3
    }

    /// Offset of star `index` within the star array.
    pub const fn constellation_star(&self, index: usize) -> usize {
        self.constellation.start + CONSTELLATION_HEADER_LEN + index * CONSTELLATION_STAR_LEN
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The two file shapes seen in the wild. Both sets of numbers came off
    /// real saves and were confirmed by finding the constellation's
    /// `0xffffff` padding exactly where each layout predicts it.
    #[test]
    fn derives_known_versions() {
        let v26 = Layout::derive(13726, 26).unwrap();
        let tail = v26.tail.expect("v26 tail is known");
        assert_eq!(tail.arena_ruleset.len, 128);
        assert_eq!(tail.constellation.start, 0x2AFE);
        assert_eq!(tail.trailing.len, 0);
        // In v26 the constellation really is the last field.
        assert_eq!(tail.constellation.end(), v26.crc());

        let v30 = Layout::derive(13862, 30).unwrap();
        let tail = v30.tail.expect("v30 tail is known");
        assert_eq!(tail.arena_ruleset.len, 192);
        assert_eq!(tail.constellation.start, 0x2B3E);
        assert_eq!(tail.trailing.len, 72);
        assert_eq!(tail.trailing.end(), v30.crc());
    }

    /// The padding before the line tint is the marker used to confirm each
    /// layout against a real file, so it is worth pinning the offsets it
    /// was found at.
    #[test]
    fn constellation_padding_lands_where_it_was_observed() {
        let v26 = Layout::derive(13726, 26).unwrap().tail.unwrap();
        assert_eq!(v26.constellation_line_red_intensity() - 3, 0x3593);

        let v30 = Layout::derive(13862, 30).unwrap().tail.unwrap();
        assert_eq!(v30.constellation_line_red_intensity() - 3, 0x35D3);
    }

    /// A tail shape this build does not know must not be guessed at. The
    /// rest of the file still has to parse, because everything before the
    /// arena ruleset is at a fixed offset regardless of version.
    #[test]
    fn unknown_tail_shapes_leave_the_constellation_alone() {
        let odd = Layout::derive(13726 + 8, 31).unwrap();
        assert!(odd.tail.is_none());
        assert!(!odd.has_constellation());
        assert_eq!(odd.constellation(), None);
        assert_eq!(odd.crc(), 13726 + 8 - 4);
    }

    #[test]
    fn rejects_short_files() {
        assert!(Layout::derive(0, 26).is_none());
        assert!(Layout::derive(MIN_FILE_LEN - 1, 26).is_none());
        assert!(Layout::derive(MIN_FILE_LEN, 26).is_some());
    }

    #[test]
    fn constellation_block_size() {
        assert_eq!(CONSTELLATION_LEN, 2716);
    }

    /// The one real constellation available to check against had five
    /// stars and four lines at these offsets in a v30 save.
    #[test]
    fn v30_star_offsets() {
        let tail = Layout::derive(13862, 30).unwrap().tail.unwrap();
        assert_eq!(tail.constellation_star(0), 0x2B42);
        assert_eq!(tail.constellation_star(1), 0x2B42 + 56);
        assert_eq!(tail.constellation_scale(), 0x2B42 + 45 * 56);
    }

    #[test]
    fn fixed_ranges_do_not_overlap() {
        let ordered = [
            PLACES,
            BESTIARY,
            PEOPLE,
            ITEMS,
            TRAPS,
            BESTIARY_KILLED,
            BESTIARY_KILLED_BY,
            PEOPLE_KILLED,
            PEOPLE_KILLED_BY,
            DEATHCOUNT_PER_LEVEL,
            CHARACTER_DEATHS,
            PETS_RESCUED,
            COMPLETED_THEMES,
            STICKERS,
            STICKER_ANGLES,
            STICKER_VERT_OFFSETS,
            PLAYERS,
        ];
        for pair in ordered.windows(2) {
            assert!(
                pair[0].end() <= pair[1].start,
                "range at {:#x} overruns the one at {:#x}",
                pair[0].start,
                pair[1].start
            );
        }
        assert!(PLAYERS.end() <= ARENA_RULESET_START);
    }

    /// The death histogram has to end exactly where the next field starts,
    /// which is what fixes the 1022-byte gap ahead of it.
    #[test]
    fn deathcount_block_abuts_time_total() {
        assert_eq!(DEATHCOUNT_PER_LEVEL.end(), TIME_TOTAL);
        assert_eq!(DEATHCOUNT_PER_LEVEL.start, 0x08AE);
    }
}
