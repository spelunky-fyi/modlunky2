// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn journal_big_monster_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "JournalBigMonsterSheet".into(),
        sprite_sheet_path: "Data/Textures/journal_entry_mons_big.png".into(),
        chunk_size: 320,
        chunk_map: chunks(&[
            ("journal_quill_back", 0.0, 0.0, 1.0, 1.0),
            ("journal_olmec", 1.0, 0.0, 2.0, 1.0),
            ("journal_mummy", 2.0, 0.0, 3.0, 1.0),
            ("journal_anubis", 3.0, 0.0, 4.0, 1.0),
            ("journal_lamassu", 4.0, 0.0, 5.0, 1.0),
            ("journal_queen_bee", 0.0, 1.0, 1.0, 2.0),
            ("journal_ghost", 1.0, 1.0, 2.0, 2.0),
            ("journal_yeti_king", 3.0, 1.0, 4.0, 2.0),
            ("journal_yeti_queen", 4.0, 1.0, 5.0, 2.0),
            ("journal_goliath_frog", 0.0, 2.0, 1.0, 3.0),
            ("journal_giant_spider", 1.0, 2.0, 2.0, 3.0),
            ("journal_lavamander", 2.0, 2.0, 3.0, 3.0),
            ("journal_panxie", 3.0, 2.0, 4.0, 3.0),
            ("journal_celestial_jellyfish", 4.0, 2.0, 5.0, 3.0),
            ("cosmic_jelly", 4.0, 2.0, 5.0, 3.0),
            ("journal_eggplant_minister", 0.0, 3.0, 1.0, 4.0),
            ("journal_mech_rider", 1.0, 3.0, 2.0, 4.0),
            ("journal_great_humphead", 2.0, 3.0, 3.0, 4.0),
            ("journal_lahamu", 3.0, 3.0, 4.0, 4.0),
            ("journal_ammit", 4.0, 3.0, 5.0, 4.0),
            ("journal_anubis_2", 0.0, 4.0, 1.0, 5.0),
            ("journal_hundun", 1.0, 4.0, 2.0, 5.0),
            ("journal_kingu", 2.0, 4.0, 3.0, 5.0),
            ("journal_osiris", 3.0, 4.0, 4.0, 5.0),
            ("journal_tiamat", 4.0, 4.0, 5.0, 5.0),
            ("journal_giant_fly", 0.0, 5.0, 1.0, 6.0),
        ]),
    }
}
