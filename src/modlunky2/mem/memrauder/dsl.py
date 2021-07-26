import ctypes
import dataclasses

from modlunky2.mem.memrauder.model import (
    StructFieldMeta,
    DataclassStruct,
    ScalarCType,
    Array,
    Pointer,
    DeferredMemType,
    FieldPath,
)


def struct_field(
    offset: int,
    deferred_mem_type: DeferredMemType,
    metadata: dict = None,
    **kwargs,
):
    if metadata is None:
        metadata = {}
    field_meta = StructFieldMeta(offset, deferred_mem_type)
    field_meta.put_into(metadata)
    return dataclasses.field(metadata=metadata, **kwargs)


dc_struct = DataclassStruct  # pylint: disable=invalid-name


def scalar_c_type(c_type):
    def build(path: FieldPath, py_type: type):
        return ScalarCType(path, py_type, c_type)

    return build


sc_bool = scalar_c_type(ctypes.c_bool)
sc_uint8 = scalar_c_type(ctypes.c_uint8)
sc_uint16 = scalar_c_type(ctypes.c_uint16)
sc_uint32 = scalar_c_type(ctypes.c_uint32)
sc_uint64 = scalar_c_type(ctypes.c_uint64)
sc_int8 = scalar_c_type(ctypes.c_int8)
sc_int16 = scalar_c_type(ctypes.c_int16)
sc_int32 = scalar_c_type(ctypes.c_int32)
sc_int64 = scalar_c_type(ctypes.c_int64)
sc_float = scalar_c_type(ctypes.c_float)
sc_double = scalar_c_type(ctypes.c_double)
sc_longdouble = scalar_c_type(ctypes.c_longdouble)


def array(elem: DeferredMemType, count: int):
    def build(path: FieldPath, py_type: type):
        return Array(path, py_type, elem, count)

    return build


def pointer(pointed: DeferredMemType):
    def build(path: FieldPath, py_type: type):
        return Pointer(path, py_type, pointed)

    return build
