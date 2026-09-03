//! A compact, serializable view of a save.
//!
//! Two things want this. Snapshots store one alongside the `.sav` so the
//! stats views can chart a history without reparsing every archived file,
//! and restoring a snapshot compares one against another to work out
//! whether the restore would throw progress away.

use serde::{Deserialize, Serialize};

use crate::{Constellation, JournalCategory, SaveFile, data, frames_to_millis};

/// Deaths in one world, and the per-level breakdown behind the total.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WorldDeaths {
    /// World number, 1..=8.
    pub world: usize,
    /// Display name, for example "Jungle / Volcana".
    pub name: String,
    /// Deaths per level, starting at level 1.
    pub levels: Vec<u32>,
    /// Sum of `levels`.
    ///
    /// Wider than the counters it adds: a save read with
    /// `parse_unchecked` can hold junk that overflows a `u32` sum, which
    /// would panic a debug build and wrap silently in release.
    pub total: u64,
}

/// How far the last run got.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LastRun {
    /// World the run ended in.
    pub world: u8,
    /// Level the run ended in.
    pub level: u8,
    /// Theme id the run ended in.
    pub theme: u8,
    /// Name for `theme`, or "Unknown" if it is out of range.
    pub theme_name: String,
    /// Money held at the end.
    pub score: u32,
    /// Length in frames.
    pub time_frames: u32,
    /// Length in milliseconds.
    pub time_millis: i64,
}

/// How much of one journal category has been found.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JournalProgress {
    /// Category identifier, matching [`JournalCategory::as_str`].
    pub category: String,
    /// Entries discovered.
    pub discovered: usize,
    /// Entries in the category.
    pub total: usize,
}

/// Everything worth knowing about a save without holding the save itself.
///
/// Field names are camelCase over the wire, matching the rest of the app's
/// IPC. It is `Deserialize` as well as `Serialize` because snapshot
/// sidecars are read back to build the stats history.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveSummary {
    /// Save format version from the file header.
    pub version: u16,
    /// Whether the stored checksum matched the contents when this was
    /// taken. A summary of a corrupt save is still useful, so this records
    /// the problem rather than refusing to produce one.
    pub checksum_valid: bool,
    /// Sum of the death histogram. Should equal `deaths`; if it does not,
    /// something has edited one and not the other.
    pub deathcount_total: u64,

    /// Runs started.
    pub plays: i32,
    /// Deaths.
    pub deaths: i32,
    /// Normal-ending wins.
    pub wins_normal: i32,
    /// Hard-ending wins.
    pub wins_hard: i32,
    /// Cosmic Ocean wins.
    pub wins_special: i32,
    /// Lifetime money.
    pub score_total: i64,
    /// Best single-run money.
    pub score_top: i32,
    /// Total time played, in frames.
    pub time_total_frames: i64,
    /// Total time played, in milliseconds.
    pub time_total_millis: i64,
    /// Best completion time in frames, or 0 if there isn't one.
    pub time_best_frames: i32,
    /// Best completion time in milliseconds, or 0 if there isn't one.
    pub time_best_millis: i64,

    /// Deepest world reached.
    pub deepest_area: u8,
    /// Deepest level within that world.
    pub deepest_level: u8,
    /// Playable characters unlocked, out of [`data::CHARACTER_COUNT`].
    pub characters_unlocked: u32,
    /// Terra quest progress, 0..=10.
    pub shortcuts: u8,
    /// Text for `shortcuts`.
    pub shortcuts_label: String,
    /// Beat the game normally.
    pub completed_normal: bool,
    /// Beat the game without shortcuts.
    pub completed_ironman: bool,
    /// Beat the hard ending.
    pub completed_hard: bool,
    /// Whether seeded runs are unlocked.
    pub seeded_unlocked: bool,
    /// Rescue counts for Monty, Percy and Poochi.
    pub pets_rescued: [u8; 3],
    /// Stars in the constellation, or `None` when this build cannot
    /// locate the block in this save version. A save that simply has no
    /// constellation yet reads `Some(0)`.
    pub constellation_stars: Option<u8>,
    /// The constellation itself, when there is one.
    ///
    /// This is the one bulky thing in an otherwise compact summary, and it
    /// is here on purpose. A save holds exactly one constellation, so the
    /// only record of the one you had three months ago is the snapshot
    /// from back then. Pruning drops the `.sav` but keeps the sidecar, so
    /// storing it here is what lets a gallery outlive the saves. A save
    /// with no constellation stores nothing, which is nearly all of them.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub constellation: Option<Constellation>,

    /// Journal completion, one entry per category.
    pub journal: Vec<JournalProgress>,
    /// Total journal entries discovered across every category.
    pub journal_discovered: usize,
    /// Total journal entries that exist.
    pub journal_total: usize,
    /// Deaths per world.
    pub world_deaths: Vec<WorldDeaths>,
    /// Deaths per playable character, in unlock-bit order.
    pub character_deaths: Vec<i32>,
    /// How the last run ended.
    pub last_run: LastRun,
}

