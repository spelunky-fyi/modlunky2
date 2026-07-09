// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn menu_basic_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "MenuBasicSheet".into(),
        sprite_sheet_path: "Data/Textures/menu_basic.png".into(),
        chunk_size: 64,
        chunk_map: chunks(&[
            ("basic_monty", 16.0, 7.0, 17.0, 8.0),
            ("basic_percy", 17.0, 7.0, 18.0, 8.0),
            ("basic_poochi", 18.0, 7.0, 19.0, 8.0),
        ]),
    }
}

pub fn pet_heads_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "PetHeadsSheet".into(),
        sprite_sheet_path: "static/images/pet_heads.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("pet_head_monty", 0.0, 0.0, 1.0, 1.0),
            ("pet_head_percy", 1.0, 0.0, 2.0, 1.0),
            ("pet_head_poochi", 2.0, 0.0, 3.0, 1.0),
        ]),
    }
}
