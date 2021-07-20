import zipfile
import struct
import zlib
from io import BytesIO

from modlunky2.ui.install import get_zip_members


def make_zip(in_files):
    zip_file = zipfile.ZipFile(BytesIO(), "w")
    for in_file in in_files:
        zip_file.writestr(zipfile.ZipInfo(filename=in_file), b"")

    return zip_file


def compare_zip(in_files, out_files):
    zip_file = make_zip(in_files)
    for idx, out_file in enumerate(get_zip_members(zip_file)):
        assert out_file.filename == out_files[idx]


def test_rename_to_main_lua():
    in_files = ["foo.lua"]
    out_files = ["main.lua"]
    compare_zip(in_files, out_files)

    in_files = ["foo/foo.lua"]
    out_files = ["main.lua"]
    compare_zip(in_files, out_files)

    in_files = ["foo/foo.lua", "bar.lua"]
    compare_zip(in_files, in_files)


def test_data_and_soundbank_no_unwrap():
    in_files = ["Data/foo"]
    compare_zip(in_files, in_files)

    in_files = ["soundbank/foo"]
    compare_zip(in_files, in_files)


def test_unwrap_common_dir():
    in_files = ["foo/test.png", "foo/bar.png"]
    out_files = ["test.png", "bar.png"]
    compare_zip(in_files, out_files)

    in_files = ["foo/test.png", "foo/bar.png", "test"]
    compare_zip(in_files, in_files)


def test_bat_frend_regression():
    in_files = ["main.lua", "mod_info.json", "custom_images/batty.png"]
    compare_zip(in_files, in_files)


def test_unicode_filename():
    in_files = [_.decode("cp437") for _ in [b"\xb0\xa1\xb3\xaa\xb4\xd9", b"main.lua"]]
    expected = ["\uac00\ub098\ub2e4", "main.lua"]

    # Write extra field: 0x7075 "Info-ZIP Unicode Path Extra Field"
    zip_file = make_zip(in_files)
    for idx, _ in enumerate(zip_file.infolist()):
        zip_info = zip_file.getinfo(in_files[idx])
        encoded_name = expected[idx].encode("utf8")
        zip_info.extra = (
            struct.pack(
                "<HHBL",
                0x7075,
                len(encoded_name) + 5,
                1,
                zlib.crc32(in_files[idx].encode("cp437")),
            )
            + encoded_name
        )

    # Check if the unicode filename is used instead
    for idx, out_file in enumerate(get_zip_members(zip_file)):
        assert out_file.filename == expected[idx]
