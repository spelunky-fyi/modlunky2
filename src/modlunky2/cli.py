import argparse
import logging
import sys
from pathlib import Path

import requests
from flask import Flask
from packaging import version

from .views.assets import blueprint as assets_blueprint
from .views.index import blueprint as index_blueprint

PROCESS_NAME = "Spel2.exe"
# Setup static files to work with onefile exe
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR
ROOT_DIR = BASE_DIR.parent.parent

##------------------------------------------------------------------------------ UI
import tkinter as tk
from tkinter import ttk
from tkinter import *
from PIL import ImageTk, Image

# intializing the window
window = tk.Tk()
window.title("Modlunky2")
# configuring the window
window.geometry('750x450')
window.minsize(750,450)
#window.resizable(False, False)
window.configure(bg='black')
#Create Tab Control
TAB_CONTROL = ttk.Notebook(window)

#Tab1 Setup ---------------------------------
TAB1 = ttk.Frame(TAB_CONTROL)
TAB_CONTROL.add(TAB1, text='Setup')
TAB1.columnconfigure(1, minsize=290,weight=1)
TAB1.columnconfigure(0, minsize=450)
TAB1.rowconfigure(1, minsize=275,weight=1)
TAB1.rowconfigure(2, minsize=60)
TAB1.rowconfigure(3, minsize=60)

labelSetup = ttk.Label(TAB1, text="Select your mods")
labelSetup.grid(row=0,column=0, pady = 5, padx = 5, sticky="nswe")

# Create a label radiobutton frame exe list which will only be visible in debug mode
radioGroupExes = ttk.LabelFrame(TAB1, text = "Select an exe")
radioGroupExes.grid(row=0,column=1, rowspan=2, pady = 5, padx = 5, sticky="nswe")

# Logo that normally goes where the radiobutton list of exes is
#img = ImageTk.PhotoImage(Image.open(str(APP_DIR) + "/ddmods.png"))
#panel = tk.Label(TAB1, image = img, width=285, height=285)
#panel.grid(row=0, column=1, rowspan=2, pady = 5, padx = 5, sticky="nswe")

buttonPack = tk.Button(TAB1, text="Repack")
buttonPack.grid(row=2, column=1, pady = 5, padx = 5, sticky="nswe")

buttonUnPack = tk.Button(TAB1, text="Unpack")
buttonUnPack.grid(row=3, column=1, pady = 5, padx = 5, sticky="nswe")

Lb1 = Listbox(TAB1)
Lb1.grid(row=1, column=0, rowspan=4, columnspan=1, sticky="nswe")
Lb1.insert(1, "Mod 1")
Lb1.insert(2, "Skin Mod thing")
Lb1.insert(3, "Woah a mod")
Lb1.insert(4, "lol mod")
Lb1.insert(5, "mod mod")
Lb1.insert(6, "Guy")

#Tab2 Characters -----------------------
TAB2 = ttk.Frame(TAB_CONTROL)
TAB_CONTROL.add(TAB2, text='Characters')

#Tab3 Asset Mangement
TAB3 = ttk.Frame(TAB_CONTROL)
TAB_CONTROL.add(TAB3, text='Assets')

#Tab4 Level Editor
TAB4 = ttk.Frame(TAB_CONTROL)
TAB_CONTROL.add(TAB4, text='Levels')
TAB_CONTROL.pack(expand=1, fill="both")

#Tab Name Labels
ttk.Label(TAB2, text="This is Tab 2").grid(column=0, row=0, padx=10, pady=10)

##---------------------------------------------------------------------------------- UI Loaded via end of the script

if hasattr(sys, "_MEIPASS"):
    BASE_DIR = BASE_DIR / getattr(sys, "_MEIPASS")
    APP_DIR = Path(sys.executable).resolve().parent
    ROOT_DIR = BASE_DIR


app = Flask(
    __name__,
    static_folder=f"{BASE_DIR / 'static'}",
    template_folder=f"{BASE_DIR / 'templates'}",
)
app.register_blueprint(index_blueprint)
app.register_blueprint(assets_blueprint, url_prefix="/assets")


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
        "--process-name",
        default=PROCESS_NAME,
        help="Name of Spelunky Process. (Default: %(default)s",
    )
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
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as err:  # pylint: disable=broad-except
        input(f"Failed to start ({err}). Press enter to exit... :(")

def get_exes(install_dir):
    exes = []
    # Don't recurse forever. 3 levels should be enough
    exes.extend(install_dir.glob("*.exe"))
    exes.extend(install_dir.glob("*/*.exe"))
    exes.extend(install_dir.glob("*/*/*.exe"))
    return [
        exe.relative_to(install_dir)
        for exe in exes
        if exe.name not in ["modlunky2.exe"]
    ]


#Calling Main()------------------------------------------------------------------ Loads Ui
import os

i=0
for spel in get_exes(APP_DIR):
    ttk.Radiobutton(radioGroupExes, text = spel.name).grid(row=i, column=0)
    i=i+1

window.mainloop() # ---------------------------------------------------------------------------------------------------------- UNcomment me
