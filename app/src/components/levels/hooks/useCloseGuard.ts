// Window-close guard for editor windows. Intercepts the OS close button
// (title-bar X, Alt+F4, taskbar Close) so unsaved work doesn't vanish
// silently. The editor keeps its own top-level dirty flag; the guard
// only decides whether to prompt.
//
// Usage:
//   const closeGuard = useCloseGuard(dirty);
//   ...
//   {closeGuard.showConfirm && (
//     <Modal ... onClose={closeGuard.onCancelClose}>
//       ...
//       <button onClick={closeGuard.onConfirmClose}>Discard and close</button>
//     </Modal>
//   )}

import { useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";

export interface CloseGuard {
  /** True when the user tried to close the window while `shouldGuard` was
   *  true. The caller renders its own confirm modal off this flag. */
  showConfirm: boolean;
  /** Discard-and-close: unregisters the guard and asks the OS to close
   *  the window. Awaits the close so the caller can keep the confirm
   *  modal mounted through the transition. */
  onConfirmClose: () => Promise<void>;
  /** Cancel: keep the window open. */
  onCancelClose: () => void;
}

export function useCloseGuard(shouldGuard: boolean): CloseGuard {
  const [showConfirm, setShowConfirm] = useState(false);
  // Track shouldGuard in a ref so the onCloseRequested listener always
  // reads the current value without needing to re-register on every dirty
  // flip.
  const shouldGuardRef = useRef(shouldGuard);
  useEffect(() => {
    shouldGuardRef.current = shouldGuard;
  }, [shouldGuard]);
  useEffect(() => {
    const win = getCurrentWindow();
    // Always preventDefault and dispatch ourselves. If shouldGuard is
    // false, destroy() the window immediately (matching Tauri's
    // built-in "no preventDefault -> close" behavior). If true, surface
    // the confirm modal. This avoids relying on Tauri's post-handler
    // isPreventDefault() check running with the ref's *latest* value,
    // which is fragile under React's StrictMode double-invoked effects
    // and any HMR reload.
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    win
      .onCloseRequested((event) => {
        event.preventDefault();
        if (!shouldGuardRef.current) {
          void win.destroy();
          return;
        }
        setShowConfirm(true);
      })
      .then((fn) => {
        if (cancelled) fn();
        else unlisten = fn;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  return {
    showConfirm,
    onConfirmClose: async () => {
      setShowConfirm(false);
      try {
        await getCurrentWindow().destroy();
      } catch {
        // Fallback: if destroy() throws, drop the guard so the next OS
        // close request goes through.
        shouldGuardRef.current = false;
      }
    },
    onCancelClose: () => setShowConfirm(false),
  };
}
