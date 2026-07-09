// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn coffin_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CoffinSheet".into(),
        sprite_sheet_path: "Data/Textures/coffins.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("coffin", 0.0, 0.0, 2.0, 2.0)]),
    }
}
