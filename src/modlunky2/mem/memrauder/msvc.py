import ctypes
import dataclasses
from dataclasses import InitVar, dataclass
from typing import ClassVar, Generic, Optional, Tuple, TypeVar

import fnvhash

from modlunky2.mem.memrauder.dsl import struct_field, sc_uint32, sc_void_p, sc_uint64
from modlunky2.mem.memrauder.model import (
    DataclassStruct,
    DeferredMemType,
    FieldPath,
    MemContext,
    MemType,
    ScalarCValueConstructionError,
    unwrap_optional_type,
    unwrap_collection_type,
)


@dataclass(frozen=True)
class _VectorMeta:
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
    vector_meta_mem_type: MemType[_VectorMeta] = dataclasses.field(init=False)

    def __post_init__(self, py_type, deferred_elem_mem_type):
        opt_inner_type = unwrap_optional_type(self.path, py_type)
        collection_type, elem_py_type = unwrap_collection_type(
            self.path, opt_inner_type
        )
        elem_mem_type = deferred_elem_mem_type(self.path, elem_py_type)
        vector_meta_mem_type = DataclassStruct(
            self.path.append("__vector_meta"), _VectorMeta
        )

        object.__setattr__(self, "collection_type", collection_type)
        object.__setattr__(self, "elem_mem_type", elem_mem_type)
        object.__setattr__(self, "vector_meta_mem_type", vector_meta_mem_type)

    def field_size(self) -> int:
        return self.vector_meta_mem_type.field_size()

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> T:
        elem_size = self.elem_mem_type.element_size()
        vector_meta = self.vector_meta_mem_type.from_bytes(buf, mem_ctx)

        # Don't try to dereference NULL
        if vector_meta.array_addr == 0:
            return None

        elem_buf = mem_ctx.mem_reader.read(
            vector_meta.array_addr, elem_size * vector_meta.size
        )
        if elem_buf is None:
            return None

        values = []
        for i in range(0, vector_meta.size):
            elem_offset = elem_size * i
            elem_end = elem_size * (i + 1)
            try:
                elem = self.elem_mem_type.from_bytes(
                    elem_buf[elem_offset:elem_end], mem_ctx
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


K = TypeVar("K")  # pylint: disable=invalid-name
V = TypeVar("V")  # pylint: disable=invalid-name


@dataclass(frozen=True)
class _UnorderedMapMeta:
    _size_as_element_: ClassVar[int] = 64
    end: int = struct_field(0x8, sc_uint64)
    size: int = struct_field(0x10, sc_uint64)
    buckets_ptr: int = struct_field(0x18, sc_void_p)
    mask: int = struct_field(0x30, sc_uint64)
    bucket_size: int = struct_field(0x38, sc_uint64)


@dataclass(frozen=True)
class _UnorderedMapBucket:
    _size_as_element_: ClassVar[int] = 16
    first: int = struct_field(0x0, sc_void_p)
    last: int = struct_field(0x8, sc_void_p)


@dataclass(frozen=True)
class _UnorderedMapNode:
    # As a workaround, we fix the size and types of the fields key and value
    # TODO Implement proper MemType for this

    _size_as_element_: ClassVar[int] = 32
    next: int = struct_field(0x0, sc_void_p)
    prev: int = struct_field(0x8, sc_void_p)
    key: int = struct_field(0x10, sc_uint32)
    value: int = struct_field(0x18, sc_uint64)


# Contains key-value pairs. Only the "core" data is fetched eagerly. Lookups are done on-demand.
@dataclass(frozen=True)
class UnorderedMap(Generic[K, V]):
    meta: _UnorderedMapMeta
    key_mem_type: MemType
    val_mem_type: MemType
    mem_ctx: MemContext

    def get(self, key: K) -> Optional[V]:
        bucket = self._get_bucket(key)
        if bucket is None:
            return None

        # Empty bucket
        if bucket.first == self.meta.end:
            return None

        next_ = bucket.first
        while True:
            node: _UnorderedMapNode = self.mem_ctx.type_at_addr(
                _UnorderedMapNode, next_
            )
            if node is None:
                return None

            # Found key!
            if node.key == key:
                val_bytes = bytes(ctypes.c_uint64(node.value))
                return self.val_mem_type.from_bytes(val_bytes, self.mem_ctx)

            # We've searched the final bucket. give up...
            if next_ == bucket.last:
                return None

            next_ = node.next

    def _get_bucket(self, key) -> Optional[_UnorderedMapBucket]:
        idx = self._get_bucket_idx(key)
        bucket_size = self.mem_ctx.get_mem_type(_UnorderedMapBucket).element_size()
        bucket_ptr = self.meta.buckets_ptr + (idx * bucket_size)
        return self.mem_ctx.type_at_addr(_UnorderedMapBucket, bucket_ptr)

    def _hash_key(self, key) -> int:
        bytes_ = self.key_mem_type.to_bytes(key)
        return fnvhash.fnv1a_64(bytes_)

    def _get_bucket_idx(self, key) -> int:
        return self._hash_key(key) & self.meta.mask


@dataclass(frozen=True)
class UnorderedMapType(MemType[UnorderedMap[K, V]]):
    path: FieldPath
    py_type: InitVar[type]
    key_deferred_mem_type: InitVar[DeferredMemType]
    val_deferred_mem_type: InitVar[DeferredMemType]

    key_mem_type: MemType = dataclasses.field(init=False)
    val_mem_type: MemType = dataclasses.field(init=False)
    um_meta_mem_type: MemType[_UnorderedMapMeta] = dataclasses.field(init=False)

    def _unwrap_unordered_map(self, path, py_type) -> Tuple[type, type]:
        try:
            if py_type.__origin__ is not UnorderedMap:
                raise ValueError(f"field {path} must be UnorderedMap, got {py_type}")
        except AttributeError as err:
            raise ValueError(
                f"field {path} must be UnorderedMap, got {py_type}"
            ) from err
        return (py_type.__args__[0], py_type.__args__[1])

    def __post_init__(self, py_type, key_deferred_mem_type, val_deferred_mem_type):
        key_py_type, val_py_type = self._unwrap_unordered_map(self.path, py_type)

        key_mem_type = key_deferred_mem_type(self.path, key_py_type)
        val_mem_type = val_deferred_mem_type(self.path, val_py_type)
        um_meta_mem_type = DataclassStruct(self.path, _UnorderedMapMeta)

        key_size = key_mem_type.field_size()
        if key_mem_type.field_size() != 4:
            raise ValueError(
                f"key for field {self.path} must be 4 bytes, got {key_size}"
            )

        val_size = key_mem_type.field_size()
        if val_mem_type.field_size() != 8:
            raise ValueError(
                f"value for field {self.path} must be 8 bytes, got {val_size}"
            )

        try:
            key_mem_type.to_bytes
        except AttributeError as err:
            raise ValueError(
                f"key for field {self.path} must implement to_bytes(val)"
            ) from err

        object.__setattr__(self, "key_mem_type", key_mem_type)
        object.__setattr__(self, "val_mem_type", val_mem_type)
        object.__setattr__(self, "um_meta_mem_type", um_meta_mem_type)

    def field_size(self) -> int:
        return self.um_meta_mem_type.field_size()

    def element_size(self) -> int:
        return self.um_meta_mem_type.element_size()

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> T:
        meta = self.um_meta_mem_type.from_bytes(buf, mem_ctx)
        return UnorderedMap(meta, self.key_mem_type, self.val_mem_type, mem_ctx)


def unordered_map(
    key_type: DeferredMemType, val_type: DeferredMemType
) -> DeferredMemType:
    def build(path: FieldPath, py_type: type):
        return UnorderedMapType(path, py_type, key_type, val_type)

    return build
