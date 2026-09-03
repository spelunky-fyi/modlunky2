//! Checks the parser against real `savegame.sav` files.
//!
//! Real saves are personal files and cannot be committed, so this test is
//! opt-in. Point `ML2_SAVE_FIXTURES` at a directory of `.sav` files and it
//! runs; with the variable unset it reports what it would have done and
//! passes, so CI stays green.
//!
//! ```console
//! ML2_SAVE_FIXTURES="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2" \
//!     cargo test -p ml2_save --test real_saves -- --nocapture
//! ```
//!
//! The checks here are the ones that cannot be written against a synthetic
//! buffer, because they depend on the game's own internal consistency:
//! the checksum the game wrote has to verify, and the death histogram has
//! to sum to the death counter the game maintains separately. Those two
//! together are what pin the offsets down.
//!
//! The other half of the evidence is not reproducible as a test, so it is
//! recorded here. Playing the game and diffing the save before and after
//! confirmed several fields individually: a Cosmic Ocean run moved the
//! last-run block and generated a constellation, a full pass through the
//! arena settings moved 135 of the arena ruleset's 192 bytes onto the
//! fields Overlunky's struct predicts, and a short Dwelling run in which
//! one Monty was rescued moved exactly nine bytes, all of them explained:
//! Snake, Spider and Bat kill counters, the run counter, Monty's rescue
//! count, and the checksum.

use std::path::PathBuf;

use ml2_save::{JournalCategory, KillTable, SaveFile, SaveSummary, data};

/// Saves the harness found, or an empty list when it is not configured.
fn fixtures() -> Vec<PathBuf> {
    let Ok(dir) = std::env::var("ML2_SAVE_FIXTURES") else {
        return Vec::new();
    };
    let Ok(entries) = std::fs::read_dir(&dir) else {
        panic!("ML2_SAVE_FIXTURES is set to {dir}, which could not be read");
    };
    let mut paths: Vec<PathBuf> = entries
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|path| {
            path.extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("sav"))
        })
        .collect();
    paths.sort();
    assert!(
        !paths.is_empty(),
        "ML2_SAVE_FIXTURES is set to {dir}, but it holds no .sav files"
    );
    paths
}

fn skip_notice() {
    eprintln!("skipping: set ML2_SAVE_FIXTURES to a directory of savegame.sav files to run this");
}

/// Every real save must parse with its checksum intact. A failure here
/// means either the checksum algorithm or the body range is wrong.
#[test]
fn real_saves_parse_and_verify() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path)
            .unwrap_or_else(|err| panic!("{} failed to parse: {err}", path.display()));
        assert!(
            save.checksum_valid(),
            "{} has a checksum this build does not reproduce",
            path.display()
        );
    }
}

/// Reading a save and writing it straight back has to produce the same
/// bytes, every byte, including the regions nothing here decodes.
#[test]
fn real_saves_round_trip_byte_for_byte() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let original = std::fs::read(&path).unwrap();
        let save = SaveFile::parse(original.clone()).unwrap();
        let written = save.to_bytes();
        assert_eq!(
            written.len(),
            original.len(),
            "{} changed length on write",
            path.display()
        );
        if written != original {
            let first = (0..original.len())
                .find(|i| written[*i] != original[*i])
                .unwrap();
            panic!(
                "{} differs from its own bytes at {first:#x}",
                path.display()
            );
        }
    }
}

/// The game maintains a total death counter and a per-level histogram
/// independently. They agree in every real save, which is the check that
/// fixes where the histogram starts: shift it and the sum stops matching.
#[test]
fn death_histogram_agrees_with_the_death_counter() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        assert_eq!(
            save.deathcount_total(),
            save.deaths() as u64,
            "{}: histogram and counter disagree",
            path.display()
        );
    }
}

/// Worlds 3 and 5 have exactly one level each, in every version of the
/// game. So every death recorded in them must sit at level 1.
///
/// This is the sharpest available check on where the histogram starts: it
/// does not depend on how far the player got, and shifting the block by
/// even one column moves those deaths off level 1 and fails.
#[test]
fn single_level_worlds_only_have_deaths_on_level_one() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        for world in [3usize, 5] {
            let total = save.deaths_in_world_total(world).unwrap();
            let on_level_one = save.deaths_at(world, 1).unwrap();
            assert_eq!(
                total,
                on_level_one,
                "{}: {} has {total} deaths but only {on_level_one} on its one level",
                path.display(),
                data::DEATHCOUNT_WORLDS[world - 1],
            );
        }
    }
}

