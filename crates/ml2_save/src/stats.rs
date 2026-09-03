//! The full per-entry view of a save.
//!
//! [`SaveSummary`] is deliberately small: it goes in every snapshot
//! sidecar, so it holds totals and nothing else. [`SaveStats`] is the
//! other end of the trade. It names every journal entry, every kill
//! counter and every character, and it is built on demand for whichever
//! save is being looked at.
//!
//! Nothing here is stored. Keeping the per-entry detail out of the
//! sidecars is what lets a year of snapshots stay small enough to keep
//! forever.

use serde::{Deserialize, Serialize};

use crate::{JournalCategory, SaveFile, SaveSummary, data, frames_to_millis};

/// One journal entry, with whatever counters the game keeps for it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EntryStat {
    /// Position in its category, from zero. The journal numbers these
    /// from one when it displays them.
    pub index: usize,
    /// Display name.
    pub name: String,
    /// Whether the journal entry has been unlocked.
    pub discovered: bool,
    /// Times the player has killed this, or `None` for a category the
    /// game keeps no kill counters for.
    pub killed: Option<i32>,
    /// Times this has killed the player, same caveat.
    pub killed_by: Option<i32>,
}

/// One journal category and everything in it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CategoryStats {
    /// Identifier, matching [`JournalCategory::as_str`].
    pub category: String,
    /// Display name.
    pub label: String,
    /// How many entries are discovered.
    pub discovered: usize,
    /// How many entries exist.
    pub total: usize,
    /// Every entry, in journal order.
    pub entries: Vec<EntryStat>,
}

/// One playable character.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CharacterStat {
    /// Position in the unlock mask, from zero.
    pub index: usize,
    /// Display name.
    pub name: String,
    /// Whether the character is unlocked.
    pub unlocked: bool,
    /// How many times this character has died.
    pub deaths: i32,
}

/// One theme, and whether the player has finished it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ThemeStat {
    /// The game's own 1-based theme id.
    pub id: usize,
    pub name: String,
    pub completed: bool,
}

/// Everything the stats views draw from.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveStats {
    /// The totals, the same object stored in snapshot sidecars.
    pub summary: SaveSummary,
    /// Every journal category, in the order the game stores them.
    pub journal: Vec<CategoryStats>,
    /// Every playable character, in unlock-bit order.
    pub characters: Vec<CharacterStat>,
    /// Every theme, and whether it has been completed. The game tracks
    /// this separately from the three ending flags and shows it nowhere.
    pub themes: Vec<ThemeStat>,
    /// The characters in the four player slots, as last chosen.
    pub players: Vec<String>,
    /// Camp tutorial progress, 0..=4.
    pub tutorial_state: u8,
    /// Time spent in the tutorial, milliseconds.
    pub time_tutorial_millis: i64,
    /// Date of the last daily challenge played, `YYYYMMDD`.
    pub last_daily: Option<String>,
    /// Entity types the game shows as stickers on the last-game page:
    /// the character played and what they were carrying. Raw ids, with
    /// the empty slots dropped; naming them needs the entity table,
    /// which is not this crate's business.
    pub stickers: Vec<u32>,
}

