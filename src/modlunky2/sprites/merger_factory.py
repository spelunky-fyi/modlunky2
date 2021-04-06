from typing import List, Optional, Type, Dict
from pathlib import Path

from modlunky2.sprites.base_classes.base_sprite_loader import BaseSpriteLoader
from modlunky2.sprites.base_classes.base_json_sprite_merger import BaseJsonSpriteMerger
from modlunky2.sprites.base_classes.types import chunk_map_type


def create_merger_factory_for_source_sheet(
    source_sheet: Type[BaseSpriteLoader], journal_sheet: Type[BaseSpriteLoader]
):
    def merger_factory(
        target_file_name: str,
        journal_entry: Optional[str],
        entity_names: List[str],
        journal_sheet_override: Optional[Type[BaseSpriteLoader]] = None,
        additional_origins: Optional[
            Dict[Type[BaseSpriteLoader], chunk_map_type]
        ] = None,
    ):
        class SpriteMerger(BaseJsonSpriteMerger):
            _target_sprite_sheet_path = Path(
                "Data/Textures/Entities/{}_full.png".format(target_file_name)
            )
            _grid_hint_size = 8
            _origin_map = {
                **(additional_origins or {}),
                **(
                    {
                        journal_sheet_override
                        or journal_sheet: {journal_entry: (0, 0, 1, 1)},
                    }
                    if journal_entry
                    else {}
                )
            }
            _entity_origins = {source_sheet: entity_names}

        return SpriteMerger

    return merger_factory
