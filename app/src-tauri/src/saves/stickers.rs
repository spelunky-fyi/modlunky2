//! Naming the stickers on a save's last-game page.
//!
//! The save records up to twenty entity types for the last run. The game
//! draws them as little sprites under "Last Game Played", and they are a
//! summary of the run: the character played, plus the notable things that
//! were being carried at the end. A save whose last run was a warp shows
//! one sticker; a real run shows a character and its haul.
//!
//! The ids are raw `ENT_TYPE` values, which `ml2_save` deliberately does
//! not try to name: it is a file-format crate, and the entity table is
//! three quarters of a megabyte of game data. The app already links that
//! table for the level editor, so the naming happens here instead.

use std::collections::HashMap;
use std::sync::LazyLock;

use serde::Serialize;

/// The first playable character's entity type.
///
/// The twenty characters are contiguous from here, in the same order as
/// the unlock bitmask, so a character sticker can be named properly
/// ("Liz Mutton") rather than from its internal id ("Green Girl").
pub const FIRST_CHARACTER: u32 = 194;

/// Entity id to `ENT_TYPE_*` name, inverted from the bundled table once.
static NAMES_BY_ID: LazyLock<HashMap<u32, &'static str>> = LazyLock::new(|| {
    ml2_entity_data::ENTITIES
        .iter()
        // Entity ids are i64 in the bundled table but always small and
        // non-negative; the save stores them as u32.
        .filter_map(|(name, entity)| Some((u32::try_from(entity.id).ok()?, name.as_str())))
        .collect()
});

/// One sticker from the last run.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Sticker {
    /// The raw entity type, so an editor could round-trip it.
    pub entity_type: u32,
    /// Something a person would recognize.
    pub name: String,
    /// Whether this is the character that was being played.
    pub is_character: bool,
}

/// Names the stickers a save recorded, dropping the empty slots.
///
/// The array is fixed at twenty and the game leaves the tail zeroed, so a
/// zero means "no sticker" rather than "entity 0".
pub fn name_stickers(entity_types: &[u32]) -> Vec<Sticker> {
    entity_types
        .iter()
        .copied()
        .filter(|entity_type| *entity_type != 0)
        .map(|entity_type| {
            let character = character_index(entity_type);
            Sticker {
                entity_type,
                name: match character {
                    Some(index) => ml2_save::data::characters()
                        .get(index)
                        .copied()
                        .unwrap_or("Unknown")
                        .to_string(),
                    None => pretty_name(entity_type),
                },
                is_character: character.is_some(),
            }
        })
        .collect()
}

/// The playable-character index for an entity type, if it is one.
fn character_index(entity_type: u32) -> Option<usize> {
    let index = entity_type.checked_sub(FIRST_CHARACTER)? as usize;
    (index < ml2_save::data::CHARACTER_COUNT).then_some(index)
}

/// Turns `ENT_TYPE_ITEM_POWERUP_CLIMBING_GLOVES` into `Climbing Gloves`.
///
/// Falls back to the raw id when the entity is not in the table, which is
/// better than an empty cell: it at least says something is there.
fn pretty_name(entity_type: u32) -> String {
    let Some(raw) = NAMES_BY_ID.get(&entity_type) else {
        return format!("Entity {entity_type}");
    };
    let stripped = raw.strip_prefix("ENT_TYPE_").unwrap_or(raw);
    // Category prefixes say which table an entity lives in, not what it
    // is, so they are noise on a sticker.
    let stripped = [
        "ITEM_PICKUP_",
        "ITEM_POWERUP_",
        "ITEM_",
        "MOUNT_",
        "MONS_",
        "CHAR_",
        "BG_",
        "FX_",
    ]
    .iter()
    .find_map(|prefix| stripped.strip_prefix(prefix))
    .unwrap_or(stripped);

    stripped
        .split('_')
        .filter(|word| !word.is_empty())
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                Some(first) => {
                    first.to_uppercase().collect::<String>() + &chars.as_str().to_lowercase()
                }
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Character stickers get the name the game calls them, not the one
    /// the engine does. Entity 199 is `CHAR_GREEN_GIRL`, who is Liz
    /// Mutton everywhere a player can see her.
    #[test]
    fn characters_use_their_player_facing_names() {
        let stickers = name_stickers(&[199]);
        assert_eq!(stickers.len(), 1);
        assert_eq!(stickers[0].name, "Liz Mutton");
        assert!(stickers[0].is_character);
        assert_eq!(stickers[0].entity_type, 199);
    }

    #[test]
    fn the_character_range_is_bounded_at_both_ends() {
        assert_eq!(character_index(FIRST_CHARACTER), Some(0));
        assert_eq!(character_index(FIRST_CHARACTER + 19), Some(19));
        assert_eq!(character_index(FIRST_CHARACTER + 20), None);
        assert_eq!(character_index(FIRST_CHARACTER - 1), None);
        assert_eq!(character_index(0), None);
    }

    /// Items keep their own names, with the category prefix dropped: it
    /// says which table the entity lives in, not what it is.
    #[test]
    fn items_are_named_readably() {
        let stickers = name_stickers(&[539, 546]);
        assert_eq!(stickers[0].name, "Ankh");
        assert!(!stickers[0].is_character);
        assert_eq!(stickers[1].name, "Climbing Gloves");
    }

    /// The array is a fixed twenty with the tail zeroed, so a zero is an
    /// empty slot rather than an entity.
    #[test]
    fn empty_slots_are_dropped() {
        assert!(name_stickers(&[0; 20]).is_empty());
        assert_eq!(name_stickers(&[199, 0, 0, 539]).len(), 2);
    }

    /// A save edited by hand, or a newer game version, can hold an id
    /// this build has never heard of.
    #[test]
    fn an_unknown_entity_still_says_something() {
        let stickers = name_stickers(&[999_999]);
        assert_eq!(stickers[0].name, "Entity 999999");
        assert!(!stickers[0].is_character);
    }

    /// A real run from an archived save: the character plus what they
    /// were carrying at the end.
    #[test]
    fn names_a_whole_run() {
        let names: Vec<String> = name_stickers(&[211, 539, 541, 543])
            .into_iter()
            .map(|s| s.name)
            .collect();
        assert_eq!(
            names,
            vec!["Dirk Yamaoka", "Ankh", "Skeleton Key", "Playerbag"]
        );
    }
}
