// Bringing saves in from somewhere else.
//
// Two steps rather than one. Picking files only reads them, and what
// comes back is shown before anything is copied: what is in each save,
// and whether the archive already holds those exact bytes. Someone
// importing a folder of old saves has no other way to tell which ones
// they have already done.
//
// Duplicates are unticked rather than refused. Two copies of one save
// under different names is a reasonable thing to want, and the archive is
// the user's to arrange - but the common case is not wanting them, so
// that is what the boxes start at.

import { useEffect, useMemo, useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { AlertTriangle, FileDown, Loader2 } from "lucide-react";

import {
  importSaves,
  previewSaveImports,
  type ImportPreview,
  type StoredSave,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import {
  formatBytes,
  formatCount,
  formatDepth,
  formatTimestamp,
} from "./format";

/**
 * Opens the picker and returns what was chosen.
 *
 * Kept out of the modal so the button can open the picker first: a modal
 * that appears and then opens a file dialog on top of itself is two
 * dialogs deep for one decision.
 */
export async function pickSaveFiles(): Promise<string[]> {
  const picked = await openDialog({
    multiple: true,
    directory: false,
    title: "Choose Spelunky 2 saves",
    filters: [
      { name: "Spelunky 2 save", extensions: ["sav"] },
      { name: "All files", extensions: ["*"] },
    ],
  });
  if (picked === null) return [];
  return Array.isArray(picked) ? picked : [picked];
}

export function ImportModal({
  paths,
  onClose,
  onImported,
}: {
  /** The files picked, or empty when the modal is closed. */
  paths: string[];
  onClose: () => void;
  onImported: (saves: StoredSave[]) => void;
}) {
  const toast = useToast();
  const [previews, setPreviews] = useState<ImportPreview[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  const key = paths.join("\u0000");
  useEffect(() => {
    if (paths.length === 0) return;
    setPreviews(null);
    setError(null);
    let cancelled = false;
    previewSaveImports(paths).then(
      (result) => {
        if (cancelled) return;
        setPreviews(result);
        // Everything importable starts ticked except the duplicates,
        // which is what someone re-running an import wants.
        setChosen(
          new Set(
            result
              .filter((p) => p.error === null && p.duplicate === null)
              .map((p) => p.path),
          ),
        );
      },
      (err: unknown) => {
        if (!cancelled) setError(extractMessage(err));
      },
    );
    return () => {
      cancelled = true;
    };
    // `paths` is a fresh array each render; its contents are the identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const counts = useMemo(() => {
    const rows = previews ?? [];
    return {
      importable: rows.filter((p) => p.error === null).length,
      duplicates: rows.filter((p) => p.error === null && p.duplicate).length,
      unreadable: rows.filter((p) => p.error !== null).length,
    };
  }, [previews]);

  if (paths.length === 0) return null;

  const toggle = (path: string) =>
    setChosen((current) => {
      const next = new Set(current);
      if (!next.delete(path)) next.add(path);
      return next;
    });

  const setAll = (on: boolean) =>
    setChosen(
      on
        ? new Set(
            (previews ?? []).filter((p) => p.error === null).map((p) => p.path),
          )
        : new Set(),
    );

  const confirm = async () => {
    const rows = (previews ?? []).filter((p) => chosen.has(p.path));
    if (rows.length === 0) return;
    setBusy(true);
    try {
      const outcome = await importSaves(
        rows.map((p) => ({
          path: p.path,
          // The file's own name is what the user already associates with
          // this save; renaming afterwards is one click.
          description: p.fileName.replace(/\.sav$/i, ""),
        })),
      );
      onImported(outcome.imported);
      if (outcome.failed.length > 0) {
        toast.warning(
          `Imported ${outcome.imported.length}; ${outcome.failed.length} could not be copied.`,
        );
      } else {
        toast.success(
          outcome.imported.length === 1
            ? "Save imported."
            : `${outcome.imported.length} saves imported.`,
        );
      }
      onClose();
    } catch (err) {
      toast.error(extractMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={
        paths.length === 1 ? "Import a save" : `Import ${paths.length} saves`
      }
      size="lg"
      footer={
        <>
          <button type="button" className="saves-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="saves-btn saves-btn-primary"
            disabled={busy || chosen.size === 0}
            onClick={() => void confirm()}
          >
            {busy
              ? "Importing..."
              : chosen.size === 1
                ? "Import a copy"
                : `Import ${chosen.size} copies`}
          </button>
        </>
      }
    >
      {error !== null ? (
        <p className="saves-error">
          <AlertTriangle size={14} aria-hidden="true" />
          {error}
        </p>
      ) : previews === null ? (
        <p className="ed-loading">
          <Loader2 size={16} className="spin" aria-hidden="true" /> Reading{" "}
          {paths.length === 1 ? "the save" : `${paths.length} saves`}...
        </p>
      ) : (
        <>
          {counts.duplicates > 0 && (
            <p className="saves-warning">
              <AlertTriangle size={14} aria-hidden="true" />
              {counts.duplicates === 1
                ? "One of these is already in your archive and has been deselected."
                : `${counts.duplicates} of these are already in your archive and have been deselected.`}{" "}
              Importing it again replaces the duplicate.
            </p>
          )}
          {counts.unreadable > 0 && (
            <p className="saves-warning">
              <AlertTriangle size={14} aria-hidden="true" />
              {counts.unreadable === 1
                ? "One file could not be read and cannot be imported."
                : `${counts.unreadable} files could not be read and cannot be imported.`}
            </p>
          )}

          {previews.length > 1 && (
            <div className="import-actions">
              <span className="ed-toolbar-count">
                {chosen.size} of {counts.importable} selected
              </span>
              <button
                type="button"
                className="saves-btn"
                onClick={() => setAll(true)}
              >
                Select all
              </button>
              <button
                type="button"
                className="saves-btn"
                onClick={() => setAll(false)}
              >
                Select none
              </button>
            </div>
          )}

          <ul className="import-list">
            {previews.map((preview) => (
              <li
                key={preview.path}
                className={preview.error !== null ? "bad" : undefined}
              >
                <label>
                  <input
                    type="checkbox"
                    checked={chosen.has(preview.path)}
                    disabled={preview.error !== null}
                    onChange={() => toggle(preview.path)}
                  />
                  <span className="import-name" title={preview.path}>
                    {preview.fileName}
                  </span>
                </label>
                <span className="import-detail">
                  {preview.error !== null ? (
                    <em>{preview.error}</em>
                  ) : (
                    <>
                      {preview.summary && (
                        <>
                          {formatCount(preview.summary.plays)} runs &middot;{" "}
                          {formatDepth(
                            preview.summary.deepestArea,
                            preview.summary.deepestLevel,
                          )}{" "}
                          &middot;{" "}
                        </>
                      )}
                      {formatBytes(preview.fileSize)}
                      {preview.modifiedAtMs !== null && (
                        <> &middot; {formatTimestamp(preview.modifiedAtMs)}</>
                      )}
                      {!preview.checksumValid && (
                        <>
                          {" "}
                          &middot; <em>bad checksum</em>
                        </>
                      )}
                      {preview.duplicate && (
                        <>
                          {" "}
                          &middot;{" "}
                          <em>
                            already archived as{" "}
                            {preview.duplicate.description || "an unnamed save"}
                          </em>
                        </>
                      )}
                    </>
                  )}
                </span>
              </li>
            ))}
          </ul>

          <p className="saves-hint">
            <FileDown size={13} aria-hidden="true" /> This makes a copy of your
            original files.
          </p>
        </>
      )}
    </Modal>
  );
}

/** The message out of a rejected command, which arrives as a string. */
function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  return String(err);
}
