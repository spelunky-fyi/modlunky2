import logging
import os
import shutil
import threading
from pathlib import Path

from flask import Blueprint, current_app, render_template, request

from modlunky2.assets.assets import AssetStore
from modlunky2.assets.constants import (EXTRACTED_DIR,
                                        OVERRIDES_DIR, FILEPATH_DIRS, PACKS_DIR)
from modlunky2.assets.exc import MissingAsset
from modlunky2.assets.patcher import Patcher

blueprint = Blueprint("assets", __name__)


MODS = Path("Mods")

TOP_LEVEL_DIRS = [
    EXTRACTED_DIR,
    PACKS_DIR,
    OVERRIDES_DIR
]

def get_overrides(install_dir):
    dir_ = install_dir / MODS / OVERRIDES_DIR

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
    mods_dir = install_dir / MODS

    for dir_ in TOP_LEVEL_DIRS:
        (mods_dir / dir_).mkdir(parents=True, exist_ok=True)

    for dir_ in FILEPATH_DIRS:
        (mods_dir / EXTRACTED_DIR / dir_).mkdir(parents=True, exist_ok=True)
        (mods_dir / ".compressed" / EXTRACTED_DIR / dir_).mkdir(parents=True, exist_ok=True)

    with exe_filename.open("rb") as exe:
        asset_store = AssetStore.load_from_file(exe)
        unextracted = asset_store.extract(
            mods_dir / EXTRACTED_DIR,
            mods_dir / ".compressed" / EXTRACTED_DIR,
        )

    for asset in unextracted:
        logging.warning("Un-extracted Asset %s", asset)

    dest = mods_dir / EXTRACTED_DIR / "Spel2.exe"
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
            asset_store.repackage(
                search_dirs,
                extract_dir,
                mods_dir / ".compressed",
            )
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

    source_exe = current_app.config.SPELUNKY_INSTALL_DIR / MODS/ EXTRACTED_DIR / "Spel2.exe"
    dest_exe = current_app.config.SPELUNKY_INSTALL_DIR / "Spel2.exe"
    mods_dir = current_app.config.SPELUNKY_INSTALL_DIR / MODS

    search_dirs = [mods_dir / "Overrides"]
    extract_dir = mods_dir / "Extracted"

    thread = threading.Thread(
        target=repack_assets, args=(mods_dir, search_dirs, extract_dir, source_exe, dest_exe)
    )
    thread.start()

    return render_template("assets_repack.html", exe=dest_exe)