/// There is no level 0, so column 0 of every row must be empty. A
/// histogram read one column early would put the Dwelling's first-level
/// deaths there.
#[test]
fn no_deaths_at_level_zero() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let bytes = std::fs::read(&path).unwrap();
        let start = ml2_save::layout::DEATHCOUNT_PER_LEVEL.start;
        for world in 0..data::DEATHCOUNT_WORLDS.len() {
            let at = start + world * ml2_save::layout::DEATHCOUNT_COLUMNS * 4;
            let value = u32::from_le_bytes(bytes[at..at + 4].try_into().unwrap());
            assert_eq!(
                value,
                0,
                "{}: world {} has {value} deaths at level 0",
                path.display(),
                world + 1
            );
        }
    }
}

/// Deaths must land somewhere a level could exist. Worlds sometimes record
/// one past their usual last level, so this only rules out the absurd.
#[test]
fn deaths_land_on_plausible_levels() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        for world in 1..=data::DEATHCOUNT_WORLDS.len() {
            for level in 100..255 {
                assert_eq!(
                    save.deaths_at(world, level).unwrap(),
                    0,
                    "{}: deaths recorded at {world}-{level}",
                    path.display(),
                );
            }
        }
    }
}

/// Journal discovery counts cannot exceed the number of entries that
/// exist, which they would if a category's range overran the next one's.
#[test]
fn journal_counts_stay_within_their_categories() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        for category in JournalCategory::ALL {
            let discovered = save.discovered_count(category);
            assert!(
                discovered <= category.count(),
                "{}: {} discovered {discovered} of {}",
                path.display(),
                category.as_str(),
                category.count()
            );
        }
    }
}

/// Whatever a save records as its deepest depth has to be a real place.
#[test]
fn deepest_depth_is_plausible() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        let (area, level) = (save.deepest_area(), save.deepest_level());
        // A save that has never been played reads 0-0.
        if area == 0 && level == 0 {
            continue;
        }
        assert!(
            (1..=8).contains(&area),
            "{}: deepest area {area} is not a world",
            path.display()
        );
        assert!(
            level >= 1 && usize::from(level) <= data::WORLD_LEVEL_COUNTS[usize::from(area) - 1],
            "{}: {area}-{level} is not a level that exists",
            path.display()
        );
    }
}

/// A constellation the game wrote has to be internally consistent: no line
/// may point at a star that is not there.
#[test]
fn constellations_are_internally_consistent() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        let Some(constellation) = save.constellation() else {
            continue;
        };
        for line in &constellation.lines {
            assert!(
                usize::from(line.from) < constellation.stars.len()
                    && usize::from(line.to) < constellation.stars.len(),
                "{}: line {}-{} but only {} stars",
                path.display(),
                line.from,
                line.to,
                constellation.stars.len()
            );
        }
        // The game's own charts sit inside the coordinate space
        // `Constellation::from_points` maps into.
        for star in &constellation.stars {
            assert!(
                star.x.is_finite() && star.y.is_finite(),
                "{}: star at a non-finite position",
                path.display()
            );
            assert!(
                star.x.abs() <= 2.0 && star.y.abs() <= 2.0,
                "{}: star at ({}, {}) is outside the expected range",
                path.display(),
                star.x,
                star.y
            );
        }
    }
}

/// Not an assertion so much as a readout. Run with `--nocapture` to see
/// what the parser makes of each file, which is the quickest way to sanity
/// check a save version nobody has looked at yet.
#[test]
fn dump_summaries() {
    let paths = fixtures();
    if paths.is_empty() {
        return skip_notice();
    }
    for path in paths {
        let save = SaveFile::read(&path).unwrap();
        let summary = SaveSummary::from_save(&save);
        let name = path.file_name().unwrap().to_string_lossy();
        eprintln!(
            "{name}: v{} {} bytes | {} plays, {} deaths, {}N/{}H/{}CO wins | deepest {}-{} \
             | journal {}/{} | {} characters | constellation {} | tail {}",
            summary.version,
            save.as_bytes().len(),
            summary.plays,
            summary.deaths,
            summary.wins_normal,
            summary.wins_hard,
            summary.wins_special,
            summary.deepest_area,
            summary.deepest_level,
            summary.journal_discovered,
            summary.journal_total,
            summary.characters_unlocked,
            match summary.constellation_stars {
                Some(n) => format!("{n} stars"),
                None => "unreadable".to_string(),
            },
            if save.layout().has_constellation() {
                "known"
            } else {
                "UNKNOWN"
            },
        );
        for world in &summary.world_deaths {
            if world.total > 0 {
                eprintln!(
                    "    {:<20} {:>4}  {:?}",
                    world.name, world.total, world.levels
                );
            }
        }
    }
}

