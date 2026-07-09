// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{MergerConfig, OriginEntry};

pub fn snake() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/snake.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_SNAKE_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_SNAKE_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_SNAKE_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_SNAKE_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_SNAKE_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_SNAKE_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_SNAKE_19_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_SNAKE_19_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_SNAKE_19_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_SNAKE_19_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_SNAKE_19_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_SNAKE_19_5", 3.0, 2.0, 4.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_snake", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn bat() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/bat.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_BAT_9_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_BAT_9_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_BAT_9_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_BAT_9_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_BAT_9_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_BAT_9_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_BAT_41_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_BAT_41_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_BAT_41_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_BAT_41_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_BAT_41_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_BAT_41_5", 3.0, 2.0, 4.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_bat", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn fly() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/fly.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Basic1".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_ITEM_FLY_41_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_ITEM_FLY_41_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_ITEM_FLY_41_2", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_ITEM_FLY_41_3", 1.0, 1.0, 2.0, 2.0),
            ]),
        }],
    }
}

pub fn skeleton() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/skeleton.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_SKELETON_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_SKELETON_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_SKELETON_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_SKELETON_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_SKELETON_2_3", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_SKELETON_2_4", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_SKELETON_2_5", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_SKELETON_2_6", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_SKELETON_2_7", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_SKELETON_2_8", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_SKELETON_3_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_SKELETON_3_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_SKELETON_3_2", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_SKELETON_3_3", 1.0, 3.0, 2.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_skeleton", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn spider() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/spider.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_SPIDER_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_SPIDER_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_SPIDER_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_SPIDER_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_SPIDER_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_SPIDER_3_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_SPIDER_3_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_SPIDER_3_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_SPIDER_5_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_SPIDER_5_1", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_SPIDER_5_2", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_SPIDER_5_3", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_SPIDER_14_0", 0.0, 3.0, 1.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_spider", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn ufo() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/ufo.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_UFO_5_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_UFO_5_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_UFO_5_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_UFO_5_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_UFO_5_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_UFO_5_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_UFO_5_6", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_UFO_5_7", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_UFO_13_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_UFO_19_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_UFO_19_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_UFO_19_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_UFO_19_3", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_UFO_19_4", 1.0, 3.0, 2.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_ufo", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn alien() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/alien.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_ALIEN_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_ALIEN_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_ALIEN_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_ALIEN_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_ALIEN_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_ALIEN_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_ALIEN_3_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_ALIEN_5_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_ALIEN_5_1", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_ALIEN_5_2", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_ALIEN_11_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_ALIEN_11_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_ALIEN_11_2", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_ALIEN_11_3", 1.0, 3.0, 2.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_alien", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn cobra() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/cobra.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_COBRA_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_COBRA_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_COBRA_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_COBRA_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_COBRA_2_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_COBRA_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_COBRA_19_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_COBRA_19_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_COBRA_19_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_COBRA_19_3", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_COBRA_19_4", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_COBRA_19_5", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_COBRA_45_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_COBRA_45_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_COBRA_45_2", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_COBRA_45_3", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_COBRA_45_4", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_COBRA_45_5", 2.0, 3.0, 3.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_cobra", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn scorpion() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/scorpion.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_SCORPION_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_SCORPION_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_SCORPION_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_SCORPION_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_SCORPION_0_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_SCORPION_2_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_SCORPION_2_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_SCORPION_2_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_SCORPION_2_3", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_SCORPION_2_4", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_SCORPION_3_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_SCORPION_3_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_SCORPION_3_2", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_SCORPION_3_3", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_SCORPION_12_0", 2.0, 3.0, 3.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_scorpion", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn golden_monkey() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/golden_monkey.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("additional_golden_monkey_0", 0.0, 0.0, 1.0, 1.0),
                    ("additional_golden_monkey_1", 1.0, 0.0, 2.0, 1.0),
                ]),
            },
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GOLDMONKEY_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_3_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_9_0", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_9_1", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_9_2", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_19_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_19_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_19_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_19_3", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_GOLDMONKEY_19_4", 1.0, 2.0, 2.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_golden_monkey", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn bee() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/bee.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_BEE_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_BEE_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_BEE_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_BEE_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_BEE_2_3", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_BEE_2_4", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_BEE_2_5", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_BEE_14_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_BEE_41_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_BEE_41_1", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_BEE_41_2", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_BEE_41_3", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_BEE_41_4", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_BEE_41_5", 1.0, 3.0, 2.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_bee", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn magmar() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/magmar.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MAGMAMAN_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_2_0", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_2_1", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_2_2", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_2_3", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_2_4", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_2_5", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_3_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_13_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_13_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_13_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_13_3", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_13_4", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_28_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_28_1", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_MAGMAMAN_28_2", 3.0, 3.0, 4.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_magmar", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn vampire() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/vampire.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_VAMPIRE_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_4", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_VAMPIRE_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_VAMPIRE_3_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_VAMPIRE_9_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_VAMPIRE_9_1", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_VAMPIRE_9_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_VAMPIRE_9_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_VAMPIRE_9_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_VAMPIRE_9_5", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_VAMPIRE_12_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_VAMPIRE_15_0", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_VAMPIRE_16_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_VAMPIRE_17_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_VAMPIRE_18_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_VAMPIRE_41_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_VAMPIRE_41_1", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_VAMPIRE_41_2", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_VAMPIRE_41_3", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_VAMPIRE_41_4", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_VAMPIRE_41_5", 2.0, 4.0, 3.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_vampire", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn vlad() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/vlad.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_VLAD_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_VLAD_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_VLAD_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_VLAD_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_VLAD_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_VLAD_2_4", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_VLAD_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_VLAD_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_VLAD_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_VLAD_3_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_VLAD_9_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_VLAD_9_1", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_VLAD_9_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_VLAD_9_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_VLAD_9_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_VLAD_9_5", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_VLAD_12_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_VLAD_15_0", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_VLAD_16_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_VLAD_17_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_VLAD_18_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_VLAD_41_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_VLAD_41_1", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_VLAD_41_2", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_VLAD_41_3", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_VLAD_41_4", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_VLAD_41_5", 2.0, 4.0, 3.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_vlad", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "StickerSheet".into(),
                target_chunks: chunks(&[("sticker_vlad", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn leprechaun() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/leprechaun.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_LEPRECHAUN_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_6", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_2_7", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_12_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_15_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_16_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_17_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_18_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_19_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_19_1", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_19_2", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_LEPRECHAUN_19_3", 2.0, 3.0, 3.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_leprechaun", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn cave_man() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/cave_man.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Basic2".into(),
                target_chunks: chunks(&[
                    ("caveman_additional_0_1", 0.0, 0.0, 1.0, 1.0),
                    ("caveman_additional_0_2", 1.0, 0.0, 2.0, 1.0),
                    ("caveman_additional_0_3", 2.0, 0.0, 3.0, 1.0),
                    ("caveman_additional_0_4", 3.0, 0.0, 4.0, 1.0),
                    ("caveman_additional_0_5", 4.0, 0.0, 5.0, 1.0),
                    ("caveman_additional_0_6", 5.0, 0.0, 6.0, 1.0),
                    ("caveman_additional_0_7", 6.0, 0.0, 7.0, 1.0),
                    ("caveman_additional_0_8", 7.0, 0.0, 8.0, 1.0),
                    ("caveman_additional_1_1", 0.0, 1.0, 1.0, 2.0),
                    ("caveman_additional_1_2", 1.0, 1.0, 2.0, 2.0),
                ]),
            },
            OriginEntry {
                loader_name: "Basic2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_CAVEMAN_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_1_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_0", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_1", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_2", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_3", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_4", 6.0, 0.0, 7.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_5", 7.0, 0.0, 8.0, 1.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_6", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_7", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_8", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_2_9", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_12_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_14_0", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_15_0", 6.0, 1.0, 7.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_16_0", 7.0, 1.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_17_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_18_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_20_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_2", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_3", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_4", 6.0, 2.0, 7.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_5", 7.0, 2.0, 8.0, 3.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_6", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_7", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_8", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_9", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_10", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_11", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_12", 6.0, 3.0, 7.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_13", 7.0, 3.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_14", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_22_15", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_28_1", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_0", 3.0, 4.0, 4.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_1", 4.0, 4.0, 5.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_2", 5.0, 4.0, 6.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_3", 6.0, 4.0, 7.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_4", 7.0, 4.0, 8.0, 5.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_5", 0.0, 5.0, 1.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_6", 1.0, 5.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_32_7", 2.0, 5.0, 3.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_42_0", 3.0, 5.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_42_1", 4.0, 5.0, 5.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_42_2", 5.0, 5.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_42_3", 6.0, 5.0, 7.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_42_4", 7.0, 5.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_43_0", 0.0, 6.0, 1.0, 7.0),
                    ("ENT_TYPE_MONS_CAVEMAN_43_1", 1.0, 6.0, 2.0, 7.0),
                    ("ENT_TYPE_MONS_CAVEMAN_43_2", 2.0, 6.0, 3.0, 7.0),
                    ("ENT_TYPE_MONS_CAVEMAN_43_3", 3.0, 6.0, 4.0, 7.0),
                    ("ENT_TYPE_MONS_CAVEMAN_43_4", 4.0, 6.0, 5.0, 7.0),
                    ("ENT_TYPE_MONS_CAVEMAN_45_0", 5.0, 6.0, 6.0, 7.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_cave_man", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "StickerSheet".into(),
                target_chunks: chunks(&[("sticker_cave_man", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn robot() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/robot.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_ROBOT_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_ROBOT_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_ROBOT_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_ROBOT_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_ROBOT_19_0", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_ROBOT_19_1", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_ROBOT_19_2", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_ROBOT_19_3", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_ROBOT_22_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_ROBOT_22_1", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_ROBOT_22_2", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_ROBOT_22_3", 3.0, 2.0, 4.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_robot", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn imp() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/imp.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_IMP_34_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_IMP_34_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_IMP_34_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_IMP_34_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_IMP_34_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_IMP_34_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_IMP_41_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_IMP_41_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_IMP_41_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_IMP_41_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_IMP_41_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_IMP_41_5", 3.0, 2.0, 4.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_imp", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn tiki_man() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/tiki_man.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_TIKIMAN_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_6", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_TIKIMAN_2_7", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_TIKIMAN_11_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_TIKIMAN_11_1", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_TIKIMAN_11_2", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_TIKIMAN_11_3", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_TIKIMAN_11_4", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_TIKIMAN_12_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_TIKIMAN_15_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_TIKIMAN_16_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_TIKIMAN_17_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_TIKIMAN_18_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_TIKIMAN_43_0", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_TIKIMAN_43_1", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_TIKIMAN_43_2", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_TIKIMAN_43_3", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_TIKIMAN_43_4", 3.0, 4.0, 4.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_tiki_man", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn man_trap() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/man_trap.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MANTRAP_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_6", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_MANTRAP_2_7", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_MANTRAP_12_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_3", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_4", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_5", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_MANTRAP_19_6", 3.0, 3.0, 4.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_man_trap", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn fire_bug() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/fire_bug.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_FIREBUG_7_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_8_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_8_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_8_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_8_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_8_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_19_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_19_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_19_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_19_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_19_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_27_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_27_2", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_FIREBUG_27_3", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_FIREBUG_27_4", 2.0, 3.0, 3.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_2_3", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_2_4", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_28_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_28_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_28_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_41_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_41_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_41_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_FIREBUG_UNCHAINED_41_3", 0.0, 3.0, 1.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_fire_bug", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn mole() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/mole.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MOLE_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_MOLE_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_MOLE_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_MOLE_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_MOLE_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_MOLE_2_4", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_MOLE_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_MOLE_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MOLE_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_MOLE_3_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_MOLE_3_1", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_MOLE_3_2", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_MOLE_12_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_MOLE_15_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_MOLE_16_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_MOLE_17_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_MOLE_18_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_MOLE_27_0", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_MOLE_27_1", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_MOLE_27_2", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_MOLE_27_3", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_MOLE_28_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_MOLE_28_1", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_MOLE_28_2", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_MOLE_28_3", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_MOLE_29_0", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_MOLE_29_1", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_MOLE_29_2", 3.0, 4.0, 4.0, 5.0),
                    ("ENT_TYPE_MONS_MOLE_29_3", 4.0, 4.0, 5.0, 5.0),
                    ("ENT_TYPE_MONS_MOLE_30_0", 5.0, 4.0, 6.0, 5.0),
                    ("ENT_TYPE_MONS_MOLE_30_1", 0.0, 5.0, 1.0, 6.0),
                    ("ENT_TYPE_MONS_MOLE_30_2", 1.0, 5.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_MOLE_30_3", 2.0, 5.0, 3.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_mole", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn witch_doctor() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/witch_doctor.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("witchdoctor_additional_0", 0.0, 0.0, 1.0, 1.0),
                    ("witchdoctor_additional_1", 1.0, 0.0, 2.0, 1.0),
                ]),
            },
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_WITCHDOCTOR_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_4", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_12_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_15_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_16_0", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_17_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_18_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_19_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_19_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_19_2", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_43_0", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_43_1", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_43_2", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_43_3", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_43_4", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_45_0", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_46_0", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_46_1", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_WITCHDOCTOR_46_2", 1.0, 4.0, 2.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_witch_doctor", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn horned_lizard() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/horned_lizard.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_HORNEDLIZARD_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_2_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_3_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_3_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_12_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_19_1", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_19_2", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_19_3", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_27_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_27_1", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_27_2", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_27_3", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_28_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_28_1", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_28_2", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_HORNEDLIZARD_28_3", 0.0, 4.0, 1.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_horned_lizard", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn witch_doctor_skull() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/witch_doctor_skull.png".into(),
        grid_hint_size: 8,
        origin_map: vec![OriginEntry {
            loader_name: "Monsters1".into(),
            target_chunks: chunks(&[
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_22_0", 0.0, 0.0, 1.0, 1.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_22_1", 1.0, 0.0, 2.0, 1.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_22_2", 2.0, 0.0, 3.0, 1.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_22_3", 0.0, 1.0, 1.0, 2.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_41_0", 1.0, 1.0, 2.0, 2.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_41_1", 2.0, 1.0, 3.0, 2.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_41_2", 0.0, 2.0, 1.0, 3.0),
                ("ENT_TYPE_MONS_WITCHDOCTORSKULL_41_3", 1.0, 2.0, 2.0, 3.0),
            ]),
        }],
    }
}

pub fn monkey() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/monkey.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MONKEY_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_MONKEY_3_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_MONKEY_8_0", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_MONKEY_19_0", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_MONKEY_19_1", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MONKEY_19_2", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_MONKEY_19_3", 0.0, 2.0, 1.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_monkey", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn hang_spider() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/hang_spider.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_HANGSPIDER_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_3_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_3_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_3_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_6_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_6_1", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_6_2", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_14_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_14_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_14_3", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_19_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_19_1", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_HANGSPIDER_19_2", 2.0, 3.0, 3.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_hang_spider", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn mosquito() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/mosquito.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MOSQUITO_19_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_MOSQUITO_41_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_MOSQUITO_41_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_MOSQUITO_41_2", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_MOSQUITO_41_3", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MOSQUITO_41_4", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_MOSQUITO_41_5", 0.0, 2.0, 1.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_mosquito", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn jiangshi() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/jiangshi.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[("jiangshi_additional", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_JIANGSHI_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_JIANGSHI_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_JIANGSHI_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_JIANGSHI_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_JIANGSHI_0_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_JIANGSHI_2_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_JIANGSHI_2_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_JIANGSHI_2_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_JIANGSHI_2_3", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_JIANGSHI_3_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_JIANGSHI_27_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_JIANGSHI_27_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_JIANGSHI_27_2", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_JIANGSHI_28_2", 1.0, 3.0, 2.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_jiangshi", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn hermit_crab() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/hermit_crab.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("hermit_crab_additional_1_1", 0.0, 0.0, 1.0, 1.0),
                    ("hermit_crab_additional_1_2", 1.0, 0.0, 2.0, 1.0),
                    ("hermit_crab_additional_1_3", 2.0, 0.0, 3.0, 1.0),
                    ("hermit_crab_additional_1_4", 3.0, 0.0, 4.0, 1.0),
                    ("hermit_crab_additional_1_5", 4.0, 0.0, 5.0, 1.0),
                    ("hermit_crab_additional_1_6", 5.0, 0.0, 6.0, 1.0),
                    ("hermit_crab_additional_2_1", 6.0, 0.0, 7.0, 1.0),
                    ("hermit_crab_additional_3_1", 0.0, 1.0, 1.0, 2.0),
                    ("hermit_crab_additional_3_2", 1.0, 1.0, 2.0, 2.0),
                    ("hermit_crab_additional_3_3", 2.0, 1.0, 3.0, 2.0),
                    ("hermit_crab_additional_3_4", 3.0, 1.0, 4.0, 2.0),
                ]),
            },
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_HERMITCRAB_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_2_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_2_5", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_7_0", 6.0, 0.0, 7.0, 1.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_0", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_1", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_2", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_3", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_4", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_5", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_6", 6.0, 1.0, 7.0, 2.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_8_7", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_9_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_12_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_14_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_14_1", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_14_2", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_14_3", 6.0, 2.0, 7.0, 3.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_15_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_16_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_17_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_18_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_19_0", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_19_1", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_19_2", 6.0, 3.0, 7.0, 4.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_19_3", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_19_4", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_25_0", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_25_1", 3.0, 4.0, 4.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_26_0", 4.0, 4.0, 5.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_26_1", 5.0, 4.0, 6.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_27_0", 6.0, 4.0, 7.0, 5.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_27_1", 0.0, 5.0, 1.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_27_2", 1.0, 5.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_27_3", 2.0, 5.0, 3.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_27_4", 3.0, 5.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_27_5", 4.0, 5.0, 5.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_28_1", 5.0, 5.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_28_2", 6.0, 5.0, 7.0, 6.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_28_3", 0.0, 6.0, 1.0, 7.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_28_4", 1.0, 6.0, 2.0, 7.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_33_0", 2.0, 6.0, 3.0, 7.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_33_1", 3.0, 6.0, 4.0, 7.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_33_2", 4.0, 6.0, 5.0, 7.0),
                    ("ENT_TYPE_MONS_HERMITCRAB_33_3", 5.0, 6.0, 6.0, 7.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_hermit_crab", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn flying_fish() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/flying_fish.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_FISH_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_FISH_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_FISH_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_FISH_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_FISH_2_3", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_FISH_2_4", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_FISH_2_5", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_FISH_2_6", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_FISH_5_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_FISH_5_1", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_FISH_5_2", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_FISH_5_3", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_FISH_5_4", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_FISH_5_5", 1.0, 3.0, 2.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_flying_fish", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn octopus() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/octopus.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_OCTOPUS_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_OCTOPUS_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_OCTOPUS_3_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_OCTOPUS_3_1", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_OCTOPUS_3_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_OCTOPUS_3_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_OCTOPUS_12_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_OCTOPUS_15_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_OCTOPUS_16_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_OCTOPUS_17_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_OCTOPUS_18_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_OCTOPUS_19_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_OCTOPUS_19_1", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_OCTOPUS_19_2", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_OCTOPUS_19_3", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_OCTOPUS_19_4", 1.0, 4.0, 2.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_octopy", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn female_jiangshi() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/female_jiangshi.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[("female_jiangshi_additional", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_0_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_2_0", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_2_1", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_2_2", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_2_3", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_2_4", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_3_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_27_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_27_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_27_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_28_2", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_45_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_45_1", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_45_2", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_45_3", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_FEMALE_JIANGSHI_45_4", 4.0, 3.0, 5.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_jiangshi_assassin", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn croc_man() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/croc_man.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_CROCMAN_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_6", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_CROCMAN_2_7", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_CROCMAN_12_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_CROCMAN_15_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_CROCMAN_16_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_CROCMAN_17_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_CROCMAN_18_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_CROCMAN_19_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_CROCMAN_19_1", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_CROCMAN_19_2", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_CROCMAN_19_3", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_CROCMAN_19_4", 3.0, 3.0, 4.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_croc_man", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn sorceress() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/sorceress.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_SORCERESS_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_4", 5.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_SORCERESS_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_SORCERESS_3_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_SORCERESS_3_1", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_SORCERESS_3_2", 5.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_SORCERESS_3_3", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_SORCERESS_3_4", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_SORCERESS_12_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_SORCERESS_15_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_SORCERESS_16_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_SORCERESS_17_0", 5.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_SORCERESS_18_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_1", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_2", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_3", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_4", 5.0, 3.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_5", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_SORCERESS_19_6", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_SORCERESS_41_0", 2.0, 4.0, 3.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_sorceress", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn cat_mummy() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/cat_mummy.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_CATMUMMY_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_CATMUMMY_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_CATMUMMY_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_CATMUMMY_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_CATMUMMY_0_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_0", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_1", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_2", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_3", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_4", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_5", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_6", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_CATMUMMY_32_7", 0.0, 3.0, 1.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_cat_mummy", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn necromancer() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/necromancer.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_NECROMANCER_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_5", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_6", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_7", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_NECROMANCER_2_8", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_NECROMANCER_12_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_NECROMANCER_15_0", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_NECROMANCER_16_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_NECROMANCER_17_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_NECROMANCER_18_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_NECROMANCER_19_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_NECROMANCER_19_1", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_NECROMANCER_45_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_NECROMANCER_45_1", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_NECROMANCER_46_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_NECROMANCER_46_1", 4.0, 3.0, 5.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_necromancer", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn yeti() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/yeti.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_YETI_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_YETI_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_YETI_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_YETI_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_YETI_2_3", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_YETI_2_4", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_YETI_2_5", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_YETI_2_6", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_YETI_2_7", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_YETI_5_0", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_YETI_5_1", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_YETI_5_2", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_YETI_5_3", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_YETI_5_4", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_YETI_12_0", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_YETI_15_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_YETI_16_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_YETI_17_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_YETI_18_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_YETI_19_0", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_YETI_19_1", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_YETI_19_2", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_YETI_19_3", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_YETI_19_4", 3.0, 4.0, 4.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_yeti", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn proto_shopkeeper() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/proto_shopkeeper.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_0_4", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_2_0", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_2_1", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_2_2", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_2_3", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_2_4", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_2_5", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_10_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_10_1", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_10_2", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_10_3", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_10_4", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_12_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_15_0", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_16_0", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_17_0", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_18_0", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_45_0", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_45_1", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_PROTOSHOPKEEPER_45_2", 3.0, 4.0, 4.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_proto_shopkeeper", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn jumpdog() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/jumpdog.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_JUMPDOG_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_2", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_3", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_4", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_5", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_6", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_JUMPDOG_2_7", 2.0, 2.0, 3.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_egg_plup", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn tadpole() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/tadpole.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_TADPOLE_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_TADPOLE_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_TADPOLE_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_TADPOLE_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_TADPOLE_2_3", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_TADPOLE_2_4", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_TADPOLE_5_0", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_TADPOLE_5_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_TADPOLE_5_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_TADPOLE_5_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_TADPOLE_5_4", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_TADPOLE_5_5", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_TADPOLE_13_0", 0.0, 3.0, 1.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_tadpole", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn olmite_naked() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/olmite_naked.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_OLMITE_NAKED_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_2_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_2_1", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_2_2", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_2_3", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_2_4", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_2_5", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_3_0", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_3_1", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_12_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_15_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_16_0", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_17_0", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_18_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_OLMITE_NAKED_19_0", 2.0, 3.0, 3.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_olmite", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn grub() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/grub.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GRUB_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_GRUB_3_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_GRUB_8_0", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_GRUB_32_1", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_GRUB_32_2", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_GRUB_32_3", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_GRUB_32_4", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_GRUB_41_1", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_GRUB_41_2", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_GRUB_41_3", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_GRUB_41_4", 2.0, 2.0, 3.0, 3.0),
                ]),
            },
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_ITEM_EGGSAC_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_ITEM_EGGSAC_13_0", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_ITEM_EGGSAC_19_0", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_ITEM_EGGSAC_19_1", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_ITEM_EGGSAC_19_2", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_ITEM_EGGSAC_19_3", 2.0, 1.0, 3.0, 2.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_grub", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn frog() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/frog.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_FROG_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_FROG_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_FROG_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_FROG_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_FROG_2_0", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_FROG_2_1", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_FROG_2_2", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_FROG_2_3", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_FROG_2_4", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_FROG_2_5", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_FROG_2_6", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_FROG_3_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_FROG_27_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_FROG_27_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_FROG_27_2", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_FROG_27_3", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_FROG_28_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_FROG_28_1", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_FROG_28_2", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_FROG_28_3", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_FROG_39_0", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_FROG_40_0", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_FROG_40_1", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_FROG_40_2", 3.0, 4.0, 4.0, 5.0),
                    ("ENT_TYPE_MONS_FROG_40_3", 4.0, 4.0, 5.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_frog", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn fire_frog() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/Monsters/fire_frog.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("firefrog_dead_0", 0.0, 0.0, 1.0, 1.0),
                    ("firefrog_dead_1", 1.0, 0.0, 2.0, 1.0),
                ]),
            },
            OriginEntry {
                loader_name: "Monsters3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_FIREFROG_0_0", 0.0, 0.0, 1.0, 1.0),
                    ("ENT_TYPE_MONS_FIREFROG_0_1", 1.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_FIREFROG_0_2", 2.0, 0.0, 3.0, 1.0),
                    ("ENT_TYPE_MONS_FIREFROG_0_3", 3.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_0", 4.0, 0.0, 5.0, 1.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_1", 0.0, 1.0, 1.0, 2.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_2", 1.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_3", 2.0, 1.0, 3.0, 2.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_4", 3.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_5", 4.0, 1.0, 5.0, 2.0),
                    ("ENT_TYPE_MONS_FIREFROG_2_6", 0.0, 2.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_FIREFROG_3_0", 1.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_FIREFROG_27_0", 2.0, 2.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_FIREFROG_27_1", 3.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_FIREFROG_27_2", 4.0, 2.0, 5.0, 3.0),
                    ("ENT_TYPE_MONS_FIREFROG_27_3", 0.0, 3.0, 1.0, 4.0),
                    ("ENT_TYPE_MONS_FIREFROG_28_0", 1.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_FIREFROG_28_1", 2.0, 3.0, 3.0, 4.0),
                    ("ENT_TYPE_MONS_FIREFROG_28_2", 3.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_FIREFROG_28_3", 4.0, 3.0, 5.0, 4.0),
                    ("ENT_TYPE_MONS_FIREFROG_39_0", 0.0, 4.0, 1.0, 5.0),
                    ("ENT_TYPE_MONS_FIREFROG_40_0", 1.0, 4.0, 2.0, 5.0),
                    ("ENT_TYPE_MONS_FIREFROG_40_1", 2.0, 4.0, 3.0, 5.0),
                    ("ENT_TYPE_MONS_FIREFROG_40_2", 3.0, 4.0, 4.0, 5.0),
                    ("ENT_TYPE_MONS_FIREFROG_40_3", 4.0, 4.0, 5.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalMonsterSheet".into(),
                target_chunks: chunks(&[("journal_fire_frog", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}
