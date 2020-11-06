from pathlib import Path

import psutil

from modlunky2.spawn_item import ItemSpawner


PROCESS_NAME = "Spel2.exe"


def find_process(name):
    for proc in psutil.process_iter():
        if proc.name() == name:
            return proc


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Tool for modding Spelunky 2.")
    parser.add_argument(
        "--process-name", default=PROCESS_NAME,
        help="Name of Spelunky Process. (Default: %(default)s"
    )
    args = parser.parse_args()



    proc = find_process(args.process_name)
    if proc is None:
        print("{args.process_name} isn't running...")
        sys.exit(1)

    spawner = ItemSpawner(proc)
    while True:
        item_num = input("item? ")
        spawner.spawn(item_num)
