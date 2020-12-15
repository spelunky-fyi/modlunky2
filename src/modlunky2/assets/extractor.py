import argparse
import logging
from pathlib import Path

from .assets import AssetStore
from .constants import (
    DEFAULT_COMPRESSION_LEVEL,
    EXTRACTED_DIR,
    FILEPATH_DIRS,
    OVERRIDES_DIR,
    PACKS_DIR,
)

DEFAULT_MODS_DIR = "Mods"

TOP_LEVEL_DIRS = [EXTRACTED_DIR, PACKS_DIR, OVERRIDES_DIR]


def main():
    parser = argparse.ArgumentParser(description="Extract Spelunky 2 Assets.")
    parser.add_argument("exe", type=argparse.FileType("rb"), help="Path to Spel2.exe")
    parser.add_argument(
        "--mods-dir",
        type=str,
        default=DEFAULT_MODS_DIR,
        help="Path to directory containing mods. Default: %(default)s",
    )
    parser.add_argument(
        "--extracted-name",
        type=str,
        default=EXTRACTED_DIR,
        help="Name of the directory to extract files into. Default: %(default)s",
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
        "--no-recompress",
        dest="recompress",
        default=True,
        action="store_false",
        help=(
            "Don't recompress extracted assets. Increases extract time "
            "but packing will be slower."
        ),
    )
    parser.add_argument(
        "--no-mkdirs",
        dest="mkdirs",
        default=True,
        action="store_false",
        help="Don't make directories for Mods.",
    )

    args = parser.parse_args()

    mods_dir = Path(args.mods_dir)
    extracted_dir = Path(args.extracted_name)

    logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.INFO)

    if args.mkdirs:
        # Make all directories for extraction and overrides
        for dir_ in TOP_LEVEL_DIRS:
            (mods_dir / dir_).mkdir(parents=True, exist_ok=True)

        for dir_ in FILEPATH_DIRS:
            (mods_dir / extracted_dir / dir_).mkdir(parents=True, exist_ok=True)
            (mods_dir / ".compressed" / extracted_dir / dir_).mkdir(
                parents=True, exist_ok=True
            )

    asset_store = AssetStore.load_from_file(args.exe)
    unextracted = asset_store.extract(
        mods_dir / extracted_dir,
        mods_dir / ".compressed" / extracted_dir,
        args.compression_level,
        recompress=args.recompress,
    )

    for asset in unextracted:
        logging.warning("Un-extracted Asset %s", asset)


if __name__ == "__main__":
    main()
