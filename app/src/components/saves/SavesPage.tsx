// The Saves tab.
//
// Three things share this page, in the order someone reaches for them:
// what the live save currently holds, the saves they have deliberately
// kept, and the automatic snapshot history.
//
// Restoring is the only destructive action here, so it never happens on a
// single click. Picking Restore opens a preview that asks the backend what
// would actually change, and the backend compares the two saves' lifetime
// counters rather than their timestamps: a save archived more recently is
// not necessarily the one with more progress in it. The confirm step
// defaults to backing up the save it is about to replace.

import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import {
  AlertTriangle,
  Archive,
  Camera,
  FileDown,
  Check,
  Clock,
  FolderOpen,
  Pencil,
  SlidersHorizontal,
  LineChart,
  ListTree,
  RotateCcw,
  Search,
  Settings2,
  Trash2,
} from "lucide-react";
import {
  applyRetentionNow,
  createManagedSave,
  deleteStoredSave,
  getSaveStatus,
  getSnapshotSettings,
  listManagedSaves,
  listSaveSnapshots,
  openSavesFolder,
  previewSaveRestore,
  renameStoredSave,
  restoreStoredSave,
  setSnapshotSettings,
  type RestorePreview,
  type SaveStatus,
  type SaveSummary,
  type SnapshotSettings,
  type SaveRef,
  type StoredSave,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { Switch } from "../shared/Switch";
import {
  SnapshotSettingsModal,
  describeInterval,
} from "./SnapshotSettingsModal";
import { SaveDetailsModal, type SaveDetailsTarget } from "./SaveDetailsModal";
import { OverTimeModal } from "./OverTimeModal";
import { SaveEditorModal } from "./editor/SaveEditorModal";
import { TextPromptModal } from "./TextPromptModal";
import { ImportModal, pickSaveFiles } from "./ImportModal";
import { useToast } from "../shared/Toast";
import { filterSaves, groupByDate } from "./grouping";
import {
  formatBytes,
  formatCount,
  formatDepth,
  formatDuration,
  formatMoney,
  formatTimestamp,
} from "./format";
import "./SavesPage.css";

/** Emitted by the backend snapshotter after it archives a save. */
const SNAPSHOT_TAKEN_EVENT = "save-snapshot-taken";

export function SavesPage() {
  const toast = useToast();
  // Each of these is its own request, and `null` means it has not landed
  // yet. Reading the live save is one 14 KB file; listing the archive
  // parses every save in it, which at several hundred snapshots is two
  // orders of magnitude slower. Waiting for all of them to hold back the
  // fast one made the whole page feel as slow as its slowest part.
  const [status, setStatus] = useState<SaveStatus | null>(null);
  const [managed, setManaged] = useState<StoredSave[] | null>(null);
  const [snapshots, setSnapshots] = useState<StoredSave[] | null>(null);
  const [settings, setSettings] = useState<SnapshotSettings | null>(null);
  const [busy, setBusy] = useState(false);

  const [describing, setDescribing] = useState(false);
  const [renaming, setRenaming] = useState<StoredSave | null>(null);
  const [preview, setPreview] = useState<RestorePreview | null>(null);
  const [backupFirst, setBackupFirst] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState<StoredSave | null>(null);
  const [editingSettings, setEditingSettings] = useState(false);
  const [details, setDetails] = useState<SaveDetailsTarget | null>(null);
  /** The files being imported, once some have been picked. */
  const [importing, setImporting] = useState<string[]>([]);
  /** Which save the editor is open on, if any. */
  const [editing, setEditing] = useState<{
    source: SaveRef;
    title: string;
  } | null>(null);
  const [overTime, setOverTime] = useState(false);

  const reload = useCallback(async () => {
    const failed = (err: unknown) =>
      toast.error(`Couldn't read your saves: ${extractMessage(err)}`);

    // Each result is applied the moment it arrives rather than at the end,
    // so the page fills in from fastest to slowest. Awaiting them all
    // together still lets callers know when a refresh has settled, which
    // is what the action handlers need.
    //
    // Note that a refresh never resets these back to null: that would
    // replace a list someone is looking at with a skeleton, which is a
    // worse flash than a moment of slightly stale data.
    await Promise.allSettled([
      getSaveStatus().then(setStatus, failed),
      getSnapshotSettings().then(setSettings, failed),
      listManagedSaves().then(setManaged, failed),
      listSaveSnapshots().then(setSnapshots, failed),
    ]);
  }, [toast]);

  useEffect(() => {
    void reload();
  }, [reload]);

  // The snapshotter runs on its own schedule, so an open tab would
  // otherwise show a stale list until something else refreshed it.
  useEffect(() => {
    const unlisten = listen(SNAPSHOT_TAKEN_EVENT, () => {
      void reload();
    });
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, [reload]);

  const onArchive = useCallback(
    async (text: string) => {
      setBusy(true);
      try {
        const created = await createManagedSave(text);
        setDescribing(false);
        toast.success("Save archived.");
        // Splice the new record in rather than re-listing the archive.
        // The backend just handed it back, and re-reading several hundred
        // saves to learn what we already know is the slow way round.
        setManaged((current) => [created, ...(current ?? [])]);
        void getSaveStatus().then(setStatus, () => {});
      } catch (err) {
        toast.error(extractMessage(err));
      } finally {
        setBusy(false);
      }
    },
    [toast],
  );

  const onRename = useCallback(
    async (text: string) => {
      if (!renaming) return;
      setBusy(true);
      try {
        const updated = await renameStoredSave(renaming.id, text);
        setRenaming(null);
        // Renaming changes one row's description and nothing else, so
        // replace that row instead of re-reading the whole archive.
        const replace = (list: StoredSave[] | null) =>
          list?.map((save) => (save.id === updated.id ? updated : save)) ??
          null;
        setManaged(replace);
        setSnapshots(replace);
      } catch (err) {
        toast.error(extractMessage(err));
      } finally {
        setBusy(false);
      }
    },
    [renaming, toast],
  );

  const onDelete = useCallback(async () => {
    if (!confirmDelete) return;
    setBusy(true);
    try {
      await deleteStoredSave(confirmDelete.id);
      const gone = confirmDelete.id;
      setConfirmDelete(null);
      // Same reasoning as rename: one row left, so drop one row.
      const without = (list: StoredSave[] | null) =>
        list?.filter((save) => save.id !== gone) ?? null;
      setManaged(without);
      setSnapshots(without);
    } catch (err) {
      toast.error(extractMessage(err));
    } finally {
      setBusy(false);
    }
  }, [confirmDelete, toast]);

  /** Opens the details of an archived save.
   *
   *  A pruned snapshot has no save left to parse, so it falls back to the
   *  summary that was baked into its record; the modal says as much
   *  rather than pretending the detail is missing by accident. */
  const openManagedFolder = useCallback(
    () => void openSavesFolder("managed"),
    [],
  );
  const openSnapshotsFolder = useCallback(
    () => void openSavesFolder("snapshots"),
    [],
  );
  const openSettings = useCallback(() => setEditingSettings(true), []);

  // The picker opens first and the modal only once a file is chosen: a
  // modal that appears and then opens a file dialog on top of itself is
  // two dialogs deep for one decision.
  const startImport = useCallback(async () => {
    try {
      const picked = await pickSaveFiles();
      if (picked.length > 0) setImporting(picked);
    } catch (err) {
      toast.error(extractMessage(err));
    }
  }, [toast]);
  const startRename = useCallback(
    (stored: StoredSave) => setRenaming(stored),
    [],
  );
  const startEdit = useCallback(
    (stored: StoredSave) =>
      setEditing({
        source: { kind: "stored", id: stored.id },
        title: stored.description || "this save",
      }),
    [],
  );

  const openDetails = useCallback((stored: StoredSave) => {
    setDetails({
      title: stored.description || "Untitled save",
      subtitle: `Archived ${formatTimestamp(stored.takenAtMs)}`,
      summary: stored.summary,
      source: stored.restorable
        ? { kind: "stored", id: stored.id }
        : { kind: "summaryOnly" },
    });
  }, []);

  const onAskRestore = useCallback(
    async (stored: StoredSave) => {
      setBusy(true);
      try {
        const next = await previewSaveRestore(stored.id);
        // Default the backup on whenever there is something worth keeping.
        setBackupFirst(next.hasCurrentSave);
        setPreview(next);
      } catch (err) {
        toast.error(extractMessage(err));
      } finally {
        setBusy(false);
      }
    },
    [toast],
  );

  const onConfirmRestore = useCallback(async () => {
    if (!preview) return;
    setBusy(true);
    try {
      const backup = await restoreStoredSave(preview.stored.id, backupFirst);
      setPreview(null);
      toast.success(
        backup
          ? "Save restored. The one it replaced was archived first."
          : "Save restored.",
      );
      await reload();
    } catch (err) {
      toast.error(extractMessage(err));
    } finally {
      setBusy(false);
    }
  }, [backupFirst, preview, reload, toast]);

  const updateSettings = useCallback(
    async (next: SnapshotSettings, prune = false) => {
      // Optimistic: the control should not lag behind the click, and a
      // failed write is reported and then reconciled by the reload.
      setSettings(next);
      try {
        setSettings(await setSnapshotSettings(next));
        if (prune) {
          const pruned = await applyRetentionNow();
          toast.success(
            pruned === 1
              ? "1 snapshot reduced to stats only."
              : `${pruned} snapshots reduced to stats only.`,
          );
          await reload();
        }
      } catch (err) {
        toast.error(extractMessage(err));
        await reload();
      }
    },
    [reload, toast],
  );

  const snapshotSwitch = useMemo(
    () =>
      settings && (
        <Switch
          label="Snapshot automatically"
          hideLabel
          checked={settings.enabled}
          onChange={(enabled) => void updateSettings({ ...settings, enabled })}
          title={
            settings.enabled
              ? `Snapshotting automatically, at most one every ${describeInterval(settings.intervalHours)}`
              : "Snapshot automatically"
          }
        />
      ),
    [settings, updateSettings],
  );

  return (
    <div className="manage">
      <CurrentSaveCard
        status={status}
        onSnapshot={() => setDescribing(true)}
        onDetails={() => {
          if (!status?.summary) return;
          setDetails({
            title: "Current save",
            subtitle: status.path ?? "",
            summary: status.summary,
            source: { kind: "live" },
          });
        }}
        onOverTime={() => setOverTime(true)}
        onEdit={() =>
          setEditing({ source: { kind: "live" }, title: "the current save" })
        }
      />

      <div className="manage-columns">
        <SaveList
          title="Save Management"
          icon={<Archive size={15} aria-hidden="true" />}
          saves={managed}
          filterable
          empty="Nothing archived yet."
          busy={busy}
          onRestore={onAskRestore}
          onRename={startRename}
          onEdit={startEdit}
          onDelete={setConfirmDelete}
          onOpenFolder={openManagedFolder}
          onImport={() => void startImport()}
          onOpen={openDetails}
        />

        <SaveList
          title="Snapshots"
          icon={<Clock size={15} aria-hidden="true" />}
          saves={snapshots}
          empty={
            settings?.enabled
              ? "None yet. The first is taken shortly after your save next changes."
              : "Snapshotting is off. Turn it on to keep a rolling history."
          }
          skeletonRows={8}
          busy={busy}
          onRestore={onAskRestore}
          onRename={startRename}
          onEdit={startEdit}
          onDelete={setConfirmDelete}
          onOpenFolder={openSnapshotsFolder}
          onOpen={openDetails}
          headerControl={snapshotSwitch}
          onSettings={settings ? openSettings : undefined}
        />
      </div>

      <TextPromptModal
        open={describing}
        title="Archive this save"
        label="Description"
        initialValue=""
        placeholder=""
        hint="Optional."
        confirmLabel="Archive"
        busy={busy}
        onCancel={() => setDescribing(false)}
        onConfirm={onArchive}
      />

      <TextPromptModal
        open={renaming !== null}
        title="Rename"
        label="Description"
        initialValue={renaming?.description ?? ""}
        confirmLabel="Save"
        busy={busy}
        onCancel={() => setRenaming(null)}
        onConfirm={onRename}
      />

      <RestoreModal
        preview={preview}
        backupFirst={backupFirst}
        busy={busy}
        onBackupChange={setBackupFirst}
        onClose={() => setPreview(null)}
        onConfirm={() => void onConfirmRestore()}
      />

      <ImportModal
        paths={importing}
        onClose={() => setImporting([])}
        onImported={() => {
          // Imports are filed under each save's own date, so they land
          // anywhere in the list rather than at the top. Re-reading is
          // the only way to get the order right.
          void listManagedSaves().then(setManaged, () => {});
        }}
      />

      <SaveDetailsModal target={details} onClose={() => setDetails(null)} />

      {editing && (
        <SaveEditorModal
          open
          source={editing.source}
          title={editing.title}
          onClose={() => setEditing(null)}
          onSaved={() => {
            // A write changes the file and leaves a backup behind, so
            // both the status card and the managed library are stale.
            void getSaveStatus().then(setStatus, () => {});
            void listManagedSaves().then(setManaged, () => {});
          }}
        />
      )}
      <OverTimeModal open={overTime} onClose={() => setOverTime(false)} />

      {settings && (
        <SnapshotSettingsModal
          open={editingSettings}
          settings={settings}
          onClose={() => setEditingSettings(false)}
          onSave={(next, prune) => {
            setEditingSettings(false);
            void updateSettings(next, prune);
          }}
        />
      )}

      <Modal
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        title="Delete this save?"
        footer={
          <>
            <button
              type="button"
              className="saves-btn"
              onClick={() => setConfirmDelete(null)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="saves-btn saves-btn-danger"
              onClick={() => void onDelete()}
              disabled={busy}
            >
              Delete
            </button>
          </>
        }
      >
        <p className="saves-modal-copy">
          {confirmDelete?.description || "This archived save"} will be removed
          from disk. Your live save is not affected.
        </p>
      </Modal>
    </div>
  );
}

/** The live save: where it is, when it changed, and what is in it. */
function CurrentSaveCard({
  status,
  onSnapshot,
  onDetails,
  onOverTime,
  onEdit,
}: {
  status: SaveStatus | null;
  onSnapshot: () => void;
  onDetails: () => void;
  onOverTime: () => void;
  onEdit: () => void;
}) {
  // `null` means the read has not come back yet, which is emphatically
  // not the same as "no install directory configured". Conflating them
  // flashed a warning about Settings on every single load, which is
  // alarming and wrong.
  if (status === null) {
    return (
      <section className="saves-card saves-current" aria-busy="true">
        <div className="saves-current-head">
          <div className="saves-current-copy">
            <h2>Current save</h2>
            <p className="saves-meta" aria-hidden="true">
              <span
                className="skeleton-bar skeleton-bar-sub"
                style={{ width: 160 }}
              />
            </p>
          </div>
        </div>
        <dl className="saves-stats" aria-hidden="true">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i}>
              <dt>
                <span
                  className="skeleton-bar skeleton-bar-sub"
                  style={{ width: "70%" }}
                />
              </dt>
              <dd>
                <span className="skeleton-bar" style={{ width: "55%" }} />
              </dd>
            </div>
          ))}
        </dl>
      </section>
    );
  }

  if (!status.path) {
    return (
      <section className="saves-card saves-card-warning">
        <AlertTriangle size={16} aria-hidden="true" />
        <p>Set your Spelunky 2 install directory in Settings to use Saves.</p>
      </section>
    );
  }

  if (!status.exists) {
    return (
      <section className="saves-card saves-card-warning">
        <AlertTriangle size={16} aria-hidden="true" />
        <p>
          No save at <code>{status.path}</code> yet. Play once and it will
          appear.
        </p>
      </section>
    );
  }

  return (
    <section className="saves-card saves-current">
      <div className="saves-current-head">
        <div className="saves-current-copy">
          <h2>Current save</h2>
          <p className="saves-meta" title={status.path}>
            {status.modifiedAtMs !== null && (
              <>Changed {formatTimestamp(status.modifiedAtMs)}</>
            )}
            {status.fileSize !== null && (
              <> &middot; {formatBytes(status.fileSize)}</>
            )}
          </p>
        </div>
        {/* This card doubles as the page header, so it carries the
            page-level actions too. "Over time" is about the archive
            rather than this save, which is a stretch, but a whole
            toolbar row to hold one button is a worse trade. */}
        <div className="saves-current-actions">
          <button
            type="button"
            className="saves-btn"
            onClick={onOverTime}
            title="Charts built from past saves"
          >
            <LineChart size={14} aria-hidden="true" />
            Over time
          </button>
          <button
            type="button"
            className="saves-btn"
            onClick={onDetails}
            disabled={!status.summary}
            title="Everything in this save"
          >
            <ListTree size={14} aria-hidden="true" />
            Details
          </button>
          <button
            type="button"
            className="saves-btn"
            onClick={onEdit}
            disabled={!status.summary}
            title="Change what is in this save"
          >
            <SlidersHorizontal size={14} aria-hidden="true" />
            Edit
          </button>
          <button
            type="button"
            className="saves-btn saves-btn-primary"
            onClick={onSnapshot}
          >
            <Camera size={14} aria-hidden="true" />
            Archive this save
          </button>
        </div>
      </div>

      {status.error ? (
        <p className="saves-error">
          <AlertTriangle size={14} aria-hidden="true" />
          This save could not be read: {status.error}
        </p>
      ) : (
        status.summary && <SummaryStats summary={status.summary} />
      )}
    </section>
  );
}

