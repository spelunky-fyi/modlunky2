import datetime
import logging
import os
import os.path
from pathlib import Path
from shutil import copyfile

logger = logging.getLogger(__name__)


def make_backup(file, backup_dir):
    logger.debug("Making backup..")
    if os.path.isfile(file):
        lvl_name = (
            os.path.basename(file)
            + "_"
            + ("{date:%Y-%m-%d_%H_%M_%S}").format(date=datetime.datetime.now())
        )
        if not os.path.exists(Path(backup_dir)):
            os.makedirs(Path(backup_dir))
        copyfile(file, backup_dir + "/" + lvl_name)
        logger.debug("Backup made!")

        # Removes oldest backup every 50 backups
        _, _, files = next(os.walk(backup_dir))
        file_count = len(files)
        logger.debug("This mod has %s backups.", file_count)
        list_of_files = os.listdir(backup_dir)
        full_path = [backup_dir + f"/{x}" for x in list_of_files]
        if len(list_of_files) >= 50:
            logger.debug("Deleting oldest backup")
            oldest_file = min(full_path, key=os.path.getctime)
            os.remove(oldest_file)
    else:
        logger.debug("Backup not needed for what was a default file.")
