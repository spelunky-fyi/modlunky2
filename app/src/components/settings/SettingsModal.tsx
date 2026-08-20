import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { openUrl } from "@tauri-apps/plugin-opener";
import { CircleAlert, CircleCheck, Eye, EyeOff } from "lucide-react";
import { Modal } from "../shared/Modal";
import type { SettingsFocus } from "../shared/SetupContext";
import type { SharedConfig } from "../../types/config";
import { useToast } from "../shared/Toast";
import { ConnectInline } from "../browse/ConnectInline";
import {
  asBrowseError,
  getConfig,
  guessInstallDir,
  rebuildMods,
  refreshFyiWs,
  setConfig,
  syncDesktopShortcut,
  verifyFyiAccount,
} from "../../lib/commands";
import {
  broadcastToastLevel,
  normalizeToastLevel,
  type ToastLevel,
} from "../../lib/toastLevel";
import { installDirPlaceholder, isWindows } from "../../lib/platform";
import "./SettingsModal.css";

/** One definition of how stored config becomes form state, used both on open
 *  and after a link replaces the token behind the form's back. */
function toFormState(cfg: SharedConfig): FormState {
  return {
    installDir: cfg.installDir ?? "",
    spelunkyFyiRoot: cfg.spelunkyFyiRoot ?? "",
    spelunkyFyiApiToken: cfg.spelunkyFyiApiToken ?? "",
    commandPrefix: cfg.commandPrefix ?? "",
    toastLevel: normalizeToastLevel(cfg.toastLevel),
  };
}

