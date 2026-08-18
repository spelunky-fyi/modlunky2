import { describe, expect, it } from "vitest";

import { byName, compareMods, relativeTime, sortMods } from "./modSort";
import { defaultDescending, isModSort, type Mod } from "../types/mods";

/** A mod with only the fields the ordering looks at. */
function mod(id: string, over: Partial<Mod> = {}): Mod {
  return {
    id,
    manifest: null,
    hasUpdate: false,
    modifiedAt: 0,
    lastUsedAt: null,
    favorite: false,
    ...over,
  };
}

/** Mods carry a display name that differs from their id, and the list is
 *  ordered by what's on screen, not by the id underneath. */
function named(id: string, name: string, over: Partial<Mod> = {}): Mod {
  return mod(id, {
    manifest: {
      name,
      slug: id,
      description: "",
      logo: null,
      mod_file: { id: "f", created_at: "", download_url: "" },
    },
    ...over,
  });
}

const ids = (mods: Mod[]) => mods.map((m) => m.id);

describe("byName", () => {
  it("orders by the displayed name, not the underlying id", () => {
    const zzz = named("aaa-id", "Zebra");
    const aaa = named("zzz-id", "Aardvark");
    expect(ids(sortMods([zzz, aaa], "name", false))).toEqual([
      "zzz-id",
      "aaa-id",
    ]);
  });

  it("falls back to the id when a mod has no manifest", () => {
    expect(byName(mod("apple"), mod("banana"))).toBeLessThan(0);
  });

  it("ignores case", () => {
    expect(byName(named("a", "apple"), named("b", "Banana"))).toBeLessThan(0);
  });

  it("compares numbers by value, so Mod 2 precedes Mod 10", () => {
    const list = [named("b", "Mod 10"), named("a", "Mod 2")];
    expect(ids(sortMods(list, "name", false))).toEqual(["a", "b"]);
  });
});

describe("sorting by install time", () => {
  it("puts the newest first when descending", () => {
    const list = [
      mod("old", { modifiedAt: 1_000 }),
      mod("new", { modifiedAt: 3_000 }),
      mod("mid", { modifiedAt: 2_000 }),
    ];
    expect(ids(sortMods(list, "installed", true))).toEqual([
      "new",
      "mid",
      "old",
    ]);
  });

  it("reverses cleanly", () => {
    const list = [
      mod("old", { modifiedAt: 1_000 }),
      mod("new", { modifiedAt: 3_000 }),
    ];
    expect(ids(sortMods(list, "installed", false))).toEqual(["old", "new"]);
  });

  it("sorts a mod whose folder could not be read to the oldest end", () => {
    const list = [mod("unknown", { modifiedAt: 0 }), mod("known", { modifiedAt: 5 })];
    expect(ids(sortMods(list, "installed", true))).toEqual(["known", "unknown"]);
  });
});

describe("sorting by last used", () => {
  it("puts the most recently played first when descending", () => {
    const list = [
      mod("a", { lastUsedAt: 1_000 }),
      mod("c", { lastUsedAt: 3_000 }),
      mod("b", { lastUsedAt: 2_000 }),
    ];
    expect(ids(sortMods(list, "used", true))).toEqual(["c", "b", "a"]);
  });

  /** The whole point of the sort is surfacing what you just played. Mods that
   *  have never been played must not outrank them. */
  it("sinks never-played mods below everything that has been played", () => {
    const list = [
      mod("never-a"),
      mod("played", { lastUsedAt: 1 }),
      mod("never-b"),
    ];
    expect(ids(sortMods(list, "used", true))[0]).toBe("played");
  });

  it("treats a never-played mod as older than one played at the epoch+1", () => {
    expect(
      compareMods(mod("never"), mod("played", { lastUsedAt: 1 }), "used", false),
    ).toBeLessThan(0);
  });
});

describe("the name tie-break", () => {
  /** Regression: applying the direction flip to the tie-break as well would
   *  order equal timestamps Z-A. Ties are the common case here -- every
   *  never-played mod shares one, as does everything installed together. */
  it("stays A-Z even when the primary sort is descending", () => {
    const list = [
      named("c", "Charlie", { lastUsedAt: 5 }),
      named("a", "Alpha", { lastUsedAt: 5 }),
      named("b", "Bravo", { lastUsedAt: 5 }),
    ];
    expect(ids(sortMods(list, "used", true))).toEqual(["a", "b", "c"]);
  });

  it("stays A-Z among never-played mods", () => {
    const list = [named("c", "Charlie"), named("a", "Alpha")];
    expect(ids(sortMods(list, "used", true))).toEqual(["a", "c"]);
  });

  it("stays A-Z for equal install times", () => {
    const list = [
      named("c", "Charlie", { modifiedAt: 9 }),
      named("a", "Alpha", { modifiedAt: 9 }),
    ];
    expect(ids(sortMods(list, "installed", true))).toEqual(["a", "c"]);
  });
});

describe("sortMods", () => {
  it("does not mutate the list it was given", () => {
    const list = [mod("b", { modifiedAt: 2 }), mod("a", { modifiedAt: 1 })];
    sortMods(list, "installed", false);
    expect(ids(list)).toEqual(["b", "a"]);
  });
});

describe("relativeTime", () => {
  const now = 1_700_000_000_000;
  const ago = (ms: number) => relativeTime(now - ms, now);

  it("reports sub-minute gaps as just now", () => {
    expect(ago(0)).toBe("just now");
    expect(ago(59_000)).toBe("just now");
  });

  it("picks the largest unit that fits", () => {
    expect(ago(60_000)).toMatch(/minute/);
    expect(ago(60 * 60_000)).toMatch(/hour/);
    expect(ago(3 * 24 * 60 * 60_000)).toMatch(/3 days|days/);
    expect(ago(400 * 24 * 60 * 60_000)).toMatch(/year/);
  });

  it("crosses each boundary exactly at the threshold", () => {
    expect(ago(59_999)).toBe("just now");
    expect(ago(60_000)).not.toBe("just now");
  });

  it("phrases the result as past tense", () => {
    // Intl renders negative values as "... ago" / "yesterday"; a positive one
    // would read "in 3 days", which would be nonsense for a timestamp.
    expect(ago(3 * 24 * 60 * 60_000)).not.toMatch(/^in /);
  });
});

describe("sort option metadata", () => {
  it("accepts the known sorts and rejects anything else", () => {
    expect(isModSort("name")).toBe(true);
    expect(isModSort("installed")).toBe(true);
    expect(isModSort("used")).toBe(true);
    expect(isModSort("nonsense")).toBe(false);
    expect(isModSort(undefined)).toBe(false);
  });

  /** Names read A-Z; dates read newest-first. Getting this backwards makes
   *  every sort open on its least useful end. */
  it("defaults each field to its natural direction", () => {
    expect(defaultDescending("name")).toBe(false);
    expect(defaultDescending("installed")).toBe(true);
    expect(defaultDescending("used")).toBe(true);
  });
});
