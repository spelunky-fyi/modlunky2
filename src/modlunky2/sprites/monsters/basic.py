from pathlib import Path

from ..base_classes import BaseJsonSpriteLoader
from ..util import chunks_from_animation


class Basic1(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic01.png")
    _chunk_size = 128
    _chunk_map = {
        "snake": (0, 0, 1, 1),
        "bat": (6, 0, 7, 1),
        "fly": (12, 0, 13, 1),
        "skeleton": (0, 2, 1, 3),
        "spider": (0, 3, 1, 4),
        "ear": (0, 4, 1, 5),
        "shopkeep": (0, 6, 1, 7),
        "shopkeeper": (0, 6, 1, 7),
        "shopkeeper_clone": (0, 6, 1, 7),
        "ufo": (0, 8, 1, 9),
        "alien": (0, 9, 1, 10),
        "cobra": (0, 10, 1, 11),
        "scorpion": (0, 12, 1, 13),
        "golden_monkey": (14, 9, 15, 10),
        "monkey_gold": (14, 9, 15, 10),
        "bee": (9, 12, 10, 13),
        "magmar": (4, 14, 5, 15),
        "additional_golden_monkey_0": (11, 10, 12, 11),
        "additional_golden_monkey_1": (15, 10, 16, 11),
    }
    _entity_names = [
        "ENT_TYPE_MONS_SNAKE",
        "ENT_TYPE_MONS_BAT",
        "ENT_TYPE_ITEM_FLY",
        "ENT_TYPE_MONS_SKELETON",
        "ENT_TYPE_MONS_SPIDER",
        # "ENT_TYPE_MONS_EAR",  # :'(
        "ENT_TYPE_MONS_SHOPKEEPER",
        "ENT_TYPE_MONS_UFO",
        "ENT_TYPE_MONS_ALIEN",
        "ENT_TYPE_MONS_COBRA",
        "ENT_TYPE_MONS_SCORPION",
        "ENT_TYPE_MONS_GOLDMONKEY",
        "ENT_TYPE_MONS_BEE",
        "ENT_TYPE_MONS_MAGMAMAN",
    ]


class Basic2(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic02.png")
    _chunk_size = 128
    _chunk_map = {
        "vampire": (6, 1, 7, 2),
        "vlad": (6, 3, 7, 4),
        "caveman": (0, 5, 1, 6),
        "caveman_asleep": (8, 6, 9, 7),
        "bodyguard": (0, 8, 1, 9),
        "oldhunter": (0, 11, 1, 12),
        "leprechaun": (0, 13, 1, 14),
        "tun": (0, 14, 1, 15),
        "merchant": (0, 14, 1, 15),
        **chunks_from_animation("caveman_additional_0", (0, 7, 1, 8), 8),
        **chunks_from_animation("caveman_additional_1", (8, 7, 9, 8), 2),
    }
    _entity_names = [
        "ENT_TYPE_MONS_VAMPIRE",
        "ENT_TYPE_MONS_VLAD",
        "ENT_TYPE_MONS_LEPRECHAUN",
        "ENT_TYPE_MONS_CAVEMAN",
        "ENT_TYPE_MONS_BODYGUARD",
        "ENT_TYPE_MONS_OLD_HUNTER",
        "ENT_TYPE_MONS_MERCHANT",
    ]


class Basic3(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monstersbasic03.png")
    _chunk_size = 128
    _chunk_map = {
        "beg": (0, 0, 1, 1),
        "thief": (0, 1, 1, 2),
        "sister": (0, 5, 1, 6),
        "sister1": (0, 11, 1, 12),
        "sister2": (0, 8, 1, 9),
        "sister3": (0, 5, 1, 6),
        "yang": (0, 14, 1, 15),
    }
    _entity_names = [
        "ENT_TYPE_MONS_HUNDUNS_SERVANT",
        "ENT_TYPE_MONS_THIEF",
        "ENT_TYPE_MONS_SISTER_PARMESAN",
        "ENT_TYPE_MONS_SISTER_PARSLEY",
        "ENT_TYPE_MONS_SISTER_PARSNIP",
        "ENT_TYPE_MONS_YANG",
        "ENT_TYPE_FX_BIRDIES",
    ]


class Monsters1(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters01.png")
    _chunk_size = 128
    _chunk_map = {
        "robot": (0, 0, 1, 1),
        "imp": (4, 0, 5, 1),
        "witchdoctor": (0, 6, 1, 7),
        "critter_butterfly": (4, 7, 5, 8),
        "critter_dungbeetle": (4, 2, 5, 3),
        "critter_snail": (10, 1, 11, 2),
        "mantrap": (0, 8, 1, 9),
        "tikiman": (0, 9, 1, 10),
        "mosquito": (0, 14, 1, 15),
        "witchdoctor_additional_0": (12, 10, 13, 11),
        "witchdoctor_additional_1": (13, 10, 14, 11),
        "lizard": (9, 6, 10, 7),
        "spider_hanging": (6, 14, 7, 15),
        "mole": (0, 4, 1, 5),
        "monkey": (0, 13, 1, 14),
        "firebug": (0, 3, 1, 4),
    }
    _entity_names = [
        "ENT_TYPE_MONS_ROBOT",
        "ENT_TYPE_MONS_IMP",
        "ENT_TYPE_MONS_TIKIMAN",
        "ENT_TYPE_MONS_MANTRAP",
        "ENT_TYPE_MONS_CRITTERSNAIL",
        "ENT_TYPE_MONS_CRITTERDUNGBEETLE",
        "ENT_TYPE_MONS_FIREBUG",
        "ENT_TYPE_MONS_FIREBUG_UNCHAINED",
        "ENT_TYPE_MONS_MOLE",
        "ENT_TYPE_MONS_WITCHDOCTOR",
        "ENT_TYPE_MONS_CRITTERBUTTERFLY",
        "ENT_TYPE_MONS_HORNEDLIZARD",
        "ENT_TYPE_MONS_WITCHDOCTORSKULL",
        "ENT_TYPE_MONS_MONKEY",
        "ENT_TYPE_MONS_HANGSPIDER",
        "ENT_TYPE_MONS_MOSQUITO",
    ]


class Monsters2(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters02.png")
    _chunk_size = 128
    _chunk_map = {
        "jiangshi": (0, 0, 1, 1),
        "flying_fish": (0, 1, 1, 2),
        "assassin": (0, 6, 1, 7),
        "octopus": (0, 2, 1, 3),
        "hermitcrab": (11, 5, 12, 6),
        "crocman": (0, 8, 1, 9),
        "sorceress": (0, 10, 1, 11),
        "catmummy": (0, 11, 1, 12),
        "necromancer": (0, 12, 1, 13),
        "jiangshi_additional": (9, 0, 10, 1),
        "female_jiangshi_additional": (9, 6, 10, 7),
        "critter_fish": (13, 11, 14, 12),
        "critter_crab": (5, 5, 6, 6),
        "critter_locust": (9, 14, 10, 15),
        **chunks_from_animation("hermit_crab_additional_1", (10, 4, 11, 5), 6),
        **chunks_from_animation("hermit_crab_additional_2", (11, 5, 12, 6), 1),
        **chunks_from_animation("hermit_crab_additional_3", (12, 5, 13, 6), 4),
        **chunks_from_animation("blue_crab_1", (6, 13, 7, 14), 3),
        **chunks_from_animation("blue_crab_2", (9, 13, 10, 14), 3),
    }
    _entity_names = [
        "ENT_TYPE_MONS_JIANGSHI",
        "ENT_TYPE_MONS_HERMITCRAB",
        "ENT_TYPE_MONS_FISH",
        "ENT_TYPE_MONS_OCTOPUS",
        "ENT_TYPE_MONS_CRITTERCRAB",
        "ENT_TYPE_MONS_FEMALE_JIANGSHI",
        "ENT_TYPE_MONS_CRITTERFISH",
        "ENT_TYPE_MONS_CROCMAN",
        "ENT_TYPE_MONS_SORCERESS",
        "ENT_TYPE_MONS_CATMUMMY",
        "ENT_TYPE_MONS_CRITTERANCHOVY",
        "ENT_TYPE_MONS_NECROMANCER",
        "ENT_TYPE_MONS_CRITTERLOCUST",
    ]


class Monsters3(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters03.png")
    _chunk_size = 128
    _chunk_map = {
        "yeti": (0, 0, 1, 1),
        "proto_shopkeeper": (0, 2, 1, 3),
        "jumpdog": (0, 6, 1, 7),
        "grub": (10, 8, 11, 9),
        "tadpole": (0, 13, 1, 14),
        "olmite": (0, 8, 1, 9),
        "olmite_naked": (0, 7, 1, 8),
        "olmite_helmet": (0, 8, 1, 9),
        "olmite_armored": (0, 9, 1, 10),
        "eggsac": (7, 10, 8, 11),
        "eggsac_left": (7, 10, 8, 11),
        "eggsac_right": (7, 10, 8, 11),
        "eggsac_top": (7, 10, 8, 11),
        "eggsac_bottom": (7, 10, 8, 11),
        "frog": (0, 11, 1, 12),
        "frog_orange": (0, 12, 1, 13),
        "firefrog_dead_0": (5, 12, 6, 13),
        "firefrog_dead_1": (6, 12, 7, 13),
        "skull_drop_trap": (0, 15, 2, 16),
        "critter_penguin": (6, 3, 7, 4),
        "critter_firefly": (0, 3, 1, 4),
        "critter_drone": (1, 4, 2, 5),
        **chunks_from_animation("olmite_body_armored_1", (0, 8, 1, 9), 4),
        **chunks_from_animation("olmite_body_armored_2", (4, 8, 5, 9), 4),
        **chunks_from_animation("olmite_body_armored_3", (8, 8, 9, 9), 2),
        **chunks_from_animation("olmite_helmet_1", (0, 9, 1, 10), 4),
        **chunks_from_animation("olmite_helmet_2", (4, 9, 5, 10), 4),
        **chunks_from_animation("olmite_helmet_3", (8, 9, 9, 10), 2),
        **chunks_from_animation("olmite_helmet_4", (0, 10, 1, 11), 2),
        **chunks_from_animation("olmite_helmet_5", (2, 10, 3, 11), 4),
        **chunks_from_animation("olmite_helmet_6", (6, 10, 7, 11), 1),
    }
    _entity_names = [
        "ENT_TYPE_MONS_YETI",
        "ENT_TYPE_MONS_PROTOSHOPKEEPER",
        "ENT_TYPE_MONS_CRITTERFIREFLY",
        "ENT_TYPE_MONS_CRITTERPENGUIN",
        "ENT_TYPE_MONS_CRITTERDRONE",
        "ENT_TYPE_MONS_CRITTERSLIME",
        "ENT_TYPE_MONS_JUMPDOG",
        "ENT_TYPE_MONS_TADPOLE",
        "ENT_TYPE_MONS_OLMITE_NAKED",
        "ENT_TYPE_MONS_OLMITE_BODYARMORED",
        "ENT_TYPE_MONS_OLMITE_HELMET",
        "ENT_TYPE_MONS_GRUB",
        "ENT_TYPE_ITEM_EGGSAC",
        "ENT_TYPE_MONS_FROG",
        "ENT_TYPE_MONS_FIREFROG",
        # "ENT_TYPE_DECORATION_SKULLDROP_TRAP",  # ???
        # "ENT_TYPE_ITEM_SKULLDROPTRAP",  # ???
    ]
