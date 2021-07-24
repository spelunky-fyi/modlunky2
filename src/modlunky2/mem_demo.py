from __future__ import annotations
from abc import ABC, abstractmethod
import ctypes
from dataclasses import InitVar, dataclass
import dataclasses
from enum import IntEnum, IntFlag
import functools
from typing import (
    Any,
    Callable,
    ClassVar,
    Collection,
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


T = TypeVar("T")  # pylint: disable=invalid-name


# MemType abstracts constructing a field value from memory.
#
# Instances are expected to be reusable:
# * For multiple fields
# * For multiple from_bytes() calls
#
# If from_bytes() uses mem_reader:
# * validate_field() should check that the py_type is Optional
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
    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        raise NotImplementedError()


@dataclass
class FieldPath:
    path_parts: Tuple[str] = ()

    def __str__(self):
        return ".".join(self.path_parts)


def dataclass_from_bytes(cls: type, buf: bytes) -> Any:
    mem_type = DataclassStruct(FieldPath(), cls)
    return mem_type.from_bytes(buf, mem_reader=None)


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
class ScalarCType(MemType[T]):
    path: InitVar[FieldPath]
    py_type: T
    c_type: type

    # Dict doesn't work correctly, presumably c_foo isn't hashable
    _allowed_c_types: ClassVar[Tuple[Tuple[type, type]]] = _build_allowed_c_types()

    # TODO validate in constructor
    def __post_init__(self, path: FieldPath):
        expected_type = None
        for known_c_type, known_py_type in self._allowed_c_types:
            if known_c_type is self.c_type:
                expected_type = known_py_type
                break
        if expected_type is None:
            raise ValueError(f"field {path} has unsupported c_type {self.c_type}")

        if expected_type not in self.py_type.__mro__:
            raise ValueError(
                f"field {path} has {self.c_type} we expect the py_type ({self.py_type}) to be a subtype of {expected_type}"  # pylint: disable=line-too-long
            )

        if expected_type not in self.py_type.__mro__:
            raise TypeError(
                f"field {path}: {self.py_type} must be a subtype of {expected_type}"
            )

    def field_size(self) -> int:
        return ctypes.sizeof(self.c_type)

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        mem_value = self.c_type.from_buffer_copy(buf).value
        return self.py_type(mem_value)


@dataclass(frozen=True)
class StructField:
    path: FieldPath
    offset: int
    mem_type: MemType
    field_size: int


@dataclass(frozen=True)
class DataclassStruct(MemType[T]):
    path: FieldPath
    dataclass: T

    struct_fields: Dict[str, StructField] = dataclasses.field(init=False)

    # TODO work out relationship between StructField and dataclass
    def __post_init__(self):
        if not dataclasses.is_dataclass(self.dataclass):
            raise ValueError(
                f"field {self.path} type ({self.dataclass}) must be a dataclass"
            )

        # We use get_type_hints() because it's updated for PEPs
        type_hints = typing.get_type_hints(self.dataclass)
        struct_fields = {}
        for field in dataclasses.fields(self.dataclass):
            meta = StructFieldMeta.from_field(field)
            inner_path = FieldPath(self.path.path_parts + tuple([field.name]))
            inner_mem_type = meta.deferred_mem_type(inner_path, type_hints[field.name])
            struct_fields[field.name] = StructField(
                inner_path, meta.offset, inner_mem_type, inner_mem_type.field_size()
            )

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

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        field_data = {}
        for name, meta in self.struct_fields.items():
            upper = meta.offset + meta.field_size
            view = buf[meta.offset : upper]
            try:
                field_data[name] = meta.mem_type.from_bytes(view, mem_reader)
            except Exception as err:
                raise ValueError(f"failed to get value for field {meta.path}") from err

        try:
            return self.dataclass(**field_data)
        except Exception as err:
            raise ValueError(
                f"failed to construct value for field {self.path}"
            ) from err


@dataclass(frozen=True)
class Array(MemType[T]):
    path: InitVar[FieldPath]
    py_type: InitVar[type]
    deferred_elem_mem_type: InitVar[DeferredMemType]
    count: int

    elem_mem_type: MemType[T] = dataclasses.field(init=False)
    _total_field_size: MemType[T] = dataclasses.field(init=False)
    collection_type: Collection[T] = dataclasses.field(init=False)

    def __post_init__(self, path, py_type, deferred_elem_mem_type):
        try:
            collection_type = py_type.__origin__
        except ValueError as err:
            raise ValueError(
                f"field {path} has positive count and must be tuple or frozenset. Got type {py_type}"
            ) from err

        if collection_type not in {tuple, frozenset}:
            raise ValueError(
                f"field {path} has positive count and must be tuple or frozenset. Got type {py_type}"
            )

        # For tuples, we need to do some more checks
        elem_py_type = py_type.__args__[0]
        if collection_type is tuple:
            self._check_tuple_type_args(path, py_type.__args__)
        elif collection_type is frozenset:
            self._check_frozenset_type_args(path, py_type.__args__)
        else:
            raise Exception(
                f"field {path} has unhandled collection type {collection_type}"
            )

        elem_mem_type = deferred_elem_mem_type(path, elem_py_type)
        total_field_size = elem_mem_type.element_size() * self.count
        object.__setattr__(self, "elem_mem_type", elem_mem_type)
        object.__setattr__(self, "_total_field_size", total_field_size)
        object.__setattr__(self, "collection_type", collection_type)

    def field_size(self) -> int:
        return self._total_field_size

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        values = []
        elem_size = self.elem_mem_type.element_size()
        for i in range(0, self.count):
            elem_offset = elem_size * i
            elem_end = elem_offset + elem_size
            # TODO keep track of index for error reporting
            elem = self.elem_mem_type.from_bytes(buf[elem_offset:elem_end], mem_reader)
            values.append(elem)

        return self.collection_type(values)

    @classmethod
    def _check_tuple_type_args(cls, field_name, type_args):
        if len(type_args) != 2:
            raise ValueError(
                f"tuple field {field_name} must have 2 type parameters. Got {len(type_args)}"
            )
        if type_args[1] is not Ellipsis:
            raise ValueError(
                f"tuple field {field_name} second type parameter must be '...'. Got {type_args[1]}"
            )

    @classmethod
    def _check_frozenset_type_args(cls, field_name, type_args):
        if len(type_args) != 1:
            raise ValueError(
                f"frozenset field {field_name} must have 1 type parameter. Got {len(type_args)}"
            )


# Checks that a type is Optional and returns the inner type.
def unwrap_optional_type(path: FieldPath, py_type: type) -> type:
    try:
        if py_type.__origin__ is not Union:
            raise ValueError(f"field {path} must be Optional, got {py_type}")
    except AttributeError as err:
        raise ValueError(f"field {path} must be Optional") from err

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


@dataclass(frozen=True)
class Pointer(MemType[T]):
    path: InitVar[FieldPath]
    py_type: InitVar[type]
    deferred_mem_type: InitVar[DeferredMemType]

    mem_type: MemType[T] = dataclasses.field(init=False)
    read_size: int = dataclasses.field(init=False)

    def __post_init__(self, path, py_type, deferred_mem_type):
        pointed_py_type = unwrap_optional_type(path, py_type)
        mem_type = deferred_mem_type(py_type, pointed_py_type)

        object.__setattr__(self, "mem_type", mem_type)
        object.__setattr__(self, "read_size", mem_type.field_size())

    def field_size(self) -> int:
        return ctypes.sizeof(ctypes.c_void_p)

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        addr = ctypes.c_void_p.from_buffer_copy(buf).value
        buf = mem_reader.read(addr, self.read_size)

        if buf is None:
            return None

        return self.mem_type.from_bytes(buf, mem_reader)


### DSL

DeferredMemType = Callable[[FieldPath, Type], MemType]


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


# TODO: wire in pointers


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


auto_dc = DataclassStruct  # pylint: disable=invalid-name


def scalar_c_type(c_type):
    @functools.wraps(ScalarCType)
    def build(path: FieldPath, py_type: type):
        return ScalarCType(path, py_type, c_type)

    return build


uint8 = scalar_c_type(ctypes.c_uint8)


uint32 = scalar_c_type(ctypes.c_uint32)

# TODO other C int types


def array(elem: DeferredMemType, count: int):
    @functools.wraps(Array)
    def build(path: FieldPath, py_type: type):
        return Array(path, py_type, elem, count)

    return build


def pointer(pointed: DeferredMemType):
    @functools.wraps(Pointer)
    def build(path: FieldPath, py_type: type):
        return Pointer(path, py_type, pointed)

    return build


### Demo


class HudFlags(IntFlag):
    UPBEAT_DWELLING_MUSIC = 1 << 1 - 1
    RUNNING_TUTORIAL_SPEEDRUN = 1 << 3 - 1
    ALLOW_PAUSE = 1 << 20 - 1
    HAVE_CLOVER = 1 << 23 - 1


class WinState(IntEnum):
    UNKNOWN = -1
    NO_WIN = 0
    TIAMAT = 1
    HUNDUN = 2
    COSMIC_OCEAN = 3


@dataclass(frozen=True)
class Player:
    # Overall struct size, used for computing array element offsets
    _size_as_element_: ClassVar[int] = 4
    bombs: int = struct_field(0x0, uint8)
    ropes: int = struct_field(0x1, uint8)


@dataclass(frozen=True)
class State:
    level: int = struct_field(0x0, uint8)
    hud_flags: HudFlags = struct_field(0x1, uint32)
    win_state: WinState = struct_field(0x5, uint8)
    direct_player: Player = struct_field(0x6, auto_dc)
    nums_list: Tuple[int, ...] = struct_field(0x6, array(uint8, 2))
    enum_list: Tuple[WinState, ...] = struct_field(0xA, array(uint8, 2))
    player_list: Tuple[Player, ...] = struct_field(0x8, array(auto_dc, 2))


# Demo output:
# State(
#     level=2,
#     hud_flags=<HudFlags.HAVE_CLOVER: 4194304>,
#     win_state=<WinState.COSMIC_OCEAN: 3>,
#     direct_player=Player(bombs=99, ropes=42),
#     nums_list=(99, 42),
#     enum_list=(<WinState.NO_WIN: 0>, <WinState.NO_WIN: 0>),
#     player_list=(Player(bombs=1, ropes=2), Player(bombs=3, ropes=4)))
DEMO_BUFFER = bytes(
    [
        0x02,
        0x00,
        0x00,
        0x40,
        0x00,
        0x03,
        0x63,
        0x2A,
        0x01,
        0x02,
        0x00,
        0x00,
        0x03,
        0x04,
        0x00,
        0x00,
    ]
)

print(dataclass_from_bytes(State, DEMO_BUFFER))
