import hashlib
import logging
import os
from collections import defaultdict
from concurrent.futures import wait
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from struct import pack, unpack

import zstandard as zstd
from PIL import Image

from modlunky2.assets.constants import KNOWN_TEXTURES_V1
from modlunky2.assets.exc import NonSiblingAsset

from .chacha import Key, chacha, hash_filepath
from .constants import (BANK_ALIGNMENT, DEFAULT_COMPRESSION_LEVEL,
                        FILENAMES_TO_FILEPATHS, KNOWN_FILEPATHS,
                        PNG_NAMES_TO_DDS_NAMES, DDS_PNGS)
from .converters import dds_to_png, png_to_dds, rgba_to_png
from .exc import FileConflict, MissingAsset, MultipleMatchingAssets

logger = logging.getLogger("modlunky2")


@dataclass
class ExeAssetBlock:
    """ Represent a block of information about an asset in the exe."""

    # Position in the exe where asset is read from, or written to.
    offset: int

    # Size length of the filepath and filepath_hash
    filepath_len: int

    # The hash of the filepath
    filepath_hash: bytes

    # Whether the asset is encrypted and compressed.
    is_encrypted: bool

    # Position into the exe where the data itself
    # is read fromo, or written to.
    asset_offset: int

    # The size of the asset itself.
    asset_len: int

    @property
    def data_len(self):
        # The size of the full data portion (asset + encrypted bytes)
        return self.asset_len + 1

    @property
    def total_size(self):
        return (
            8  # 8 bytes for header (asset_len, filepath_len)
            + self.filepath_len  # The size of the filepath
            + 1  # The byte for whether the asset is encrypted
            + self.asset_len  # The size of the asset
        )

    @classmethod
    def from_exe_handle(cls, exe_handle):
        """From an exe file handle, construct an AssetInfo object.

        The exe handle should already be seeked to the appropriate position to
        begin reading.

        Returns None if there is no more assets as the current offset.
        """
        offset = exe_handle.tell()
        data_len, filepath_len = unpack(b"<II", exe_handle.read(8))

        if (data_len, filepath_len) == (0, 0):
            return

        if data_len <= 0:
            raise RuntimeError(f"Expected data length > 0, found {data_len}")

        filepath_hash = exe_handle.read(filepath_len)
        is_encrypted = exe_handle.read(1) == b"\x01"
        asset_offset = exe_handle.tell()
        asset_len = data_len - 1

        exe_handle.seek(asset_len, 1)

        return ExeAssetBlock(
            offset=offset,
            filepath_len=filepath_len,
            filepath_hash=filepath_hash,
            is_encrypted=is_encrypted,
            asset_offset=asset_offset,
            asset_len=asset_len,
        )

    def read_data(self, exe_handle):
        exe_handle.seek(self.asset_offset)
        return exe_handle.read(self.asset_len)

    def write_data(self, exe_handle, data):
        if self.asset_len != len(data):
            raise RuntimeError(
                f"Data passed was size {len(data)}, expected {self.asset_len}"
            )

        exe_handle.write(pack("<II", self.data_len, self.filepath_len))
        exe_handle.write(self.filepath_hash)
        exe_handle.write(pack("<b", self.is_encrypted))
        exe_handle.write(data)


