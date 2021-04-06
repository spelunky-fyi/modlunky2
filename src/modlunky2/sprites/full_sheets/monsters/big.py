from modlunky2.sprites.monsters.big import (
    Big1,
    Big2,
    Big3,
    Big4,
    Big5,
    Big6,
    OsirisAndAlienQueen,
    OlmecAndMech,
)
from modlunky2.sprites.journal_mons_big import JournalBigMonsterSheet
from modlunky2.sprites.journal_people import JournalPeopleSheet
from modlunky2.sprites.journal_traps import JournalTrapSheet
from modlunky2.sprites.journal_stickers import StickerSheet
from modlunky2.sprites.merger_factory import create_merger_factory_for_source_sheet
from modlunky2.sprites.util import chunks_from_animation


_big1_factory = create_merger_factory_for_source_sheet(Big1, JournalBigMonsterSheet)
QuillbackSpriteMerger = _big1_factory(
    "BigMonsters/quill_back",
    None,
    ["ENT_TYPE_MONS_CAVEMAN_BOSS"],
    additional_origins={
        JournalBigMonsterSheet: {"journal_quill_back": (0, 0, 1, 1)},
        StickerSheet: {"sticker_quill_back": (0, 0, 2, 2)},
    },
)
GiantSpiderSpriteMerger = _big1_factory(
    "BigMonsters/giant_spider", "journal_giant_spider", ["ENT_TYPE_MONS_GIANTSPIDER"]
)
QueenBeeSpriteMerger = _big1_factory(
    "BigMonsters/queen_bee", "journal_queen_bee", ["ENT_TYPE_MONS_QUEENBEE"]
)

_big2_factory = create_merger_factory_for_source_sheet(Big2, JournalBigMonsterSheet)
MummySpriteMerger = _big2_factory(
    "BigMonsters/mummy", "journal_mummy", ["ENT_TYPE_MONS_MUMMY"]
)
AnubisSpriteMerger = _big2_factory(
    "BigMonsters/anubis", "journal_anubis", ["ENT_TYPE_MONS_ANUBIS"]
)
Anubis2SpriteMerger = _big2_factory(
    "BigMonsters/anubis_2", "journal_anubis_2", ["ENT_TYPE_MONS_ANUBIS2"]
)

_big3_factory = create_merger_factory_for_source_sheet(Big3, JournalBigMonsterSheet)
LamassuSpriteMerger = _big3_factory(
    "BigMonsters/lamassu", "journal_lamassu", ["ENT_TYPE_MONS_LAMASSU"]
)
YetiKingSpriteMerger = _big3_factory(
    "BigMonsters/yeti_king", "journal_yeti_king", ["ENT_TYPE_MONS_YETIKING"]
)
YetiQueenSpriteMerger = _big3_factory(
    "BigMonsters/yeti_queen", "journal_yeti_queen", ["ENT_TYPE_MONS_YETIQUEEN"]
)

_big4_factory = create_merger_factory_for_source_sheet(Big4, JournalBigMonsterSheet)
CrabManSpriteMerger = _big4_factory(
    "BigMonsters/crab_man", "journal_panxie", ["ENT_TYPE_MONS_CRABMAN"]
)
LavamanderSpriteMerger = _big4_factory(
    "BigMonsters/lavamander", "journal_lavamander", ["ENT_TYPE_MONS_LAVAMANDER"]
)
GiantFlySpriteMerger = _big4_factory(
    "BigMonsters/giant_fly",
    "journal_giant_fly",
    ["ENT_TYPE_MONS_GIANTFLY", "ENT_TYPE_ITEM_GIANTFLY_HEAD"],
)
GiantClamSpriteMerger = _big4_factory(
    "BigMonsters/giant_clam",
    None,
    ["ENT_TYPE_ITEM_GIANTCLAM_TOP", "ENT_TYPE_ACTIVEFLOOR_GIANTCLAM_BASE"],
    additional_origins={JournalTrapSheet: {"journal_giant_clam": (0, 0, 2, 2)}},
)

