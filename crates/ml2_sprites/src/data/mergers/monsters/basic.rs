// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{MergerConfig, OriginEntry};

pub fn critter_blue_crab_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/blue_crab.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters2".into(),
            target_chunks: chunks(&[
                ("blue_crab_1_1", 0.0, 0.0, 1.0, 1.0),
                ("blue_crab_1_2", 1.0, 0.0, 2.0, 1.0),
                ("blue_crab_1_3", 2.0, 0.0, 3.0, 1.0),
                ("blue_crab_2_1", 0.0, 1.0, 1.0, 2.0),
                ("blue_crab_2_2", 1.0, 1.0, 2.0, 2.0),
                ("blue_crab_2_3", 2.0, 1.0, 3.0, 2.0),
            ]),
        }],
    }
}

pub fn olmited_armored_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/olmite_armored.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters3".into(),
            target_chunks: chunks(&[
                ("olmite_body_armored_1_1", 0.0, 0.0, 1.0, 1.0),
                ("olmite_body_armored_1_2", 1.0, 0.0, 2.0, 1.0),
                ("olmite_body_armored_1_3", 2.0, 0.0, 3.0, 1.0),
                ("olmite_body_armored_1_4", 3.0, 0.0, 4.0, 1.0),
                ("olmite_body_armored_2_1", 0.0, 1.0, 1.0, 2.0),
                ("olmite_body_armored_2_2", 1.0, 1.0, 2.0, 2.0),
                ("olmite_body_armored_2_3", 2.0, 1.0, 3.0, 2.0),
                ("olmite_body_armored_2_4", 3.0, 1.0, 4.0, 2.0),
                ("olmite_body_armored_3_1", 0.0, 2.0, 1.0, 3.0),
                ("olmite_body_armored_3_2", 1.0, 2.0, 2.0, 3.0),
            ]),
        }],
    }
}

pub fn olmite_helmet_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/olmite_helmet.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters3".into(),
            target_chunks: chunks(&[
                ("olmite_helmet_1_1", 0.0, 0.0, 1.0, 1.0),
                ("olmite_helmet_1_2", 1.0, 0.0, 2.0, 1.0),
                ("olmite_helmet_1_3", 2.0, 0.0, 3.0, 1.0),
                ("olmite_helmet_1_4", 3.0, 0.0, 4.0, 1.0),
                ("olmite_helmet_2_1", 0.0, 1.0, 1.0, 2.0),
                ("olmite_helmet_2_2", 1.0, 1.0, 2.0, 2.0),
                ("olmite_helmet_2_3", 2.0, 1.0, 3.0, 2.0),
                ("olmite_helmet_2_4", 3.0, 1.0, 4.0, 2.0),
                ("olmite_helmet_3_1", 0.0, 2.0, 1.0, 3.0),
                ("olmite_helmet_3_2", 1.0, 2.0, 2.0, 3.0),
                ("olmite_helmet_4_1", 2.0, 2.0, 3.0, 3.0),
                ("olmite_helmet_4_2", 3.0, 2.0, 4.0, 3.0),
                ("olmite_helmet_5_1", 0.0, 3.0, 1.0, 4.0),
                ("olmite_helmet_5_2", 1.0, 3.0, 2.0, 4.0),
                ("olmite_helmet_5_3", 2.0, 3.0, 3.0, 4.0),
                ("olmite_helmet_5_4", 3.0, 3.0, 4.0, 4.0),
                ("olmite_helmet_6_1", 0.0, 4.0, 1.0, 5.0),
            ]),
        }],
    }
}