impl SaveSummary {
    /// Builds a summary from a save.
    pub fn from_save(save: &SaveFile) -> Self {
        let journal: Vec<JournalProgress> = JournalCategory::ALL
            .iter()
            .map(|category| JournalProgress {
                category: category.as_str().to_owned(),
                discovered: save.discovered_count(*category),
                total: category.count(),
            })
            .collect();
        let journal_discovered = journal.iter().map(|j| j.discovered).sum();
        let journal_total = journal.iter().map(|j| j.total).sum();

        let world_deaths = (1..=data::DEATHCOUNT_WORLDS.len())
            .map(|world| {
                // Safe by construction: the range is exactly the number of
                // world rows the file has.
                let levels = save.deaths_in_world(world).unwrap_or_default();
                WorldDeaths {
                    world,
                    name: data::DEATHCOUNT_WORLDS[world - 1].to_owned(),
                    // Widened: these come from `parse_unchecked` results too, and
                    // a junk file can hold two counters that overflow a u32 sum.
                    total: levels.iter().map(|deaths| u64::from(*deaths)).sum(),
                    levels,
                }
            })
            .collect();

        let theme = save.theme_last();
        let time_total_frames = save.time_total();
        let time_best_frames = save.time_best();

        Self {
            version: save.version(),
            checksum_valid: save.checksum_valid(),
            deathcount_total: save.deathcount_total(),
            plays: save.plays(),
            deaths: save.deaths(),
            wins_normal: save.wins_normal(),
            wins_hard: save.wins_hard(),
            wins_special: save.wins_special(),
            score_total: save.score_total(),
            score_top: save.score_top(),
            time_total_frames,
            time_total_millis: frames_to_millis(time_total_frames),
            time_best_frames,
            time_best_millis: frames_to_millis(i64::from(time_best_frames)),
            deepest_area: save.deepest_area(),
            deepest_level: save.deepest_level(),
            characters_unlocked: save.characters_unlocked(),
            shortcuts: save.shortcuts(),
            shortcuts_label: data::SHORTCUT_STATES
                .get(usize::from(save.shortcuts()))
                .copied()
                .unwrap_or("Unknown")
                .to_owned(),
            completed_normal: save.completed_normal(),
            completed_ironman: save.completed_ironman(),
            completed_hard: save.completed_hard(),
            seeded_unlocked: save.seeded_unlocked(),
            pets_rescued: save.pets_rescued(),
            constellation_stars: save.constellation_star_count(),
            constellation: save.constellation().filter(|c| !c.is_empty()),
            journal,
            journal_discovered,
            journal_total,
            world_deaths,
            character_deaths: save.character_deaths(),
            last_run: LastRun {
                world: save.world_last(),
                level: save.level_last(),
                theme,
                theme_name: data::THEMES
                    .get(usize::from(theme))
                    .copied()
                    .unwrap_or("Unknown")
                    .to_owned(),
                score: save.score_last(),
                time_frames: save.time_last(),
                time_millis: frames_to_millis(i64::from(save.time_last())),
            },
        }
    }

    /// Total deaths across every world, from the histogram.
    pub fn total_world_deaths(&self) -> u64 {
        self.world_deaths.iter().map(|w| w.total).sum()
    }

