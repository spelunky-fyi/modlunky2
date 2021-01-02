import io

from pathlib import Path
import pymmh3
import re

def generate_string_hashes(strings00_data, hashed_strings_filepath: Path):
    hashed_strings = []
    current_comment_block = ""
    for string in  strings00_data.decode().splitlines():
        if string.startswith('#'):
            comment_block = string.strip(' #')
            if comment_block:
                current_comment_block = comment_block
            hashed_strings.append('')
        else:
            string_hash = pymmh3.hash64(string +  current_comment_block, seed = 0xD67FADD1)[1] & 0xFFFFFFFF
            hashed_strings.append("0x{:08x}".format(string_hash & 0xFFFFFFFF))
    hashed_strings = '\n'.join(hashed_strings)

    with hashed_strings_filepath.open("wb") as hashed_strings_file:
        hashed_strings_file.write(hashed_strings.encode())

def write_string_hashes(stringsXX_data, stringsXX_hashed_filepath: Path, hashed_strings_filepath: Path):
    with hashed_strings_filepath.open("r") as hashed_strings_file:
        hashed_strings = hashed_strings_file.read().splitlines()
        original_strings = stringsXX_data.decode().splitlines()

        merged_strings = [ f'{hash}: {string}' if hash else string for hash, string in zip(hashed_strings, original_strings) ]
        merged_strings = "\n".join(merged_strings)

        with stringsXX_hashed_filepath.open("wb") as stringsXX_hashed_file:
            stringsXX_hashed_file.write(merged_strings.encode())