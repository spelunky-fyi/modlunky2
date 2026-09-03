//! Reading a save into an editable form, and writing edits back.
//!
//! # Why this is a whole-state edit rather than a patch
//!
//! [`SaveEdits`] carries every editable field, not just the changed ones,
//! and applying it calls every setter. That sounds wasteful and would be
//! dangerous with most designs, but [`SaveFile`] edits the file's bytes in
//! place: writing a field its own value changes nothing. So applying an
//! untouched state is a no-op at the byte level, which
//! `rewriting_every_field_with_its_own_value_changes_no_bytes` asserts
//! against real saves.
//!
//! That property is what makes the editor safe. A save has regions this
//! build does not model - the sticker layout, the arena ruleset, whatever
//! sits in the gaps - and an editor that rebuilt the file from a struct
//! would silently drop all of it. Nothing here can, because nothing here
//! ever builds a file; it only overwrites the bytes it was asked to.
//!
//! # Why a save is archived before it is written
//!
//! Editing the live save is the second destructive operation in this tab,
//! and unlike a restore there is nothing to compare against afterwards: a
//! typo in a counter looks exactly like a real value. So the file is
//! archived first, into the managed library where pruning cannot reach it,
//! and the caller is told what the backup was so it can offer the undo.

use std::collections::HashMap;

use ml2_save::{Constellation, JournalCategory, KillTable, SaveFile, data};
use serde::{Deserialize, Serialize};

use super::stickers;
use super::store::{self, SaveKind, StoredSave};
use super::{err, save_path, write_atomically};

/// Which save the editor is pointed at.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
pub enum SaveRef {
    /// The game's own `savegame.sav`.
    Live,
    /// An archived copy, by id.
    #[serde(rename_all = "camelCase")]
    Stored { id: String },
}

impl SaveRef {
    /// Where this save is on disk.
    fn path(&self) -> Result<std::path::PathBuf, String> {
        match self {
            SaveRef::Live => {
                let path = save_path().ok_or("No Spelunky 2 install directory is configured.")?;
                if !path.exists() {
                    return Err(format!("No save file at {}", path.display()));
                }
                Ok(path)
            }
            SaveRef::Stored { id } => {
                let stored = store::get(id).map_err(|e| err("Could not find that save", e))?;
                if !stored.restorable {
                    return Err(
                        "That snapshot's save file was pruned, so there is nothing to edit.".into(),
                    );
                }
                Ok(std::path::PathBuf::from(stored.path))
            }
        }
    }
}

// -- the editable state ---------------------------------------------------

/// The lifetime counters the game's profile screen is built from.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfileEdit {
    pub plays: i32,
    pub deaths: i32,
    pub wins_normal: i32,
    pub wins_hard: i32,
    pub wins_special: i32,
    /// Lifetime money. Sixty-four bits, so it goes over the wire as a
    /// string: JSON numbers lose precision past 2^53 and this is a field
    /// someone will absolutely try to max out.
    pub score_total: String,
    pub score_top: i32,
    /// Total frames played, as a string for the same reason.
    pub time_total: String,
    pub time_best: i32,
    pub time_tutorial: i32,
    pub deepest_area: u8,
    pub deepest_level: u8,
}

/// The one-off flags and the character roster.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UnlocksEdit {
    pub completed_normal: bool,
    pub completed_ironman: bool,
    pub completed_hard: bool,
    pub profile_seen: bool,
    pub seeded_unlocked: bool,
    /// Terra's quest, 0..=10.
    pub shortcuts: u8,
    /// Camp tutorial progress, 0..=4.
    pub tutorial_state: u8,
}

/// What the last run ended on.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LastRunEdit {
    pub world: u8,
    pub level: u8,
    pub theme: u8,
    pub score: u32,
    pub time: u32,
    /// Entity types of the run's stickers, empty slots dropped.
    pub stickers: Vec<u32>,
}

/// The camp: who is standing in it and what has been rescued.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CampEdit {
    /// Character index per player slot.
    pub players: [u8; 4],
    /// Monty, Percy, Poochi.
    pub pets_rescued: [u8; 3],
    /// `YYYYMMDD`, or absent for a save that has never played a daily.
    pub last_daily: Option<String>,
}

/// One journal entry: whether it is in the book, and its kill counts when
/// the category keeps them.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct JournalEntryEdit {
    pub name: &'static str,
    pub discovered: bool,
    /// Times the player killed it. Absent for places, items and traps,
    /// which the game does not count kills for.
    pub killed: Option<i32>,
    pub killed_by: Option<i32>,
}

/// One journal category and everything in it.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct JournalSectionEdit {
    pub key: &'static str,
    pub label: &'static str,
    /// Whether this category keeps kill counts.
    pub has_kills: bool,
    pub entries: Vec<JournalEntryEdit>,
}

/// One playable character.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CharacterEdit {
    pub name: &'static str,
    pub unlocked: bool,
    pub deaths: i32,
}

