from pathlib import Path

from modlunky2.sprites.base_classes.base_json_sprite_merger import BaseSpriteMerger
from modlunky2.sprites.deco_sheet import CaveDecoSheet


class UdjatWallHeads(BaseSpriteMerger):
    _target_sprite_sheet_path = Path(
        "Data/Textures/Entities/Decorations/udjat_wall_heads.png"
    )
    _grid_hint_size = 8
    _origin_map = {
        CaveDecoSheet: {"udjat_wall_heads": (0, 0, 4, 4)},
    }
