// Which toast severities actually pop as floating notifications. Every toast
// is always recorded to the log/menu; this only gates the on-screen pop.
//
// Persisted in the shared Rust config (source of truth) and broadcast over a
// Tauri event so every open window updates live, mirroring lib/theme.ts.

import { emit, listen, type UnlistenFn } from "@tauri-apps/api/event";
import { useEffect } from "react";
import type { ToastVariant } from "../components/shared/Toast";

/** The threshold value: the minimum severity that shows a toast. */
export type ToastLevel = "info" | "success" | "warning" | "error";

/** Severity order, low to high. Also the toast variants. A variant pops when
 *  its rank is >= the configured level's rank. */
const RANK: Record<ToastLevel, number> = {
  info: 0,
  success: 1,
  warning: 2,
  error: 3,
};

/** Warnings and errors pop by default; success/info stay in the log. Matches
 *  the Rust DEFAULT_TOAST_LEVEL. */
export const DEFAULT_TOAST_LEVEL: ToastLevel = "warning";

/** Broadcast when the threshold changes so other windows follow. */
export const TOAST_LEVEL_CHANGED_EVENT = "toast-level-changed";

/** Coerce an arbitrary config value into a valid ToastLevel. */
export function normalizeToastLevel(
  value: string | null | undefined,
): ToastLevel {
  return value === "info" ||
    value === "success" ||
    value === "warning" ||
    value === "error"
    ? value
    : DEFAULT_TOAST_LEVEL;
}

/** Whether a toast of `variant` should pop given the configured `level`. */
export function shouldPopToast(
  variant: ToastVariant,
  level: ToastLevel,
): boolean {
  return RANK[variant] >= RANK[level];
}

/** Tell every open window the threshold changed. Persisting to config is the
 *  caller's job (via setConfig); this just fans the live update out. */
export function broadcastToastLevel(level: ToastLevel): void {
  void emit(TOAST_LEVEL_CHANGED_EVENT, { level });
}

/** Subscribe to threshold-change broadcasts from other windows. */
export function useToastLevelSync(onChange: (level: ToastLevel) => void): void {
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    void listen<{ level?: string }>(TOAST_LEVEL_CHANGED_EVENT, (event) => {
      onChange(normalizeToastLevel(event.payload?.level));
    }).then((fn) => {
      unlisten = fn;
    });
    return () => {
      unlisten?.();
    };
  }, [onChange]);
}
