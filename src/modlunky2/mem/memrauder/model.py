from __future__ import annotations  # PEP 563
from abc import ABC, abstractmethod
import ctypes
from dataclasses import InitVar, dataclass
import dataclasses
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
import typing

# Abstract memory-reader interface, used if pointers are derefrenced.
class MemoryReader(ABC):
    @abstractmethod
    def read(self, addr: int, size: int) -> Optional[bytes]:
        raise NotImplementedError()


# Memory backed by a bytes object. Intended for testing.
@dataclass(frozen=True)
class BytesReader(MemoryReader):
    slab: bytes

    def read(self, addr: int, size: int) -> Optional[bytes]:
        upper = addr + size
        if upper > len(self.slab):
            return None
        return self.slab[addr:upper]


_EMPTY_BYTES_READER = BytesReader(bytes())


T = TypeVar("T")  # pylint: disable=invalid-name

# MemType abstracts constructing a field value from memory.
#
# Instances are expected to be reusable:
# * For multiple fields
# * For multiple from_bytes() calls
#
# If from_bytes() uses mem_reader:
# * The constructor should check that the py_type is Optional
# * from_bytes() should return None if MemoryReader.read() returns None
class MemType(Generic[T], ABC):
    # The number of bytes needed for from_bytes() to succeed
    @abstractmethod
    def field_size(self) -> int:
        raise NotImplementedError()

    # The number of bytes this occupies in an array.
    #
    # This will be equal to field_size() unless we're only using part of the
    # in-memory representation (e.g. only first 2 struct fields)
    def element_size(self) -> int:
        return self.field_size()

    # Construct an instance based on they bytes in buf.
    #
    # If needed, mem_reader can be used to follow pointers.
    @abstractmethod
    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> T:
        raise NotImplementedError()


# A MemType that supports serializing a value.
class BiMemType(MemType[T]):
    @abstractmethod
    def to_bytes(self, py_val: T) -> bytes:
        raise NotImplementedError()


# MemContext automatically creates, and caches, DataclassStruct instances.
# It also holds a MemoryReader to simplify usage of both DataclassStruct
# and PolyPointer.
@dataclass
class MemContext:
    mem_reader: MemoryReader = _EMPTY_BYTES_READER
    _type_map: Dict[type, DataclassStruct] = dataclasses.field(
        default_factory=dict, compare=False, repr=False
    )

    def get_mem_type(self, cls: type) -> DataclassStruct:
        if cls in self._type_map:
            return self._type_map[cls]

        if not dataclasses.is_dataclass(cls):
            raise ValueError(f"type {cls} must be a dataclass")

        mem_type = DataclassStruct(FieldPath(), cls)
        self._type_map[cls] = mem_type
        return mem_type

    def type_from_bytes(self, cls: type, buf: bytes):
        return self.get_mem_type(cls).from_bytes(buf, self)

    def type_at_addr(self, cls: type, addr: int):
        mem_type = self.get_mem_type(cls)
        if self.mem_reader is None:
            return None

        buf = self.mem_reader.read(addr, mem_type.field_size())
        if buf is None:
            return None

        return mem_type.from_bytes(buf, self)


@dataclass(frozen=True)
class FieldPath:
    path_parts: Tuple[str] = ()

    def __str__(self):
        return ".".join(self.path_parts)

    def append(self, part):
        suffix = tuple([str(part)])
        return FieldPath(self.path_parts + suffix)


# Checks that a type is Optional and returns the inner type.
def unwrap_optional_type(path: FieldPath, py_type: type) -> type:
    try:
        if py_type.__origin__ is not Union:
            raise ValueError(f"field {path} must be Optional, got {py_type}")
    except AttributeError as err:
        raise ValueError(f"field {path} must be Optional, got {py_type}") from err

    num_args = len(py_type.__args__)
    if num_args != 2:
        raise ValueError(
            f"field {path} must be Optional. Expected 2 Union args, got {num_args}"
        )

    second_arg = py_type.__args__[1]
    if second_arg is not type(None):
        raise ValueError(
            f"field {path} must be Optional. Expected second Union arg to be None, got {second_arg}"
        )

    return py_type.__args__[0]


