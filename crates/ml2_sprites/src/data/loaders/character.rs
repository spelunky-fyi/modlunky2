// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::data::chunks;
use crate::{ChunkMap, LoaderConfig};

/// Shared chunk map used by character-family loaders.
fn character_chunk_map() -> ChunkMap {
    chunks(&[
        ("portrait", 12.0, 1.0, 16.0, 7.0),
        ("standing", 0.0, 0.0, 1.0, 1.0),
        ("walking_1", 1.0, 0.0, 2.0, 1.0),
        ("walking_2", 2.0, 0.0, 3.0, 1.0),
        ("walking_3", 3.0, 0.0, 4.0, 1.0),
        ("walking_4", 4.0, 0.0, 5.0, 1.0),
        ("walking_5", 5.0, 0.0, 6.0, 1.0),
        ("walking_6", 6.0, 0.0, 7.0, 1.0),
        ("walking_7", 7.0, 0.0, 8.0, 1.0),
        ("walking_8", 8.0, 0.0, 9.0, 1.0),
        ("stunned", 9.0, 0.0, 10.0, 1.0),
        ("swimming_1", 10.0, 0.0, 11.0, 1.0),
        ("swimming_2", 11.0, 0.0, 12.0, 1.0),
        ("swimming_3", 12.0, 0.0, 13.0, 1.0),
        ("swimming_4", 13.0, 0.0, 14.0, 1.0),
        ("swimming_5", 14.0, 0.0, 15.0, 1.0),
        ("swimming_6", 15.0, 0.0, 16.0, 1.0),
        ("crouching_1", 0.0, 1.0, 1.0, 2.0),
        ("crouching_2", 1.0, 1.0, 2.0, 2.0),
        ("crouching_3", 2.0, 1.0, 3.0, 2.0),
        ("crouching_4", 3.0, 1.0, 4.0, 2.0),
        ("crouching_5", 4.0, 1.0, 5.0, 2.0),
        ("crawling_1", 5.0, 1.0, 6.0, 2.0),
        ("crawling_2", 6.0, 1.0, 7.0, 2.0),
        ("crawling_3", 7.0, 1.0, 8.0, 2.0),
        ("crawling_4", 8.0, 1.0, 9.0, 2.0),
        ("crawling_5", 9.0, 1.0, 10.0, 2.0),
        ("crawling_6", 10.0, 1.0, 11.0, 2.0),
        ("crawling_7", 11.0, 1.0, 12.0, 2.0),
        ("stun_1", 0.0, 2.0, 1.0, 3.0),
        ("stun_2", 1.0, 2.0, 2.0, 3.0),
        ("stun_3", 2.0, 2.0, 3.0, 3.0),
        ("stun_4", 3.0, 2.0, 4.0, 3.0),
        ("flip_1", 4.0, 2.0, 5.0, 3.0),
        ("flip_2", 5.0, 2.0, 6.0, 3.0),
        ("flip_3", 6.0, 2.0, 7.0, 3.0),
        ("flip_4", 7.0, 2.0, 8.0, 3.0),
        ("flip_5", 8.0, 2.0, 9.0, 3.0),
        ("flip_6", 9.0, 2.0, 10.0, 3.0),
        ("flip_7", 10.0, 2.0, 11.0, 3.0),
        ("holding", 11.0, 2.0, 12.0, 3.0),
        ("teetering_1", 0.0, 3.0, 1.0, 4.0),
        ("teetering_2", 1.0, 3.0, 2.0, 4.0),
        ("teetering_3", 2.0, 3.0, 3.0, 4.0),
        ("teetering_4", 3.0, 3.0, 4.0, 4.0),
        ("teetering_5", 4.0, 3.0, 5.0, 4.0),
        ("teetering_6", 5.0, 3.0, 6.0, 4.0),
        ("teetering_7", 6.0, 3.0, 7.0, 4.0),
        ("teetering_8", 7.0, 3.0, 8.0, 4.0),
        ("ledge_grab_1", 8.0, 3.0, 9.0, 4.0),
        ("ledge_grab_2", 9.0, 3.0, 10.0, 4.0),
        ("ledge_grab_3", 10.0, 3.0, 11.0, 4.0),
        ("ledge_grab_4", 11.0, 3.0, 12.0, 4.0),
        ("whipping_1", 0.0, 4.0, 1.0, 5.0),
        ("whipping_2", 1.0, 4.0, 2.0, 5.0),
        ("whipping_3", 2.0, 4.0, 3.0, 5.0),
        ("whipping_4", 3.0, 4.0, 4.0, 5.0),
        ("whipping_5", 4.0, 4.0, 5.0, 5.0),
        ("whipping_6", 5.0, 4.0, 6.0, 5.0),
        ("throwing_1", 6.0, 4.0, 7.0, 5.0),
        ("throwing_2", 7.0, 4.0, 8.0, 5.0),
        ("throwing_3", 8.0, 4.0, 9.0, 5.0),
        ("throwing_4", 9.0, 4.0, 10.0, 5.0),
        ("throwing_5", 10.0, 4.0, 11.0, 5.0),
        ("enter_1", 0.0, 5.0, 1.0, 6.0),
        ("enter_2", 1.0, 5.0, 2.0, 6.0),
        ("enter_3", 2.0, 5.0, 3.0, 6.0),
        ("enter_4", 3.0, 5.0, 4.0, 6.0),
        ("enter_5", 4.0, 5.0, 5.0, 6.0),
        ("enter_6", 5.0, 5.0, 6.0, 6.0),
        ("exit_1", 6.0, 5.0, 7.0, 6.0),
        ("exit_2", 7.0, 5.0, 8.0, 6.0),
        ("exit_3", 8.0, 5.0, 9.0, 6.0),
        ("exit_4", 9.0, 5.0, 10.0, 6.0),
        ("exit_5", 10.0, 5.0, 11.0, 6.0),
        ("exit_6", 11.0, 5.0, 12.0, 6.0),
        ("climbing_ladder_1", 0.0, 6.0, 1.0, 7.0),
        ("climbing_ladder_2", 1.0, 6.0, 2.0, 7.0),
        ("climbing_ladder_3", 2.0, 6.0, 3.0, 7.0),
        ("climbing_ladder_4", 3.0, 6.0, 4.0, 7.0),
        ("climbing_ladder_5", 4.0, 6.0, 5.0, 7.0),
        ("climbing_ladder_6", 5.0, 6.0, 6.0, 7.0),
        ("pushing_1", 6.0, 6.0, 7.0, 7.0),
        ("pushing_2", 7.0, 6.0, 8.0, 7.0),
        ("pushing_3", 8.0, 6.0, 9.0, 7.0),
        ("pushing_4", 9.0, 6.0, 10.0, 7.0),
        ("pushing_5", 10.0, 6.0, 11.0, 7.0),
        ("pushing_6", 11.0, 6.0, 12.0, 7.0),
        ("climbing_rope_1", 0.0, 7.0, 1.0, 8.0),
        ("climbing_rope_2", 1.0, 7.0, 2.0, 8.0),
        ("climbing_rope_3", 2.0, 7.0, 3.0, 8.0),
        ("climbing_rope_4", 3.0, 7.0, 4.0, 8.0),
        ("climbing_rope_5", 4.0, 7.0, 5.0, 8.0),
        ("climbing_rope_6", 5.0, 7.0, 6.0, 8.0),
        ("climbing_rope_7", 6.0, 7.0, 7.0, 8.0),
        ("climbing_rope_8", 7.0, 7.0, 8.0, 8.0),
        ("climbing_rope_9", 8.0, 7.0, 9.0, 8.0),
        ("climbing_rope_10", 9.0, 7.0, 10.0, 8.0),
        ("crouching_mount_1", 10.0, 7.0, 11.0, 8.0),
        ("crouching_mount_2", 11.0, 7.0, 12.0, 8.0),
        ("crouching_mount_3", 12.0, 7.0, 13.0, 8.0),
        ("crouching_mount_4", 13.0, 7.0, 14.0, 8.0),
        ("crouching_mount_5", 14.0, 7.0, 15.0, 8.0),
        ("looking_up_1", 0.0, 8.0, 1.0, 9.0),
        ("looking_up_2", 1.0, 8.0, 2.0, 9.0),
        ("looking_up_3", 2.0, 8.0, 3.0, 9.0),
        ("looking_up_4", 3.0, 8.0, 4.0, 9.0),
        ("looking_up_5", 4.0, 8.0, 5.0, 9.0),
        ("looking_up_6", 5.0, 8.0, 6.0, 9.0),
        ("looking_up_7", 6.0, 8.0, 7.0, 9.0),
        ("sitting", 7.0, 8.0, 8.0, 9.0),
        ("looking_up_sitting_1", 8.0, 8.0, 9.0, 9.0),
        ("looking_up_sitting_2", 9.0, 8.0, 10.0, 9.0),
        ("looking_up_sitting_3", 10.0, 8.0, 11.0, 9.0),
        ("looking_up_sitting_4", 11.0, 8.0, 12.0, 9.0),
        ("looking_up_sitting_5", 12.0, 8.0, 13.0, 9.0),
        ("looking_up_sitting_6", 13.0, 8.0, 14.0, 9.0),
        ("looking_up_sitting_7", 14.0, 8.0, 15.0, 9.0),
        ("jumping_1", 0.0, 9.0, 1.0, 10.0),
        ("jumping_2", 1.0, 9.0, 2.0, 10.0),
        ("jumping_3", 2.0, 9.0, 3.0, 10.0),
        ("jumping_4", 3.0, 9.0, 4.0, 10.0),
        ("jumping_5", 4.0, 9.0, 5.0, 10.0),
        ("jumping_6", 5.0, 9.0, 6.0, 10.0),
        ("jumping_7", 6.0, 9.0, 7.0, 10.0),
        ("jumping_8", 7.0, 9.0, 8.0, 10.0),
        ("jumping_9", 8.0, 9.0, 9.0, 10.0),
        ("jumping_10", 9.0, 9.0, 10.0, 10.0),
        ("jumping_11", 10.0, 9.0, 11.0, 10.0),
        ("jumping_12", 11.0, 9.0, 12.0, 10.0),
        ("rope_coiled", 12.0, 9.0, 13.0, 10.0),
        ("rope_top", 13.0, 9.0, 14.0, 10.0),
        ("rope_unrolled", 13.0, 9.0, 14.0, 10.0),
        ("rope_short", 14.0, 9.0, 15.0, 10.0),
        ("rope_burned", 15.0, 9.0, 16.0, 10.0),
        ("ghosting_1", 0.0, 10.0, 1.0, 11.0),
        ("ghosting_2", 1.0, 10.0, 2.0, 11.0),
        ("ghosting_3", 2.0, 10.0, 3.0, 11.0),
        ("ghosting_4", 3.0, 10.0, 4.0, 11.0),
        ("ghosting_5", 4.0, 10.0, 5.0, 11.0),
        ("ghosting_6", 5.0, 10.0, 6.0, 11.0),
        ("ghosting_7", 6.0, 10.0, 7.0, 11.0),
        ("ghosting_8", 7.0, 10.0, 8.0, 11.0),
        ("ghosting_9", 8.0, 10.0, 9.0, 11.0),
        ("ghosting_10", 9.0, 10.0, 10.0, 11.0),
        ("ghosting_11", 10.0, 10.0, 11.0, 11.0),
        ("ghosting_12", 11.0, 10.0, 12.0, 11.0),
        ("ghosting_13", 12.0, 10.0, 13.0, 11.0),
        ("ghosting_14", 13.0, 10.0, 14.0, 11.0),
        ("ghosting_15", 14.0, 10.0, 15.0, 11.0),
        ("ghosting_16", 15.0, 10.0, 16.0, 11.0),
        ("icon", 0.0, 11.0, 1.0, 12.0),
        ("bag", 1.0, 11.0, 2.0, 12.0),
        ("playerbag", 1.0, 11.0, 2.0, 12.0),
        ("wanted", 2.0, 11.0, 3.0, 12.0),
        ("pointer", 3.0, 11.0, 4.0, 12.0),
        ("taming_1", 4.0, 11.0, 5.0, 12.0),
        ("taming_2", 5.0, 11.0, 6.0, 12.0),
        ("taming_3", 6.0, 11.0, 7.0, 12.0),
        ("taming_4", 7.0, 11.0, 8.0, 12.0),
        ("taming_5", 8.0, 11.0, 9.0, 12.0),
        ("taming_6", 9.0, 11.0, 10.0, 12.0),
        ("ghost_stun", 10.0, 11.0, 11.0, 12.0),
        ("rope_segment", 0.0, 12.0, 1.0, 13.0),
        ("rope_uncoiling_1", 1.0, 12.0, 2.0, 13.0),
        ("rope_uncoiling_2", 2.0, 12.0, 3.0, 13.0),
        ("rope_uncoiling_3", 3.0, 12.0, 4.0, 13.0),
        ("rope_uncoiling_4", 4.0, 12.0, 5.0, 13.0),
        ("rope_end", 5.0, 12.0, 6.0, 13.0),
        ("rope_burning_1", 6.0, 12.0, 7.0, 13.0),
        ("rope_burning_2", 7.0, 12.0, 8.0, 13.0),
        ("rope_burning_3", 8.0, 12.0, 9.0, 13.0),
        ("rope_burning_4", 9.0, 12.0, 10.0, 13.0),
        ("whip_1", 10.0, 12.0, 11.0, 13.0),
        ("whip_2", 11.0, 12.0, 12.0, 13.0),
        ("whip_3", 12.0, 12.0, 13.0, 13.0),
        ("whip_4", 13.0, 12.0, 14.0, 13.0),
        ("whip_5", 14.0, 12.0, 15.0, 13.0),
        ("whip_6", 15.0, 12.0, 16.0, 13.0),
        ("stun_effect_1", 0.0, 13.0, 1.0, 14.0),
        ("stun_effect_2", 1.0, 13.0, 2.0, 14.0),
        ("stun_effect_3", 2.0, 13.0, 3.0, 14.0),
        ("stun_effect_4", 3.0, 13.0, 4.0, 14.0),
        ("stun_effect_5", 4.0, 13.0, 5.0, 14.0),
        ("stun_effect_6", 5.0, 13.0, 6.0, 14.0),
        ("stun_effect_7", 6.0, 13.0, 7.0, 14.0),
        ("stun_effect_8", 7.0, 13.0, 8.0, 14.0),
        ("stun_effect_9", 8.0, 13.0, 9.0, 14.0),
        ("stun_effect_10", 9.0, 13.0, 10.0, 14.0),
        ("stun_effect_11", 10.0, 13.0, 11.0, 14.0),
        ("stun_effect_12", 11.0, 13.0, 12.0, 14.0),
        ("petting_1", 0.0, 14.0, 1.0, 15.0),
        ("petting_2", 1.0, 14.0, 2.0, 15.0),
        ("petting_3", 2.0, 14.0, 3.0, 15.0),
        ("petting_4", 3.0, 14.0, 4.0, 15.0),
        ("petting_5", 4.0, 14.0, 5.0, 15.0),
        ("petting_6", 5.0, 14.0, 6.0, 15.0),
        ("petting_7", 6.0, 14.0, 7.0, 15.0),
        ("petting_8", 7.0, 14.0, 8.0, 15.0),
    ])
}

