import argparse
import logging
import shutil
import sys
from pathlib import Path

from .assets import AssetStore
from .constants import DEFAULT_COMPRESSION_LEVEL, EXTRACTED_DIR, OVERRIDES_DIR
from .exc import MissingAsset
from .patcher import Patcher

DEFAULT_MODS_DIR = "Mods"


def main():
    parser = argparse.ArgumentParser(description="Extract Spelunky 2 Assets.")

    parser.add_argument(
        "--mods-dir",
        type=str,
        default=DEFAULT_MODS_DIR,
        help="Path to directory containing mods.",
    )
    parser.add_argument(
        "--pack-dir",
        action="append",
        default=[],
        help="Path to directory of mod pack to pack. Can be passed multiple times.",
    )
    parser.add_argument(
        "--compression-level",
        type=int,
        default=DEFAULT_COMPRESSION_LEVEL,
        help=(
            " Value between 1 and 22 (higher = smaller data size)"
            " - if modified assets are too large, increase compression"
        ),
    )
    parser.add_argument(
        "source",
        type=argparse.FileType("rb"),
        help="Path to original Spel2.exe. This should be used as a source and not ever patched.",
    )
    parser.add_argument(
        "dest",
        type=str,
        default="Spel2-modded.exe",
        help="Path where patched binary will be created.",
    )
    args = parser.parse_args()
    dest = Path(args.dest)
    mods_dir = Path(args.mods_dir)

    logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.INFO)

    if dest.exists():
        answer = input(
            f"File {dest} already exists. Would you like to overwrite it? [y/N]: "
        )
        if answer.lower() not in ("y", "yes"):
            print("Exiting...")
            sys.exit(0)

    print(f"Making copy of {args.source.name} to {dest}")
    shutil.copy2(args.source.name, dest)

    search_dirs = []
    for search_dir in args.pack_dir:
        search_dirs.append(search_dir)
    search_dirs.append(OVERRIDES_DIR)

    with dest.open("rb+") as dest_file:
        asset_store = AssetStore.load_from_file(dest_file)
        try:
            asset_store.repackage(
                search_dirs,
                mods_dir / EXTRACTED_DIR,
                mods_dir / ".compressed",
                args.compression_level,
            )
        except MissingAsset as err:
            print("")
            print(f"Failed to find expected asset: {err}. Unabled to proceed...")
            print("Have you run modlunky2-asset-extract in this directory?")
            print("")
            sys.exit(1)

        patcher = Patcher(dest_file)
        patcher.patch_checksum()
        patcher.patch_release()


if __name__ == "__main__":
    main()
