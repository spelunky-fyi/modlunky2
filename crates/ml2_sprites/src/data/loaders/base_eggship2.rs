// Hand-maintained loader. Unlike its siblings in this directory, this one
// is not covered by the sprite-data code generator, so keep it in sync
// manually when the sprite sheet layout changes.

use crate::LoaderConfig;
use crate::data::chunks;

/// `EggShip2Sheet`. Only carries `olmecship`; sprite sheet is
/// `Data/Textures/base_eggship2.png` at 128px per chunk.
pub fn egg_ship2_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "EggShip2Sheet".into(),
        sprite_sheet_path: "Data/Textures/base_eggship2.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("olmecship", 0.0, 0.0, 3.0, 3.0)]),
    }
}