pub fn character_black_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterBlackSheet".into(),
        sprite_sheet_path: "Data/Textures/char_black.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_lime_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterLimeSheet".into(),
        sprite_sheet_path: "Data/Textures/char_lime.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_magenta_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterMagentaSheet".into(),
        sprite_sheet_path: "Data/Textures/char_magenta.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_olive_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterOliveSheet".into(),
        sprite_sheet_path: "Data/Textures/char_olive.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_orange_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterOrangeSheet".into(),
        sprite_sheet_path: "Data/Textures/char_orange.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_pink_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterPinkSheet".into(),
        sprite_sheet_path: "Data/Textures/char_pink.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_red_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterRedSheet".into(),
        sprite_sheet_path: "Data/Textures/char_red.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_violet_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterVioletSheet".into(),
        sprite_sheet_path: "Data/Textures/char_violet.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_white_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterWhiteSheet".into(),
        sprite_sheet_path: "Data/Textures/char_white.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_yellow_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterYellowSheet".into(),
        sprite_sheet_path: "Data/Textures/char_yellow.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_blue_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterBlueSheet".into(),
        sprite_sheet_path: "Data/Textures/char_blue.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_cerulean_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterCeruleanSheet".into(),
        sprite_sheet_path: "Data/Textures/char_cerulean.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_cinnabar_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterCinnabarSheet".into(),
        sprite_sheet_path: "Data/Textures/char_cinnabar.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_cyan_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterCyanSheet".into(),
        sprite_sheet_path: "Data/Textures/char_cyan.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_egg_child_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterEggChildSheet".into(),
        sprite_sheet_path: "Data/Textures/char_eggchild.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_gold_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterGoldSheet".into(),
        sprite_sheet_path: "Data/Textures/char_gold.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_gray_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterGraySheet".into(),
        sprite_sheet_path: "Data/Textures/char_gray.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_green_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterGreenSheet".into(),
        sprite_sheet_path: "Data/Textures/char_green.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_hired_hand_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterHiredHandSheet".into(),
        sprite_sheet_path: "Data/Textures/char_hired.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_iris_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterIrisSheet".into(),
        sprite_sheet_path: "Data/Textures/char_iris.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_khaki_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterKhakiSheet".into(),
        sprite_sheet_path: "Data/Textures/char_khaki.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}

pub fn character_lemon_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CharacterLemonSheet".into(),
        sprite_sheet_path: "Data/Textures/char_lemon.png".into(),
        chunk_size: 128,
        chunk_map: character_chunk_map(),
    }
}
