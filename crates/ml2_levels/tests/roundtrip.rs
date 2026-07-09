//! Round-trip integration tests against canonical `.lvl` fixtures.
//!
//! - `test-level-in.lvl` is the raw input.
//! - `test-level-out-1.lvl` is the byte-for-byte output of a no-op
//!   parse -> write cycle.
//! - `test-level-out-2.lvl` is the output after three specific
//!   mutations: clear the file-level comment, clear the `coffin_player`
//!   template comment, and set the `vault_wall` tile-code comment.

use std::path::PathBuf;

use ml2_levels::LevelFile;

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(name)
}

fn read_fixture(name: &str) -> String {
    let bytes = std::fs::read(fixture(name)).expect("fixture read");
    let (decoded, _, _) = encoding_rs::WINDOWS_1252.decode(&bytes);
    decoded.into_owned()
}

#[test]
fn parse_then_write_matches_out1_byte_for_byte() {
    let level = LevelFile::from_path(fixture("test-level-in.lvl")).expect("parse");
    let actual = level.to_string().expect("serialize");
    let expected = read_fixture("test-level-out-1.lvl");

    if actual != expected {
        // Show the first mismatching line for easier debugging.
        let a_lines: Vec<&str> = actual.split_inclusive('\n').collect();
        let e_lines: Vec<&str> = expected.split_inclusive('\n').collect();
        for (i, (a, e)) in a_lines.iter().zip(e_lines.iter()).enumerate() {
            if a != e {
                panic!(
                    "line {i} differs\n  expected: {e:?}\n  actual:   {a:?}\n\n\
                     total lines actual={}, expected={}",
                    a_lines.len(),
                    e_lines.len()
                );
            }
        }
        panic!(
            "outputs identical up to shared prefix; lengths differ: actual={}, expected={}",
            a_lines.len(),
            e_lines.len()
        );
    }
}

#[test]
fn parse_mutate_write_matches_out2_byte_for_byte() {
    let mut level = LevelFile::from_path(fixture("test-level-in.lvl")).expect("parse");

    // 1. Clear the file-level comment.
    level.comment = None;

    // 2. Clear the `coffin_player` template comment. Public API doesn't
    //    expose direct mutation of an entry, so walk it via the
    //    templates container.
    {
        // Write access to a template in-place goes through the templates
        // public accessor: clone, mutate, reinsert.
        let templates = &mut level.level_templates;
        let mut current = templates
            .get("coffin_player")
            .expect("coffin_player template present")
            .clone();
        current.comment = None;
        templates.set(current);
    }

    // 3. Set the `vault_wall` tile-code comment to " // Vault Wall".
    //    Storage preserves the leading `//` and space; on write,
    //    `to_line` strips them.
    {
        let codes = &mut level.tile_codes;
        let mut current = codes.get("vault_wall").expect("vault_wall present").clone();
        current.comment = Some(" // Vault Wall".to_string());
        codes.set(current);
    }

    let actual = level.to_string().expect("serialize");
    let expected = read_fixture("test-level-out-2.lvl");

    if actual != expected {
        let a_lines: Vec<&str> = actual.split_inclusive('\n').collect();
        let e_lines: Vec<&str> = expected.split_inclusive('\n').collect();
        for (i, (a, e)) in a_lines.iter().zip(e_lines.iter()).enumerate() {
            if a != e {
                panic!(
                    "line {i} differs\n  expected: {e:?}\n  actual:   {a:?}\n\n\
                     total lines actual={}, expected={}",
                    a_lines.len(),
                    e_lines.len()
                );
            }
        }
        panic!(
            "outputs identical up to shared prefix; lengths differ: actual={}, expected={}",
            a_lines.len(),
            e_lines.len()
        );
    }
}
