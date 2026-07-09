//! Vanilla multi-room mosaic constants + setroom-name matcher.
//!
//! The small data tables the mosaic editor uses to sort vanilla setroom
//! templates into a rectangular grid:
//!
//! - `REVERSED_ROOMS` (5 setroom names whose front / back layers are
//!   drawn in reversed order)
//! - `BASE_TEMPLATES` (the three template families
//!   `setroom{y}-{x}` / `challenge_{y}-{x}` /
//!   `palaceofpleasure_{y}-{x}`)
//! - `VanillaSetroomType` (none / front / back / dual, how a template
//!   represents its layers)
//! - `match_setroom` / `find_vanilla_setroom`, the (y, x) parser the
//!   mosaic layout code walks over every template name.
//!
//! The `find_roommap` grid algorithm isn't included here: it's
//! UI-adjacent and no Rust consumer needs it yet. When mosaic editor
//! work lands, add it then. Everything a future consumer needs beyond
//! `find_roommap` (template families, reversed-layer list, setroom
//! parser) lives in this module.

use once_cell::sync::Lazy;
use regex::Regex;

/// Setroom template names whose front and back layers are drawn in
/// reversed order. Load-bearing at every FG/BG draw + save site: swap
/// the list wrong and those rooms render / persist with the layers
/// flipped.
pub const REVERSED_ROOMS: &[&str] = &[
    "palaceofpleasure_1-1",
    "palaceofpleasure_3-2",
    "udjatentrance",
    "challenge_entrance",
    "blackmarket_exit",
];

/// One entry from the vanilla base-template registry. `name` is the
/// human-facing category label (`"setroom"`, `"challenge"`, `"palace
/// of pleasure"`) and `pattern` is a `{y}` / `{x}` template used both
/// to generate a canonical template name and, once compiled to a regex,
/// to parse `(y, x)` back out of a template's name.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BaseTemplateData {
    pub name: &'static str,
    pub pattern: &'static str,
}

/// The three vanilla multi-room template families. Order is
/// load-bearing: `find_vanilla_setroom` searches them in this order,
/// so a template name that matched both `setroom{y}-{x}` and
/// `challenge_{y}-{x}` (nothing does today, but nothing enforces
/// disjointness) would bind to the earlier family.
pub const BASE_SETROOM: BaseTemplateData = BaseTemplateData {
    name: "setroom",
    pattern: "setroom{y}-{x}",
};
pub const BASE_CHALLENGE: BaseTemplateData = BaseTemplateData {
    name: "challenge",
    pattern: "challenge_{y}-{x}",
};
pub const BASE_PALACE: BaseTemplateData = BaseTemplateData {
    name: "palace of pleasure",
    pattern: "palaceofpleasure_{y}-{x}",
};

pub const BASE_TEMPLATES: &[BaseTemplateData] = &[BASE_SETROOM, BASE_CHALLENGE, BASE_PALACE];

/// How a template represents its layers on disk. Serialized as its
/// lowercase name so a shared config.json round-trips.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VanillaSetroomType {
    None,
    Front,
    Back,
    Dual,
}

impl VanillaSetroomType {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Front => "front",
            Self::Back => "back",
            Self::Dual => "dual",
        }
    }
}

/// `(x, y)` coord parsed out of a template name.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RoomCoords {
    pub x: u32,
    pub y: u32,
}

/// A template name that matched some `BASE_TEMPLATES` family, together
/// with which family it matched + the extracted `(x, y)`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MatchedSetroom {
    pub family: BaseTemplateData,
    pub coords: RoomCoords,
}

/// Replaces `{y}` / `{x}` in a template pattern with numeric capture
/// groups and returns the compiled anchored regex. Escapes every other
/// pattern character so a family with punctuation (nothing today, but
/// future-proofed) parses cleanly.
fn compile_pattern(pattern: &str) -> Regex {
    // Split on the `{y}` and `{x}` placeholders so the surrounding
    // literals get escaped and the placeholders become named groups.
    let mut re = String::from("^");
    let mut rest = pattern;
    while !rest.is_empty() {
        let y_idx = rest.find("{y}");
        let x_idx = rest.find("{x}");
        let next_idx = match (y_idx, x_idx) {
            (Some(y), Some(x)) => Some((y.min(x), if y < x { 'y' } else { 'x' })),
            (Some(y), None) => Some((y, 'y')),
            (None, Some(x)) => Some((x, 'x')),
            (None, None) => None,
        };
        match next_idx {
            Some((idx, tag)) => {
                re.push_str(&regex::escape(&rest[..idx]));
                match tag {
                    'y' => re.push_str(r"(?P<y>\d+)"),
                    'x' => re.push_str(r"(?P<x>\d+)"),
                    _ => unreachable!(),
                }
                rest = &rest[idx + 3..];
            }
            None => {
                re.push_str(&regex::escape(rest));
                rest = "";
            }
        }
    }
    re.push('$');
    Regex::new(&re).expect("valid template pattern")
}

