from pathlib import Path

from ..base_classes.base_json_sprite_loader import BaseJsonSpriteLoader
from ..util import chunks_from_animation


class Mounts(BaseJsonSpriteLoader):
    _sprite_sheet_path = Path("Data/Textures/mounts.png")
    _chunk_size = 128
    _chunk_map = {
        "turkey": (0, 0, 1, 1),
        "rockdog": (0, 4, 1, 5),
        "axolotl": (0, 8, 1, 9),
        "qilin": (0, 12, 1, 13),
    }
    _entity_names = ["ENT_TYPE_MOUNT_TURKEY", "ENT_TYPE_MOUNT_ROCKDOG", "ENT_TYPE_MOUNT_AXOLOTL", "ENT_TYPE_MOUNT_QILIN"]