/** The handful of numbers worth showing at a glance. The full breakdown is
 *  the Stats panel's job. */
function SummaryStats({ summary }: { summary: SaveSummary }) {
  const stats = useMemo(
    () => [
      { label: "Runs", value: formatCount(summary.plays) },
      { label: "Deaths", value: formatCount(summary.deaths) },
      {
        label: "Wins",
        value: `${summary.winsNormal}N / ${summary.winsHard}H / ${summary.winsSpecial}CO`,
      },
      {
        label: "Deepest",
        value: formatDepth(summary.deepestArea, summary.deepestLevel),
      },
      {
        label: "Journal",
        value: `${summary.journalDiscovered}/${summary.journalTotal}`,
      },
      { label: "Characters", value: `${summary.charactersUnlocked}/20` },
      { label: "Time played", value: formatDuration(summary.timeTotalMillis) },
      { label: "Best money", value: formatMoney(summary.scoreTop) },
    ],
    [summary],
  );

  return (
    <>
      <dl className="saves-stats">
        {stats.map((stat) => (
          <div key={stat.label}>
            <dt>{stat.label}</dt>
            <dd>{stat.value}</dd>
          </div>
        ))}
      </dl>
      {!summary.checksumValid && (
        <p className="saves-error">
          <AlertTriangle size={14} aria-hidden="true" />
          This save's checksum does not match its contents. The game may reject
          it.
        </p>
      )}
    </>
  );
}

