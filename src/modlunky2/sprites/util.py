from math import floor, ceil, sqrt
from logging import getLogger

from modlunky2.sprites.base_classes.types import image_crop_tuple

logger = getLogger("modlunky2")


def chunks_from_animation(
    base_name: str, start_chunk: image_crop_tuple, num_chunks: int
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
        chunks["{}_{}".format(base_name, i + 1)] = coords

    return chunks


def chunks_from_json(entities_json: dict, textures_json: dict, entity_name: str):
    if entity_name in entities_json:
        entity_data = entities_json[entity_name]
        texture_id = str(entity_data["texture"])
        if texture_id in textures_json:
            texture_data = textures_json[texture_id]
            num_chunks_width = texture_data["num_tiles"]["width"]

            chunks = {}
            animations = sorted(entity_data["animations"].items(), key=lambda x: int(x[0]))
            for animation_id, animation_data in animations:
                first_chunk = animation_data["texture"]
                for i in range(0, animation_data["count"]):
                    chunk_x = (first_chunk + i) % num_chunks_width
                    chunk_y = (first_chunk + i) // num_chunks_width
                    chunks["{}_{}_{}".format(entity_name, animation_id, i)] = (
                        chunk_x,
                        chunk_y,
                        chunk_x + 1,
                        chunk_y + 1,
                    )
            return chunks
        logger.error("Could not find texture %s in textures.json", texture_id)
        return {}

    logger.error("Could not find entity %s in entities.json", entity_name)
    return {}


def chunk_mapping_from_json(entities_json: dict, textures_json: dict, entity_name: str):
    chunks = chunks_from_json(entities_json, textures_json, entity_name)

    def get_unique_chunks(chunks: dict):
        unique_chunks = {}
        for chunk_name, chunk_coords in chunks.items():
            if chunk_coords not in unique_chunks.values():
                unique_chunks[chunk_name] = chunk_coords
        return unique_chunks

    unique_chunks = get_unique_chunks(chunks)
    num_chunks = len(unique_chunks)

    def compute_best_chunk_width(num_chunks: int):
        low_width = floor(sqrt(num_chunks))
        high_width = ceil(sqrt(num_chunks))
        low_delta = low_width * low_width + low_width - num_chunks
        high_delta = high_width * high_width - num_chunks
        if 0 <= low_delta < high_delta:
            return low_width
        return high_width
    num_chunks_width = compute_best_chunk_width(num_chunks)

    i = 0
    chunk_mapping = {}
    for chunk_name, chunk_coords in unique_chunks.items():
        to_chunk_x = i % num_chunks_width
        to_chunk_y = i // num_chunks_width
        chunk_mapping[chunk_name] = {
            "from": chunk_coords,
            "to": (
                to_chunk_x,
                to_chunk_y,
                to_chunk_x + 1,
                to_chunk_y + 1,
            ),
        }
        i += 1

    return chunk_mapping


def target_chunks_from_json(entities_json: dict, textures_json: dict, entity_name: str):
    chunk_mapping = chunk_mapping_from_json(entities_json, textures_json, entity_name)

    target_chunks = {}
    for chunk_name, chunk_mapping in chunk_mapping.items():
        target_chunks[chunk_name] = chunk_mapping["to"]
    return target_chunks
