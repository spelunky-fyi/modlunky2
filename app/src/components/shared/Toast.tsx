import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { listen } from "@tauri-apps/api/event";
import { getConfig, recordToast } from "../../lib/commands";
import {
  DEFAULT_TOAST_LEVEL,
  TOAST_LEVEL_CHANGED_EVENT,
  normalizeToastLevel,
  shouldPopToast,
  type ToastLevel,
} from "../../lib/toastLevel";
import "./Toast.css";

export type ToastVariant = "info" | "success" | "warning" | "error";

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
}

export interface ToastHistoryEntry extends Toast {
  /// Client-side ms timestamp so the Logs modal can render "12:34:56"
  /// without a second data pass.
  tsMs: number;
}

interface ToastAPI {
  push(message: string, variant?: ToastVariant): void;
  success(message: string): void;
  error(message: string): void;
  info(message: string): void;
  warning(message: string): void;
  dismiss(id: string): void;
  history(): ToastHistoryEntry[];
}

const ToastContext = createContext<ToastAPI | null>(null);

const AUTO_DISMISS_MS = 4500;
/// Cap on retained history. Matches the log ring buffer's philosophy:
/// deep enough to cover a debugging session, not so deep it grows
/// unboundedly during a long-running app.
const MAX_HISTORY = 200;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);
  /// Kept in a ref because Logs modal reads on demand, not on every
  /// render; sticking it in useState would rerender the whole app for
  /// every toast just to keep an off-screen list current.
  const historyRef = useRef<ToastHistoryEntry[]>([]);
  // Minimum severity that actually pops. Every toast is still recorded to the
  // history/log below; this only gates the on-screen render. Kept in a ref so
  // `push` stays stable and a threshold change just affects future toasts.
  const levelRef = useRef<ToastLevel>(DEFAULT_TOAST_LEVEL);
  useEffect(() => {
    void getConfig()
      .then((cfg) => {
        levelRef.current = normalizeToastLevel(cfg.toastLevel);
      })
      .catch(() => {});
    let unlisten: (() => void) | undefined;
    void listen<{ level?: string }>(TOAST_LEVEL_CHANGED_EVENT, (event) => {
      levelRef.current = normalizeToastLevel(event.payload?.level);
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string, variant: ToastVariant = "info") => {
      counterRef.current += 1;
      const id = `t${counterRef.current}`;
      const entry: ToastHistoryEntry = {
        id,
        message,
        variant,
        tsMs: Date.now(),
      };
      historyRef.current.push(entry);
      if (historyRef.current.length > MAX_HISTORY) {
        historyRef.current.splice(
          0,
          historyRef.current.length - MAX_HISTORY,
        );
      }
      // Mirror to the Rust-side ring buffer so the standalone Logs
      // window (a separate React tree with its own historyRef) can
      // still show a full session's worth of toasts. Fire-and-forget:
      // a failed record shouldn't block the user's toast from
      // rendering in-window.
      void recordToast(entry).catch(() => {});
      // Below the configured threshold: recorded to the log above, but not
      // popped on screen.
      if (!shouldPopToast(variant, levelRef.current)) return;
      setToasts((current) => [...current, { id, message, variant }]);
      window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  const api: ToastAPI = useMemo(
    () => ({
      push,
      success: (m) => push(m, "success"),
      error: (m) => push(m, "error"),
      info: (m) => push(m, "info"),
      warning: (m) => push(m, "warning"),
      dismiss,
      history: () => historyRef.current.slice(),
    }),
    [push, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-container" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.variant}`} role="status">
            <span className="toast-message">{t.message}</span>
            <button
              className="toast-dismiss"
              aria-label="Dismiss"
              onClick={() => dismiss(t.id)}
              type="button"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastAPI {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return ctx;
}
