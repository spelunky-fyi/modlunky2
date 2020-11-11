from dataclasses import dataclass
from typing import List

from flask import Blueprint, render_template

blueprint = Blueprint("index", __name__)


@dataclass
class Link:
    site: str
    link: str


@dataclass
class Person:
    name: str
    links: List[Link] = None


@blueprint.route('/')
def index():
    people = [
        Person("iojonmbnmb", [Link("github", "https://github.com/iojon")]),
        Person("Cloppershy", [Link("github", "https://github.com/Cloppershy")]),
        Person("Dregu", [Link("github", "https://github.com/Dregu")]),
        Person("SciresM", [Link("github", "https://github.com/SciresM")]),
        Person("garebear"),
    ]
    return render_template("index.html", people=people)
