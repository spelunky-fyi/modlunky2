// Scale and geometry helpers for the hand-rolled charts.
//
// These are separated from the components because they are the part worth
// testing: an axis that picks 0/347/694 instead of 0/200/400/600 is the
// difference between a chart you can read a value off and one you can't.

/** A plot area in SVG user units. */
export interface Box {
  width: number;
  height: number;
  /** Space reserved for axis labels, inside the SVG. */
  padding: { top: number; right: number; bottom: number; left: number };
}

/**
 * Rounds `value` up to the next "nice" number: 1, 2 or 5 times a power
 * of ten.
 *
 * An axis topping out at exactly the largest data point crops the mark
 * that matters, and one topping out at an arbitrary number gives ticks
 * nobody can read against. Snapping to 1/2/5 is what produces ticks like
 * 200 / 400 / 600 rather than 173 / 346 / 519.
 */
export function niceCeil(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const normalized = value / magnitude;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

/**
 * Rounds a raw axis step up to the nearest readable interval: 1, 2, 2.5,
 * 5 or 10 times a power of ten.
 *
 * 2.5 earns its place in that list. Without it, a step of 22.5 rounds all
 * the way to 50, which halves the tick count and leaves an axis topping
 * out at twice the data.
 */
function niceStep(raw: number): number {
  if (!Number.isFinite(raw) || raw <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const normalized = raw / magnitude;
  const step = [1, 2, 2.5, 5, 10].find((candidate) => normalized <= candidate) ?? 10;
  return step * magnitude;
}

/**
 * Evenly spaced tick values from 0 up to at least `max`.
 *
 * `count` is the target number of intervals, not a guarantee: the step is
 * rounded to something readable first, then the axis extends to the next
 * whole step past the data. Rounding the top before deriving the step is
 * what produces axes that stop at double the largest value.
 */
export function axisTicks(max: number, count = 4): number[] {
  const safeMax = Number.isFinite(max) && max > 0 ? max : 1;
  const step = niceStep(safeMax / Math.max(1, count));
  const top = step * Math.ceil(safeMax / step);
  const ticks: number[] = [];
  for (let value = 0; value <= top + step / 2; value += step) {
    // Floating-point accumulation turns 0.30000000000000004 into a tick
    // label; rounding at a fixed precision keeps them clean.
    ticks.push(Number(value.toFixed(6)));
  }
  return ticks;
}

/** A time-series point. */
export interface TrendPoint {
  /** Epoch milliseconds. */
  t: number;
  v: number;
}

/** Where a point landed in SVG user units. */
export interface PlottedPoint extends TrendPoint {
  x: number;
  y: number;
  index: number;
}

export interface Trend {
  points: PlottedPoint[];
  /** `d` for the line path. Empty when there is nothing to draw. */
  path: string;
  /** `d` for the area wash beneath the line. */
  areaPath: string;
  ticks: number[];
  /** Top of the value axis. */
  max: number;
  box: Box;
}

/**
 * Projects a time series into a plot box.
 *
 * The value axis always starts at zero. These are lifetime counters, so a
 * zoomed axis would turn "deaths went from 594 to 596" into a dramatic
 * climb, which is exactly the misreading a stats page should not invite.
 *
 * A single point still gets plotted, centered, so a brand-new history
 * shows something rather than an empty frame.
 */
export function buildTrend(points: TrendPoint[], box: Box): Trend {
  const { width, height, padding } = box;
  const plotWidth = Math.max(1, width - padding.left - padding.right);
  const plotHeight = Math.max(1, height - padding.top - padding.bottom);

  const values = points.map((p) => p.v);
  const max = niceCeil(Math.max(1, ...values));
  const ticks = axisTicks(Math.max(1, ...values));
  const axisTop = ticks[ticks.length - 1] ?? max;

  const times = points.map((p) => p.t);
  const minT = Math.min(...times);
  const maxT = Math.max(...times);
  const span = maxT - minT;

  const plotted: PlottedPoint[] = points.map((p, index) => ({
    ...p,
    index,
    // With one point, or several sharing a timestamp, there is no span to
    // scale against; centering beats dividing by zero.
    x: padding.left + (span === 0 ? plotWidth / 2 : ((p.t - minT) / span) * plotWidth),
    y: padding.top + plotHeight - (p.v / axisTop) * plotHeight,
  }));

  const path = plotted
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
    .join(" ");

  const baseline = padding.top + plotHeight;
  const areaPath =
    plotted.length > 0
      ? `${path} L${plotted[plotted.length - 1].x.toFixed(2)},${baseline.toFixed(2)} ` +
        `L${plotted[0].x.toFixed(2)},${baseline.toFixed(2)} Z`
      : "";

  return { points: plotted, path, areaPath, ticks, max: axisTop, box };
}

/**
 * The point nearest `x`, for a crosshair that follows the pointer without
 * demanding it land on a dot.
 */
export function nearestPoint(
  points: PlottedPoint[],
  x: number,
): PlottedPoint | null {
  if (points.length === 0) return null;
  let best = points[0];
  let bestDistance = Math.abs(points[0].x - x);
  for (const point of points) {
    const distance = Math.abs(point.x - x);
    if (distance < bestDistance) {
      best = point;
      bestDistance = distance;
    }
  }
  return best;
}

/**
 * Bar length as a percentage of the widest bar in the set.
 *
 * Relative to the largest value rather than to a fixed axis, because
 * these bars carry their value as a direct label; the length is for
 * comparing them to each other.
 */
export function barPercent(value: number, max: number): number {
  if (max <= 0) return 0;
  return Math.max(0, Math.min(100, (value / max) * 100));
}
