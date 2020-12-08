import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR
ROOT_DIR = BASE_DIR.parent.parent

# Setup static files to work with onefile exe
if hasattr(sys, "_MEIPASS"):
    BASE_DIR = BASE_DIR / getattr(sys, "_MEIPASS")
    APP_DIR = Path(sys.executable).resolve().parent
    ROOT_DIR = BASE_DIR
