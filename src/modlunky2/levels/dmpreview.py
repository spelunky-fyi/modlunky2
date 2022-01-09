import argparse
from enum import IntEnum
import logging
from pathlib import Path
import re
from typing import List

from modlunky2.levels.level_file import LevelFile
from modlunky2.levels.level_templates import TemplateSetting

PREVIEW_WIDTH = 30
PREVIEW_HEIGHT = 15
NUM_ARENAS = 40
DMPREVIEW_SIZE = 18_000
ROOM_WIDTH = 10
ROOM_HEIGHT = 8
ARENA_SIZE = DMPREVIEW_SIZE // NUM_ARENAS
VALID_SIZES = set(
    [
        ("2", "2"),
        ("3", "2"),
    ]
)


class PreviewImages(IntEnum):
    EMPTY = 0xFF
    FLOOR = 0x00
    PUSH_BLOCK = 0x01
    CRATE = 0x02
    LADDER = 0x03
    VINES = 0x04
    CHAIN = 0x05
    POLE = 0x06
    SPIKES = 0x07
    CEILING_SPIKES = 0x08
    BONE_BLOCKS = 0x09
    SPEAR_TRAP = 0x0A
    FALLING_PLATFORM = 0x0B
    CONVEYER_LEFT = 0x0C
    CONVEYER_RIGHT = 0x0D
    TNT = 0x0E
    LIQUID = 0x0F
    CRUSH_TRAP = 0x10
    QUICK_SAND = 0x11
    ICE = 0x12
    SPRING = 0x13
    ELEVATOR = 0x14
    LASERS = 0x15
    SPARK_BALLS = 0x16
    REGEN_BLOCKS = 0x17
    TUBES = 0x18
    FOLIAGE = 0x19


ARENA_LEVEL_FILES = {
    level_filename: idx
    for idx, level_filename in enumerate(
        [
            "dm1-1.lvl",
            "dm1-2.lvl",
            "dm1-3.lvl",
            "dm1-4.lvl",
            "dm1-5.lvl",
            "dm2-1.lvl",
            "dm2-2.lvl",
            "dm2-3.lvl",
            "dm2-4.lvl",
            "dm2-5.lvl",
            "dm3-1.lvl",
            "dm3-2.lvl",
            "dm3-3.lvl",
            "dm3-4.lvl",
            "dm3-5.lvl",
            "dm4-1.lvl",
            "dm4-2.lvl",
            "dm4-3.lvl",
            "dm4-4.lvl",
            "dm4-5.lvl",
            "dm5-1.lvl",
            "dm5-2.lvl",
            "dm5-3.lvl",
            "dm5-4.lvl",
            "dm5-5.lvl",
            "dm6-1.lvl",
            "dm6-2.lvl",
            "dm6-3.lvl",
            "dm6-4.lvl",
            "dm6-5.lvl",
            "dm7-1.lvl",
            "dm7-2.lvl",
            "dm7-3.lvl",
            "dm7-4.lvl",
            "dm7-5.lvl",
            "dm8-1.lvl",
            "dm8-2.lvl",
            "dm8-3.lvl",
            "dm8-4.lvl",
            "dm8-5.lvl",
        ]
    )
}

ARENA_NAMES = [
    "Dwelling - Boneyard",
    "Dwelling - Ladders",
    "Dwelling - The Boss Room",
    "Dwelling - The Dig",
    "Dwelling - Apartments",
    "Jungle - Vines",
    "Jungle - Ruins",
    "Jungle - No Roots",
    "Jungle - Tower to Heaven",
    "Jungle - Prickly",
    "Volcana - Treadmill",
    "Volcana - Precarious",
    "Volcana - Smelter",
    "Volcana - Scrapyard",
    "Volcana - Chained",
    "Tide Pool - Clam Bake",
    "Tide Pool - Barrier Reef",
    "Tide Pool - Pole Dance",
    "Tide Pool - Two Houses",
    "Tide Pool - Eight Treasures",
    "Temple of Anubis - Roundabout",
    "Temple of Anubis - Pyramid",
    "Temple of Anubis - Burial Chamber",
    "Temple of Anubis - Grinder",
    "Temple of Anubis - Sandpit",
    "Ice Caves - Ice Box",
    "Ice Caves - Bounce House",
    "Ice Caves - Sprung",
    "Ice Caves - The Platform",
    "Ice Caves - Forgotten God",
    "Neo Babylon - Zap Cage",
    "Neo Babylon - Fungal",
    "Neo Babylon - Holy Mountain",
    "Neo Babylon - Neo City",
    "Neo Babylon - Power Plant",
    "Sunken City - Scar Tissue",
    "Sunken City - Indigestion",
    "Sunken City - Temple of Frog",
    "Sunken City - Pipe Dream",
    "Sunken City - Passions",
]

