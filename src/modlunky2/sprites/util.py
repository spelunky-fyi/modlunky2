from modlunky2.sprites.base_classes.types import image_crop_tuple


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
        chunks["{}{}".format(base_name, i + 1)] = coords

    return chunks
