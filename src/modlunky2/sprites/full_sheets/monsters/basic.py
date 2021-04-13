from pathlib import Path

from modlunky2.sprites.base_classes.base_sprite_merger import BaseSpriteMerger
from modlunky2.sprites.monsters.basic import (
    Basic1,
    Basic2,
    Basic3,
    Monsters1,
    Monsters2,
    Monsters3,
)
from modlunky2.sprites.journal_mons import JournalMonsterSheet
from modlunky2.sprites.journal_people import JournalPeopleSheet
from modlunky2.sprites.journal_stickers import StickerSheet
from modlunky2.sprites.merger_factory import create_merger_factory_for_source_sheet
from modlunky2.sprites.util import chunks_from_animation


_basic1_factory = create_merger_factory_for_source_sheet(Basic1, JournalMonsterSheet)
SnakeSpriteMerger = _basic1_factory(
    "Monsters/snake", "journal_snake", ["ENT_TYPE_MONS_SNAKE"]
)
BatSpriteMerger = _basic1_factory("Monsters/bat", "journal_bat", ["ENT_TYPE_MONS_BAT"])
FlySpriteMerger = _basic1_factory("Monsters/fly", None, ["ENT_TYPE_ITEM_FLY"])
SkeletonSpriteMerger = _basic1_factory(
    "Monsters/skeleton", "journal_skeleton", ["ENT_TYPE_MONS_SKELETON"]
)
SpiderSpriteMerger = _basic1_factory(
    "Monsters/spider", "journal_spider", ["ENT_TYPE_MONS_SPIDER"]
)
# EarSpriteMerger = _basic1_factory("People/ear", None, [ "ENT_TYPE_MONS_EAR" ])  # RIP Ear
ShopkeeperSpriteMerger = _basic1_factory(
    "People/shopkeeper",
    None,
    ["ENT_TYPE_MONS_SHOPKEEPER"],
    additional_origins={
        JournalPeopleSheet: {"journal_shopkeeper": (0, 0, 1, 1)},
        StickerSheet: {"sticker_shopkeeper": (0, 0, 1, 1)},
    },
)
UfoSpriteMerger = _basic1_factory("Monsters/ufo", "journal_ufo", ["ENT_TYPE_MONS_UFO"])
AlienSpriteMerger = _basic1_factory(
    "Monsters/alien", "journal_alien", ["ENT_TYPE_MONS_ALIEN"]
)
CobraSpriteMerger = _basic1_factory(
    "Monsters/cobra", "journal_cobra", ["ENT_TYPE_MONS_COBRA"]
)
ScorpionSpriteMerger = _basic1_factory(
    "Monsters/scorpion", "journal_scorpion", ["ENT_TYPE_MONS_SCORPION"]
)
GoldenMonkeySpriteMerger = _basic1_factory(
    "Monsters/golden_monkey", "journal_golden_monkey", ["ENT_TYPE_MONS_GOLDMONKEY"],
    additional_origins={
        Basic1: {
            "additional_golden_monkey_0": (0, 0, 1, 1),
            "additional_golden_monkey_1": (1, 0, 2, 1),
        },
    },
)
BeeSpriteMerger = _basic1_factory("Monsters/bee", "journal_bee", ["ENT_TYPE_MONS_BEE"])
MagmarSpriteMerger = _basic1_factory(
    "Monsters/magmar", "journal_magmar", ["ENT_TYPE_MONS_MAGMAMAN"]
)

