//! LevelChance and MonsterChance directives. Both use the same shape:
//! `name` + a value that's either a single int or a 4-int list of per-difficulty
//! chances. They differ only in the whitelist and the directive prefix, so the
//! implementation is shared via a `ChanceKind` marker.

use std::io::Write;

use indexmap::IndexMap;
use once_cell::sync::Lazy;

use crate::error::{LevelError, Result};
use crate::utils::{DirectivePrefix, format_comment, parse_chance_values, split_comment, to_line};

pub const VALID_LEVEL_CHANCES: &[&str] = &[
    "arrowtrap_chance",
    "beehive_chance",
    "bigspeartrap_chance",
    "chain_blocks_chance",
    "crusher_trap_chance",
    "eggsac_chance",
    "jungle_spear_trap_chance",
    "lasertrap_chance",
    "leprechaun_chance",
    "liontrap_chance",
    "minister_chance",
    "pushblock_chance",
    "skulldrop_chance",
    "snap_trap_chance",
    "sparktrap_chance",
    "spike_ball_chance",
    "stickytrap_chance",
    "totemtrap_chance",
];

pub const VALID_MONSTER_CHANCES: &[&str] = &[
    "bat",
    "bee",
    "cat",
    "caveman",
    "cobra",
    "crabman",
    "critteranchovy",
    "critterbutterfly",
    "crittercrab",
    "critterdrone",
    "critterdungbeetle",
    "critterfirefly",
    "critterfish",
    "critterlocust",
    "critterpenguin",
    "critterslime",
    "crittersnail",
    "crocman",
    "female_jiangshi",
    "firebug",
    "firefrog",
    "fish",
    "frog",
    "giantfly",
    "giantspider",
    "hangspider",
    "hermitcrab",
    "hornedlizard",
    "imp",
    "jiangshi",
    "landmine",
    "lavamander",
    "leprechaun",
    "mantrap",
    "mole",
    "monkey",
    "mosquito",
    "necromancer",
    "octopus",
    "olmite",
    "robot",
    "snake",
    "sorceress",
    "spider",
    "springtrap",
    "tadpole",
    "tikiman",
    "ufo",
    "vampire",
    "witchdoctor",
    "yeti",
];

static LEVEL_NAME_PADDING: Lazy<usize> = Lazy::new(|| max_len(VALID_LEVEL_CHANCES) + 4);
static MONSTER_NAME_PADDING: Lazy<usize> = Lazy::new(|| max_len(VALID_MONSTER_CHANCES) + 4);

fn max_len(names: &[&str]) -> usize {
    names.iter().map(|s| s.len()).max().unwrap_or(0)
}

const VALUE_PADDING: usize = 28;

#[derive(Debug, Clone, PartialEq)]
pub enum ChanceValue {
    Single(i64),
    PerDifficulty([i64; 4]),
}

impl ChanceValue {
    fn parse_raw(name: &str, raw: &str) -> Result<Self> {
        let values = parse_chance_values(raw).map_err(|e| LevelError::InvalidValue {
            name: name.to_string(),
            value: raw.to_string(),
            reason: e.to_string(),
        })?;
        match values.len() {
            1 => Ok(Self::Single(values[0])),
            4 => Ok(Self::PerDifficulty([
                values[0], values[1], values[2], values[3],
            ])),
            n => Err(LevelError::BadChanceLen {
                name: name.to_string(),
                count: n,
            }),
        }
    }

    fn to_str(&self) -> String {
        match self {
            Self::Single(v) => v.to_string(),
            Self::PerDifficulty(vs) => vs.iter().map(i64::to_string).collect::<Vec<_>>().join(", "),
        }
    }
}

