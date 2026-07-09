// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn journal_people_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "JournalPeopleSheet".into(),
        sprite_sheet_path: "Data/Textures/journal_entry_people.png".into(),
        chunk_size: 160,
        chunk_map: chunks(&[
            ("journal_char_yellow", 0.0, 0.0, 1.0, 1.0),
            ("journal_char_magenta", 1.0, 0.0, 2.0, 1.0),
            ("journal_char_cyan", 2.0, 0.0, 3.0, 1.0),
            ("journal_char_black", 3.0, 0.0, 4.0, 1.0),
            ("journal_char_cinnabar", 4.0, 0.0, 5.0, 1.0),
            ("journal_char_green", 5.0, 0.0, 6.0, 1.0),
            ("journal_char_olive", 6.0, 0.0, 7.0, 1.0),
            ("journal_char_white", 7.0, 0.0, 8.0, 1.0),
            ("journal_char_cerulean", 8.0, 0.0, 9.0, 1.0),
            ("journal_char_blue", 9.0, 0.0, 10.0, 1.0),
            ("journal_char_lime", 0.0, 1.0, 1.0, 2.0),
            ("journal_char_lemon", 1.0, 1.0, 2.0, 2.0),
            ("journal_char_iris", 2.0, 1.0, 3.0, 2.0),
            ("journal_char_gold", 3.0, 1.0, 4.0, 2.0),
            ("journal_char_red", 4.0, 1.0, 5.0, 2.0),
            ("journal_char_pink", 5.0, 1.0, 6.0, 2.0),
            ("journal_char_violet", 6.0, 1.0, 7.0, 2.0),
            ("journal_char_gray", 7.0, 1.0, 8.0, 2.0),
            ("journal_char_khaki", 8.0, 1.0, 9.0, 2.0),
            ("journal_char_orange", 9.0, 1.0, 10.0, 2.0),
            ("journal_hired_hand", 0.0, 2.0, 1.0, 3.0),
            ("journal_eggplant_child", 1.0, 2.0, 2.0, 3.0),
            ("journal_shopkeeper", 2.0, 2.0, 3.0, 3.0),
            ("journal_tun", 3.0, 2.0, 4.0, 3.0),
            ("journal_yang", 4.0, 2.0, 5.0, 3.0),
            ("journal_eggplant_king", 4.0, 2.0, 6.0, 4.0),
            ("journal_van_horsing", 5.0, 2.0, 6.0, 3.0),
            ("journal_sparrow", 6.0, 2.0, 7.0, 3.0),
            ("journal_parsley", 7.0, 2.0, 8.0, 3.0),
            ("journal_parsnip", 8.0, 2.0, 9.0, 3.0),
            ("journal_parmesan", 9.0, 2.0, 10.0, 3.0),
            ("journal_beg", 0.0, 3.0, 1.0, 4.0),
            ("journal_tusks_bodyguard", 1.0, 3.0, 2.0, 4.0),
            ("journal_cave_man_shopkeeper", 2.0, 3.0, 3.0, 4.0),
            ("journal_ghost_shopkeeper", 3.0, 3.0, 4.0, 4.0),
            ("journal_yama", 4.0, 3.0, 6.0, 5.0),
            ("journal_madame_tusk", 6.0, 3.0, 8.0, 5.0),
            ("journal_waddler", 8.0, 3.0, 10.0, 5.0),
            ("journal_mama_tunnel", 0.0, 4.0, 1.0, 5.0),
        ]),
    }
}
