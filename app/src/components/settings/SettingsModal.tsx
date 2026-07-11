import { useEffect, useMemo, useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { openUrl } from "@tauri-apps/plugin-opener";
import { Eye, EyeOff } from "lucide-react";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import {
  getConfig,
  guessInstallDir,
  rebuildMods,
  refreshFyiWs,
  setConfig,
  syncDesktopShortcut,
} from "../../lib/commands";
import {
  broadcastToastLevel,
  normalizeToastLevel,
  type ToastLevel,
} from "../../lib/toastLevel";
import "./SettingsModal.css";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  onSaved?: (didInstallDirChange: boolean) => void;
}

interface FormState {
  installDir: string;
  spelunkyFyiRoot: string;
  spelunkyFyiApiToken: string;
  commandPrefix: string;
  toastLevel: ToastLevel;
}

const EMPTY_FORM: FormState = {
  installDir: "",
  spelunkyFyiRoot: "",
  spelunkyFyiApiToken: "",
  commandPrefix: "",
  toastLevel: "warning",
};

// Ordered as the severity ladder, low to high. The chosen level and every
// level above it pop; the rest stay log-only.
const TOAST_LEVEL_OPTIONS: { value: ToastLevel; label: string }[] = [
  { value: "info", label: "Info" },
  { value: "success", label: "Success" },
  { value: "warning", label: "Warning" },
  { value: "error", label: "Error" },
];

const DEFAULT_FYI_ROOT = "https://spelunky.fyi/";

