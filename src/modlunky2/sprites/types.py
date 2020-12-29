from typing import Dict, Tuple, Union

_number_type = Union[float, int]
image_crop_tuple = Tuple[_number_type, _number_type, _number_type, _number_type]
chunk_map_type = Dict[str, image_crop_tuple]
