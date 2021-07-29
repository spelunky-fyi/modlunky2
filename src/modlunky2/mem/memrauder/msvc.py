import dataclasses
from dataclasses import InitVar, dataclass
from typing import TypeVar

from modlunky2.mem.memrauder.dsl import struct_field, sc_uint32, sc_void_p
from modlunky2.mem.memrauder.model import (
    DataclassStruct,
    DeferredMemType,
    FieldPath,
    MemType,
    MemoryReader,
    ScalarCValueConstructionError,
    unwrap_optional_type,
    unwrap_collection_type,
)


@dataclass(frozen=True)
class VectorMeta:
    array_addr: int = struct_field(0x8, sc_void_p)
    size: int = struct_field(0x10, sc_uint32)


T = TypeVar("T")  # pylint: disable=invalid-name


@dataclass(frozen=True)
class Vector(MemType[T]):
    path: FieldPath
    py_type: InitVar[type]
    deferred_mem_type: InitVar[DeferredMemType]

    elem_mem_type: MemType = dataclasses.field(init=False)
    collection_type: T = dataclasses.field(init=False)
    vector_meta_mem_type: MemType[VectorMeta] = dataclasses.field(init=False)

    def __post_init__(self, py_type, deferred_elem_mem_type):
        opt_inner_type = unwrap_optional_type(self.path, py_type)
        collection_type, elem_py_type = unwrap_collection_type(
            self.path, opt_inner_type
        )
        elem_mem_type = deferred_elem_mem_type(self.path, elem_py_type)
        vector_meta_mem_type = DataclassStruct(
            self.path.append("__vector_meta"), VectorMeta
        )

        object.__setattr__(self, "collection_type", collection_type)
        object.__setattr__(self, "elem_mem_type", elem_mem_type)
        object.__setattr__(self, "vector_meta_mem_type", vector_meta_mem_type)

    def field_size(self) -> int:
        return self.vector_meta_mem_type.field_size()

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        elem_size = self.elem_mem_type.element_size()
        vector_meta = self.vector_meta_mem_type.from_bytes(buf, mem_reader)

        # Don't try to dereference NULL
        if vector_meta.array_addr == 0:
            return None

        elem_buf = mem_reader.read(vector_meta.array_addr, elem_size * vector_meta.size)
        if elem_buf is None:
            return None

        values = []
        for i in range(0, vector_meta.size):
            elem_offset = elem_size * i
            elem_end = elem_size * (i + 1)
            try:
                elem = self.elem_mem_type.from_bytes(
                    elem_buf[elem_offset:elem_end], mem_reader
                )
                values.append(elem)
            except ScalarCValueConstructionError:
                # TODO include index when re-raising?
                raise
            except Exception as err:
                raise ValueError(
                    f"failed to deserialize index {i} of field {self.path}"
                ) from err
        return self.collection_type(values)


def vector(elem: DeferredMemType) -> DeferredMemType:
    def build(path: FieldPath, py_type: type):
        return Vector(path, py_type, elem)

    return build
