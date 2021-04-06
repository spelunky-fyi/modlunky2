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


_basic1_factory = create_merger_factory_for_source_sheet(Basic1, JournalMonsterSheet)
SnakeSpriteMerger = _basic1_factory(
    "monsters/snake", "journal_snake", ["ENT_TYPE_MONS_SNAKE"]
)
BatSpriteMerger = _basic1_factory("monsters/bat", "journal_bat", ["ENT_TYPE_MONS_BAT"])
FlySpriteMerger = _basic1_factory("monsters/fly", None, ["ENT_TYPE_ITEM_FLY"])
SkeletonSpriteMerger = _basic1_factory(
    "monsters/skeleton", "journal_skeleton", ["ENT_TYPE_MONS_SKELETON"]
)
SpiderSpriteMerger = _basic1_factory(
    "monsters/spider", "journal_spider", ["ENT_TYPE_MONS_SPIDER"]
)
# EarSpriteMerger = _basic1_factory("people/ear", None, [ "ENT_TYPE_MONS_EAR" ])  # RIP Ear
ShopkeeperSpriteMerger = _basic1_factory(
    "people/shopkeeper",
    None,
    ["ENT_TYPE_MONS_SHOPKEEPER"],
    additional_origins={
        JournalPeopleSheet: {"journal_shopkeeper": (0, 0, 1, 1)},
        StickerSheet: {"sticker_shopkeeper": (0, 0, 1, 1)},
    },
)
UfoSpriteMerger = _basic1_factory("monsters/ufo", "journal_ufo", ["ENT_TYPE_MONS_UFO"])
AlienSpriteMerger = _basic1_factory(
    "monsters/alien", "journal_alien", ["ENT_TYPE_MONS_ALIEN"]
)
CobraSpriteMerger = _basic1_factory(
    "monsters/cobra", "journal_cobra", ["ENT_TYPE_MONS_COBRA"]
)
ScorpionSpriteMerger = _basic1_factory(
    "monsters/scorpion", "journal_scorpion", ["ENT_TYPE_MONS_SCORPION"]
)
GoldenMonkeySpriteMerger = _basic1_factory(
    "monsters/golden_monkey", "journal_golden_monkey", ["ENT_TYPE_MONS_GOLDMONKEY"]
)
BeeSpriteMerger = _basic1_factory("monsters/bee", "journal_bee", ["ENT_TYPE_MONS_BEE"])
MagmarSpriteMerger = _basic1_factory(
    "monsters/magmar", "journal_magmar", ["ENT_TYPE_MONS_MAGMAMAN"]
)

_basic2_factory = create_merger_factory_for_source_sheet(Basic2, JournalMonsterSheet)
VampireSpriteMerger = _basic2_factory(
    "monsters/vampire", "journal_vampire", ["ENT_TYPE_MONS_VAMPIRE"]
)
VladSpriteMerger = _basic2_factory(
    "monsters/vlad",
    None,
    ["ENT_TYPE_MONS_VLAD"],
    additional_origins={
        JournalMonsterSheet: {"journal_vlad": (0, 0, 1, 1)},
        StickerSheet: {"sticker_vlad": (0, 0, 1, 1)},
    },
)
LeprechaunSpriteMerger = _basic2_factory(
    "monsters/leprechaun", "journal_leprechaun", ["ENT_TYPE_MONS_LEPRECHAUN"]
)
CaveManSpriteMerger = _basic2_factory(
    "monsters/cave_man",
    None,
    ["ENT_TYPE_MONS_CAVEMAN"],
    additional_origins={
        JournalMonsterSheet: {"journal_cave_man": (0, 0, 1, 1)},
        JournalPeopleSheet: {"journal_cave_man_shopkeeper": (0, 0, 1, 1)},
        StickerSheet: {"sticker_cave_man": (0, 0, 1, 1)},
    },
)
BodyguardSpriteMerger = _basic2_factory(
    "people/bodyguard",
    "journal_tusks_bodyguard",
    ["ENT_TYPE_MONS_BODYGUARD"],
    journal_sheet_override=JournalPeopleSheet,
)
OldHunterSpriteMerger = _basic2_factory(
    "people/old_hunter",
    None,
    ["ENT_TYPE_MONS_OLD_HUNTER"],
    additional_origins={
        JournalPeopleSheet: {"journal_van_horsing": (0, 0, 1, 1)},
        StickerSheet: {"sticker_van_horsing": (0, 0, 1, 1)},
    },
)
MerchantSpriteMerger = _basic2_factory(
    "people/merchant",
    None,
    ["ENT_TYPE_MONS_MERCHANT"],
    additional_origins={
        JournalPeopleSheet: {"journal_tun": (0, 0, 1, 1)},
        StickerSheet: {"sticker_tun": (0, 0, 1, 1)},
    },
)