# Checks the type is an unbounded tuple and returns the element type.
def unwrap_tuple_type(path: FieldPath, py_type: type) -> type:
    try:
        if py_type.__origin__ is not tuple:
            raise ValueError(f"field {path} must be tuple. Got type {py_type}")

    except AttributeError:
        raise ValueError(  # pylint: disable=raise-missing-from
            f"field {path} must be tuple. Got type {py_type}"
        )

    args_len = len(py_type.__args__)
    if args_len != 2:
        raise ValueError(
            f"tuple field {path} must have 2 type parameters. Got {args_len}"
        )

    second_arg = py_type.__args__[1]
    if second_arg is not Ellipsis:
        raise ValueError(
            f"tuple field {path} second type parameter must be '...'. Got {second_arg}"
        )
    return py_type.__args__[0]


# Checks that a type is frozenset and returns the element type.
def unwrap_frozenset_type(path: FieldPath, py_type: type):
    try:
        if py_type.__origin__ is not frozenset:
            raise ValueError(f"field {path} must be frozenset. Got type {py_type}")

    except AttributeError:
        raise ValueError(  # pylint: disable=raise-missing-from
            f"field {path} must be frozenset. Got type {py_type}"
        )

    args_len = len(py_type.__args__)
    if args_len != 1:
        raise ValueError(
            f"frozenset field {path} must have 1 type parameter. Got {args_len}"
        )
    return py_type.__args__[0]


# Checks that a type is either tuple or frozen set. Returns the collection type and element type.
def unwrap_collection_type(path: FieldPath, py_type: type) -> Tuple[type, type]:
    try:
        collection_type = py_type.__origin__
    except AttributeError:
        raise ValueError(  # pylint: disable=raise-missing-from
            f"field {path} must be tuple or frozenset. Got type {py_type}"
        )

    if collection_type is tuple:
        return (tuple, unwrap_tuple_type(path, py_type))
    elif collection_type is frozenset:
        return (frozenset, unwrap_frozenset_type(path, py_type))
    else:
        raise ValueError(f"field {path} must be tuple or frozenset. Got type {py_type}")


DeferredMemType = Callable[[FieldPath, Type], MemType]
DeferredBiMemType = Callable[[FieldPath, Type], BiMemType]

# Metadata stored during dataclass definition
@dataclass(frozen=True)
class StructFieldMeta:
    _METADATA_KEY: ClassVar[str] = "ml2_field_metadata"

    offset: int
    deferred_mem_type: DeferredMemType

    def put_into(self, metadata: dict):
        if self._METADATA_KEY in metadata:
            raise ValueError(f"metadata dict already has {self._METADATA_KEY}")
        metadata[self._METADATA_KEY] = self

    @classmethod
    def from_field(cls, field: dataclasses.Field) -> StructFieldMeta:
        if cls._METADATA_KEY not in field.metadata:
            raise ValueError(f"field {field.name} has no stuct_field() metadata")
        return field.metadata[cls._METADATA_KEY]


@dataclass(frozen=True)
class _StructField:
    path: FieldPath
    offset: int
    mem_type: MemType
    field_size: int


@dataclass(frozen=True)
class DataclassStruct(MemType[T]):
    path: FieldPath
    dataclass: T

    struct_fields: Dict[str, _StructField] = dataclasses.field(init=False)

    def __post_init__(self):
        if not dataclasses.is_dataclass(self.dataclass):
            raise ValueError(
                f"field {self.path} type ({self.dataclass}) must be a dataclass"
            )

        # We use get_type_hints() because it's updated for PEP 563
        type_hints = typing.get_type_hints(self.dataclass)
        struct_fields = {}
        for field in dataclasses.fields(self.dataclass):
            meta = StructFieldMeta.from_field(field)
            inner_path = self.path.append(field.name)
            inner_mem_type = meta.deferred_mem_type(inner_path, type_hints[field.name])
            struct_fields[field.name] = _StructField(
                inner_path, meta.offset, inner_mem_type, inner_mem_type.field_size()
            )

        # TODO search for dataclasses in MRO and check that our offsets don't overlap

        object.__setattr__(self, "struct_fields", struct_fields)

    def field_size(self) -> int:
        upper = 0
        for field in self.struct_fields.values():
            field_upper = field.offset + field.mem_type.field_size()
            if field_upper > upper:
                upper = field_upper

        return upper

    def element_size(self) -> int:
        try:
            return self.dataclass._size_as_element_  # pylint: disable=protected-access
        except AttributeError:
            raise ValueError(  # pylint: disable=raise-missing-from
                f"{self.dataclass} must have _size_as_element_ attribute to be used in array field"
            )

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> T:
        field_data = {}
        for name, meta in self.struct_fields.items():
            upper = meta.offset + meta.field_size
            view = buf[meta.offset : upper]
            try:
                field_data[name] = meta.mem_type.from_bytes(view, mem_ctx)
            except ScalarCValueConstructionError:
                # If we failed to convert a leaf value, abandon building the object but re-raise the exception
                raise
            except Exception as err:
                raise ValueError(f"failed to get value for field {meta.path}") from err

        try:
            return self.dataclass(**field_data)
        except Exception as err:
            raise ValueError(
                f"failed to construct value for field {self.path}"
            ) from err


