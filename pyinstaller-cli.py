# Entry point for PyInstaller
# pyinstaller.exe .\pyinstaller-cli.py --name modlunky2 --onefile
from multiprocessing import freeze_support
from modlunky2.cli import main


if __name__ == "__main__":
    freeze_support()
    main()
