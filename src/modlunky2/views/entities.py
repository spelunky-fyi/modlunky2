import logging

from flask import Blueprint, current_app, redirect, render_template, request

from modlunky2.code_execution import ProcessNotRunning

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
