from dataclasses import dataclass
from typing import Optional, Tuple
import pytest

from modlunky2.mem.memrauder.dsl import sc_uint8, sc_uint16, struct_field
from modlunky2.mem.memrauder.model import (
    BytesReader,
    DataclassStruct,
    FieldPath,
    mem_type_from_bytes,
)
from modlunky2.mem.memrauder.msvc import Vector, vector


@pytest.mark.parametrize(
    "vec_buf,expected",
    [
        (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00",
            (11, 12, 13),
        ),
        (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00",
            tuple([12]),
        ),
        (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x0a\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00",
            None,
        ),
        (
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x0a\x00\x00\x00",
            None,
        ),
    ],
)
def test_vector_model(vec_buf, expected):
    mem_type = Vector(FieldPath(), Optional[Tuple[int, ...]], sc_uint8)
    arr_buf = b"\x0a\x0b\x0c\x0d"
    mem_reader = BytesReader(arr_buf)
    assert mem_type_from_bytes(mem_type, vec_buf, mem_reader) == expected


def test_vesctor_bad_buf():
    vec_buf = b""
    arr_buf = b"\xff\x03\x00\x09\x00"
    mem_type = Vector(FieldPath(), Optional[Tuple[int, ...]], sc_uint8)
    mem_reader = BytesReader(arr_buf)
    with pytest.raises(ValueError):
        mem_type.from_bytes(vec_buf, mem_reader)


@dataclass(frozen=True)
class VecWrap:
    num_list: Optional[Tuple[int, ...]] = struct_field(0x1, vector(sc_uint16))


def test_vector_dsl():
    vec_wrap_buf = b"\xff\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00"
    arr_buf = b"\xff\x03\x00\x09\x00"
    mem_type = DataclassStruct(FieldPath(), VecWrap)
    mem_reader = BytesReader(arr_buf)
    assert mem_type_from_bytes(mem_type, vec_wrap_buf, mem_reader) == VecWrap((3, 9))
