// Everything that configures the snapshotter, in one place.
//
// The schedule and the retention policy live here rather than above the
// snapshot list, where two controls nobody touches twice a year would
// cost the list a chunk of its height. The list keeps only the on/off
// switch, the one thing worth a click from the card itself.
//
// Retention is the part that needs explaining rather than just exposing:
//
//   - each tier says in plain words what its number means, so nobody has
//     to know what "weekly = 4" does to their archive
//   - the effect on the archive they actually have is shown live, so the
//     answer to "what will this delete" is on screen before they commit
//
// The presets exist because most people want one of three shapes and
// should not have to derive them.

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  previewRetention,
  type RetentionPolicy,
  type RetentionPreview,
  type SnapshotSettings,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { Switch } from "../shared/Switch";
import "./SnapshotSettingsModal.css";

/** How often the snapshotter may capture. */
export const INTERVAL_CHOICES = [
  // `label` names the schedule for the picker; `every` completes the
  // sentence "at most one every ___", which the two readings of "daily"
  // cannot both do.
  { hours: 1, label: "Hourly", every: "hour" },
  { hours: 6, label: "Every 6 hours", every: "6 hours" },
  { hours: 12, label: "Every 12 hours", every: "12 hours" },
  { hours: 24, label: "Daily", every: "day" },
  { hours: 24 * 7, label: "Weekly", every: "week" },
];

/** The tiers, with what each number actually means. */
const TIERS: {
  key: keyof RetentionPolicy;
  label: string;
  describe: (n: number) => string;
}[] = [
  {
    key: "hourly",
    label: "Hourly",
    describe: (n) =>
      `the last snapshot of each of the past ${plural(n, "hour")}`,
  },
  {
    key: "daily",
    label: "Daily",
    describe: (n) => `one a day for the past ${plural(n, "day")}`,
  },
  {
    key: "weekly",
    label: "Weekly",
    describe: (n) => `one a week for the past ${plural(n, "week")}`,
  },
  {
    key: "monthly",
    label: "Monthly",
    describe: (n) => `one a month for the past ${plural(n, "month")}`,
  },
  {
    key: "yearly",
    label: "Yearly",
    describe: (n) => `one a year for the past ${plural(n, "year")}`,
  },
];

const PRESETS: { name: string; hint: string; policy: RetentionPolicy }[] = [
  {
    name: "Balanced",
    hint: "A day of hourly, then thinning out to a couple of years",
    policy: { hourly: 24, daily: 7, weekly: 4, monthly: 12, yearly: 2 },
  },
  {
    name: "Recent only",
    hint: "The last few days, and nothing older",
    policy: { hourly: 12, daily: 7, weekly: 0, monthly: 0, yearly: 0 },
  },
  {
    name: "Long history",
    hint: "Fewer recent, but a decade of coverage",
    policy: { hourly: 6, daily: 7, weekly: 8, monthly: 24, yearly: 10 },
  },
];

interface SnapshotSettingsModalProps {
  open: boolean;
  settings: SnapshotSettings;
  onClose: () => void;
  /** Saves the settings. `prune` asks for the retention policy to be
   *  applied straight away rather than at the next capture. */
  onSave: (settings: SnapshotSettings, prune: boolean) => void;
}