/// Deaths in one world, level by level.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorldDeathsEdit {
    /// 1-based world number, as a player would say it.
    pub world: usize,
    pub name: &'static str,
    /// Level number that `levels[0]` refers to. Not always 1; see
    /// [`DEATH_LEVELS`].
    pub first_level: usize,
    /// Deaths at `first_level`, `first_level + 1`, and so on.
    pub levels: Vec<u32>,
}

/// One theme's completion flag.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ThemeEdit {
    pub id: usize,
    pub name: &'static str,
    pub completed: bool,
}

/// Everything the editor can change, plus the labels it needs to draw.
///
/// The names are static tables that never change, so sending them with
/// the values costs a few kilobytes once per open and saves the frontend
/// keeping a duplicate copy of the game's data in sync with this one.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EditableSave {
    pub path: String,
    pub version: u16,
    /// False for a save whose checksum did not verify when it was read.
    /// It is still editable - refusing would leave someone stuck with a
    /// broken save and no tool - but it is worth saying so.
    pub checksum_valid: bool,
    pub profile: ProfileEdit,
    pub unlocks: UnlocksEdit,
    pub last_run: LastRunEdit,
    pub camp: CampEdit,
    pub journal: Vec<JournalSectionEdit>,
    pub characters: Vec<CharacterEdit>,
    pub deaths: Vec<WorldDeathsEdit>,
    pub themes: Vec<ThemeEdit>,
    pub constellation: Option<Constellation>,
    /// Whether this build can locate the constellation in this save at
    /// all. False for an unrecognised version, where writing one would
    /// mean guessing at an offset.
    pub constellation_editable: bool,
    /// Labels for Terra's eleven states, so the picker matches the game.
    pub shortcut_states: Vec<&'static str>,
    /// Names for the entity ids this save's stickers hold.
    ///
    /// Stickers are raw entity types and the table that names them is
    /// three quarters of a megabyte, so it does not go over the wire.
    /// Only the ids actually present are named, which covers reading and
    /// removing; an id typed by hand shows as a number until it is saved.
    /// The frontend resolves playable characters itself, from the
    /// character list it already has.
    pub sticker_names: HashMap<u32, String>,
    /// Entity id of the first playable character, so the frontend can map
    /// a character sticker onto the roster it already holds.
    pub first_character_entity: u32,
}

/// The values to write back. Same shape as [`EditableSave`], without the
/// labels, which are ours rather than the save's.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveEdits {
    pub profile: ProfileEdit,
    pub unlocks: UnlocksEdit,
    pub last_run: LastRunEdit,
    pub camp: CampEdit,
    /// Discovery flags per category, keyed the same way the sections were
    /// sent out.
    pub journal: Vec<JournalSectionValues>,
    pub characters: Vec<CharacterValues>,
    /// Deaths per world, each carrying the level its first entry means.
    pub deaths: Vec<WorldDeathValues>,
    /// Completion flag per 1-based theme id.
    pub themes: Vec<bool>,
    /// Absent leaves whatever chart the save already has alone; a chart
    /// replaces it.
    pub constellation: Option<Constellation>,
}

/// The values for one journal category.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JournalSectionValues {
    pub key: String,
    pub discovered: Vec<bool>,
    /// Empty for a category that keeps no kill counts.
    #[serde(default)]
    pub killed: Vec<i32>,
    #[serde(default)]
    pub killed_by: Vec<i32>,
}

/// The death counts for one world.
///
/// Carries `first_level` rather than letting this side re-derive it: the
/// derivation depends on what the save holds, so zeroing the one count
/// below the floor would shift the floor, and the edits would then land a
/// row off from where they were typed.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WorldDeathValues {
    /// 1-based world number.
    pub world: usize,
    /// Level number that `levels[0]` refers to.
    pub first_level: usize,
    pub levels: Vec<u32>,
}

/// The values for one playable character.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CharacterValues {
    pub unlocked: bool,
    pub deaths: i32,
}

/// What a save turned into.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EditResult {
    /// How many bytes of the file actually changed. Zero means the edits
    /// matched what was already there, which is worth saying plainly
    /// rather than reporting a successful write of nothing.
    pub changed_bytes: usize,
    /// The archived copy of what was overwritten, when one was made.
    pub backup: Option<StoredSave>,
    /// The save as it now stands, so the editor can rebase on it without
    /// a second round trip.
    pub save: Box<EditableSave>,
}

// -- reading --------------------------------------------------------------

