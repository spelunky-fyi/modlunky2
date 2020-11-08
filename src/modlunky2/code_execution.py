import struct
import time
import textwrap
from pathlib import Path
import logging

import psutil

from .injectlib import Injector

DELTA = 0xc00


def signed(x):
    return x if x & 0x80000000 == 0 else x - 0x100000000


def find_process(name):
    for proc in psutil.process_iter(["name", "pid"]):
        if proc.name() == name:
            return proc


class ProcessNotRunning(Exception):
    pass


def ensure_attached(method):
    def inner(self, *args, **kwargs):
        if self.code_executor is None:
            logging.info("No process attached. Looking for Spel2.exe")
            proc = find_process(self.proc_name)
            if proc is None:
                raise ProcessNotRunning("Can't find Spel2.exe running")
            logging.info("Found process (%s). Attaching...", proc)
            self.code_executor = CodeExecutor(proc)

        try:
            method(self, *args, **kwargs)
        except Exception:
            self.code_executor = None
            logging.warning("Failed to run command. Process might have gone away. Attempting to reconnect.")
            proc = find_process(self.proc_name)
            if proc is None:
                raise ProcessNotRunning("Can't find Spel2.exe running")
            logging.info("Found process (%s). Attaching...", proc)

            try:
                self.code_executor = CodeExecutor(proc)
                method(self, *args, **kwargs)
            except Exception:
                self.code_exector = None
                raise ProcessNotRunning("Failed to run command. Attached process has gone away?")
    return inner


class CodeExecutionManager:
    def __init__(self, proc_name):
        self.proc_name = proc_name
        self.code_executor = None

    @ensure_attached
    def spawn_item(self, item_num):
        self.code_executor.spawn_item(item_num)


class CodeExecutor:
    def __init__(self, proc):
        """Attach to a process for allowing code execution."""

        with Path(proc.cmdline()[0]).open('rb') as proc_file:
            self.data = proc_file.read()

        self.proc = Injector(proc)
        self.base = self.proc.find_base('spel2.exe')
        self.main_thread = self.proc.threads()[0]

        _, self.state = self.find('83 78 0C 05 0F 85 ', -15)
        self.state = self.proc.r64(self.base + self.state)

        _, self.layer_off = self.find('C6 80 58 44 06 00 01 ', -7, 'imm')

        inst, _ = self.find('BA 88 02 00 00', 1, 'off')
        self.load_item, _ = self.find('BA 88 02 00 00', 8, 'off', start=inst)
        self.load_item += signed(struct.unpack_from("<L", self.data, self.load_item + 1)[0]) + 5
        self.load_item += DELTA
        self.load_item += self.base

        _, self.items_off = self.find('33 D2 8B 41 28 01', -7, 'imm')

        self.load_code()

    def find(self, sep, offset=-7, type='pc', start=0):
        off = self.data.find(bytes.fromhex(sep), start)
        if type == 'off':
            return off + offset, None
        inst = self.data[off + offset:off]
        off2, = struct.unpack_from("<L", inst, 3)
        if type == 'imm':
            gm = off2
        elif type == 'pc':
            gm = off + offset + 7 + off2 + DELTA
        return off + DELTA, gm

    def load_code(self):
        self.proc.run(textwrap.dedent(rf"""
        import os
        import sys

        try:
            import ctypes
        except Exception as err:
            os.system('''msg * "%s"''' % err)

        class CriticalSection:
            def __enter__(self, *args):
                ctypes.windll.kernel32.SuspendThread({self.main_thread})

            def __exit__(self, *args):
                ctypes.windll.kernel32.ResumeThread({self.main_thread})

        def with_critical(f):
            def inner(*args, **kwargs):
                try:
                    with CriticalSection():
                        f(*args, **kwargs)
                except Exception as e:
                    os.system("msg * \"Failed: %s\"" % e)
            return inner

        load_item = with_critical((ctypes.CFUNCTYPE(ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int64,
            ctypes.c_float,
            ctypes.c_float
        ))({self.load_item}))

        """).strip().encode())

    def spawn_item(self, item_num, rel_x=1, rel_y=1):
        layer = self.proc.r64(self.state + self.layer_off)
        items = self.proc.r64(self.state + self.items_off)

        player_index = self.proc.r8(items)
        size = self.proc.r8(items + 1)
        player = self.proc.r64(items + 8 + player_index * 8)

        # Player X, Y
        x, y = struct.unpack("<2f", self.proc.read(player + 0x40, 8))
        x += rel_x
        y += rel_y

        #print(f"State: {self.state}, Layer Offset: {self.layer_off}, Load Item: {self.load_item}")
        #print(f"Layer: {layer}, Items: {items}, Player Index: {player_index}, Size: {size}, Player: {player}")
        
        self.proc.run(rf"load_item({layer}, {item_num}, {x}, {y})".encode())