_big5_factory = create_merger_factory_for_source_sheet(Big5, JournalBigMonsterSheet)
AmmitSpriteMerger = _big5_factory(
    "BigMonsters/ammit", "journal_ammit", ["ENT_TYPE_MONS_AMMIT"]
)
MadameTuskSpriteMerger = _big5_factory(
    "BigMonsters/madame_tusk",
    None,
    ["ENT_TYPE_MONS_MADAMETUSK"],
    additional_origins={JournalPeopleSheet: {"journal_madame_tusk": (0, 0, 2, 2)}},
)
EggplantMinisterSpriteMerger = _big5_factory(
    "BigMonsters/eggplant_minister",
    "journal_eggplant_minister",
    ["ENT_TYPE_MONS_EGGPLANT_MINISTER"],
    additional_origins={
        Big5: {
            **chunks_from_animation("minister_small_walk", (0, 0, 1, 1), 4),
            **chunks_from_animation("minister_small_walk", (0, 1, 1, 2), 3, 4),
        }
    },
)
GiantFrogSpriteMerger = _big5_factory(
    "BigMonsters/giant_frog", "journal_goliath_frog", ["ENT_TYPE_MONS_GIANTFROG"]
)

_big6_factory = create_merger_factory_for_source_sheet(Big6, JournalBigMonsterSheet)
GiantFishSpriteMerger = _big6_factory(
    "BigMonsters/giant_fish", "journal_great_humphead", ["ENT_TYPE_MONS_GIANTFISH"]
)
KinguSpriteMerger = _big6_factory(
    "BigMonsters/kingu",
    None,
    [
        "ENT_TYPE_ACTIVEFLOOR_KINGU_PLATFORM",
        "ENT_TYPE_FX_KINGU_HEAD",
        "ENT_TYPE_FX_KINGU_LIMB",
        "ENT_TYPE_FX_KINGU_PLATFORM",
        "ENT_TYPE_FX_KINGU_SHADOW",
        "ENT_TYPE_FX_KINGU_HEAD",
    ],
    additional_origins={
        JournalBigMonsterSheet: {"journal_kingu": (0, 0, 1, 1)},
        StickerSheet: {"sticker_kingu": (0, 0, 2, 2)},
    },
)
StorageGuySpriteMerger = _big6_factory(
    "BigMonsters/waddler",
    None,
    ["ENT_TYPE_MONS_STORAGEGUY"],
    additional_origins={JournalPeopleSheet: {"journal_waddler": (0, 0, 2, 2)}},
)

_osiris_factory = create_merger_factory_for_source_sheet(
    OsirisAndAlienQueen, JournalBigMonsterSheet
)
OsirisSpriteMerger = _osiris_factory(
    "BigMonsters/osiris",
    None,
    ["ENT_TYPE_MONS_OSIRIS_HEAD", "ENT_TYPE_MONS_OSIRIS_HAND"],
    additional_origins={
        JournalBigMonsterSheet: {"journal_osiris": (0, 0, 1, 1)},
        StickerSheet: {"sticker_osiris": (0, 0, 2, 2)},
    },
)
AlienQueenSpriteMerger = _osiris_factory(
    "BigMonsters/alien_queen",
    None,
    [
        "ENT_TYPE_MONS_ALIENQUEEN",
        "ENT_TYPE_FX_ALIENQUEEN_EYE",
        "ENT_TYPE_FX_ALIENQUEEN_EYEBALL",
    ],
    additional_origins={
        JournalBigMonsterSheet: {"journal_lahamu": (0, 0, 1, 1)},
        StickerSheet: {"sticker_lahamu": (0, 0, 2, 2)},
    },
)

_olmec_factory = create_merger_factory_for_source_sheet(
    OlmecAndMech, JournalBigMonsterSheet
)
OlmecSpriteMerger = _olmec_factory(
    "BigMonsters/olmec",
    None,
    [
        "ENT_TYPE_FX_OLMECPART_FLOATER",
        "ENT_TYPE_FX_OLMECPART_LARGE",
        "ENT_TYPE_FX_OLMECPART_MEDIUM",
        "ENT_TYPE_FX_OLMECPART_SMALL",
        "ENT_TYPE_FX_OLMECPART_SMALLEST",
    ],
    additional_origins={
        JournalBigMonsterSheet: {"journal_olmec": (0, 0, 1, 1)},
        StickerSheet: {"sticker_olmec": (0, 0, 2, 2)},
    },
)
MechSpriteMerger = _olmec_factory(
    "Mounts/mech",
    None,
    ["ENT_TYPE_MOUNT_MECH", "ENT_TYPE_FX_MECH_COLLAR"],
)
