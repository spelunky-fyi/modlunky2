import ctypes
from ctypes.wintypes import DWORD, HANDLE
from dataclasses import dataclass
from typing import ClassVar, Optional
from pathlib import Path
from struct import pack, unpack, calcsize

import fnvhash
import pywintypes
import psutil
import win32api
import win32con
import win32process


VirtualQueryEx = ctypes.windll.kernel32.VirtualQueryEx


def find_spelunky2_pid() -> Optional[psutil.Process]:
    for proc in psutil.process_iter():
        try:
            if proc.name() == "Spel2.exe":
                return proc.pid
        except psutil.NoSuchProcess:
            continue


class _MEMORY_BASIC_INFORMATION64(ctypes.Structure):  # pylint: disable=invalid-name
    _fields_ = [
        ("BaseAddress", ctypes.c_ulonglong),
        ("AllocationBase", ctypes.c_ulonglong),
        ("AllocationProtect", DWORD),
        ("__alignment1", DWORD),
        ("RegionSize", ctypes.c_ulonglong),
        ("State", DWORD),
        ("Protect", DWORD),
        ("Type", DWORD),
        ("__alignment2", DWORD),
    ]


class MemoryBasicInformation:
    def __init__(self, mbi):
        self.base_address = mbi.BaseAddress
        self.allocation_base = mbi.AllocationBase
        self.allocation_protect = mbi.AllocationProtect
        self.region_size = mbi.RegionSize
        self.state = mbi.State
        self.protect = mbi.Protect
        self.type = mbi.Type

    @classmethod
    def from_virtual_query(cls, proc_handle, addr):
        mbi = _MEMORY_BASIC_INFORMATION64()
        size = ctypes.c_size_t(ctypes.sizeof(mbi))

        written = VirtualQueryEx(
            HANDLE(int(proc_handle)),
            ctypes.c_ulonglong(addr),
            ctypes.byref(mbi),
            size,
        )

        if not written:
            return None

        return cls(mbi)


