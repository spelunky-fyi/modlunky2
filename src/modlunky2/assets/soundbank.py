import argparse
import logging
from enum import Enum
from pathlib import Path

import fsb5
from fsb5.utils import LibraryNotFoundException

from .riff import RIFF


logger = logging.getLogger("modlunky2")


class Extension(Enum):
    WAV = "wav"
    OGG = "ogg"


def extract_soundbank(
    soundbank_path: Path, dest_path: Path, extract_extensions: Extension = None
):

    if extract_extensions:
        extract_extensions = set(ext.value for ext in extract_extensions)

    for ext in Extension:
        if extract_extensions and ext.value not in extract_extensions:
            continue
        ext_dest_path = dest_path / ext.value
        if not ext_dest_path.exists():
            ext_dest_path.mkdir(parents=True, exist_ok=True)

    with soundbank_path.open("rb") as soundbank_file:
        riff = RIFF(soundbank_file)

        for i in range(len(riff.children) - 2):
            chunk = riff.children[i + 2]

            # read the file into a FSB5 object
            chunk.seek(0)
            chunk.seek(0x20 - chunk.offset % 0x20)
            fsb = fsb5.FSB5(chunk.read())

            # from python-fsb5 repo ==
            # get the extension of samples based off the sound format specified in the header
            ext = fsb.get_sample_extension()
            if extract_extensions and ext not in extract_extensions:
                continue

            for sample in fsb.samples:
                logger.info(
                    "Extracting %s.%s (%sHz, %s channels, %s samples)",
                    sample.name,
                    ext,
                    sample.frequency,
                    sample.channels,
                    sample.samples,
                )
                try:
                    with (dest_path / ext / f"{sample.name}.{ext}").open(
                        "wb"
                    ) as out_file:
                        out_file.write(fsb.rebuild_sample(sample))
                except LibraryNotFoundException as err:
                    logger.error(
                        "Failed to extract files for extension %s: %s", ext, err
                    )
                    return

            logger.info("Extracted %s %s files from bank %s", len(fsb.samples), ext, i)


def main():
    parser = argparse.ArgumentParser(description="Extract Spelunky 2 soundbank.")
    parser.add_argument("soundbank", help="Path to soundbank.bank")

    args = parser.parse_args()
    logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.INFO)

    extract_soundbank(
        Path(args.soundbank),
        Path("sound"),
        extract_extensions=[Extension.WAV, Extension.OGG],
    )


if __name__ == "__main__":
    main()