impl EditableSave {
    /// Reads a save into its editable form.
    fn from_save(save: &SaveFile, path: String) -> Self {
        let journal = JournalCategory::ALL
            .into_iter()
            .map(|category| {
                let table = KillTable::ALL
                    .into_iter()
                    .find(|table| table.category() == category);
                let entries = (0..category.count())
                    .map(|index| JournalEntryEdit {
                        name: data::name(category, index).unwrap_or("?"),
                        discovered: save.discovered(category, index).unwrap_or(false),
                        killed: table.map(|t| save.killed(t, index).unwrap_or(0)),
                        killed_by: table.map(|t| save.killed_by(t, index).unwrap_or(0)),
                    })
                    .collect();
                JournalSectionEdit {
                    key: category.as_str(),
                    label: category.label(),
                    has_kills: table.is_some(),
                    entries,
                }
            })
            .collect();

        let character_deaths = save.character_deaths();
        let characters = data::characters()
            .iter()
            .enumerate()
            .map(|(index, name)| CharacterEdit {
                name,
                unlocked: save.character_unlocked(index).unwrap_or(false),
                deaths: character_deaths.get(index).copied().unwrap_or(0),
            })
            .collect();

        // Only the levels a death can land on. The file has room for 255
        // per world and the game uses a handful, so sending the whole
        // block would be mostly zeroes, a grid nobody can read, and an
        // invitation to put deaths on levels that cannot happen.
        let deaths = (1..=8)
            .map(|world| {
                let (first_level, last_level) = death_level_range(save, world);
                WorldDeathsEdit {
                    world,
                    name: data::DEATHCOUNT_WORLDS[world - 1],
                    first_level,
                    levels: (first_level..=last_level)
                        .map(|level| save.deaths_at(world, level).unwrap_or(0))
                        .collect(),
                }
            })
            .collect();

        let completed = save.completed_themes();
        let themes = (1..data::THEMES.len())
            .map(|id| ThemeEdit {
                id,
                name: data::THEMES[id],
                completed: completed.get(id).copied().unwrap_or(false),
            })
            .collect();

        Self {
            path,
            version: save.version(),
            checksum_valid: save.checksum_valid(),
            profile: ProfileEdit {
                plays: save.plays(),
                deaths: save.deaths(),
                wins_normal: save.wins_normal(),
                wins_hard: save.wins_hard(),
                wins_special: save.wins_special(),
                score_total: save.score_total().to_string(),
                score_top: save.score_top(),
                time_total: save.time_total().to_string(),
                time_best: save.time_best(),
                time_tutorial: save.time_tutorial(),
                deepest_area: save.deepest_area(),
                deepest_level: save.deepest_level(),
            },
            unlocks: UnlocksEdit {
                completed_normal: save.completed_normal(),
                completed_ironman: save.completed_ironman(),
                completed_hard: save.completed_hard(),
                profile_seen: save.profile_seen(),
                seeded_unlocked: save.seeded_unlocked(),
                shortcuts: save.shortcuts(),
                tutorial_state: save.tutorial_state(),
            },
            last_run: LastRunEdit {
                world: save.world_last(),
                level: save.level_last(),
                theme: save.theme_last(),
                score: save.score_last(),
                time: save.time_last(),
                stickers: save.stickers().into_iter().filter(|id| *id != 0).collect(),
            },
            camp: CampEdit {
                players: save.players(),
                pets_rescued: save.pets_rescued(),
                last_daily: save.last_daily(),
            },
            journal,
            characters,
            deaths,
            themes,
            constellation: save.constellation(),
            constellation_editable: save.constellation_star_count().is_some(),
            shortcut_states: data::SHORTCUT_STATES.to_vec(),
            sticker_names: stickers::name_stickers(&save.stickers())
                .into_iter()
                .map(|sticker| (sticker.entity_type, sticker.name))
                .collect(),
            first_character_entity: stickers::FIRST_CHARACTER,
        }
    }
}

/// Levels a death can actually be recorded at, per world.
///
/// The histogram has 255 columns for every world and the game reaches very
/// few of them. Two ends matter, and both are about the Cosmic Ocean,
/// stored as world 8:
///
/// - It is entered from 7-4, so its levels start at **5**. Columns 1 to 4
///   can never be written.
/// - Its last playable level is **98**. 99 is the closing cutscene, which
///   you arrive at rather than survive, so a death cannot land there -
///   even though `deepest_level` reads 99 for anyone who has finished it.
///
/// Both ends were checked against eight real saves: world-8 counts appear
/// only at levels 7 and 98, with 1 to 4 and 99 empty in every one, while
/// every other world uses 1 up to its own last level.
///
/// Deliberately narrower than `data::WORLD_LEVEL_COUNTS`, which is the
/// highest level *number* a world has rather than the highest one you can
/// die on.
const DEATH_LEVELS: [(usize, usize); 8] = [
    (1, 4),
    (1, 4),
    (1, 1),
    (1, 4),
    (1, 1),
    (1, 4),
    (1, 4),
    (5, 98),
];

/// Highest level number the histogram has a column for.
const DEATH_COLUMNS: usize = 254;

/// The levels to show for `world`, given what the save actually holds.
///
/// Normally the table above, widened at either end by any count that falls
/// outside it. A number this build refuses to show is a number nobody can
/// correct, so an unexpected value is never hidden - it is evidence the
/// table is wrong rather than something to bury.
fn death_level_range(save: &SaveFile, world: usize) -> (usize, usize) {
    let (floor, ceiling) = DEATH_LEVELS[world - 1];
    let held = |level: usize| save.deaths_at(world, level).unwrap_or(0) != 0;

    let first = (1..floor).find(|level| held(*level)).unwrap_or(floor);
    let last = ((ceiling + 1)..=DEATH_COLUMNS)
        .rfind(|level| held(*level))
        .unwrap_or(ceiling);
    (first, last)
}

