import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import {
  AlertCircle,
  Check,
  FolderOpen,
  Loader2,
  Package,
  Play,
} from "lucide-react";
import {
  extractAssets,
  getExtractStatus,
  listExtractableExes,
  openDirectory,
  type ExtractOptions,
} from "../../lib/commands";
import { useToast } from "../shared/Toast";
import "./ExtractPage.css";

interface ProgressPayload {
  phase: string;
  detail: string | null;
  done: number | null;
  total: number | null;
}

const PHASE_LABELS: Record<string, string> = {
  preparing: "Preparing",
  "extracting-assets": "Extracting assets",
  "backing-up-exe": "Backing up game exe",
  "extracting-audio": "Extracting audio",
  "hashing-strings": "Generating string hashes",
  "loading-sprite-sheets": "Loading source sprite sheets",
  "generating-entity-sheets": "Generating entity sprites",
  done: "Extraction complete",
};

const DEFAULT_OPTIONS: ExtractOptions = {
  extractWav: false,
  extractOgg: false,
  reuseExtracted: false,
  generateStringHashes: true,
  createEntitySprites: true,
};

/** One row of the live phase list on the right column. */
interface PhaseEntry {
  phase: string;
  label: string;
  done: number | null;
  total: number | null;
  status: "running" | "complete";
}

type PageStatus = "loading" | "idle" | "running" | "success" | "error";

