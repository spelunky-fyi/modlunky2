import subprocess
from pathlib import Path

DATA = [
    "dist/libogg.dll;.",
    "dist/libogg.dll;.",
    "src/modlunky2/VERSION;.",
    "src/modlunky2/static;static",
]
BASE_DIR = Path(__file__).parent.resolve()

def run_pyinstaller():
    pyinstaller_args = ["pyinstaller.exe", f"{BASE_DIR / 'pyinstaller-cli.py'}"]
    for data in DATA:
        pyinstaller_args.extend(["--add-data", data])

    pyinstaller_args.extend([
        "--name=modlunky2",
        f"--icon={BASE_DIR / 'src/modlunky2/static/images/icon.ico'}",
        "--clean",
        "--onedir",
        "--noconsole",
        "--noconfirm",
    ])

    process = subprocess.Popen(pyinstaller_args)
    process.communicate()


def build_launcher():
    process = subprocess.Popen([
        "cargo",
        "build",
        f"--manifest-path={BASE_DIR / 'src/launcher/Cargo.toml'}",
        "--release",
    ])
    process.communicate()


def main():
    run_pyinstaller()
    build_launcher()


if __name__ == "__main__":
    main()