/// Reading every editable field and writing it straight back must leave
/// the file byte-for-byte identical.
///
/// This is the guarantee the whole editor rests on. The save has regions
/// this build does not model - sticker angles, the arena ruleset, whatever
/// is in the gaps - and an editor that round-tripped through a struct
/// would quietly drop them. Editing in place cannot, and this proves it
/// on real files rather than on a buffer of the right length.
#[test]
fn rewriting_every_field_with_its_own_value_changes_no_bytes() {
    let paths = fixtures();
    if paths.is_empty() {
        eprintln!("ML2_SAVE_FIXTURES not set; skipping");
        return;
    }

    for path in paths {
        let original = std::fs::read(&path).expect("reading fixture");
        let mut save = SaveFile::parse(original.clone()).expect("parsing fixture");

        // Scalars.
        save.set_plays(save.plays());
        save.set_deaths(save.deaths());
        save.set_wins_normal(save.wins_normal());
        save.set_wins_hard(save.wins_hard());
        save.set_wins_special(save.wins_special());
        save.set_score_total(save.score_total());
        save.set_score_top(save.score_top());
        save.set_time_total(save.time_total());
        save.set_time_best(save.time_best());
        save.set_time_tutorial(save.time_tutorial());
        save.set_score_last(save.score_last());
        save.set_time_last(save.time_last());
        save.set_deepest_area(save.deepest_area());
        save.set_deepest_level(save.deepest_level());
        save.set_world_last(save.world_last());
        save.set_level_last(save.level_last());
        save.set_theme_last(save.theme_last());
        save.set_completed_normal(save.completed_normal());
        save.set_completed_ironman(save.completed_ironman());
        save.set_completed_hard(save.completed_hard());
        save.set_profile_seen(save.profile_seen());
        save.set_seeded_unlocked(save.seeded_unlocked());
        save.set_tutorial_state(save.tutorial_state());
        save.set_shortcuts(save.shortcuts());
        save.set_character_mask(save.character_mask());

        // Journal discovery and kill counts.
        for category in JournalCategory::ALL {
            for index in 0..category.count() {
                let value = save.discovered(category, index).unwrap();
                save.set_discovered(category, index, value).unwrap();
            }
        }
        for table in KillTable::ALL {
            for index in 0..table.count() {
                let killed = save.killed(table, index).unwrap();
                save.set_killed(table, index, killed).unwrap();
                let killed_by = save.killed_by(table, index).unwrap();
                save.set_killed_by(table, index, killed_by).unwrap();
            }
        }

        // Arrays.
        for (index, deaths) in save.character_deaths().into_iter().enumerate() {
            save.set_character_deaths(index, deaths).unwrap();
        }
        save.set_pets_rescued(save.pets_rescued());
        for (id, done) in save.completed_themes().into_iter().enumerate() {
            save.set_theme_completed(id, done).unwrap();
        }
        save.set_players(save.players()).unwrap();
        save.set_stickers(&save.stickers()).unwrap();
        let daily = save.last_daily();
        save.set_last_daily(daily.as_deref()).unwrap();

        for world in 1..=8 {
            for level in 1..=99 {
                let deaths = save.deaths_at(world, level).unwrap();
                save.set_deaths_at(world, level, deaths).unwrap();
            }
        }

        if let Some(constellation) = save.constellation() {
            save.set_constellation(&constellation).unwrap();
        }

        let rewritten = save.to_bytes();
        assert_eq!(
            rewritten.len(),
            original.len(),
            "{} changed length",
            path.display()
        );
        let differing: Vec<usize> = (0..original.len())
            .filter(|i| rewritten[*i] != original[*i])
            .collect();
        assert!(
            differing.is_empty(),
            "{} changed at {} offsets, first at {:#x}",
            path.display(),
            differing.len(),
            differing.first().copied().unwrap_or(0)
        );
    }
}
