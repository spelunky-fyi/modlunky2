from pathlib import Path

from s2_control.spawn_item import ItemSpawner

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sidecar for controlling Spelunky 2.")
    parser.add_argument("exe", type=Path, help="Path to Spel2.exe")
    parser.add_argument("item", type=int, default=364)
    args = parser.parse_args()

    if not args.exe.exists():
        print("{args.exe} doesn't exist...")
        sys.exit(1)

    spawner = ItemSpawner(args.exe)
    spawner.spawn(args.item)
