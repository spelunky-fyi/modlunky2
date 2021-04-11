import logging
from urllib.request import urlretrieve
from subprocess import Popen

from .constants import IS_EXE


logger = logging.getLogger("modlunky2")

LATEST_EXE = (
    "https://github.com/spelunky-fyi/modlunky2/releases/latest/download/modlunky2.exe"
)


def self_update(self_exe):
    if not IS_EXE:
        logger.warning("Tried to update while not an exe. Doing nothing...")
        return

    if self_exe is None:
        logger.warning("Passed None as self_exe. Doing nothing...")
        return

    exe_dir = self_exe.parent.resolve()

    new_path = exe_dir / f"{self_exe.stem}.backup{self_exe.suffix}"
    if new_path.exists():
        logger.info("Found previous backup. Removing...")
        new_path.unlink(missing_ok=True)

    logger.info("Moving running version to %s", new_path)
    self_exe.rename(new_path)

    logger.info("Downloading latest version now.")
    urlretrieve(LATEST_EXE, self_exe)

    logger.info("Launching new version now.")
    Popen([str(self_exe)])
