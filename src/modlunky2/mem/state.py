from typing import TYPE_CHECKING
from struct import unpack

from .entities import EntityMap

if TYPE_CHECKING:
    from . import Spel2Process


class Player:
    def __init__(self, proc, offset):
        self._proc: "Spel2Process" = proc
        self._offset = offset

    def items(self):
        offset = self._offset + 0x18
        return self._proc.read_vector(offset, "<L")

    def inside(self):
        """std::map. Need to implement red/black tree."""
        # inside = player1_ent_addr + 0x128
        # print("inside", hex(inside))
        # print("")

        # node1_addr = proc.read_void_p(inside)
        # print("node1_addr", hex(node1_addr))
        # print("")

        # x = proc.read_memory(node1_addr, 8 * 3)
        # pointers = unpack(b"PPP", x)
        # print("x", list(map(hex, pointers)))
        # print("x more", proc.read_memory(node1_addr + (8 * 3), 4))
        # print(proc.read_memory(node1_addr + (8 * 3) + 4, 16))
        # print("x more", proc.read_u16(node1_addr + (8 * 3) + 4))

        # print("")
        # p = pointers[0]
        # x = proc.read_memory(p, 8 * 3)
        # pointers = unpack(b"PPP", x)
        # print("x", list(map(hex, pointers)))
        # print("x more", proc.read_memory(p + (8 * 3), 4))
        # print(proc.read_memory(p + (8 * 3) + 4, 16))
        # print("x more", proc.read_u16(p + (8 * 3) + 4))

        # print("")
        # p = pointers[2]
        # x = proc.read_memory(p, 8 * 3)
        # pointers = unpack(b"PPP", x)
        # print("x", list(map(hex, pointers)))
        # print("x more", proc.read_memory(p + (8 * 3), 4))
        # print("x more", hex(proc.read_u16(p + (8 * 3) + 4)))
        # item_count = proc.read_u64(inside + 8)


class State:
    def __init__(self, proc):
        self._proc: "Spel2Process" = proc
        self._offset = proc.get_feedcode() - 0x5F  ##0x85D

    def run_recap(self):
        offset = self._offset + 0x9F4
        return self._proc.read_u32(offset)

    def players(self):  # items
        offset = self._offset + 0x12B0
        items_ptr = self._proc.read_void_p(offset) + 8
        player_pointers = self._proc.read_memory(items_ptr, 8 * 4)

        players = []

        for idx in range(0, len(player_pointers), 8):
            player_pointer = player_pointers[idx : idx + 8]
            if player_pointer == b"\x00\x00\x00\x00\x00\x00\x00\x00":
                players.append(None)
                continue

            player_pointer = unpack("P", player_pointer)[0]
            players.append(Player(self._proc, player_pointer))

        return players

    def uid_to_entity(self):
        offset = self._offset + 0x1308
        return EntityMap(self._proc, offset)
