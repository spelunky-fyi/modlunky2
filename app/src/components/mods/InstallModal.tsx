import { useEffect, useState } from "react";
import { open as openDialog, ask } from "@tauri-apps/plugin-dialog";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import {
  installFromFyi,
  installFromLocal,
  listPackIds,
} from "../../lib/commands";
import "./InstallModal.css";

type Source = "fyi" | "file";

interface InstallModalProps {
  open: boolean;
  onClose: () => void;
}

const CODE_PATTERN = /^[-\w]+$/;
const DEST_PATTERN = /^[-\w.]+$/;

export function InstallModal({ open, onClose }: InstallModalProps) {
  const toast = useToast();
  const [source, setSource] = useState<Source>("fyi");
  const [code, setCode] = useState("");
  const [filePath, setFilePath] = useState("");
  const [destId, setDestId] = useState("");
  const [lastAutoDest, setLastAutoDest] = useState("");
  const [existingPacks, setExistingPacks] = useState<string[]>([]);
  const [installing, setInstalling] = useState(false);

  const reset = () => {
    setSource("fyi");
    setCode("");
    setFilePath("");
    setDestId("");
    setLastAutoDest("");
    setInstalling(false);
  };

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    listPackIds()
      .then((ids) => {
        if (!cancelled) setExistingPacks(ids);
      })
      .catch(() => {
        if (!cancelled) setExistingPacks([]);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleClose = () => {
    if (installing) return;
    reset();
    onClose();
  };

  const handlePickFile = async () => {
    try {
      const picked = await openDialog({
        multiple: false,
        directory: false,
        // Python install.py:188-195 accepted .zip archives, single .lua files
        // (renamed to main.lua at the destination), and arbitrary loose files
        // (dropped in the pack folder as-is). Match that.
        filters: [
          { name: "Mod (zip, lua, or file)", extensions: ["zip", "lua", "*"] },
        ],
        title: "Choose a mod file",
      });
      if (typeof picked === "string" && picked.length > 0) {
        setFilePath(picked);
        // Auto-suggest destination from the file stem, but leave user edits
        // alone. Only overwrite the destination field if it's empty or still
        // holds the previous auto-suggestion.
        const stem = fileStem(picked);
        if (destId === "" || destId === lastAutoDest) {
          setDestId(stem);
        }
        setLastAutoDest(stem);
      }
    } catch (err) {
      toast.error(`Pick failed: ${extractMessage(err)}`);
    }
  };

  const installFyi = async () => {
    const parsed = parseFyiCode(code);
    if (!parsed) {
      toast.error("That doesn't look like a valid spelunky.fyi mod code.");
      return;
    }
    setInstalling(true);
    try {
      await installFromFyi(parsed, false);
      toast.success(`Installed ${parsed}.`);
      reset();
      onClose();
    } catch (err) {
      if (isModExists(err)) {
        const yes = await ask(
          `You already have ${parsed} installed. Update it to the latest version?`,
          { title: "Already installed", kind: "warning" },
        );
        if (yes) {
          try {
            await installFromFyi(parsed, true);
            toast.success(`Updated ${parsed}.`);
            reset();
            onClose();
          } catch (retryErr) {
            toast.error(`Update failed: ${extractMessage(retryErr)}`);
          }
        }
      } else if (isLibraryMod(err)) {
        toast.error(
          `${parsed} is a library mod. Install the pack that depends on it, and the library will come along automatically.`,
        );
      } else {
        toast.error(`Install failed: ${extractMessage(err)}`);
      }
    } finally {
      setInstalling(false);
    }
  };

  const installLocal = async () => {
    const trimmed = destId.trim();
    if (!DEST_PATTERN.test(trimmed)) {
      toast.error(
        "Destination name can only contain letters, numbers, dashes, dots, and underscores.",
      );
      return;
    }
    setInstalling(true);
    try {
      await installFromLocal(filePath, trimmed, false);
      toast.success(`Installed ${trimmed}.`);
      reset();
      onClose();
    } catch (err) {
      if (isModExists(err)) {
        const yes = await ask(
          `You already have ${trimmed} installed. Overwrite it with this file?`,
          { title: "Already installed", kind: "warning" },
        );
        if (yes) {
          try {
            await installFromLocal(filePath, trimmed, true);
            toast.success(`Overwrote ${trimmed}.`);
            reset();
            onClose();
          } catch (retryErr) {
            toast.error(`Overwrite failed: ${extractMessage(retryErr)}`);
          }
        }
      } else {
        toast.error(`Install failed: ${extractMessage(err)}`);
      }
    } finally {
      setInstalling(false);
    }
  };

  const handleInstall = () => {
    if (source === "fyi") void installFyi();
    else void installLocal();
  };

  const canInstall =
    !installing &&
    ((source === "fyi" && code.trim().length > 0) ||
      (source === "file" &&
        filePath.length > 0 &&
        destId.trim().length > 0));

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Install a mod"
      size="md"
      footer={
        <>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={handleClose}
            disabled={installing}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleInstall}
            disabled={!canInstall}
          >
            {installing ? "Installing…" : "Install"}
          </button>
        </>
      }
    >
      <div className="install-source-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={source === "fyi"}
          className={`install-source-tab${source === "fyi" ? " active" : ""}`}
          onClick={() => setSource("fyi")}
          disabled={installing}
        >
          From spelunky.fyi
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={source === "file"}
          className={`install-source-tab${source === "file" ? " active" : ""}`}
          onClick={() => setSource("file")}
          disabled={installing}
        >
          From file
        </button>
      </div>

      {source === "fyi" ? (
        <div className="install-form">
          <label className="install-field">
            <span className="install-label">Mod code or URL</span>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="mod-slug or https://spelunky.fyi/mods/m/mod-slug/"
              spellCheck={false}
              autoFocus
              disabled={installing}
            />
            <span className="install-hint">
              Requires a spelunky.fyi API token in Settings.
            </span>
          </label>
        </div>
      ) : (
        <div className="install-form">
          <label className="install-field">
            <span className="install-label">Mod archive</span>
            <div className="install-file-row">
              <input
                type="text"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                placeholder="No file chosen"
                spellCheck={false}
                readOnly
              />
              <button
                type="button"
                className="btn btn-ghost"
                onClick={handlePickFile}
                disabled={installing}
              >
                Choose{"…"}
              </button>
            </div>
            <span className="install-hint">
              A .zip pack, a single .lua script (installed as main.lua), or a
              loose file to drop into the pack folder.
            </span>
          </label>

          <label className="install-field">
            <span className="install-label">Destination pack</span>
            <input
              type="text"
              value={destId}
              onChange={(e) => setDestId(e.target.value)}
              placeholder="Pack folder name under Mods/Packs"
              spellCheck={false}
              disabled={installing}
              list="install-existing-packs"
            />
            <datalist id="install-existing-packs">
              {existingPacks.map((id) => (
                <option key={id} value={id} />
              ))}
            </datalist>
            <span className="install-hint">
              Prefilled from the file name. Type a new name to create a new
              pack, or pick an existing pack to overwrite it.
            </span>
          </label>
        </div>
      )}
    </Modal>
  );
}

function parseFyiCode(raw: string): string | null {
  let candidate = raw.trim();
  if (/^https?:\/\//i.test(candidate)) {
    try {
      const url = new URL(candidate);
      const parts = url.pathname.split("/").filter(Boolean);
      candidate = parts[parts.length - 1] ?? "";
    } catch {
      return null;
    }
  }
  return CODE_PATTERN.test(candidate) ? candidate : null;
}

function fileStem(path: string): string {
  const base = path.split(/[/\\]/).pop() ?? "";
  const idx = base.lastIndexOf(".");
  return idx > 0 ? base.slice(0, idx) : base;
}

function isModExists(err: unknown): boolean {
  return (
    typeof err === "object" && err !== null && "ModExistsError" in err
  );
}

function isLibraryMod(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "LibraryModNotInstallable" in err
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