impl SaveStats {
    /// Builds the full stats for a save.
    pub fn from_save(save: &SaveFile) -> Self {
        // Read each counter array once rather than per entry.
        let bestiary_killed = save.bestiary_killed();
        let bestiary_killed_by = save.bestiary_killed_by();
        let people_killed = save.people_killed();
        let people_killed_by = save.people_killed_by();
        let character_deaths = save.character_deaths();

        let journal = JournalCategory::ALL
            .iter()
            .map(|category| {
                let (killed, killed_by) = match category {
                    JournalCategory::Bestiary => {
                        (Some(&bestiary_killed), Some(&bestiary_killed_by))
                    }
                    JournalCategory::People => (Some(&people_killed), Some(&people_killed_by)),
                    // The game keeps no kill counters for places, items or
                    // traps, so these stay `None` rather than a
                    // meaningless zero.
                    _ => (None, None),
                };

                let entries = (0..category.count())
                    .map(|index| EntryStat {
                        index,
                        name: data::name(*category, index).unwrap_or("Unknown").to_owned(),
                        discovered: save.discovered(*category, index).unwrap_or(false),
                        killed: killed.and_then(|v| v.get(index).copied()),
                        killed_by: killed_by.and_then(|v| v.get(index).copied()),
                    })
                    .collect();

                CategoryStats {
                    category: category.as_str().to_owned(),
                    label: category.label().to_owned(),
                    discovered: save.discovered_count(*category),
                    total: category.count(),
                    entries,
                }
            })
            .collect();

        let characters = (0..data::CHARACTER_COUNT)
            .map(|index| CharacterStat {
                index,
                name: data::characters()
                    .get(index)
                    .copied()
                    .unwrap_or("Unknown")
                    .to_owned(),
                unlocked: save.character_unlocked(index).unwrap_or(false),
                deaths: character_deaths.get(index).copied().unwrap_or(0),
            })
            .collect();

        // Theme ids are 1-based, and the array's slot 0 and last slot are
        // placeholders rather than themes, so neither is offered.
        let completed = save.completed_themes();
        let themes = (1..data::THEMES.len() - 1)
            .map(|id| ThemeStat {
                id,
                name: data::THEMES[id].to_owned(),
                completed: completed.get(id).copied().unwrap_or(false),
            })
            .collect();

        let players = save
            .players()
            .iter()
            .map(|index| {
                data::characters()
                    .get(usize::from(*index))
                    .copied()
                    .unwrap_or("Unknown")
                    .to_owned()
            })
            .collect();

        Self {
            summary: SaveSummary::from_save(save),
            journal,
            characters,
            themes,
            players,
            tutorial_state: save.tutorial_state(),
            time_tutorial_millis: frames_to_millis(i64::from(save.time_tutorial())),
            last_daily: save.last_daily(),
            stickers: save
                .stickers()
                .into_iter()
                .filter(|entity_type| *entity_type != 0)
                .collect(),
        }
    }

    /// The entries that have killed the player most, across the bestiary
    /// and the people, highest first.
    ///
    /// Both lists are merged because the question "what keeps killing me"
    /// does not care whether the answer is a monster or a shopkeeper, and
    /// splitting them hides the shopkeeper who is quietly top of the list.
    pub fn deadliest(&self, limit: usize) -> Vec<&EntryStat> {
        let mut all: Vec<&EntryStat> = self
            .journal
            .iter()
            .flat_map(|category| category.entries.iter())
            .filter(|entry| entry.killed_by.unwrap_or(0) > 0)
            .collect();
        // Descending by kills, then by name so equal counts stay in a
        // stable order rather than shuffling between reads.
        all.sort_by(|a, b| {
            b.killed_by
                .unwrap_or(0)
                .cmp(&a.killed_by.unwrap_or(0))
                .then_with(|| a.name.cmp(&b.name))
        });
        all.truncate(limit);
        all
    }

