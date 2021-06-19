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
    print(state.time_total)


if __name__ == "__main__":
    try:
        test()
    except KeyboardInterrupt:
        pass