class ExeAsset:
    def __init__(self, asset_block, filepath):
        self.asset_block = asset_block
        self.filepath = filepath
        self.data = None
        self.disk_asset = None

    def match_hash(self, hash_):
        min_len = min(len(hash_), self.asset_block.filepath_len)
        return hash_[:min_len] == self.asset_block.filepath_hash[:min_len]

    def load_data(self, handle):
        """ Cache data on the asset. Must be called before extraction."""
        handle.seek(self.asset_block.asset_offset)
        self.data = handle.read(self.asset_block.asset_len)

    def extract(
        self,
        extract_dir: Path,
        compressed_dir: Path,
        key: Key,
        compression_level=DEFAULT_COMPRESSION_LEVEL,
        recompress=True,
    ):
        if not self.filepath:
            raise RuntimeError("Asset doesn't have filepath.")

        if self.data is None:
            raise RuntimeError("load_data hasn't been called.")

        filepath = extract_dir / self.filepath

        compressed_filepath = compressed_dir / f"{self.filepath}.zst"
        md5sum_filepath = compressed_dir / f"{self.filepath}.md5sum"

        if self.asset_block.is_encrypted:
            try:
                # Decrypt
                self.data = chacha(self.filepath.encode(), self.data, key)

                # Decompress
                cctx = zstd.ZstdDecompressor()
                self.data = cctx.decompress(self.data)

                if recompress:
                    # Recompress at higher compression level to give
                    # better chance of assets fitting in binary
                    logger.info("Storing compressed asset %s...", compressed_filepath)
                    with compressed_filepath.open("wb") as compressed_file:
                        cctx = zstd.ZstdCompressor(level=compression_level)
                        compressed_data = cctx.compress(self.data)
                        compressed_file.write(compressed_data)

            except Exception:  # pylint: disable=broad-except
                logger.exception("Failed compression")
                return None

        if self.filepath in KNOWN_TEXTURES_V1:
            self.data = rgba_to_png(self.data)
        elif self.filepath in DDS_PNGS:
            self.data = dds_to_png(self.data)

        if recompress:
            # Get a hash of the the uncompressed file to be used
            # to detect if the source file changed
            md5sum = hashlib.md5(self.data).hexdigest()
            with md5sum_filepath.open("w") as md5sum_file:
                md5sum_file.write(md5sum)

        logger.info("Storing asset %s...", filepath)
        if self.filepath in DDS_PNGS:
            filepath = filepath.with_suffix(".png")

        with filepath.open("wb") as asset_file:
            asset_file.write(self.data)


class AssetStore:
    """ Represents a bundle of asset blocks read from, or to be packed into, an exe."""

    BUNDLE_OFFSET = 0x400

    def __init__(self, exe_handle):
        self.assets = []
        self.exe_handle = exe_handle
        self.total_size = 0
        self._key = Key()

    @property
    def key(self):
        return self._key.key

    def update_key(self, size):
        self._key.update(size)

    @classmethod
    def load_from_file(cls, exe_handle):
        asset_store = cls(exe_handle)
        asset_store.exe_handle.seek(cls.BUNDLE_OFFSET)

        while True:
            asset_block = ExeAssetBlock.from_exe_handle(exe_handle)

            if asset_block is None:
                # We've reached the end of the asset blocks.
                break

            asset_store.update_key(asset_block.data_len)
            asset_store.total_size += asset_block.total_size
            asset_store.assets.append(ExeAsset(asset_block, None))

        asset_store.populate_asset_filepaths()
        return asset_store

    def find_asset(self, filepath):
        if filepath is None:
            return None
        filepath_hash = self.hash_filepath(filepath)
        for asset in self.assets:
            if asset.match_hash(filepath_hash):
                return asset
        return None

    def hash_filepath(self, filepath):
        if filepath is None:
            return None

        if not isinstance(filepath, bytes):
            filepath = filepath.encode()

        return hash_filepath(filepath, self.key)

    def populate_asset_filepaths(self):
        for filepath in KNOWN_FILEPATHS:
            asset = self.find_asset(filepath)
            if asset is None:
                continue
            asset.filepath = filepath

    @staticmethod
    def _extract_single(asset, *args, **kwargs):
        try:
            logger.info("Extracting %s... ", asset.filepath)
            asset.extract(*args, **kwargs)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed Extraction")

    def extract(
        self,
        extract_dir,
        compressed_dir,
        compression_level=DEFAULT_COMPRESSION_LEVEL,
        max_workers=max(os.cpu_count() - 2, 1),
        recompress=True,
    ):
        unextracted = []
        for asset in self.assets:
            if asset.filepath is None:
                # No known filepaths matched this asset.
                unextracted.append(asset)
                continue

            asset.load_data(self.exe_handle)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(
                    self._extract_single,
                    asset,
                    extract_dir,
                    compressed_dir,
                    self.key,
                    compression_level,
                    recompress,
                )
                for asset in self.assets
                if asset.filepath
            ]
            wait(futures, timeout=300)

        return unextracted

    def pack_assets(self):
        self.exe_handle.seek(self.BUNDLE_OFFSET)

        for asset in self.assets:
            if asset.filepath is None:
                continue

            assert asset.asset_block.asset_len == asset.disk_asset.get_asset_len()
            data = asset.disk_asset.get_asset_data()

            if asset.asset_block.is_encrypted:
                logger.info("Encrypting file %s", asset.disk_asset.asset_path)
                data = chacha(asset.filepath.encode(), data, self.key)

            logger.info("Packing file %s", asset.disk_asset.asset_path)
            self.exe_handle.write(
                pack("<II", asset.asset_block.data_len, asset.asset_block.filepath_len)
            )
            self.exe_handle.write(asset.asset_block.filepath_hash)
            self.exe_handle.write(pack("<b", asset.asset_block.is_encrypted))
            self.exe_handle.write(data)

        self.exe_handle.write(pack("<II", 0, 0))

    def recalculate_key(self):
        """ Recalculate the key from the current assets."""
        new_key = Key()
        for asset in self.assets:
            if asset.filepath is None:
                continue
            new_key.update(asset.asset_block.data_len)
        self._key = new_key

    def update_filepath_hashes(self):
        for asset in self.assets:
            if asset.filepath is None:
                continue
            asset.asset_block.filepath_hash = self.hash_filepath(asset.filepath).ljust(
                asset.asset_block.filepath_len, b"\x00"
            )

    def repackage(
        self,
        search_dirs,
        fallback_dir,
        compressed_dir,
        compression_level=DEFAULT_COMPRESSION_LEVEL,
    ):
        disk_bundle = DiskBundle.from_dirs(
            self.assets,
            search_dirs,
            fallback_dir,
            compressed_dir,
        )
        disk_bundle.compress_if_needed(compression_level=compression_level)

        offset = self.BUNDLE_OFFSET
        for asset in self.assets:
            if asset.filepath is None:
                continue
            disk_asset = disk_bundle.get(str(Path(asset.filepath).name))
            if disk_asset is None:
                raise MissingAsset(f"FAIL {asset.filepath}")

            asset.disk_asset = disk_asset

            asset.asset_block.offset = offset
            asset.asset_block.asset_len = disk_asset.get_asset_len()
            asset.asset_block.asset_offset = (
                asset.asset_block.offset + 8 + asset.asset_block.filepath_len + 1
            )

            # The name hash of soundbank files is padded such that the asset_offset
            # is divisible by 32.
            #
            # Padding is between 1 and 32 bytes
            if disk_asset.asset_path.suffix == ".bank":
                padding = (
                    BANK_ALIGNMENT - asset.asset_block.asset_offset % BANK_ALIGNMENT
                )
                asset.asset_block.filepath_len += padding
                asset.asset_block.asset_offset += padding

            offset += asset.asset_block.total_size

        self.recalculate_key()
        self.update_filepath_hashes()
        self.pack_assets()


