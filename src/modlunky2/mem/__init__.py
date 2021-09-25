from __future__ import annotations  # PEP 563
import ctypes
from ctypes.wintypes import DWORD, HANDLE, LONG, MAX_PATH, WPARAM
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from struct import unpack, calcsize

import pywintypes  # pylint: disable=import-error
import win32api  # pylint: disable=import-error
import win32con  # pylint: disable=import-error
import win32process  # pylint: disable=import-error

from modlunky2.mem.state import State
from modlunky2.mem.memrauder.model import (
    MemoryReader,
    MemContext,
)

VirtualQueryEx = ctypes.windll.kernel32.VirtualQueryEx
CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
Process32First = ctypes.windll.kernel32.Process32First
Process32Next = ctypes.windll.kernel32.Process32Next
CloseHandle = ctypes.windll.kernel32.CloseHandle


TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = -1


@dataclass
class Spel2Reader(MemoryReader):
    proc: "Spel2Process"

    def read(self, addr: int, size: int) -> Optional[bytes]:
        return self.proc.read_memory(addr, size)


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("cntUsage", DWORD),
        ("th32ProcessID", DWORD),
        ("th32DefaultHeapID", WPARAM),
        ("th32ModuleID", DWORD),
        ("cntThreads", DWORD),
        ("th32ParentProcessID", DWORD),
        ("pcPriClassBase", LONG),
        ("dwFlags", DWORD),
        ("szExeFile", ctypes.c_char * MAX_PATH),
    ]


def process_list():
    processes = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if processes == INVALID_HANDLE_VALUE:
        return

    pe32 = PROCESSENTRY32()
    pe32.dwSize = (  # pylint: disable=attribute-defined-outside-init, invalid-name
        ctypes.sizeof(PROCESSENTRY32)
    )
    if Process32First(processes, ctypes.byref(pe32)) == win32con.FALSE:
        return

    while True:
        yield pe32
        if Process32Next(processes, ctypes.byref(pe32)) == win32con.FALSE:
            break

    CloseHandle(processes)


def find_spelunky2_pid() -> Optional[DWORD]:
    for proc in process_list():
        if proc.szExeFile == b"Spel2.exe":
            return proc.th32ProcessID
    return None


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

    def pprint(self):
        print("MemoryBasicInformation:")
        print(f"    Base Address: {hex(self.base_address)}")
        print(f"    Allocation Base: {hex(self.allocation_base)}")
        print(f"    Allocation Protect: {self.allocation_protect}")
        print(f"    Region Size: {self.region_size}")
        print(f"    State: {self.state}")
        print(f"    Protect: {self.protect}")
        print(f"    Type: {self.type}")


class FeedcodeNotFound(Exception):
    """Failed to find feedcode within Spelunky2 memory."""


class Spel2Process:
    def __init__(self, proc_handle):
        self.proc_handle = proc_handle
        self._feedcode = None
        self.mem_ctx = MemContext(Spel2Reader(self))

    @classmethod
    def from_pid(cls, pid):
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
        )
        if not handle:
            return None

        return cls(handle)

    def running(self):
        return win32con.STILL_ACTIVE == win32process.GetExitCodeProcess(
            self.proc_handle
        )

    def read_memory(self, offset, size):
        try:
            return win32process.ReadProcessMemory(self.proc_handle, offset, size)
        except pywintypes.error:
            return None

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

    def memory_pages(self, min_addr=0x10000, max_addr=0x00007FFFFFFEFFFF):
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
        return None

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

    def try_get_feedcode(self) -> Optional[int]:
        if self._feedcode is not None:
            return self._feedcode
        for page in self.memory_pages(min_addr=0x40000000000):
            result = self.find_in_page(page, b"\x00\xde\xc0\xed\xfe")
            if result:
                self._feedcode = result
                return result
        return None

    def get_feedcode(self) -> int:
        feedcode = self.try_get_feedcode()
        if feedcode is None:
            raise FeedcodeNotFound()
        return feedcode

    def get_state(self) -> Optional[State]:
        addr = self.get_feedcode() - 0x5F
        return self.mem_ctx.type_at_addr(State, addr)
