// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn journal_place_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "JournalPlaceSheet".into(),
        sprite_sheet_path: "Data/Textures/journal_entry_place.png".into(),
        chunk_size: 320,
        chunk_map: chunks(&[
            ("journal_dwelling", 0.0, 0.0, 2.0, 1.0),
            ("journal_jungle", 2.0, 0.0, 4.0, 1.0),
            ("journal_volcana", 4.0, 0.0, 6.0, 1.0),
            ("journal_olmecs_lair", 6.0, 0.0, 8.0, 1.0),
            ("journal_tide_pool", 0.0, 1.0, 2.0, 2.0),
            ("journal_temple_of_anubis", 2.0, 1.0, 4.0, 2.0),
            ("journal_ice_caves", 4.0, 1.0, 6.0, 2.0),
            ("journal_neo_babylon", 6.0, 1.0, 8.0, 2.0),
            ("journal_sunken_city", 0.0, 2.0, 2.0, 3.0),
            ("journal_cosmic_ocean", 2.0, 2.0, 4.0, 3.0),
            ("journal_city_of_gold", 4.0, 2.0, 6.0, 3.0),
            ("journal_duat", 6.0, 2.0, 8.0, 3.0),
            ("journal_abzu", 0.0, 3.0, 2.0, 4.0),
            ("journal_tiamats_throne", 2.0, 3.0, 4.0, 4.0),
            ("journal_eggplant_world", 4.0, 3.0, 6.0, 4.0),
            ("journal_hunduns_hideaway", 6.0, 3.0, 8.0, 4.0),
        ]),
    }
}