def _build_allowed_c_types():
    pair_list = [(ctypes.c_bool, bool)]
    for c_type in [
        ctypes.c_int8,
        ctypes.c_uint8,
        ctypes.c_int16,
        ctypes.c_uint16,
        ctypes.c_int32,
        ctypes.c_uint32,
        ctypes.c_int64,
        ctypes.c_uint64,
        ctypes.c_void_p,
    ]:
        pair_list.append((c_type, int))
    for c_type in [
        ctypes.c_float,
        ctypes.c_double,
        ctypes.c_longdouble,
    ]:
        pair_list.append((c_type, float))

    return tuple(pair_list)


@dataclass(frozen=True)
class ScalarCValueConstructionError(Exception):
    path: FieldPath
    value: Any

    def __str__(self):
        return f"failed to construct Python value from C value ({self.value}) for field {self.path}"


@dataclass(frozen=True)
class ScalarCType(BiMemType[T]):
    path: FieldPath
    py_type: T
    c_type: type

    # Dict doesn't work correctly, presumably c_foo isn't hashable
    _allowed_c_types: ClassVar[Tuple[Tuple[type, type]]] = _build_allowed_c_types()

    def __post_init__(self):
        expected_type = None
        for known_c_type, known_py_type in self._allowed_c_types:
            if known_c_type is self.c_type:
                expected_type = known_py_type
                break
        if expected_type is None:
            raise ValueError(f"field {self.path} has unsupported c_type {self.c_type}")

        if expected_type not in self.py_type.__mro__:
            raise ValueError(
                f"field {self.path} has {self.c_type} we expect the py_type ({self.py_type}) to be a subtype of {expected_type}"  # pylint: disable=line-too-long
            )

        if expected_type not in self.py_type.__mro__:
            raise TypeError(
                f"field {self.path}: {self.py_type} must be a subtype of {expected_type}"
            )

    def field_size(self) -> int:
        return ctypes.sizeof(self.c_type)

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> T:
        try:
            mem_value = self.c_type.from_buffer_copy(buf).value
        except Exception as err:
            raise ValueError(
                f"failed to deserialize C value for field {self.path}"
            ) from err

        # c_void_p special cases NULL as None, but that's not valid for int()
        if mem_value is None and self.c_type is ctypes.c_void_p:
            mem_value = 0

        try:
            return self.py_type(mem_value)
        except Exception as err:
            raise ScalarCValueConstructionError(self.path, mem_value) from err

    def to_bytes(self, py_val: T) -> bytes:
        try:
            c_val = self.c_type(py_val)
        except TypeError as err:
            raise ValueError(
                f"failed to serialize value {py_val!r} for field {self.path}"
            ) from err
        return bytes(c_val)


@dataclass(frozen=True)
class Array(MemType[T]):
    path: FieldPath
    py_type: InitVar[type]
    deferred_elem_mem_type: InitVar[DeferredMemType]
    count: int

    elem_mem_type: MemType = dataclasses.field(init=False)
    _total_field_size: int = dataclasses.field(init=False)
    collection_type: T = dataclasses.field(init=False)

    def __post_init__(self, py_type, deferred_elem_mem_type):
        collection_type, elem_py_type = unwrap_collection_type(self.path, py_type)
        elem_mem_type = deferred_elem_mem_type(self.path, elem_py_type)
        total_field_size = elem_mem_type.element_size() * self.count
        object.__setattr__(self, "elem_mem_type", elem_mem_type)
        object.__setattr__(self, "_total_field_size", total_field_size)
        object.__setattr__(self, "collection_type", collection_type)

    def field_size(self) -> int:
        return self._total_field_size

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> T:
        values = []
        elem_size = self.elem_mem_type.element_size()
        for i in range(0, self.count):
            elem_offset = elem_size * i
            elem_end = elem_size * (i + 1)
            try:
                elem = self.elem_mem_type.from_bytes(buf[elem_offset:elem_end], mem_ctx)
                values.append(elem)
            except ScalarCValueConstructionError:
                # TODO include index when re-raising?
                raise
            except Exception as err:
                raise ValueError(
                    f"failed to deserialize index {i} of field {self.path}"
                ) from err

        return self.collection_type(values)


