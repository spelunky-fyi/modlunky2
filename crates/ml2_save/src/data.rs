//! Names for the fixed entry tables in a save file.
//!
//! The journal arrays in `savegame.sav` are positional: entry N of the
//! bestiary is a single byte at a known offset, with nothing in the file to
//! say what it is. These tables supply the missing half.
//!
//! Names come from the game's own journal and match the ones the
//! spelunky.fyi save editor and checklist use, so an index means the same
//! thing in all three tools. Every table here is indexed from zero while
//! the journal numbers its entries from one, so the journal's "01:
//! Dwelling" is `PLACES[0]`.

use crate::JournalCategory;

/// The 16 journal places, in save-file order.
pub const PLACES: [&str; 16] = [
    "Dwelling",
    "Jungle",
    "Volcana",
    "Olmec's Lair",
    "Tide Pool",
    "Abzu",
    "Temple of Anubis",
    "The City of Gold",
    "Duat",
    "Ice Caves",
    "Neo Babylon",
    "Tiamat's Throne",
    "Sunken City",
    "Eggplant World",
    "Hundun's Hideaway",
    "Cosmic Ocean",
];

/// The 78 bestiary entries, in save-file order.
pub const BESTIARY: [&str; 78] = [
    "Snake",
    "Spider",
    "Bat",
    "Caveman",
    "Skeleton",
    "Horned Lizard",
    "Cave Mole",
    "Quillback",
    "Mantrap",
    "Tiki man",
    "Witch Doctor",
    "Mosquito",
    "Monkey",
    "Hang Spider",
    "Giant Spider",
    "Magmar",
    "Robot",
    "Fire Bug",
    "Imp",
    "Lavamander",
    "Vampire",
    "Vlad",
    "Olmec",
    "Jiangshi",
    "Jiangshi Assassin",
    "Flying Fish",
    "Octopy",
    "Hermit Crab",
    "Pangxie",
    "Great Humphead",
    "Kingu",
    "Crocman",
    "Cobra",
    "Mummy",
    "Sorceress",
    "Cat Mummy",
    "Necromancer",
    "Anubis",
    "Ammit",
    "Apep",
    "Anubis II",
    "Osiris",
    "UFO",
    "Alien",
    "Yeti",
    "Yeti King",
    "Yeti Queen",
    "Lahamu",
    "Proto Shopkeeper",
    "Olmite",
    "Lamassu",
    "Tiamat",
    "Tadpole",
    "Frog",
    "Fire Frog",
    "Goliath Frog",
    "Grub",
    "Giant Fly",
    "Hundun",
    "Eggplant Minister",
    "Eggplup",
    "Celestial Jelly",
    "Scorpion",
    "Bee",
    "Queen Bee",
    "Scarab",
    "Golden Monkey",
    "Leprechaun",
    "Monty",
    "Percy",
    "Poochi",
    "Ghist",
    "Ghost",
    "Cave Turkey",
    "Rock Dog",
    "Axolotl",
    "Qilin",
    "Mech Rider",
];

/// The 38 people entries, in save-file order.
///
/// The first [`CHARACTER_COUNT`] are the playable characters, in the
/// same order as the bits of the unlock mask. The rest are
/// shopkeepers, quest givers and other NPCs.
pub const PEOPLE: [&str; 38] = [
    "Ana Spelunky",
    "Margaret Tunnel",
    "Colin Northward",
    "Roffy D. Sloth",
    "Alto Singh",
    "Liz Mutton",
    "Nekka the Eagle",
    "LISE Project",
    "Coco Von Diamonds",
    "Manfred Tunnel",
    "Little Jay",
    "Tina Flan",
    "Valerie Crump",
    "Au",
    "Demi Von Diamonds",
    "Pilot",
    "Princess Airyn",
    "Dirk Yamaoka",
    "Guy Spelunky",
    "Classic Guy",
    "Terra Tunnel",
    "Hired Hand",
    "Eggplant Child",
    "Shopkeeper",
    "Tun",
    "Yang",
    "Madame Tusk",
    "Tusk's Bodyguard",
    "Waddler",
    "Caveman Shopkeeper",
    "Ghist Shopkeeper",
    "Van Horsing",
    "Parsley",
    "Parsnip",
    "Parmesan",
    "Sparrow",
    "Beg",
    "Eggplant King",
];

/// The 54 journal items, in save-file order.
pub const ITEMS: [&str; 54] = [
    "Rope Pile",
    "Bomb Bag",
    "Bomb Box",
    "Paste",
    "Spectacles",
    "Climbing Gloves",
    "Pitcher's Mitt",
    "Spring Shoes",
    "Spike Shoes",
    "Compass",
    "Alien Compass",
    "Parachute",
    "Udjat Eye",
    "Kapala",
    "Hedjet",
    "Crown",
    "Eggplant Crown",
    "The True Crown",
    "Ankh",
    "Tablet of Destiny",
    "Skeleton Key",
    "Royal Jelly",
    "Cape",
    "Vlad's Cape",
    "Jetpack",
    "Telepack",
    "Hoverpack",
    "Powerpack",
    "Webgun",
    "Shotgun",
    "Freeze Ray",
    "Clone Gun",
    "Crossbow",
    "Camera",
    "Teleporter",
    "Mattock",
    "Boomerang",
    "Machete",
    "Excalibur",
    "Broken Sword",
    "Plasma Cannon",
    "Scepter",
    "Hou Yi's Bow",
    "Arrow of Light",
    "Wooden Shield",
    "Metal Shield",
    "Idol",
    "The Tusk Idol",
    "Curse Pot",
    "Ushabti",
    "Eggplant",
    "Cooked Turkey",
    "Elixir",
    "Four-Leaf Clover",
];