TILECODE_MAPPING = {
    "empty": PreviewImages.EMPTY,
    "babylon_floor": PreviewImages.FLOOR,
    "bone_block": PreviewImages.BONE_BLOCKS,
    "climbing_pole": PreviewImages.POLE,
    "conveyorbelt_left": PreviewImages.CONVEYER_LEFT,
    "conveyorbelt_right": PreviewImages.CONVEYER_RIGHT,
    "crate": PreviewImages.CRATE,
    "crushtrap": PreviewImages.CRUSH_TRAP,
    "crushtraplarge": PreviewImages.CRUSH_TRAP,
    "elevator": PreviewImages.ELEVATOR,
    "falling_platform": PreviewImages.FALLING_PLATFORM,
    "floor_hard": PreviewImages.EMPTY,
    "floor": PreviewImages.FLOOR,
    "forcefield_top": PreviewImages.LASERS,
    "forcefield": PreviewImages.LASERS,
    "icefloor": PreviewImages.ICE,
    "jungle_spear_trap": PreviewImages.SPEAR_TRAP,
    "ladder_plat": PreviewImages.LADDER,
    "ladder": PreviewImages.LADDER,
    "lava": PreviewImages.LIQUID,
    "minewood_floor": PreviewImages.FLOOR,
    "mushroom_base": PreviewImages.FOLIAGE,
    "pagoda_floor": PreviewImages.FLOOR,
    "pagoda_platform": PreviewImages.FLOOR,
    "pipe": PreviewImages.TUBES,
    "powder_keg": PreviewImages.TNT,
    "push_block": PreviewImages.PUSH_BLOCK,
    "quicksand": PreviewImages.QUICK_SAND,
    "regenerating_block": PreviewImages.REGEN_BLOCKS,
    "spark_trap": PreviewImages.SPARK_BALLS,
    "spikes": PreviewImages.SPIKES,
    "spring_trap": PreviewImages.SPRING,
    "stone_floor": PreviewImages.FLOOR,
    "sunken_floor": PreviewImages.FLOOR,
    "temple_floor": PreviewImages.FLOOR,
    "thinice": PreviewImages.ICE,
    "thorn_vine": PreviewImages.FLOOR,
    "timed_forcefield": PreviewImages.LASERS,
    "tree_base": PreviewImages.FOLIAGE,
    "upsidedown_spikes": PreviewImages.CEILING_SPIKES,
    "vine": PreviewImages.VINES,
    "water": PreviewImages.LIQUID,
    "chainandblocks_ceiling": PreviewImages.FLOOR,
    "factory_generator": PreviewImages.FLOOR,
    "slidingwall_ceiling": PreviewImages.FLOOR,
    # Double-check these
    "bigspear_trap": PreviewImages.EMPTY,
    "giantclam": PreviewImages.EMPTY,
    "giant_frog": PreviewImages.EMPTY,
    "fountain_drain": PreviewImages.EMPTY,
    "idol_hold": PreviewImages.EMPTY,
    "landmine": PreviewImages.EMPTY,
    "laser_trap": PreviewImages.EMPTY,
    "slidingwall_switch": PreviewImages.EMPTY,
}

EMPTY_TILECODES = set(
    {
        "cavemanboss",
        "cookfire",
        "dm_spawn_point",
    }
)


ROW_OFFSETS = {
    "setroom0-0": 0,
    "setroom0-1": 0,
    "setroom0-2": 0,
    "setroom1-0": 8,
    "setroom1-1": 8,
    "setroom1-2": 8,
}

COLUMN_OFFSETS = {
    ("small", "setroom0-0"): 5,
    ("small", "setroom0-1"): 15,
    ("small", "setroom1-0"): 5,
    ("small", "setroom1-1"): 15,
    ("large", "setroom0-0"): 0,
    ("large", "setroom0-1"): 10,
    ("large", "setroom0-2"): 20,
    ("large", "setroom1-0"): 0,
    ("large", "setroom1-1"): 10,
    ("large", "setroom1-2"): 20,
}


def _byte_chunks(bytes_, size):
    return [bytes_[idx : idx + size] for idx in range(0, len(bytes_), size)]


