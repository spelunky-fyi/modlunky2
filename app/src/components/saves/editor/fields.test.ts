import { describe, expect, it } from "vitest";
import { clockToFrames, framesToClock } from "./fields";

describe("framesToClock", () => {
  it("formats a frame count the way the game shows a time", () => {
    expect(framesToClock(0)).toBe("0:00:00.000");
    expect(framesToClock(60)).toBe("0:00:01.000");
    expect(framesToClock(4358)).toBe("0:01:12.633");
    expect(framesToClock(60 * 60 * 60)).toBe("1:00:00.000");
  });

  // The save uses -1 for "no time set", which is not the same as a
  // zero-second run, so it must not render as one.
  it("shows an unset time as empty rather than as zero", () => {
    expect(framesToClock(-1)).toBe("");
  });
});

describe("clockToFrames", () => {
  it("round-trips whatever it printed", () => {
    for (const frames of [0, 1, 60, 4358, 216000, 1234567]) {
      expect(clockToFrames(framesToClock(frames))).toBe(frames);
    }
  });

  it("accepts fewer parts than it prints", () => {
    // Typing "90" for ninety seconds is the obvious thing to try.
    expect(clockToFrames("90")).toBe(5400);
    expect(clockToFrames("1:30")).toBe(5400);
    expect(clockToFrames("0:01:30")).toBe(5400);
  });

  it("pads a short fraction rather than misreading it", () => {
    // ".5" is half a second, not five milliseconds.
    expect(clockToFrames("0:00:00.5")).toBe(30);
    expect(clockToFrames("0:00:00.05")).toBe(3);
  });

  it("gives back the unset sentinel for an empty field", () => {
    expect(clockToFrames("")).toBe(-1);
    expect(clockToFrames("   ")).toBe(-1);
  });

  // A field that cannot be parsed has to say so, or the editor writes a
  // silent zero over a real time.
  it("refuses what it cannot read", () => {
    expect(clockToFrames("about an hour")).toBeNull();
    expect(clockToFrames("1:2:3:4")).toBeNull();
    expect(clockToFrames("-5")).toBeNull();
    expect(clockToFrames("1:")).toBeNull();
    expect(clockToFrames("99999999999")).toBeNull();
  });
});
