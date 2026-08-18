// Ordering rules for the Mods page's inactive list, and the relative-time
// wording that explains the result on each row.
//
// Split out of ModsPage so it can be tested without mounting a component:
// these are pure functions over Mod, and a couple of them encode decisions
// that are easy to undo by accident (see the comments on compareMods and the
// `used` arm below).
//
// Only the inactive column is ordered this way. The active column is
// Playlunky's load_order.txt, whose order is data the game reads rather than
// a view, so it is left exactly as the user dragged it.

import type { Mod, ModSort } from "../types/mods";

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 60 * 60 * 1000],
  ["month", 30 * 24 * 60 * 60 * 1000],
  ["week", 7 * 24 * 60 * 60 * 1000],
  ["day", 24 * 60 * 60 * 1000],
  ["hour", 60 * 60 * 1000],
  ["minute", 60 * 1000],
];

/**
 * "3 days ago", "yesterday", "just now".
 *
 * Uses the platform formatter so the wording follows the user's locale
 * rather than hard-coded English. `now` is injectable so callers under test
 * don't depend on the wall clock.
 */
export function relativeTime(ms: number, now: number = Date.now()): string {
  const fmt = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const elapsed = now - ms;
  for (const [unit, size] of RELATIVE_UNITS) {
    if (elapsed >= size) return fmt.format(-Math.floor(elapsed / size), unit);
  }
  return "just now";
}

/** Display name shown in the row, which is what alphabetical should follow. */
export function displayName(mod: Mod): string {
  return mod.manifest?.name ?? mod.id;
}

/** Case-insensitive and numeric-aware, so "Mod 2" precedes "Mod 10". */
export function byName(a: Mod, b: Mod): number {
  return displayName(a).localeCompare(displayName(b), undefined, {
    sensitivity: "base",
    numeric: true,
  });
}

/** Ascending comparison on `sort`'s field alone, with no tie-break. */
export function compareBySort(a: Mod, b: Mod, sort: ModSort): number {
  switch (sort) {
    case "installed":
      return a.modifiedAt - b.modifiedAt;
    // Never-used mods count as older than anything that has been used, so
    // descending puts them last rather than at the top, where they'd bury
    // the mods this sort exists to surface.
    case "used":
      return (a.lastUsedAt ?? 0) - (b.lastUsedAt ?? 0);
    case "name":
      return byName(a, b);
  }
}

/**
 * Full ordering: the chosen field in the chosen direction, then name as the
 * tie-break.
 *
 * The tie-break is deliberately outside the direction flip. Reversing it too
 * would order equal timestamps Z-A, and timestamp ties are common -- every
 * mod that has never been used shares one, as does everything installed in
 * the same operation.
 */
export function compareMods(
  a: Mod,
  b: Mod,
  sort: ModSort,
  descending: boolean,
): number {
  const primary = compareBySort(a, b, sort) * (descending ? -1 : 1);
  return primary || byName(a, b);
}

/** Convenience for the list itself: a new array in display order. */
export function sortMods(
  mods: Mod[],
  sort: ModSort,
  descending: boolean,
): Mod[] {
  return [...mods].sort((a, b) => compareMods(a, b, sort, descending));
}