    /// The entries the player has killed most, highest first.
    pub fn most_killed(&self, limit: usize) -> Vec<&EntryStat> {
        let mut all: Vec<&EntryStat> = self
            .journal
            .iter()
            .flat_map(|category| category.entries.iter())
            .filter(|entry| entry.killed.unwrap_or(0) > 0)
            .collect();
        all.sort_by(|a, b| {
            b.killed
                .unwrap_or(0)
                .cmp(&a.killed.unwrap_or(0))
                .then_with(|| a.name.cmp(&b.name))
        });
        all.truncate(limit);
        all
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tests::blank_save;

    #[test]
    fn covers_every_entry_of_every_category() {
        let stats = SaveStats::from_save(&blank_save(13862, 30));
        assert_eq!(stats.journal.len(), 5);
        for category in &stats.journal {
            assert_eq!(category.entries.len(), category.total);
            for (i, entry) in category.entries.iter().enumerate() {
                assert_eq!(entry.index, i);
                assert!(!entry.name.is_empty());
            }
        }
        assert_eq!(stats.characters.len(), 20);
        assert_eq!(stats.characters[0].name, "Ana Spelunky");
    }

    /// Themes are the game's own 1-based ids, so the placeholder at
    /// either end of the table must not be offered as something to
    /// complete.
    #[test]
    fn themes_skip_the_placeholders() {
        let stats = SaveStats::from_save(&blank_save(13862, 30));
        assert_eq!(
            stats.themes.first().map(|t| t.name.as_str()),
            Some("Dwelling")
        );
        assert_eq!(
            stats.themes.last().map(|t| t.name.as_str()),
            Some("Arena"),
            "the trailing Unknown slot is not a theme"
        );
        assert!(stats.themes.iter().all(|t| !t.completed));
        assert!(stats.themes.iter().all(|t| t.id >= 1));
    }

    #[test]
    fn reads_the_completed_themes() {
        let mut save = blank_save(13862, 30);
        // Theme 2 is Jungle; the array is indexed by the 1-based id.
        save.write_u8(crate::layout::COMPLETED_THEMES.start + 2, 1);
        let stats = SaveStats::from_save(&save);
        let jungle = stats.themes.iter().find(|t| t.id == 2).unwrap();
        assert_eq!(jungle.name, "Jungle");
        assert!(jungle.completed);
        assert_eq!(stats.themes.iter().filter(|t| t.completed).count(), 1);
    }

    #[test]
    fn names_the_characters_in_the_player_slots() {
        let mut save = blank_save(13862, 30);
        let slots = crate::layout::PLAYERS.start;
        save.write_u8(slots, 0);
        save.write_u8(slots + 1, 5);
        let stats = SaveStats::from_save(&save);
        assert_eq!(stats.players.len(), 4);
        assert_eq!(stats.players[0], "Ana Spelunky");
        assert_eq!(stats.players[1], "Liz Mutton");
    }

    /// A save that has never played a daily has no date to report, and
    /// an empty field is not a date.
    #[test]
    fn last_daily_is_absent_when_unset() {
        let save = blank_save(13862, 30);
        assert_eq!(save.last_daily(), None);
        assert_eq!(SaveStats::from_save(&save).last_daily, None);
    }

    #[test]
    fn last_daily_reads_the_stored_date() {
        let mut save = blank_save(13862, 30);
        for (i, byte) in b"20260128".iter().enumerate() {
            save.write_u8(crate::layout::LAST_DAILY.start + i, *byte);
        }
        assert_eq!(save.last_daily().as_deref(), Some("20260128"));
    }

    /// Only the bestiary and the people have kill counters. The other
    /// three must report `None` rather than a zero that looks like data.
    #[test]
    fn only_the_right_categories_carry_kill_counters() {
        let stats = SaveStats::from_save(&blank_save(13862, 30));
        for category in &stats.journal {
            let has_counters = matches!(category.category.as_str(), "bestiary" | "people");
            for entry in &category.entries {
                assert_eq!(
                    entry.killed.is_some(),
                    has_counters,
                    "{} entry {} kill counter",
                    category.category,
                    entry.index
                );
                assert_eq!(entry.killed_by.is_some(), has_counters);
            }
        }
    }

    #[test]
    fn reads_the_counters_it_is_given() {
        let mut save = blank_save(13862, 30);
        save.set_discovered(JournalCategory::Bestiary, 0, true)
            .unwrap();
        save.set_character_unlocked(3, true).unwrap();

        let stats = SaveStats::from_save(&save);
        let bestiary = &stats.journal[1];
        assert_eq!(bestiary.category, "bestiary");
        assert!(bestiary.entries[0].discovered);
        assert_eq!(bestiary.discovered, 1);
        assert!(stats.characters[3].unlocked);
        assert!(!stats.characters[4].unlocked);
    }

    /// The two leaderboards merge the bestiary and the people, so a
    /// shopkeeper at the top of the list is not hidden behind a category
    /// split.
    #[test]
    fn leaderboards_merge_categories_and_rank_by_count() {
        let mut save = blank_save(13862, 30);
        // Snake (bestiary 0) killed the player twice.
        save.write_i32(crate::layout::BESTIARY_KILLED_BY.start, 2);
        // Shopkeeper-ish (people 20) killed them nine times.
        save.write_i32(crate::layout::PEOPLE_KILLED_BY.start + 20 * 4, 9);

        let stats = SaveStats::from_save(&save);
        let deadliest = stats.deadliest(10);
        assert_eq!(deadliest.len(), 2);
        assert_eq!(deadliest[0].killed_by, Some(9));
        assert_eq!(deadliest[1].name, "Snake");
    }

    #[test]
    fn leaderboards_drop_zeroes_and_respect_the_limit() {
        let mut save = blank_save(13862, 30);
        for i in 0..5 {
            save.write_i32(crate::layout::BESTIARY_KILLED.start + i * 4, (i as i32) + 1);
        }
        let stats = SaveStats::from_save(&save);

        let all = stats.most_killed(100);
        assert_eq!(all.len(), 5, "entries with no kills must not appear");
        assert_eq!(all[0].killed, Some(5));

        assert_eq!(stats.most_killed(2).len(), 2);
        assert!(
            stats.deadliest(10).is_empty(),
            "nothing has killed the player"
        );
    }
}
