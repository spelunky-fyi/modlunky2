from __future__ import annotations
import array
import ctypes
from dataclasses import dataclass
import dataclasses
from enum import IntEnum, IntFlag
from ctypes import c_uint32, c_uint8
from typing import Any, ClassVar, Optional, Tuple, Union
import typing


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


# TODO: fallback value for enums?
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
DEMO_BUFFER = array.array(
    "B",
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
    ],
)

# Unused for now, maybe handy for pointers
def unwrap_optional(opt_type: type) -> type:
    if opt_type.__origin__ is not Union:
        raise ValueError("Not a union type. Can't be Optional")
    union_args = opt_type.__args__
    num_args = len(union_args)
    if num_args != 2:
        raise ValueError(f"Not an Optional type. Expected 2 union args, got {num_args}")
    if union_args[1] is not type(None):
        raise ValueError(
            f"Not an Optional type. Expected second Union arg to be None, got {union_args[1]}"
        )
    return union_args[0]


### Loading structs from buffers


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
    c_type: Optional[type]

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

            type_info = type_hints[dc_field.name]
            collection_type = None
            py_type = None
            if meta.count == 1:
                py_type = cls._py_type_for_single(dc_field.name, type_info, meta)
            else:
                collection_type, py_type = cls._collection_type_info(
                    dc_field.name, type_info, meta
                )

            sc_field = StructField(
                name=dc_field.name,
                offset=meta.offset,
                count=meta.count,
                c_type=meta.c_type,
                collection_type=collection_type,
                py_type=py_type,
            )
            struct_fields.append(sc_field)
        return tuple(struct_fields)

    def element_size(self):
        # TODO consider alignment

        if self.c_type is not None:
            return ctypes.sizeof(self.c_type)

        try:
            return self.py_type._size_as_element_  # pylint: disable=protected-access
        except AttributeError:
            raise ValueError(  # pylint: disable=raise-missing-from
                f"{self.py_type} must have _size_as_element_ attribute to be used as in an array in field {self.name}"
            )

    def size(self):
        if self.count > 1:
            return self.element_size() * self.count

        if self.c_type is None:
            return dataclass_memory_range(self.py_type).stop
        else:
            return ctypes.sizeof(self.c_type)

    def from_buffer(self, buf, base_offset: int) -> Any:
        val_offset = base_offset + self.offset
        # Read single values directly
        if self.count == 1:
            return self._value_from_buffer(buf, val_offset)

        elem_size = self.element_size()
        values = []
        for i in range(0, self.count):
            elem_offset = val_offset + elem_size * i
            # TODO keep track of index for error reporting
            values.append(self._value_from_buffer(buf, elem_offset))
        return self.collection_type(values)

    def _value_from_buffer(self, buf, val_offset) -> Any:
        # This doesn't use self.offset because the caller is exepceted to compute the position

        # TODO: Consider whether support array size 1
        if self.c_type is not None:
            val = self.c_type.from_buffer(buf, val_offset).value
            try:
                return self.py_type(val)
            except Exception as err:
                raise Exception(
                    f"failed to construct value for field {self.name}"
                ) from err

        # TODO keep track of the 'path', for use in sub-field error reporting
        return dataclass_from_buffer(self.py_type, buf, val_offset)

    @classmethod
    def _collection_type_info(cls, field_name, type_info, meta):
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
        py_type = None
        if collection_type is tuple:
            py_type = cls._py_type_for_tuple(field_name, type_info.__args__, meta)
        elif collection_type is frozenset:
            py_type = cls._py_type_for_frozenset(field_name, type_info.__args__, meta)
        else:
            raise Exception(
                f"field {field_name} has unhandled collection type {collection_type}"
            )

        return (collection_type, py_type)

    _allowed_c_types = [(ctypes.c_bool, bool)]
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
        _allowed_c_types.append((c_type, int))
    _int_enum_types = frozenset([IntEnum, IntFlag])
    for c_type in [
        ctypes.c_float,
        ctypes.c_double,
        ctypes.c_longdouble,
    ]:
        _allowed_c_types.append((c_type, float))

    @classmethod
    def _check_c_and_py_types_match(cls, field_name, c_type, py_type):
        expected_type = None
        for known_c_type, known_py_type in cls._allowed_c_types:
            if known_c_type is c_type:
                expected_type = known_py_type
                break
        if expected_type is None:
            raise ValueError(f"field {field_name} has an unsupported c_type {c_type}")

        if expected_type not in py_type.__mro__:
            raise ValueError(
                f"field {field_name} has type {py_type}, but we expect {expected_type} for c_type {c_type}"
            )

    @classmethod
    def _py_type_for_single(cls, field_name, type_info, meta: StructFieldMeta):
        # TODO Check c_type is something we expect. We don't handle strings, and pointers are handled elsewhre
        # TODO Check if py_type is something we expect: bool, int, float, subclass of Enum
        if meta.c_type is None and not dataclasses.is_dataclass(type_info):
            raise ValueError(
                f"field {field_name} must have a c_type or a dataclass as its type (got {type_info})"
            )
        if meta.c_type is None:
            try:
                # Validate by trying to construct StructField
                cls.within_dataclass(type_info)
            except Exception as err:
                raise ValueError(
                    "field {field_name} has an invalid dataclass {type_info}"
                ) from err
        else:
            cls._check_c_and_py_types_match(field_name, meta.c_type, type_info)
        return type_info

    @classmethod
    def _py_type_for_tuple(cls, field_name, type_args, meta):
        if len(type_args) != 2:
            raise ValueError(
                f"tuple field {field_name} must have 2 type parameters. Got {len(type_args)}"
            )
        if type_args[1] is not Ellipsis:
            raise ValueError(
                f"tuple field {field_name} second type parameter must be '...'. Got {type_args[1]}"
            )
        return cls._py_type_for_single(field_name, type_args[0], meta)

    @classmethod
    def _py_type_for_frozenset(cls, field_name, type_args, meta):
        if len(type_args) != 1:
            raise ValueError(
                f"frozenset field {field_name} must have 1 type parameter. Got {len(type_args)}"
            )
        return cls._py_type_for_single(field_name, type_args[0], meta)


def dataclass_from_buffer(cls: type, buf, offset: int = 0) -> Any:
    # TODO do validation once per "top level" call, collect all type errors up-front

    field_data = {}
    for field in StructField.within_dataclass(cls):
        field_data[field.name] = field.from_buffer(buf, offset)

    # TODO catch excpetion to provide field info
    return cls(**field_data)


### Memory loading

# TODO Support pointers. Identify needed memory ranges top-down, fetch and store for use as we build objects bottom-up
# If memory read fails, we either fail overall read or treat all pointers into that range as broken.
# We should dedupe ranges and coalesce overlapping ranges (if they exist?).
# For pointers, the dataclass field must be Optional to cope with null.
# Maybe use c_type=c_void_p for pointers.
# No intention to support strings. Null termination is obnoxious


def dataclass_memory_range(cls: type) -> range:
    lower = None
    upper = None
    for field in StructField.within_dataclass(cls):
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


### Demo ugliness :)

print(dataclass_from_buffer(State, DEMO_BUFFER))
print(f"memory range for State is {dataclass_memory_range(State)}")