_basic3_factory = create_merger_factory_for_source_sheet(Basic3, JournalPeopleSheet)
HundunsServantSpriteMerger = _basic3_factory(
    "people/hunduns_servant",
    "journal_beg",
    ["ENT_TYPE_MONS_HUNDUNS_SERVANT"],
)
ThiefSpriteMerger = _basic3_factory(
    "people/thief",
    None,
    ["ENT_TYPE_MONS_THIEF"],
    additional_origins={
        JournalPeopleSheet: {"journal_sparrow": (0, 0, 1, 1)},
        StickerSheet: {"sticker_sparrow": (0, 0, 1, 1)},
    },
)
ParmesanSpriteMerger = _basic3_factory(
    "people/parmesan",
    None,
    ["ENT_TYPE_MONS_SISTER_PARMESAN"],
    additional_origins={
        JournalPeopleSheet: {"journal_parmesan": (0, 0, 1, 1)},
        StickerSheet: {"sticker_parmesan": (0, 0, 1, 1)},
    },
)
ParsleySpriteMerger = _basic3_factory(
    "people/parslet",
    None,
    ["ENT_TYPE_MONS_SISTER_PARSLEY"],
    additional_origins={
        JournalPeopleSheet: {"journal_parsley": (0, 0, 1, 1)},
        StickerSheet: {"sticker_parsley": (0, 0, 1, 1)},
    },
)
ParsnipSpriteMerger = _basic3_factory(
    "people/parsnip",
    None,
    ["ENT_TYPE_MONS_SISTER_PARSNIP"],
    additional_origins={
        JournalPeopleSheet: {"journal_parsnip": (0, 0, 1, 1)},
        StickerSheet: {"sticker_parsnip": (0, 0, 1, 1)},
    },
)
YanSpriteMerger = _basic3_factory(
    "people/yang",
    None,
    ["ENT_TYPE_MONS_YANG"],
    additional_origins={
        JournalPeopleSheet: {"journal_yang": (0, 0, 1, 1)},
        StickerSheet: {"sticker_yang": (0, 0, 1, 1)},
    },
)

_monsters1_factory = create_merger_factory_for_source_sheet(
    Monsters1, JournalMonsterSheet
)
RobotSpriteMerger = _monsters1_factory(
    "monsters/robot",
    "journal_robot",
    ["ENT_TYPE_MONS_ROBOT"],
)
ImpSpriteMerger = _monsters1_factory(
    "monsters/imp",
    "journal_imp",
    ["ENT_TYPE_MONS_IMP"],
)
ManTrapSpriteMerger = _monsters1_factory(
    "monsters/man_trap",
    "journal_man_trap",
    ["ENT_TYPE_MONS_MANTRAP"],
)
TikiManSpriteMerger = _monsters1_factory(
    "monsters/tiki_man",
    "journal_tiki_man",
    ["ENT_TYPE_MONS_TIKIMAN"],
)
CritterSnailSpriteMerger = _monsters1_factory(
    "critters/snail",
    None,
    ["ENT_TYPE_MONS_CRITTERSNAIL"],
)
CritterDungBeetleSpriteMerger = _monsters1_factory(
    "critters/dung_beetle",
    None,
    ["ENT_TYPE_MONS_CRITTERDUNGBEETLE"],
)
FireBugSpriteMerger = _monsters1_factory(
    "monsters/fire_bug",
    "journal_fire_bug",
    ["ENT_TYPE_MONS_FIREBUG", "ENT_TYPE_MONS_FIREBUG_UNCHAINED"],
)
MoleSpriteMerger = _monsters1_factory(
    "monsters/mole",
    "journal_mole",
    ["ENT_TYPE_MONS_MOLE"],
)
WitchDoctorSpriteMerger = _monsters1_factory(
    "monsters/witch_doctor",
    "journal_witch_doctor",
    ["ENT_TYPE_MONS_WITCHDOCTOR"],
)
CritterButterflySpriteMerger = _monsters1_factory(
    "critters/butterfly",
    None,
    ["ENT_TYPE_MONS_CRITTERBUTTERFLY"],
)
HornedLizardSpriteMerger = _monsters1_factory(
    "monsters/horned_lizard",
    "journal_horned_lizard",
    ["ENT_TYPE_MONS_HORNEDLIZARD"],
)
WitchDoctorSkullSpriteMerger = _monsters1_factory(
    "monsters/witch_doctor_skull",
    None,
    ["ENT_TYPE_MONS_WITCHDOCTORSKULL"],
)
MonkeySpriteMerger = _monsters1_factory(
    "monsters/monkey",
    "journal_monkey",
    ["ENT_TYPE_MONS_MONKEY"],
)
HangSpiderSpriteMerger = _monsters1_factory(
    "monsters/hang_spider",
    "journal_hang_spider",
    ["ENT_TYPE_MONS_HANGSPIDER"],
)
MosquitoSpriteMerger = _monsters1_factory(
    "monsters/mosquito",
    "journal_mosquito",
    ["ENT_TYPE_MONS_MOSQUITO"],
)