export function ExtractPage() {
  const toast = useToast();
  const [exes, setExes] = useState<string[]>([]);
  const [exe, setExe] = useState<string>("");
  const [options, setOptions] = useState<ExtractOptions>(DEFAULT_OPTIONS);
  const [status, setStatus] = useState<PageStatus>("loading");
  const [phases, setPhases] = useState<PhaseEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");
  // Track the currently-live phase key so a same-phase event only updates
  // its counter, and switching phase closes out the previous one as done.
  const currentPhaseRef = useRef<string | null>(null);

  const reloadExes = useCallback(async () => {
    setStatus("loading");
    try {
      const found = await listExtractableExes();
      setExes(found);
      // Prefer the top-level Spel2.exe (directly under install_dir) over any
      // deeper copies in DLC subdirs, then fall back to any Spel2.exe, then
      // to the first entry.
      const spel2Root = found.find((f) => f.toLowerCase() === "spel2.exe");
      const spel2Any = found.find((f) => f.toLowerCase().endsWith("spel2.exe"));
      setExe(spel2Root ?? spel2Any ?? found[0] ?? "");
      setStatus("idle");
    } catch (err) {
      toast.error(`Couldn't scan for exes: ${extractMessage(err)}`);
      setStatus("idle");
    }
  }, [toast]);

  useEffect(() => {
    void reloadExes();
  }, [reloadExes]);

  // Resume progress display if an extract was already running when this
  // component mounted (nav-away-and-back, hot reload, etc). The Rust
  // side mirrors phase + counter into a shared slot; we snapshot it on
  // mount and seed our phases array with a single "current" row. The
  // event listener then takes over from the next tick.
  useEffect(() => {
    let cancelled = false;
    getExtractStatus()
      .then((snap) => {
        if (cancelled || !snap) return;
        const label = PHASE_LABELS[snap.phase] ?? snap.phase;
        setStatus("running");
        setPhases([
          {
            phase: snap.phase,
            label,
            done: snap.done,
            total: snap.total,
            status: "running",
          },
        ]);
        currentPhaseRef.current = snap.phase;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const unlistenPromise = listen<ProgressPayload>(
      "extract-progress",
      (event) => {
        const { phase, done, total } = event.payload;
        const label = PHASE_LABELS[phase] ?? phase;
        // Decide whether this event opens a new phase row BEFORE the
        // setState updater runs, so React 18 StrictMode's dev double-
        // invocation of the updater sees the same closed-over decision
        // both times. Reading currentPhaseRef.current inside the updater
        // would let the two invocations diverge (the ref gets mutated
        // between them by any other event that fires in the same tick).
        const isNewPhase = currentPhaseRef.current !== phase;
        currentPhaseRef.current = phase;
        setPhases((prev) => {
          if (!isNewPhase) {
            // Same phase, update counter.
            return prev.map((p) =>
              p.phase === phase ? { ...p, done, total } : p,
            );
          }
          // New phase: mark previous running row as complete + append.
          return [
            ...prev.map((p) =>
              p.status === "running"
                ? { ...p, status: "complete" as const }
                : p,
            ),
            {
              phase,
              label,
              done,
              total,
              status:
                phase === "done"
                  ? ("complete" as const)
                  : ("running" as const),
            },
          ];
        });
      },
    );
    return () => {
      unlistenPromise.then((unlisten) => unlisten());
    };
  }, []);

  const handleExtract = async () => {
    if (!exe) {
      toast.error("Choose an exe first.");
      return;
    }
    setStatus("running");
    setErrorMessage("");
    setPhases([]);
    currentPhaseRef.current = null;
    try {
      await extractAssets(exe, options);
      // Ensure the last live phase gets marked complete even if the "done"
      // event was already swallowed by React batching.
      setPhases((prev) =>
        prev.map((p) =>
          p.status === "running" ? { ...p, status: "complete" as const } : p,
        ),
      );
      setStatus("success");
      toast.success("Extraction complete.");
    } catch (err) {
      const msg = extractMessage(err);
      setErrorMessage(msg);
      setStatus("error");
      toast.error(`Extract failed: ${msg}`);
    }
  };

  const handleOpenExtracted = async () => {
    try {
      await openDirectory("extracted");
    } catch (err) {
      toast.error(extractMessage(err));
    }
  };

  const runDisabled = status !== "idle" && status !== "success" && status !== "error";
  const canRun = !!exe && !runDisabled;

  return (
    <div className="extract-page">
      <header className="extract-header">
        <div className="extract-header-copy">
          <h2 className="extract-title">Extract Assets</h2>
          <p className="extract-subtitle">
            Extract assets from Spel2.exe into Mods/Extracted. Some features, such as the level editor, require these assets to be present. You can also use this to generate entity sprite sheets for mods.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-ghost extract-header-btn"
          onClick={() => void handleOpenExtracted()}
        >
          <FolderOpen size={14} aria-hidden="true" />
          <span>Open Extracted folder</span>
        </button>
      </header>

      <div className="extract-body">
        {/* --- Left: source + options ---------------------------------- */}
        <div className="extract-config">
          <section className="extract-section">
            <div className="extract-section-title">Source exe</div>
            {status === "loading" ? (
              <p className="extract-hint">Scanning...</p>
            ) : exes.length === 0 ? (
              <p className="extract-hint">
                No .exe files found under the install directory. Check the
                install dir in Settings.
              </p>
            ) : (
              <div className="extract-exe-row">
                <select
                  value={exe}
                  onChange={(e) => setExe(e.target.value)}
                  disabled={status === "running"}
                >
                  {exes.map((e) => (
                    <option key={e} value={e}>
                      {e}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => void reloadExes()}
                  disabled={status === "running"}
                >
                  Rescan
                </button>
              </div>
            )}
          </section>

          <section className="extract-section">
            <div className="extract-section-title">Options</div>
            <OptionRow
              checked={options.generateStringHashes}
              disabled={status === "running"}
              onChange={(v) =>
                setOptions((o) => ({ ...o, generateStringHashes: v }))
              }
              label="Generate string hashes"
              hint="Writes strings*_hashed.str to reference for targeted string mods."
            />
            <OptionRow
              checked={options.createEntitySprites}
              disabled={status === "running"}
              onChange={(v) =>
                setOptions((o) => ({ ...o, createEntitySprites: v }))
              }
              label="Create entity sprite sheets"
              hint="Writes per-entity PNGs under Data/Textures/Entities."
            />
            <OptionRow
              checked={options.extractWav}
              disabled={status === "running"}
              onChange={(v) => setOptions((o) => ({ ...o, extractWav: v }))}
              label="Extract .wav from soundbank."
              hint="These are typically the sound effects."
            />
            <OptionRow
              checked={options.extractOgg}
              disabled={status === "running"}
              onChange={(v) => setOptions((o) => ({ ...o, extractOgg: v }))}
              label="Extract .ogg from soundbank"
              hint="These are typically the music tracks."
            />
            <OptionRow
              checked={options.reuseExtracted}
              disabled={status === "running"}
              onChange={(v) =>
                setOptions((o) => ({ ...o, reuseExtracted: v }))
              }
              label="Reuse extracted assets"
              hint="Skip binary extraction, run the other options against the last extracted output."
            />
          </section>

          <div className="extract-actions">
            <button
              type="button"
              className="btn btn-primary extract-run"
              onClick={() => void handleExtract()}
              disabled={!canRun}
            >
              {status === "running" ? (
                <>
                  <Loader2
                    size={14}
                    className="extract-spin"
                    aria-hidden="true"
                  />
                  <span>Extracting...</span>
                </>
              ) : (
                <>
                  <Play size={14} aria-hidden="true" />
                  <span>Extract</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* --- Right: status ------------------------------------------- */}
        <div className="extract-status">
          <StatusPanel
            status={status}
            phases={phases}
            errorMessage={errorMessage}
          />
        </div>
      </div>
    </div>
  );
}

interface OptionRowProps {
  checked: boolean;
  disabled: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint: string;
}

function OptionRow({
  checked,
  disabled,
  onChange,
  label,
  hint,
}: OptionRowProps) {
  return (
    <label className={`extract-option${disabled ? " disabled" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <div className="extract-option-copy">
        <span className="extract-option-label">{label}</span>
        <span className="extract-option-hint">{hint}</span>
      </div>
    </label>
  );
}

function StatusPanel({
  status,
  phases,
  errorMessage,
}: {
  status: PageStatus;
  phases: PhaseEntry[];
  errorMessage: string;
}) {
  if (status === "idle" || status === "loading") {
    return (
      <div className="extract-status-idle">
        <div className="extract-status-icon idle">
          <Package size={26} aria-hidden="true" />
        </div>
        <div className="extract-status-heading">Ready to extract</div>
        <p className="extract-status-body">
          Choose which artifacts to write, then hit Extract. Progress will
          show up here per phase.
        </p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="extract-status-error">
        <div className="extract-status-error-head">
          <AlertCircle size={16} aria-hidden="true" />
          <span>Extraction failed</span>
        </div>
        <pre className="extract-status-error-body">{errorMessage}</pre>
      </div>
    );
  }

  return (
    <>
      <div className="extract-status-heading">
        {status === "success"
          ? "Extraction complete"
          : "Extraction in progress"}
      </div>
      <ol className="extract-phase-list">
        {phases.map((p) => (
          <PhaseRow key={p.phase} entry={p} />
        ))}
        {phases.length === 0 && (
          <li className="extract-phase-placeholder">Waiting for the first phase...</li>
        )}
      </ol>
    </>
  );
}

function PhaseRow({ entry }: { entry: PhaseEntry }) {
  const pct =
    entry.total && entry.total > 0 && entry.done !== null
      ? Math.min(100, Math.round((entry.done / entry.total) * 100))
      : null;
  return (
    <li className={`extract-phase extract-phase-${entry.status}`}>
      <span className="extract-phase-glyph" aria-hidden="true">
        {entry.status === "complete" ? (
          <Check size={12} />
        ) : (
          <Loader2 size={12} className="extract-spin" />
        )}
      </span>
      <div className="extract-phase-body">
        <div className="extract-phase-row">
          <span className="extract-phase-label">{entry.label}</span>
          {entry.done !== null && entry.total !== null && entry.total > 0 && (
            <span className="extract-phase-count">
              {entry.done} / {entry.total}
            </span>
          )}
        </div>
        {entry.status === "running" && (
          <div className="extract-phase-track">
            <div
              className={`extract-phase-fill${pct === null ? " extract-phase-fill-indeterminate" : ""}`}
              style={pct === null ? undefined : { width: `${pct}%` }}
            />
          </div>
        )}
      </div>
    </li>
  );
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
