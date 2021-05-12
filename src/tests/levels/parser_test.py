# pylint: disable=protected-access

from io import StringIO
from collections import OrderedDict
from pathlib import Path

from modlunky2.levels import (
    LevelFile,
    LevelSetting,
    TileCode,
    LevelChance,
    MonsterChance,
    LevelTemplate,
)
from modlunky2.levels.level_templates import TemplateSetting, Chunk


def test_parser():
    with (Path(__file__).parent / "test-level-in.lvl").open(
        "r", encoding="cp1252"
    ) as handle:
        level_file = LevelFile.from_handle(handle)

    assert level_file.comment == (
        "// ------------------------------\n"
        "//  AREA EIGHT (COSMIC OCEAN) - SUNKEN CITY\n"
        "// ------------------------------\n"
    )

    assert level_file.level_settings._inner == OrderedDict(
        [
            (
                "back_room_chance",
                LevelSetting(
                    name="back_room_chance",
                    value=0,
                    comment="% chance of a second room (default = 5%)",
                ),
            ),
            (
                "back_room_interconnection_chance",
                LevelSetting(
                    name="back_room_interconnection_chance",
                    value=0,
                    comment="% chance of a second room interconnection (default = 20%)",
                ),
            ),
            (
                "back_room_hidden_door_chance",
                LevelSetting(
                    name="back_room_hidden_door_chance",
                    value=0,
                    comment="1/N chance of a hidden door (default = 500)",
                ),
            ),
            (
                "back_room_hidden_door_cache_chance",
                LevelSetting(
                    name="back_room_hidden_door_cache_chance",
                    value=0,
                    comment="1/N chance of a hidden door to a cache (default = 1000)",
                ),
            ),
            (
                "mount_chance",
                LevelSetting(
                    name="mount_chance",
                    value=0,
                    comment="1/N chance of a mount (default = 5000)",
                ),
            ),
            (
                "altar_room_chance",
                LevelSetting(
                    name="altar_room_chance",
                    value=0,
                    comment="1/N chance of an altar room (default = 14)",
                ),
            ),
            (
                "idol_room_chance",
                LevelSetting(
                    name="idol_room_chance",
                    value=0,
                    comment="1/N chance of an idol room (default = 10)",
                ),
            ),
            (
                "floor_side_spread_chance",
                LevelSetting(
                    name="floor_side_spread_chance",
                    value=0,
                    comment="1/N chance of a spreadable floor spreading to its side (default = 10)",
                ),
            ),
            (
                "floor_bottom_spread_chance",
                LevelSetting(
                    name="floor_bottom_spread_chance",
                    value=0,
                    comment="1/N chance of a spreadable floor spreading to its bottom (default = 5)",
                ),
            ),
            (
                "max_liquid_particles",
                LevelSetting(
                    name="max_liquid_particles",
                    value=2000,
                    comment="Maximum number of liquid drops that can be created until no more liquid rooms are allowed",
                ),
            ),
            (
                "flagged_liquid_rooms",
                LevelSetting(
                    name="flagged_liquid_rooms",
                    value=7,
                    comment="Number of random rooms that will be flagged for being eligible to spawn liquid",
                ),
            ),
            (
                "liquid_gravity",
                LevelSetting(
                    name="liquid_gravity",
                    value=10.0,
                    comment="Liquid vertical gravity (default -10.0)",
                ),
            ),
            (
                "machine_bigroom_chance",
                LevelSetting(
                    name="machine_bigroom_chance",
                    value=0,
                    comment="1/N chance of spawning a machine big room (default = 0)",
                ),
            ),
            (
                "machine_wideroom_chance",
                LevelSetting(
                    name="machine_wideroom_chance",
                    value=0,
                    comment="1/N chance of spawning a machine wide room (default = 0)",
                ),
            ),
            (
                "machine_tallroom_chance",
                LevelSetting(
                    name="machine_tallroom_chance",
                    value=0,
                    comment="1/N chance of spawning a machine tall room (default = 0)",
                ),
            ),
            (
                "machine_rewardroom_chance",
                LevelSetting(
                    name="machine_rewardroom_chance",
                    value=0,
                    comment="1/N chance of spawning a machine reward room (default = 0)",
                ),
            ),
        ]
    )

    assert level_file.tile_codes._inner == OrderedDict(
        [
            ("chunk_ground", TileCode(name="chunk_ground", value="5", comment="")),
            ("chunk_air", TileCode(name="chunk_air", value="6", comment="")),
            (
                "chunk_door",
                TileCode(
                    name="chunk_door",
                    value="8",
                    comment="Chunk with entrance or exit in it",
                ),
            ),
            ("empty", TileCode(name="empty", value="0", comment="")),
            ("floor", TileCode(name="floor", value="1", comment="")),
            (
                "floor%50",
                TileCode(
                    name="floor%50",
                    value="2",
                    comment="50% chance of floor, 50% chance of empty",
                ),
            ),
            ("sunken_floor", TileCode(name="sunken_floor", value="=", comment="")),
            (
                "sunken_floor%50",
                TileCode(name="sunken_floor%50", value="-", comment=""),
            ),
            (
                "floor_hard",
                TileCode(
                    name="floor_hard",
                    value="X",
                    comment='Indestructible ("hard") floor',
                ),
            ),
            (
                "floor_hard%50%floor",
                TileCode(
                    name="floor_hard%50%floor",
                    value="Y",
                    comment="50% chance of hard floor, 50% chance of regular floor",
                ),
            ),
            (
                "adjacent_floor",
                TileCode(
                    name="adjacent_floor",
                    value="Z",
                    comment="Hard floor or empty depending on whether this leads to another second layer room",
                ),
            ),
            ("door", TileCode(name="door", value="9", comment="Exit or entrance")),
            ("door2", TileCode(name="door2", value="D", comment="Door to other Layer")),
            (
                "treasure",
                TileCode(
                    name="treasure",
                    value="t",
                    comment="Gold (30%), gem (30%), treasure chest (20%), crate (10%), bones/pot (5%), or nothing (5%)",
                ),
            ),
            ("spikes", TileCode(name="spikes", value="^", comment="")),
            ("push_block", TileCode(name="push_block", value="4", comment="")),
            ("pipe", TileCode(name="pipe", value="p", comment="")),
            (
                "regenerating_block",
                TileCode(name="regenerating_block", value="r", comment=""),
            ),
            ("bigspear_trap", TileCode(name="bigspear_trap", value="C", comment="")),
            ("bone_block", TileCode(name="bone_block", value="f", comment="")),
            ("sticky_trap", TileCode(name="sticky_trap", value="B", comment="")),
            (
                "altar",
                TileCode(name="altar", value="x", comment="Each side of the altar"),
            ),
            ("idol", TileCode(name="idol", value="I", comment="Idol statue")),
            (
                "vault_wall",
                TileCode(name="vault_wall", value="|", comment="Vault wall"),
            ),
            (
                "coffin",
                TileCode(
                    name="coffin", value="g", comment="Character coffin (NPC/Player)"
                ),
            ),
            ("shop_sign", TileCode(name="shop_sign", value="K", comment="")),
            ("shop_door", TileCode(name="shop_door", value="k", comment="")),
            ("lamp_hang", TileCode(name="lamp_hang", value="l", comment="")),
            ("shop_wall", TileCode(name="shop_wall", value=".", comment="")),
            ("shop_item", TileCode(name="shop_item", value="S", comment="")),
            ("wanted_poster", TileCode(name="wanted_poster", value="W", comment="")),
            (
                "shopkeeper",
                TileCode(name="shopkeeper", value="$", comment="Shopkeeper and items"),
            ),
            (
                "storage_guy",
                TileCode(name="storage_guy", value="G", comment="Storage guy"),
            ),
            (
                "storage_floor",
                TileCode(name="storage_floor", value="q", comment="Storage floors"),
            ),
            ("autowalltorch", TileCode(name="autowalltorch", value="M", comment="")),
            ("mother_statue", TileCode(name="mother_statue", value="s", comment="")),
            ("eggplant_door", TileCode(name="eggplant_door", value="U", comment="")),
            ("giant_frog", TileCode(name="giant_frog", value="n", comment="")),
            ("guts_floor", TileCode(name="guts_floor", value="T", comment="")),
            ("water", TileCode(name="water", value="w", comment="")),
        ]
    )

    assert level_file.level_chances._inner == OrderedDict(
        [
            (
                "arrowtrap_chance",
                LevelChance(name="arrowtrap_chance", value=35, comment=""),
            ),
            (
                "bigspeartrap_chance",
                LevelChance(name="bigspeartrap_chance", value=35, comment=""),
            ),
            (
                "stickytrap_chance",
                LevelChance(name="stickytrap_chance", value=25, comment=""),
            ),
            (
                "skulldrop_chance",
                LevelChance(name="skulldrop_chance", value=10, comment=""),
            ),
            ("eggsac_chance", LevelChance(name="eggsac_chance", value=20, comment="")),
        ]
    )

    assert level_file.monster_chances._inner == OrderedDict(
        [
            ("frog", MonsterChance(name="frog", value=30, comment="")),
            ("firefrog", MonsterChance(name="firefrog", value=50, comment="")),
            ("tadpole", MonsterChance(name="tadpole", value=30, comment="")),
            ("giantfly", MonsterChance(name="giantfly", value=40, comment="")),
            ("critterslime", MonsterChance(name="critterslime", value=60, comment="")),
        ]
    )

    expected_level_templates = OrderedDict(
        [
            (
                "entrance",
                LevelTemplate(
                    name="entrance",
                    comment="",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["=", "=", "0", "0", "=", "=", "=", "=", "=", "="],
                                ["1", "1", "0", "0", "=", "=", "=", "=", "=", "1"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "r", "r", "1", "1", "1", "1", "0", "0"],
                                ["0", "r", "r", "r", "0", "0", "0", "r", "r", "0"],
                                ["0", "1", "r", "1", "0", "0", "0", "r", "r", "0"],
                                ["1", "1", "1", "1", "0", "9", "0", "1", "r", "1"],
                                ["0", "0", "1", "1", "1", "1", "1", "1", "1", "1"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["0", "0", "0", "r", "r", "r", "0", "0", "0", "0"],
                                ["0", "0", "0", "r", "1", "r", "0", "0", "0", "0"],
                                ["0", "p", "1", "1", "1", "1", "1", "=", "1", "0"],
                                ["0", "p", "p", "p", "p", "p", "p", "p", "1", "0"],
                                ["0", "r", "1", "1", "0", "0", "0", "p", "1", "0"],
                                ["0", "r", "1", "1", "0", "0", "0", "0", "1", "0"],
                                ["0", "0", "p", "p", "0", "9", "0", "0", "1", "1"],
                                ["0", "0", "p", "1", "1", "1", "1", "1", "1", "1"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
            (
                "exit",
                LevelTemplate(
                    name="exit",
                    comment="",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[],
                            foreground=[
                                ["-", "=", "=", "=", "=", "=", "=", "=", "=", "="],
                                ["0", "0", "2", "=", "=", "=", "=", "2", "0", "0"],
                                ["0", "0", "0", "=", "=", "=", "=", "0", "0", "0"],
                                ["0", "0", "=", "=", "=", "=", "=", "=", "0", "0"],
                                ["0", "0", "0", "8", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["1", "1", "=", "=", "=", "=", "=", "=", "1", "2"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[],
                            foreground=[
                                ["1", "1", "1", "1", "1", "1", "1", "1", "0", "0"],
                                ["0", "0", "8", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "r", "=", "=", "=", "=", "=", "=", "r", "0"],
                                ["0", "r", "0", "0", "0", "0", "0", "0", "r", "0"],
                                ["r", "r", "=", "0", "0", "0", "=", "r", "r", "0"],
                                ["0", "0", "=", "0", "0", "0", "=", "1", "1", "0"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
            (
                "side",
                LevelTemplate(
                    name="side",
                    comment="",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["0", "0", "p", "1", "1", "1", "1", "1", "0", "0"],
                                ["0", "2", "p", "1", "1", "1", "2", "1", "1", "1"],
                                ["0", "p", "p", "0", "0", "0", "0", "1", "1", "1"],
                                ["0", "p", "0", "0", "0", "0", "0", "1", "0", "0"],
                                ["0", "p", "0", "0", "0", "0", "0", "r", "0", "0"],
                                ["0", "p", "p", "0", "1", "1", "0", "r", "0", "0"],
                                ["0", "2", "1", "1", "1", "1", "1", "1", "1", "1"],
                                ["0", "0", "0", "1", "1", "1", "0", "0", "0", "0"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="// Room",
                            settings=[TemplateSetting.FLIP, TemplateSetting.LIQUID],
                            foreground=[
                                ["=", "=", "=", "=", "=", "=", "0", "0", "0", "0"],
                                ["=", "w", "w", "w", "=", "=", "=", "=", "=", "0"],
                                ["=", "w", "=", "w", "=", "w", "w", "w", "=", "0"],
                                ["=", "w", "=", "w", "w", "w", "w", "w", "=", "0"],
                                ["=", "w", "=", "=", "w", "w", "=", "w", "=", "0"],
                                ["0", "0", "C", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "=", "=", "=", "0", "0", "0", "0", "=", "="],
                                ["0", "0", "-", "0", "0", "0", "0", "0", "=", "="],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["=", "1", "1", "1", "1", "1", "=", "=", "=", "="],
                                ["0", "0", "r", "r", "r", "r", "r", "r", "0", "0"],
                                ["=", "=", "1", "r", "r", "r", "r", "1", "=", "="],
                                ["0", "2", "1", "1", "1", "1", "1", "1", "2", "0"],
                                ["0", "0", "2", "1", "1", "1", "1", "2", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
                                ["1", "1", "0", "0", "0", "0", "0", "0", "1", "1"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
            (
                "coffin_player",
                LevelTemplate(
                    name="coffin_player",
                    comment="Coffin room holding a dead player (both sides must be open)",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[],
                            foreground=[
                                ["=", "=", "1", "=", "=", "=", "=", "=", "=", "="],
                                ["=", "p", "p", "0", "0", "0", "0", "0", "0", "="],
                                ["=", "p", "1", "0", "0", "0", "0", "g", "0", "="],
                                ["1", "p", "1", "1", "=", "=", "=", "=", "=", "="],
                                ["0", "p", "1", "0", "0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0", "0", "1", "1", "0", "0"],
                                ["1", "1", "1", "1", "=", "=", "=", "=", "=", "="],
                                ["1", "1", "1", "1", "1", "1", "1", "1", "1", "1"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[],
                            foreground=[
                                ["=", "=", "=", "=", "=", "=", "=", "1", "=", "="],
                                ["=", "0", "0", "0", "0", "0", "0", "p", "p", "="],
                                ["=", "g", "0", "0", "0", "0", "0", "1", "p", "="],
                                ["=", "=", "=", "=", "=", "=", "1", "1", "p", "1"],
                                ["0", "0", "0", "0", "0", "0", "0", "1", "p", "0"],
                                ["0", "0", "1", "1", "0", "0", "0", "0", "0", "0"],
                                ["=", "=", "=", "=", "=", "=", "1", "1", "1", "1"],
                                ["1", "1", "1", "1", "1", "1", "1", "1", "1", "1"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
            (
                "chunk_door",
                LevelTemplate(
                    name="chunk_door",
                    comment="",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["0", "0", "0", "0", "0", "0"],
                                ["0", "0", "0", "9", "0", "="],
                                ["2", "=", "=", "=", "=", "="],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["0", "0", "0", "0", "0", "0"],
                                ["0", "0", "9", "0", "=", "0"],
                                ["=", "=", "=", "=", "=", "0"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["0", "0", "0", "0", "0", "0"],
                                ["0", "=", "0", "9", "0", "0"],
                                ["=", "=", "=", "=", "=", "2"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
            (
                "chunk_ground",
                LevelTemplate(
                    name="chunk_ground",
                    comment="",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.IGNORE],
                            foreground=[
                                ["0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.LIQUID, TemplateSetting.FLIP],
                            foreground=[
                                ["1", "r", "1", "1", "1"],
                                ["1", "w", "w", "w", "r"],
                                ["1", "w", "w", "w", "1"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["2", "p", "1", "1", "2"],
                                ["1", "p", "p", "p", "0"],
                                ["1", "1", "1", "1", "1"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
            (
                "chunk_air",
                LevelTemplate(
                    name="chunk_air",
                    comment="",
                    chunks=[
                        Chunk(
                            comment="",
                            settings=[],
                            foreground=[
                                ["0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0"],
                                ["0", "0", "0", "0", "0"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[],
                            foreground=[
                                ["0", "0", "0", "0", "0"],
                                ["0", "r", "r", "r", "0"],
                                ["0", "0", "0", "0", "0"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["1", "1", "1", "0", "0"],
                                ["2", "2", "2", "0", "0"],
                                ["0", "0", "0", "0", "0"],
                            ],
                            background=[],
                        ),
                        Chunk(
                            comment="",
                            settings=[TemplateSetting.FLIP],
                            foreground=[
                                ["1", "2", "1", "2", "1"],
                                ["1", "0", "1", "0", "1"],
                                ["2", "0", "2", "0", "2"],
                            ],
                            background=[],
                        ),
                    ],
                ),
            ),
        ]
    )

    assert level_file.level_templates._inner.keys() == expected_level_templates.keys()
    for key, value in expected_level_templates.items():
        assert level_file.level_templates._inner[key] == value


def test_write_no_changes():
    with (Path(__file__).parent / "test-level-in.lvl").open(
        "r", encoding="cp1252"
    ) as handle:
        level_file = LevelFile.from_handle(handle)

    out_handle = StringIO()
    level_file.write(out_handle)
    out_handle.seek(0)
    with (Path(__file__).parent / "test-level-out-1.lvl").open(
        "r", encoding="cp1252"
    ) as handle:
        expected_out = handle.read()

    assert out_handle.getvalue() == expected_out


def test_write_comments():
    with (Path(__file__).parent / "test-level-in.lvl").open(
        "r", encoding="cp1252"
    ) as handle:
        level_file = LevelFile.from_handle(handle)

    level_file.comment = None
    level_file.level_templates._inner["coffin_player"].comment = None
    level_file.tile_codes._inner["vault_wall"].comment = " // Vault Wall"

    out_handle = StringIO()
    level_file.write(out_handle)
    out_handle.seek(0)
    with (Path(__file__).parent / "test-level-out-2.lvl").open(
        "r", encoding="cp1252"
    ) as handle:
        expected_out = handle.read()

    assert out_handle.getvalue() == expected_out
