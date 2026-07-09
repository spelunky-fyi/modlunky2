// Hand-maintained loader. Unlike its siblings in this directory, this one
// is not covered by the sprite-data code generator, so this file is
// authoritative and must be updated by hand when the sprite sheet layout
// changes. `chunk_map` entries are `(name, x0, y0, x1, y1)` in 128px chunks.

use crate::LoaderConfig;
use crate::data::chunks;

/// `FloorMiscSheet`. Traps, altars, elevators, forcefields, dice / prize
/// machines, storage floors, laser and crush traps, etc. Sprite sheet is
/// `Data/Textures/floormisc.png` at 128px per chunk.
pub fn floor_misc_sheet() -> LoaderConfig {
    LoaderConfig {
        name: "FloorMiscSheet".into(),
        sprite_sheet_path: "Data/Textures/floormisc.png".into(),
        chunk_size: 128,
        chunk_map: chunks(&[
            ("push_block_reg", 0.0, 0.0, 1.0, 1.0),
            ("arrow_trap", 1.0, 0.0, 2.0, 1.0),
            ("altar", 2.0, 0.0, 3.0, 1.0),
            ("altar_trim_right", 2.0, 1.0, 3.0, 2.0),
            ("altar_trim_left", 3.0, 1.0, 4.0, 2.0),
            ("totemtrap", 4.0, 0.0, 5.0, 2.0),
            ("totem_trap", 4.0, 0.0, 5.0, 2.0),
            ("liontrap", 5.0, 0.0, 6.0, 2.0),
            ("lion_trap", 5.0, 0.0, 6.0, 2.0),
            ("sunken_arrowtrap", 6.0, 0.0, 7.0, 1.0),
            ("spark_trap", 7.0, 0.0, 8.0, 1.0),
            ("spark_trap_off", 7.0, 1.0, 8.0, 2.0),
            ("minewood_platform_disconnected", 0.0, 1.0, 1.0, 2.0),
            ("minewood_platform_connected", 1.0, 1.0, 2.0, 2.0),
            ("minewood_scaffolding_disconnected1", 0.0, 2.0, 1.0, 3.0),
            ("minewood_scaffolding_disconnected2", 0.0, 3.0, 2.0, 4.0),
            ("minewood_scaffolding_connected1", 1.0, 2.0, 2.0, 3.0),
            ("minewood_scaffolding_connected2", 1.0, 3.0, 2.0, 4.0),
            ("cookfire", 6.0, 1.0, 7.0, 2.0),
            ("powder_keg", 2.0, 2.0, 3.0, 3.0),
            ("factory_generator", 3.0, 2.0, 4.0, 3.0),
            ("alien_generator", 3.0, 2.0, 4.0, 3.0),
            ("totemtrap_broken_edge", 4.0, 2.0, 5.0, 3.0),
            ("liontrap_broken_edge", 5.0, 2.0, 6.0, 3.0),
            ("storage_floor", 6.0, 2.0, 7.0, 3.0),
            ("storage_floor_activated", 7.0, 2.0, 8.0, 3.0),
            ("elevator", 2.0, 3.0, 3.0, 4.0),
            ("crushing_elevator", 2.0, 3.0, 3.0, 4.0),
            ("elevator_up", 3.0, 3.0, 4.0, 4.0),
            ("elevator_down", 4.0, 3.0, 5.0, 4.0),
            ("jungle_spear_trap", 5.0, 3.0, 6.0, 4.0),
            ("tidepool_single_step_platform", 6.0, 3.0, 7.0, 4.0),
            ("tidepool_platform_top", 7.0, 3.0, 8.0, 4.0),
            ("pagoda_platform", 7.0, 3.0, 8.0, 4.0),
            ("tidepool_platform_middle", 7.0, 4.0, 8.0, 5.0),
            ("tidepool_platform_bottom", 7.0, 5.0, 8.0, 6.0),
            ("tidepool_platform_bottom_broken", 6.0, 4.0, 7.0, 5.0),
            ("tidepool_platform_middle_broken", 6.0, 5.0, 7.0, 6.0),
            ("crushtraplarge", 0.0, 4.0, 2.0, 6.0),
            ("crushtrap", 0.0, 6.0, 1.0, 7.0),
            ("lasertrap", 2.0, 4.0, 3.0, 5.0),
            ("laser_trap", 2.0, 4.0, 3.0, 5.0),
            ("lasertrap_charging1", 3.0, 4.0, 4.0, 5.0),
            ("lasertrap_charging2", 4.0, 4.0, 5.0, 5.0),
            ("lasertrap_charged", 5.0, 4.0, 6.0, 5.0),
            ("udjat_socket", 4.0, 5.0, 5.0, 6.0),
            ("udjat_socket_filled", 5.0, 5.0, 6.0, 6.0),
            ("udjat_socket_border", 2.0, 5.0, 3.0, 6.0),
            ("udjat_socket_border_filled", 3.0, 5.0, 4.0, 6.0),
            ("forcefield_top", 1.0, 6.0, 2.0, 7.0),
            ("forcefield", 2.0, 6.0, 3.0, 7.0),
            ("forcefield_charging1", 3.0, 6.0, 4.0, 7.0),
            ("forcefield_charging2", 4.0, 6.0, 5.0, 7.0),
            ("forcefield_charging3", 5.0, 6.0, 6.0, 7.0),
            ("door2_back", 0.0, 7.0, 1.0, 8.0),
            ("door_ledge", 1.0, 7.0, 2.0, 8.0),
            ("prize_dispenser_off", 2.0, 7.0, 3.0, 8.0),
            ("prize_dispenser", 3.0, 7.0, 4.0, 8.0),
            ("dice_machine_off", 4.0, 7.0, 5.0, 8.0),
            ("dice_machine", 5.0, 7.0, 6.0, 8.0),
            ("gambling_poster", 6.0, 6.0, 8.0, 8.0),
        ]),
    }
}
