from math import ceil, sqrt
from logging import getLogger

from modlunky2.sprites.base_classes.types import chunk_map_type, image_crop_tuple

logger = getLogger("modlunky2")


def chunks_from_animation(
    base_name: str, start_chunk: image_crop_tuple, num_chunks: int, off: int = 0
):
    chunk_width = start_chunk[2] - start_chunk[0]

    chunks = {}
    for i in range(0, num_chunks):
        coords = (
            start_chunk[0] + i * chunk_width,
            start_chunk[1],
            start_chunk[2] + i * chunk_width,
            start_chunk[3],
        )
        chunks[f"{base_name}_{off + i + 1}"] = coords

    return chunks


def chunks_from_json(
    entities_json: dict, textures_json: dict, entity_name: str, chunk_size: int
) -> chunk_map_type:
    if entity_name in entities_json:
        entity_data = entities_json[entity_name]
        texture_id = str(entity_data["texture"])
        if texture_id in textures_json:
            texture_data = textures_json[texture_id]
            num_chunks_width = texture_data["num_tiles"]["width"]
            (offset_width, offset_height) = (
                texture_data["offset"]["width"] / chunk_size,
                texture_data["offset"]["height"] / chunk_size,
            )

            chunk_height_scaling = texture_data["tile_height"] / chunk_size
            chunk_width_scaling = texture_data["tile_width"] / chunk_size

            chunks = {}
            animations = sorted(
                entity_data["animations"].items(), key=lambda x: int(x[0])
            )
            if not animations:
                tile_x = entity_data["tile_x"]
                tile_y = entity_data["tile_y"]
                animations.append(
                    (
                        "0",
                        {
                            "count": 1,
                            "texture": tile_y * num_chunks_width + tile_x,
                        },
                    )
                )
            for animation_id, animation_data in animations:
                first_chunk = animation_data["texture"]
                for i in range(0, animation_data["count"]):
                    chunk_x = (first_chunk + i) % num_chunks_width
                    chunk_y = (first_chunk + i) // num_chunks_width
                    chunks[f"{entity_name}_{animation_id}_{i}"] = (
                        offset_width + chunk_x * chunk_width_scaling,
                        offset_height + chunk_y * chunk_height_scaling,
                        offset_width + (chunk_x + 1) * chunk_width_scaling,
                        offset_height + (chunk_y + 1) * chunk_height_scaling,
                    )
            return chunks
        logger.error(
            "Failed generating chunks for entity '%s': Could not find texture %s in textures.json",
            entity_name,
            texture_id,
        )
        return {}

    logger.error(
        "Failed generating chunks for entity '%s': Could not find entity in entities.json"
    )
    return {}


def chunk_mapping_from_json(
    entities_json: dict, textures_json: dict, entity_name: str, chunk_size: int
):
    chunks = chunks_from_json(entities_json, textures_json, entity_name, chunk_size)

    def get_unique_chunks(chunks: chunk_map_type):
        unique_chunks = {}
        for chunk_name, chunk_coords in chunks.items():
            if chunk_coords not in unique_chunks.values():
                unique_chunks[chunk_name] = chunk_coords
        return unique_chunks

    unique_chunks = get_unique_chunks(chunks)
    num_chunks_width = ceil(sqrt(len(unique_chunks)))

    def get_chunk_size(chunks: chunk_map_type):
        (chunk_width, chunk_height) = (0, 0)
        for _, chunk_coords in chunks.items():
            this_chunk_width = chunk_coords[2] - chunk_coords[0]
            this_chunk_height = chunk_coords[3] - chunk_coords[1]
            chunk_width = max(chunk_width, this_chunk_width)
            chunk_height = max(chunk_height, this_chunk_height)
        return (chunk_width, chunk_height)

    (chunk_width, chunk_height) = get_chunk_size(unique_chunks)

    chunk_mapping = {}
    for i, (chunk_name, chunk_coords) in enumerate(unique_chunks.items()):
        this_chunk_width = chunk_coords[2] - chunk_coords[0]
        this_chunk_height = chunk_coords[3] - chunk_coords[1]
        to_chunk_x = (i % num_chunks_width) * chunk_width
        to_chunk_y = (i // num_chunks_width) * chunk_height
        chunk_mapping[chunk_name] = {
            "from": chunk_coords,
            "to": (
                to_chunk_x,
                to_chunk_y,
                to_chunk_x + this_chunk_width,
                to_chunk_y + this_chunk_height,
            ),
        }
    return chunk_mapping


def target_chunks_from_json(
    entities_json: dict, textures_json: dict, entity_name: str, chunk_size: int
):
    chunk_mapping = chunk_mapping_from_json(
        entities_json, textures_json, entity_name, chunk_size
    )

    target_chunks = {}
    for chunk_name, chunk_mapping in chunk_mapping.items():
        target_chunks[chunk_name] = chunk_mapping["to"]
    return target_chunks
