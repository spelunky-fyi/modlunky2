import enum
from typing import Optional, TYPE_CHECKING
from struct import unpack

from .entities import EntityMap, Entity

if TYPE_CHECKING:
    from . import Spel2Process


class Player:
    def __init__(self, proc, offset):
        self._proc: "Spel2Process" = proc
        self._offset = offset

    def overlay(self) -> Optional[Entity]:
        offset = self._offset + 0x10
        entity_ptr = self._proc.read_void_p(offset)
        if not entity_ptr:
            return None
        return Entity(self._proc, entity_ptr)

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


class RunRecapFlags(enum.IntFlag):
    PACIFIST = 1 << 1 - 1
    VEGAN = 1 << 2 - 1
    VEGETARIAN = 1 << 3 - 1
    PETTY_CRIMINAL = 1 << 4 - 1
    WANTED_CRIMINAL = 1 << 5 - 1
    CRIME_LORD = 1 << 6 - 1
    KING = 1 << 7 - 1
    QUEEN = 1 << 8 - 1
    FOOL = 1 << 9 - 1
    EGGPLANT = 1 << 10 - 1
    NO_GOLD = 1 << 11 - 1
    LIKED_PETS = 1 << 12 - 1
    LOVED_PETS = 1 << 13 - 1
    TOOK_DAMAGE = 1 << 14 - 1
    USED_ANKH = 1 << 15 - 1
    KILLED_KINGU = 1 << 16 - 1
    KILLED_OSIRIS = 1 << 17 - 1
    NORMAL_ENDING = 1 << 18 - 1
    HARD_ENDING = 1 << 19 - 1
    SPECIAL_ENDING = 1 << 20 - 1
    DIED = 1 << 21 - 1


class HudFlags(enum.IntFlag):
    UPBEAT_DWELLING_MUSIC = 1 << 1 - 1
    RUNNING_TUTORIAL_SPEEDRUN = 1 << 3 - 1
    ALLOW_PAUSE = 1 << 20 - 1
    HAVE_CLOVER = 1 << 23 - 1


class State:
    def __init__(self, proc):
        self._proc: "Spel2Process" = proc
        self._offset = proc.get_feedcode() - 0x5F

    def run_recap_flags(self):
        offset = self._offset + 0x9F4
        return RunRecapFlags(self._proc.read_u32(offset))

    def hud_flags(self):
        offset = self._offset + 0xA10
        return HudFlags(self._proc.read_u32(offset))

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

    def time_total(self):
        offset = self._offset + 0x64
        return self._proc.read_u32(offset)

    def uid_to_entity(self):
        offset = self._offset + 0x1308
        return EntityMap(self._proc, offset)