    /// Compares this summary against `other`, treating `self` as the save
    /// that would be replaced.
    ///
    /// See [`ProgressComparison`] for what the result means.
    pub fn compare(&self, other: &SaveSummary) -> ProgressComparison {
        let mut regressions = Vec::new();
        let mut advances = Vec::new();

        for (label, from, to) in self.monotonic_stats(other) {
            let delta = StatDelta {
                label: label.to_owned(),
                from,
                to,
            };
            if to < from {
                regressions.push(delta);
            } else if to > from {
                advances.push(delta);
            }
        }

        // Best time is the one counter that improves by going down, and
        // zero means "no time yet" rather than "instant", so it cannot go
        // through the loop above.
        let (from, to) = (
            i64::from(self.time_best_frames),
            i64::from(other.time_best_frames),
        );
        let delta = StatDelta {
            label: "Best time".to_owned(),
            from,
            to,
        };
        match (from, to) {
            (0, 0) => {}
            (0, _) => advances.push(delta),
            (_, 0) => regressions.push(delta),
            _ if to < from => advances.push(delta),
            _ if to > from => regressions.push(delta),
            _ => {}
        }

        ProgressComparison {
            regressions,
            advances,
        }
    }

    /// The counters that only ever go up during normal play, so a drop in
    /// any of them means the replacement really is behind.
    ///
    /// Deepest depth is folded into one number so 2-1 compares as deeper
    /// than 1-4 rather than the level being compared on its own.
    fn monotonic_stats(&self, other: &SaveSummary) -> Vec<(&'static str, i64, i64)> {
        let depth = |s: &SaveSummary| i64::from(s.deepest_area) * 100 + i64::from(s.deepest_level);
        vec![
            ("Runs played", self.plays.into(), other.plays.into()),
            ("Deaths", self.deaths.into(), other.deaths.into()),
            (
                "Normal wins",
                self.wins_normal.into(),
                other.wins_normal.into(),
            ),
            ("Hard wins", self.wins_hard.into(), other.wins_hard.into()),
            (
                "Cosmic Ocean wins",
                self.wins_special.into(),
                other.wins_special.into(),
            ),
            ("Total money", self.score_total, other.score_total),
            ("Best money", self.score_top.into(), other.score_top.into()),
            (
                "Time played",
                self.time_total_frames,
                other.time_total_frames,
            ),
            ("Deepest depth", depth(self), depth(other)),
            (
                "Characters unlocked",
                self.characters_unlocked.into(),
                other.characters_unlocked.into(),
            ),
            (
                "Shortcut progress",
                self.shortcuts.into(),
                other.shortcuts.into(),
            ),
            (
                "Journal entries",
                self.journal_discovered as i64,
                other.journal_discovered as i64,
            ),
        ]
    }
}

/// One stat that differs between two saves.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StatDelta {
    /// Human-readable name of the stat.
    pub label: String,
    /// Value in the save being replaced.
    pub from: i64,
    /// Value in the save replacing it.
    pub to: i64,
}

/// What restoring one save over another would do to the numbers.
///
/// The counters this looks at only climb during normal play, so anything
/// in `regressions` is progress the current save has and the replacement
/// does not. That is the signal for warning before a restore, and for
/// offering to back the current save up first.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProgressComparison {
    /// Stats that would go backwards.
    pub regressions: Vec<StatDelta>,
    /// Stats that would go forwards.
    pub advances: Vec<StatDelta>,
}

impl ProgressComparison {
    /// Whether the restore would lose progress.
    pub fn loses_progress(&self) -> bool {
        !self.regressions.is_empty()
    }

