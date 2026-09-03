// A single-series line chart for one counter over time.
//
// The history charts are small multiples rather than one plot with
// several lines. Runs, deaths and journal entries have wildly different
// magnitudes, and putting them together would mean either a second y-axis
// (which invents a correlation out of the arbitrary alignment of two
// scales) or a shared axis on which the small series are flat lines along
// the bottom. One chart per counter, each with its own axis, says the same
// thing without either problem.

import { useId, useMemo, useRef, useState } from "react";
import { Table2 } from "lucide-react";
import { buildTrend, nearestPoint, type PlottedPoint, type TrendPoint } from "./scale";
import { formatTimestamp } from "../format";
import "./charts.css";

const WIDTH = 520;
const HEIGHT = 150;
const PADDING = { top: 10, right: 14, bottom: 22, left: 46 };

interface TrendChartProps {
  title: string;
  subtitle?: string;
  points: TrendPoint[];
  format?: (value: number) => string;
  /** Shown when there are too few points to draw a line. */
  empty?: string;
}

export function TrendChart({
  title,
  subtitle,
  points,
  format = (v) => v.toLocaleString(),
  empty = "Not enough history yet.",
}: TrendChartProps) {
  const [showTable, setShowTable] = useState(false);
  const [hovered, setHovered] = useState<PlottedPoint | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const tableId = useId();

  const trend = useMemo(
    () =>
      buildTrend(points, { width: WIDTH, height: HEIGHT, padding: PADDING }),
    [points],
  );

  const baseline = HEIGHT - PADDING.bottom;
  const last = trend.points[trend.points.length - 1] ?? null;
  const active = hovered ?? last;

  // The pointer moves in CSS pixels but the chart is drawn in a fixed
  // viewBox, so the x has to be converted before it can be compared to a
  // point's position.
  const onMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * WIDTH;
    setHovered(nearestPoint(trend.points, x));
  };

  return (
    <section className="chart">
      <header className="chart-head">
        <div>
          <h3 className="chart-title">{title}</h3>
          {subtitle && <p className="chart-subtitle">{subtitle}</p>}
        </div>
        {points.length > 0 && (
          <button
            type="button"
            className="chart-toggle"
            aria-pressed={showTable}
            aria-controls={tableId}
            title={showTable ? "Show the chart" : "Show the numbers as a table"}
            onClick={() => setShowTable((v) => !v)}
          >
            <Table2 size={13} aria-hidden="true" />
            {showTable ? "Chart" : "Table"}
          </button>
        )}
      </header>

      {points.length === 0 ? (
        <p className="chart-empty">{empty}</p>
      ) : showTable ? (
        <div className="chart-table-wrap" id={tableId}>
          <table className="chart-table">
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={`${p.t}-${i}`}>
                  <th scope="row">{formatTimestamp(p.t)}</th>
                  <td>{format(p.v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="trend-wrap" id={tableId}>
          <svg
            ref={svgRef}
            className="trend"
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={`${title}. ${points.length} points from ${formatTimestamp(points[0].t)} to ${formatTimestamp(points[points.length - 1].t)}.`}
            onPointerMove={onMove}
            onPointerLeave={() => setHovered(null)}
          >
            {/* Hairline grid, one step off the surface, solid. */}
            {trend.ticks.map((tick) => {
              const y =
                PADDING.top +
                (HEIGHT - PADDING.top - PADDING.bottom) * (1 - tick / trend.max);
              return (
                <g key={tick}>
                  <line
                    className="trend-grid"
                    x1={PADDING.left}
                    x2={WIDTH - PADDING.right}
                    y1={y}
                    y2={y}
                  />
                  <text className="trend-tick" x={PADDING.left - 6} y={y + 3}>
                    {compact(tick)}
                  </text>
                </g>
              );
            })}

            <path className="trend-area" d={trend.areaPath} />
            <path className="trend-line" d={trend.path} />

            {active && (
              <line
                className="trend-crosshair"
                x1={active.x}
                x2={active.x}
                y1={PADDING.top}
                y2={baseline}
              />
            )}

            {/* The end point is always marked; the hovered one joins it.
                Every point is not marked, which would be noise. */}
            {last && <circle className="trend-dot" cx={last.x} cy={last.y} r={4} />}
            {active && active !== last && (
              <circle className="trend-dot" cx={active.x} cy={active.y} r={4} />
            )}
          </svg>

          <div className="trend-readout" aria-live="polite">
            {active ? (
              <>
                <strong>{format(active.v)}</strong>
                <span>{formatTimestamp(active.t)}</span>
              </>
            ) : (
              <span>&nbsp;</span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

/** Axis ticks get compact labels so a 5-digit count does not crowd the
 *  plot; the readout and the table carry the exact value. */
function compact(value: number): string {
  if (value >= 1_000_000) return `${trimZero(value / 1_000_000)}M`;
  if (value >= 1_000) return `${trimZero(value / 1_000)}K`;
  return String(value);
}

function trimZero(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}
