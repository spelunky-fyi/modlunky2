import contextlib
import logging
import sys
import traceback
import os
import subprocess
import webbrowser
import struct
import zipfile
from functools import wraps

from modlunky2.assets.patcher import Patcher

logger = logging.getLogger("modlunky2")


def is_patched(exe_filename):
    with exe_filename.open("rb") as exe:
        return Patcher(exe).is_checksum_patched()


def tb_info():
    return "".join(traceback.format_exception(*sys.exc_info())).strip()


def is_windows():
    return "nt" in os.name


def open_directory(directory):
    if not directory.exists():
        return

    if not is_windows():
        subprocess.run(["xdg-open", f"{directory}"], check=False)
        return

    webbrowser.open(f"file://{directory}")


@contextlib.contextmanager
def temp_chdir(new_dir):
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_dir)


def zipinfo_fixup_filename(inf: zipfile.ZipInfo):
    # Support UTF-8 filenames using extra fields
    # Code from https://github.com/python/cpython/pull/23736
    extra = inf.extra
    unpack = struct.unpack

    while len(extra) >= 4:
        type_, length = struct.unpack("<HH", extra[:4])
        if length + 4 > len(extra):
            raise zipfile.BadZipFile(
                "Corrupt extra field %04x (size=%d)" % (type_, length)
            )

        if type_ == 0x7075:
            data = extra[4 : length + 4]
            # Unicode Path Extra Field
            up_version, _up_name_crc = unpack("<BL", data[:5])
            up_unicode_name = data[5:].decode("utf-8")
            if up_version == 1:
                inf.filename = up_unicode_name

        extra = extra[length + 4 :]
