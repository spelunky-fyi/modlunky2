// Formatting helpers for the Saves tab.
//
// These live apart from the page because they are the parts worth testing
// on their own: the save file stores times as frame counts and money as
// raw integers, and both read badly unless converted.

/** A count with thousands separators. */
export function formatCount(value: number): string {
  return value.toLocaleString();
}

/** Money, as the game shows it. */
export function formatMoney(value: number): string {
  return `$${value.toLocaleString()}`;
}

/**
 * A duration in milliseconds, at the coarsest useful precision.
 *
 * Total play time runs to hundreds of hours, while a single run is
 * usually a couple of minutes, so one fixed format cannot serve both.
 * Under a minute keeps the seconds; past an hour the seconds are noise.
 */
export function formatDuration(millis: number): string {
  if (!Number.isFinite(millis) || millis <= 0) return "0s";
  const totalSeconds = Math.floor(millis / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${formatCount(hours)}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

/** A file size. Saves are always a few kilobytes, but the archive folder
 *  as a whole can add up. */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * An epoch-millisecond timestamp, as a date and time in the user's locale.
 *
 * Recent times are given relatively, because "3 hours ago" is what
 * someone scanning a snapshot list actually wants to know. Anything older
 * than a day gets the real date, where the exact day matters more than
 * the elapsed time.
 */
export function formatTimestamp(ms: number, now: number = Date.now()): string {
  const elapsed = now - ms;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (elapsed < 0) return new Date(ms).toLocaleString();
  if (elapsed < minute) return "just now";
  if (elapsed < hour) {
    const minutes = Math.floor(elapsed / minute);
    return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  }
  if (elapsed < day) {
    const hours = Math.floor(elapsed / hour);
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  }
  return new Date(ms).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * The world number the Cosmic Ocean is stored under.
 *
 * The game displays it as world 7 instead. See {@link formatDepth}.
 */
export const COSMIC_OCEAN_AREA = 8;

/**
 * A depth as the game writes it on screen, e.g. "7-99".
 *
 * The save stores the Cosmic Ocean as world 8, but every screen in the
 * game calls it 7: the profile's "Deepest Level" reads 7-99 for a save
 * holding 8/99. Displaying the stored number would leave people unable to
 * reconcile this page with their own profile, so the translation happens
 * here, at the last possible moment. The stored value is never rewritten.
 */
export function formatDepth(area: number, level: number): string {
  const shown = area === COSMIC_OCEAN_AREA ? 7 : area;
  return `${shown}-${level}`;
}

/**
 * A depth with the area it belongs to, for tooltips and table cells.
 *
 * Worth the extra words because the display convention makes "7-5"
 * ambiguous on its own: it could be Sunken City or the Cosmic Ocean, and
 * only the name settles it.
 */
export function describeDepth(area: number, level: number, areaName: string): string {
  return `${formatDepth(area, level)} (${areaName})`;
}
