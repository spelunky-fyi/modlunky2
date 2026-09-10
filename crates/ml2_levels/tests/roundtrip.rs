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

/// The three non-ASCII tile codes carried by the `nonascii`/`mojibake`
/// fixtures, as (name, expected value, expected cp1252 byte).
const NON_ASCII_CODES: &[(&str, &str, u8)] = &[
    ("vault_wall", "\u{ff}", 0xFF),
    ("styled_floor", "\u{e7}", 0xE7),
    ("treasure_vaultchest%50%crate", "\u{20ac}", 0x80),
];

fn assert_non_ascii_codes(level: &LevelFile) {
    for (name, expected, _) in NON_ASCII_CODES {
        let tc = level
            .tile_codes
            .get(name)
            .unwrap_or_else(|| panic!("{name} tile code present"));
        assert_eq!(
            tc.value, *expected,
            "{name} should decode to one char, got {:?}",
            tc.value
        );
        assert_eq!(tc.value.chars().count(), 1);
    }
}

#[test]
fn non_ascii_tile_codes_survive_a_write_cycle() {
    let bytes = std::fs::read(fixture("test-level-nonascii.lvl")).expect("fixture read");
    let level = LevelFile::from_bytes(&bytes).expect("parse");
    assert_non_ascii_codes(&level);

    // Each value must go back out as its single cp1252 byte, not as a
    // multi-byte UTF-8 sequence. Writing UTF-8 into a cp1252 `.lvl` produced
    // files that failed to reload ("value \u{e2}\u{201a}\u{ac} must be exactly
    // one character") and that Spelunky 2 itself couldn't read.
    let written = level.to_bytes().expect("serialize");
    assert_eq!(
        written, bytes,
        "write cycle must be byte-for-byte identical"
    );
    for (_, _, byte) in NON_ASCII_CODES {
        assert!(
            written.contains(byte),
            "expected cp1252 byte {byte:#04X} in output"
        );
    }
    assert!(
        !written.windows(3).any(|w| w == [0xE2, 0x82, 0xAC]),
        "output must not contain the UTF-8 encoding of \u{20ac}"
    );
}

#[test]
fn utf8_written_into_a_cp1252_file_is_repaired_on_load() {
    // A file saved by an affected Modlunky build: high bytes stored as their
    // UTF-8 sequences. It must load rather than erroring out...
    let level = LevelFile::from_path(fixture("test-level-mojibake.lvl")).expect("parse");
    assert_non_ascii_codes(&level);

    // ...and saving it must heal the file back to correct cp1252 bytes.
    let repaired = level.to_bytes().expect("serialize");
    let expected = std::fs::read(fixture("test-level-nonascii.lvl")).expect("fixture read");
    assert_eq!(repaired, expected, "resaving must repair the file on disk");
}