export function SnapshotSettingsModal({
  open,
  settings,
  onClose,
  onSave,
}: SnapshotSettingsModalProps) {
  const [draft, setDraft] = useState<SnapshotSettings>(settings);
  const [preview, setPreview] = useState<RetentionPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);

  // Reopening should always start from what is actually saved, not from
  // whatever was abandoned last time.
  // Keyed on `open` alone. `settings` is a fresh object on every
  // background refresh, and the snapshotter refreshes whenever it
  // captures - re-seeding on that would wipe half-typed retention tiers
  // with no visible cause.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (open) setDraft(settings);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setPreviewing(true);
    previewRetention(draft.retention)
      .then((result) => {
        if (!cancelled) setPreview(result);
      })
      .catch(() => {
        if (!cancelled) setPreview(null);
      })
      .finally(() => {
        if (!cancelled) setPreviewing(false);
      });
    return () => {
      cancelled = true;
    };
  }, [draft.retention, open]);

  const setTier = useCallback((key: keyof RetentionPolicy, value: number) => {
    setDraft((current) => ({
      ...current,
      retention: {
        ...current.retention,
        policy: {
          ...current.retention.policy,
          [key]: Math.max(0, Math.min(999, value)),
        },
      },
    }));
  }, []);

  const { keepAll, policy } = draft.retention;
  const matchesPreset = (candidate: RetentionPolicy) =>
    TIERS.every((tier) => policy[tier.key] === candidate[tier.key]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Snapshot settings"
      size="lg"
      footer={
        <>
          <button type="button" className="saves-btn" onClick={onClose}>
            Cancel
          </button>
          {preview !== null && preview.pruned > 0 && !keepAll && (
            <button
              type="button"
              className="saves-btn saves-btn-danger"
              onClick={() => onSave(draft, true)}
            >
              Save and prune {preview.pruned} now
            </button>
          )}
          <button
            type="button"
            className="saves-btn saves-btn-primary"
            onClick={() => onSave(draft, false)}
          >
            Save
          </button>
        </>
      }
    >
      <label className="settings-row">
        <span className="settings-row-label">How often</span>
        <select
          value={draft.intervalHours}
          onChange={(e) =>
            setDraft((current) => ({
              ...current,
              intervalHours: Number(e.target.value),
            }))
          }
        >
          {INTERVAL_CHOICES.map((choice) => (
            <option key={choice.hours} value={choice.hours}>
              {choice.label}
            </option>
          ))}
        </select>
        <span className="settings-row-hint">
          At most one snapshot every {describeInterval(draft.intervalHours)},
          and only when the save has actually changed.
        </span>
      </label>

      <hr className="settings-rule" />

      <h3 className="settings-heading">Retention</h3>
      <p className="settings-copy">
        Pruning doesn't delete the snapshot. It removes the full save file but
        keeps a summary that can be used for stats over time.
      </p>

      <div className="settings-keep-all">
        <Switch
          label="Keep every snapshot"
          checked={keepAll}
          onChange={(next) =>
            setDraft((current) => ({
              ...current,
              retention: { ...current.retention, keepAll: next },
            }))
          }
        />
        <p className="settings-hint">About 5 MB a year at a daily snapshot.</p>
      </div>

      <fieldset className="settings-tiers" disabled={keepAll}>
        <legend>Keep</legend>
        {TIERS.map((tier) => {
          const value = policy[tier.key];
          return (
            <label key={tier.key} className="settings-tier">
              <span className="settings-tier-label">{tier.label}</span>
              <input
                type="number"
                min={0}
                max={999}
                value={value}
                onChange={(e) => setTier(tier.key, Number(e.target.value))}
              />
              <span className="settings-tier-hint">
                {value === 0 ? "off" : tier.describe(value)}
              </span>
            </label>
          );
        })}
      </fieldset>

      <div className="settings-preview" aria-live="polite">
        <h4>
          What this does to your archive
          {previewing && (
            <Loader2 size={12} className="settings-spin" aria-hidden="true" />
          )}
        </h4>
        {preview === null ? (
          <p className="settings-hint">Could not read your snapshots.</p>
        ) : preview.restorable === 0 && preview.historyOnly === 0 ? (
          <p className="settings-hint">
            No snapshots yet, so there is nothing to prune.
          </p>
        ) : (
          <>
            <p className="settings-counts">
              <strong>{preview.kept}</strong> of {preview.restorable} snapshots
              keep their save file
              {preview.pruned > 0 && (
                <>
                  , <strong>{preview.pruned}</strong> become stats-only
                </>
              )}
              .
            </p>
            {preview.historyOnly > 0 && (
              <p className="settings-hint">
                {preview.historyOnly} already stats-only, and unaffected.
              </p>
            )}
            <p className="settings-hint">
              Roughly {formatSize(preview.kept)} of save files kept.
              {preview.pruned > 0 &&
                " Saving applies this at the next snapshot; use Save and prune to do it now."}
            </p>
          </>
        )}
      </div>

      <div className="settings-presets">
        <span className="settings-presets-label">Presets</span>
        {PRESETS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            className={`settings-preset${!keepAll && matchesPreset(preset.policy) ? " active" : ""}`}
            title={preset.hint}
            onClick={() =>
              setDraft((current) => ({
                ...current,
                retention: { keepAll: false, policy: { ...preset.policy } },
              }))
            }
          >
            {preset.name}
          </button>
        ))}
      </div>
    </Modal>
  );
}

/** Completes "at most one every ___". */
export function describeInterval(hours: number): string {
  const choice = INTERVAL_CHOICES.find((c) => c.hours === hours);
  if (choice) return choice.every;
  return `${hours} hours`;
}

/** Saves are a fixed 13.9 KB, so a count converts straight to a size. */
function formatSize(count: number): string {
  const bytes = count * 13862;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function plural(n: number, unit: string): string {
  return `${n} ${unit}${n === 1 ? "" : "s"}`;
}