macro_rules! chance_type {
    (
        $Struct:ident, $Container:ident,
        $prefix_variant:ident,
        $padding:ident
    ) => {
        #[derive(Debug, Clone)]
        pub struct $Struct {
            pub name: String,
            pub value: ChanceValue,
            pub comment: Option<String>,
        }

        impl $Struct {
            pub const PREFIX: &'static str = DirectivePrefix::$prefix_variant.as_str();

            pub fn parse(line: &str) -> Result<Self> {
                let (rest, comment) = split_comment(line);
                let mut split = rest.splitn(2, char::is_whitespace);
                let directive = split
                    .next()
                    .ok_or_else(|| LevelError::MissingName(line.to_string()))?;
                let value_str = split
                    .next()
                    .ok_or_else(|| LevelError::MissingValue(rest.clone()))?
                    .trim();

                let name = directive
                    .strip_prefix(Self::PREFIX)
                    .ok_or_else(|| LevelError::MissingName(line.to_string()))?;
                if name.is_empty() {
                    return Err(LevelError::MissingName(line.to_string()));
                }

                let value = ChanceValue::parse_raw(name, value_str)?;
                Ok(Self {
                    name: name.to_string(),
                    value,
                    comment,
                })
            }

            pub fn to_line(&self) -> String {
                to_line(
                    Self::PREFIX,
                    &self.name,
                    *$padding,
                    &self.value.to_str(),
                    VALUE_PADDING,
                    self.comment.as_deref(),
                )
            }
        }

        #[derive(Debug, Default, Clone)]
        pub struct $Container {
            inner: IndexMap<String, $Struct>,
            pub comment: Option<String>,
        }

        impl $Container {
            pub fn new() -> Self {
                Self::default()
            }

            pub fn all(&self) -> impl Iterator<Item = &$Struct> {
                self.inner.values()
            }

            pub fn get(&self, name: &str) -> Option<&$Struct> {
                self.inner.get(name)
            }

            pub fn set(&mut self, obj: $Struct) {
                self.inner.insert(obj.name.clone(), obj);
            }

            pub fn is_empty(&self) -> bool {
                self.inner.is_empty()
            }

            pub fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
                writer.write_all(format_comment(self.comment.as_deref()).as_bytes())?;
                for obj in self.inner.values() {
                    writer.write_all(obj.to_line().as_bytes())?;
                }
                writer.write_all(b"\n")?;
                Ok(())
            }
        }
    };
}

chance_type!(LevelChance, LevelChances, LevelChance, LEVEL_NAME_PADDING);
chance_type!(
    MonsterChance,
    MonsterChances,
    MonsterChance,
    MONSTER_NAME_PADDING
);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_single_level_chance() {
        let c = LevelChance::parse("\\%arrowtrap_chance          35").unwrap();
        assert_eq!(c.name, "arrowtrap_chance");
        assert_eq!(c.value, ChanceValue::Single(35));
        assert_eq!(c.comment, None);
    }

    #[test]
    fn parse_multi_level_chance() {
        let c = LevelChance::parse("\\%arrowtrap_chance 1, 2, 3, 4").unwrap();
        assert_eq!(c.value, ChanceValue::PerDifficulty([1, 2, 3, 4]));
    }

    #[test]
    fn parse_monster_chance() {
        let c = MonsterChance::parse("\\+frog          30").unwrap();
        assert_eq!(c.name, "frog");
        assert_eq!(c.value, ChanceValue::Single(30));
    }

    #[test]
    fn bad_chance_length_errors() {
        let err = LevelChance::parse("\\%arrowtrap_chance 1, 2, 3");
        assert!(matches!(err, Err(LevelError::BadChanceLen { .. })));
    }

    #[test]
    fn parse_non_int_value_wraps_as_invalid_value() {
        // A parse failure inside parse_chance_values must bubble up as
        // LevelError::InvalidValue rather than a bare ParseIntError so
        // callers see a directive-scoped error message.
        let err = LevelChance::parse("\\%arrowtrap_chance 1, 2, x");
        assert!(
            matches!(err, Err(LevelError::InvalidValue { .. })),
            "got {err:?}"
        );
    }

    #[test]
    fn parse_trailing_comma_wraps_as_invalid_value() {
        let err = LevelChance::parse("\\%arrowtrap_chance 1, 2, 3,");
        assert!(
            matches!(err, Err(LevelError::InvalidValue { .. })),
            "got {err:?}"
        );
    }

    #[test]
    fn writer_emits_padded_comma_join() {
        let c = LevelChance {
            name: "arrowtrap_chance".into(),
            value: ChanceValue::PerDifficulty([2, 4, 6, 8]),
            comment: None,
        };
        assert!(c.to_line().contains("2, 4, 6, 8"));
    }
}
