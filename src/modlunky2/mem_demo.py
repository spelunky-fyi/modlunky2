import array
import ctypes
from dataclasses import dataclass, field
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
    return field(metadata=metadata, **kwargs)


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


def validate_collection_field_type(a_field: dataclasses.Field):
    try:
        collection_type = a_field.type.__origin__
    except ValueError as err:
        raise ValueError(
            f"field {a_field.name} has positive count and must be tuple or frozenset. Got type {a_field.type}"
        ) from err

    if collection_type is not tuple:
        raise ValueError(
            f"field {a_field.name} has positive count and must be tuple or frozenset. Got type {a_field.type}"
        )

    # For tuples, we need to do some more checks
    type_args = a_field.type.__args__
    if len(type_args) != 2:
        raise ValueError(
            f"tuple field {a_field.name} must have 2 type parameters. Got {len(type_args)}"
        )
    if type_args[1] is not Ellipsis:
        raise ValueError(
            f"tuple field {a_field.name} second type parameter must be '...'. Got {type_args[1]}"
        )
    c_type = a_field.metadata[MetadataKey.C_TYPE]
    if c_type is None and not dataclasses.is_dataclass(type_args[0]):
        raise ValueError(
            f"tuple field {a_field.name} must either have a c_type, or the first type parameter must be a dataclass. Got {type_args[0]}"
        )


def element_size_for_field(a_field: dataclasses.Field):
    validate_collection_field_type(a_field)
    field_name = a_field.name
    c_type = a_field.metadata.get(MetadataKey.C_TYPE)

    # TODO consider alignment

    if c_type is not None:
        return ctypes.sizeof(c_type)

    # For both tuple and frozenset, the first type parameter is what we want
    cls = a_field.type.__args__[0]
    if not dataclasses.dataclass(cls):
        raise ValueError(f"{field_name} doesn't have a c_type and isn't a dataclass")

    try:
        return cls._size_as_element_  # pylint: disable=protected-access
    except AttributeError:
        raise ValueError(  # pylint: disable=raise-missing-from
            f"{field_name} must have _size_as_element_ attribute to be used as a field"
        )


def collection_type_for_field(a_field: dataclasses.Field):
    validate_collection_field_type(a_field)
    return a_field.type.__origin__


def dataclass_from_buffer(cls: type, buf, offset: int = 0) -> Any:
    print(f"reading dataclass {cls!r}")
    field_data = {}
    field_list = list(dataclasses.fields(cls))
    for a_field in field_list:
        if not a_field.init:
            continue
        field_data[a_field.name] = field_from_buffer(a_field, buf, offset)

    return cls(**field_data)


def field_from_buffer(a_field: dataclasses.Field, buf, base_offset: int = 0) -> Any:
    print(f"reading field {a_field.name!r} {a_field.type!r} {a_field.metadata!r} ...")
    field_offset = base_offset + a_field.metadata[MetadataKey.OFFSET]
    count = a_field.metadata[MetadataKey.COUNT]
    # Read single values directly
    if count == 1:
        return field_element_from_buffer(a_field, buf, field_offset)

    if count <= 0:
        raise ValueError(f"field {a_field.name} has non-positive count {count}")

    collection_type = collection_type_for_field(a_field)
    elem_size = 4  # element_size_for_field(a_field)
    values = []
    for i in range(0, count):
        elem_offset = field_offset + elem_size * i
        values.append(field_element_from_buffer(a_field, buf, elem_offset))
    return collection_type(values)


def field_element_from_buffer(a_field: dataclasses.Field, buf, elem_offset) -> Any:
    print(
        f"reading element for field {a_field.name!r} {a_field.type!r} {a_field.metadata!r} ..."
    )
    c_type = a_field.metadata.get(MetadataKey.C_TYPE)
    count = a_field.metadata.get(MetadataKey.COUNT)

    # TODO: Check if type is tuple or frozenset, since those aren't expected for single values.
    # TODO: Consider whether support array size 1
    underlying_type = a_field.type
    if count > 1:
        validate_collection_field_type(a_field)
        underlying_type = underlying_type.__args__[0]

    if c_type is not None:
        val = c_type.from_buffer(buf, elem_offset).value
        try:
            return underlying_type(val)
        except Exception as err:
            # TODO add this in other places, provide more detail
            raise Exception(
                f"failed to construct value for field {a_field.name}"
            ) from err

    if dataclasses.is_dataclass(underlying_type):
        return dataclass_from_buffer(underlying_type, buf, elem_offset)
    else:
        raise Exception(
            "Field {a_field.name} isn't a dataclass and doesn't have a c_type"
        )


print(dataclass_from_buffer(State, DEMO_BUFFER))
