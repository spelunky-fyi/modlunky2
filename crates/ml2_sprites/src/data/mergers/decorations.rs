// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{MergerConfig, OriginEntry};

pub fn udjat_wall_heads() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Decorations/udjat_wall_heads.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "CaveDecoSheet".into(),
            target_chunks: chunks(&[("udjat_wall_heads", 0.0, 0.0, 4.0, 4.0)]),
        }],
    }
}
