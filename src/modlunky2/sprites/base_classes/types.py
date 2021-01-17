from typing import Dict, Tuple, Union

_number_type = Union[float, int]
image_crop_tuple = Tuple[_number_type, _number_type, _number_type, _number_type]
chunk_map_type = Dict[str, image_crop_tuple]

image_crop_tuple_whole_number = Tuple[int, int, int, int]
chunk_map_type_whole_number = Dict[str, image_crop_tuple_whole_number]
