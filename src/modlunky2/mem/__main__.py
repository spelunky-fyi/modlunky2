import time

from . import find_spelunky2_pid, Spel2Process


def test():
    print("Finding Spel2.exe")
    pid = find_spelunky2_pid()
    if pid is None:
        print("Failed to get pid")
        return

    print("Opening Process")
    proc = Spel2Process.from_pid(pid)
    if proc is None:
        print("Failed to make proc")
        return

    print("Getting State")
    state = proc.get_state()
    print("Done getting State")

    # Get EntityDB Type
    entity_db = proc.get_entity_db()
    entry = entity_db.get_entity_db_entry_by_id(4)
    print(entry.id())

    while True:
        player1 = state.players()[0]
        if player1 is None:
            time.sleep(0.1)
            continue

        print(state.hud_flags())
        print(state.run_recap_flags())
        overlay = player1.overlay()
        if overlay:
            print(overlay.type().id())
            if overlay.type().id() == 897:
                turkey = overlay.as_mount()
                print("Tamed?", turkey.is_tamed())
        entity_map = state.uid_to_entity()
        for item in player1.items():
            print(entity_map.get(item).type().name())
        print("")
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        test()
    except KeyboardInterrupt:
        pass