// -- writing --------------------------------------------------------------

/// Applies every field of `edits` to `save`.
///
/// Fields the user did not touch carry their existing values and so write
/// themselves back unchanged; see the module docs.
fn apply(save: &mut SaveFile, edits: &SaveEdits) -> Result<(), String> {
    let profile = &edits.profile;
    save.set_plays(profile.plays);
    save.set_deaths(profile.deaths);
    save.set_wins_normal(profile.wins_normal);
    save.set_wins_hard(profile.wins_hard);
    save.set_wins_special(profile.wins_special);
    save.set_score_total(parse_i64(&profile.score_total, "Total money")?);
    save.set_score_top(profile.score_top);
    save.set_time_total(parse_i64(&profile.time_total, "Time played")?);
    save.set_time_best(profile.time_best);
    save.set_time_tutorial(profile.time_tutorial);
    save.set_deepest_area(profile.deepest_area);
    save.set_deepest_level(profile.deepest_level);

    let unlocks = &edits.unlocks;
    save.set_completed_normal(unlocks.completed_normal);
    save.set_completed_ironman(unlocks.completed_ironman);
    save.set_completed_hard(unlocks.completed_hard);
    save.set_profile_seen(unlocks.profile_seen);
    save.set_seeded_unlocked(unlocks.seeded_unlocked);
    save.set_shortcuts(unlocks.shortcuts);
    save.set_tutorial_state(unlocks.tutorial_state);

    let last = &edits.last_run;
    save.set_world_last(last.world);
    save.set_level_last(last.level);
    save.set_theme_last(last.theme);
    save.set_score_last(last.score);
    save.set_time_last(last.time);
    save.set_stickers(&last.stickers)
        .map_err(|e| err("Stickers", e))?;

    let camp = &edits.camp;
    save.set_players(camp.players)
        .map_err(|e| err("Player slots", e))?;
    save.set_pets_rescued(camp.pets_rescued);
    save.set_last_daily(camp.last_daily.as_deref())
        .map_err(|e| err("Last daily", e))?;

    for section in &edits.journal {
        let category = JournalCategory::ALL
            .into_iter()
            .find(|c| c.as_str() == section.key)
            .ok_or_else(|| format!("Unknown journal category {:?}", section.key))?;
        expect_len(section.discovered.len(), category.count(), category.label())?;
        for (index, discovered) in section.discovered.iter().enumerate() {
            save.set_discovered(category, index, *discovered)
                .map_err(|e| err(category.label(), e))?;
        }

        if let Some(table) = KillTable::ALL
            .into_iter()
            .find(|table| table.category() == category)
        {
            expect_len(section.killed.len(), table.count(), category.label())?;
            expect_len(section.killed_by.len(), table.count(), category.label())?;
            for index in 0..table.count() {
                save.set_killed(table, index, section.killed[index])
                    .map_err(|e| err(category.label(), e))?;
                save.set_killed_by(table, index, section.killed_by[index])
                    .map_err(|e| err(category.label(), e))?;
            }
        }
    }

    expect_len(edits.characters.len(), data::CHARACTER_COUNT, "Characters")?;
    let mut mask = 0u32;
    for (index, character) in edits.characters.iter().enumerate() {
        if character.unlocked {
            mask |= 1 << index;
        }
        save.set_character_deaths(index, character.deaths)
            .map_err(|e| err("Character deaths", e))?;
    }
    save.set_character_mask(mask);

    expect_len(edits.deaths.len(), 8, "Deaths by level")?;
    for (offset, world_deaths) in edits.deaths.iter().enumerate() {
        let world = offset + 1;
        // Out of order would write every world's counts onto its
        // neighbour, so the caller has to say which world it means.
        if world_deaths.world != world {
            return Err(format!(
                "Deaths by level arrived out of order: expected world {world}, got {}.",
                world_deaths.world
            ));
        }
        let name = data::DEATHCOUNT_WORLDS[offset];
        if world_deaths.first_level == 0 {
            return Err(format!("{name} starts at level 0, which is not a level."));
        }
        if world_deaths.levels.is_empty() {
            return Err(format!("{name} arrived with no levels."));
        }
        // The far end needs no separate check: `set_deaths_at` bounds
        // every write, so a list running off the block is refused there.
        for (index, deaths) in world_deaths.levels.iter().enumerate() {
            save.set_deaths_at(world, world_deaths.first_level + index, *deaths)
                .map_err(|e| err("Deaths by level", e))?;
        }
    }

    // Sent 1-based with id 0 omitted, since 0 is not a theme.
    expect_len(edits.themes.len(), data::THEMES.len() - 1, "Themes")?;
    for (offset, completed) in edits.themes.iter().enumerate() {
        save.set_theme_completed(offset + 1, *completed)
            .map_err(|e| err("Themes", e))?;
    }

    if let Some(constellation) = &edits.constellation {
        save.set_constellation(constellation)
            .map_err(|e| err("Constellation", e))?;
    }

    Ok(())
}

