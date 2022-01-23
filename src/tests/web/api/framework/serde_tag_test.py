from __future__ import annotations  # PEP 563
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Dict
import pytest

from serde import serde

from modlunky2.web.api.framework.serde_tag import (
    TagException,
    TagDeserializer,
    to_tagged_dict,
)


@serde
@dataclass
class A:
    kind: str
    a_num: int


@serde
@dataclass
class B:
    kind: str
    a_str: str


@serde
@dataclass
class Rogue:
    kind: str
    a_float: float


class NotSerde:
    pass


@pytest.mark.parametrize(
    "obj",
    [A("A", 3), B("B", "woah")],
)
def test_round_trip(obj: Any):
    de = TagDeserializer([A, B])
    assert de.from_tagged_dict(to_tagged_dict(obj)) == obj


@pytest.mark.parametrize(
    "data,obj",
    [
        ({"A": {"kind": "hi", "a_num": 23}}, A("hi", 23)),
        ({"B": {"kind": "bye", "a_str": "what"}}, B("bye", "what")),
    ],
)
def test_ok_dict(data: Dict[str, Any], obj: Any):
    de = TagDeserializer([A, B])
    assert de.from_tagged_dict(data) == obj
    assert to_tagged_dict(obj) == data


@pytest.mark.parametrize(
    "data,expectation",
    [
        (
            {"C": {"some": "thing"}},
            pytest.raises(TagException, match=r"isn't a known type"),
        ),
        (
            {"A": {"kind": "thing", "a_num": 99}, "more": 3},
            pytest.raises(TagException, match=r"expected 1"),
        ),
    ],
)
def test_bad_dict(data: Dict[str, Any], expectation: AbstractContextManager[None]):
    de = TagDeserializer([A, B])
    with expectation:
        de.from_tagged_dict(data)


def test_bad_type():
    with pytest.raises(TagException, match=r"isn't deserializable"):
        TagDeserializer([NotSerde])
