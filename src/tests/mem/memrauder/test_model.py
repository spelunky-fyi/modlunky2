import ctypes
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import FrozenSet, Optional, Set, Tuple
import pytest

from modlunky2.mem.memrauder.model import (
    Array,
    BytesReader,
    DataclassStruct,
    FieldPath,
    Pointer,
    ScalarCType,
    ScalarCValueConstructionError,
    StructFieldMeta,
)

EMPTY_BYTES_READER = BytesReader(bytes())


def deferred_uint8(path, elm_type):
    return ScalarCType(path, elm_type, ctypes.c_uint8)


class FourEnum(IntEnum):
    FOUR = 4


class SecondBitFlag(IntFlag):
    SECOND = 1 << 2


@pytest.mark.parametrize(
    "py_type,expected",
    [(int, 4), (FourEnum, FourEnum.FOUR), (SecondBitFlag, SecondBitFlag.SECOND)],
)
def test_scalar_c_type_byte(py_type, expected):
    sc_type = ScalarCType(FieldPath(), py_type, ctypes.c_uint8)
    assert sc_type.from_bytes(b"\x04", EMPTY_BYTES_READER) == expected


@pytest.mark.parametrize(
    "addr_bytes,expected",
    [
        (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
        (b"\x0b\x00\x00\x00\x00\x00\x00\x00", 11),
        (b"\x00\x01\x00\x00\x00\x00\x00\x00", 256),
    ],
)
def test_scalar_c_type_pointer(addr_bytes, expected):
    sc_type = ScalarCType(FieldPath(), int, ctypes.c_void_p)
    assert sc_type.from_bytes(addr_bytes, EMPTY_BYTES_READER) == expected


def test_scalar_c_type_mismatch():
    def build():
        ScalarCType(FieldPath(), int, ctypes.c_float)

    with pytest.raises(ValueError):
        build()


def test_scalar_c_type_too_small():
    def read():
        sc_type = ScalarCType(FieldPath(), int, ctypes.c_uint8)
        sc_type.from_bytes(b"", EMPTY_BYTES_READER)

    with pytest.raises(ValueError):
        read()


def test_scalar_c_type_construction_error():
    def read():
        sc_type = ScalarCType(FieldPath(), FourEnum, ctypes.c_uint8)
        sc_type.from_bytes(b"\x00", EMPTY_BYTES_READER)

    with pytest.raises(ScalarCValueConstructionError):
        read()


def test_dataclass_struct_simple():
    meta_0 = {}
    StructFieldMeta(0x0, deferred_uint8).put_into(meta_0)
    meta_3 = {}
    StructFieldMeta(0x3, deferred_uint8).put_into(meta_3)

    @dataclass
    class MyStruct:
        field_a: int = field(metadata=meta_0)
        field_b: int = field(metadata=meta_3)

    dc_struct = DataclassStruct(FieldPath(), MyStruct)
    assert dc_struct.from_bytes(b"\x00\x01\x02\x03", EMPTY_BYTES_READER) == MyStruct(
        0, 3
    )


def test_dataclass_struct_nested():
    meta_0 = {}
    StructFieldMeta(0x0, deferred_uint8).put_into(meta_0)
    meta_2 = {}
    StructFieldMeta(0x2, deferred_uint8).put_into(meta_2)

    @dataclass
    class Inner:
        field_a: int = field(metadata=meta_0)
        field_b: int = field(metadata=meta_2)

    def deferred_inner(path, field_type):
        return DataclassStruct(path, field_type)

    meta_3_inner = {}
    StructFieldMeta(0x3, deferred_inner).put_into(meta_3_inner)

    @dataclass
    class Outer:
        field_0: int = field(metadata=meta_0)
        field_2: int = field(metadata=meta_2)
        inner: Inner = field(metadata=meta_3_inner)

    dc_outer = DataclassStruct(FieldPath(), Outer)
    assert dc_outer.from_bytes(
        b"\x00\x01\x02\x03\x04\x05", EMPTY_BYTES_READER
    ) == Outer(0, 2, Inner(3, 5))


def test_dataclass_struct_general_error():
    meta_0 = {}
    StructFieldMeta(0x0, deferred_uint8).put_into(meta_0)

    @dataclass
    class MyStruct:
        field_a: FourEnum = field(metadata=meta_0)

    dc_struct = DataclassStruct(FieldPath(), MyStruct)
    with pytest.raises(ValueError):
        # Too few bytes in buffer
        dc_struct.from_bytes(b"", EMPTY_BYTES_READER)


def test_dataclass_struct_scalar_c_error_passthrough():
    meta_0 = {}
    StructFieldMeta(0x0, deferred_uint8).put_into(meta_0)

    @dataclass
    class MyStruct:
        field_a: FourEnum = field(metadata=meta_0)

    dc_struct = DataclassStruct(FieldPath(), MyStruct)
    with pytest.raises(ScalarCValueConstructionError):
        dc_struct.from_bytes(b"\x00", EMPTY_BYTES_READER)


@pytest.mark.parametrize(
    "py_type,expected", [(Tuple[int, ...], (10, 2)), (FrozenSet[int], {10, 2})]
)
def test_array_uint8(py_type, expected):
    arr = Array(FieldPath, py_type, deferred_uint8, count=2)
    assert arr.from_bytes(b"\x0a\x02", EMPTY_BYTES_READER) == expected


@pytest.mark.parametrize("py_type", (Tuple[int, int], Set[int], int, FrozenSet[float]))
def test_array_type_mismatch(py_type):
    def build():
        Array(FieldPath, py_type, deferred_uint8, count=2)

    with pytest.raises(ValueError):
        build()


def test_array_too_small():
    def read():
        sc_type = Array(FieldPath, Tuple[int, ...], deferred_uint8, count=2)
        sc_type.from_bytes(b"", EMPTY_BYTES_READER)

    with pytest.raises(ValueError):
        read()


def test_array_scalar_c_error_passthrough():
    def read():
        sc_type = Array(FieldPath, Tuple[FourEnum, ...], deferred_uint8, count=2)
        sc_type.from_bytes(b"\x04\x00", EMPTY_BYTES_READER)

    with pytest.raises(ScalarCValueConstructionError):
        read()


@pytest.mark.parametrize(
    "addr_bytes,expected",
    [
        (b"\x01\x00\x00\x00\x00\x00\x00\x00", 3),
        (b"\x02\x00\x00\x00\x00\x00\x00\x00", 16),
    ],
)
def test_pointer_uint8(addr_bytes, expected):
    bytes_reader = BytesReader(b"\x0c\x03\x10")
    arr = Pointer(FieldPath, Optional[int], deferred_uint8)
    assert arr.from_bytes(addr_bytes, bytes_reader) == expected