_basic2_factory = create_merger_factory_for_source_sheet(Basic2, JournalMonsterSheet)
VampireSpriteMerger = _basic2_factory(
    "Monsters/vampire", "journal_vampire", ["ENT_TYPE_MONS_VAMPIRE"]
)
VladSpriteMerger = _basic2_factory(
    "Monsters/vlad",
    None,
    ["ENT_TYPE_MONS_VLAD"],
    additional_origins={
        JournalMonsterSheet: {"journal_vlad": (0, 0, 1, 1)},
        StickerSheet: {"sticker_vlad": (0, 0, 1, 1)},
    },
)
LeprechaunSpriteMerger = _basic2_factory(
    "Monsters/leprechaun", "journal_leprechaun", ["ENT_TYPE_MONS_LEPRECHAUN"]
)
CaveManSpriteMerger = _basic2_factory(
    "Monsters/cave_man",
    None,
    ["ENT_TYPE_MONS_CAVEMAN"],
    additional_origins={
        Basic2: {
            **chunks_from_animation("caveman_additional_0", (0, 0, 1, 1), 8),
            **chunks_from_animation("caveman_additional_1", (0, 1, 1, 2), 2),
        },
        JournalMonsterSheet: {"journal_cave_man": (0, 0, 1, 1)},
        StickerSheet: {"sticker_cave_man": (0, 0, 1, 1)}
    },
)
BodyguardSpriteMerger = _basic2_factory(
    "People/bodyguard",
    "journal_tusks_bodyguard",
    ["ENT_TYPE_MONS_BODYGUARD"],
    journal_sheet_override=JournalPeopleSheet,
)
OldHunterSpriteMerger = _basic2_factory(
    "People/old_hunter",
    None,
    ["ENT_TYPE_MONS_OLD_HUNTER"],
    additional_origins={
        JournalPeopleSheet: {"journal_van_horsing": (0, 0, 1, 1)},
        StickerSheet: {"sticker_van_horsing": (0, 0, 1, 1)},
    },
)
MerchantSpriteMerger = _basic2_factory(
    "People/merchant",
    None,
    ["ENT_TYPE_MONS_MERCHANT"],
    additional_origins={
        JournalPeopleSheet: {"journal_tun": (0, 0, 1, 1)},
        StickerSheet: {"sticker_tun": (0, 0, 1, 1)},
    },
)

_basic3_factory = create_merger_factory_for_source_sheet(Basic3, JournalPeopleSheet)
HundunsServantSpriteMerger = _basic3_factory(
    "People/hunduns_servant",
    "journal_beg",
    ["ENT_TYPE_MONS_HUNDUNS_SERVANT"],
)
ThiefSpriteMerger = _basic3_factory(
    "People/thief",
    None,
    ["ENT_TYPE_MONS_THIEF"],
    additional_origins={
        JournalPeopleSheet: {"journal_sparrow": (0, 0, 1, 1)},
        StickerSheet: {"sticker_sparrow": (0, 0, 1, 1)},
    },
)
ParmesanSpriteMerger = _basic3_factory(
    "People/parmesan",
    None,
    ["ENT_TYPE_MONS_SISTER_PARMESAN"],
    additional_origins={
        JournalPeopleSheet: {"journal_parmesan": (0, 0, 1, 1)},
        StickerSheet: {"sticker_parmesan": (0, 0, 1, 1)},
    },
)
ParsleySpriteMerger = _basic3_factory(
    "People/parsley",
    None,
    ["ENT_TYPE_MONS_SISTER_PARSLEY"],
    additional_origins={
        JournalPeopleSheet: {"journal_parsley": (0, 0, 1, 1)},
        StickerSheet: {"sticker_parsley": (0, 0, 1, 1)},
    },
)
ParsnipSpriteMerger = _basic3_factory(
    "People/parsnip",
    None,
    ["ENT_TYPE_MONS_SISTER_PARSNIP"],
    additional_origins={
        JournalPeopleSheet: {"journal_parsnip": (0, 0, 1, 1)},
        StickerSheet: {"sticker_parsnip": (0, 0, 1, 1)},
    },
)
YangSpriteMerger = _basic3_factory(
    "People/yang",
    None,
    ["ENT_TYPE_MONS_YANG"],
    additional_origins={
        JournalPeopleSheet: {"journal_yang": (0, 0, 1, 1)},
        StickerSheet: {"sticker_yang": (0, 0, 1, 1)},
    },
)
BirdiesSpriteMerger = _basic3_factory(
    "Critters/birdies",
    None,
    ["ENT_TYPE_FX_BIRDIES"],
)

