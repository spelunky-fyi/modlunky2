// Level Sequence side panel: shows the pack's playthrough in order, lets
// the user drag entries to reorder, add a level from the pack that isn't
// in the sequence yet, or remove one. Edits are held in the parent as a
// `pendingSequence` list of file_names so the top-bar Save flushes them
// into level_configuration.ls alongside per-entry edits.
//
// Layout mirrors the Mods page: two columns side by side, Available on
// the left, Sequence on the right. Click "+" to add; click "x" to
// remove. Reorder inside the right column with the drag handle.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { CSS } from "@dnd-kit/utilities";
import { CheckCircle2, Download, GripVertical, Plus, X } from "lucide-react";
import { useToast } from "../shared/Toast";
import {
  checkLatestLevelSequence,
  getLevelSequenceStatus,
  installLevelSequence,
  listCustomLevels,
  type LevelConfigurations,
  type LevelSequenceStatus,
} from "../../lib/commands";
import "./SequencePanel.css";

interface Props {
  pack: string;
  /** Pack's config as last read from disk. Only sequence.file_name is
   *  consulted; per-entry display data (name/identifier) isn't shown in
   *  the panel to keep rows scannable when packs use file-name-derived
   *  labels (which is most of them). */
  config: LevelConfigurations | null;
  /** Ordered list of file_names representing the pending sequence. Null
   *  means "no pending change; use config.sequence as-is". */
  pendingSequence: string[] | null;
  onChangePendingSequence: (next: string[] | null) => void;
  /** Currently open file; the row for it gets a highlight so users can spot
   *  where they are without scanning names. */
  currentFileName: string | null;
}