/// Try to parse `room` as an instance of `family`'s template pattern.
/// Returns the extracted `(x, y)` on match, `None` otherwise.
pub fn match_setroom(family: BaseTemplateData, room: &str) -> Option<RoomCoords> {
    // Cache one regex per pattern; the three vanilla families exhaust
    // the useful cache today, but the map handles any future family
    // added to BASE_TEMPLATES.
    static CACHE: Lazy<std::sync::Mutex<std::collections::HashMap<&'static str, Regex>>> =
        Lazy::new(|| std::sync::Mutex::new(std::collections::HashMap::new()));
    let mut cache = CACHE.lock().unwrap();
    let re = cache
        .entry(family.pattern)
        .or_insert_with(|| compile_pattern(family.pattern));
    let caps = re.captures(room)?;
    let y = caps.name("y")?.as_str().parse::<u32>().ok()?;
    let x = caps.name("x")?.as_str().parse::<u32>().ok()?;
    Some(RoomCoords { x, y })
}

/// Walk `BASE_TEMPLATES` in order and return the first family +
/// coords that `room` matches.
pub fn find_vanilla_setroom(room: &str) -> Option<MatchedSetroom> {
    for family in BASE_TEMPLATES {
        if let Some(coords) = match_setroom(*family, room) {
            return Some(MatchedSetroom {
                family: *family,
                coords,
            });
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reversed_rooms_list_is_pinned() {
        // Pin the 5 canonical reversed-room names. Any rename here
        // breaks FG/BG orientation for those rooms in a future mosaic
        // editor.
        assert_eq!(
            REVERSED_ROOMS,
            &[
                "palaceofpleasure_1-1",
                "palaceofpleasure_3-2",
                "udjatentrance",
                "challenge_entrance",
                "blackmarket_exit",
            ]
        );
    }

    #[test]
    fn base_templates_have_expected_names_and_patterns() {
        assert_eq!(BASE_SETROOM.name, "setroom");
        assert_eq!(BASE_SETROOM.pattern, "setroom{y}-{x}");
        assert_eq!(BASE_CHALLENGE.name, "challenge");
        assert_eq!(BASE_CHALLENGE.pattern, "challenge_{y}-{x}");
        assert_eq!(BASE_PALACE.name, "palace of pleasure");
        assert_eq!(BASE_PALACE.pattern, "palaceofpleasure_{y}-{x}");
    }

    #[test]
    fn vanilla_setroom_type_serializes_as_lowercase_name() {
        assert_eq!(VanillaSetroomType::None.as_str(), "none");
        assert_eq!(VanillaSetroomType::Front.as_str(), "front");
        assert_eq!(VanillaSetroomType::Back.as_str(), "back");
        assert_eq!(VanillaSetroomType::Dual.as_str(), "dual");
    }

    #[test]
    fn match_setroom_parses_dash_format() {
        let coords = match_setroom(BASE_SETROOM, "setroom2-3").expect("match");
        assert_eq!(coords, RoomCoords { x: 3, y: 2 });
    }

    #[test]
    fn match_setroom_rejects_non_matching_name() {
        assert!(match_setroom(BASE_SETROOM, "entrance").is_none());
    }

    #[test]
    fn match_setroom_rejects_wrong_family() {
        // A `challenge_1-2` name matches the challenge family, not
        // setroom.
        assert!(match_setroom(BASE_SETROOM, "challenge_1-2").is_none());
        assert_eq!(
            match_setroom(BASE_CHALLENGE, "challenge_1-2"),
            Some(RoomCoords { x: 2, y: 1 })
        );
    }

    #[test]
    fn find_vanilla_setroom_walks_families_in_order() {
        let m = find_vanilla_setroom("palaceofpleasure_4-1").expect("match");
        assert_eq!(m.family.name, "palace of pleasure");
        assert_eq!(m.coords, RoomCoords { x: 1, y: 4 });
    }

    #[test]
    fn find_vanilla_setroom_returns_none_on_unknown_name() {
        assert!(find_vanilla_setroom("blackmarket_exit").is_none());
    }
}