_monsters2_factory = create_merger_factory_for_source_sheet(
    Monsters2, JournalMonsterSheet
)
JiangshiSpriteMerger = _monsters2_factory(
    "monsters/jiangshi",
    "journal_jiangshi",
    ["ENT_TYPE_MONS_JIANGSHI"],
)
HermitCrabSpriteMerger = _monsters2_factory(
    "monsters/hermit_crab",
    "journal_hermit_crab",
    ["ENT_TYPE_MONS_HERMITCRAB"],
)
FlyingFishSpriteMerger = _monsters2_factory(
    "monsters/flying_fish",
    "journal_flying_fish",
    ["ENT_TYPE_MONS_FISH"],
)
OctopusSpriteMerger = _monsters2_factory(
    "monsters/octopus",
    "journal_octopy",
    ["ENT_TYPE_MONS_OCTOPUS"],
)
CritterCrabSpriteMerger = _monsters2_factory(
    "critters/crab",
    None,
    ["ENT_TYPE_MONS_CRITTERCRAB"],
)
FemaleJiangshiSpriteMerger = _monsters2_factory(
    "monsters/female_jiangshi",
    "journal_jiangshi_assassin",
    ["ENT_TYPE_MONS_FEMALE_JIANGSHI"],
)
CritterFishSpriteMerger = _monsters2_factory(
    "critters/fish",
    None,
    ["ENT_TYPE_MONS_CRITTERFISH"],
)
CrocManSpriteMerger = _monsters2_factory(
    "monsters/croc_man",
    "journal_croc_man",
    ["ENT_TYPE_MONS_CROCMAN"],
)
SorceressSpriteMerger = _monsters2_factory(
    "monsters/sorceress",
    "journal_sorceress",
    ["ENT_TYPE_MONS_SORCERESS"],
)
CatMummySpriteMerger = _monsters2_factory(
    "monsters/cat_mummy",
    "journal_cat_mummy",
    ["ENT_TYPE_MONS_CATMUMMY"],
)
CritterAnchovySpriteMerger = _monsters2_factory(
    "critters/anchovy",
    None,
    ["ENT_TYPE_MONS_CRITTERANCHOVY"],
)
NecromancerSpriteMerger = _monsters2_factory(
    "monsters/necromancer",
    "journal_necromancer",
    ["ENT_TYPE_MONS_NECROMANCER"],
)
CrittersLocustSpriteMerger = _monsters2_factory(
    "critters/locust",
    None,
    ["ENT_TYPE_MONS_CRITTERLOCUST"],
)

_monsters3_factory = create_merger_factory_for_source_sheet(
    Monsters3, JournalMonsterSheet
)
YetiSpriteMerger = _monsters3_factory(
    "monsters/yeti",
    "journal_yeti",
    ["ENT_TYPE_MONS_YETI"],
)
ProtoShopkeeperSpriteMerger = _monsters3_factory(
    "monsters/proto_shopkeeper",
    "journal_proto_shopkeeper",
    ["ENT_TYPE_MONS_PROTOSHOPKEEPER"],
)
CritterFireflySpriteMerger = _monsters3_factory(
    "critters/firefly",
    None,
    ["ENT_TYPE_MONS_CRITTERFIREFLY"],
)
SpriteMerger = _monsters3_factory(
    "critters/penguin",
    None,
    ["ENT_TYPE_MONS_CRITTERPENGUIN"],
)
SpriteMerger = _monsters3_factory(
    "critters/drone",
    None,
    ["ENT_TYPE_MONS_CRITTERDRONE"],
)
SpriteMerger = _monsters3_factory(
    "critters/slime",
    None,
    ["ENT_TYPE_MONS_CRITTERSLIME"],
)
JumpdogSpriteMerger = _monsters3_factory(
    "monsters/jumpdog",
    "journal_egg_plup",
    ["ENT_TYPE_MONS_JUMPDOG"],
)
TadpoleSpriteMerger = _monsters3_factory(
    "monsters/tadpole",
    "journal_tadpole",
    ["ENT_TYPE_MONS_TADPOLE"],
)
OlmiteNakedSpriteMerger = _monsters3_factory(
    "monsters/olmite_naked",
    "journal_olmite",
    ["ENT_TYPE_MONS_OLMITE_NAKED"],
)
OlmitedArmoredSpriteMerger = _monsters3_factory(
    "monsters/olmite_armored",
    None,
    ["ENT_TYPE_MONS_OLMITE_BODYARMORED"],
)
OlmiteHelmetSpriteMerger = _monsters3_factory(
    "monsters/olmite_helmet",
    None,
    ["ENT_TYPE_MONS_OLMITE_HELMET"],
)
GrubSpriteMerger = _monsters3_factory(
    "monsters/grub",
    "journal_grub",
    ["ENT_TYPE_MONS_GRUB", "ENT_TYPE_ITEM_EGGSAC"],
)
FrogSpriteMerger = _monsters3_factory(
    "monsters/frog",
    "journal_frog",
    ["ENT_TYPE_MONS_FROG"],
)
FireFrogSpriteMerger = _monsters3_factory(
    "monsters/fire_frog",
    "journal_fire_frog",
    ["ENT_TYPE_MONS_FIREFROG"],
)
