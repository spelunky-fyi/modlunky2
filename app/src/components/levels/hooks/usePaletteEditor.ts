// Palette editor UI state + delete flow shared between the Vanilla and
// Custom editors. Owns:
//
//   - swatch overrides for tiles added after atlas build
//   - paletteChangedSinceSave dirty flag
//   - reorder-lock + help modal open state
//   - pending-delete state + the confirm flow that rewrites the on-disk
//     grid content, resets undo history, and syncs the primary/secondary
//     picker so deleted tiles don't linger as the active brush
//
// Palette LIST state (`palette` array + setPalette) stays in the parent
// because useLevelCanvas needs it as an input, and this hook needs the
// canvas refs as inputs. Passing them through works around the circular
// dep without forcing either hook to know about the other.
//
// Palette ADD is also parent-owned. Vanilla's add path allocates a code
// that inherits from sister files' dependency palettes and can defer to
// a user-confirmed collision, which Custom doesn't need. Sharing a
// single add path would force a discriminated-union prop that reads
// worse than the current split.

import { useCallback, useEffect, useState } from "react";
import type { CustomLevelPaletteEntry } from "../../../lib/commands";

interface Toast {
  success: (msg: string) => void;
  error: (msg: string) => void;
}

interface Refs {
  gridsRef: React.MutableRefObject<Map<string, string[][]>>;
  bgGridsRef: React.MutableRefObject<Map<string, string[][]>>;
  editedKeysRef: React.MutableRefObject<Set<string>>;
  currentRoomTouchedRef: React.MutableRefObject<boolean>;
}

export interface PaletteEditorArgs {
  /** Current palette list. Owned by the parent because useLevelCanvas
   *  reads it too. */
  palette: CustomLevelPaletteEntry[];
  setPalette: React.Dispatch<React.SetStateAction<CustomLevelPaletteEntry[]>>;
  /** Parent-owned "palette shape changed since save" ref. Kept in the
   *  parent so `recomputeDirty` (defined between the canvas hook and
   *  this hook to break a cyclic dep) can read it too. */
  paletteChangedSinceSave: React.MutableRefObject<boolean>;
  /** Ref bundle from the shared canvas hook. Used by the delete confirm
   *  to rewrite grid cells and mark them dirty. */
  refs: Refs;
  /** Key in the grids map that identifies the currently-editing thing
   *  (a room key for Vanilla, a file name for Custom). The delete
   *  confirm uses it only to flip `currentRoomTouchedRef` when the
   *  active thing's cells got rewritten. */
  currentKey: string | null;
  /** Selection state from the canvas hook. Cleared when the deleted
   *  tile was the active brush. */
  primary: string | null;
  secondary: string | null;
  setPrimary: (name: string | null) => void;
  setSecondary: (name: string | null) => void;
  /** Canvas history reset. Called after a delete because the wholesale
   *  grid rewrite is not undoable and stale strokes would apply on top
   *  of the replaced content. */
  resetHistory: () => void;
  /** Bumps the version counter that drives grid-derived memos (e.g. the
   *  Vanilla rooms tree's dirty pips). */
  bumpGridsVersion: () => void;
  /** Editor-side hook that reconciles the top-level `dirty` flag after
   *  a palette-shape change. */
  recomputeDirty: () => void;
  /** Resets reorder mode when the user switches files. A stray reorder
   *  state carried over from the previous file would look wrong against
   *  the new palette. */
  selectedKey: string | null;
  toast: Toast;
}

export interface PaletteEditor {
  swatchOverrides: Map<string, string>;
  setSwatchOverrides: React.Dispatch<React.SetStateAction<Map<string, string>>>;
  paletteHelpOpen: boolean;
  setPaletteHelpOpen: React.Dispatch<React.SetStateAction<boolean>>;
  paletteReorderMode: boolean;
  setPaletteReorderMode: React.Dispatch<React.SetStateAction<boolean>>;
  pendingPaletteDelete: PendingPaletteDelete | null;
  setPendingPaletteDelete: React.Dispatch<
    React.SetStateAction<PendingPaletteDelete | null>
  >;
  /** Reorder wired for the shared PaletteSidebarSection: replaces the
   *  entry list and flags a save-worthy change. */
  handleReorder: (next: CustomLevelPaletteEntry[]) => void;
  /** Count cells across all fg + bg grids that reference this tile
   *  name. Used to gate the delete-confirm modal. */
  countPaletteUsage: (name: string) => number;
  /** Pick the fill tile used to overwrite a deleted entry. Prefer
   *  "empty" if it survives, else the first remaining entry, else "". */
  pickReplacement: (deletedName: string) => string;
  /** Front door for the delete flow. Refuses "empty", drops the entry
   *  outright if it's unused, opens the confirm modal otherwise. */
  handlePaletteDelete: (name: string) => void;
  /** Consumer for the confirm modal's primary action. Rewrites all
   *  cells, drops the entry, resets history + selection. */
  confirmPaletteDelete: () => void;
  /** Clear per-file state on file load / unload. Wipes swatch overrides
   *  and the dirty flag; leaves the palette list alone (caller replaces
   *  it with the loaded file's entries). */
  resetForFileLoad: () => void;
}

export interface PendingPaletteDelete {
  name: string;
  count: number;
  replacement: string;
}

