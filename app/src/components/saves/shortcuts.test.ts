import { describe, expect, it } from "vitest";
import { shortcutProgress, TOTAL_DELIVERIES } from "./shortcuts";

describe("shortcutProgress", () => {
  it("treats 0 as never having met Terra", () => {
    const progress = shortcutProgress(0);
    expect(progress.metTerra).toBe(false);
    expect(progress.delivered).toBe(0);
    expect(progress.stages.flatMap((s) => s.deliveries).every((d) => !d.done)).toBe(
      true,
    );
  });

  /** Meeting Terra is a precondition, not one of the nine deliveries.
   *  Counting it as one would show a filled dot before anything is given. */
  it("counts meeting Terra as no deliveries", () => {
    const progress = shortcutProgress(1);
    expect(progress.metTerra).toBe(true);
    expect(progress.delivered).toBe(0);
  });

  it("fills deliveries in order", () => {
    const progress = shortcutProgress(3);
    expect(progress.delivered).toBe(2);
    const done = progress.stages.flatMap((s) => s.deliveries).map((d) => d.done);
    expect(done.slice(0, 2)).toEqual([true, true]);
    expect(done.slice(2).every((d) => !d)).toBe(true);
  });

  /** Each group of three opens one shortcut, which is the whole reason
   *  for grouping them. */
  it("completes a stage exactly when its three are done", () => {
    expect(shortcutProgress(4).stages[0].complete).toBe(true);
    expect(shortcutProgress(4).stages[1].complete).toBe(false);

    expect(shortcutProgress(7).stages[1].complete).toBe(true);
    expect(shortcutProgress(7).stages[2].complete).toBe(false);

    expect(shortcutProgress(10).stages.every((s) => s.complete)).toBe(true);
  });

  it("names the shortcut each stage opens", () => {
    expect(shortcutProgress(10).stages.map((s) => s.opens)).toEqual([
      "1-4",
      "3-1",
      "5-1",
    ]);
  });

  it("has nine deliveries in three stages of three", () => {
    const progress = shortcutProgress(10);
    expect(progress.stages).toHaveLength(3);
    expect(progress.stages.every((s) => s.deliveries.length === 3)).toBe(true);
    expect(progress.delivered).toBe(TOTAL_DELIVERIES);
    expect(progress.total).toBe(TOTAL_DELIVERIES);
  });

  /** A save editor can write anything into this byte. */
  it("clamps values outside the range the game uses", () => {
    expect(shortcutProgress(99).delivered).toBe(9);
    expect(shortcutProgress(-5).delivered).toBe(0);
    expect(shortcutProgress(-5).metTerra).toBe(false);
    expect(shortcutProgress(Number.NaN).delivered).toBe(0);
  });

  it("names what Terra asks for at each step", () => {
    const first = shortcutProgress(0).stages[0].deliveries.map((d) => d.label);
    expect(first).toEqual(["$2,000", "1 bomb", "$10,000"]);
    const last = shortcutProgress(0).stages[2].deliveries.map((d) => d.label);
    expect(last).toEqual(["$50,000", "a hired hand", "the golden key"]);
  });
});
