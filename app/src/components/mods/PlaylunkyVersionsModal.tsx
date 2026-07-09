import { useCallback, useEffect, useState } from "react";
import { ask } from "@tauri-apps/plugin-dialog";
import { AlertTriangle } from "lucide-react";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import {
  downloadPlaylunkyVersion,
  listInstalledPlaylunky,
  listPlaylunkyReleases,
  removePlaylunkyVersion,
} from "../../lib/commands";
import type { PlaylunkyReleaseInfo } from "../../types/playlunky";
import "./PlaylunkyVersionsModal.css";

interface PlaylunkyVersionsModalProps {
  open: boolean;
  onClose: () => void;
  activeVersion: string | null;
  onSetActive: (tag: string) => void;
  onChanged: () => void;
}

type RowState =
  | { kind: "idle" }
  | { kind: "installing" }
  | { kind: "removing" };

export function PlaylunkyVersionsModal({
  open,
  onClose,
  activeVersion,
  onSetActive,
  onChanged,
}: PlaylunkyVersionsModalProps) {
  const toast = useToast();
  const [releases, setReleases] = useState<PlaylunkyReleaseInfo[]>([]);
  const [installedExtras, setInstalledExtras] = useState<string[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [rowStates, setRowStates] = useState<Record<string, RowState>>({});

  const load = useCallback(async (force = false) => {
    setStatus("loading");
    try {
      const [rels, installed] = await Promise.all([
        listPlaylunkyReleases(force),
        listInstalledPlaylunky(),
      ]);
      const knownTags = new Set(rels.map((r) => r.tag));
      const extras = installed.filter((t) => !knownTags.has(t));
      setReleases(rels);
      setInstalledExtras(extras);
      setStatus("ready");
    } catch (err) {
      setErrorMessage(extractMessage(err));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void load();
  }, [open, load]);

  const setRow = (tag: string, next: RowState) =>
    setRowStates((r) => ({ ...r, [tag]: next }));

  const handleInstall = async (tag: string) => {
    setRow(tag, { kind: "installing" });
    try {
      await downloadPlaylunkyVersion(tag);
      toast.success(`Installed Playlunky ${tag}.`);
      onChanged();
      await load();
    } catch (err) {
      toast.error(`Install failed: ${extractMessage(err)}`);
    } finally {
      setRow(tag, { kind: "idle" });
    }
  };

  const handleRemove = async (tag: string) => {
    const yes = await ask(`Remove Playlunky ${tag}?`, {
      title: "Remove version",
      kind: "warning",
    });
    if (!yes) return;
    setRow(tag, { kind: "removing" });
    try {
      await removePlaylunkyVersion(tag);
      toast.success(`Removed Playlunky ${tag}.`);
      onChanged();
      await load();
    } catch (err) {
      toast.error(`Remove failed: ${extractMessage(err)}`);
    } finally {
      setRow(tag, { kind: "idle" });
    }
  };

  const rows = [
    ...releases.map((r) => ({
      tag: r.tag,
      prerelease: r.prerelease,
      installed: r.installed,
      knownRelease: true,
    })),
    ...installedExtras.map((t) => ({
      tag: t,
      prerelease: false,
      installed: true,
      knownRelease: false,
    })),
  ];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Playlunky versions"
      size="lg"
      footer={
        <>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => void load(true)}
            disabled={status === "loading"}
          >
            Refresh
          </button>
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        </>
      }
    >
      {status === "loading" && <p className="pl-hint">Loading…</p>}
      {status === "error" && (
        <div className="pl-error">
          <p>Couldn’t load Playlunky releases.</p>
          <pre>{errorMessage}</pre>
        </div>
      )}

      {status === "ready" && activeVersion && activeVersion !== "nightly" && (
        <div className="pl-warning">
          <AlertTriangle size={16} />
          <span>
            Modding API updates only ship in <strong>nightly</strong>. Consider
            switching if you need the latest fixes.
          </span>
        </div>
      )}

      {status === "ready" && (
        <ul className="pl-list">
          {rows.map((row) => {
            const rowStatus = rowStates[row.tag] ?? { kind: "idle" };
            const isActive = row.installed && activeVersion === row.tag;
            return (
              <li key={row.tag} className="pl-row">
                <div className="pl-row-info">
                  <span className="pl-tag">{row.tag}</span>
                  {row.prerelease && (
                    <span className="pl-badge pl-badge-muted">prerelease</span>
                  )}
                  {isActive && (
                    <span className="pl-badge pl-badge-accent">active</span>
                  )}
                  {row.installed && !isActive && (
                    <span className="pl-badge pl-badge-muted">installed</span>
                  )}
                  {!row.knownRelease && (
                    <span className="pl-badge pl-badge-muted">
                      not on github
                    </span>
                  )}
                </div>
                <div className="pl-row-actions">
                  {row.installed ? (
                    <>
                      {!isActive && (
                        <button
                          type="button"
                          className="btn btn-ghost pl-btn"
                          onClick={() => onSetActive(row.tag)}
                        >
                          Set active
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-ghost pl-btn pl-btn-danger"
                        onClick={() => void handleRemove(row.tag)}
                        disabled={rowStatus.kind !== "idle"}
                      >
                        {rowStatus.kind === "removing" ? "Removing…" : "Remove"}
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary pl-btn"
                      onClick={() => void handleInstall(row.tag)}
                      disabled={rowStatus.kind !== "idle"}
                    >
                      {rowStatus.kind === "installing"
                        ? "Installing…"
                        : "Install"}
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Modal>
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
