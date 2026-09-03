// How the archive has changed over time, as a modal.
//
// The collection half of the stats: charts
// built from every archived save, and the gallery of every constellation
// they hold. It is separate from a single save's details because it
// answers a different question and costs far more to build - it parses
// the whole archive, where details parses one file.

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Sparkles } from "lucide-react";
import {
  getStatsOverview,
  type GalleryEntry,
  type HistoryPoint,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { TrendChart } from "./charts/TrendChart";
import { ConstellationView } from "./charts/ConstellationView";
import { formatDuration, formatMoney, formatTimestamp } from "./format";
import "./stats.css";

export function OverTimeModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [overview, setOverview] = useState<{
    history: HistoryPoint[];
    gallery: GalleryEntry[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!open) return;
    setError(null);
    try {
      setOverview(await getStatsOverview());
    } catch (err) {
      // Not an empty archive. Telling someone with four hundred
      // snapshots on disk that they have none sends them to entirely the
      // wrong problem.
      setError(extractMessage(err));
    }
  }, [open]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!open) return null;

  return (
    <Modal open onClose={onClose} title="Over time" size="xl">
      <div className="stats charts stats-modal">
        {error !== null ? (
          <p className="stats-error">
            <AlertTriangle size={14} aria-hidden="true" />
            Your archive could not be read: {error}
          </p>
        ) : overview === null ? (
          <OverTimeSkeleton />
        ) : (
          <>
            <HistoryCard history={overview.history} />
            <ConstellationCard gallery={overview.gallery} />
          </>
        )}
      </div>
    </Modal>
  );
}

/** Building this parses every archived save, so the wait is real enough
 *  to deserve a shape rather than a spinner. */
function OverTimeSkeleton() {
  return (
    <>
      <section className="stats-card" aria-busy="true">
        <h2 className="stats-heading">Over time</h2>
        <div className="stats-grid" aria-hidden="true">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="skeleton-chart" />
          ))}
        </div>
      </section>
      <section className="stats-card" aria-busy="true">
        <h2 className="stats-heading">Constellations</h2>
        <ul className="stats-gallery" aria-hidden="true">
          {Array.from({ length: 3 }, (_, i) => (
            <li key={i}>
              <div className="skeleton-constellation" />
              <div className="stats-gallery-caption">
                <span className="skeleton-bar" style={{ width: "50%" }} />
                <span
                  className="skeleton-bar skeleton-bar-sub"
                  style={{ width: "70%" }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

/** Counters over time, one small multiple per measure.
 *
 *  Deliberately not one chart with several lines: these counters differ
 *  by orders of magnitude, and sharing an axis would flatten the small
 *  ones while a second axis would invent a relationship between them. */
function HistoryCard({ history }: { history: HistoryPoint[] }) {
  const series = useMemo(() => {
    const at = (pick: (point: HistoryPoint) => number) =>
      history.map((point) => ({ t: point.takenAtMs, v: pick(point) }));
    return {
      plays: at((p) => p.plays),
      deaths: at((p) => p.deaths),
      journal: at((p) => p.journalDiscovered),
      score: at((p) => p.scoreTotal),
      time: at((p) => p.timeTotalMillis),
      wins: at((p) => p.wins),
    };
  }, [history]);

  if (history.length === 0) {
    return (
      <section className="stats-card">
        <h2 className="stats-heading">Over time</h2>
        <p className="stats-note">
          Nothing archived yet. Archive a save, or turn on snapshots, and these
          charts fill in as you gain history.
        </p>
      </section>
    );
  }

  return (
    <section className="stats-card">
      <h2 className="stats-heading">Over time</h2>
      <p className="stats-note">
        {`${history.length} archived save${history.length === 1 ? "" : "s"}, from ${formatTimestamp(history[0].takenAtMs)}.`}
      </p>
      <div className="stats-grid">
        <TrendChart title="Runs played" points={series.plays} />
        <TrendChart title="Deaths" points={series.deaths} />
        <TrendChart title="Journal entries" points={series.journal} />
        <TrendChart title="Wins" points={series.wins} />
        <TrendChart
          title="Money collected"
          points={series.score}
          format={formatMoney}
        />
        <TrendChart
          title="Time played"
          points={series.time}
          format={formatDuration}
        />
      </div>
    </section>
  );
}

/** Every constellation across the archive.
 *
 *  A save holds one at a time and generating a new one overwrites it, so
 *  without an archive this view could only ever show a single chart. */
function ConstellationCard({ gallery }: { gallery: GalleryEntry[] }) {
  return (
    <section className="stats-card">
      <h2 className="stats-heading">
        <Sparkles size={15} aria-hidden="true" />
        Constellations
      </h2>
      {gallery.length === 0 ? (
        <p className="stats-note">No constellations yet.</p>
      ) : (
        <>
          <ul className="stats-gallery">
            {gallery.map((entry) => (
              <li key={entry.signature}>
                <ConstellationView
                  constellation={entry.constellation}
                  label={`Constellation with ${entry.constellation.stars.length} stars, from ${entry.description || formatTimestamp(entry.lastSeenMs)}`}
                />
                <div className="stats-gallery-caption">
                  <span className="stats-gallery-title">
                    {entry.description || "Untitled"}
                    {entry.isCurrent && (
                      <span className="stats-gallery-tag">current</span>
                    )}
                  </span>
                  <span className="stats-gallery-meta">
                    {entry.constellation.stars.length} stars,{" "}
                    {entry.constellation.lines.length} lines
                    {entry.occurrences > 1 &&
                      ` · in ${entry.occurrences} saves`}
                    {" · "}
                    {formatTimestamp(entry.lastSeenMs)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/** The message out of a rejected command, which arrives as a string. */
function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  return String(err);
}
