import argparse
import logging
import sys
import threading
from pathlib import Path

import requests
from flask import Flask
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from packaging import version
from PIL import Image, ImageTk

from .constants import APP_DIR, BASE_DIR, ROOT_DIR
from .native import NativeUI
from .views.assets import blueprint as assets_blueprint
from .views.assets import ws_blueprint as assets_ws_blueprint
from .views.index import blueprint as index_blueprint

app = Flask(
    __name__,
    static_folder=f"{BASE_DIR / 'static'}",
    template_folder=f"{BASE_DIR / 'templates'}",
)
sockets = Sockets(app)

app.register_blueprint(index_blueprint)
app.register_blueprint(assets_blueprint, url_prefix="/assets")
sockets.register_blueprint(assets_ws_blueprint, url_prefix="/ws/assets")


#WebSocketHandler.log_request = lambda _: None


def get_latest_version():
    try:
        return version.parse(
            requests.get(
                "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest"
            ).json()["tag_name"]
        )
    except Exception:  # pylint: disable=broad-except
        return None


def get_current_version():
    with (ROOT_DIR / "VERSION").open() as version_file:
        return version.parse(version_file.read().strip())


def main():
    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="The host to listen on."
    )
    parser.add_argument("--port", type=int, default=8040, help="Port to listen on.")
    parser.add_argument("--debug", default=False, action="store_true")
    parser.add_argument(
        "--install-dir",
        default=APP_DIR,
        help="Path to Spelunky 2 installation. (Default: %(default)s",
    )
    args = parser.parse_args()

    log_format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")

    try:
        app.config.SPELUNKY_INSTALL_DIR = Path(args.install_dir)
        app.config.MODLUNKY_CURRENT_VERSION = get_current_version()
        app.config.MODLUNKY_LATEST_VERSION = get_latest_version()
        app.config.MODLUNKY_NEEDS_UPDATE = (
            app.config.MODLUNKY_CURRENT_VERSION < app.config.MODLUNKY_LATEST_VERSION
        )
        #folder_selected = filedialog.askdirectory()

        native_ui = NativeUI("http://localhost:8040/")

        def run_webserver():
            webserver = pywsgi.WSGIServer(
                (args.host, args.port), app,
                log=None,
                handler_class=WebSocketHandler,
            )
            native_ui.register_shutdown_handler(webserver.stop)
            webserver.serve_forever()
        webserver_thread = threading.Thread(target=run_webserver, daemon=True)
        webserver_thread.start()

        native_ui.mainloop()
    except Exception as err:  # pylint: disable=broad-except
        input(f"Failed to start ({err}). Press enter to exit... :(")