export function usePaletteEditor(args: PaletteEditorArgs): PaletteEditor {
  const {
    palette,
    setPalette,
    paletteChangedSinceSave,
    refs,
    currentKey,
    primary,
    secondary,
    setPrimary,
    setSecondary,
    resetHistory,
    bumpGridsVersion,
    recomputeDirty,
    selectedKey,
    toast,
  } = args;

  const [swatchOverrides, setSwatchOverrides] = useState<Map<string, string>>(
    () => new Map(),
  );
  const [paletteHelpOpen, setPaletteHelpOpen] = useState(false);
  const [paletteReorderMode, setPaletteReorderMode] = useState(false);
  const [pendingPaletteDelete, setPendingPaletteDelete] =
    useState<PendingPaletteDelete | null>(null);

  // Drop reorder mode when the user switches files. Otherwise a stray
  // active reorder state would carry over into the new palette.
  useEffect(() => {
    setPaletteReorderMode(false);
  }, [selectedKey]);

  const countPaletteUsage = useCallback(
    (name: string): number => {
      let n = 0;
      for (const grid of refs.gridsRef.current.values()) {
        for (const row of grid) {
          for (const cell of row) if (cell === name) n++;
        }
      }
      for (const grid of refs.bgGridsRef.current.values()) {
        for (const row of grid) {
          for (const cell of row) if (cell === name) n++;
        }
      }
      return n;
    },
    // Refs are stable; deps intentionally empty.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const pickReplacement = useCallback(
    (deletedName: string): string => {
      const empty = palette.find(
        (p) => p.name === "empty" && p.name !== deletedName,
      );
      if (empty) return empty.name;
      const first = palette.find((p) => p.name !== deletedName);
      return first?.name ?? "";
    },
    [palette],
  );

  const handleReorder = useCallback(
    (next: CustomLevelPaletteEntry[]) => {
      setPalette(next);
      paletteChangedSinceSave.current = true;
      recomputeDirty();
    },
    [setPalette, recomputeDirty],
  );

  const handlePaletteDelete = useCallback(
    (name: string) => {
      if (name === "empty") {
        // "empty" is the fallback replacement for every other palette
        // deletion; refusing to remove it keeps deletes from silently
        // rewriting to blank cells.
        toast.error("Can't delete the empty tile.");
        return;
      }
      const count = countPaletteUsage(name);
      const replacement = pickReplacement(name);
      if (count === 0) {
        setPalette((prev) => prev.filter((p) => p.name !== name));
        if (primary === name) setPrimary(replacement || null);
        if (secondary === name) setSecondary(replacement || null);
        paletteChangedSinceSave.current = true;
        recomputeDirty();
        toast.success(`Removed "${name}" from palette.`);
        return;
      }
      setPendingPaletteDelete({ name, count, replacement });
    },
    [
      countPaletteUsage,
      pickReplacement,
      primary,
      secondary,
      setPrimary,
      setSecondary,
      setPalette,
      recomputeDirty,
      toast,
    ],
  );

  const confirmPaletteDelete = useCallback(() => {
    const pending = pendingPaletteDelete;
    if (!pending) return;
    const { name, replacement } = pending;
    // Rewrite every occurrence across fg + bg grids for every key. In
    // Vanilla mode "key" is a room key; in Custom it's a file name. The
    // dirtiness bookkeeping is identical either way.
    for (const [key, grid] of refs.gridsRef.current) {
      let touched = false;
      for (const row of grid) {
        for (let i = 0; i < row.length; i++) {
          if (row[i] === name) {
            row[i] = replacement;
            touched = true;
          }
        }
      }
      if (touched) {
        refs.editedKeysRef.current.add(key);
        if (key === currentKey) refs.currentRoomTouchedRef.current = true;
      }
    }
    for (const [key, grid] of refs.bgGridsRef.current) {
      let touched = false;
      for (const row of grid) {
        for (let i = 0; i < row.length; i++) {
          if (row[i] === name) {
            row[i] = replacement;
            touched = true;
          }
        }
      }
      if (touched) {
        refs.editedKeysRef.current.add(key);
        if (key === currentKey) refs.currentRoomTouchedRef.current = true;
      }
    }
    setPalette((prev) => prev.filter((p) => p.name !== name));
    if (primary === name) setPrimary(replacement || null);
    if (secondary === name) setSecondary(replacement || null);
    paletteChangedSinceSave.current = true;
    resetHistory();
    setPendingPaletteDelete(null);
    bumpGridsVersion();
    recomputeDirty();
    toast.success(
      `Removed "${name}"; replaced ${pending.count} cell${pending.count === 1 ? "" : "s"}.`,
    );
  }, [
    pendingPaletteDelete,
    primary,
    secondary,
    setPrimary,
    setSecondary,
    setPalette,
    currentKey,
    refs,
    resetHistory,
    bumpGridsVersion,
    recomputeDirty,
    toast,
  ]);

  const resetForFileLoad = useCallback(() => {
    setSwatchOverrides(new Map());
    paletteChangedSinceSave.current = false;
  }, []);

  return {
    swatchOverrides,
    setSwatchOverrides,
    paletteHelpOpen,
    setPaletteHelpOpen,
    paletteReorderMode,
    setPaletteReorderMode,
    pendingPaletteDelete,
    setPendingPaletteDelete,
    handleReorder,
    countPaletteUsage,
    pickReplacement,
    handlePaletteDelete,
    confirmPaletteDelete,
    resetForFileLoad,
  };
}
