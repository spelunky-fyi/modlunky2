from pathlib import Path
import sys
import logging
import threading
import binascii
import shutil
import os

from flask import Blueprint, current_app, Response, redirect, render_template, request

from s2_data.assets.assets import KNOWN_ASSETS, AssetStore, EXTRACTED_DIR, OVERRIDES_DIR, MissingAsset
from s2_data.assets.patcher import Patcher  
from modlunky2.code_execution import CodeExecutionManager, ProcessNotRunning

blueprint = Blueprint("entities", __name__)


@blueprint.route('/')
def entities():
    return render_template("entities.html")


@blueprint.route('/spawn', methods=["POST"])
def entities_spawn():
    entity_num = int(request.form['spawn-entity-number'])
    try:
        current_app.config.SPELUNKY_CEM.load_entity(entity_num)
    except ProcessNotRunning as err:
        logging.error("Failed to spawn entity. Process isn't running: %s", err)
    return redirect("/entities/")