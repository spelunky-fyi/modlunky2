from dataclasses import dataclass
from typing import ClassVar, FrozenSet, Tuple, Optional

from modlunky2.mem.memrauder.dsl import (
    array,
    sc_bool,
    sc_uint8,
    sc_uint16,
    dc_struct,
    pointer,
    struct_field,
)
from modlunky2.mem.memrauder.model import (
    BytesReader,
    DataclassStruct,
    FieldPath,
    mem_type_from_bytes,
)


@dataclass(frozen=True)
class Player:
    _size_as_element_: ClassVar[int] = 3
    bombs: int = struct_field(0x0, sc_uint8)
    ropes: int = struct_field(0x1, sc_uint8)


@dataclass(frozen=True)
class State:
    level: int = struct_field(0x0, sc_uint8)
    bool_tuple: Tuple[bool, ...] = struct_field(0x2, array(sc_bool, 3))
    player_set: FrozenSet[Player] = struct_field(0x5, array(dc_struct, 2))
    pointed_int: Optional[int] = struct_field(0xB, pointer(sc_uint16))


def test_player():
    player_mt = DataclassStruct(FieldPath(), Player)
    state_bytes = b"\x10\x20"
    assert mem_type_from_bytes(player_mt, state_bytes) == Player(16, 32)


def test_state():
    state_mt = DataclassStruct(FieldPath(), State)
    state_bytes = (
        b"\x05\xff\x00\x01\x01\x63\x2a\xff\x08\x01\xff\x02\x00\x00\x00\x00\x00\x00\x00"
    )
    bytes_reader = BytesReader(b"\x00\x00\x03\x01")
    expected = State(
        5, (False, True, True), frozenset([Player(99, 42), Player(8, 1)]), 259
    )
    assert mem_type_from_bytes(state_mt, state_bytes, bytes_reader) == expected
