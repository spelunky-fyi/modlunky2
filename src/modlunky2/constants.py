import sys
from pathlib import Path

# The base directory where all source files exist
BASE_DIR = Path(__file__).resolve().parent

# The directory where the entry point is executed.
APP_DIR = BASE_DIR

# Is this program executed as an exe.
IS_EXE = False

# Setup static files to work with onefile exe
if hasattr(sys, "_MEIPASS"):
    # When extracted into a temp directory, the directory which is the base
    # to all files distributed with the exe.
    BASE_DIR = BASE_DIR / getattr(sys, "_MEIPASS")

    # The directory where the exe is executed from.
    APP_DIR = Path(sys.executable).resolve().parent

    # Is this program executed as an exe.
    IS_EXE = True
