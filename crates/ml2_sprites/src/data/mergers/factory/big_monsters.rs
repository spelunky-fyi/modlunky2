// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{MergerConfig, OriginEntry};

pub fn quill_back() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/quill_back.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_0_1", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_0_2", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_0_3", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_0_4", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_0_5", 10.0, 0.0, 12.0, 2.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_2_0", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_2_1", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_2_2", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_2_3", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_2_4", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_2_5", 10.0, 2.0, 12.0, 4.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_3_0", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_10_0", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_10_1", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_10_2", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_10_3", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_13_0", 10.0, 4.0, 12.0, 6.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_19_0", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_19_1", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_19_2", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_19_3", 6.0, 6.0, 8.0, 8.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_22_0", 8.0, 6.0, 10.0, 8.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_22_2", 10.0, 6.0, 12.0, 8.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_45_0", 0.0, 8.0, 2.0, 10.0),
                    ("ENT_TYPE_MONS_CAVEMAN_BOSS_45_1", 2.0, 8.0, 4.0, 10.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_quill_back", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "StickerSheet".into(),
                target_chunks: chunks(&[("sticker_quill_back", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}

pub fn giant_spider() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/giant_spider.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big1".into(),
                target_chunks: chunks(&[("giant_spider_additional", 0.0, 0.0, 2.0, 2.0)]),
            },
            OriginEntry {
                loader_name: "Big1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GIANTSPIDER_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_0_1", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_0_2", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_0_3", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_2_0", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_2_1", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_2_2", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_2_3", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_3_0", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_3_1", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_3_2", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_5_0", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_5_1", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_5_2", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_5_3", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_19_0", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_19_1", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_19_2", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_19_3", 6.0, 6.0, 8.0, 8.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_19_4", 8.0, 6.0, 10.0, 8.0),
                    ("ENT_TYPE_MONS_GIANTSPIDER_19_5", 0.0, 8.0, 2.0, 10.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_giant_spider", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn queen_bee() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/queen_bee.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big1".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_QUEENBEE_41_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_QUEENBEE_41_1", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_QUEENBEE_41_2", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_QUEENBEE_41_3", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_QUEENBEE_41_4", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_QUEENBEE_41_5", 4.0, 2.0, 6.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_queen_bee", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn mummy() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/mummy.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big2".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MUMMY_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MUMMY_2_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_MUMMY_2_1", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_MUMMY_2_2", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_MUMMY_2_3", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_MUMMY_2_4", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_MUMMY_2_5", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_MUMMY_19_0", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_MUMMY_19_1", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_MUMMY_19_2", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_MUMMY_19_3", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_MUMMY_19_4", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_MUMMY_19_5", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_MUMMY_19_6", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_MUMMY_19_7", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_MUMMY_19_8", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_MUMMY_19_9", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_MUMMY_19_10", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_MUMMY_19_11", 6.0, 6.0, 8.0, 8.0),
                    ("ENT_TYPE_MONS_MUMMY_22_0", 8.0, 6.0, 10.0, 8.0),
                    ("ENT_TYPE_MONS_MUMMY_22_1", 0.0, 8.0, 2.0, 10.0),
                    ("ENT_TYPE_MONS_MUMMY_22_2", 2.0, 8.0, 4.0, 10.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_mummy", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn lamassu() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/lamassu.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_LAMASSU_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_LAMASSU_2_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_LAMASSU_2_1", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_LAMASSU_2_2", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_LAMASSU_2_3", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_LAMASSU_2_4", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_LAMASSU_22_0", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_LAMASSU_22_1", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_LAMASSU_22_2", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_0", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_1", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_2", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_3", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_4", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_5", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_LAMASSU_41_6", 6.0, 6.0, 8.0, 8.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_lamassu", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn yeti_king() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/yeti_king.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_YETIKING_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_YETIKING_1_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_YETIKING_2_0", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_YETIKING_2_1", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_YETIKING_2_2", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_YETIKING_2_3", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_YETIKING_2_4", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_YETIKING_2_5", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_YETIKING_19_0", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_YETIKING_19_1", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_YETIKING_19_2", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_YETIKING_22_0", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_YETIKING_22_1", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_YETIKING_22_2", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_YETIKING_38_0", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_YETIKING_38_1", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_YETIKING_38_2", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_YETIKING_39_0", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_YETIKING_39_1", 6.0, 6.0, 8.0, 8.0),
                    ("ENT_TYPE_MONS_YETIKING_40_0", 8.0, 6.0, 10.0, 8.0),
                    ("ENT_TYPE_MONS_YETIKING_40_1", 0.0, 8.0, 2.0, 10.0),
                    ("ENT_TYPE_MONS_YETIKING_40_2", 2.0, 8.0, 4.0, 10.0),
                    ("ENT_TYPE_MONS_YETIKING_40_3", 4.0, 8.0, 6.0, 10.0),
                    ("ENT_TYPE_MONS_YETIKING_40_4", 6.0, 8.0, 8.0, 10.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_yeti_king", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn yeti_queen() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/yeti_queen.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big3".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_YETIQUEEN_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_1_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_2_0", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_2_1", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_2_2", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_2_3", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_2_4", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_2_5", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_3_0", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_19_0", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_19_1", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_19_2", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_22_0", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_22_1", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_22_2", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_39_0", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_39_1", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_39_2", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_40_0", 6.0, 6.0, 8.0, 8.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_40_1", 8.0, 6.0, 10.0, 8.0),
                    ("ENT_TYPE_MONS_YETIQUEEN_40_2", 0.0, 8.0, 2.0, 10.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_yeti_queen", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn crab_man() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/crab_man.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("crabman_additional", 0.0, 0.0, 2.0, 2.0),
                    ("crabman_open_claw", 2.0, 0.0, 3.0, 1.0),
                    ("crabman_closed_claw", 3.0, 0.0, 4.0, 1.0),
                    ("crabman_chain_claw", 2.0, 1.0, 3.0, 2.0),
                ]),
            },
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_CRABMAN_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_CRABMAN_2_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_CRABMAN_2_1", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_CRABMAN_2_2", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_CRABMAN_2_3", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_CRABMAN_2_4", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_CRABMAN_2_5", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_CRABMAN_19_0", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_CRABMAN_19_1", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_CRABMAN_19_2", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_CRABMAN_19_3", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_CRABMAN_22_0", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_CRABMAN_22_1", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_CRABMAN_22_2", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_CRABMAN_38_0", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_CRABMAN_38_1", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_CRABMAN_40_0", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_CRABMAN_40_1", 4.0, 6.0, 6.0, 8.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_panxie", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn lavamander() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/lavamander.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("lavamander_additional_1", 0.0, 0.0, 2.0, 2.0),
                    ("lavamander_additional_2", 2.0, 0.0, 4.0, 2.0),
                    ("lavamander_additional_3", 4.0, 0.0, 6.0, 2.0),
                ]),
            },
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_LAVAMANDER_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_1_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_3_0", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_3_1", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_19_0", 8.0, 0.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_19_1", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_19_2", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_19_3", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_22_0", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_22_1", 8.0, 2.0, 10.0, 4.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_22_2", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_31_0", 2.0, 4.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_31_1", 4.0, 4.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_31_2", 6.0, 4.0, 8.0, 6.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_45_0", 8.0, 4.0, 10.0, 6.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_45_1", 0.0, 6.0, 2.0, 8.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_45_2", 2.0, 6.0, 4.0, 8.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_45_3", 4.0, 6.0, 6.0, 8.0),
                    ("ENT_TYPE_MONS_LAVAMANDER_45_4", 6.0, 6.0, 8.0, 8.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_lavamander", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn giant_fly() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/giant_fly.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GIANTFLY_22_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTFLY_22_1", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTFLY_22_2", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTFLY_41_0", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTFLY_41_1", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTFLY_41_2", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTFLY_41_3", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTFLY_41_4", 2.0, 4.0, 4.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_0_0", 0.0, 0.0, 1.0, 2.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_2_0", 1.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_45_0", 2.0, 0.0, 3.0, 2.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_45_1", 3.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_45_2", 0.0, 2.0, 1.0, 4.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_45_3", 1.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_46_0", 2.0, 2.0, 3.0, 4.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_46_1", 3.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_46_2", 0.0, 4.0, 1.0, 6.0),
                    ("ENT_TYPE_ITEM_GIANTFLY_HEAD_46_3", 1.0, 4.0, 2.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_giant_fly", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn giant_clam() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/giant_clam.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_ITEM_GIANTCLAM_TOP_0_0", 0.0, 0.0, 3.0, 2.0),
                    ("ENT_TYPE_ITEM_GIANTCLAM_TOP_9_0", 3.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_ITEM_GIANTCLAM_TOP_27_0", 0.0, 2.0, 3.0, 4.0),
                    ("ENT_TYPE_ITEM_GIANTCLAM_TOP_27_1", 3.0, 2.0, 6.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "Big4".into(),
                target_chunks: chunks(&[(
                    "ENT_TYPE_ACTIVEFLOOR_GIANTCLAM_BASE_0_0",
                    0.0,
                    0.0,
                    3.0,
                    2.0,
                )]),
            },
            OriginEntry {
                loader_name: "JournalTrapSheet".into(),
                target_chunks: chunks(&[("journal_giant_clam", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}

pub fn ammit() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/ammit.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big5".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_AMMIT_0_0", 0.0, 0.0, 2.0, 1.0),
                    ("ENT_TYPE_MONS_AMMIT_2_0", 2.0, 0.0, 4.0, 1.0),
                    ("ENT_TYPE_MONS_AMMIT_2_1", 4.0, 0.0, 6.0, 1.0),
                    ("ENT_TYPE_MONS_AMMIT_2_2", 6.0, 0.0, 8.0, 1.0),
                    ("ENT_TYPE_MONS_AMMIT_2_3", 8.0, 0.0, 10.0, 1.0),
                    ("ENT_TYPE_MONS_AMMIT_2_4", 0.0, 1.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_AMMIT_2_5", 2.0, 1.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_AMMIT_2_6", 4.0, 1.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_AMMIT_19_0", 6.0, 1.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_AMMIT_19_1", 8.0, 1.0, 10.0, 2.0),
                    ("ENT_TYPE_MONS_AMMIT_19_2", 0.0, 2.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_AMMIT_19_3", 2.0, 2.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_AMMIT_19_4", 4.0, 2.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_AMMIT_19_5", 6.0, 2.0, 8.0, 3.0),
                    ("ENT_TYPE_MONS_AMMIT_19_6", 8.0, 2.0, 10.0, 3.0),
                    ("ENT_TYPE_MONS_AMMIT_22_0", 0.0, 3.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_AMMIT_22_1", 2.0, 3.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_AMMIT_22_2", 4.0, 3.0, 6.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_ammit", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn madame_tusk() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/madame_tusk.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big5".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_MADAMETUSK_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_2_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_2_1", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_2_2", 6.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_2_3", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_2_4", 2.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_2_5", 4.0, 2.0, 6.0, 4.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_22_0", 6.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_22_1", 0.0, 4.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_MADAMETUSK_22_2", 2.0, 4.0, 4.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalPeopleSheet".into(),
                target_chunks: chunks(&[("journal_madame_tusk", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}

pub fn eggplant_minister() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/eggplant_minister.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big5".into(),
                target_chunks: chunks(&[
                    ("minister_small_walk_1", 0.0, 0.0, 1.0, 1.0),
                    ("minister_small_walk_2", 1.0, 0.0, 2.0, 1.0),
                    ("minister_small_walk_3", 2.0, 0.0, 3.0, 1.0),
                    ("minister_small_walk_4", 3.0, 0.0, 4.0, 1.0),
                    ("minister_small_walk_5", 0.0, 1.0, 1.0, 2.0),
                    ("minister_small_walk_6", 1.0, 1.0, 2.0, 2.0),
                    ("minister_small_walk_7", 2.0, 1.0, 3.0, 2.0),
                ]),
            },
            OriginEntry {
                loader_name: "Big5".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_0_0", 0.0, 0.0, 1.0, 3.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_0", 1.0, 0.0, 2.0, 3.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_1", 2.0, 0.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_2", 3.0, 0.0, 4.0, 3.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_3", 0.0, 3.0, 1.0, 6.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_4", 1.0, 3.0, 2.0, 6.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_5", 2.0, 3.0, 3.0, 6.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_2_6", 3.0, 3.0, 4.0, 6.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_9_0", 0.0, 6.0, 1.0, 9.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_10_0", 1.0, 6.0, 2.0, 9.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_10_1", 2.0, 6.0, 3.0, 9.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_10_2", 3.0, 6.0, 4.0, 9.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_10_3", 0.0, 9.0, 1.0, 12.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_10_4", 1.0, 9.0, 2.0, 12.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_10_5", 2.0, 9.0, 3.0, 12.0),
                    ("ENT_TYPE_MONS_EGGPLANT_MINISTER_27_0", 3.0, 9.0, 4.0, 12.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_eggplant_minister", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn giant_frog() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/giant_frog.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big5".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GIANTFROG_0_0", 0.0, 0.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_GIANTFROG_0_1", 3.0, 0.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_GIANTFROG_0_2", 6.0, 0.0, 9.0, 3.0),
                    ("ENT_TYPE_MONS_GIANTFROG_3_0", 0.0, 3.0, 3.0, 6.0),
                    ("ENT_TYPE_MONS_GIANTFROG_3_1", 3.0, 3.0, 6.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_goliath_frog", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn giant_fish() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/giant_fish.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big6".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_GIANTFISH_2_0", 0.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTFISH_2_1", 4.0, 0.0, 8.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTFISH_2_2", 8.0, 0.0, 12.0, 2.0),
                    ("ENT_TYPE_MONS_GIANTFISH_2_3", 0.0, 2.0, 4.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTFISH_22_0", 4.0, 2.0, 8.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTFISH_22_1", 8.0, 2.0, 12.0, 4.0),
                    ("ENT_TYPE_MONS_GIANTFISH_22_2", 0.0, 4.0, 4.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_great_humphead", 0.0, 0.0, 1.0, 1.0)]),
            },
        ],
    }
}

pub fn waddler() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/waddler.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "Big6".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_STORAGEGUY_0_0", 0.0, 0.0, 2.0, 2.0),
                    ("ENT_TYPE_MONS_STORAGEGUY_2_0", 2.0, 0.0, 4.0, 2.0),
                    ("ENT_TYPE_MONS_STORAGEGUY_22_0", 4.0, 0.0, 6.0, 2.0),
                    ("ENT_TYPE_MONS_STORAGEGUY_22_1", 0.0, 2.0, 2.0, 4.0),
                    ("ENT_TYPE_MONS_STORAGEGUY_22_2", 2.0, 2.0, 4.0, 4.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalPeopleSheet".into(),
                target_chunks: chunks(&[("journal_waddler", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}

pub fn osiris() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/osiris.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "OsirisAndAlienQueen".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_OSIRIS_HEAD_12_0", 0.0, 0.0, 5.0, 7.0),
                    ("ENT_TYPE_MONS_OSIRIS_HEAD_13_0", 5.0, 0.0, 10.0, 7.0),
                    ("ENT_TYPE_MONS_OSIRIS_HEAD_41_0", 0.0, 7.0, 5.0, 14.0),
                ]),
            },
            OriginEntry {
                loader_name: "OsirisAndAlienQueen".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_OSIRIS_HAND_19_0", 0.0, 0.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_OSIRIS_HAND_19_1", 3.0, 0.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_OSIRIS_HAND_19_2", 0.0, 3.0, 3.0, 6.0),
                    ("ENT_TYPE_MONS_OSIRIS_HAND_19_3", 3.0, 3.0, 6.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_osiris", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "StickerSheet".into(),
                target_chunks: chunks(&[("sticker_osiris", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}

pub fn alien_queen() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/alien_queen.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "OsirisAndAlienQueen".into(),
                target_chunks: chunks(&[
                    ("ENT_TYPE_MONS_ALIENQUEEN_2_0", 0.0, 0.0, 3.0, 3.0),
                    ("ENT_TYPE_MONS_ALIENQUEEN_2_1", 3.0, 0.0, 6.0, 3.0),
                    ("ENT_TYPE_MONS_ALIENQUEEN_2_2", 6.0, 0.0, 9.0, 3.0),
                    ("ENT_TYPE_MONS_ALIENQUEEN_2_3", 0.0, 3.0, 3.0, 6.0),
                    ("ENT_TYPE_MONS_ALIENQUEEN_2_4", 3.0, 3.0, 6.0, 6.0),
                    ("ENT_TYPE_MONS_ALIENQUEEN_13_0", 6.0, 3.0, 9.0, 6.0),
                ]),
            },
            OriginEntry {
                loader_name: "OsirisAndAlienQueen".into(),
                target_chunks: chunks(&[("ENT_TYPE_FX_ALIENQUEEN_EYE_0_0", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "OsirisAndAlienQueen".into(),
                target_chunks: chunks(&[(
                    "ENT_TYPE_FX_ALIENQUEEN_EYEBALL_0_0",
                    0.0,
                    0.0,
                    1.0,
                    1.0,
                )]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_lahamu", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "StickerSheet".into(),
                target_chunks: chunks(&[("sticker_lahamu", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}

pub fn olmec() -> MergerConfig {
    MergerConfig {
        target_sprite_sheet_path: "Data/Textures/Entities/BigMonsters/olmec.png".into(),
        grid_hint_size: 8,
        origin_map: vec![
            OriginEntry {
                loader_name: "OlmecAndMech".into(),
                target_chunks: chunks(&[
                    ("olmec", 0.0, 0.0, 4.0, 4.0),
                    ("olmec_stone1", 4.0, 0.0, 8.0, 4.0),
                    ("olmec_stone2", 8.0, 0.0, 12.0, 4.0),
                    ("olmec_stone3", 12.0, 0.0, 16.0, 4.0),
                    ("olmec_piece1", 0.0, 4.0, 4.0, 6.0),
                    ("olmec_piece2", 0.0, 6.0, 4.0, 8.0),
                    ("olmec_piece3", 0.0, 8.0, 4.0, 10.0),
                    ("olmec_piece4", 0.0, 10.0, 4.0, 12.0),
                    ("olmec_piece5", 0.0, 12.0, 4.0, 14.0),
                    ("olmec_cannon1", 4.0, 4.0, 8.0, 6.0),
                    ("olmec_cannon2", 4.0, 6.0, 8.0, 8.0),
                    ("olmec_cannon3", 4.0, 8.0, 8.0, 10.0),
                    ("olmec_cannon4", 8.0, 4.0, 10.0, 6.0),
                    ("olmec_cannon5", 8.0, 6.0, 10.0, 8.0),
                    ("olmec_floater1", 10.0, 4.0, 12.0, 5.0),
                    ("olmec_floater2", 12.0, 4.0, 14.0, 5.0),
                    ("olmec_floater3", 14.0, 4.0, 16.0, 5.0),
                ]),
            },
            OriginEntry {
                loader_name: "JournalBigMonsterSheet".into(),
                target_chunks: chunks(&[("journal_olmec", 0.0, 0.0, 1.0, 1.0)]),
            },
            OriginEntry {
                loader_name: "StickerSheet".into(),
                target_chunks: chunks(&[("sticker_olmec", 0.0, 0.0, 2.0, 2.0)]),
            },
        ],
    }
}
