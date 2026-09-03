// The inputs every editor section is built from.
//
// Two things here are less obvious than they look.
//
// Numbers keep their draft as a string. An input bound to a number cannot
// hold "" or "-" or "01", so a field that parses on every keystroke fights
// the user: clearing it snaps back to 0, and a minus sign vanishes before
// the digits arrive. These keep the text the user typed and report the
// parsed value alongside it, committing on blur.
//
// Times are stored as frames. Nobody thinks in frames, so they are shown
// as a clock and parsed back. The save also uses -1 as "no time set",
// which is not the same as zero and has to survive a round trip.

import { useEffect, useId, useRef, useState } from "react";

/** Frames per second the game runs at. */
const FPS = 60;

/** A labelled row, the shape every field in here takes. */
export function Field({
  label,
  hint,
  htmlFor,
  children,
  wide,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: React.ReactNode;
  /** Lets the control take the full row rather than sitting in a column. */
  wide?: boolean;
}) {
  return (
    <div className={`ed-field${wide ? " wide" : ""}`}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {hint && <p className="ed-hint">{hint}</p>}
    </div>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  hint?: string;
  /** Marks the field as changed from what the save held. */
  dirty?: boolean;
}

/**
 * A whole number.
 *
 * The draft is a string so the field can be empty or half-typed without
 * the value underneath lurching around. It commits on every valid
 * keystroke, so the rest of the editor stays live, but a draft that does
 * not parse leaves the last good value in place and shows the field as
 * invalid rather than silently writing a zero.
 */
export function NumberField({
  label,
  value,
  onChange,
  min = 0,
  max = 2147483647,
  hint,
  dirty,
}: NumberFieldProps) {
  const id = useId();
  const [draft, setDraft] = useState(String(value));
  // Only re-seed when the value changed from outside, or typing would be
  // overwritten by the round trip through the parent.
  const lastCommitted = useRef(value);
  useEffect(() => {
    if (value !== lastCommitted.current) {
      lastCommitted.current = value;
      setDraft(String(value));
    }
  }, [value]);

  const parsed = Number(draft);
  const valid =
    draft.trim() !== "" &&
    Number.isInteger(parsed) &&
    parsed >= min &&
    parsed <= max;

  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        className={`ed-input${valid ? "" : " invalid"}${dirty ? " dirty" : ""}`}
        value={draft}
        onChange={(e) => {
          const next = e.target.value;
          setDraft(next);
          const n = Number(next);
          if (next.trim() !== "" && Number.isInteger(n) && n >= min && n <= max) {
            lastCommitted.current = n;
            onChange(n);
          }
        }}
        onBlur={() => {
          // Put the field back to the value that is actually stored, so a
          // draft that never parsed does not sit there looking committed.
          if (!valid) setDraft(String(lastCommitted.current));
        }}
      />
    </Field>
  );
}

/**
 * A 64-bit number, which stays a string the whole way down.
 *
 * `score_total` and `time_total` are `i64` in the file. Passing them
 * through a JavaScript number would round anything past 2^53, and this is
 * precisely the field someone types twenty digits into.
 */