class Arena:
    def __init__(self, bytes_: List[str]):
        self.bytes = bytes_

    def pprint(self, header=None):
        if header is not None:
            print(header)

        for idx, byte_ in enumerate(self.bytes):
            print(f"{byte_:02x}", end=" ")
            if idx % PREVIEW_WIDTH == PREVIEW_WIDTH - 1:
                print("")

    @classmethod
    def from_level_file(cls, level_file: LevelFile):
        tile_codes = {}
        for tile_code in level_file.tile_codes.all():
            tile_name = re.split(r"%\d+", tile_code.name)[0]
            tile_codes[tile_code.value] = tile_name

        size = level_file.level_settings.get("size").value
        size_name = "large"
        if size == ("2", "2"):
            size_name = "small"
        bytes_ = [0xFF] * ARENA_SIZE

        for template in level_file.level_templates.all():

            chunk_idx = 0
            room = template.chunks[chunk_idx]
            while TemplateSetting.IGNORE in room.settings:
                chunk_idx += 1
                room = template.chunks[chunk_idx]

            row_offset = ROW_OFFSETS[template.name]
            column_offset = COLUMN_OFFSETS[(size_name, template.name)]

            for row_idx, row in enumerate(room.foreground):
                # The last row is never used in arena
                if template.name.startswith("setroom1-") and row_idx == 7:
                    continue

                flipped = False
                if TemplateSetting.ONLYFLIP in room.settings:
                    flipped = True
                    row.reverse()

                row_idx = row_idx + row_offset
                row_start = row_idx * PREVIEW_WIDTH

                for tile_idx, tile in enumerate(row):

                    byte_offset = row_start + column_offset + tile_idx
                    tile_name = tile_codes[tile]
                    if flipped:
                        if tile_name == "conveyorbelt_left":
                            tile_name = "conveyorbelt_right"
                        elif tile_name == "conveyorbelt_right":
                            tile_name = "conveyorbelt_left"

                    if tile_name in TILECODE_MAPPING:
                        byte_value = TILECODE_MAPPING[tile_name].value
                        if byte_value == 0xFF:
                            continue

                        bytes_[byte_offset] = byte_value
                        if tile_name in ("tree_base", "mushroom_base"):
                            bytes_[byte_offset - PREVIEW_WIDTH] = byte_value
                            bytes_[byte_offset - PREVIEW_WIDTH * 2] = byte_value
                            # Weird un-used tile
                            bytes_[byte_offset - PREVIEW_WIDTH * 3] = 0x1A
                        elif tile_name == "chainandblocks_ceiling":
                            bytes_[byte_offset + PREVIEW_WIDTH] = PreviewImages.CHAIN
                            bytes_[
                                byte_offset + PREVIEW_WIDTH * 2
                            ] = PreviewImages.CHAIN
                            bytes_[
                                byte_offset + PREVIEW_WIDTH * 3
                            ] = PreviewImages.CHAIN
                            bytes_[
                                byte_offset + PREVIEW_WIDTH * 4
                            ] = PreviewImages.CHAIN
                        elif tile_name == "crushtraplarge":
                            bytes_[byte_offset + 1] = PreviewImages.CRUSH_TRAP
                            bytes_[
                                byte_offset + PREVIEW_WIDTH
                            ] = PreviewImages.CRUSH_TRAP
                            bytes_[
                                byte_offset + PREVIEW_WIDTH + 1
                            ] = PreviewImages.CRUSH_TRAP

                    else:
                        if tile_name not in EMPTY_TILECODES:
                            logging.warning("Unknown Tilecode... %s", tile_name)

                        # bytes_[byte_offset] = PreviewImages.EMPTY

        if size_name == "small":
            padding = [0xFF] * PREVIEW_WIDTH * 2
            if bytes_[390:] == padding:
                bytes_ = padding + bytes_[:390]

        return cls(bytes_)


class DmPreviewTok:
    def __init__(self, arenas: List[Arena]):
        self.arenas = arenas

    @classmethod
    def from_path(cls, dmpreview_path):

        arenas = []

        with dmpreview_path.open("rb") as dmpreview:
            bytes_ = dmpreview.read()
            assert (
                len(bytes_) == DMPREVIEW_SIZE
            ), "Expected 18,000 bytes from dmpreview.tok"
            for chunk in _byte_chunks(bytes_, ARENA_SIZE):
                arenas.append(Arena(chunk))

        return cls(arenas)

    def pprint(self):
        for idx, arena in enumerate(self.arenas):
            arena.pprint(header=f"# {ARENA_NAMES[idx]}")
            print("")

    def write(self, out_path):
        bytes_ = bytearray()
        for arena in self.arenas:
            bytes_.extend(arena.bytes)

        assert len(bytes_) == DMPREVIEW_SIZE, "Expected 18,000 bytes from dmpreview.tok"

        with out_path.open("wb") as out_file:
            out_file.write(bytes_)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "levels_dir", type=Path, help="Path to Arena files to generate previews for"
    )
    parser.add_argument(
        "original_dmpreview", type=Path, help="Path to an original dmpreview.tok"
    )

    args = parser.parse_args()

    logging.basicConfig()

    dmpreviewtok = DmPreviewTok.from_path(args.original_dmpreview)

    for level_filepath in args.levels_dir.glob("dm*.lvl"):
        level_file = LevelFile.from_path(level_filepath)

        assert (
            level_file.level_settings.get("size").value in VALID_SIZES
        ), "Invalid Level Size"
        arena = Arena.from_level_file(level_file)

        arena_idx = ARENA_LEVEL_FILES[level_filepath.name]
        dmpreviewtok.arenas[arena_idx] = arena

    # dmpreviewtok.pprint()
    dmpreviewtok.write(Path("dmpreview.new.tok"))


if __name__ == "__main__":
    main()