interface SettingsModalProps {
  open: boolean;
  /** Which field the user was sent here to fix, if any. */
  focus?: SettingsFocus | null;
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

export function SettingsModal({
  open,
  focus,
  onClose,
  onSaved,
}: SettingsModalProps) {
  const toast = useToast();
  const [initial, setInitial] = useState<FormState>(EMPTY_FORM);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [status, setStatus] = useState<
    "idle" | "loading" | "saving" | "guessing"
  >("idle");
  const [showToken, setShowToken] = useState(false);
  // Whether the "you'll lose your changes" prompt is up.
  const [confirmClose, setConfirmClose] = useState(false);
  // Set briefly when the user was sent here to fix one specific thing, so the
  // field they came for is the one they land on rather than one row among a
  // dozen. Cleared on a timer: it's a pointer, not a state the form stays in.
  const [highlight, setHighlight] = useState<SettingsFocus | null>(null);
  const installDirRef = useRef<HTMLInputElement | null>(null);
  const tokenRef = useRef<HTMLInputElement | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    if (!open || !focus) {
      setHighlight(null);
      return;
    }
    setHighlight(focus);
    // After the modal has painted, or there is nothing to focus yet.
    const raf = requestAnimationFrame(() => {
      const el =
        focus === "installDir" ? installDirRef.current : tokenRef.current;
      el?.focus();
      el?.scrollIntoView({ block: "center", behavior: "smooth" });
    });
    const timer = window.setTimeout(() => setHighlight(null), 2600);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(timer);
    };
  }, [open, focus]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    // A reopen starts clean, so a prompt left over from last time doesn't
    // greet the user on the way in.
    setConfirmClose(false);
    setStatus("loading");
    setShowToken(false);
    getConfig()
      .then((cfg) => {
        if (cancelled) return;
        const loaded = toFormState(cfg);
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

  /* Reported inline rather than by toast. Toasts are gated on a severity
     threshold that defaults to warnings-and-above, so a success one never pops
     for most people: the button appeared to do nothing when the token worked
     and complained when it did not, which is the wrong way round. The answer to
     "does this work" also belongs next to the thing being asked about, and
     needs to stay there long enough to read. */
  /**
   * Connecting writes a token to the config from Rust, underneath this form.
   *
   * Without re-reading it, the form would still hold the token from when the
   * modal opened -- usually empty -- and saving any *other* change afterwards
   * would write that stale value straight over the one just linked. Re-reading
   * also doubles as the confirmation that it worked, since the token field
   * visibly fills in.
   */
  const handleLinked = useCallback(() => {
    void getConfig()
      .then((cfg) => {
        // Only the token. Linking changed nothing else, and replacing the whole
        // form would throw away edits the user has in progress in other fields.
        const token = cfg.spelunkyFyiApiToken ?? "";
        setInitial((prev) => ({ ...prev, spelunkyFyiApiToken: token }));
        setForm((prev) => ({ ...prev, spelunkyFyiApiToken: token }));
        setTestResult({
          ok: true,
          message: "Connected.",
        });
      })
      .catch(() => {
        // The token is stored either way; this only refreshes the view of it.
        // Say so rather than claiming a failure that did not happen.
        setTestResult({
          ok: true,
          message: "Connected. Reopen Settings to see the token.",
        });
      });
  }, []);

  const handleTestToken = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await verifyFyiAccount();
      setTestResult({
        ok: true,
        message: "spelunky.fyi accepted your account.",
      });
    } catch (err) {
      const browseError = asBrowseError(err);
      setTestResult({
        ok: false,
        message:
          browseError.kind === "needsAccount"
            ? "No account connected."
            : browseError.message,
      });
    } finally {
      setTesting(false);
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

  /**
   * Every way out of this modal comes through here -- Cancel, the X, Escape,
   * and a backdrop click all reach `Modal`'s `onClose` -- so guarding this one
   * function covers all of them.
   *
   * The early return while the confirm is up matters: `Modal` binds its Escape
   * handler on `window`, so with both open a single Escape reaches both. This
   * closure was built in a render where `confirmClose` was already true, so it
   * bows out and lets the confirm handle that keypress alone.
   */
  const handleClose = () => {
    if (status === "saving") return;
    if (confirmClose) return;
    if (dirty) {
      setConfirmClose(true);
      return;
    }
    onClose();
  };

  const discardAndClose = () => {
    setConfirmClose(false);
    onClose();
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
      // Announced only once the mod subsystem is actually back up. Callers
      // treat this as "the app now matches the new settings", and the Mods
      // tab unlocks on it, so firing it any earlier hands them a manager that
      // isn't running yet.
      onSaved?.(installDirChanged);
      onClose();
    } catch (err) {
      toast.error(`Save failed: ${extractMessage(err)}`);
    } finally {
      setStatus("idle");
    }
  };

  return (
    <>
      <Modal
        open={open}
        onClose={handleClose}
        title="Settings"
        size="md"
        footer={
          <>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={handleClose}
              disabled={status === "saving"}
            >
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
            <label
              className={`settings-field${highlight === "installDir" ? " is-highlighted" : ""}`}
            >
              <span className="settings-label">
                Spelunky 2 install directory
              </span>
              <div className="settings-path-row">
                <input
                  ref={installDirRef}
                  type="text"
                  value={form.installDir}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, installDir: e.target.value }))
                  }
                  placeholder={installDirPlaceholder}
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

            <div
              className={`settings-field${highlight === "apiToken" ? " is-highlighted" : ""}`}
            >
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
                  ref={tokenRef}
                  type={showToken ? "text" : "password"}
                  value={form.spelunkyFyiApiToken}
                  onChange={(e) => {
                    setTestResult(null);
                    setForm((f) => ({
                      ...f,
                      spelunkyFyiApiToken: e.target.value,
                    }));
                  }}
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
              <div className="settings-token-actions">
                {/* A token can be reset on the website at any time and nothing
                    tells the app, so without this the first sign of a dead one
                    is a failed install. Tests what is saved rather than what is
                    typed, because the field is not applied until Save runs. */}
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={testing || dirty}
                  title={
                    dirty
                      ? "Save your changes first, then test them"
                      : "Check that spelunky.fyi accepts the saved token"
                  }
                  onClick={() => void handleTestToken()}
                >
                  {testing ? "Testing…" : "Test connection"}
                </button>
                <ConnectInline onLinked={handleLinked} />
              </div>
              {testResult && (
                <p
                  className={`settings-test-result${testResult.ok ? " ok" : " bad"}`}
                  role="status"
                >
                  {testResult.ok ? (
                    <CircleCheck size={14} aria-hidden="true" />
                  ) : (
                    <CircleAlert size={14} aria-hidden="true" />
                  )}
                  {testResult.message}
                </p>
              )}
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
                placeholder="Leave blank"
                spellCheck={false}
              />
              <span className="settings-hint">
                {isWindows
                  ? "Advanced. Runs before the game and the launchers on each launch. Leave blank unless you need a wrapper."
                  : "Advanced. Leave blank to use the Proton that Steam already set up for Spelunky 2, which is detected automatically. Setting this replaces it with your own wrapper."}
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

      {/* Rendered after the settings modal so its portal lands on top of it,
          and tied to `open` as well so any path that closes the parent takes
          the prompt with it rather than leaving it stranded. */}
      {open && confirmClose && (
        <Modal
          open
          onClose={() => setConfirmClose(false)}
          title="Unsaved changes"
          size="sm"
          footer={
            <>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setConfirmClose(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger-ghost"
                onClick={discardAndClose}
              >
                Discard and close
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void handleSave()}
                disabled={status === "saving"}
              >
                {status === "saving" ? "Saving…" : "Save and close"}
              </button>
            </>
          }
        >
          <p className="settings-hint">
            You have unsaved changes to your settings. Close anyway? Your
            changes will be lost.
          </p>
        </Modal>
      )}
    </>
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
