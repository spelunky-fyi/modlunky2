from typing import Optional

from modlunky2.constants import BASE_DIR

from modlunky2.sprites.items import ItemSheet
from modlunky2.sprites.coffins import CoffinSheet
from modlunky2.sprites.journal_stickers import StickerSheet
from modlunky2.sprites.journal_items import JournalItemSheet
from modlunky2.sprites.journal_people import JournalPeopleSheet
from modlunky2.sprites.journal_mons import JournalMonsterSheet
from modlunky2.sprites.journal_mons_big import JournalBigMonsterSheet
from modlunky2.sprites.journal_place import JournalPlaceSheet
from modlunky2.sprites.journal_traps import JournalTrapSheet
from modlunky2.sprites.character import (
    CharacterBlackSheet,
    CharacterBlueSheet,
    CharacterCeruleanSheet,
    CharacterCinnabarSheet,
    CharacterCyanSheet,
    CharacterEggChildSheet,
    CharacterGoldSheet,
    CharacterGraySheet,
    CharacterGreenSheet,
    CharacterHiredHandSheet,
    CharacterIrisSheet,
    CharacterKhakiSheet,
    CharacterLemonSheet,
    CharacterLimeSheet,
    CharacterMagentaSheet,
    CharacterOliveSheet,
    CharacterOrangeSheet,
    CharacterPinkSheet,
    CharacterRedSheet,
    CharacterVioletSheet,
    CharacterWhiteSheet,
    CharacterYellowSheet,
)
from modlunky2.sprites.monsters.mounts import Mounts
from modlunky2.sprites.monsters.pets import Pets
from modlunky2.sprites.monsters.ghost import Ghost
from modlunky2.sprites.monsters.basic import (
    Basic1,
    Basic2,
    Basic3,
    Monsters1,
    Monsters2,
    Monsters3,
)
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
from modlunky2.sprites.tilecode_extras import (
    EXTRA_TILECODE_CLASSES,
    TilecodeExtras,
)
from modlunky2.sprites.menu_leader import MenuLeaderSheet
from modlunky2.sprites.menu_basic import MenuBasicSheet, PetHeadsSheet
from modlunky2.sprites.deco_sheet import CaveDecoSheet


def get_all_sprite_loaders(
    entities_json: Optional[dict], textures_json: Optional[dict], base_path: str
):
    return [
        ItemSheet(base_path),
        CoffinSheet(base_path),
        StickerSheet(base_path),
        JournalItemSheet(base_path),
        JournalPeopleSheet(base_path),
        JournalMonsterSheet(base_path),
        JournalBigMonsterSheet(base_path),
        JournalPlaceSheet(base_path),
        JournalTrapSheet(base_path),
        CharacterBlackSheet(base_path),
        CharacterLimeSheet(base_path),
        CharacterMagentaSheet(base_path),
        CharacterOliveSheet(base_path),
        CharacterOrangeSheet(base_path),
        CharacterPinkSheet(base_path),
        CharacterRedSheet(base_path),
        CharacterVioletSheet(base_path),
        CharacterWhiteSheet(base_path),
        CharacterYellowSheet(base_path),
        CharacterBlueSheet(base_path),
        CharacterCeruleanSheet(base_path),
        CharacterCinnabarSheet(base_path),
        CharacterCyanSheet(base_path),
        CharacterEggChildSheet(base_path),
        CharacterGoldSheet(base_path),
        CharacterGraySheet(base_path),
        CharacterGreenSheet(base_path),
        CharacterHiredHandSheet(base_path),
        CharacterIrisSheet(base_path),
        CharacterKhakiSheet(base_path),
        CharacterLemonSheet(base_path),
        Mounts(entities_json, textures_json, base_path),
        Pets(entities_json, textures_json, base_path),
        MenuLeaderSheet(base_path),
        MenuBasicSheet(base_path),
        PetHeadsSheet(BASE_DIR / "static"),
        Basic1(entities_json, textures_json, base_path),
        Basic2(entities_json, textures_json, base_path),
        Basic3(entities_json, textures_json, base_path),
        Monsters1(entities_json, textures_json, base_path),
        Monsters2(entities_json, textures_json, base_path),
        Monsters3(entities_json, textures_json, base_path),
        Big1(entities_json, textures_json, base_path),
        Big2(entities_json, textures_json, base_path),
        Big3(entities_json, textures_json, base_path),
        Big4(entities_json, textures_json, base_path),
        Big5(entities_json, textures_json, base_path),
        Big6(entities_json, textures_json, base_path),
        OsirisAndAlienQueen(entities_json, textures_json, base_path),
        OlmecAndMech(entities_json, textures_json, base_path),
        Ghost(entities_json, textures_json, base_path),
        CaveDecoSheet(base_path),
        # These uses the constant BASE_DIR as the base path as this
        # texture is bundled with the source rather than coming
        # from the extracted assets.
        TilecodeExtras(BASE_DIR),
    ] + [class_(BASE_DIR) for class_ in EXTRA_TILECODE_CLASSES]
