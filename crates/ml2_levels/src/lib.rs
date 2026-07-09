//! Spelunky 2 `.lvl` file parser and serializer.
//!
//! The `.lvl` format is a plain-text, cp1252-encoded configuration file
//! composed of six section kinds keyed by a two-character `\X` prefix:
//! level settings (`\-`), tile codes (`\?`), level chances (`\%`), monster
//! chances (`\+`), templates (`\.`), and template settings (`\!`, appearing
//! inside a template's room). Comments start with `//` and are preserved
//! at three levels of granularity: file, section, and per-directive.
//!
//! Byte-for-byte round-trip fidelity against the game's own `.lvl`
//! files is a test invariant.

mod chances;
pub mod dmpreview;
mod error;
mod file;
pub mod mosaic;
mod settings;
mod templates;
mod tilecodes;
mod utils;

pub use chances::{
    ChanceValue, LevelChance, LevelChances, MonsterChance, MonsterChances, VALID_LEVEL_CHANCES,
    VALID_MONSTER_CHANCES,
};
pub use error::{LevelError, Result};
pub use file::LevelFile;
pub use settings::{LevelSetting, LevelSettingValue, LevelSettings, VALID_LEVEL_SETTINGS};
pub use templates::{LevelTemplate, LevelTemplates, Room, TemplateSetting};
pub use tilecodes::{
    TileCode, TileCodes, VALID_SHORT_CODES, VALID_TILE_CODES, percent_delim, usable_short_codes,
};
pub use utils::{DirectivePrefix, SECTION_COMMENT};
