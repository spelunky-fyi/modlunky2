from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Iterable, NewType, Type

from serde.de import from_dict, is_deserializable
from serde.se import to_dict

TaggedMessage = NewType("TaggedMessage", Dict[str, Any])


class TagException(Exception):
    pass


def to_tagged_dict(obj: Any) -> TaggedMessage:
    data = to_dict(obj, convert_sets=True)
    tag = type(obj).__name__
    return TaggedMessage({tag: data})


@dataclass(frozen=True)
class TagDeserializer:
    types: InitVar[Iterable[Type[Any]]]

    _type_map: Dict[str, Type[Any]] = field(default_factory=dict, init=False)

    def __post_init__(self, types: Iterable[Type[Any]]):
        type_map: Dict[str, Type[Any]] = {}
        for typ in types:
            if not is_deserializable(typ):
                raise TagException(f"{typ} isn't deserializable with pyserde")

            type_map[typ.__name__] = typ
        object.__setattr__(self, "_type_map", MappingProxyType(type_map))

    def from_tagged_dict(self, data: TaggedMessage) -> Any:
        if len(data) != 1:
            raise TagException(f"Data has {len(data)} keys, expected 1")
        tag = next(iter(data.keys()))

        if tag not in self._type_map:
            raise TagException(f"Data has tag {tag}, which isn't a known type")
        typ = self._type_map[tag]

        return from_dict(typ, data[tag])