/** Placeholder rows shown while a listing is in flight.
 *
 *  Shaped like the real rows rather than a generic spinner, so the card
 *  keeps its size and the eye already knows where the content will be.
 *  Hidden from assistive tech, which gets `aria-busy` on the region
 *  instead of a description of some grey boxes. */
function SkeletonRows({ count }: { count: number }) {
  return (
    <div className="saves-scroll" aria-busy="true" aria-hidden="true">
      <div className="skeleton-head" />
      <ul className="saves-list">
        {Array.from({ length: count }, (_, i) => (
          <li key={i} className="saves-row skeleton-row">
            <div className="saves-row-main">
              {/* Varying widths, so it reads as a list of different
                  things rather than as a loading bar. */}
              <span
                className="skeleton-bar"
                style={{ width: `${52 + ((i * 17) % 34)}%` }}
              />
              <span
                className="skeleton-bar skeleton-bar-sub"
                style={{ width: `${64 + ((i * 11) % 22)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Memoized, because the page re-renders for reasons this list does not
 *  care about - a modal opening, an action running - and reconciling
 *  several hundred rows every time is what made the page feel heavy.
 *  Every prop it takes is a stable identity from the page above. */
const SaveList = memo(function SaveList({
  title,
  icon,
  saves,
  empty,
  busy,
  skeletonRows = 6,
  filterable,
  headerControl,
  onRestore,
  onRename,
  onEdit,
  onDelete,
  onOpenFolder,
  onSettings,
  onImport,
  onOpen,
}: {
  title: string;
  icon: React.ReactNode;
  /** `null` while the listing is still in flight, which draws skeleton
   *  rows instead of an empty state. An empty array really means empty. */
  saves: StoredSave[] | null;
  empty: string;
  busy: boolean;
  /** How many skeleton rows to draw while loading. Roughly what the box
   *  will hold, so the card does not visibly resize when data lands. */
  skeletonRows?: number;
  /** Offers a filter box once the list is long enough to need one.
   *
   *  Off for snapshots: they are all called "Automatic snapshot", so
   *  filtering by name has nothing to bite on, and the date headings
   *  already make scrolling to a rough point quick. */
  filterable?: boolean;
  /** A control for the title bar, beside the heading. */
  headerControl?: React.ReactNode;
  onRestore: (stored: StoredSave) => void;
  onRename: (stored: StoredSave) => void;
  onEdit: (stored: StoredSave) => void;
  onDelete: (stored: StoredSave) => void;
  onOpenFolder: () => void;
  onSettings?: () => void;
  /** Copies a save file in from elsewhere. Absent on the snapshot list,
   *  which is the snapshotter's to fill. */
  onImport?: () => void;
  /** Opens a save's details. The row's text is the button, so the
   *  action buttons beside it stay separately clickable and the whole
   *  thing keeps working from the keyboard. */
  onOpen: (stored: StoredSave) => void;
}) {
  const [query, setQuery] = useState("");
  const loading = saves === null;
  const rows = saves ?? [];
  const showFilter = filterable === true && rows.length > 8;

  // Grouped rather than paged. A snapshot archive only grows, and every
  // row in it looks like every other row, so the useful question is "when"
  // rather than "which page". Date headings answer that while scrolling.
  const groups = useMemo(
    () => groupByDate(showFilter ? filterSaves(rows, query) : rows),
    [rows, query, showFilter],
  );
  const matched = groups.reduce(
    (total, group) => total + group.saves.length,
    0,
  );

  return (
    <section className="saves-card saves-list-card">
      <div className="saves-list-head">
        <h2>
          {icon}
          {title}
          {loading ? (
            <span
              className="saves-count saves-count-loading"
              aria-hidden="true"
            />
          ) : (
            <span className="saves-count">{formatCount(rows.length)}</span>
          )}
        </h2>
        {headerControl}
        <div className="saves-list-actions">
          {onImport && (
            <button
              type="button"
              className="saves-icon-btn"
              onClick={onImport}
              aria-label="Import a save"
              title="Copy a save file in from elsewhere"
            >
              <FileDown size={14} aria-hidden="true" />
            </button>
          )}
          {onSettings && (
            <button
              type="button"
              className="saves-icon-btn"
              onClick={onSettings}
              aria-label={`${title} settings`}
              title="Settings"
            >
              <Settings2 size={14} aria-hidden="true" />
            </button>
          )}
          <button
            type="button"
            className="saves-icon-btn"
            onClick={onOpenFolder}
            aria-label={`Open the ${title} folder`}
            title="Open this folder"
          >
            <FolderOpen size={14} aria-hidden="true" />
          </button>
        </div>
      </div>

      {showFilter && (
        <div className="saves-search">
          <Search size={13} aria-hidden="true" />
          <input
            type="search"
            value={query}
            placeholder="Filter by name or date"
            aria-label={`Filter ${title}`}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query !== "" && (
            <span className="saves-search-count">
              {formatCount(matched)} of {formatCount(rows.length)}
            </span>
          )}
        </div>
      )}

      {loading ? (
        <SkeletonRows count={skeletonRows} />
      ) : rows.length === 0 ? (
        <p className="saves-empty">{empty}</p>
      ) : matched === 0 ? (
        <p className="saves-empty">Nothing matches "{query}".</p>
      ) : (
        <div className="saves-scroll">
          {groups.map((group) => (
            <div key={group.label} className="saves-group">
              <h3 className="saves-group-head">
                {group.label}
                <span>{formatCount(group.saves.length)}</span>
              </h3>
              <ul className="saves-list">
                {group.saves.map((stored) => (
                  <li key={stored.id} className="saves-row">
                    <button
                      type="button"
                      className="saves-row-main saves-row-open"
                      onClick={() => onOpen(stored)}
                      title="View this save's details"
                    >
                      <span className="saves-row-title">
                        {/* The name needs its own box to be truncated in:
                            `text-overflow` does nothing to the children of
                            a flex container, so putting the ellipsis on
                            the row above let a long name push the whole
                            column wider. */}
                        <span className="saves-row-name">
                          {stored.description || <em>No description</em>}
                        </span>
                        {/* The two kinds Modlunky archives on your
                            behalf are tagged, so a copy you did not ask
                            for is never mistaken for one you did. */}
                        {stored.kind === "preRestore" && (
                          <span
                            className="saves-tag"
                            title="Archived automatically before a restore"
                          >
                            pre-restore
                          </span>
                        )}
                        {stored.kind === "imported" && (
                          <span
                            className="saves-tag"
                            title={`Copied in from ${stored.sourcePath}`}
                          >
                            imported
                          </span>
                        )}
                        {stored.kind === "preEdit" && (
                          <span
                            className="saves-tag"
                            title="Archived automatically before the editor wrote to this save"
                          >
                            pre-edit
                          </span>
                        )}
                        {!stored.restorable && (
                          <span
                            className="saves-tag saves-tag-quiet"
                            title="The save file was pruned. Its stats are kept for the history charts."
                          >
                            stats only
                          </span>
                        )}
                      </span>
                      <span className="saves-row-meta">
                        {formatTimestamp(stored.takenAtMs)} &middot;{" "}
                        {formatCount(stored.summary.plays)} runs &middot;{" "}
                        {formatDepth(
                          stored.summary.deepestArea,
                          stored.summary.deepestLevel,
                        )}
                      </span>
                    </button>
                    <div className="saves-row-actions">
                      {/* A pruned record has no save file, so restoring
                          and editing are not disabled - they are absent.
                          A greyed-out button invites a click and then
                          explains itself; nothing to click says the same
                          thing without the detour. The row's own tag
                          already says why. */}
                      {stored.restorable && (
                        <>
                          <button
                            type="button"
                            className="saves-btn saves-btn-quiet"
                            disabled={busy}
                            onClick={() => onRestore(stored)}
                          >
                            <RotateCcw size={13} aria-hidden="true" />
                            Restore
                          </button>
                          <button
                            type="button"
                            className="saves-icon-btn"
                            aria-label="Edit"
                            title="Change what is in this save"
                            disabled={busy}
                            onClick={() => onEdit(stored)}
                          >
                            <SlidersHorizontal size={13} aria-hidden="true" />
                          </button>
                        </>
                      )}
                      <button
                        type="button"
                        className="saves-icon-btn"
                        aria-label="Rename"
                        title="Rename"
                        disabled={busy}
                        onClick={() => onRename(stored)}
                      >
                        <Pencil size={13} aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        className="saves-icon-btn saves-icon-danger"
                        aria-label="Delete"
                        title="Delete"
                        disabled={busy}
                        onClick={() => onDelete(stored)}
                      >
                        <Trash2 size={13} aria-hidden="true" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
});

/** The restore confirmation.
 *
 *  This is the whole safety story of the feature, so it says plainly what
 *  would be lost rather than asking "are you sure?". */
function RestoreModal({
  preview,
  backupFirst,
  busy,
  onBackupChange,
  onClose,
  onConfirm,
}: {
  preview: RestorePreview | null;
  backupFirst: boolean;
  busy: boolean;
  onBackupChange: (next: boolean) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!preview) return null;
  const { comparison, losesProgress, identical, hasCurrentSave, stored } =
    preview;

  return (
    <Modal
      open
      onClose={onClose}
      title="Restore this save?"
      size="lg"
      footer={
        <>
          <button type="button" className="saves-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className={`saves-btn ${losesProgress ? "saves-btn-danger" : "saves-btn-primary"}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {losesProgress ? "Restore anyway" : "Restore"}
          </button>
        </>
      }
    >
      <p className="saves-modal-copy">
        <strong>{stored.description || "This archived save"}</strong>, from{" "}
        {formatTimestamp(stored.takenAtMs)}, will replace your current save.
      </p>

      {!hasCurrentSave && (
        <p className="saves-note">
          There is no readable save to replace, so nothing can be lost.
        </p>
      )}

      {identical && (
        <p className="saves-note">
          <Check size={14} aria-hidden="true" />
          This is identical to your current save on every stat compared.
        </p>
      )}

      {losesProgress && (
        <div className="saves-warn">
          <h3>
            <AlertTriangle size={15} aria-hidden="true" />
            Your current save is further along
          </h3>
          <p>These would go backwards:</p>
          <DeltaTable deltas={comparison.regressions} />
        </div>
      )}

      {comparison.advances.length > 0 && (
        <details className="saves-details">
          <summary>
            {comparison.advances.length} stat
            {comparison.advances.length === 1 ? "" : "s"} would go forwards
          </summary>
          <DeltaTable deltas={comparison.advances} />
        </details>
      )}

      {hasCurrentSave && (
        <label className="saves-checkbox">
          <input
            type="checkbox"
            checked={backupFirst}
            onChange={(e) => onBackupChange(e.target.checked)}
          />
          <span>Archive my current save first, so this can be undone</span>
        </label>
      )}
    </Modal>
  );
}

function DeltaTable({
  deltas,
}: {
  deltas: RestorePreview["comparison"]["regressions"];
}) {
  return (
    <table className="saves-delta">
      <thead>
        <tr>
          <th>Stat</th>
          <th>Now</th>
          <th>After</th>
        </tr>
      </thead>
      <tbody>
        {deltas.map((delta) => (
          <tr key={delta.label}>
            <td>{delta.label}</td>
            <td>{formatDelta(delta.label, delta.from)}</td>
            <td>{formatDelta(delta.label, delta.to)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Most deltas are plain counts, but a few carry units that make them
 *  unreadable as raw numbers. */
function formatDelta(label: string, value: number): string {
  if (label === "Time played") return formatDuration((value * 1000) / 60);
  if (label === "Best time") {
    return value === 0 ? "none" : formatDuration((value * 1000) / 60);
  }
  if (label === "Deepest depth") {
    // Through `formatDepth`, so the Cosmic Ocean reads as 7 here and in
    // every other place a depth is shown.
    return formatDepth(Math.floor(value / 100), value % 100);
  }
  if (label === "Total money" || label === "Best money") {
    return formatMoney(value);
  }
  return formatCount(value);
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
