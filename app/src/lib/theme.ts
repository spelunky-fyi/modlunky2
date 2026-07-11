// App color theme (dark / light). Dark is the default and original look;
// light is opt-in via Settings.
//
// The theme is persisted in the shared Rust config (source of truth) but is
// mirrored to localStorage so the pre-paint inline script in index.html can
// set `data-theme` on <html> synchronously, before any React/CSS lands, in
// every window. That avoids a flash of the wrong theme when a light-mode user
// opens the app or a secondary window (editor / logs / character chooser),
// which all share this origin's localStorage.
//
// A theme change broadcasts a Tauri event so every already-open window
// re-themes live, not just the window that made the change.

import { emit, listen, type UnlistenFn } from "@tauri-apps/api/event";
import { useEffect } from "react";

export type Theme = "dark" | "light";

/** localStorage key read by the pre-paint script in index.html. */
export const THEME_STORAGE_KEY = "ml2-theme";

/** Broadcast when the theme changes so other windows can follow. */
export const THEME_CHANGED_EVENT = "theme-changed";

/** Coerce an arbitrary config/storage value into a valid Theme. Anything
 *  that isn't exactly "light" falls back to dark, matching the Rust default. */
export function normalizeTheme(value: string | null | undefined): Theme {
  return value === "light" ? "light" : "dark";
}

/** Apply a theme to this window: set the document attribute the CSS keys off
 *  of, and refresh the localStorage mirror the pre-paint script reads. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Private-mode / storage-disabled: the attribute is still set, we just
    // lose the no-flash fast path on the next launch. Not worth surfacing.
  }
}

/** Apply the theme locally and tell every other open window to match. */
export function broadcastTheme(theme: Theme): void {
  applyTheme(theme);
  void emit(THEME_CHANGED_EVENT, { theme });
}

/** Subscribe this window to theme-change broadcasts from other windows.
 *  Call once near the root so every window (any route) stays in sync. */
export function useThemeSync(): void {
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    void listen<{ theme?: string }>(THEME_CHANGED_EVENT, (event) => {
      applyTheme(normalizeTheme(event.payload?.theme));
    }).then((fn) => {
      unlisten = fn;
    });
    return () => {
      unlisten?.();
    };
  }, []);
}
