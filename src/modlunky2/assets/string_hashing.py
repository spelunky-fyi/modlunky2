import zlib
import logging
from pathlib import Path


class StringHashes:
    def __init__(self, hashes):
        # A list of crc32 hashes of the line striped of whitespace.
        # If None the line should be written as is, otherwise the
        # line should be written as `crc_hash: original line of text`.
        self.hashes = hashes

    @classmethod
    def from_data(cls, strings_data):
        hashes = []
        current_comment_section = None

        for line in strings_data.decode().splitlines():
            if line.startswith("#"):
                comment_section = line.strip(" #")
                if comment_section:
                    current_comment_section = comment_section
                string_hash = None
            else:
                str_to_hash = line.strip()
                if current_comment_section is not None:
                    str_to_hash += current_comment_section

                string_hash = "0x{:08x}".format(zlib.crc32(str_to_hash.encode()))

            hashes.append(string_hash)

        return cls(hashes=hashes)

    def write_string_hashes(self, strings_data, hashed_strings_dest: Path):
        lines = strings_data.decode().splitlines()
        if len(lines) != len(self.hashes):
            logging.debug("Data for %s has %s lines, expected %s.")
            return

        with hashed_strings_dest.open("wb") as hashed_strings_file:
            for line_num, line in enumerate(lines):
                if line_num >= len(self.hashes):
                    hashed_strings_file.write(f"{line}\n".encode())
                    continue

                string_hash = self.hashes[line_num]
                if string_hash is None:
                    output_line = line
                else:
                    output_line = f"{string_hash}: {line}"

                hashed_strings_file.write(f"{output_line}\n".encode())