class ResolutionPolicy(Enum):
    RaiseError = 1
    FirstWins = 2
    LastWins = 3


@dataclass
class DiskBundle:
    def __init__(self, disk_assets):
        self.disk_assets = disk_assets

    def get(self, filepath, default=None):
        return self.disk_assets.get(filepath, default)

    @staticmethod
    def get_files_from_search_dir(search_dir: Path):
        out_files = {}

        if not search_dir.exists():
            return out_files

        for root, dirs, files in os.walk(search_dir, topdown=True):
            # Remove compressed directories
            dirs[:] = [d for d in dirs if d not in [".compressed"]]

            for file_ in files:
                # For DDS_PNGS we need to convert to actual name to test
                # for validity of files
                real_name = PNG_NAMES_TO_DDS_NAMES.get(file_, file_)
                if real_name not in FILENAMES_TO_FILEPATHS:
                    continue

                if file_ in out_files:
                    raise MultipleMatchingAssets(
                        f"Found {file_} multiple times in {search_dir}"
                    )

                out_files[file_] = Path(root) / file_

        return out_files

    @classmethod
    def from_dirs(
        cls,
        exe_assets,
        search_dirs,
        fallback_dir,
        compressed_dir,
        resolution_policy=ResolutionPolicy.RaiseError,
    ):

        modfiles_by_filename = defaultdict(list)
        disk_assets = {}

        for search_dir in search_dirs:
            for file_, file_path in cls.get_files_from_search_dir(
                Path(search_dir)
            ).items():
                modfiles_by_filename[file_].append(file_path)

        for asset in exe_assets:
            if asset.filepath is None:
                continue
            filepath = Path(asset.filepath)
            if asset.filepath in DDS_PNGS:
                filepath = filepath.with_suffix(".png")
            modpack_files = modfiles_by_filename.get(filepath.name)

            # No modpacks overrode this asset. Get it from
            # fallback directory.
            if not modpack_files:
                asset_path = fallback_dir / filepath
                if not asset_path.exists():
                    raise MissingAsset(f"Didn't find an asset for {filepath}")

                disk_assets[str(Path(asset.filepath).name)] = DiskAsset(
                    asset_path, compressed_dir, asset
                )
                continue

            if (
                resolution_policy == ResolutionPolicy.RaiseError
                and len(modpack_files) >= 2
            ):
                raise FileConflict(
                    f"{filepath} found in multiple packs: {', '.join(map(str, modpack_files))}"
                )

            idx = 0
            if resolution_policy == ResolutionPolicy.FirstWins:
                idx = 0
            elif resolution_policy == ResolutionPolicy.LastWins:
                idx = -1

            asset_path = modpack_files[idx]
            disk_assets[str(Path(asset.filepath).name)] = DiskAsset(
                asset_path, compressed_dir, asset
            )

        return cls(disk_assets)

    def compress_if_needed(
        self,
        compression_level=DEFAULT_COMPRESSION_LEVEL,
        max_workers=max(os.cpu_count() - 2, 1),
    ):
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(disk_asset.compress, compression_level)
                for disk_asset in self.disk_assets.values()
                if disk_asset.needs_compression()
            ]
            wait(futures, timeout=300)


