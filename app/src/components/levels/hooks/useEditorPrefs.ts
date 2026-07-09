// App-wide level-editor UI preferences (default zoom, clamp, grid defaults),
// persisted in the shared config.json. Loaded once on mount; every update is
// written back so the choice survives editor-window reopens and app restarts.
// Held once per consumer (an editor window or the splash) and passed down to
// the canvas / bottom bar / settings modal so edits reflect live in-window.

import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_EDITOR_PREFS,
  getEditorPrefs,
  setEditorPrefs,
  type EditorPrefs,
} from "../../../lib/commands";

export interface UseEditorPrefs {
  prefs: EditorPrefs;
  /** Merge a partial update into prefs and persist the result. */
  updatePrefs: (patch: Partial<EditorPrefs>) => void;
  /** False until the initial load resolves. Lets consumers avoid persisting
   *  default values back over a not-yet-loaded config. */
  loaded: boolean;
}

export function useEditorPrefs(): UseEditorPrefs {
  const [prefs, setPrefs] = useState<EditorPrefs>(DEFAULT_EDITOR_PREFS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getEditorPrefs()
      .then((p) => {
        if (!cancelled) {
          setPrefs(p);
          setLoaded(true);
        }
      })
      .catch(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const updatePrefs = useCallback((patch: Partial<EditorPrefs>) => {
    setPrefs((prev) => {
      const next = { ...prev, ...patch };
      setEditorPrefs(next).catch(() => {});
      return next;
    });
  }, []);

  return { prefs, updatePrefs, loaded };
}
