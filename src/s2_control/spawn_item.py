import struct
import time
import lief

from .injectlib import Injector


def signed(x):
    return x if x & 0x80000000 == 0 else x - 0x100000000


class ItemSpawner:
    def __init__(self, target):
        self.data = open(target, 'rb').read()

        pe = lief.parse(target)
        for sect in pe.sections:
            if sect.name == '.text':
                delta = -sect.offset + sect.virtual_address

        proc = Injector.from_name('Spel2.exe')
        base = proc.find_base('spel2.exe')

        _, state = self.find('83 78 0C 05 0F 85 ', -15)
        state = proc.r64(base + state)

        _, layer_off = self.find('C6 80 58 44 06 00 01 ', -7, 'imm')
        layer = proc.r64(state + layer_off)

        print(hex(state + layer_off))

        inst, _ = self.find('BA 88 02 00 00', 1, 'off')

        self.load_item, _ = self.find('BA 88 02 00 00', 8, 'off', start=inst)
        self.load_item += signed(struct.unpack_from("<L", data, load_item + 1)[0]) + 5
        self.load_item += delta
        self.load_item += base

        self.main_thread = proc.threads()[0]

    def spawn(self, item):
        proc.run(rf"""
        import ctypes
        import sys
        import os

        def hook(name, *args):
            if name != 'ctypes.seh_exception':
                return
            os.system("cmd")

        sys.addaudithook(hook)

        class CriticalSection:
            def __enter__(self, *args):
                ctypes.windll.kernel32.SuspendThread({self.main_thread})

            def __exit__(self, *args):
                ctypes.windll.kernel32.ResumeThread({self.main_thread})

        # load_item(state.layer[0], entity_name, x, y)
        try:
            with CriticalSection():
                load_item = (ctypes.CFUNCTYPE(ctypes.c_void_p,
                    ctypes.c_void_p,
                    ctypes.c_int64,
                    ctypes.c_float,
                    ctypes.c_float))({self.load_item})
                for i in range(30):
                    instance = load_item({self.layer}, {item}, i, 84.0)
        except Exception as e:
            import os
            os.system("msg * \"%s\"" % e)
        """.strip().encode())

        print(proc.r8(state + 0x65))
        print(proc.r8(state + 0x67))
        print(proc.r8(state + 0x71))


    def find(self, sep, offset=-7, type='pc', start=0):
        off = self.data.find(bytes.fromhex(sep), start)
        if type == 'off':
            return off + offset, None
        inst = self.data[off + offset:off]
        off2, = struct.unpack_from("<L", inst, 3)
        if type == 'imm':
            gm = off2
        elif type == 'pc':
            gm = off + offset + 7 + off2 + delta
        return off + delta, gm
