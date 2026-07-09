// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn menu_leader_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "MenuLeaderSheet".into(),
        sprite_sheet_path: "Data/Textures/menu_leader.png".into(),
        chunk_size: 64,
        chunk_map: chunks(&[
            ("leader_char_yellow", 0.0, 7.0, 2.0, 8.0),
            ("leader_char_magenta", 2.0, 7.0, 4.0, 8.0),
            ("leader_char_cyan", 4.0, 7.0, 6.0, 8.0),
            ("leader_char_black", 6.0, 7.0, 8.0, 8.0),
            ("leader_char_cinnabar", 8.0, 7.0, 10.0, 8.0),
            ("leader_char_green", 10.0, 7.0, 12.0, 8.0),
            ("leader_char_olive", 12.0, 7.0, 14.0, 8.0),
            ("leader_char_white", 14.0, 7.0, 16.0, 8.0),
            ("leader_char_cerulean", 16.0, 7.0, 18.0, 8.0),
            ("leader_char_blue", 18.0, 7.0, 20.0, 8.0),
            ("leader_char_lime", 0.0, 9.0, 2.0, 10.0),
            ("leader_char_lemon", 2.0, 9.0, 4.0, 10.0),
            ("leader_char_iris", 4.0, 9.0, 6.0, 10.0),
            ("leader_char_gold", 6.0, 9.0, 8.0, 10.0),
            ("leader_char_red", 8.0, 9.0, 10.0, 10.0),
            ("leader_char_pink", 10.0, 9.0, 12.0, 10.0),
            ("leader_char_violet", 12.0, 9.0, 14.0, 10.0),
            ("leader_char_gray", 14.0, 9.0, 16.0, 10.0),
            ("leader_char_khaki", 16.0, 9.0, 18.0, 10.0),
            ("leader_char_orange", 18.0, 9.0, 20.0, 10.0),
        ]),
    }
}
