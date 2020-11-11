import logging
import sys
from pathlib import Path
from packaging import version

from flask import Flask
import requests

from .code_execution import CodeExecutionManager
from .views.assets import blueprint as assets_blueprint
from .views.entities import blueprint as entities_blueprint
from .views.index import blueprint as index_blueprint

PROCESS_NAME = "Spel2.exe"
# Setup static files to work with onefile exe
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR
ROOT_DIR = BASE_DIR.parent.parent
if hasattr(sys, '_MEIPASS'):
    BASE_DIR = BASE_DIR / sys._MEIPASS
    APP_DIR = Path(sys.executable).resolve().parent
    ROOT_DIR = BASE_DIR


app = Flask(
    __name__,
    static_folder=f"{BASE_DIR / 'static'}",
    template_folder=f"{BASE_DIR / 'templates'}",
)
app.register_blueprint(index_blueprint)
app.register_blueprint(entities_blueprint, url_prefix="/entities")
app.register_blueprint(assets_blueprint, url_prefix="/assets")

def get_latest_version():
    try:
        return version.parse(requests.get(
            "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest"
        ).json()["tag_name"])
    except Exception:
        return None

def get_current_version():
    with (ROOT_DIR / "VERSION").open() as version_file:
        return version.parse(version_file.read().strip())


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument('--host', type=str, default='127.0.0.1', help='The host to listen on.')
    parser.add_argument('--port', type=int, default=8040, help='Port to listen on.')
    parser.add_argument('--debug', default=False, action="store_true")
    parser.add_argument(
        "--process-name", default=PROCESS_NAME,
        help="Name of Spelunky Process. (Default: %(default)s"
    )
    parser.add_argument(
        "--install-dir", default=APP_DIR,
        help="Path to Spelunky 2 installation. (Default: %(default)s"
    )
    args = parser.parse_args()

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    try:
        app.config.SPELUNKY_INSTALL_DIR = Path(args.install_dir)
        app.config.SPELUNKY_CEM = CodeExecutionManager(args.process_name)
        app.config.MODLUNKY_CURRENT_VERSION = get_current_version()
        app.config.MODLUNKY_LATEST_VERSION = get_latest_version()
        app.config.MODLUNKY_NEEDS_UPDATE = app.config.MODLUNKY_CURRENT_VERSION < app.config.MODLUNKY_LATEST_VERSION
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as err:
        input(f"Failed to start ({err}). Press enter to exit... :(")
