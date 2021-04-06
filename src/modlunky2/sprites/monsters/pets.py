from pathlib import Path

from ..base_classes.base_json_sprite_loader import BaseJsonSpriteLoader

class Pets(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/monsters_pets.png")
    _chunk_size = 128
    _chunk_map = {
            "monty": (0, 0, 1, 1),
            "percy": (0, 4, 1, 5),
            "poochi": (0, 8, 1, 9),
        }
    _entity_names = ["ENT_TYPE_MONS_PET_DOG", "ENT_TYPE_MONS_PET_CAT", "ENT_TYPE_MONS_PET_HAMSTER"]
