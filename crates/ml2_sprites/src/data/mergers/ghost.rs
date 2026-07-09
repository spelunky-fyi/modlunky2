// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{MergerConfig, OriginEntry};

pub fn ghist_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghist.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Ghost".into(),
                target_chunks: chunks(&[
                    ("ghist_angry_0_1", 0.0, 0.0, 1.0, 1.0),
                    ("ghist_angry_0_2", 1.0, 0.0, 2.0, 1.0),
                    ("ghist_angry_0_3", 2.0, 0.0, 3.0, 1.0),
                    ("ghist_angry_1_1", 0.0, 1.0, 1.0, 2.0),
                    ("ghist_angry_1_2", 1.0, 1.0, 2.0, 2.0),
                    ("ghist_angry_1_3", 2.0, 1.0, 3.0, 2.0),
                    ("ghist_angry_2_1", 0.0, 2.0, 1.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "Ghost".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GHIST_22_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_GHIST_22_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_GHIST_22_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_GHIST_41_0", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_GHIST_41_1", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_GHIST_41_2", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_GHIST_41_3", 0.0, 2.0, 1.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalPeopleSheet".into(),
                target_chunks: chunks(&[("journal_ghost_shopkeeper", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn ghost_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Ghost".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GHOST_12_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_GHOST_22_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_GHOST_22_1", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_GHOST_22_2", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_GHOST_41_0", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_GHOST_41_1", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_GHOST_41_2", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_GHOST_41_3", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_GHOST_41_4", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_GHOST_41_5", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_GHOST_41_6", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_GHOST_41_7", 6.0, 4.0, 8.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_ghost", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn ghost_medium_sad_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost_sad.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Ghost".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_12_0", 0.0, 0.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_22_0", 2.0, 0.0, 4.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_22_1", 4.0, 0.0, 6.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_22_2", 6.0, 0.0, 8.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_41_0", 0.0, 2.0, 2.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_41_1", 2.0, 2.0, 4.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_41_2", 4.0, 2.0, 6.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_41_3", 6.0, 2.0, 8.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_41_4", 0.0, 4.0, 2.0, 6.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_SAD_41_5", 2.0, 4.0, 4.0, 6.0),
            ]),
        }],
    }
}

pub fn ghost_medium_happy_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost_happy.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Ghost".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_12_0", 0.0, 0.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_22_0", 2.0, 0.0, 4.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_22_1", 4.0, 0.0, 6.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_22_2", 6.0, 0.0, 8.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_41_0", 0.0, 2.0, 2.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_41_1", 2.0, 2.0, 4.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_41_2", 4.0, 2.0, 6.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_41_3", 6.0, 2.0, 8.0, 4.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_41_4", 0.0, 4.0, 2.0, 6.0),
                ("ENT_TYPE_MONS_GHOST_MEDIUM_HAPPY_41_5", 2.0, 4.0, 4.0, 6.0),
            ]),
        }],
    }
}

pub fn ghost_small_sad_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost_small_sad.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Ghost".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_12_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_22_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_22_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_22_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_41_0", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_41_1", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_41_2", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_SAD_41_3", 1.0, 2.0, 2.0, 3.0),
            ]),
        }],
    }
}

pub fn ghost_small_happy_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost_small_happy.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Ghost".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_12_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_22_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_22_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_22_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_41_0", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_41_1", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_41_2", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_HAPPY_41_3", 1.0, 2.0, 2.0, 3.0),
            ]),
        }],
    }
}

pub fn ghost_small_surprised_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost_small_surprised.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Ghost".into(),
            target_chunks: chunks(&[
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_12_0",
                    0.0,
                    0.0,
                    1.0,
                    1.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_22_0",
                    1.0,
                    0.0,
                    2.0,
                    1.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_22_1",
                    2.0,
                    0.0,
                    3.0,
                    1.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_22_2",
                    0.0,
                    1.0,
                    1.0,
                    2.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_41_0",
                    1.0,
                    1.0,
                    2.0,
                    2.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_41_1",
                    2.0,
                    1.0,
                    3.0,
                    2.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_41_2",
                    0.0,
                    2.0,
                    1.0,
                    3.0,
                ),
                (
                    "ENT_TYPE_MONS_GHOST_SMALL_SURPRISED_41_3",
                    1.0,
                    2.0,
                    2.0,
                    3.0,
                ),
            ]),
        }],
    }
}

pub fn ghost_small_angry_sprite_merger() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Ghost/ghost_small_angry.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Ghost".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_12_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_22_0", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_22_1", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_22_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_41_0", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_41_1", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_41_2", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_GHOST_SMALL_ANGRY_41_3", 1.0, 2.0, 2.0, 3.0),
            ]),
        }],
    }
}
