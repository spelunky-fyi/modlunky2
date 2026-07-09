// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn cave_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "CaveFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_cave.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("ladder", 4.0, 1.0, 5.0, 2.0),
            ("ladder_plat", 4.0, 2.0, 5.0, 3.0),
            ("bone_block", 10.0, 2.0, 11.0, 3.0),
            ("idol_floor", 10.0, 0.0, 11.0, 1.0),
            ("starting_exit", 0.5, 7.0, 3.0, 9.0),
            ("minewood_floor_hanging_hide", 6.0, 1.0, 7.0, 3.0),
            ("ghist_door2", 10.0, 6.0, 12.0, 8.0),
        ]),
    }
}

pub fn volcana_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "VolcanaFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_volcano.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("conveyorbelt_right", 8.0, 10.0, 9.0, 11.0),
            ("conveyorbelt_left", 8.0, 11.0, 9.0, 12.0),
            ("falling_platform", 4.0, 5.0, 5.0, 6.0),
        ]),
    }
}

pub fn jungle_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "JungleFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_jungle.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("vine", 4.0, 1.0, 5.0, 2.0),
            ("growable_vine", 4.0, 2.0, 5.0, 3.0),
            ("tree_base", 3.0, 11.0, 4.0, 12.0),
            ("jungle_floor", 0.0, 0.0, 1.0, 1.0),
            ("bush_block", 10.0, 2.0, 11.0, 3.0),
        ]),
    }
}

pub fn tide_pool_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "TidePoolFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_tidepool.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("climbing_pole", 4.0, 1.0, 5.0, 2.0),
            ("growable_climbing_pole", 4.0, 0.0, 5.0, 1.0),
            ("fountain_head", 10.0, 2.0, 12.0, 4.0),
        ]),
    }
}

pub fn temple_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "TempleFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_temple.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
        ]),
    }
}

pub fn ice_caves_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "IceCavesFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_ice.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("icefloor", 7.0, 1.0, 8.0, 2.0),
            ("thinice", 3.0, 11.0, 4.0, 12.0),
            ("upsidedown_spikes", 8.0, 9.0, 9.0, 10.0),
            ("falling_platform", 4.0, 5.0, 5.0, 6.0),
            ("eggplant_altar", 10.0, 2.0, 11.0, 3.0),
        ]),
    }
}

pub fn surface_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "SurfaceFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_surface.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("surface_floor", 0.0, 0.0, 1.0, 1.0),
        ]),
    }
}

pub fn sunken_city_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "SunkenCityFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_sunken.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("bigspear_trap", 8.0, 9.0, 10.0, 10.0),
        ]),
    }
}

pub fn babylon_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "BabylonFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_babylon.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("mushroom_base", 9.0, 11.0, 10.0, 12.0),
            ("palace_sign", 3.0, 8.0, 5.0, 10.0),
        ]),
    }
}

pub fn eggplant_floor_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "EggplantFloorSheet".into(),
        sprite_sheet_path: "Data/Textures/floor_eggplant.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block", 7.0, 0.0, 8.0, 1.0),
            ("entrance", 0.5, 7.0, 3.0, 9.0),
            ("entrance_shortcut", 0.5, 7.0, 3.0, 9.0),
            ("door", 0.5, 7.0, 3.0, 9.0),
            ("exit", 0.5, 9.5, 3.0, 11.5),
            ("door2", 8.0, 6.0, 10.0, 8.0),
            ("door2_secret", 8.0, 6.0, 10.0, 8.0),
            ("spikes", 5.0, 9.0, 6.0, 10.0),
            ("dirt", 0.0, 0.0, 4.0, 7.0),
            ("floor", 0.0, 0.0, 1.0, 1.0),
            ("eggplant_door", 0.5, 7.0, 3.0, 9.0),
            ("ghist_door2", 10.0, 6.0, 12.0, 8.0),
            ("fountain_head", 10.0, 2.0, 12.0, 4.0),
        ]),
    }
}
