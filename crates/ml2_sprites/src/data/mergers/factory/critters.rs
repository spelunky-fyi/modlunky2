// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{MergerConfig, OriginEntry};

pub fn birdies() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/birdies.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Basic3".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_FX_BIRDIES_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_FX_BIRDIES_0_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_FX_BIRDIES_0_2", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_FX_BIRDIES_0_3", 3.0, 0.0, 4.0, 1.0),
                ("ENT_TYPE_FX_BIRDIES_0_4", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_FX_BIRDIES_0_5", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_FX_BIRDIES_0_6", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_FX_BIRDIES_0_7", 3.0, 1.0, 4.0, 2.0),
                ("ENT_TYPE_FX_BIRDIES_0_8", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_FX_BIRDIES_0_9", 1.0, 2.0, 2.0, 3.0),
                ("ENT_TYPE_FX_BIRDIES_0_10", 2.0, 2.0, 3.0, 3.0),
                ("ENT_TYPE_FX_BIRDIES_0_11", 3.0, 2.0, 4.0, 3.0),
            ]),
        }],
    }
}

pub fn snail() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/snail.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters1".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERSNAIL_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSNAIL_2_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSNAIL_2_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSNAIL_2_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSNAIL_2_3", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSNAIL_2_4", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSNAIL_2_5", 0.0, 2.0, 1.0, 3.0),
            ]),
        }],
    }
}

pub fn dung_beetle() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/dung_beetle.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters1".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_2_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_2_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_2_2", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_2_3", 3.0, 0.0, 4.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_5_0", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_5_1", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_5_2", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_5_3", 3.0, 1.0, 4.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_28_0", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_28_1", 1.0, 2.0, 2.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_28_2", 2.0, 2.0, 3.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERDUNGBEETLE_28_3", 3.0, 2.0, 4.0, 3.0),
            ]),
        }],
    }
}

pub fn butterfly() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/butterfly.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters1".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERBUTTERFLY_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERBUTTERFLY_41_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERBUTTERFLY_41_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERBUTTERFLY_41_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERBUTTERFLY_41_4", 1.0, 1.0, 2.0, 2.0),
            ]),
        }],
    }
}

pub fn crab() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/crab.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters2".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERCRAB_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERCRAB_2_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERCRAB_2_2", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERCRAB_2_3", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERCRAB_2_4", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERCRAB_2_5", 2.0, 1.0, 3.0, 2.0),
            ]),
        }],
    }
}

pub fn fish() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/fish.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters2".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERFISH_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFISH_2_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFISH_2_2", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFISH_2_3", 3.0, 0.0, 4.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_0", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_1", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_2", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_3", 3.0, 1.0, 4.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_4", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_5", 1.0, 2.0, 2.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERFISH_5_6", 2.0, 2.0, 3.0, 3.0),
            ]),
        }],
    }
}

pub fn anchovy() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/anchovy.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters2".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERANCHOVY_2_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERANCHOVY_2_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERANCHOVY_2_2", 0.0, 1.0, 1.0, 2.0),
            ]),
        }],
    }
}

pub fn locust() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/locust.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters2".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERLOCUST_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERLOCUST_41_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERLOCUST_41_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERLOCUST_41_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERLOCUST_41_3", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERLOCUST_41_4", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERLOCUST_41_5", 0.0, 2.0, 1.0, 3.0),
            ]),
        }],
    }
}

pub fn firefly() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/firefly.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters3".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERFIREFLY_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFIREFLY_41_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFIREFLY_41_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERFIREFLY_41_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERFIREFLY_41_3", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERFIREFLY_41_4", 2.0, 1.0, 3.0, 2.0),
            ]),
        }],
    }
}

pub fn penguin() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/penguin.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters3".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERPENGUIN_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_2_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_2_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_2_2", 3.0, 0.0, 4.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_2_3", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_2_4", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_2_5", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_5_0", 3.0, 1.0, 4.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_10_0", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_27_0", 1.0, 2.0, 2.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_27_1", 2.0, 2.0, 3.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERPENGUIN_27_2", 3.0, 2.0, 4.0, 3.0),
            ]),
        }],
    }
}

pub fn drone() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/drone.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters3".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERDRONE_2_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERDRONE_2_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERDRONE_2_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERDRONE_2_3", 1.0, 1.0, 2.0, 2.0),
            ]),
        }],
    }
}

pub fn slime() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Critters/slime.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters3".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_CRITTERSLIME_0_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_0_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_0_2", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_0_3", 3.0, 0.0, 4.0, 1.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_2_0", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_2_1", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_2_2", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_2_3", 3.0, 1.0, 4.0, 2.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_2_4", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_CRITTERSLIME_3_0", 1.0, 2.0, 2.0, 3.0),
            ]),
        }],
    }
}
