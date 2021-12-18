import serde.json

from modlunky2.mem.arena_state import ArenaState
from modlunky2.mem import find_spelunky2_pid, Spel2Process


def dump_arena(arena: ArenaState):
    print("Arena")
    print("-------------")
    print("Format:", arena.format)
    print("Ruleset:", arena.ruleset)
    print("Timer:", arena.timer)
    print("Timer Ending:", arena.timer_ending)
    print("Wins:", arena.wins)
    print("Lives:", arena.lives)
    print("Time to Win:", arena.time_to_win)
    print("Health:", arena.health)
    print("Bombs:", arena.bombs)
    print("Ropes:", arena.ropes)
    print("Stun Time:", arena.stun_time)
    print("Mount:", arena.mount)
    print("Arena Select", arena.arena_select)
    print("Dark Level Chances:", arena.dark_level_chance)
    print("Crate Frequency:", arena.crate_frequency)
    print(
        "Items Enabled:",
        ", ".join(map(str, arena.get_enabled_items(arena.items_enabled))),
    )
    print(
        "Items In Crates:",
        ", ".join(map(str, arena.get_enabled_items(arena.items_in_crate))),
    )
    print("Held Item:", arena.held_item)
    print("Equipped Backitem:", arena.equipped_backitem)
    print(
        "Equipped Items:",
        ", ".join(map(str, arena.get_enabled_items(arena.equipped_items))),
    )
    print("Whip Damage:", arena.whip_damage)
    print("Final Ghost:", arena.final_ghost)
    print("Breath Cooldown:", arena.breath_cooldown)
    print("Punish Ball:", arena.punish_ball)

    print("Areas:", ", ".join(map(str, arena.get_enabled_levels())))


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

    config = serde.json.to_json(state.arena_state, indent=4, sort_keys=True)
    arena = serde.json.from_json(ArenaState, config)
    dump_arena(arena)


if __name__ == "__main__":
    try:
        test()
    except KeyboardInterrupt:
        pass
