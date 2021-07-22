import array
import ctypes
from dataclasses import dataclass
import dataclasses
from enum import Enum, IntEnum, IntFlag
from ctypes import c_uint32, c_uint8
from typing import Any, ClassVar, Tuple, Union


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


class MetadataKey(Enum):
    OFFSET = "ml2_offset"
    C_TYPE = "ml2_c_type"
    COUNT = "ml2_count"


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
    metadata[MetadataKey.OFFSET] = offset
    metadata[MetadataKey.C_TYPE] = c_type
    metadata[MetadataKey.COUNT] = count
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


def validate_collection_field_type(field: dataclasses.Field):
    try:
        collection_type = field.type.__origin__
    except ValueError as err:
        raise ValueError(
            f"field {field.name} has positive count and must be tuple or frozenset. Got type {field.type}"
        ) from err

    if collection_type is not tuple:
        raise ValueError(
            f"field {field.name} has positive count and must be tuple or frozenset. Got type {field.type}"
        )

    # For tuples, we need to do some more checks
    type_args = field.type.__args__
    if len(type_args) != 2:
        raise ValueError(
            f"tuple field {field.name} must have 2 type parameters. Got {len(type_args)}"
        )
    if type_args[1] is not Ellipsis:
        raise ValueError(
            f"tuple field {field.name} second type parameter must be '...'. Got {type_args[1]}"
        )
    c_type = field.metadata[MetadataKey.C_TYPE]
    if c_type is None and not dataclasses.is_dataclass(type_args[0]):
        raise ValueError(
            f"field {field.name} must have a c_type, or a dataclass as the first type parameter (got {type_args[0]})"
        )


def element_size_for_field(field: dataclasses.Field):
    validate_collection_field_type(field)
    field_name = field.name
    c_type = field.metadata[MetadataKey.C_TYPE]

    # TODO consider alignment

    if c_type is not None:
        return ctypes.sizeof(c_type)

    # For both tuple and frozenset, the first type parameter is what we want
    cls = field.type.__args__[0]
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{field_name} doesn't have a c_type and isn't a dataclass")
    try:
        return cls._size_as_element_  # pylint: disable=protected-access
    except AttributeError:
        raise ValueError(  # pylint: disable=raise-missing-from
            f"{field_name} must have _size_as_element_ attribute to be used as in an array"
        )


def collection_type_for_field(field: dataclasses.Field):
    validate_collection_field_type(field)
    return field.type.__origin__


def dataclass_from_buffer(cls: type, buf, offset: int = 0) -> Any:
    # TODO do validation once per "top level" call, collect all type errors up-front

    field_data = {}
    for field in dataclasses.fields(cls):
        # TODO check for overlapping fields
        if not field.init:
            continue
        field_data[field.name] = field_from_buffer(field, buf, offset)

    # TODO catch excpetion to provide field info
    return cls(**field_data)


def field_from_buffer(field: dataclasses.Field, buf, base_offset: int = 0) -> Any:
    field_offset = base_offset + field.metadata[MetadataKey.OFFSET]
    count = field.metadata[MetadataKey.COUNT]
    # Read single values directly
    if count == 1:
        return field_value_fom_buffer(field, buf, field_offset)

    if count <= 0:
        raise ValueError(f"field {field.name} has non-positive count {count}")

    collection_type = collection_type_for_field(field)
    elem_size = element_size_for_field(field)
    values = []
    for i in range(0, count):
        elem_offset = field_offset + elem_size * i
        # TODO keep track of index for error reporting
        values.append(field_value_fom_buffer(field, buf, elem_offset))
    return collection_type(values)


def field_value_fom_buffer(field: dataclasses.Field, buf, elem_offset) -> Any:
    c_type = field.metadata.get(MetadataKey.C_TYPE)
    count = field.metadata.get(MetadataKey.COUNT)

    # TODO: Consider whether support array size 1
    py_type = field.type
    if count > 1:
        validate_collection_field_type(field)
        py_type = py_type.__args__[0]

    if c_type is not None:
        # TODO Check c_type is something we expect. We don't handle strings, and pointers are handled elsewhre
        # TODO Check if py_type is something we expect: bool, int, float, subclass of Enum
        val = c_type.from_buffer(buf, elem_offset).value
        try:
            return py_type(val)
        except Exception as err:
            raise Exception(
                f"failed to construct value for field {field.name}"
            ) from err

    # TODO keep track of the 'path', for use in sub-field error reporting
    if dataclasses.is_dataclass(py_type):
        return dataclass_from_buffer(py_type, buf, elem_offset)
    else:
        raise Exception(
            "Field {field.name} isn't a dataclass and doesn't have a c_type"
        )


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
    for field in dataclasses.fields(cls):
        offset = field.metadata[MetadataKey.OFFSET]
        count = field.metadata[MetadataKey.COUNT]
        c_type = field.metadata[MetadataKey.C_TYPE]
        if lower is None or offset < lower:
            lower = offset

        size = None
        if count == 1:
            if c_type is None:
                size = dataclass_memory_range(field.type).stop
            else:
                size = ctypes.sizeof(c_type)
        elif count > 1:
            size = element_size_for_field(field) * count
        else:
            raise ValueError(f"field {field.name} has non-positive count ({count})")

        field_upper = offset + size
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
