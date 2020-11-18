import binascii
import logging
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

from flask import Blueprint, current_app, render_template, request
from s2_data.assets.assets import (EXTRACTED_DIR, KNOWN_ASSETS, OVERRIDES_DIR,
                                   AssetStore, MissingAsset)
from s2_data.assets.patcher import Patcher

blueprint = Blueprint("assets", __name__)


ASSETS_ROOT = Path("Mods")
EXTRACTED_DIR = ASSETS_ROOT / EXTRACTED_DIR
OVERRIDES_DIR = ASSETS_ROOT / OVERRIDES_DIR
ASSET_DIRS = ["Data/Fonts", "Data/Levels/Arena", "Data/Textures/OldTextures"]


def get_overrides(install_dir):
    dir_ = install_dir / OVERRIDES_DIR

    if not dir_.exists():
        return None

    overrides = []
    for root, dirs, files in os.walk(dir_, topdown=True):
        dirs[:] = [d for d in dirs if d not in [".compressed"]]

        for file_ in files:
            overrides.append(Path(root) / file_)

    return overrides


@blueprint.route("/")
def assets():
    exes = []
    # Don't recurse forever. 3 levels should be enough
    exes.extend(current_app.config.SPELUNKY_INSTALL_DIR.glob("*.exe"))
    exes.extend(current_app.config.SPELUNKY_INSTALL_DIR.glob("*/*.exe"))
    exes.extend(current_app.config.SPELUNKY_INSTALL_DIR.glob("*/*/*.exe"))
    exes = [
        exe.relative_to(current_app.config.SPELUNKY_INSTALL_DIR)
        for exe in exes
        if exe.name not in ["modlunky2.exe"]
    ]
    overrides = get_overrides(current_app.config.SPELUNKY_INSTALL_DIR)

    return render_template("assets.html", exes=exes, overrides=overrides)


def extract_assets(install_dir, exe_filename):
    # Make all directories for extraction and overrides
    (install_dir / "Mods" / "Packs").mkdir(parents=True, exist_ok=True)
    (install_dir / "Mods" / "Overrides").mkdir(parents=True, exist_ok=True)
    for dir_ in ASSET_DIRS:
        (install_dir / EXTRACTED_DIR / dir_).mkdir(parents=True, exist_ok=True)
        (install_dir / "Mods" / ".compressed" / "Extracted" / dir_).mkdir(parents=True, exist_ok=True)


    with exe_filename.open("rb") as exe:
        asset_store = AssetStore.load_from_file(exe)
        seen = {}
        for filename in KNOWN_ASSETS:
            asset = asset_store.find_asset(filename)
            name_hash = asset_store.filename_hash(filename)
            if asset is None:
                logging.info(
                    "Asset %s not found with hash %s...",
                    filename.decode(),
                    repr(binascii.hexlify(name_hash)),
                )
                continue

            asset.filename = filename
            seen[asset.name_hash] = asset

            filepath = Path(filename.decode())
            logging.info("Extracting %s.. ", filepath)
            asset.load_data(exe)

        def extract_single(asset):
            try:
                logging.info("Extracting %s... ", asset.filename.decode())
                asset.extract(install_dir / "Mods", "Extracted", asset_store.key)
            except Exception as err:  # pylint: disable=broad-except
                logging.error(err)

        pool = ThreadPoolExecutor()
        futures = [pool.submit(extract_single, asset) for asset in seen.values()]
        wait(futures, timeout=300)

    for asset in sorted(asset_store.assets, key=lambda a: a.offset):
        name_hash = asset_store.filename_hash(asset.filename)
        if asset.name_hash not in seen:
            logging.warning("Un-extracted Asset %s. Things might not work. :X", asset)

    dest = install_dir / EXTRACTED_DIR / "Spel2.exe"
    if exe_filename != dest:
        logging.info("Backing up exe to %s", dest)
        shutil.copy2(exe_filename, dest)

    logging.info("Extraction complete!")


@blueprint.route("/extract/", methods=["POST"])
def assets_extract():

    exe = current_app.config.SPELUNKY_INSTALL_DIR / request.form["extract-target"]
    thread = threading.Thread(
        target=extract_assets, args=(current_app.config.SPELUNKY_INSTALL_DIR, exe)
    )
    thread.start()

    return render_template("assets_extract.html", exe=exe)


def repack_assets(mods_dir, search_dirs, extract_dir, source_exe, dest_exe):
    shutil.copy2(source_exe, dest_exe)

    with dest_exe.open("rb+") as dest_file:
        asset_store = AssetStore.load_from_file(dest_file)
        try:
            asset_store.repackage(Path(mods_dir), search_dirs, extract_dir)
        except MissingAsset as err:
            logging.error(
                "Failed to find expected asset: %s. Unabled to proceed...", err
            )
            return

        patcher = Patcher(dest_file)
        patcher.patch()
    logging.info("Repacking complete!")


@blueprint.route("/repack/", methods=["POST"])
def assets_repack():

    source_exe = current_app.config.SPELUNKY_INSTALL_DIR / EXTRACTED_DIR / "Spel2.exe"
    dest_exe = current_app.config.SPELUNKY_INSTALL_DIR / "Spel2.exe"
    mods_dir = current_app.config.SPELUNKY_INSTALL_DIR / ASSETS_ROOT

    search_dirs = ["Overrides"]
    extract_dir = "Extracted"

    thread = threading.Thread(
        target=repack_assets, args=(mods_dir, search_dirs, extract_dir, source_exe, dest_exe)
    )
    thread.start()

    return render_template("assets_repack.html", exe=dest_exe)
