import logging
import requests
from packaging import version

from modlunky2.constants import BASE_DIR

logger = logging.getLogger(__name__)


def latest_version():
    logger.debug("Fetching latest version of Modlunky")
    try:
        return version.parse(
            requests.get(
                "https://api.github.com/repos/spelunky-fyi/modlunky2/releases/latest",
                timeout=5,
            ).json()["tag_name"]
        )
    except Exception:  # pylint: disable=broad-except
        return None


def current_version():
    with (BASE_DIR / "VERSION").open(encoding="utf-8") as version_file:
        return version.parse(version_file.read().strip())
