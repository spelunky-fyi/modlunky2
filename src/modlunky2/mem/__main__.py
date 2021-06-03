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

    # Get EntityDB Type
    entity_db = proc.get_entity_db()
    entry = entity_db.get_entity_db_entry_by_id(4)
    print(entry.id())

    player1 = state.players()[0]
    print(player1.items())

    entity_map = state.uid_to_entity()
    print(entity_map.get(1041).type().id())


if __name__ == "__main__":
    test()