export function BigNumberField({
  label,
  value,
  onChange,
  hint,
  dirty,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  hint?: string;
  dirty?: boolean;
}) {
  const id = useId();
  const valid = /^-?\d+$/.test(value.trim()) && fitsInI64(value.trim());

  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        className={`ed-input${valid ? "" : " invalid"}${dirty ? " dirty" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  );
}

/** Whether a digit string is inside the range the file's field can hold. */
function fitsInI64(raw: string): boolean {
  try {
    const n = BigInt(raw);
    return n >= -(2n ** 63n) && n <= 2n ** 63n - 1n;
  } catch {
    return false;
  }
}

/**
 * A duration the save stores as a frame count.
 *
 * Shown as `h:mm:ss.mmm` because that is how the game shows times and how
 * a person would say one. The stored -1 means "no time set" and is kept
 * as an empty field: writing it as 0 would claim a zero-second run, which
 * is a different and much more interesting lie.
 */
export function TimeField({
  label,
  frames,
  onChange,
  hint,
  dirty,
}: {
  label: string;
  frames: number;
  onChange: (next: number) => void;
  hint?: string;
  dirty?: boolean;
}) {
  const id = useId();
  const [draft, setDraft] = useState(() => framesToClock(frames));
  const lastCommitted = useRef(frames);
  useEffect(() => {
    if (frames !== lastCommitted.current) {
      lastCommitted.current = frames;
      setDraft(framesToClock(frames));
    }
  }, [frames]);

  const parsed = clockToFrames(draft);
  const valid = parsed !== null;

  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <input
        id={id}
        type="text"
        className={`ed-input${valid ? "" : " invalid"}${dirty ? " dirty" : ""}`}
        value={draft}
        placeholder="0:00:00.000"
        onChange={(e) => {
          setDraft(e.target.value);
          const next = clockToFrames(e.target.value);
          if (next !== null) {
            lastCommitted.current = next;
            onChange(next);
          }
        }}
        onBlur={() => {
          if (!valid) setDraft(framesToClock(lastCommitted.current));
        }}
      />
    </Field>
  );
}

/** Renders a frame count as `h:mm:ss.mmm`. -1 is "unset" and shows empty. */
export function framesToClock(frames: number): string {
  if (frames < 0) return "";
  const totalMs = Math.round((frames * 1000) / FPS);
  const ms = totalMs % 1000;
  const totalSeconds = Math.floor(totalMs / 1000);
  const seconds = totalSeconds % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (n: number, width = 2) => String(n).padStart(width, "0");
  return `${hours}:${pad(minutes)}:${pad(seconds)}.${pad(ms, 3)}`;
}

/**
 * Parses `h:mm:ss.mmm` back to frames. Empty means the -1 the save uses
 * for "no time"; anything unparseable is null so the caller can refuse it.
 *
 * Accepts fewer parts than it prints, since typing `1:30` for a minute and
 * a half is the obvious thing to try.
 */
export function clockToFrames(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return -1;
  if (!/^\d+(:\d{1,2}){0,2}(\.\d{1,3})?$/.test(trimmed)) return null;

  const [clock, fraction = ""] = trimmed.split(".");
  const parts = clock.split(":").map(Number);
  if (parts.some((part) => !Number.isFinite(part))) return null;
  // Read right to left, so "90" is 90 seconds and "1:30" is 90 seconds.
  let seconds = 0;
  for (const part of parts) seconds = seconds * 60 + part;
  const ms = Number(fraction.padEnd(3, "0"));
  const frames = Math.round(((seconds * 1000 + ms) * FPS) / 1000);
  return frames > 2147483647 ? null : frames;
}

/** A checkbox that looks like the rest of the editor. */
export function CheckField({
  label,
  checked,
  onChange,
  hint,
  dirty,
  disabled,
  title,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  hint?: string;
  dirty?: boolean;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <label
      className={`ed-check${dirty ? " dirty" : ""}${disabled ? " disabled" : ""}`}
      title={title}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="ed-check-body">
        <span className="ed-check-label">{label}</span>
        {hint && <span className="ed-check-hint">{hint}</span>}
      </span>
    </label>
  );
}

/** A picker over a fixed list, valued by index. */
export function SelectField({
  label,
  value,
  options,
  onChange,
  hint,
  dirty,
}: {
  label: string;
  value: number;
  options: string[];
  onChange: (next: number) => void;
  hint?: string;
  dirty?: boolean;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <select
        id={id}
        className={`ed-input${dirty ? " dirty" : ""}`}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {options.map((option, index) => (
          <option key={option + String(index)} value={index}>
            {option}
          </option>
        ))}
      </select>
    </Field>
  );
}

/** A section heading with an optional aside on the right. */
export function SectionHead({
  title,
  blurb,
  aside,
}: {
  title: string;
  blurb?: string;
  aside?: React.ReactNode;
}) {
  return (
    <header className="ed-section-head">
      <div>
        <h3>{title}</h3>
        {blurb && <p>{blurb}</p>}
      </div>
      {aside}
    </header>
  );
}
