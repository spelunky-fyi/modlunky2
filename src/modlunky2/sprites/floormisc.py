from pathlib import Path

from .base_classes import BaseSpriteLoader


class FloorMiscSheet(BaseSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/floormisc.png")
    _chunk_size = 128
    # Left, upper, right, lower
    # Note trying to match the names I see in the `.lvl` files for the names of these
    # things
    _chunk_map = {
        "push_block": (0, 0, 1, 1),
        "arrow_trap": (1, 0, 2, 1),
        "altar": (2, 0, 4, 1),
        "altar_trim_right": (2, 1, 3, 2),
        "altar_trim_left": (3, 1, 4, 2),
        "totemtrap": (4, 0, 5, 2),
        "liontrap": (5, 0, 6, 2),
        "sunken_arrowtrap": (6, 0, 7, 1),
        "spark_trap": (7, 0, 8, 1),
        "spark_trap_off": (7, 1, 8, 2),
        "minewood_platform_disconnected": (0, 1, 1, 2),
        "minewood_platform_connected": (1, 1, 2, 2),
        "minewood_scaffolding_disconnected1": (0, 2, 1, 3),
        "minewood_scaffolding_disconnected2": (0, 3, 2, 4),
        "minewood_scaffolding_connected1": (1, 2, 2, 3),
        "minewood_scaffolding_connected2": (1, 3, 2, 4),
        "cookfire": (6, 1, 7, 2),
        "powder_keg": (2, 2, 3, 3),
        "factory_generator": (3, 2, 4, 3),
        # Used when the top of a totem trap is broken
        "totemtrap_broken_edge": (4, 2, 5, 3),
        "liontrap_broken_edge": (5, 2, 6, 3),
        # Waddler storage floor
        "storage_floor": (6, 2, 7, 3),
        "storage_floor_activated": (7, 2, 8, 3),
        "elevator": (2, 3, 3, 4),
        "elevator_up": (3, 3, 4, 4),
        "elevator_down": (4, 3, 5, 4),
        "jungle_spear_trap": (5, 3, 6, 4),
        # Used when a platform is directly above the ground or another platform
        "tidepool_single_step_platform": (6, 3, 7, 4),
        "tidepool_platform_top": (7, 3, 8, 4),
        "tidepool_platform_middle": (7, 4, 8, 5),
        "tidepool_platform_bottom": (7, 5, 8, 6),
        "tidepool_platform_bottom_broken": (6, 4, 7, 5),
        "tidepool_platform_middle_broken": (6, 5, 7, 6),
        "crushtraplarge": (0, 4, 2, 6),
        "crushtrap": (0, 6, 1, 7),
        "lasertrap": (2, 4, 3, 5),
        "lasertrap_charging1": (3, 4, 4, 5),
        "lasertrap_charging2": (4, 4, 5, 5),
        "lasertrap_charged": (5, 4, 6, 5),
        "udjat_socket": (4, 5, 5, 6),
        "udjat_socket_filled": (5, 5, 6, 6),
        "udjat_socket_border": (2, 5, 3, 6),
        "udjat_socket_border_filled": (3, 5, 4, 6),
        "forcefield_top": (1, 6, 2, 7),
        "forcefield": (2, 6, 3, 7),
        "forcefield_charging1": (3, 6, 4, 7),
        "forcefield_charging2": (4, 6, 5, 7),
        "forcefield_charging3": (5, 6, 6, 7),
        # This is the door outline that is in the "background" layer to go to the
        # "front" layer
        "door2_back": (0, 7, 1, 8),
        # Ledge that keeps a door functional if ground is destroyed under it
        "door_ledge": (1, 7, 2, 8),
        "prize_dispenser_off": (2, 7, 3, 8),
        "prize_dispenser": (3, 7, 4, 8),
        "dice_machine_off": (4, 7, 5, 8),
        "dice_machine": (5, 7, 6, 8),
        "gambling_poster": (6, 6, 8, 8),
    }
