import requests
from packaging import version

from modlunky2.constants import BASE_DIR


def latest_version():
    try:
        return version.parse(
            requests.get(
                "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest"
            ).json()["tag_name"]
        )
    except Exception:  # pylint: disable=broad-except
        return None


def current_version():
    with (BASE_DIR / "VERSION").open() as version_file:
        return version.parse(version_file.read().strip())
