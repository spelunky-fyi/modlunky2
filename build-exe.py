# pylint: disable=invalid-name

import argparse
import subprocess
import os
from pathlib import Path

OPTIONAL_DATA = [
    "dist/libogg.dll;.",
    "dist/libvorbis.dll;.",
    "dist/s99-client.exe;.",
]
DATA = [
    "src/modlunky2/VERSION;.",
    "src/modlunky2/static;static",
]
BASE_DIR = Path(__file__).parent.resolve()

DEBUG_DIR = Path("src/launcher/target/debug")
RELEASE_DIR = Path("src/launcher/target/release")
EXE_NAME = Path("modlunky2.exe")


def run_pyinstaller(debug):
    pyinstaller_args = ["pyinstaller.exe", f"{BASE_DIR / 'pyinstaller-cli.py'}"]

    for data in DATA:
        pyinstaller_args.extend(["--add-data", data])

    for data in OPTIONAL_DATA:
        src, _, _ = data.partition(";")
        if Path(src).exists():
            pyinstaller_args.extend(["--add-data", data])

    pyinstaller_args.extend(
        [
            "--name=modlunky2",
            f"--icon={BASE_DIR / 'src/modlunky2/static/images/icon.ico'}",
            "--clean",
            "--onedir",
            "--noconfirm",
        ]
    )

    if not debug:
        pyinstaller_args.append("--noconsole")

    subprocess.check_call(pyinstaller_args)


def build_launcher(debug):
    args = [
        "cargo",
        "build",
        f"--manifest-path={BASE_DIR / 'src/launcher/Cargo.toml'}",
    ]

    if not debug:
        args.append("--release")

    subprocess.check_call(args)


def main():
    parser = argparse.ArgumentParser(description="Build modlunky2 exe")
    parser.add_argument(
        "--debug", action="store_true", help="Whether to build debug exe."
    )
    args = parser.parse_args()
    run_pyinstaller(args.debug)
    build_launcher(args.debug)

    artifact_dir = RELEASE_DIR
    if args.debug:
        artifact_dir = DEBUG_DIR

    print(f"exe successfully built at {artifact_dir / EXE_NAME}")
    os.startfile(BASE_DIR / artifact_dir)


if __name__ == "__main__":
    main()