    /// Whether the two saves look the same on every stat compared.
    pub fn is_identical(&self) -> bool {
        self.regressions.is_empty() && self.advances.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tests::blank_save;

    fn save_with(plays: i32, deaths: i32, wins: i32) -> SaveFile {
        let mut save = blank_save(13862, 30);
        save.set_plays(plays);
        save.set_deaths(deaths);
        save.set_wins_normal(wins);
        save
    }

    #[test]
    fn summarizes_a_save() {
        let mut save = save_with(10, 4, 1);
        save.set_discovered(JournalCategory::Places, 0, true)
            .unwrap();
        save.set_discovered(JournalCategory::Places, 3, true)
            .unwrap();
        save.set_deaths_at(1, 1, 3).unwrap();
        save.set_deaths_at(3, 1, 1).unwrap();
        save.set_deepest_area(4);
        save.set_deepest_level(2);

        let summary = SaveSummary::from_save(&save);
        assert_eq!(summary.plays, 10);
        assert_eq!(summary.journal_discovered, 2);
        assert_eq!(summary.journal_total, 16 + 78 + 38 + 54 + 24);
        assert_eq!(summary.total_world_deaths(), 4);
        assert_eq!(summary.deathcount_total, 4);
        assert_eq!(summary.world_deaths[0].levels, vec![3, 0, 0, 0]);
        assert_eq!(summary.world_deaths[2].name, "Olmec's Lair");
        assert_eq!(summary.world_deaths[2].levels, vec![1]);
        assert_eq!(summary.deepest_area, 4);
    }

    /// The Cosmic Ocean row is 99 levels long rather than being trimmed to
    /// the handful the player has reached, so charts of it stay stable.
    #[test]
    fn cosmic_ocean_row_is_long() {
        let save = blank_save(13862, 30);
        let summary = SaveSummary::from_save(&save);
        assert_eq!(summary.world_deaths[7].levels.len(), 99);
    }

    #[test]
    fn detects_a_restore_that_loses_progress() {
        let current = SaveSummary::from_save(&save_with(100, 40, 5));
        let older = SaveSummary::from_save(&save_with(60, 20, 5));

        let comparison = current.compare(&older);
        assert!(comparison.loses_progress());
        let labels: Vec<&str> = comparison
            .regressions
            .iter()
            .map(|d| d.label.as_str())
            .collect();
        assert!(labels.contains(&"Runs played"));
        assert!(labels.contains(&"Deaths"));
        assert!(
            !labels.contains(&"Normal wins"),
            "equal stats are not regressions"
        );
    }

    #[test]
    fn a_newer_save_only_advances() {
        let current = SaveSummary::from_save(&save_with(60, 20, 5));
        let newer = SaveSummary::from_save(&save_with(100, 40, 6));

        let comparison = current.compare(&newer);
        assert!(!comparison.loses_progress());
        assert!(!comparison.is_identical());
    }

    #[test]
    fn identical_saves_compare_equal() {
        let summary = SaveSummary::from_save(&save_with(60, 20, 5));
        assert!(summary.compare(&summary.clone()).is_identical());
    }

    /// Best time improves downward, and zero means no time at all, so it
    /// needs the two special cases the other counters do not.
    #[test]
    fn best_time_compares_the_right_way_round() {
        let mut fast = blank_save(13862, 30);
        fast.set_time_best(6000);
        let mut slow = blank_save(13862, 30);
        slow.set_time_best(9000);
        let none = blank_save(13862, 30);

        let fast = SaveSummary::from_save(&fast);
        let slow = SaveSummary::from_save(&slow);
        let none = SaveSummary::from_save(&none);

        assert!(
            fast.compare(&slow).loses_progress(),
            "slower is a regression"
        );
        assert!(
            !slow.compare(&fast).loses_progress(),
            "faster is an advance"
        );
        assert!(
            fast.compare(&none).loses_progress(),
            "losing a time is a regression"
        );
        assert!(
            !none.compare(&fast).loses_progress(),
            "gaining a time is not"
        );
        assert!(none.compare(&none.clone()).is_identical());
    }

    /// Deepest depth has to compare as a depth, not as two numbers, or
    /// 2-1 looks like a regression from 1-4.
    #[test]
    fn deepest_depth_compares_as_one_value() {
        let mut shallow = blank_save(13862, 30);
        shallow.set_deepest_area(1);
        shallow.set_deepest_level(4);
        let mut deep = blank_save(13862, 30);
        deep.set_deepest_area(2);
        deep.set_deepest_level(1);

        let shallow = SaveSummary::from_save(&shallow);
        let deep = SaveSummary::from_save(&deep);
        assert!(!shallow.compare(&deep).loses_progress());
        assert!(deep.compare(&shallow).loses_progress());
    }

    #[test]
    fn round_trips_through_json() {
        let summary = SaveSummary::from_save(&save_with(7, 3, 1));
        let json = serde_json::to_string(&summary).unwrap();
        assert!(json.contains("\"worldDeaths\""), "expected camelCase keys");
        let back: SaveSummary = serde_json::from_str(&json).unwrap();
        assert_eq!(back, summary);
    }
}
