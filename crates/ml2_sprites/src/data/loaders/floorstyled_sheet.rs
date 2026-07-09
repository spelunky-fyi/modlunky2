// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn hive_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "HiveStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_beehive.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("beehive_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn duat_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "DuatStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_duat.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("duat_floor", 1.0, 3.0, 2.0, 4.0),
            ("altar_duat", 8.0, 1.0, 10.0, 2.0),
            ("push_block", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn gold_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "GoldStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_gold.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("cog_floor", 1.0, 3.0, 2.0, 4.0),
            ("slidingwall_ceiling", 5.0, 8.0, 6.0, 10.0),
            ("slidingwall_switch", 6.0, 8.0, 7.0, 9.0),
            ("gold_crushtraplarge", 6.0, 0.0, 8.0, 2.0),
            ("push_block", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn guts_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "GutsStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_guts.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("guts_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn pagoda_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "PagodaStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_pagoda.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("pagoda_floor", 7.0, 2.0, 8.0, 3.0),
            ("slidingwall_ceiling", 5.0, 8.0, 6.0, 10.0),
            ("slidingwall", 5.0, 8.0, 6.0, 10.0),
            ("slidingwall_switch", 6.0, 8.0, 7.0, 9.0),
        ]),
    }
}

pub fn temple_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "TempleStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_temple.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("temple_floor", 1.0, 3.0, 2.0, 4.0),
            ("push_block", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn mothership_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "MothershipStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_mothership.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("mothership_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn babylon_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "BabylonStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_babylon.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("babylon_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn sunken_city_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "SunkenCityStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_sunken.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("sunken_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn palace_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "PalaceStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_palace.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("palace_floor", 7.0, 2.0, 8.0, 3.0),
            ("palace_entrance", 8.0, 6.0, 10.0, 8.0),
            ("palace_table", 7.0, 1.0, 10.0, 2.0),
            ("palace_table_tray", 8.0, 0.0, 9.0, 1.0),
            ("palace_chandelier", 4.0, 8.0, 7.0, 10.0),
            ("palace_candle", 7.0, 0.0, 8.0, 1.0),
            ("palace_bookcase", 8.0, 2.0, 9.0, 3.0),
        ]),
    }
}

pub fn stoned_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "StonedStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_stone.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("stone_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}

pub fn wood_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "WoodStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_wood.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door_drop_held", 8.0, 6.0, 10.0, 8.0),
            ("minewood_floor", 7.0, 2.0, 8.0, 3.0),
            ("wanted_poster", 6.0, 6.0, 8.0, 8.0),
            ("shop_sign", 4.0, 8.0, 6.0, 10.0),
            ("shop_door", 9.0, 0.0, 10.0, 1.0),
        ]),
    }
}

pub fn vlad_styled_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "VladStyledFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floorstyled_vlad.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("styled_floor", 7.0, 2.0, 8.0, 3.0),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("crown_statue", 8.0, 0.0, 10.0, 3.0),
            ("vlad_floor", 7.0, 2.0, 8.0, 3.0),
        ]),
    }
}
