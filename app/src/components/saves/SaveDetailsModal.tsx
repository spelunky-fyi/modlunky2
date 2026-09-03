// Everything in one save, as a modal.
//
// The per-save half of the stats. Making it a
// modal keyed to a save rather than a page keyed to *the* save is what
// lets any archived snapshot be opened, and means looking at one save no
// longer loads a year of history to do it.

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Flag as FlagIcon, Sparkles } from "lucide-react";
import {
  getSaveStats,
  getStoredSaveStats,
  type EntryStat,
  type SaveStats,
  type SaveSummary,
  type Sticker,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { BarList, type BarDatum } from "./charts/BarList";
import { ConstellationView } from "./charts/ConstellationView";
import {
  formatCount,
  formatDepth,
  formatDuration,
  formatMoney,
} from "./format";
import { shortcutProgress } from "./shortcuts";
import "./stats.css";

/** The pets, in the order the save stores their rescue counts. */
const PETS = ["Monty", "Percy", "Poochi"];

/** Which save to describe, and how to fetch the detail for it. */
export type DetailsSource =
  | { kind: "live" }
  | { kind: "stored"; id: string }
  /** A pruned snapshot: its summary survives, the save it came from does
   *  not, so per-entry detail cannot be rebuilt. */
  | { kind: "summaryOnly" };

export interface SaveDetailsTarget {
  title: string;
  subtitle: string;
  /** Always available, from the listing or the status read. */
  summary: SaveSummary;
  source: DetailsSource;
}

export function SaveDetailsModal({
  target,
  onClose,
}: {
  target: SaveDetailsTarget | null;
  onClose: () => void;
}) {
  const [stats, setStats] = useState<SaveStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const source = target?.source;

  useEffect(() => {
    // Cleared unconditionally, before the early return: a pruned snapshot
    // has nothing to load, and leaving the previous save's stats behind
    // would show its stickers and journal under this snapshot's heading.
    setStats(null);
    setError(null);
    if (source === undefined || source.kind === "summaryOnly") return;

    // Guards against a slower earlier load landing after a newer one and
    // pairing one save's title with another's numbers.
    let cancelled = false;
    const load = async () => {
      try {
        const detail =
          source.kind === "live"
            ? await getSaveStats()
            : await getStoredSaveStats(source.id);
        if (!cancelled) setStats(detail);
      } catch (err) {
        if (!cancelled) setError(extractMessage(err));
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [source]);

  if (target === null) return null;

  return (
    <Modal open onClose={onClose} title={target.title} size="xl">
      <div className="stats charts stats-modal">
        <p className="stats-subtitle">{target.subtitle}</p>

        <ProfileCard summary={target.summary} stats={stats} />

        <LastRunCard
          summary={target.summary}
          stickers={stats?.stickers ?? []}
        />

        {target.summary.constellation && (
          <section className="stats-card">
            <h2 className="stats-heading">
              <Sparkles size={15} aria-hidden="true" />
              Constellation
            </h2>
            <div className="stats-single-constellation">
              <ConstellationView
                constellation={target.summary.constellation}
                height={260}
              />
            </div>
          </section>
        )}

        {target.source.kind === "summaryOnly" ? (
          <section className="stats-card">
            <p className="stats-note stats-note-last">
              This snapshot's save file was pruned, so its totals are all that
              remain. The per-level and per-entry breakdowns need the save
              itself.
            </p>
          </section>
        ) : error !== null ? (
          <section className="stats-card stats-error">
            <AlertTriangle size={16} aria-hidden="true" />
            <div>
              <h2>Could not read this save</h2>
              <p>{error}</p>
            </div>
          </section>
        ) : stats === null ? (
          <DetailSkeleton />
        ) : (
          <>
            <DeathsCard stats={stats} />
            <JournalCard stats={stats} />
          </>
        )}
      </div>
    </Modal>
  );
}

/** The run the save was left on, the way the game's own journal shows it.
 *
 *  Worth its own card rather than a line in the profile: someone who
 *  archives a save right after a run they are pleased with is archiving
 *  precisely this. The stickers are part of it - the game draws them
 *  under the same heading, and they name the character played and what
 *  they were still carrying at the end. */
function LastRunCard({
  summary,
  stickers,
}: {
  summary: SaveSummary;
  stickers: Sticker[];
}) {
  const run = summary.lastRun;
  const played = stickers.filter((sticker) => sticker.isCharacter);
  const carried = stickers.filter((sticker) => !sticker.isCharacter);

  return (
    <section className="stats-card">
      <h2 className="stats-heading">
        <FlagIcon size={15} aria-hidden="true" />
        Last game played
      </h2>
      <dl className="stats-tiles">
        <div>
          <dt>Level</dt>
          <dd>{formatDepth(run.world, run.level)}</dd>
        </div>
        <div>
          <dt>Money</dt>
          <dd>{formatMoney(run.score)}</dd>
        </div>
        <div>
          <dt>Time</dt>
          <dd>{formatDuration(run.timeMillis)}</dd>
        </div>
        <div>
          <dt>Area</dt>
          <dd>{run.themeName}</dd>
        </div>
      </dl>

      {stickers.length > 0 && (
        <div className="stats-stickers">
          {played.length > 0 && (
            <p>
              <span className="stats-stickers-label">Character</span>
              {played.map((sticker) => (
                <span key={sticker.entityType} className="sticker">
                  {sticker.name}
                </span>
              ))}
            </p>
          )}
          {carried.length > 0 && (
            <p>
              <span className="stats-stickers-label">Items</span>
              {carried.map((sticker) => (
                <span key={sticker.entityType} className="sticker">
                  {sticker.name}
                </span>
              ))}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/** The save writes this as eight digits, `YYYYMMDD`. */
function formatDailyDate(raw: string | null): string {
  if (raw === null || raw.length !== 8) return "Never";
  const year = Number(raw.slice(0, 4));
  const month = Number(raw.slice(4, 6));
  const day = Number(raw.slice(6, 8));
  const date = new Date(year, month - 1, day);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Stands in for the two cards that need the save parsed. */
function DetailSkeleton() {
  return (
    <section className="stats-card" aria-busy="true">
      <h2 className="stats-heading">Deaths</h2>
      <div className="stats-grid" aria-hidden="true">
        <div className="skeleton-chart" />
        <div className="skeleton-chart" />
      </div>
    </section>
  );
}

/** The game's Player Profile, plus the parts it computes rather than
 *  stores. */
function ProfileCard({
  summary,
  stats,
}: {
  summary: SaveSummary;
  stats?: SaveStats | null;
}) {
  const wins = summary.winsNormal + summary.winsHard + summary.winsSpecial;

  // The game shows these four but does not store them. Average score is
  // over every run; average time is over wins, which is what makes it
  // "how long a completed run takes" rather than a meaningless number
  // dragged down by thousands of deaths in 1-1.
  const winPercent = summary.plays > 0 ? (wins / summary.plays) * 100 : 0;
  const averageScore =
    summary.plays > 0 ? Math.round(summary.scoreTotal / summary.plays) : 0;
  const averageTimeMillis = wins > 0 ? summary.timeTotalMillis / wins : 0;
  const deadliest = deadliestLevel(summary);

  const tiles: { label: string; value: string; title?: string }[] = [
    { label: "Plays", value: formatCount(summary.plays) },
    {
      label: "Wins",
      value: `${summary.winsNormal} / ${summary.winsHard} / ${summary.winsSpecial}`,
      title: "Normal / Hard / Cosmic Ocean",
    },
    { label: "Deaths", value: formatCount(summary.deaths) },
    { label: "Win %", value: `${winPercent.toFixed(2)}%` },
    { label: "Average score", value: formatMoney(averageScore) },
    { label: "Top score", value: formatMoney(summary.scoreTop) },
    {
      label: "Total money",
      value: formatMoney(summary.scoreTotal),
      title: "Every dollar collected, across every run",
    },
    {
      label: "Deepest level",
      value: formatDepth(summary.deepestArea, summary.deepestLevel),
      title:
        summary.deepestArea === 8
          ? "The save stores the Cosmic Ocean as world 8; the game shows it as 7"
          : undefined,
    },
    {
      label: "Deadliest level",
      value: deadliest ? formatDepth(deadliest.world, deadliest.level) : "-",
      title: deadliest
        ? `${formatCount(deadliest.deaths)} deaths there`
        : undefined,
    },
    {
      label: "Average time",
      value: wins > 0 ? formatDuration(averageTimeMillis) : "-",
      title: "Total time played, divided by completed runs",
    },
    {
      label: "Best time",
      value:
        summary.timeBestMillis > 0
          ? formatDuration(summary.timeBestMillis)
          : "-",
    },
    { label: "Time played", value: formatDuration(summary.timeTotalMillis) },
    {
      label: "Characters",
      value: `${summary.charactersUnlocked} / 20`,
    },
  ];
  if (stats) {
    tiles.push(
      {
        label: "Tutorial",
        value:
          stats.tutorialState >= 4 ? "Done" : `Step ${stats.tutorialState}`,
      },
      {
        label: "Tutorial time",
        value: formatDuration(stats.timeTutorialMillis),
        title: "Time spent in the camp tutorial",
      },
      { label: "Last daily", value: formatDailyDate(stats.lastDaily) },
    );
  }

  return (
    <section className="stats-card">
      <h2 className="stats-heading">Player profile</h2>
      <dl className="stats-tiles">
        {tiles.map((tile) => (
          <div key={tile.label} title={tile.title}>
            <dt>{tile.label}</dt>
            <dd>{tile.value}</dd>
          </div>
        ))}
      </dl>

      <ul className="stats-flags">
        <Flag on={summary.completedNormal} label="Normal ending" />
        <Flag on={summary.completedIronman} label="No shortcuts" />
        <Flag on={summary.completedHard} label="Hard ending" />
        <Flag on={summary.seededUnlocked} label="Seeded runs" />
      </ul>

      <div className="stats-split">
        <Shortcuts value={summary.shortcuts} />
        <Pets counts={summary.petsRescued} />
      </div>
    </section>
  );
}

/** Terra's quest as the nine deliveries it actually is.
 *
 *  The save keeps one number, and the obvious rendering is the one-line
 *  description of whatever step you are on. That hides the structure:
 *  three deliveries open a shortcut, three more open the next, three more
 *  the last. Drawn out, you can see at a glance how far off the next one
 *  is, which the sentence never told you. */
function Shortcuts({ value }: { value: number }) {
  const progress = shortcutProgress(value);

  return (
    <div className="stats-block">
      <h3 className="stats-block-head">
        Shortcuts
        <span>
          {progress.delivered} / {progress.total}
        </span>
      </h3>

      <ol className="shortcut-track">
        {progress.stages.map((stage, index) => (
          <li key={stage.opens} className="shortcut-stage">
            {/* The rail between groups, so three groups of three read as
                a sequence rather than nine loose dots. */}
            {index > 0 && (
              <span
                className={`shortcut-rail${progress.stages[index - 1].complete ? " done" : ""}`}
                aria-hidden="true"
              />
            )}
            <span className="shortcut-dots">
              {stage.deliveries.map((delivery) => (
                <span
                  key={delivery.label}
                  className={`shortcut-dot${delivery.done ? " done" : ""}`}
                  title={`${delivery.label}${delivery.done ? " (given)" : ""}`}
                />
              ))}
            </span>
            <span className={`shortcut-opens${stage.complete ? " done" : ""}`}>
              {stage.opens}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Rescue counts for the three pets.
 *
 *  Bars rather than three numbers in a sentence: they are counts of the
 *  same thing, so the interesting part is how they compare, and the game
 *  shows these nowhere at all. */
function Pets({ counts }: { counts: [number, number, number] }) {
  const most = Math.max(1, ...counts);
  const total = counts.reduce((sum, count) => sum + count, 0);

  return (
    <div className="stats-block">
      <h3 className="stats-block-head">
        Pets rescued
        <span>{formatCount(total)}</span>
      </h3>
      <ul className="pets">
        {PETS.map((name, index) => (
          <li key={name} className="pet">
            <span className="pet-name">{name}</span>
            <span className="pet-track">
              <span
                className="pet-fill"
                style={{ width: `${(counts[index] / most) * 100}%` }}
              />
            </span>
            <span className="pet-count">{formatCount(counts[index])}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Flag({ on, label }: { on: boolean; label: string }) {
  return (
    <li className={`stats-flag${on ? " on" : ""}`}>
      {on ? "✓" : "–"} {label}
    </li>
  );
}

/** Where deaths happen. The per-level histogram is the single most
 *  interesting thing in the save file, and the game shows only its
 *  maximum. */
function DeathsCard({ stats }: { stats: SaveStats }) {
  const [world, setWorld] = useState<number | null>(null);

  const byWorld: BarDatum[] = stats.summary.worldDeaths.map((w) => ({
    key: String(w.world),
    label: w.name,
    value: w.total,
  }));

  const byLevel: BarDatum[] = useMemo(() => {
    const rows = stats.summary.worldDeaths
      .filter((w) => world === null || w.world === world)
      .flatMap((w) =>
        w.levels.map((deaths, index) => ({
          world: w.world,
          level: index + 1,
          name: w.name,
          deaths,
        })),
      )
      // Levels the player has never died on would otherwise pad the
      // Cosmic Ocean's row out to 99 empty bars.
      .filter((row) => row.deaths > 0)
      .sort((a, b) => b.deaths - a.deaths);

    return rows.map((row) => ({
      key: `${row.world}-${row.level}`,
      label: formatDepth(row.world, row.level),
      value: row.deaths,
      detail: row.name,
    }));
  }, [stats, world]);

  const byCharacter: BarDatum[] = stats.characters
    .filter((c) => c.deaths > 0)
    .sort((a, b) => b.deaths - a.deaths)
    .map((c) => ({ key: String(c.index), label: c.name, value: c.deaths }));

  const deadliest = stats.journal
    .flatMap((c) => c.entries)
    .filter((e) => (e.killedBy ?? 0) > 0)
    .sort((a, b) => (b.killedBy ?? 0) - (a.killedBy ?? 0));

  const mostKilled = stats.journal
    .flatMap((c) => c.entries)
    .filter((e) => (e.killed ?? 0) > 0)
    .sort((a, b) => (b.killed ?? 0) - (a.killed ?? 0));

  return (
    <section className="stats-card">
      <h2 className="stats-heading">Deaths</h2>

      <div className="stats-grid">
        <BarList
          title="By world"
          data={byWorld}
          labelHeading="World"
          valueHeading="Deaths"
        />
        <BarList
          title="By level"
          data={byLevel}
          labelHeading="Level"
          valueHeading="Deaths"
          empty={
            world === null
              ? "No deaths recorded."
              : "No deaths recorded in this world."
          }
          action={
            <label className="chart-select">
              <span>World</span>
              <select
                value={world ?? ""}
                onChange={(e) =>
                  setWorld(
                    e.target.value === "" ? null : Number(e.target.value),
                  )
                }
              >
                <option value="">All</option>
                {stats.summary.worldDeaths.map((w) => (
                  <option key={w.world} value={w.world}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
          }
        />
      </div>

      <div className="stats-grid">
        <BarList
          title="As character"
          data={byCharacter}
          labelHeading="Character"
          valueHeading="Deaths"
        />
        <BarList
          title="By enemy"
          data={toBars(deadliest, (e) => e.killedBy ?? 0)}
          labelHeading="Entry"
          valueHeading="Killed you"
        />
      </div>

      <BarList
        title="Your kills"
        data={toBars(mostKilled, (e) => e.killed ?? 0)}
        labelHeading="Entry"
        valueHeading="Killed"
      />
    </section>
  );
}

function toBars(
  entries: EntryStat[],
  value: (e: EntryStat) => number,
): BarDatum[] {
  return entries.map((e) => ({
    key: `${e.name}-${e.index}`,
    label: e.name,
    value: value(e),
  }));
}

/** Journal completion, one meter per category. */
function JournalCard({ stats }: { stats: SaveStats }) {
  const [category, setCategory] = useState<string>(
    stats.journal[0]?.category ?? "",
  );
  const active = stats.journal.find((c) => c.category === category);
  const missing = active?.entries.filter((e) => !e.discovered) ?? [];

  return (
    <section className="stats-card">
      <h2 className="stats-heading">Journal</h2>
      <p className="stats-note">
        {formatCount(stats.summary.journalDiscovered)} of{" "}
        {formatCount(stats.summary.journalTotal)} entries discovered.
      </p>

      <ul className="stats-meters">
        {stats.journal.map((c) => {
          const percent = c.total > 0 ? (c.discovered / c.total) * 100 : 0;
          return (
            <li key={c.category}>
              <div className="stats-meter-head">
                <span>{c.label}</span>
                <span className="stats-meter-value">
                  {c.discovered} / {c.total}
                </span>
              </div>
              <div className="stats-meter-track">
                <div
                  className="stats-meter-fill"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>

      <div className="stats-filter">
        <label>
          <span>Still missing from</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {stats.journal.map((c) => (
              <option key={c.category} value={c.category}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {missing.length === 0 ? (
        <p className="stats-complete">
          {"✓"} {active?.label} is complete.
        </p>
      ) : (
        <ul className="stats-missing">
          {missing.map((e) => (
            <li key={e.index}>
              <span className="stats-missing-index">
                {String(e.index + 1).padStart(2, "0")}
              </span>
              {e.name}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** The world and level with the most deaths, which is what the game's
 *  profile screen calls "Deadliest Level". */
function deadliestLevel(
  summary: SaveSummary,
): { world: number; level: number; deaths: number } | null {
  let best: { world: number; level: number; deaths: number } | null = null;
  for (const world of summary.worldDeaths) {
    world.levels.forEach((deaths, index) => {
      if (deaths > 0 && (best === null || deaths > best.deaths)) {
        best = { world: world.world, level: index + 1, deaths };
      }
    });
  }
  return best;
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const v of Object.values(err)) {
      if (typeof v === "string") return v;
    }
    return JSON.stringify(err);
  }
  return String(err);
}
