from __future__ import annotations
from abc import ABC, abstractmethod
import ctypes
from dataclasses import dataclass
import dataclasses
from enum import IntEnum, IntFlag
from ctypes import c_uint32, c_uint8
from typing import Any, ClassVar, Generic, List, Optional, Tuple, TypeVar, Union
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

    # TODO this will be replaced with validation during construction
    @abstractmethod
    def validate_field(self, path: FieldPath, py_type: type):
        raise NotImplementedError()

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


@dataclass(frozen=True)
class StructField:
    name: str
    offset: int
    # If > 1 this is an array. Must be positive
    count: int

    # If the field is an array, the python collection type to use
    collection_type: Optional[type]
    # For non-arrays, the python type of the field
    # For arrays, the python type of the elements
    py_type: type
    mem_type: MemType

    @classmethod
    def within_dataclass(cls, a_dataclass: type) -> Tuple[StructField, ...]:
        # We use get_type_hints() because it's updated for PEPs
        type_hints = typing.get_type_hints(a_dataclass)
        struct_fields = []

        # TODO check for overlapping fields
        for dc_field in dataclasses.fields(a_dataclass):
            if not dc_field.init:
                continue

            meta = StructFieldMeta.from_field(dc_field)

            collection_type = None
            py_type = type_hints[dc_field.name]
            mem_type = None
            if meta.count > 1:
                collection_type, py_type = cls._collection_type_info(
                    dc_field.name, py_type
                )
            mem_type = cls._mem_type_for_single(dc_field.name, py_type, meta)

            sc_field = StructField(
                name=dc_field.name,
                offset=meta.offset,
                count=meta.count,
                collection_type=collection_type,
                py_type=py_type,
                mem_type=mem_type,
            )
            struct_fields.append(sc_field)
        return tuple(struct_fields)

    def element_size(self):
        # TODO consider alignment
        return self.mem_type.element_size()

    def size(self):
        if self.count > 1:
            return self.element_size() * self.count

        return self.mem_type.field_size()

    def from_buffer(self, buf: bytes) -> Any:
        val_offset = 0 + self.offset
        # Read single values directly
        if self.count == 1:
            return self._value_from_buffer(buf[val_offset:])

        elem_size = self.element_size()
        values = []
        for i in range(0, self.count):
            elem_offset = val_offset + elem_size * i
            # TODO keep track of index for error reporting
            values.append(self._value_from_buffer(buf[elem_offset:]))
        return self.collection_type(values)

    def validate(self, path: FieldPath):
        my_name = self.name
        if self.count > 1:
            my_name += "[]"
        my_path = FieldPath(path.path_parts + tuple([my_name]))

        self.mem_type.validate_field(my_path, self.py_type)

    def _value_from_buffer(self, buf: bytes) -> Any:
        # This doesn't use self.offset because the caller is exepceted to compute the position

        return self.mem_type.from_bytes(buf, mem_reader=None)

    @classmethod
    def _collection_type_info(cls, field_name, type_info):
        try:
            collection_type = type_info.__origin__
        except ValueError as err:
            raise ValueError(
                f"field {field_name} has positive count and must be tuple or frozenset. Got type {type_info}"
            ) from err

        if collection_type not in {tuple, frozenset}:
            raise ValueError(
                f"field {field_name} has positive count and must be tuple or frozenset. Got type {type_info}"
            )

        # For tuples, we need to do some more checks
        py_type = type_info.__args__[0]
        if collection_type is tuple:
            cls._check_tuple_type_args(field_name, type_info.__args__)
        elif collection_type is frozenset:
            py_type = cls._check_frozenset_type_args(field_name, type_info.__args__)
        else:
            raise Exception(
                f"field {field_name} has unhandled collection type {collection_type}"
            )

        return (collection_type, py_type)

    @classmethod
    def _mem_type_for_single(cls, field_name, py_type, meta: StructFieldMeta):
        if meta.c_type is None and not dataclasses.is_dataclass(py_type):
            raise ValueError(
                f"field {field_name} must have a c_type or a dataclass as its type (got {py_type})"
            )
        if meta.c_type is None:
            return DataclassType(py_type)
        else:
            return ScalarCType(meta.c_type, py_type)

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