/// Parses a 64-bit field that travelled as a string.
fn parse_i64(raw: &str, what: &str) -> Result<i64, String> {
    raw.trim()
        .parse::<i64>()
        .map_err(|_| format!("{what} is not a whole number."))
}

fn expect_len(got: usize, want: usize, what: &str) -> Result<(), String> {
    if got == want {
        return Ok(());
    }
    Err(format!("{what} should have {want} entries, but got {got}."))
}

// -- commands -------------------------------------------------------------

/// Reads a save into the form the editor works on.
#[tauri::command]
pub fn get_editable_save(source: SaveRef) -> Result<EditableSave, String> {
    let path = source.path()?;
    // `parse_unchecked` rather than `parse`: a save whose checksum does
    // not verify is exactly the save someone opens an editor to fix, and
    // refusing to show it would leave them with no way to do that. The
    // flag rides along so the UI can say so.
    let bytes = std::fs::read(&path).map_err(|e| err("Could not read the save", e))?;
    let save = SaveFile::parse_unchecked(bytes).map_err(|e| err("Could not read the save", e))?;
    Ok(EditableSave::from_save(&save, path.display().to_string()))
}

/// Writes edits back to a save.
///
/// `backup` archives the file first, into the managed library where
/// pruning cannot reach it. It defaults on for the live save and is the
/// only way back from a bad edit.
#[tauri::command(async)]
pub fn apply_save_edits(
    source: SaveRef,
    edits: SaveEdits,
    backup: bool,
    description: String,
) -> Result<EditResult, String> {
    let path = source.path()?;
    let original = std::fs::read(&path).map_err(|e| err("Could not read the save", e))?;
    let mut save = SaveFile::parse_unchecked(original.clone())
        .map_err(|e| err("Could not read the save", e))?;

    // Everything is validated and applied to the in-memory copy before
    // anything touches the disk, so a rejected edit leaves the file alone.
    apply(&mut save, &edits)?;
    let edited = save.to_bytes();

    // Re-parse what is about to be written, and report *that* rather than
    // the buffer it was built from.
    //
    // Two reasons. It verifies the bytes before they reach the disk, using
    // the same check the game would. And it is the only way to describe
    // the result honestly: `to_bytes` recomputes the checksum into the
    // copy it returns and deliberately leaves the source struct alone, so
    // asking `save` whether its checksum verifies compares a stale stored
    // value against a fresh computed one and always answers no. Reporting
    // that told the user their save was broken every single time they
    // saved a perfectly good one.
    let written = SaveFile::parse(edited.clone())
        .map_err(|e| err("Refusing to write a save that does not verify", e))?;
    let describe = || {
        Box::new(EditableSave::from_save(
            &written,
            path.display().to_string(),
        ))
    };

    let changed_bytes = if edited.len() == original.len() {
        (0..edited.len())
            .filter(|i| edited[*i] != original[*i])
            .count()
    } else {
        edited.len()
    };

    if changed_bytes == 0 {
        return Ok(EditResult {
            changed_bytes: 0,
            backup: None,
            save: describe(),
        });
    }

    // The backup is taken from the file on disk, before the write, so it
    // is a copy of exactly what is about to be replaced.
    let stored = if backup {
        Some(
            store::capture(&path, &description, SaveKind::PreEdit)
                .map_err(|e| err("Could not back up the save before editing", e))?,
        )
    } else {
        None
    };

    write_atomically(&path, &edited).map_err(|e| err("Could not write the save", e))?;

    // An archived save's sidecar records the hash and size of its file,
    // and the file has just changed underneath it.
    if let SaveRef::Stored { id } = &source
        && let Err(err) = store::record_edit(id, &edited)
    {
        tracing::warn!("Could not update the record for {id}: {err}");
    }

    Ok(EditResult {
        changed_bytes,
        backup: stored,
        save: describe(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A save built the way the crate's own tests build one.
    fn sample() -> SaveFile {
        let mut bytes = vec![0u8; 13862];
        bytes[0..2].copy_from_slice(&30u16.to_le_bytes());
        let mut save = SaveFile::parse_unchecked(bytes).expect("parses");
        save.set_plays(100);
        save.set_deaths(90);
        save.set_score_total(1_234_567_890_123);
        save.set_players([1, 2, 3, 4]).unwrap();
        save.set_discovered(JournalCategory::Places, 3, true)
            .unwrap();
        save.set_killed(KillTable::Bestiary, 5, 42).unwrap();
        save.set_deaths_at(1, 4, 7).unwrap();
        save
    }

    /// Reading a save and writing the result straight back must not move
    /// a byte. This is the same guarantee the crate proves against real
    /// files, checked again at the layer that actually assembles the
    /// edits, where a missed field or a mismatched order would show up.
    #[test]
    fn a_round_trip_through_the_editor_changes_nothing() {
        let save = sample();
        let before = save.to_bytes();
        let editable = EditableSave::from_save(&save, "test".into());

        let edits = SaveEdits {
            profile: editable.profile.clone(),
            unlocks: editable.unlocks.clone(),
            last_run: editable.last_run.clone(),
            camp: editable.camp.clone(),
            journal: editable
                .journal
                .iter()
                .map(|section| JournalSectionValues {
                    key: section.key.to_string(),
                    discovered: section.entries.iter().map(|e| e.discovered).collect(),
                    killed: section.entries.iter().filter_map(|e| e.killed).collect(),
                    killed_by: section.entries.iter().filter_map(|e| e.killed_by).collect(),
                })
                .collect(),
            characters: editable
                .characters
                .iter()
                .map(|c| CharacterValues {
                    unlocked: c.unlocked,
                    deaths: c.deaths,
                })
                .collect(),
            deaths: editable
                .deaths
                .iter()
                .map(|world| WorldDeathValues {
                    world: world.world,
                    first_level: world.first_level,
                    levels: world.levels.clone(),
                })
                .collect(),
            themes: editable.themes.iter().map(|t| t.completed).collect(),
            constellation: editable.constellation.clone(),
        };

        let mut edited = SaveFile::parse_unchecked(before.clone()).unwrap();
        apply(&mut edited, &edits).expect("applies");
        assert_eq!(edited.to_bytes(), before);
    }

    /// Builds the edits for a save, so a test can change one field of them
    /// and leave the rest exactly as they were read.
    fn edits_for(save: &SaveFile) -> SaveEdits {
        let editable = EditableSave::from_save(save, "test".into());
        SaveEdits {
            profile: editable.profile.clone(),
            unlocks: editable.unlocks.clone(),
            last_run: editable.last_run.clone(),
            camp: editable.camp.clone(),
            journal: editable
                .journal
                .iter()
                .map(|section| JournalSectionValues {
                    key: section.key.to_string(),
                    discovered: section.entries.iter().map(|e| e.discovered).collect(),
                    killed: section.entries.iter().filter_map(|e| e.killed).collect(),
                    killed_by: section.entries.iter().filter_map(|e| e.killed_by).collect(),
                })
                .collect(),
            characters: editable
                .characters
                .iter()
                .map(|c| CharacterValues {
                    unlocked: c.unlocked,
                    deaths: c.deaths,
                })
                .collect(),
            deaths: editable
                .deaths
                .iter()
                .map(|world| WorldDeathValues {
                    world: world.world,
                    first_level: world.first_level,
                    levels: world.levels.clone(),
                })
                .collect(),
            themes: editable.themes.iter().map(|t| t.completed).collect(),
            constellation: editable.constellation.clone(),
        }
    }

    /// Byte offsets that differ between two versions of the same save,
    /// with the trailing checksum removed.
    ///
    /// The checksum covers the whole file, so it moves on every edit and
    /// says nothing about which field was touched.
    fn differing_ignoring_checksum(before: &[u8], after: &[u8]) -> Vec<usize> {
        assert_eq!(before.len(), after.len(), "length changed");
        let body = before.len() - 4;
        (0..body).filter(|i| before[*i] != after[*i]).collect()
    }

    /// Asserts the edit landed inside a single field of `width` bytes.
    ///
    /// Not an exact byte count: writing 100 over 101 changes one byte of
    /// a four-byte little-endian integer and leaves the other three
    /// zeroed, so counting bytes would be asserting the value rather than
    /// the extent. What matters is that nothing outside the field moved.
    fn assert_within_one_field(moved: &[usize], width: usize) {
        assert!(!moved.is_empty(), "nothing changed at all");
        let first = moved[0];
        let last = moved[moved.len() - 1];
        assert!(
            last - first < width,
            "changes span {} bytes, wider than the {width}-byte field: {moved:?}",
            last - first + 1
        );
    }

    /// Changing one field must move that field's bytes and the checksum,
    /// and nothing else.
    ///
    /// The round-trip test proves an untouched edit writes nothing. This
    /// proves the other half: that a touched one does not write anything
    /// *extra*. Together they are the whole safety argument for pointing
    /// this at a real save.
    #[test]
    fn changing_one_field_moves_only_that_field() {
        let save = sample();
        let before = save.to_bytes();

        let mut edits = edits_for(&save);
        edits.profile.plays = 101; // was 100

        let mut edited = SaveFile::parse_unchecked(before.clone()).unwrap();
        apply(&mut edited, &edits).expect("applies");
        let after = edited.to_bytes();

        let moved = differing_ignoring_checksum(&before, &after);
        assert_within_one_field(&moved, 4);
        assert_eq!(edited.plays(), 101);
        // Everything else the profile screen reads is untouched.
        assert_eq!(edited.deaths(), 90);
        assert_eq!(edited.score_total(), 1_234_567_890_123);
        // And the written bytes carry a checksum that verifies. `parse`
        // is the check: it refuses a save whose checksum disagrees, which
        // is exactly what the game would do.
        assert_ne!(&after[after.len() - 4..], &before[before.len() - 4..]);
        SaveFile::parse(after).expect("the written save verifies");
    }

    /// The same, for a field buried in an array rather than a scalar at a
    /// fixed offset - the case where an off-by-one would land on a
    /// neighbour instead.
    #[test]
    fn changing_one_journal_entry_moves_only_that_entry() {
        let save = sample();
        let before = save.to_bytes();

        let mut edits = edits_for(&save);
        // Entry 5 of the bestiary's kill counts.
        let bestiary = edits
            .journal
            .iter_mut()
            .find(|section| section.key == "bestiary")
            .expect("bestiary");
        bestiary.killed[5] = 43; // was 42

        let mut edited = SaveFile::parse_unchecked(before.clone()).unwrap();
        apply(&mut edited, &edits).expect("applies");

        let moved = differing_ignoring_checksum(&before, &edited.to_bytes());
        assert_within_one_field(&moved, 4);
        assert_eq!(edited.killed(KillTable::Bestiary, 5).unwrap(), 43);
        // The neighbours on both sides, and the parallel array, are the
        // places an off-by-one would land.
        assert_eq!(edited.killed(KillTable::Bestiary, 4).unwrap(), 0);
        assert_eq!(edited.killed(KillTable::Bestiary, 6).unwrap(), 0);
        assert_eq!(edited.killed_by(KillTable::Bestiary, 5).unwrap(), 0);
    }

    /// A refused edit must leave the file completely alone rather than
    /// writing the fields it got through before the bad one.
    #[test]
    fn a_rejected_edit_writes_nothing() {
        let save = sample();
        let before = save.to_bytes();

        let mut edits = edits_for(&save);
        edits.profile.plays = 999;
        edits.camp.last_daily = Some("not a date".into());

        let mut edited = SaveFile::parse_unchecked(before.clone()).unwrap();
        apply(&mut edited, &edits).expect_err("bad date");

        // `apply` works on a copy the caller throws away on error, which
        // is what makes this safe; the command never writes that copy.
        let mut target = SaveFile::parse_unchecked(before.clone()).unwrap();
        assert_eq!(target.to_bytes(), before);
        assert_eq!(target.plays(), 100);
        target.set_plays(100);
        assert_eq!(target.to_bytes(), before);
    }

    /// A save written by the editor has to verify, and has to *report*
    /// that it verifies.
    ///
    /// `to_bytes` recomputes the checksum into the copy it returns and
    /// leaves the source struct alone, so asking the struct afterwards
    /// compares a stale stored checksum against a fresh computed one and
    /// always says no. Describing the result from that struct told the
    /// user their save was broken every time they saved a good one.
    #[test]
    fn the_written_save_verifies_and_says_so() {
        let save = sample();
        let mut edits = edits_for(&save);
        edits.profile.plays = 4321;

        let mut edited = SaveFile::parse_unchecked(save.to_bytes()).unwrap();
        apply(&mut edited, &edits).expect("applies");
        let bytes = edited.to_bytes();

        // The bytes are good...
        let written = SaveFile::parse(bytes).expect("the written save verifies");
        assert!(written.checksum_valid());
        // ...and the state handed back describes those bytes, not the
        // struct they came from.
        let described = EditableSave::from_save(&written, "test".into());
        assert!(
            described.checksum_valid,
            "a freshly written save must not report a bad checksum"
        );
        assert_eq!(described.profile.plays, 4321);

        // The trap itself, pinned so nobody reintroduces it.
        assert!(
            !edited.checksum_valid(),
            "to_bytes leaves the source struct's stored checksum stale; \
             that is why the result is described from the written bytes"
        );
    }

    /// The 64-bit fields travel as strings because JSON cannot carry them
    /// exactly, so the value has to survive the trip.
    #[test]
    fn large_counters_survive_the_string_round_trip() {
        let mut save = sample();
        save.set_score_total(9_007_199_254_740_995);
        let editable = EditableSave::from_save(&save, "test".into());
        assert_eq!(editable.profile.score_total, "9007199254740995");
        assert_eq!(
            parse_i64(&editable.profile.score_total, "Total money").unwrap(),
            9_007_199_254_740_995
        );
    }

    #[test]
    fn a_bad_number_is_refused_rather_than_written_as_zero() {
        assert!(parse_i64("", "Total money").is_err());
        assert!(parse_i64("lots", "Total money").is_err());
        assert!(parse_i64("1.5", "Total money").is_err());
        assert_eq!(parse_i64("  42 ", "Total money").unwrap(), 42);
    }

    /// A short list would otherwise write only part of a category and
    /// leave the rest at whatever it was, which is worse than refusing.
    #[test]
    fn a_wrong_length_list_is_refused() {
        let save = sample();
        let editable = EditableSave::from_save(&save, "test".into());
        let mut edits = SaveEdits {
            profile: editable.profile.clone(),
            unlocks: editable.unlocks.clone(),
            last_run: editable.last_run.clone(),
            camp: editable.camp.clone(),
            journal: vec![JournalSectionValues {
                key: "places".into(),
                discovered: vec![true; 3],
                killed: Vec::new(),
                killed_by: Vec::new(),
            }],
            characters: Vec::new(),
            deaths: Vec::new(),
            themes: Vec::new(),
            constellation: None,
        };
        let mut target = SaveFile::parse_unchecked(save.to_bytes()).unwrap();
        let error = apply(&mut target, &edits).expect_err("too few places");
        assert!(error.contains("Places"), "{error}");

        edits.journal[0].key = "nowhere".into();
        let error = apply(&mut target, &edits).expect_err("unknown category");
        assert!(error.contains("nowhere"), "{error}");
    }

    /// Unlock flags are a bitmask in the file but a list of toggles in the
    /// editor, and the mask has to come back out the way it went in.
    #[test]
    fn character_toggles_rebuild_the_mask() {
        let mut save = sample();
        save.set_character_mask(0b1010_1010);
        let editable = EditableSave::from_save(&save, "test".into());
        assert!(!editable.characters[0].unlocked);
        assert!(editable.characters[1].unlocked);
        assert!(editable.characters[7].unlocked);

        let mut mask = 0u32;
        for (index, character) in editable.characters.iter().enumerate() {
            if character.unlocked {
                mask |= 1 << index;
            }
        }
        assert_eq!(mask, 0b1010_1010);
    }

    /// Each world is sent with only the levels it has, so the Dwelling is
    /// four rows and the Cosmic Ocean is ninety-nine.
    #[test]
    fn worlds_carry_only_the_levels_they_have() {
        let editable = EditableSave::from_save(&sample(), "test".into());
        assert_eq!(editable.deaths.len(), 8);
        assert_eq!(editable.deaths[0].first_level, 1);
        assert_eq!(editable.deaths[0].levels.len(), 4);
        assert_eq!(editable.deaths[0].levels[3], 7);
        assert_eq!(editable.deaths[2].levels.len(), 1, "Olmec's Lair");
    }

    /// The Cosmic Ocean is entered from 7-4 and its last playable level is
    /// 98; 99 is the closing cutscene, which you arrive at rather than
    /// survive. Only 5 to 98 can hold a death.
    #[test]
    fn the_cosmic_ocean_covers_only_its_playable_levels() {
        let editable = EditableSave::from_save(&sample(), "test".into());
        let cosmic = &editable.deaths[7];
        assert_eq!(cosmic.name, "Cosmic Ocean");
        assert_eq!(cosmic.first_level, 5);
        assert_eq!(cosmic.levels.len(), 94, "levels 5 through 98");
    }

    /// A count somewhere this build did not expect must still be shown. A
    /// number nobody can see is a number nobody can correct, and it is
    /// evidence the table is wrong rather than something to bury.
    #[test]
    fn an_unexpected_count_widens_the_range_rather_than_hiding() {
        let mut save = sample();
        save.set_deaths_at(8, 2, 3).unwrap();
        save.set_deaths_at(8, 99, 4).unwrap();
        let editable = EditableSave::from_save(&save, "test".into());
        let cosmic = &editable.deaths[7];
        assert_eq!(cosmic.first_level, 2);
        assert_eq!(cosmic.levels[0], 3, "level 2");
        assert_eq!(cosmic.levels.len(), 98, "levels 2 through 99");
        assert_eq!(cosmic.levels[97], 4, "level 99");
    }

    /// The offsets have to follow `first_level`, or an edit lands on the
    /// wrong row - the failure that field exists to prevent.
    #[test]
    fn edits_land_on_the_level_the_row_names() {
        let save = sample();
        let mut edits = edits_for(&save);
        let cosmic = &mut edits.deaths[7];
        assert_eq!(cosmic.first_level, 5);
        cosmic.levels[0] = 11; // level 5
        cosmic.levels[2] = 22; // level 7

        let mut edited = SaveFile::parse_unchecked(save.to_bytes()).unwrap();
        apply(&mut edited, &edits).expect("applies");
        assert_eq!(edited.deaths_at(8, 5).unwrap(), 11);
        assert_eq!(edited.deaths_at(8, 7).unwrap(), 22);
        assert_eq!(edited.deaths_at(8, 4).unwrap(), 0, "untouched below");
        assert_eq!(edited.deaths_at(8, 6).unwrap(), 0);
    }

    #[test]
    fn deaths_out_of_order_are_refused() {
        let save = sample();
        let mut edits = edits_for(&save);
        edits.deaths.swap(0, 1);
        let mut target = SaveFile::parse_unchecked(save.to_bytes()).unwrap();
        let error = apply(&mut target, &edits).expect_err("out of order");
        assert!(error.contains("out of order"), "{error}");
    }

    /// Theme id 0 is not a theme, so the list starts at 1 and the ids say
    /// so - the frontend must not have to know that off by heart.
    #[test]
    fn themes_are_sent_one_based() {
        let editable = EditableSave::from_save(&sample(), "test".into());
        assert_eq!(editable.themes.len(), data::THEMES.len() - 1);
        assert_eq!(editable.themes[0].id, 1);
        assert_eq!(editable.themes[0].name, "Dwelling");
    }

    /// Empty sticker slots are dropped on the way out, so the editor
    /// shows a run's actual stickers rather than seventeen blanks.
    #[test]
    fn empty_sticker_slots_are_not_sent() {
        let mut save = sample();
        save.set_stickers(&[199, 539]).unwrap();
        let editable = EditableSave::from_save(&save, "test".into());
        assert_eq!(editable.last_run.stickers, vec![199, 539]);
    }
}
