from modlunky2.config import CACHE_DIR, DATA_DIR

PLAYLUNKY_RELEASES_URL = "https://api.github.com/repos/spelunky-fyi/Playlunky/releases"
PLAYLUNKY_RELEASES_PATH = CACHE_DIR / "playlunky-releases.json"
PLAYLUNKY_DATA_DIR = DATA_DIR / "playlunky"

SPEL2_DLL = "spel2.dll"
PLAYLUNKY_DLL = "playlunky64.dll"
PLAYLUNKY_EXE = "playlunky_launcher.exe"
PLAYLUNKY_FILES = [SPEL2_DLL, PLAYLUNKY_DLL, PLAYLUNKY_EXE]
PLAYLUNKY_VERSION_FILENAME = "playlunky.version"
