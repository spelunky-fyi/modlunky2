// Hand-maintained loader. Unlike its siblings in this directory, this one
// is not covered by the sprite-data code generator, so keep it in sync
// manually when the sprite sheet layout changes.

use crate::LoaderConfig;
use crate::data::chunks;

/// `DecoExtraSheet`. Only carries `shopkeeper_vat`; sprite sheet is
/// `Data/Textures/deco_extra.png` at 128px per chunk.
pub fn deco_extra_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "DecoExtraSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_extra.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("shopkeeper_vat", 4.0, 5.0, 8.0, 11.0)]),
    }
}
