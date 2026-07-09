// Sprite loader/merger configs describing which chunks live in which
// sheet, keyed by tile name for the sprite fetcher lookup.

use crate::LoaderConfig;
use crate::data::chunks;

pub fn journal_trap_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "JournalTrapSheet".into(),
        sprite_sheet_path: "Data/Textures/journal_entry_traps.png".into(),
        chunk_size: 160,
        chunk_map: chunks(&[
            ("journal_arrow_trap", 0.0, 0.0, 1.0, 1.0),
            ("journal_spear_trap", 1.0, 0.0, 2.0, 1.0),
            ("journal_thorny_vine", 2.0, 0.0, 3.0, 1.0),
            ("journal_powder_box", 3.0, 0.0, 4.0, 1.0),
            ("journal_falling_platform", 4.0, 0.0, 5.0, 1.0),
            ("journal_crush_trap", 6.0, 0.0, 7.0, 1.0),
            ("journal_laser_trap", 7.0, 0.0, 8.0, 1.0),
            ("journal_spring_trap", 8.0, 0.0, 9.0, 1.0),
            ("journal_landmine", 9.0, 0.0, 10.0, 1.0),
            ("journal_spikes", 0.0, 1.0, 1.0, 2.0),
            ("journal_spark_trap", 1.0, 1.0, 2.0, 2.0),
            ("journal_egg_sac", 2.0, 1.0, 3.0, 2.0),
            ("journal_bear_trap", 3.0, 1.0, 4.0, 2.0),
            ("journal_totem_trap", 0.0, 4.0, 1.0, 6.0),
            ("journal_lion_trap", 1.0, 4.0, 2.0, 6.0),
            ("journal_log_trap", 2.0, 4.0, 3.0, 6.0),
            ("journal_sticky_trap", 3.0, 4.0, 4.0, 6.0),
            ("journal_sliding_wall", 4.0, 4.0, 5.0, 6.0),
            ("journal_giant_crush_trap", 0.0, 8.0, 2.0, 10.0),
            ("journal_boulder", 2.0, 8.0, 4.0, 10.0),
            ("journal_giant_clam", 4.0, 8.0, 6.0, 10.0),
            ("journal_bone_drop", 8.0, 8.0, 10.0, 10.0),
            ("journal_frog_trap", 6.0, 9.0, 8.0, 10.0),
        ]),
    }
}