export function SequencePanel({
  pack,
  config,
  pendingSequence,
  onChangePendingSequence,
  currentFileName,
}: Props) {
  // Effective sequence: pending override wins over disk state.
  const sequence = useMemo<string[]>(() => {
    if (pendingSequence) return pendingSequence;
    return (config?.sequence ?? []).map((e) => e.file_name);
  }, [config, pendingSequence]);
  const sequenceSet = useMemo(() => new Set(sequence), [sequence]);

  const [availableFiles, setAvailableFiles] = useState<string[] | null>(null);
  const [filesError, setFilesError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setFilesError(null);
    listCustomLevels(pack)
      .then((f) => {
        if (!cancelled) setAvailableFiles(f);
      })
      .catch((err) => {
        if (!cancelled) setFilesError(extractMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [pack]);

  // Files present on disk but not in the sequence yet, alphabetized so
  // long packs stay scannable.
  const notInSequence = useMemo(() => {
    if (!availableFiles) return [];
    const filtered = availableFiles.filter((f) => !sequenceSet.has(f));
    filtered.sort((a, b) => a.localeCompare(b));
    return filtered;
  }, [availableFiles, sequenceSet]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const from = sequence.indexOf(String(active.id));
      const to = sequence.indexOf(String(over.id));
      if (from < 0 || to < 0) return;
      onChangePendingSequence(arrayMove(sequence, from, to));
    },
    [sequence, onChangePendingSequence],
  );

  const handleRemove = useCallback(
    (fileName: string) => {
      onChangePendingSequence(sequence.filter((f) => f !== fileName));
    },
    [sequence, onChangePendingSequence],
  );

  const handleAdd = useCallback(
    (fileName: string) => {
      // Idempotent: if it was already there for any reason, don't duplicate.
      if (sequenceSet.has(fileName)) return;
      onChangePendingSequence([...sequence, fileName]);
    },
    [sequence, sequenceSet, onChangePendingSequence],
  );

  const hasPending = pendingSequence !== null;
  const loading = availableFiles === null && !filesError;

  return (
    <div className="seq-panel">
      <div className="seq-panel-topbar">
        <p className="seq-panel-hint">
          Order in which the game will load levels. Runtime uses{" "}
          <code>level_configuration.ls</code> and the Level Sequence Lua
          library.
        </p>
        <button
          type="button"
          className="seq-panel-revert"
          onClick={() => onChangePendingSequence(null)}
          title="Discard the pending sequence changes and re-show the saved order"
          disabled={!hasPending}
          aria-hidden={!hasPending}
          data-visible={hasPending ? "yes" : "no"}
        >
          Revert changes
        </button>
      </div>

      {filesError && <div className="seq-panel-error">{filesError}</div>}

      <div className="seq-panel-grid">
        {/* --- Left: files available to add ------------------------------ */}
        <section className="seq-col">
          <header className="seq-col-header">
            <span className="seq-col-title">Available</span>
            <span className="seq-col-count">
              {loading ? "..." : notInSequence.length}
            </span>
          </header>
          <div className="seq-col-body">
            {loading ? (
              <div className="seq-col-empty">Loading pack levels...</div>
            ) : notInSequence.length === 0 ? (
              <div className="seq-col-empty">
                All pack levels are already in the sequence.
              </div>
            ) : (
              <ul className="seq-col-list">
                {notInSequence.map((fileName) => (
                  <AvailableRow
                    key={fileName}
                    fileName={fileName}
                    onAdd={() => handleAdd(fileName)}
                  />
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* --- Right: files in sequence order --------------------------- */}
        <section className="seq-col">
          <header className="seq-col-header">
            <span className="seq-col-title">Sequence</span>
            <span className="seq-col-count">{sequence.length}</span>
          </header>
          <div className="seq-col-body">
            {sequence.length === 0 ? (
              <div className="seq-col-empty">
                No levels yet. Add one from the left to get the playthrough
                started.
              </div>
            ) : (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                modifiers={[restrictToVerticalAxis]}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={sequence}
                  strategy={verticalListSortingStrategy}
                >
                  <ol className="seq-col-list">
                    {sequence.map((fileName, i) => (
                      <SequenceRow
                        key={fileName}
                        fileName={fileName}
                        order={i + 1}
                        isCurrent={currentFileName === fileName}
                        onRemove={() => handleRemove(fileName)}
                      />
                    ))}
                  </ol>
                </SortableContext>
              </DndContext>
            )}
          </div>
        </section>
      </div>

      <LevelSequenceLibrarySection pack={pack} />
    </div>
  );
}

// --- LevelSequence Lua library section -------------------------------------

/**
 * Install / update status for the LevelSequence Lua library inside the
 * pack. Reads the current install on mount and lets the user check for
 * updates + install with one click. The library ships as a versioned
 * GitHub release; the download URL is composed by the backend.
 */
function LevelSequenceLibrarySection({ pack }: { pack: string }) {
  const toast = useToast();
  const [status, setStatus] = useState<LevelSequenceStatus | null>(null);
  const [latest, setLatest] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [installing, setInstalling] = useState(false);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await getLevelSequenceStatus(pack);
      setStatus(s);
    } catch (err) {
      toast.error(`Library status failed: ${extractMessage(err)}`);
    }
  }, [pack, toast]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const handleCheck = useCallback(async () => {
    setChecking(true);
    try {
      const tag = await checkLatestLevelSequence();
      setLatest(tag);
    } catch (err) {
      toast.error(`Check failed: ${extractMessage(err)}`);
    } finally {
      setChecking(false);
    }
  }, [toast]);

  const handleInstall = useCallback(async () => {
    setInstalling(true);
    try {
      const tag = await installLevelSequence(pack);
      setLatest(tag);
      await refreshStatus();
      toast.success(`Installed LevelSequence ${tag}.`);
    } catch (err) {
      toast.error(`Install failed: ${extractMessage(err)}`);
    } finally {
      setInstalling(false);
    }
  }, [pack, refreshStatus, toast]);

  // Derive labels + call-to-action from the (installed, latest) tuple.
  const isInstalled = status?.folderExists ?? false;
  const installedVersion = status?.installedVersion ?? null;
  const hasUpdate =
    isInstalled &&
    installedVersion !== null &&
    latest !== null &&
    latest !== installedVersion;
  const upToDate =
    isInstalled &&
    installedVersion !== null &&
    latest !== null &&
    latest === installedVersion;

  const installLabel = !isInstalled
    ? "Install"
    : hasUpdate
      ? `Update to ${latest}`
      : installedVersion === null
        ? "Overwrite"
        : "Reinstall";

  return (
    <section className="seq-panel-library">
      <div className="seq-panel-library-head">
        <div className="seq-panel-library-title">Level Sequence library</div>
        <StatusPill
          installed={isInstalled}
          installedVersion={installedVersion}
          upToDate={upToDate}
          hasUpdate={hasUpdate}
        />
      </div>
      {!isInstalled && (
        <p className="seq-panel-library-desc">
          The Lua runtime that plays this pack's sequence. Install it into
          the pack so <code>main.lua</code> can find it at load.
        </p>
      )}
      {isInstalled && installedVersion === null && (
        <p className="seq-panel-library-desc">
          Installed, but no version marker found. It may be managed
          externally (e.g. via git). Overwriting will replace it with the
          version the editor tracks.
        </p>
      )}
      <div className="seq-panel-library-actions">
        <button
          type="button"
          className="seq-panel-library-btn"
          onClick={() => void handleCheck()}
          disabled={checking}
          title="Check GitHub for the latest release"
        >
          {checking ? "Checking..." : "Check for updates"}
        </button>
        <button
          type="button"
          className="seq-panel-library-btn primary"
          onClick={() => void handleInstall()}
          disabled={installing}
        >
          <Download size={14} aria-hidden="true" />
          <span>{installing ? "Installing..." : installLabel}</span>
        </button>
      </div>
    </section>
  );
}

function StatusPill({
  installed,
  installedVersion,
  upToDate,
  hasUpdate,
}: {
  installed: boolean;
  installedVersion: string | null;
  upToDate: boolean;
  hasUpdate: boolean;
}) {
  if (!installed) {
    return <span className="seq-panel-library-pill missing">Not installed</span>;
  }
  if (upToDate) {
    return (
      <span className="seq-panel-library-pill uptodate">
        <CheckCircle2 size={12} aria-hidden="true" />
        <span>Up to date ({installedVersion})</span>
      </span>
    );
  }
  if (hasUpdate) {
    return (
      <span className="seq-panel-library-pill update">
        Update available ({installedVersion})
      </span>
    );
  }
  return (
    <span className="seq-panel-library-pill installed">
      {installedVersion ?? "Managed externally"}
    </span>
  );
}

// --- Rows -----------------------------------------------------------------

interface AvailableRowProps {
  fileName: string;
  onAdd: () => void;
}

function AvailableRow({ fileName, onAdd }: AvailableRowProps) {
  return (
    <li className="seq-row available">
      <span className="seq-row-file">{fileName}</span>
      <button
        type="button"
        className="seq-row-add"
        onClick={onAdd}
        aria-label={`Add ${fileName} to sequence`}
        title="Add to sequence"
      >
        <Plus size={14} aria-hidden="true" />
      </button>
    </li>
  );
}

interface SequenceRowProps {
  fileName: string;
  order: number;
  isCurrent: boolean;
  onRemove: () => void;
}

function SequenceRow({
  fileName,
  order,
  isCurrent,
  onRemove,
}: SequenceRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: fileName });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : undefined,
    zIndex: isDragging ? 1 : undefined,
  };
  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`seq-row sequence${isCurrent ? " current" : ""}${isDragging ? " dragging" : ""}`}
    >
      <button
        type="button"
        className="seq-row-handle"
        aria-label={`Drag ${fileName}`}
        {...attributes}
        {...listeners}
      >
        <GripVertical size={14} aria-hidden="true" />
      </button>
      <span className="seq-row-order">{order}</span>
      <span className="seq-row-file">{fileName}</span>
      <button
        type="button"
        className="seq-row-remove"
        onClick={onRemove}
        aria-label={`Remove ${fileName} from sequence`}
        title="Remove from sequence (keeps the file + config entry)"
      >
        <X size={14} aria-hidden="true" />
      </button>
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
