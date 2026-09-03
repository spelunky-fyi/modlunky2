import { describe, expect, it } from "vitest";
import {
  describeDepth,
  formatBytes,
  formatCount,
  formatDepth,
  formatDuration,
  formatMoney,
  formatTimestamp,
} from "./format";

describe("formatDuration", () => {
  it("drops seconds once the duration reaches an hour", () => {
    // Total play time runs to hundreds of hours; seconds are noise there.
    expect(formatDuration(3_600_000)).toBe("1h 0m");
    expect(formatDuration(3_600_000 * 2 + 60_000 * 30)).toBe("2h 30m");
  });

  it("keeps seconds for a single run", () => {
    expect(formatDuration(90_000)).toBe("1m 30s");
    expect(formatDuration(9_000)).toBe("9s");
  });

  it("separates thousands in very long play times", () => {
    expect(formatDuration(3_600_000 * 1234)).toBe("1,234h 0m");
  });

  it("treats missing or nonsensical values as zero", () => {
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(-5)).toBe("0s");
    expect(formatDuration(Number.NaN)).toBe("0s");
  });
});

describe("formatBytes", () => {
  it("scales to the size of a save file", () => {
    expect(formatBytes(512)).toBe("512 B");
    // A real savegame.sav is about this big.
    expect(formatBytes(13862)).toBe("13.5 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("formatTimestamp", () => {
  const now = Date.UTC(2026, 8, 2, 12, 0, 0);

  it("uses relative time for anything within a day", () => {
    expect(formatTimestamp(now - 30_000, now)).toBe("just now");
    expect(formatTimestamp(now - 60_000, now)).toBe("1 minute ago");
    expect(formatTimestamp(now - 120_000, now)).toBe("2 minutes ago");
    expect(formatTimestamp(now - 3_600_000, now)).toBe("1 hour ago");
    expect(formatTimestamp(now - 3_600_000 * 5, now)).toBe("5 hours ago");
  });

  it("switches to a real date past a day, where the day matters more", () => {
    const older = formatTimestamp(now - 3_600_000 * 30, now);
    expect(older).not.toMatch(/ago/);
    expect(older).toMatch(/2026/);
  });

  it("does not report a future timestamp as elapsed time", () => {
    // Clock skew or a file copied with its original mtime.
    expect(formatTimestamp(now + 60_000, now)).not.toMatch(/ago/);
  });
});

describe("counts and money", () => {
  it("separates thousands", () => {
    expect(formatCount(2526)).toBe("2,526");
    expect(formatMoney(527225)).toBe("$527,225");
  });

  it("handles the zero case plainly", () => {
    expect(formatCount(0)).toBe("0");
    expect(formatMoney(0)).toBe("$0");
  });
});

describe("formatDepth", () => {
  /** The save stores the Cosmic Ocean as world 8; every screen in the
   *  game shows it as 7. A stats page that disagreed with the profile
   *  screen would be unusable for cross-checking. */
  it("shows the Cosmic Ocean as world 7, the way the game does", () => {
    expect(formatDepth(8, 99)).toBe("7-99");
    expect(formatDepth(8, 5)).toBe("7-5");
  });

  it("leaves every other world alone", () => {
    expect(formatDepth(1, 1)).toBe("1-1");
    expect(formatDepth(7, 4)).toBe("7-4");
  });

  /** "7-5" alone could be Sunken City or the Cosmic Ocean, so anything
   *  that can afford the words should name the area. */
  it("can disambiguate with the area name", () => {
    expect(describeDepth(8, 5, "Cosmic Ocean")).toBe("7-5 (Cosmic Ocean)");
    expect(describeDepth(7, 4, "Sunken City")).toBe("7-4 (Sunken City)");
  });
});
