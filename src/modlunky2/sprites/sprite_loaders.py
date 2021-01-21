from .items import ItemSheet
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


def get_all_sprite_loaders(base_path: str):
    return [
        ItemSheet(base_path),
        StickerSheet(base_path),
        JournalItemSheet(base_path),
        JournalPeopleSheet(base_path),
        JournalMonsterSheet(base_path),
        JournalBigMonsterSheet(base_path),
        JournalPlaceSheet(base_path),
        JournalTrapSheet(base_path),
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
        Mounts(base_path),
        Pets(base_path),
    ]