_monsters1_factory = create_merger_factory_for_source_sheet(
    Monsters1, JournalMonsterSheet
)
RobotSpriteMerger = _monsters1_factory(
    "Monsters/robot",
    "journal_robot",
    ["ENT_TYPE_MONS_ROBOT"],
)
ImpSpriteMerger = _monsters1_factory(
    "Monsters/imp",
    "journal_imp",
    ["ENT_TYPE_MONS_IMP"],
)
ManTrapSpriteMerger = _monsters1_factory(
    "Monsters/man_trap",
    "journal_man_trap",
    ["ENT_TYPE_MONS_MANTRAP"],
)
TikiManSpriteMerger = _monsters1_factory(
    "Monsters/tiki_man",
    "journal_tiki_man",
    ["ENT_TYPE_MONS_TIKIMAN"],
)
CritterSnailSpriteMerger = _monsters1_factory(
    "Critters/snail",
    None,
    ["ENT_TYPE_MONS_CRITTERSNAIL"],
)
CritterDungBeetleSpriteMerger = _monsters1_factory(
    "Critters/dung_beetle",
    None,
    ["ENT_TYPE_MONS_CRITTERDUNGBEETLE"],
)
FireBugSpriteMerger = _monsters1_factory(
    "Monsters/fire_bug",
    "journal_fire_bug",
    ["ENT_TYPE_MONS_FIREBUG", "ENT_TYPE_MONS_FIREBUG_UNCHAINED"],
)
MoleSpriteMerger = _monsters1_factory(
    "Monsters/mole",
    "journal_mole",
    ["ENT_TYPE_MONS_MOLE"],
)
WitchDoctorSpriteMerger = _monsters1_factory(
    "Monsters/witch_doctor",
    "journal_witch_doctor",
    ["ENT_TYPE_MONS_WITCHDOCTOR"],
    additional_origins={
        Monsters1: {
            "witchdoctor_additional_0": (0, 0, 1, 1),
            "witchdoctor_additional_1": (1, 0, 2, 1),
        },
    },
)
CritterButterflySpriteMerger = _monsters1_factory(
    "Critters/butterfly",
    None,
    ["ENT_TYPE_MONS_CRITTERBUTTERFLY"],
)
HornedLizardSpriteMerger = _monsters1_factory(
    "Monsters/horned_lizard",
    "journal_horned_lizard",
    ["ENT_TYPE_MONS_HORNEDLIZARD"],
)
WitchDoctorSkullSpriteMerger = _monsters1_factory(
    "Monsters/witch_doctor_skull",
    None,
    ["ENT_TYPE_MONS_WITCHDOCTORSKULL"],
)
MonkeySpriteMerger = _monsters1_factory(
    "Monsters/monkey",
    "journal_monkey",
    ["ENT_TYPE_MONS_MONKEY"],
)
HangSpiderSpriteMerger = _monsters1_factory(
    "Monsters/hang_spider",
    "journal_hang_spider",
    ["ENT_TYPE_MONS_HANGSPIDER"],
)
MosquitoSpriteMerger = _monsters1_factory(
    "Monsters/mosquito",
    "journal_mosquito",
    ["ENT_TYPE_MONS_MOSQUITO"],
)

_monsters2_factory = create_merger_factory_for_source_sheet(
    Monsters2, JournalMonsterSheet
)
JiangshiSpriteMerger = _monsters2_factory(
    "Monsters/jiangshi",
    "journal_jiangshi",
    ["ENT_TYPE_MONS_JIANGSHI"],
    additional_origins={
        Monsters2: {
            "jiangshi_additional": (0, 0, 1, 1),
        },
    },
)
HermitCrabSpriteMerger = _monsters2_factory(
    "Monsters/hermit_crab",
    "journal_hermit_crab",
    ["ENT_TYPE_MONS_HERMITCRAB"],
    additional_origins={
        Monsters2: {
            **chunks_from_animation("hermit_crab_additional_1", (0, 0, 1, 1), 6),
            **chunks_from_animation("hermit_crab_additional_2", (6, 0, 7, 1), 1),
            **chunks_from_animation("hermit_crab_additional_3", (0, 1, 1, 2), 4),
        },
    },
)
FlyingFishSpriteMerger = _monsters2_factory(
    "Monsters/flying_fish",
    "journal_flying_fish",
    ["ENT_TYPE_MONS_FISH"],
)
OctopusSpriteMerger = _monsters2_factory(
    "Monsters/octopus",
    "journal_octopy",
    ["ENT_TYPE_MONS_OCTOPUS"],
)
CritterCrabSpriteMerger = _monsters2_factory(
    "Critters/crab",
    None,
    ["ENT_TYPE_MONS_CRITTERCRAB"],
)
class CritterBlueCrabSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Critters/blue_crab.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Monsters2: {
            **chunks_from_animation("blue_crab_1", (0, 0, 1, 1), 3),
            **chunks_from_animation("blue_crab_2", (0, 1, 1, 2), 3),
        }
    }
