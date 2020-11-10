import logging
import struct
import textwrap
from pathlib import Path

from dll_injector import Injector


class ProcessNotRunning(Exception):
    pass


def ensure_attached(method):
    def inner(self, *args, **kwargs):
        if self.code_executor is None:
            logging.info("No process attached. Looking for Spel2.exe")
            proc = Injector.from_name(self.proc_name, self.dll_path)
            if proc is None:
                raise ProcessNotRunning("Can't find Spel2.exe running")
            logging.info("Found process (%s). Attaching...", proc)
            proc.inject()
            self.code_executor = proc

        try:
            method(self, *args, **kwargs)
        except Exception as err:
            self.code_executor = None
            logging.warning(f"Failed to run command ({err}). Process might have gone away. Attempting to reconnect.")
            proc = Injector.from_name(self.proc_name, self.dll_path)
            if proc is None:
                raise ProcessNotRunning("Can't find Spel2.exe running")
            logging.info("Found process (%s). Attaching...", proc)

            try:
                proc.inject()
                self.code_executor = proc
                method(self, *args, **kwargs)
            except Exception:
                self.code_exector = None
                raise ProcessNotRunning("Failed to run command. Attached process has gone away?")
    return inner


class CodeExecutionManager:
    def __init__(self, proc_name, dll_path):
        self.proc_name = proc_name
        self.dll_path = str(dll_path)
        self.code_executor = None

    @ensure_attached
    def load_entity(self, entity_num):
        self.code_executor.load_entity(entity_num, 1, 1)

    def shutdown(self):
        print("shutting down")
        self.code_executor = None
        print("shutting down 2")