def dataclass_from_buffer(cls: type, buf) -> Any:
    mem_type = DataclassType(cls)
    mem_type.validate()
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
    c_type: type
    py_type: type  # Should match T. TODO can we write that explcitly?

    # Dict doesn't work correctly, presumably c_foo isn't hashable
    _allowed_c_types: ClassVar[Tuple[Tuple[type, type]]] = _build_allowed_c_types()

    def field_size(self) -> int:
        return ctypes.sizeof(self.c_type)

    def validate_field(self, path: FieldPath, py_type: type):
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

        if self.py_type not in py_type.__mro__:
            raise TypeError(
                f"field {path}: {py_type} must be a subtype of {self.py_type}"
            )

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        mem_value = self.c_type.from_buffer_copy(buf).value
        return self.py_type(mem_value)


@dataclass(frozen=True)
class DataclassType(MemType[T]):
    # TODO move all the dataclass logic into here
    dataclass: T
    struct_fields: List[StructField] = dataclasses.field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self, "struct_fields", StructField.within_dataclass(self.dataclass)
        )

    def field_size(self) -> int:
        return self.memory_range().stop

    def element_size(self) -> int:
        try:
            return self.dataclass._size_as_element_  # pylint: disable=protected-access
        except AttributeError:
            raise ValueError(  # pylint: disable=raise-missing-from
                f"{self.dataclass} must have _size_as_element_ attribute to be used in array field"
            )

    def validate(self):
        path = FieldPath()
        for field in self.struct_fields:
            field.validate(path)

    def validate_field(self, path: FieldPath, py_type: type):
        if self.dataclass not in py_type.__mro__:
            raise TypeError(
                f"field {path} {py_type} must be a subtype of {self.dataclass}"
            )

        for field in self.struct_fields:
            field.validate(path)

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        # TODO do validation once per "top level" call, collect all type errors up-front

        field_data = {}
        for field in self.struct_fields:
            field_data[field.name] = field.from_buffer(buf)

        # TODO catch excpetion to provide field info
        return self.dataclass(**field_data)

    def memory_range(self) -> range:
        lower = None
        upper = None
        for field in self.struct_fields:
            if lower is None or field.offset < lower:
                lower = field.offset
            field_upper = field.offset + field.size()
            if upper is None or field_upper > upper:
                upper = field_upper

        # TODO as part of dataclass validation, check there's at least 1 field
        if lower is None:
            raise Exception("lower was None when sizing {cls}")
        if upper is None:
            raise Exception("upper was None when sizing {cls}")

        return range(lower, upper)


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
    mem_type: MemType[T]
    read_size: int = dataclasses.field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "read_size", self.mem_type.field_size())

    def field_size(self) -> int:
        return ctypes.sizeof(ctypes.c_void_p)

    def validate_field(self, path: FieldPath, py_type: type):
        pointed_py_type = unwrap_optional_type(path, py_type)
        self.mem_type.validate_field(path, pointed_py_type)

    def from_bytes(self, buf: bytes, mem_reader: MemoryReader) -> T:
        addr = ctypes.c_void_p.from_buffer_copy(buf).value
        buf = mem_reader.read(addr, self.read_size)
        if buf is None:
            return None

        return self.mem_type.from_bytes(buf, mem_reader)


### DSL


@dataclass(frozen=True)
class StructFieldMeta:
    _METADATA_KEY: ClassVar[str] = "ml2_field_metadata"

    offset: int
    c_type: Optional[type]
    count: int

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
    c_type: type = None,
    count: int = 1,
    metadata: dict = None,
    **kwargs,
):
    if metadata is None:
        metadata = {}
    if count < 1:
        raise ValueError(f"count must be positive (got {count})")
    field_meta = StructFieldMeta(offset=offset, c_type=c_type, count=count)
    field_meta.put_into(metadata)
    return dataclasses.field(metadata=metadata, **kwargs)


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
    bombs: int = struct_field(0x0, c_uint8)
    ropes: int = struct_field(0x1, c_uint8)


@dataclass(frozen=True)
class State:
    level: int = struct_field(0x0, c_uint8)
    hud_flags: HudFlags = struct_field(0x1, c_uint32)
    win_state: WinState = struct_field(0x5, c_uint8)
    direct_player: Player = struct_field(0x6)
    nums_list: Tuple[int, ...] = struct_field(0x6, count=2, c_type=c_uint8)
    enum_list: Tuple[WinState, ...] = struct_field(0xA, count=2, c_type=c_uint8)
    player_list: Tuple[Player, ...] = struct_field(0x8, count=2)


# Demo output:
# State(
#     level=2,
#     hud_flags=<HudFlags.HAVE_CLOVER: 4194304>,
#     win_state=<WinState.COSMIC_OCEAN: 3>,
#     direct_player=Player(bombs=99, ropes=42),
#     nums_list=(99, 0),
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

print(dataclass_from_buffer(State, DEMO_BUFFER))
print(f"memory range for State is {DataclassType(State).memory_range()}")
