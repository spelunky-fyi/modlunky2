import ctypes
from ctypes.wintypes import DWORD, HANDLE
from typing import Optional
from pathlib import Path
from struct import unpack

import win32api
import win32con
import pywintypes
import psutil
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

    def read_u32(self, offset):
        result = self.read_memory(offset, 4)
        if result is None:
            return None

        return unpack(b"<L", result)[0]

    def find(self, start, needle, size):

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

    def get_offset_past_bundle(self, exe):
        offset = 0x1000

        while True:
            header = win32process.ReadProcessMemory(self.proc_handle, exe + offset, 8)
            data_len, filepath_len = unpack(b"<II", header)
            if (data_len, filepath_len) == (0, 0):
                break
            offset += 8 + data_len + filepath_len

        return offset
