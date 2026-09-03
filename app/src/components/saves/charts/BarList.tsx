// A horizontal bar chart for comparing magnitudes.
//
// Every chart on the Stats panel is one series answering "which of these
// is biggest", so there is no categorical palette here: one hue for every
// bar. Coloring each bar by its own value would double-encode the length
// the bar already shows, and coloring them by category would spend the
// only free channel on identity nobody is asking about.
//
// Values ride the bar tips as direct labels rather than living only in a
// tooltip, so the numbers are readable without a pointer, and there is a
// table view for anyone who wants the whole thing as text.

import { useId, useState, type ReactNode } from "react";
import { Table2 } from "lucide-react";
import { barPercent } from "./scale";
import "./charts.css";

/** A row plus the surface gap under it, for turning a row count into a
 *  pixel height. Matches `.bar-row` in charts.css. */
const ROW_HEIGHT = 22;

export interface BarDatum {
  /** Stable key. */
  key: string;
  /** Row label. */
  label: string;
  value: number;
  /** Extra context for the tooltip and the table's second column. */
  detail?: string;
}

interface BarListProps {
  title: string;
  /** One line under the title saying what is plotted. Doubles as the
   *  legend a single-series chart does not need. */
  subtitle?: string;
  data: BarDatum[];
  /** Turns a value into its display string. */
  format?: (value: number) => string;
  /** Shown instead of the chart when there is nothing to plot. */
  empty?: string;
  /** Column heading for the label column in the table view. */
  labelHeading?: string;
  /** Column heading for the value column. */
  valueHeading?: string;
  /** How many rows fit before the list starts scrolling inside itself.
   *
   *  Some of these lists are genuinely long: a player who has been
   *  through the Cosmic Ocean has died on well over a hundred distinct
   *  levels, and the bestiary is 78 entries. An expanding "show all"
   *  just moved the problem, turning one card into a page of its own.
   *  A bounded box with its own scrollbar keeps every row reachable
   *  without letting one chart set the height of everything. */
  maxRows?: number;
  /** A control rendered in the header, beside the table toggle.
   *
   *  For anything that changes what this chart plots. Putting it in the
   *  header rather than above the card keeps it next to the title it
   *  applies to, so its scope is obvious and it does not read as a
   *  heading of its own. */
  action?: ReactNode;
}

export function BarList({
  title,
  subtitle,
  data,
  format = (v) => v.toLocaleString(),
  empty = "Nothing recorded yet.",
  labelHeading = "Name",
  valueHeading = "Value",
  maxRows = 14,
  action,
}: BarListProps) {
  const [showTable, setShowTable] = useState(false);
  const tableId = useId();

  const max = data.reduce((acc, d) => Math.max(acc, d.value), 0);
  // Only bound the height once there is more than fits, so a short list
  // does not get a scroll container it will never use.
  const scrolls = data.length > maxRows;

  return (
    <section className="chart">
      <header className="chart-head">
        <div>
          <h3 className="chart-title">{title}</h3>
          {subtitle && (
            <p className="chart-subtitle">
              {subtitle}
              {scrolls && ` · ${data.length} rows`}
            </p>
          )}
        </div>
        {(action || data.length > 0) && (
          <div className="chart-actions">
            {action}
            {data.length > 0 && (
              <button
                type="button"
                className="chart-toggle"
                aria-pressed={showTable}
                aria-controls={tableId}
                title={
                  showTable ? "Show the chart" : "Show the numbers as a table"
                }
                onClick={() => setShowTable((v) => !v)}
              >
                <Table2 size={13} aria-hidden="true" />
                {showTable ? "Chart" : "Table"}
              </button>
            )}
          </div>
        )}
      </header>

      {data.length === 0 ? (
        <p className="chart-empty">{empty}</p>
      ) : showTable ? (
        <div className="chart-table-wrap" id={tableId}>
          <table className="chart-table">
            <thead>
              <tr>
                <th scope="col">{labelHeading}</th>
                <th scope="col">{valueHeading}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.key}>
                  <th scope="row">{d.label}</th>
                  <td>{format(d.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ul
          className={`bars${scrolls ? " bars-scroll" : ""}`}
          id={tableId}
          style={scrolls ? { maxHeight: maxRows * ROW_HEIGHT } : undefined}
        >
          {data.map((d) => (
            <li
              key={d.key}
              className="bar-row"
              title={
                d.detail
                  ? `${d.label}: ${format(d.value)} (${d.detail})`
                  : `${d.label}: ${format(d.value)}`
              }
            >
              <span className="bar-label">{d.label}</span>
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{ width: `${barPercent(d.value, max)}%` }}
                />
              </span>
              <span className="bar-value">{format(d.value)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
