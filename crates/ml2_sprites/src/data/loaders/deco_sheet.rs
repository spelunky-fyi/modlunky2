// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn cave_deco_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CaveDecoSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_cave.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("kali_bg", 0.0, 0.0, 4.0, 5.0),
            ("woodenlog_trap", 1.0, 5.0, 3.0, 10.0),
            ("udjat_wall_heads", 8.0, 8.0, 12.0, 12.0),
        ]),
    }
}

pub fn volcana_deco_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "VolcanaDecoSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_volcano.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("kali_bg", 0.0, 0.0, 4.0, 5.0),
            ("drill", 1.0, 5.0, 3.0, 8.0),
            ("vlad_banner", 1.0, 8.0, 3.0, 12.0),
        ]),
    }
}

pub fn jungle_deco_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "JungleDecoSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_jungle.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("stone_door", 0.0, 5.0, 3.0, 7.0)]),
    }
}

pub fn ice_caves_deco_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "IceCavesDecoSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_ice.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("moai_statue", 0.0, 7.0, 4.0, 12.0),
            ("boulder", 0.0, 5.0, 2.0, 7.0),
        ]),
    }
}

pub fn sunken_city_deco_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "SunkenCityDecoSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_sunken.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[("mother_statue", 0.0, 5.0, 2.0, 11.0)]),
    }
}

pub fn surface_deco_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "SurfaceDecoSheet".into(),
        sprite_sheet_path: "Data/Textures/deco_basecamp.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("construction_sign", 5.0, 12.0, 6.0, 13.0),
            ("boombox", 5.0, 14.0, 6.0, 15.0),
            ("tutorial_speedrun_sign", 7.0, 14.0, 8.0, 15.0),
            ("tutorial_menu_sign", 7.0, 14.0, 8.0, 15.0),
            ("singlebed", 0.0, 15.0, 1.0, 16.0),
            ("dresser", 2.0, 14.0, 3.0, 15.0),
            ("bunkbed", 0.0, 13.0, 2.0, 15.0),
            ("diningtable", 14.0, 10.0, 16.0, 11.0),
            ("sidetable", 9.0, 12.0, 10.0, 13.0),
            ("chair_looking_left", 3.0, 15.0, 4.0, 16.0),
            ("chair_looking_right", 3.0, 15.0, 4.0, 16.0),
            ("couch", 6.0, 15.0, 8.0, 16.0),
            ("tv", 8.0, 15.0, 9.0, 16.0),
            ("dog_sign", 12.0, 10.0, 14.0, 12.0),
            ("shortcut_station_banner", 10.0, 8.0, 12.0, 12.0),
            ("telescope", 12.0, 8.0, 14.0, 10.0),
        ]),
    }
}