@dataclass
class DiskAsset:
    # Path to the asset on disk
    asset_path: Path

    # Root directory where compression files are stored
    compressed_dir: Path

    exe_asset: ExeAsset

    def __post_init__(self):
        # assets cannot live higher than the compressed dir
        # to avoid complicating the caching structure. This
        # code ensures the asset_path is a sibling or a child
        # of a sibling. This also normalized the path, removing
        # and `..`'s.
        root = self.compressed_dir.resolve().parent
        try:
            self.rel_asset_path = self.asset_path.resolve().relative_to(root)
            # This is needed to clean up and `.`/`..`'s
            self.asset_path = root / self.rel_asset_path
        except ValueError as err:
            raise NonSiblingAsset(
                f"Disk Asset ({self.asset_path}) not sibling of ({self.compressed_dir})."
            ) from err

    def md5sum_of_asset(self):
        with self.asset_path.open("rb") as file_:
            md5sum = hashlib.md5()
            chunk = file_.read(8192)
            while chunk:
                md5sum.update(chunk)
                chunk = file_.read(8192)
            return md5sum.hexdigest().encode()

    @property
    def real_suffix(self):
        if self.exe_asset.filepath in DDS_PNGS:
            return ".DDS"
        return Path(self.exe_asset.filepath).suffix

    @property
    def compressed_path(self):
        return (
            self.compressed_dir
            / f"{self.rel_asset_path.with_suffix(self.real_suffix)}.zst"
        )

    @property
    def md5sum_path(self):
        return (
            self.compressed_dir
            / f"{self.rel_asset_path.with_suffix(self.real_suffix)}.md5sum"
        )

    def needs_compression(self):
        if not self.exe_asset.asset_block.is_encrypted:
            return False

        if not self.md5sum_path.exists():
            return True

        if not self.compressed_path.exists():
            return True

        md5sum = self.md5sum_of_asset()
        with self.md5sum_path.open("rb") as md5sum_file:
            stored_md5sum = md5sum_file.read().strip()
        if md5sum != stored_md5sum:
            return True

        return False

    def compress(self, compression_level=DEFAULT_COMPRESSION_LEVEL):
        if not self.exe_asset.asset_block.is_encrypted:
            return

        self.compressed_path.parent.mkdir(parents=True, exist_ok=True)
        self.md5sum_path.parent.mkdir(parents=True, exist_ok=True)

        if self.asset_path.suffix == ".png":
            logger.info('Converting image "%s" to DDS', self.asset_path)
            with Image.open(self.asset_path) as img:
                data = png_to_dds(img)
        else:
            with open(self.asset_path, "rb") as asset_file:
                data = asset_file.read()

        md5sum = self.md5sum_of_asset()
        with self.md5sum_path.open("wb") as md5sum_file:
            md5sum_file.write(md5sum)

        logger.info("Compressing %s...", self.asset_path)
        cctx = zstd.ZstdCompressor(level=compression_level)
        data = cctx.compress(data)
        with open(self.compressed_path, "wb") as compressed_file:
            compressed_file.write(data)

    def get_asset_len(self):
        if self.exe_asset.asset_block.is_encrypted:
            path = self.compressed_path
        else:
            path = self.asset_path
        return path.stat().st_size

    def get_asset_data(self):
        if self.exe_asset.asset_block.is_encrypted:
            path = self.compressed_path
        else:
            path = self.asset_path

        with path.open("rb") as file_:
            return file_.read()
