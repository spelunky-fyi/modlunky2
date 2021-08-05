import ctypes
from dataclasses import dataclass
from typing import Optional, Tuple
import pytest

from modlunky2.mem.memrauder.dsl import sc_uint8, sc_uint16, struct_field
from modlunky2.mem.memrauder.model import (
    BytesReader,
    DataclassStruct,
    FieldPath,
    MemContext,
    ScalarCType,
)
from modlunky2.mem.memrauder.msvc import (
    UnorderedMap,
    UnorderedMapType,
    _UnorderedMapNode,
    _UnorderedMapNodeType,
    Vector,
    vector,
)


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
    mem_ctx = MemContext(BytesReader(arr_buf))
    assert mem_type.from_bytes(vec_buf, mem_ctx) == expected


def test_vesctor_bad_buf():
    vec_buf = b""
    arr_buf = b"\xff\x03\x00\x09\x00"
    mem_type = Vector(FieldPath(), Optional[Tuple[int, ...]], sc_uint8)
    mem_ctx = MemContext(BytesReader(arr_buf))
    with pytest.raises(ValueError):
        mem_type.from_bytes(vec_buf, mem_ctx)


@dataclass(frozen=True)
class VecWrap:
    num_list: Optional[Tuple[int, ...]] = struct_field(0x1, vector(sc_uint16))


def test_vector_dsl():
    vec_wrap_buf = b"\xff\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00"
    arr_buf = b"\xff\x03\x00\x09\x00"
    mem_type = DataclassStruct(FieldPath(), VecWrap)
    mem_ctx = MemContext(BytesReader(arr_buf))
    assert mem_type.from_bytes(vec_wrap_buf, mem_ctx) == VecWrap((3, 9))


uint8_type = ScalarCType(FieldPath(), int, ctypes.c_uint8)
uint16_type = ScalarCType(FieldPath(), int, ctypes.c_uint16)


@pytest.mark.parametrize(
    "key_type,val_type,node_bytes,expected",
    [
        (
            uint8_type,
            uint8_type,
            (
                b"\x00\x01"
                + b"\x00" * 6
                + b"\x10"
                + b"\x00" * 7
                + b"\x07"
                + b"\xff" * 7
                + b"\x05"
            ),
            _UnorderedMapNode(
                next_addr=0x100, prev_addr=0x10, key=b"\x07", value=b"\x05"
            ),
        ),
        (
            uint16_type,
            uint8_type,
            (
                b"\x01\x01"
                + b"\x00" * 6
                + b"\x11"
                + b"\x00" * 7
                + b"\x07\x02"
                + b"\xff" * 6
                + b"\x05"
            ),
            _UnorderedMapNode(
                next_addr=0x101, prev_addr=0x11, key=b"\x07\x02", value=b"\x05"
            ),
        ),
    ],
)
def test_unordered_map_node_deserialize(key_type, val_type, node_bytes, expected):
    node_type = _UnorderedMapNodeType(key_type, val_type)
    node = node_type.from_bytes(node_bytes, MemContext())
    assert node == expected


UNORDERED_MAP_BYTES = (
    b"\xff" * 8
    + b"\xcd" * 8
    + b"\xea" * 8
    + b"\x01"  # First bucket at address 1
    + b"\x00" * 7
    + b"\xff" * 16  # Unused bytes between buckets_ptr and mask
    + b"\x01"  # Mask is 1 so bucket is 1 as long as fnv1a_64() is odd
    + b"\x00" * 7
    + b"\xba" * 8  # meta.end
)
UNORDERED_MAP_MEM = (
    b"\xff" * 17  # Our first bucket shouldn't be looked at
    + b"\x22"  # Node at address 34
    + b"\x00" * 7
    + b"\xbc" * 8  # End pointer for test bucket
    + b"\xff"  # Garbage before node
    + b"\xbc" * 8  # next_addr just needs to not equal meta.end
    + b"\xff" * 8  # prev_addr is unused
    + b"\x02"  # key
    + b"\x00" * 3
    + b"\x57" * 4  # padding between fields
    + b"\x03\x00"  # value
    + b"\xff" * 6  # padding after fields
)


def test_unordered_map_type():
    def uint32_deferred(field, py_type):
        assert field == FieldPath()
        assert py_type is int
        return ScalarCType(FieldPath(), int, ctypes.c_uint32)

    def uint16_deferred(field, py_type):
        assert field == FieldPath()
        assert py_type is int
        return ScalarCType(FieldPath(), int, ctypes.c_uint16)

    mem_type = UnorderedMapType(
        FieldPath(), UnorderedMap[int, int], uint32_deferred, uint16_deferred
    )
    mem_ctx = MemContext(BytesReader(UNORDERED_MAP_MEM))
    uo_map: UnorderedMap = mem_type.from_bytes(UNORDERED_MAP_BYTES, mem_ctx)
    # Sanity check key fields before we try to call get()
    assert uo_map.meta.buckets_ptr == 1
    assert uo_map.meta.mask == 1

    value = uo_map.get(2)
    assert value == 3