/// The 24 journal traps, in save-file order.
pub const TRAPS: [&str; 24] = [
    "Spikes",
    "Arrow Trap",
    "Totem Trap",
    "Log Trap",
    "Spear Trap",
    "Thorny Vine",
    "Bear Trap",
    "Powder Box",
    "Falling Platform",
    "Spikeball",
    "Lion Trap",
    "Giant Clam",
    "Sliding Wall",
    "Crush Trap",
    "Giant Crush Trap",
    "Boulder",
    "Spring Trap",
    "Landmine",
    "Laser Trap",
    "Spark Trap",
    "Frog Trap",
    "Sticky Trap",
    "Bone Drop",
    "Egg Sac",
];

/// Number of playable characters, which is also the width of the unlock
/// bit mask and the length of the per-character death array.
pub const CHARACTER_COUNT: usize = 20;

/// Every bit the unlock mask actually uses. The field is a `u32` but only
/// the low 20 bits mean anything, so this masks off the rest before
/// counting or comparing.
pub const CHARACTER_MASK_ALL: u32 = (1 << CHARACTER_COUNT) - 1;

/// The playable characters, in unlock-bit order.
pub fn characters() -> &'static [&'static str] {
    &PEOPLE[..CHARACTER_COUNT]
}

/// Names for one journal category, indexed from zero.
pub fn names(category: JournalCategory) -> &'static [&'static str] {
    match category {
        JournalCategory::Places => &PLACES,
        JournalCategory::Bestiary => &BESTIARY,
        JournalCategory::People => &PEOPLE,
        JournalCategory::Items => &ITEMS,
        JournalCategory::Traps => &TRAPS,
    }
}

/// The name of one entry, or `None` if the index is past the end of the
/// category.
pub fn name(category: JournalCategory, index: usize) -> Option<&'static str> {
    names(category).get(index).copied()
}

/// The eight worlds the death histogram is broken down by.
///
/// These are worlds rather than themes: world 2 covers both Jungle and
/// Volcana, and the file does not record which branch a death happened in.
/// World 8 is the Cosmic Ocean, which the game also reports as area 8 in
/// the deepest-depth fields.
pub const DEATHCOUNT_WORLDS: [&str; 8] = [
    "Dwelling",
    "Jungle / Volcana",
    "Olmec's Lair",
    "Tide Pool / Temple",
    "Ice Caves",
    "Neo Babylon",
    "Sunken City",
    "Cosmic Ocean",
];

/// How many levels each world normally has, used to decide how much of a
/// death histogram row is worth showing.
///
/// This is a floor, not a limit. Real saves record the odd death past the
/// end of a world, so `SaveFile::deaths_in_world` extends the row when it
/// finds one rather than hiding it. The Cosmic Ocean genuinely does run to
/// level 99, which is why its row is long.
pub const WORLD_LEVEL_COUNTS: [usize; 8] = [4, 4, 1, 4, 1, 4, 4, 99];

/// The themes, indexed by the game's own 1-based theme id, so slot 0 is a
/// placeholder. Used by the last-run theme field and the per-theme
/// completion flags.
pub const THEMES: [&str; 20] = [
    "None",
    "Dwelling",
    "Jungle",
    "Volcana",
    "Olmec's Lair",
    "Tide Pool",
    "Temple of Anubis",
    "Ice Caves",
    "Neo Babylon",
    "Sunken City",
    "Cosmic Ocean",
    "City of Gold",
    "Duat",
    "Abzu",
    "Tiamat's Throne",
    "Eggplant World",
    "Hundun's Hideaway",
    "Base Camp",
    "Arena",
    "Unknown",
];

/// The three pets, in the order their rescue counts are stored.
pub const PETS: [&str; 3] = ["Monty", "Percy", "Poochi"];

/// Terra's quest / shortcut progress, indexed by the stored value.
pub const SHORTCUT_STATES: [&str; 11] = [
    "Never met Terra",
    "Met Terra",
    "1-4 shortcut: gave $2,000",
    "1-4 shortcut: gave 1 bomb",
    "1-4 shortcut: gave $10,000",
    "3-1 shortcut: gave 1 rope",
    "3-1 shortcut: gave a weapon",
    "3-1 shortcut: gave a mount",
    "5-1 shortcut: gave $50,000",
    "5-1 shortcut: gave a hired hand",
    "5-1 shortcut: gave the golden key",
];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::JournalCategory;

    /// Each name table has to be exactly as long as the array of flags it
    /// describes, or every index past the mismatch labels the wrong entry.
    #[test]
    fn name_tables_match_save_arrays() {
        for category in JournalCategory::ALL {
            assert_eq!(
                names(category).len(),
                category.count(),
                "{} name table is the wrong length",
                category.as_str()
            );
        }
    }

    #[test]
    fn character_table_is_a_prefix_of_people() {
        assert_eq!(characters().len(), CHARACTER_COUNT);
        assert_eq!(characters()[0], "Ana Spelunky");
        assert_eq!(CHARACTER_MASK_ALL, 0x000f_ffff);
    }

    #[test]
    fn world_tables_agree() {
        assert_eq!(DEATHCOUNT_WORLDS.len(), WORLD_LEVEL_COUNTS.len());
    }
}
