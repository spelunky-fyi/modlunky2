import ctypes
import psutil
import struct


kernel32 = ctypes.windll.kernel32

error = kernel32.GetLastError
gpa = kernel32.GetProcAddress
gpa.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
gpa.restype = ctypes.c_void_p
alloc = kernel32.VirtualAllocEx
alloc.restype = ctypes.c_void_p


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.c_int32),
        ('cntUsage', ctypes.c_int32),
        ('th32ThreadID', ctypes.c_int32),
        ('th32OwnerProcessID', ctypes.c_int32),
        ('tpBasePri', ctypes.c_int32),
        ('tpDeltaPri', ctypes.c_int32),
        ('dwFlags', ctypes.c_int32)
    ]


class Injector:
    def __init__(self, proc):
        self.proc = proc
        self.pid = proc.pid
        self.handle = kernel32.OpenProcess(0x1f0fff, False, proc.pid)

        self.python_loaded = False

    def find_base(self, name):
        for dll in self.proc.memory_maps(grouped=False):
            if name in dll.path.lower():
                base = int(dll.addr.split('-')[0], 16)
                break
        return base

    @staticmethod
    def from_name(name):
        for proc in psutil.process_iter():
            if proc.name() == name:
                return Injector(proc)

        raise Exception("Not found!")

    def read(self, addr, size):
        n_reads = (ctypes.c_int32 * 1)()
        buf = ctypes.create_string_buffer(size)
        buf[:size] = b'\x00' * size
        res = kernel32.ReadProcessMemory(
            self.handle, ctypes.c_uint64(addr), buf, ctypes.c_uint64(size), n_reads)
        assert res, "Error: %d" % error()
        return buf.raw

    def write(self, addr, payload):
        n_reads = (ctypes.c_int32 * 1)()
        size = len(payload)
        buf = ctypes.create_string_buffer(size)
        buf[:size] = payload
        res = kernel32.WriteProcessMemory(
            self.handle, ctypes.c_uint64(addr), buf, ctypes.c_uint64(size), n_reads)
        assert res, "Error: %d" % error()
        return buf.raw

    def r64(self, addr):
        return struct.unpack("<Q", self.read(addr, 8))[0]

    def w64(self, addr, p):
        res = struct.pack("<Q", p)
        write(addr, res)

    def r32(self, addr):
        return struct.unpack("<L", self.read(addr, 4))[0]

    def w32(self, addr, p):
        res = struct.pack("<L", p)
        self.write(addr, res)

    def r8(self, addr):
        return struct.unpack("<B", self.read(addr, 1))[0]

    def w8(self, addr, p):
        res = struct.pack("<B", p)
        self.write(addr, res)

    def alloc(self, size=None, payload=None):
        if size is None and payload is None:
            raise Exception("size or payload is required")

        if payload is not None and not isinstance(payload, bytes):
            raise Exception("Please encode your payload first!")

        if size is None:
            size = len(payload) + 0xfff
            size -= size & 0xfff

        addr = alloc(self.handle, None, size, 0x1000, 0x40)

        if addr is not None:
            if payload is not None:
                self.write(addr, payload)
            return addr
        else:
            raise Exception("Allocation failed: %d" % error())

    def load_lib(self, name):
        ldw = gpa(kernel32._handle, b'LoadLibraryA')
        self.call(ldw, self.alloc(payload=name))

    def call(self, addr, args):
        assert addr
        tid = (ctypes.c_uint32 * 1)()
        handle = kernel32.CreateRemoteThread(self.handle,
            None,
            0,
            ctypes.c_void_p(addr),
            ctypes.c_void_p(args),
            0,
            tid)
        assert tid[0]
        kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0xFFFFFFFF)

    def run(self, code):
        py = ctypes.windll.python38
        if not self.python_loaded:
            buf = ctypes.create_string_buffer(0x1000)
            kernel32.GetModuleFileNameA(ctypes.c_void_p(py._handle), buf, ctypes.c_uint64(0x1000))

            self.load_lib(buf.raw)
            self.call(gpa(py._handle, b'Py_Initialize'), 0)
            self.python_loaded = True

        self.call(gpa(py._handle, b'PyRun_SimpleString'), self.alloc(payload=code))

    def threads(self):
        snapshot = kernel32.CreateToolhelp32Snapshot(4, 0)
        buf = (THREADENTRY32 * 1)()
        buf[0].dwSize = ctypes.sizeof(buf)
        success = kernel32.Thread32First(snapshot, buf)
        threads = []
        while success:
            if buf[0].th32OwnerProcessID == self.pid:
                threads.append(buf[0].th32ThreadID)
            success = kernel32.Thread32Next(snapshot, buf)
        return threads