@dataclass(frozen=True)
class Pointer(MemType[T]):
    path: InitVar[FieldPath]
    py_type: InitVar[type]
    deferred_mem_type: InitVar[DeferredMemType]

    mem_type: MemType[T] = dataclasses.field(init=False)
    read_size: int = dataclasses.field(init=False)

    def __post_init__(self, path, py_type, deferred_mem_type):
        pointed_py_type = unwrap_optional_type(path, py_type)
        mem_type = deferred_mem_type(path, pointed_py_type)

        object.__setattr__(self, "mem_type", mem_type)
        object.__setattr__(self, "read_size", mem_type.field_size())

    def field_size(self) -> int:
        return ctypes.sizeof(ctypes.c_void_p)

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> Optional[T]:
        addr = ctypes.c_void_p.from_buffer_copy(buf).value
        if addr is None:
            return None

        buf = mem_ctx.mem_reader.read(addr, self.read_size)

        if buf is None:
            return None

        return self.mem_type.from_bytes(buf, mem_ctx)


C = TypeVar("C")  # pylint: disable=invalid-name


# A PolyPointer encapsulates both a value, and the address it was obtained from.
# This facilitates casting between classes.
@dataclass(frozen=True)
class PolyPointer(Generic[T]):
    addr: Optional[int]
    value: Optional[T]
    mem_ctx: MemContext

    def __post_init__(self):
        if (self.addr is None) != (self.value is None):
            raise ValueError(
                "addr and value must either both be None, or both non-None"
            )

    def present(self):
        return self.addr is not None

    def as_type(self, cls: C) -> Optional[C]:
        if not dataclasses.is_dataclass(cls):
            raise ValueError("Target class ({cls}) must be a dataclass")

        if not self.present():
            return None

        # This is an up-cast
        if isinstance(self.value, cls):
            return self.value

        value_type = type(self.value)
        if not issubclass(cls, value_type):
            raise TypeError("Trying to cast {value_type} to unrelated class {cls}")

        return self.mem_ctx.type_at_addr(cls, self.addr)

    def as_poly_type(self, cls: C) -> PolyPointer[C]:
        new_value = self.as_type(cls)
        return PolyPointer(self.addr, new_value, self.mem_ctx)

    @staticmethod
    def make_empty(mem_ctx: Optional[MemContext] = None) -> PolyPointer:
        if mem_ctx is None:
            mem_ctx = MemContext()
        return PolyPointer(None, None, mem_ctx)


@dataclass(frozen=True)
class PolyPointerType(MemType[PolyPointer[T]]):
    path: InitVar[FieldPath]
    py_type: InitVar[type]
    deferred_mem_type: InitVar[DeferredMemType]

    mem_type: MemType[T] = dataclasses.field(init=False)
    read_size: int = dataclasses.field(init=False)

    def __post_init__(self, path, py_type, deferred_mem_type):
        pointed_py_type = self._unwrap_poly_pointer(path, py_type)
        mem_type = deferred_mem_type(path, pointed_py_type)

        object.__setattr__(self, "mem_type", mem_type)
        object.__setattr__(self, "read_size", mem_type.field_size())

    def _unwrap_poly_pointer(self, path, py_type) -> type:
        try:
            if py_type.__origin__ is not PolyPointer:
                raise ValueError(f"field {path} must be PolyPointer, got {py_type}")
        except AttributeError as err:
            raise ValueError(
                f"field {path} must be PolyPointer, got {py_type}"
            ) from err
        return py_type.__args__[0]

    def field_size(self) -> int:
        return ctypes.sizeof(ctypes.c_void_p)

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> PolyPointer[T]:
        addr = ctypes.c_void_p.from_buffer_copy(buf).value
        if addr is None:
            return PolyPointer.make_empty(mem_ctx)

        buf = mem_ctx.mem_reader.read(addr, self.read_size)
        if buf is None:
            return PolyPointer.make_empty(mem_ctx)

        value = self.mem_type.from_bytes(buf, mem_ctx)
        if value is None:
            return PolyPointer.make_empty(mem_ctx)

        return PolyPointer[T](addr, value, mem_ctx)
