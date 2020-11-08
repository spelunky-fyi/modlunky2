from pathlib import Path
import sys
import logging
import threading
import binascii
import shutil
import os

from flask import Blueprint, current_app, Response, redirect, render_template, request

from s2_data.assets.assets import KNOWN_ASSETS, AssetStore, EXTRACTED_DIR, OVERRIDES_DIR, MissingAsset
from s2_data.assets.patcher import Patcher  
from modlunky2.code_execution import CodeExecutionManager, ProcessNotRunning

blueprint = Blueprint("assets", __name__)


ASSETS_ROOT = Path("Mods")
EXTRACTED_DIR = ASSETS_ROOT / EXTRACTED_DIR
OVERRIDES_DIR = ASSETS_ROOT / OVERRIDES_DIR
ASSET_DIRS = [
    "Data/Fonts",
    "Data/Levels/Arena",
    "Data/Textures/OldTextures"
]


def get_overrides():
    dir_ = current_app.config.SPELUNKY_INSTALL_DIR / OVERRIDES_DIR

    if not dir_.exists():
        return None

    overrides = []
    for root, dirs, files in os.walk(dir_, topdown=True):
        dirs[:] = [d for d in dirs if d not in [".compressed"]]

        for file_ in files:
            overrides.append(Path(root) / file_)

    return overrides


@blueprint.route('/')
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
    overrides = get_overrides()

    return render_template("assets.html", exes=exes, overrides=overrides)


def extract_assets(exe_filename):
    # Make all directories for extraction and overrides
    for dir_ in ASSET_DIRS:
        (current_app.config.SPELUNKY_INSTALL_DIR / EXTRACTED_DIR / dir_).mkdir(parents=True, exist_ok=True)
        (current_app.config.SPELUNKY_INSTALL_DIR / EXTRACTED_DIR / ".compressed" / dir_).mkdir(parents=True, exist_ok=True)
        (current_app.config.SPELUNKY_INSTALL_DIR / OVERRIDES_DIR / dir_).mkdir(parents=True, exist_ok=True)
        (current_app.config.SPELUNKY_INSTALL_DIR / OVERRIDES_DIR / ".compressed" / dir_).mkdir(parents=True, exist_ok=True)

    with exe_filename.open('rb') as exe:
        asset_store = AssetStore.load_from_file(exe)
        seen = {}
        for filename in KNOWN_ASSETS:
            asset = asset_store.find_asset(filename)
            name_hash = asset_store.filename_hash(filename)
            if asset is None:
                logging.info("Asset %s not found with hash %s...",
                    filename.decode(),
                    repr(binascii.hexlify(name_hash))
                )
                continue

            asset.filename = filename
            seen[asset.name_hash] = asset

            filepath = Path(filename.decode())
            logging.info("Extracting %s.. ", filepath)
            asset.extract(current_app.config.SPELUNKY_INSTALL_DIR / EXTRACTED_DIR, exe, asset_store.key)

    for asset in sorted(asset_store.assets, key=lambda a: a.offset):
        name_hash = asset_store.filename_hash(asset.filename)
        if asset.name_hash not in seen:
            logging.warning("Un-extracted Asset %s. Things might not work. :X", asset)

    dest = current_app.config.SPELUNKY_INSTALL_DIR / EXTRACTED_DIR / "Spel2.exe"
    logging.info("Backing up exe to %s", dest)
    shutil.copy2(exe_filename, dest)

    logging.info("Extraction complete!")


@blueprint.route('/extract/', methods=["POST"])
def assets_extract():

    exe = current_app.config.SPELUNKY_INSTALL_DIR / request.form['extract-target']
    thread = threading.Thread(target=extract_assets, args=(exe,))
    thread.start()    

    return render_template("assets_extract.html", exe=exe)


def repack_assets(source_exe, dest_exe):
    shutil.copy2(source_exe, dest_exe)

    mods_dir = current_app.config.SPELUNKY_INSTALL_DIR / ASSETS_ROOT
    with dest_exe.open("rb+") as dest_file:
        asset_store = AssetStore.load_from_file(dest_file)
        try:
            asset_store.repackage(Path(mods_dir))
        except MissingAsset as err:
            logging.error("Failed to find expected asset: %s. Unabled to proceed...", err)
            return

        patcher = Patcher(dest_file)
        patcher.patch()
    logging.info("Repacking complete!")


@blueprint.route('/repack/', methods=["POST"])
def assets_repack():

    source_exe = current_app.config.SPELUNKY_INSTALL_DIR / EXTRACTED_DIR / "Spel2.exe"
    dest_exe = current_app.config.SPELUNKY_INSTALL_DIR / "Spel2.exe"

    thread = threading.Thread(target=repack_assets, args=(source_exe, dest_exe))
    thread.start()    

    return render_template("assets_repack.html", exe=dest_exe)