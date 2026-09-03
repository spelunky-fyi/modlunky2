import { describe, expect, it } from "vitest";
import { filterSaves, groupByDate, type GroupableSave } from "./grouping";

/** Local noon, so a day's boundaries are unambiguous wherever this runs. */
function at(year: number, month: number, day: number, hour = 12): number {
  return new Date(year, month - 1, day, hour, 0, 0, 0).getTime();
}

const NOW = at(2026, 9, 3, 15);

function save(ms: number, description = "Automatic snapshot"): GroupableSave {
  return { id: String(ms), takenAtMs: ms, description };
}

describe("groupByDate", () => {
  it("gives the near past fine headings and the distant past coarse ones", () => {
    const groups = groupByDate(
      [
        save(at(2026, 9, 3, 9)),
        save(at(2026, 9, 2, 9)),
        save(at(2026, 8, 30, 9)),
        save(at(2026, 8, 20, 9)),
        save(at(2026, 5, 4, 9)),
        save(at(2025, 11, 4, 9)),
      ],
      NOW,
    );
    expect(groups.map((g) => g.label)).toEqual([
      "Today",
      "Yesterday",
      "Earlier this week",
      "Earlier this month",
      "May",
      "November 2025",
    ]);
  });

  /** The year is only worth printing when it is not the current one. */
  it("names the year only when it differs", () => {
    const groups = groupByDate([save(at(2026, 5, 4)), save(at(2025, 5, 4))], NOW);
    expect(groups[0].label).toBe("May");
    expect(groups[1].label).toBe("May 2025");
  });

  it("keeps consecutive saves from one day in a single group", () => {
    const groups = groupByDate(
      [save(at(2026, 9, 3, 14)), save(at(2026, 9, 3, 11)), save(at(2026, 9, 3, 8))],
      NOW,
    );
    expect(groups).toHaveLength(1);
    expect(groups[0].saves).toHaveLength(3);
  });

  it("loses nothing", () => {
    const saves = Array.from({ length: 200 }, (_, i) => save(NOW - i * 3_600_000));
    const groups = groupByDate(saves, NOW);
    expect(groups.flatMap((g) => g.saves)).toHaveLength(200);
  });

  /** Clock skew, or a file copied with its original timestamp, would
   *  otherwise fall through every branch and land in a month heading. */
  it("handles a timestamp in the future", () => {
    const groups = groupByDate([save(NOW + 60_000)], NOW);
    expect(groups[0].label).toBe("Just now");
  });

  it("returns nothing for nothing", () => {
    expect(groupByDate([], NOW)).toEqual([]);
  });
});

describe("filterSaves", () => {
  const saves = [
    save(at(2026, 9, 3), "Before the Cosmic Ocean"),
    save(at(2026, 5, 4), "Automatic snapshot"),
    save(at(2025, 11, 4), "beep boop"),
  ];

  it("matches the description, case insensitively", () => {
    expect(filterSaves(saves, "cosmic")).toHaveLength(1);
    expect(filterSaves(saves, "BEEP")).toHaveLength(1);
  });

  /** Automatic snapshots all share one description, so the date is the
   *  only thing that tells them apart. */
  it("matches the date too", () => {
    expect(filterSaves(saves, "2025")).toHaveLength(1);
    expect(filterSaves(saves, "may")).toHaveLength(1);
  });

  it("passes everything through for an empty query", () => {
    expect(filterSaves(saves, "")).toHaveLength(3);
    expect(filterSaves(saves, "   ")).toHaveLength(3);
  });

  it("returns nothing when nothing matches", () => {
    expect(filterSaves(saves, "zzzz")).toHaveLength(0);
  });
});