class Spel2Process:
    def __init__(self, proc_handle):
        self.proc_handle = proc_handle

    @classmethod
    def from_pid(cls, pid):
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
        )
        if not handle:
            return

        return cls(handle)

    def read_memory(self, offset, size):
        try:
            return win32process.ReadProcessMemory(self.proc_handle, offset, size)
        except pywintypes.error:
            return None

    def read_u16(self, offset):
        result = self.read_memory(offset, 2)
        if result is None:
            return None

        return unpack(b"<H", result)[0]

    def read_u32(self, offset):
        result = self.read_memory(offset, 4)
        if result is None:
            return None

        return unpack(b"<L", result)[0]

    def read_i32(self, offset):
        result = self.read_memory(offset, 4)
        if result is None:
            return None

        return unpack(b"<l", result)[0]

    def read_u64(self, offset):
        result = self.read_memory(offset, 8)
        if result is None:
            return None

        return unpack(b"<Q", result)[0]

    def read_i64(self, offset):
        result = self.read_memory(offset, 8)
        if result is None:
            return None

        return unpack(b"<q", result)[0]

    def read_void_p(self, offset):
        result = self.read_memory(offset, calcsize(b"P"))
        if result is None:
            return None
        return unpack(b"P", result)[0]

    def read_vector(self, offset, format_char):
        result = self.read_memory(offset, 24)
        if result is None:
            return result

        data_ptr = unpack(b"P", result[8:16])[0]
        size = unpack(b"<L", result[20:24])[0]
        out = []
        if not size:
            return out

        item_size = calcsize(format_char)

        result = self.read_memory(data_ptr, size * item_size)
        if result is None:
            return None

        return [
            unpack(format_char, result[idx : idx + item_size])[0]
            for idx in range(0, len(result), item_size)
        ]

    def find(self, offset, needle, bsize=4096):
        if bsize < len(needle):
            raise ValueError(
                "The buffer size must be larger than the string being searched for."
            )

        cursor = offset
        overlap = len(needle) - 1
        while True:
            buffer = self.read_memory(cursor, bsize)
            if not buffer:
                return None
            cursor += len(buffer)

            pos = buffer.find(needle)
            if pos >= 0:
                return cursor - len(buffer) + pos

            if len(buffer) <= overlap:
                return None

            cursor -= overlap

    def find_one(self, start, needle, size):
        buffer = self.read_memory(start, size)
        if buffer is None:
            return None

        pos = buffer.find(needle)
        if pos >= 0:
            return start + pos

        return None

    def find_in_page(self, mbi: MemoryBasicInformation, needle):
        return self.find(mbi.base_address, needle, mbi.region_size)

    def memory_pages(self):
        min_addr = 0x10000
        max_addr = 0x00007FFFFFFEFFFF

        addr = min_addr

        while True:
            mbi = MemoryBasicInformation.from_virtual_query(self.proc_handle, addr)
            if not mbi:
                break

            addr += mbi.region_size

            if mbi.state != win32con.MEM_COMMIT:
                continue

            if mbi.type != win32con.MEM_PRIVATE:
                continue

            if mbi.protect & win32con.PAGE_NOACCESS:
                continue

            yield mbi

            if addr >= max_addr:
                break

    def get_spel2_module(self):
        module_handles = win32process.EnumProcessModules(self.proc_handle)
        for module_handle in module_handles:

            module_filename = Path(
                win32process.GetModuleFileNameEx(self.proc_handle, module_handle)
            )

            if module_filename.name == "Spel2.exe":
                return module_handle

    def get_offset_past_bundle(self):
        exe = self.get_spel2_module()
        offset = 0x1000

        while True:
            header = win32process.ReadProcessMemory(self.proc_handle, exe + offset, 8)
            data_len, filepath_len = unpack(b"<II", header)
            if (data_len, filepath_len) == (0, 0):
                break
            offset += 8 + data_len + filepath_len

        return exe + offset

    def get_feedcode(self):
        for page in self.memory_pages():
            result = self.find_in_page(page, b"\x00\xde\xc0\xed\xfe")
            if result:
                return result
        return None

    def get_state(self):
        return State(self)

    def get_entity_db(self):
        return EntityDB(self)


class Player:
    def __init__(self, proc, offset):
        self._proc: Spel2Process = proc
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
        self._proc: Spel2Process = proc
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


@dataclass
class UnorderedMapMeta:
    SIZE: ClassVar[int] = 64

    # Terminal address for Node linked list
    end: int
    size: int
    buckets_ptr: int
    mask: int
    bucket_size: int

    @classmethod
    def from_offset(cls, proc, offset):
        data = proc.read_memory(offset, cls.SIZE)

        end = unpack("<Q", data[8 : 8 + 8])[0]
        size = unpack("<Q", data[16 : 16 + 8])[0]
        buckets_ptr = unpack("P", data[24 : 24 + 8])[0]
        mask = unpack("<Q", data[48 : 48 + 8])[0]
        bucket_size = unpack("<Q", data[56 : 56 + 8])[0]

        return cls(end, size, buckets_ptr, mask, bucket_size)


@dataclass
class Bucket:
    SIZE: ClassVar[int] = 16
    first: int
    last: int

    @classmethod
    def from_offset(cls, proc, offset):
        data = proc.read_memory(offset, cls.SIZE)

        first = unpack("P", data[0 : 0 + 8])[0]
        last = unpack("P", data[8 : 8 + 8])[0]
        return cls(first, last)


@dataclass
class Node:

    SIZE: ClassVar[int] = 32

    next: int
    prev: int
    key: int
    value: int

    @classmethod
    def from_offset(cls, proc, offset, key_char, value_char) -> "Node":
        key_size = calcsize(key_char)
        value_size = calcsize(value_char)
        data = proc.read_memory(offset, cls.SIZE)

        next_ = unpack("P", data[0 : 0 + 8])[0]
        prev = unpack("P", data[8 : 8 + 8])[0]
        key = unpack(key_char, data[16 : 16 + key_size])[0]
        # key + 8 regardless of keysize because of padding
        value = unpack(value_char, data[24 : 24 + value_size])[0]

        return Node(next_, prev, key, value)