FemaleJiangshiSpriteMerger = _monsters2_factory(
    "Monsters/female_jiangshi",
    "journal_jiangshi_assassin",
    ["ENT_TYPE_MONS_FEMALE_JIANGSHI"],
    additional_origins={
        Monsters2: {
            "female_jiangshi_additional": (0, 0, 1, 1),
        },
    },
)
CritterFishSpriteMerger = _monsters2_factory(
    "Critters/fish",
    None,
    ["ENT_TYPE_MONS_CRITTERFISH"],
)
CrocManSpriteMerger = _monsters2_factory(
    "Monsters/croc_man",
    "journal_croc_man",
    ["ENT_TYPE_MONS_CROCMAN"],
)
SorceressSpriteMerger = _monsters2_factory(
    "Monsters/sorceress",
    "journal_sorceress",
    ["ENT_TYPE_MONS_SORCERESS"],
)
CatMummySpriteMerger = _monsters2_factory(
    "Monsters/cat_mummy",
    "journal_cat_mummy",
    ["ENT_TYPE_MONS_CATMUMMY"],
)
CritterAnchovySpriteMerger = _monsters2_factory(
    "Critters/anchovy",
    None,
    ["ENT_TYPE_MONS_CRITTERANCHOVY"],
)
NecromancerSpriteMerger = _monsters2_factory(
    "Monsters/necromancer",
    "journal_necromancer",
    ["ENT_TYPE_MONS_NECROMANCER"],
)
CrittersLocustSpriteMerger = _monsters2_factory(
    "Critters/locust",
    None,
    ["ENT_TYPE_MONS_CRITTERLOCUST"],
)

_monsters3_factory = create_merger_factory_for_source_sheet(
    Monsters3, JournalMonsterSheet
)
YetiSpriteMerger = _monsters3_factory(
    "Monsters/yeti",
    "journal_yeti",
    ["ENT_TYPE_MONS_YETI"],
)
ProtoShopkeeperSpriteMerger = _monsters3_factory(
    "Monsters/proto_shopkeeper",
    "journal_proto_shopkeeper",
    ["ENT_TYPE_MONS_PROTOSHOPKEEPER"],
)
CritterFireflySpriteMerger = _monsters3_factory(
    "Critters/firefly",
    None,
    ["ENT_TYPE_MONS_CRITTERFIREFLY"],
)
PenguinSpriteMerger = _monsters3_factory(
    "Critters/penguin",
    None,
    ["ENT_TYPE_MONS_CRITTERPENGUIN"],
)
DroneSpriteMerger = _monsters3_factory(
    "Critters/drone",
    None,
    ["ENT_TYPE_MONS_CRITTERDRONE"],
)
SlimeSpriteMerger = _monsters3_factory(
    "Critters/slime",
    None,
    ["ENT_TYPE_MONS_CRITTERSLIME"],
)
JumpdogSpriteMerger = _monsters3_factory(
    "Monsters/jumpdog",
    "journal_egg_plup",
    ["ENT_TYPE_MONS_JUMPDOG"],
)
TadpoleSpriteMerger = _monsters3_factory(
    "Monsters/tadpole",
    "journal_tadpole",
    ["ENT_TYPE_MONS_TADPOLE"],
)
OlmiteNakedSpriteMerger = _monsters3_factory(
    "Monsters/olmite_naked",
    "journal_olmite",
    ["ENT_TYPE_MONS_OLMITE_NAKED"],
)
class OlmitedArmoredSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Monsters/olmite_armored.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Monsters3: {
            **chunks_from_animation("olmite_body_armored_1", (0, 0, 1, 1), 4),
            **chunks_from_animation("olmite_body_armored_2", (0, 1, 1, 2), 4),
            **chunks_from_animation("olmite_body_armored_3", (0, 2, 1, 3), 2),
        }
    }
class OlmiteHelmetSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Monsters/olmite_helmet.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        Monsters3: {
            **chunks_from_animation("olmite_helmet_1", (0, 0, 1, 1), 4),
            **chunks_from_animation("olmite_helmet_2", (0, 1, 1, 2), 4),
            **chunks_from_animation("olmite_helmet_3", (0, 2, 1, 3), 2),
            **chunks_from_animation("olmite_helmet_4", (2, 2, 3, 3), 2),
            **chunks_from_animation("olmite_helmet_5", (0, 3, 1, 4), 4),
            **chunks_from_animation("olmite_helmet_6", (0, 4, 1, 5), 1),
        }
    }
GrubSpriteMerger = _monsters3_factory(
    "Monsters/grub",
    "journal_grub",
    ["ENT_TYPE_MONS_GRUB", "ENT_TYPE_ITEM_EGGSAC"],
)
FrogSpriteMerger = _monsters3_factory(
    "Monsters/frog",
    "journal_frog",
    ["ENT_TYPE_MONS_FROG"],
)
FireFrogSpriteMerger = _monsters3_factory(
    "Monsters/fire_frog",
    "journal_fire_frog",
    ["ENT_TYPE_MONS_FIREFROG"],
    additional_origins={
        Monsters3: {
            "firefrog_dead_0": (0, 0, 1, 1),
            "firefrog_dead_1": (1, 0, 2, 1),
        },
    },
)
