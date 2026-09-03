// Grouping and filtering for the save lists.
//
// A snapshot archive grows on its own and never shrinks, so these lists
// are the one part of the feature that gets worse with use. Hundreds of
// rows of "2 runs, 596 deaths" all look alike, and scrolling through them
// gives you no idea where you are. Date headings restore that: you scroll
// to roughly when you remember, not to roughly how far down.

/** The minimum a row needs to be grouped and filtered. */
export interface GroupableSave {
  id: string;
  takenAtMs: number;
  description: string;
}

export interface SaveGroup<T> {
  /** Heading, e.g. "Today" or "March 2026". */
  label: string;
  saves: T[];
}

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Start of the local day `ms` falls in. */
function startOfDay(ms: number): number {
  const date = new Date(ms);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

/**
 * Buckets saves under date headings, newest first.
 *
 * The near past gets fine-grained headings and the distant past gets
 * coarse ones, because that is how people remember when something
 * happened: "this morning" or "some time in March", never "63 days ago".
 *
 * Input is assumed newest-first, which is the order the store returns.
 */
export function groupByDate<T extends GroupableSave>(
  saves: T[],
  now: number = Date.now(),
): SaveGroup<T>[] {
  const today = startOfDay(now);
  const groups: SaveGroup<T>[] = [];
  let current: SaveGroup<T> | null = null;

  for (const save of saves) {
    const label = labelFor(save.takenAtMs, today, now);
    if (current === null || current.label !== label) {
      current = { label, saves: [] };
      groups.push(current);
    }
    current.saves.push(save);
  }
  return groups;
}

function labelFor(ms: number, today: number, now: number): string {
  // A timestamp in the future (clock skew, or a file copied with its
  // original time) would otherwise fall through every branch below.
  if (ms > now) return "Just now";

  const day = startOfDay(ms);
  if (day === today) return "Today";
  if (day === today - DAY) return "Yesterday";
  if (today - day < 7 * DAY) return "Earlier this week";
  if (today - day < 30 * DAY) return "Earlier this month";

  const date = new Date(ms);
  const sameYear = new Date(now).getFullYear() === date.getFullYear();
  return date.toLocaleDateString(undefined, {
    month: "long",
    ...(sameYear ? {} : { year: "numeric" }),
  });
}

/**
 * Filters by a free-text query against the description and the date.
 *
 * Matching the rendered date as well as the description means "march" or
 * "2026" finds things, which is most of what anyone would type when
 * hunting through a year of automatic snapshots that all share the same
 * boilerplate description.
 */
export function filterSaves<T extends GroupableSave>(
  saves: T[],
  query: string,
): T[] {
  const needle = query.trim().toLowerCase();
  if (needle === "") return saves;
  return saves.filter((save) => {
    if (save.description.toLowerCase().includes(needle)) return true;
    const date = new Date(save.takenAtMs);
    const printed = `${date.toLocaleDateString()} ${date.toLocaleDateString(undefined, {
      month: "long",
      year: "numeric",
    })}`.toLowerCase();
    return printed.includes(needle);
  });
}
