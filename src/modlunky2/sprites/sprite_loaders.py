from modlunky2.constants import BASE_DIR

from .items import ItemSheet
from .coffins import CoffinSheet
from .deco_extra import DecoExtraSheet
from .base_eggship2 import EggShip2Sheet
from .journal_stickers import StickerSheet
from .journal_items import JournalItemSheet
from .journal_people import JournalPeopleSheet
from .journal_mons import JournalMonsterSheet
from .journal_mons_big import JournalBigMonsterSheet
from .journal_place import JournalPlaceSheet
from .journal_traps import JournalTrapSheet
from .character import *
from .monsters.mounts import Mounts
from .monsters.pets import Pets
from .monsters.basic import Basic1, Basic2, Basic3, Monsters1, Monsters2, Monsters3
from .monsters.big import (
    Big1,
    Big2,
    Big3,
    Big4,
    Big5,
    Big6,
    OsirisAndAlienQueen,
    OlmecAndMech,
)
from .tilecode_extras import TilecodeExtras
from .menu_leader import MenuLeaderSheet


def get_all_sprite_loaders(entities_json: dict, textures_json: dict, base_path: str):
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
        # This uses the constant BASE_DIR as the base path as this
        # texture is bundled with the source rather than coming
        # from the extracted assets.
        TilecodeExtras(BASE_DIR),
    ]
