r"""

Library for patching out checksum checking for assets.

This is the code that validates the checksum and calls exit() when it doesn't match:
                  /------------------------------------------\
cmp rax,rcx  jz -/   xor ecx,ecx  call cs:exit        int 3   \-> mov rcx,[rbp+17h]
48 3B C1     74 09   33 C9        FF ?? ?? ?? ?? ??   CC          48 8B 4D 17
48 3B C1     74 09   90 90        90 90 90 90 90 90   90
                     [               nop               ]

We overwrite the exit() call with NOPs
"""

import logging

PATCH_START = b"\x48\x3B\xC1\x74\x09\x33\xC9\xFF"
PATCH_END = 0xCC
PATCH_REPLACE = b"\x48\x3B\xC1\x74\x09" + b"\x90" * 9


logger = logging.getLogger("modlunky2")


class Patcher:
    def __init__(self, exe_handle):
        self.exe_handle = exe_handle

    def find(self, needle, offset=0, bsize=4096):
        if bsize < len(needle):
            raise ValueError(
                "The buffer size must be larger than the string being searched for."
            )

        self.exe_handle.seek(offset)
        overlap = len(needle) - 1

        while True:
            buffer = self.exe_handle.read(bsize)
            if not buffer:
                return -1

            pos = buffer.find(needle)
            if pos >= 0:
                return self.exe_handle.tell() - len(buffer) + pos

            if len(buffer) <= overlap:
                return -1

            self.exe_handle.seek(self.exe_handle.tell() - overlap)

    def is_patched(self) -> bool:
        """ Returns true of the binary has already been patched."""
        self.exe_handle.seek(0)
        return self.find(PATCH_START) == -1


    def patch(self):
        self.exe_handle.seek(0)

        logger.info("Patching asset checksum check")
        index = self.find(PATCH_START)
        if index == -1:
            logger.warning("Didn't find instructions to patch. Is game unmodified?")
            return False

        self.exe_handle.seek(index)
        ops = self.exe_handle.read(14)

        if ops[-1] != PATCH_END:
            logger.warning(
                "Checksum check has unexpected form, this script has "
                "to be updated for the current game version."
            )
            logger.warning("(Expected 0x{:02x}, found 0x{:02x})".format(PATCH_END, ops[-1]))
            return False

        logger.info("Found check at 0x{:08x}, replacing with NOPs".format(index))
        self.exe_handle.seek(index)
        self.exe_handle.write(PATCH_REPLACE)
