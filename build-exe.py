import subprocess
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


def run_pyinstaller():
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
            "--noconsole",
            "--noconfirm",
        ]
    )

    subprocess.check_call(pyinstaller_args)


def build_launcher():
    subprocess.check_call(
        [
            "cargo",
            "build",
            f"--manifest-path={BASE_DIR / 'src/launcher/Cargo.toml'}",
            "--release",
        ]
    )


def main():
    run_pyinstaller()
    build_launcher()


if __name__ == "__main__":
    main()