class UnorderedMap:
    KEY_CHAR = "<Q"
    VALUE_CHAR = "P"

    def __init__(self, proc, offset):
        self._proc: Spel2Process = proc
        self._offset = offset

    def _get_meta(self) -> UnorderedMapMeta:
        return UnorderedMapMeta.from_offset(self._proc, self._offset)

    def get_node(self, offset):
        return Node.from_offset(self._proc, offset, self.KEY_CHAR, self.VALUE_CHAR)

    def get(self, key, meta: UnorderedMapMeta = None):
        if meta is None:
            meta = self._get_meta()

        bucket = self.get_bucket(key, meta)

        # Empty bucket
        if bucket.first == meta.end:
            return None

        next_ = bucket.first
        while True:
            node = self.get_node(next_)

            # Found key!
            if node.key == key:
                return node.value

            # We've searched the final bucket. give up...
            if next_ == bucket.last:
                return None

            next_ = node.next

    def get_bucket(self, key, meta: UnorderedMapMeta = None) -> Bucket:
        if meta is None:
            meta = self._get_meta()
        idx = self._get_bucket_idx(key, meta)
        offset = meta.buckets_ptr + (idx * Bucket.SIZE)
        return Bucket.from_offset(self._proc, offset)

    def _hash_key(self, key) -> int:
        bytes_ = pack(self.KEY_CHAR, key)
        return fnvhash.fnv1a_64(bytes_)

    def _get_bucket_idx(self, key, meta: UnorderedMapMeta = None) -> int:
        if meta is None:
            meta = self._get_meta()
        return self._hash_key(key) & meta.mask


class EntityMap(UnorderedMap):
    KEY_CHAR = "<L"
    VALUE_CHAR = "P"

    def get(self, key, meta=None):
        result = super().get(key)
        if result is None:
            return None

        return Entity(self._proc, result)


class EntityDBEntry:
    def __init__(self, proc, offset):
        self._proc: Spel2Process = proc
        self._offset = offset

    def id(self):
        return self._proc.read_u32(self._offset + 0x14)


class EntityDB:

    ENTITY_DB_SIZE = 256  # Size of EntityDB

    def __init__(self, proc):
        self._proc: Spel2Process = proc
        self._offset = proc.get_offset_past_bundle()
        self._entity_db_ptr = self._get_entity_db_ptr()

    def _get_entity_db_ptr(self):
        entity_instr = self._proc.find(
            self._offset, b"\x48\xB8\x02\x55\xA7\x74\x52\x9D\x51\x43"
        )
        return self._proc.read_void_p(
            entity_instr + self._proc.read_u32(entity_instr - 4)
        )

    def get_entity_db_entry_by_id(self, entity_id) -> EntityDBEntry:
        return EntityDBEntry(
            self._proc, self._entity_db_ptr + (self.ENTITY_DB_SIZE * entity_id)
        )


class Entity:
    def __init__(self, proc, offset):
        self._proc: Spel2Process = proc
        self._offset = offset

    def type(self):
        result = self._proc.read_void_p(self._offset + 8)
        return EntityDBEntry(self._proc, result)


def test():
    print("Finding Spel2.exe")
    pid = find_spelunky2_pid()
    if pid is None:
        print("Failed to get pid")
        return

    print("Opening Process")
    proc = Spel2Process.from_pid(pid)
    if proc is None:
        print("Failed to make proc")
        return

    print("Getting State")
    state = proc.get_state()

    # Get EntityDB Type
    entity_db = proc.get_entity_db()
    entry = entity_db.get_entity_db_entry_by_id(4)
    print(entry.id())

    player1 = state.players()[0]
    print(player1.items())

    entity_map = state.uid_to_entity()
    print(entity_map.get(1041).type().id())


if __name__ == "__main__":
    test()