export function SettingsModal({ open, onClose, onSaved }: SettingsModalProps) {
  const toast = useToast();
  const [initial, setInitial] = useState<FormState>(EMPTY_FORM);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [status, setStatus] = useState<"idle" | "loading" | "saving" | "guessing">("idle");
  const [showToken, setShowToken] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setStatus("loading");
    setShowToken(false);
    getConfig()
      .then((cfg) => {
        if (cancelled) return;
        const loaded: FormState = {
          installDir: cfg.installDir ?? "",
          spelunkyFyiRoot: cfg.spelunkyFyiRoot ?? "",
          spelunkyFyiApiToken: cfg.spelunkyFyiApiToken ?? "",
          commandPrefix: cfg.commandPrefix ?? "",
          toastLevel: normalizeToastLevel(cfg.toastLevel),
        };
        setInitial(loaded);
        setForm(loaded);
        setStatus("idle");
      })
      .catch((err) => {
        if (cancelled) return;
        toast.error(`Failed to load settings: ${extractMessage(err)}`);
        setStatus("idle");
      });
    return () => {
      cancelled = true;
    };
  }, [open, toast]);

  const dirty = useMemo(
    () =>
      form.installDir !== initial.installDir ||
      form.spelunkyFyiRoot !== initial.spelunkyFyiRoot ||
      form.spelunkyFyiApiToken !== initial.spelunkyFyiApiToken ||
      form.commandPrefix !== initial.commandPrefix ||
      form.toastLevel !== initial.toastLevel,
    [form, initial],
  );

  const handleBrowse = async () => {
    try {
      const picked = await openDialog({
        directory: true,
        multiple: false,
        defaultPath: form.installDir || undefined,
        title: "Select Spelunky 2 install directory",
      });
      if (typeof picked === "string" && picked.length > 0) {
        setForm((f) => ({ ...f, installDir: picked }));
      }
    } catch (err) {
      toast.error(`Browse failed: ${extractMessage(err)}`);
    }
  };

  const handleGuess = async () => {
    setStatus("guessing");
    try {
      const found = await guessInstallDir();
      if (found) {
        setForm((f) => ({ ...f, installDir: found }));
        toast.success("Found it.");
      } else {
        toast.warning("Couldn't find Spelunky 2 automatically. Try Browse.");
      }
    } catch (err) {
      toast.error(`Auto-detect failed: ${extractMessage(err)}`);
    } finally {
      setStatus("idle");
    }
  };

  const handleOpenTokenPage = async () => {
    const root = form.spelunkyFyiRoot.trim() || DEFAULT_FYI_ROOT;
    const url = joinUrl(root, "accounts/settings/");
    try {
      await openUrl(url);
    } catch (err) {
      toast.error(`Couldn't open browser: ${extractMessage(err)}`);
    }
  };

  const handleSave = async () => {
    setStatus("saving");
    try {
      await setConfig({
        installDir: form.installDir,
        spelunkyFyiRoot: form.spelunkyFyiRoot,
        spelunkyFyiApiToken: form.spelunkyFyiApiToken,
        commandPrefix: form.commandPrefix,
        toastLevel: form.toastLevel,
      });
      // Fan the new threshold out to every open window's ToastProvider.
      if (form.toastLevel !== initial.toastLevel) {
        broadcastToastLevel(form.toastLevel);
      }
      const installDirChanged = form.installDir !== initial.installDir;
      const authChanged =
        form.spelunkyFyiApiToken !== initial.spelunkyFyiApiToken ||
        form.spelunkyFyiRoot !== initial.spelunkyFyiRoot;
      setInitial(form);
      onSaved?.(installDirChanged);

      // Keep the desktop shortcut aligned with any command_prefix or
      // install_dir change. Non-fatal on failure.
      await syncDesktopShortcut().catch(() => {});

      // Hot-reload the mod subsystem tree so the new install dir or fyi
      // credentials take effect without a restart. If rebuild fails we
      // fall back to the honest "restart to apply" message.
      if (installDirChanged || authChanged) {
        try {
          await rebuildMods();
          // Only touch the fyi push-install WS if credentials changed;
          // an install-dir edit alone doesn't affect the connection.
          if (authChanged) {
            await refreshFyiWs().catch(() => {});
          }
          toast.success("Settings applied.");
        } catch (err) {
          toast.error(
            `Settings saved, but the mod subsystem couldn't reload: ${extractMessage(err)}. Restart the app to apply.`,
          );
        }
      } else {
        toast.success("Settings saved.");
      }
      onClose();
    } catch (err) {
      toast.error(`Save failed: ${extractMessage(err)}`);
    } finally {
      setStatus("idle");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Settings"
      size="md"
      footer={
        <>
          <button className="btn btn-ghost" type="button" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={handleSave}
            disabled={!dirty || status === "saving" || status === "loading"}
          >
            {status === "saving" ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      {status === "loading" ? (
        <p className="settings-hint">Loading…</p>
      ) : (
        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (dirty) handleSave();
          }}
        >
          <label className="settings-field">
            <span className="settings-label">Spelunky 2 install directory</span>
            <div className="settings-path-row">
              <input
                type="text"
                value={form.installDir}
                onChange={(e) =>
                  setForm((f) => ({ ...f, installDir: e.target.value }))
                }
                placeholder="C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2"
                spellCheck={false}
              />
              <button
                className="btn btn-ghost"
                type="button"
                onClick={handleBrowse}
              >
                Browse{"…"}
              </button>
              <button
                className="btn btn-ghost"
                type="button"
                onClick={handleGuess}
                disabled={status === "guessing"}
                title="Try to find Spelunky 2 automatically"
              >
                {status === "guessing" ? "Searching…" : "I'm feeling lucky"}
              </button>
            </div>
            <span className="settings-hint">
              The Spelunky 2 folder that contains Spel2.exe.
            </span>
          </label>

          <div className="settings-field">
            <div className="settings-label-row">
              <span className="settings-label">spelunky.fyi API token</span>
              <button
                type="button"
                className="settings-linklike"
                onClick={handleOpenTokenPage}
              >
                Get your token
              </button>
            </div>
            <div className="settings-token-row">
              <input
                type={showToken ? "text" : "password"}
                value={form.spelunkyFyiApiToken}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    spelunkyFyiApiToken: e.target.value,
                  }))
                }
                placeholder="Optional, required to install mods from spelunky.fyi"
                spellCheck={false}
              />
              <button
                type="button"
                className="icon-button settings-eye"
                onClick={() => setShowToken((v) => !v)}
                aria-label={showToken ? "Hide token" : "Show token"}
                title={showToken ? "Hide token" : "Show token"}
              >
                {showToken ? (
                  <EyeOff size={16} aria-hidden="true" />
                ) : (
                  <Eye size={16} aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          <label className="settings-field">
            <span className="settings-label">spelunky.fyi root</span>
            <input
              type="text"
              value={form.spelunkyFyiRoot}
              onChange={(e) =>
                setForm((f) => ({ ...f, spelunkyFyiRoot: e.target.value }))
              }
              placeholder={DEFAULT_FYI_ROOT}
              spellCheck={false}
            />
            <span className="settings-hint">
              Leave blank to use the default.
            </span>
          </label>

          <label className="settings-field">
            <span className="settings-label">Playlunky command prefix</span>
            <input
              type="text"
              value={form.commandPrefix}
              onChange={(e) =>
                setForm((f) => ({ ...f, commandPrefix: e.target.value }))
              }
              placeholder="Leave blank on Windows"
              spellCheck={false}
            />
            <span className="settings-hint">
              Advanced. Runs before playlunky_launcher.exe on each launch.
              Useful for Proton or Wine wrappers on non-Windows setups.
            </span>
          </label>

          <label className="settings-field">
            <span className="settings-label">Toast severity threshold</span>
            <select
              value={form.toastLevel}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  toastLevel: e.target.value as ToastLevel,
                }))
              }
            >
              {TOAST_LEVEL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <span className="settings-hint">
              The lowest severity that pops a toast; this level and anything
              more severe show. Everything is still recorded to the toast log.
            </span>
          </label>
        </form>
      )}
    </Modal>
  );
}

function joinUrl(root: string, path: string): string {
  const rootTrim = root.endsWith("/") ? root : `${root}/`;
  const pathTrim = path.startsWith("/") ? path.slice(1) : path;
  return `${rootTrim}${pathTrim}`;
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const value of Object.values(err)) {
      if (typeof value === "string") return value;
    }
    return JSON.stringify(err);
  }
  return String(err);
}
