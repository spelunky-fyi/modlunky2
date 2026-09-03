import { describe, expect, it } from "vitest";
import {
  axisTicks,
  barPercent,
  buildTrend,
  nearestPoint,
  niceCeil,
  type Box,
} from "./scale";

const BOX: Box = {
  width: 300,
  height: 100,
  padding: { top: 10, right: 10, bottom: 20, left: 40 },
};

describe("niceCeil", () => {
  it("snaps up to 1, 2 or 5 times a power of ten", () => {
    expect(niceCeil(1)).toBe(1);
    expect(niceCeil(7)).toBe(10);
    expect(niceCeil(11)).toBe(20);
    expect(niceCeil(45)).toBe(50);
    expect(niceCeil(173)).toBe(200);
    expect(niceCeil(596)).toBe(1000);
    expect(niceCeil(2526)).toBe(5000);
  });

  it("never returns zero, so nothing divides by it", () => {
    expect(niceCeil(0)).toBe(1);
    expect(niceCeil(-5)).toBe(1);
    expect(niceCeil(Number.NaN)).toBe(1);
  });
});

describe("axisTicks", () => {
  it("produces round steps a reader can count off", () => {
    expect(axisTicks(90, 4)).toEqual([0, 25, 50, 75, 100]);
    expect(axisTicks(173, 4)).toEqual([0, 50, 100, 150, 200]);
    expect(axisTicks(596, 4)).toEqual([0, 200, 400, 600]);
  });

  it("always starts at zero and ends at or above the data", () => {
    for (const max of [1, 7, 45, 90, 173, 596, 2526, 8784220]) {
      const ticks = axisTicks(max);
      expect(ticks[0]).toBe(0);
      expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(max);
    }
  });

  /** An axis that stops at double the data wastes half the plot. */
  it("does not overshoot the data by more than one step", () => {
    for (const max of [1, 7, 45, 90, 173, 596, 2526]) {
      const ticks = axisTicks(max);
      const step = ticks[1] - ticks[0];
      const top = ticks[ticks.length - 1];
      expect(top - max).toBeLessThan(step);
    }
  });

  it("keeps tick values free of floating-point dust", () => {
    for (const tick of axisTicks(3, 4)) {
      expect(String(tick)).not.toMatch(/00000|99999/);
    }
  });
});

describe("buildTrend", () => {
  const points = [
    { t: 1000, v: 10 },
    { t: 2000, v: 20 },
    { t: 3000, v: 15 },
  ];

  it("spans the plot area horizontally", () => {
    const trend = buildTrend(points, BOX);
    expect(trend.points[0].x).toBeCloseTo(40);
    expect(trend.points[2].x).toBeCloseTo(290);
  });

  /** Lifetime counters zoomed to their own range turn a rounding-error
   *  change into a dramatic climb. The axis has to start at zero. */
  it("anchors the value axis at zero", () => {
    const trend = buildTrend(
      [
        { t: 1, v: 594 },
        { t: 2, v: 596 },
      ],
      BOX,
    );
    expect(trend.ticks[0]).toBe(0);
    // Both points sit near the same height, rather than at opposite ends.
    const [a, b] = trend.points;
    expect(Math.abs(a.y - b.y)).toBeLessThan(5);
  });

  it("centers a single point instead of dividing by a zero span", () => {
    const trend = buildTrend([{ t: 5, v: 3 }], BOX);
    expect(trend.points).toHaveLength(1);
    expect(trend.points[0].x).toBeCloseTo(40 + 250 / 2);
    expect(Number.isFinite(trend.points[0].y)).toBe(true);
  });

  it("handles several points sharing one timestamp", () => {
    const trend = buildTrend(
      [
        { t: 7, v: 1 },
        { t: 7, v: 2 },
      ],
      BOX,
    );
    expect(trend.points.every((p) => Number.isFinite(p.x))).toBe(true);
  });

  it("builds a closed area path beneath the line", () => {
    const trend = buildTrend(points, BOX);
    expect(trend.path.startsWith("M")).toBe(true);
    expect(trend.areaPath.endsWith("Z")).toBe(true);
  });

  it("produces no path for no data", () => {
    const trend = buildTrend([], BOX);
    expect(trend.path).toBe("");
    expect(trend.areaPath).toBe("");
  });
});

describe("nearestPoint", () => {
  const trend = buildTrend(
    [
      { t: 1000, v: 10 },
      { t: 2000, v: 20 },
      { t: 3000, v: 15 },
    ],
    BOX,
  );

  it("finds the closest point to a pointer x, not an exact hit", () => {
    expect(nearestPoint(trend.points, 42)?.index).toBe(0);
    expect(nearestPoint(trend.points, 160)?.index).toBe(1);
    expect(nearestPoint(trend.points, 1000)?.index).toBe(2);
  });

  it("returns null with nothing to hit", () => {
    expect(nearestPoint([], 10)).toBeNull();
  });
});

describe("barPercent", () => {
  it("scales against the largest bar", () => {
    expect(barPercent(50, 100)).toBe(50);
    expect(barPercent(100, 100)).toBe(100);
    expect(barPercent(0, 100)).toBe(0);
  });

  it("never produces a negative or overflowing bar", () => {
    expect(barPercent(5, 0)).toBe(0);
    expect(barPercent(-5, 100)).toBe(0);
    expect(barPercent(150, 100)).toBe(100);
  });
});
