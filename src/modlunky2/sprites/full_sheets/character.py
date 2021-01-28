from pathlib import Path

from ..base_classes.base_sprite_merger import BaseSpriteMerger
from ..character import *
from ..journal_people import JournalPeopleSheet
from ..journal_stickers import StickerSheet


def _create_class_for_character(color: str, character_sheet_type: type):
    class CharacterSpriteMerger(BaseSpriteMerger):
        _target_sprite_sheet_path = Path(
            "Data/Textures/Entities/char_{}_full.png".format(color)
        )
        _grid_hint_size = 8
        _origin_map = {
            character_sheet_type: character_sheet_type._chunk_map,
            JournalPeopleSheet: {"journal_char_{}".format(color): (0, 0, 1, 1)},
            StickerSheet: {"sticker_char_{}".format(color): (0, 0, 1, 1)},
        }

    return CharacterSpriteMerger


CharacterBlackSpriteMerger = _create_class_for_character("black", CharacterBlackSheet)
CharacterBlackSpriteMerger = _create_class_for_character("black", CharacterBlackSheet)
CharacterLimeSpriteMerger = _create_class_for_character("lime", CharacterLimeSheet)
CharacterMagentaSpriteMerger = _create_class_for_character(
    "magenta", CharacterMagentaSheet
)
CharacterOliveSpriteMerger = _create_class_for_character("olive", CharacterOliveSheet)
CharacterOrangeSpriteMerger = _create_class_for_character(
    "orange", CharacterOrangeSheet
)
CharacterPinkSpriteMerger = _create_class_for_character("pink", CharacterPinkSheet)
CharacterRedSpriteMerger = _create_class_for_character("red", CharacterRedSheet)
CharacterVioletSpriteMerger = _create_class_for_character(
    "violet", CharacterVioletSheet
)
CharacterWhiteSpriteMerger = _create_class_for_character("white", CharacterWhiteSheet)
CharacterYellowSpriteMerger = _create_class_for_character(
    "yellow", CharacterYellowSheet
)
CharacterBlueSpriteMerger = _create_class_for_character("blue", CharacterBlueSheet)
CharacterCeruleanSpriteMerger = _create_class_for_character(
    "cerulean", CharacterCeruleanSheet
)
CharacterCinnabarSpriteMerger = _create_class_for_character(
    "cinnabar", CharacterCinnabarSheet
)
CharacterCyanSpriteMerger = _create_class_for_character("cyan", CharacterCyanSheet)
CharacterGoldSpriteMerger = _create_class_for_character("gold", CharacterGoldSheet)
CharacterGraySpriteMerger = _create_class_for_character("gray", CharacterGraySheet)
CharacterGreenSpriteMerger = _create_class_for_character("green", CharacterGreenSheet)
CharacterIrisSpriteMerger = _create_class_for_character("iris", CharacterIrisSheet)
CharacterKhakiSpriteMerger = _create_class_for_character("khaki", CharacterKhakiSheet)
CharacterLemonSpriteMerger = _create_class_for_character("lemon", CharacterLemonSheet)


class CharacterEggChildSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/char_eggchild_full.png")
    _grid_hint_size = 8
    _origin_map = {
        CharacterEggChildSheet: CharacterEggChildSheet._chunk_map,
        JournalPeopleSheet: {"journal_eggplant_child": (0, 0, 1, 1)},
    }


class CharacterHiredHandSpriteMerger(BaseSpriteMerger):
    _target_sprite_sheet_path = Path("Data/Textures/Entities/char_hired_full.png")
    _grid_hint_size = 8
    _origin_map = {
        CharacterHiredHandSheet: CharacterHiredHandSheet._chunk_map,
        JournalPeopleSheet: {"journal_hired_hand": (0, 0, 1, 1)},
    }
