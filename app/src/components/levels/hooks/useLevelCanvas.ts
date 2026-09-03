// Shared canvas hook for the level editors. Holds the fg/bg grid refs,
// undo/redo stacks, marquee state, layer routing, tools, view + link
// settings, and all the paint pipeline glue. VanillaEditor and (soon)
// CustomEditor both consume this so they don't drift on the hot path.
//
// The hook is deliberately unaware of "which file/room is loaded" beyond
// a caller-supplied `currentKey` string, it just stores per-key grids in
// its maps. Callers own the load-from-disk / save-to-disk / rooms tree
// details, plus anything tied to their own format (rules for vanilla,
// level_configuration for custom).

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  readText as readClipboardText,
  writeText as writeClipboardText,
} from "@tauri-apps/plugin-clipboard-manager";
import type { CustomLevelPaletteEntry } from "../../../lib/commands";
import type {
  Selection,
  TileCanvasHandle,
  Tool,
} from "../TileCanvas";

/** Column-count of blank spacer inserted between fg and bg in the
 *  side-by-side view. Exported so callers doing their own math (setroom
 *  mosaicing, level view) stay consistent. */
export const DUAL_GAP_COLS = 2;

export type CanvasLayer = "foreground" | "background";

/** One addressable cell of authored level data: which grid it lives in
 *  (`key` + `layer`) and where inside that grid (`row`, `col`, always in
 *  AUTHORED coords, never display coords). Every read and write in the
 *  paint pipeline is expressed in these terms, which is what lets one
 *  canvas edit many rooms at once. */
export interface RoutedCell {
  key: string;
  layer: CanvasLayer;
  row: number;
  col: number;
}

/** Translates between canvas coords (what the user clicks) and authored
 *  cells (what gets stored). Callers supply one when a single canvas shows
 *  more than the current key's grid -- the whole-level mosaic, where each
 *  region of the canvas belongs to a different room. */
export interface CellRouter {
  /** Authored cell under a canvas coord, or null where nothing is
   *  editable (spacer columns, gaps between rooms). */
  toCell: (row: number, col: number) => RoutedCell | null;
  /** Where an authored cell currently shows on the canvas, or null when
   *  it isn't on screen at all. Used to push sprite updates. */
  toCanvas: (cell: RoutedCell) => { row: number; col: number } | null;
}

export interface PaintEdit {
  row: number;
  col: number;
  oldName: string;
  newName: string;
  /** Which layer's grid map this edit belongs to. Stored per-edit so a
   *  single drag that crosses the fg/bg boundary (Link-layers on) still
   *  undoes correctly. */
  layer: CanvasLayer;
  /** Which grid this edit belongs to. Stored per-edit so a stroke that
   *  crosses room boundaries in the whole-level view undoes correctly. */
  key: string;
}
export type Stroke = PaintEdit[];

export interface UseLevelCanvasParams {
  /** Map key for the currently-open grid. Vanilla passes
   *  `${templateName}#${roomIndex}`, Custom passes the file name.
   *  `null` when no grid is open. */
  currentKey: string | null;
  /** True when the current grid supports both layers (Dual room in
   *  vanilla; per-file setting in custom). Non-dual rooms force
   *  layerView to "fg" internally. */
  isDual: boolean;
  /** Display the current room mirrored horizontally. Paint clicks are
   *  translated so writes land at the authored (un-mirrored) column,
   *  matching Python's ONLYFLIP semantics. Toggle on for FLIP preview or
   *  force-on for ONLYFLIP; other rooms should pass false. */
  mirrored?: boolean;
  /** Current palette. Used for erase-tile resolution and paste
   *  sanitization; not stored inside the hook. */
  palette: CustomLevelPaletteEntry[];
  /** Set when one canvas shows several grids at once (the whole-level
   *  mosaic). Every paint, marquee op, and undo entry then routes through
   *  it instead of assuming `currentKey`. Null / omitted for the ordinary
   *  one-grid-per-canvas case. */
  cellRouter?: CellRouter | null;
  /** True if the caller stores a settings override for the given key.
   *  Vanilla returns `settingsRef.current.has(key)`; Custom always
   *  returns false. Used only to keep the "edited keys" reconciliation
   *  from clearing the pip while there's a live override. */
  hasSettingsOverride?: (key: string) => boolean;
  /** Fires when the internal `editedKeys` set gains or loses an entry
   *  so the caller can bump its own re-render tick / re-run its dirty
   *  computation. */
  onEditedKeysChanged?: () => void;
  /** Called when a marquee op wants to notify the user. */
  toast: {
    success: (msg: string) => void;
    error: (msg: string) => void;
  };
}

export interface UseLevelCanvasReturn {
  // ---- Refs the caller may need to read directly ----
  canvasRef: React.MutableRefObject<TileCanvasHandle | null>;
  gridsRef: React.MutableRefObject<Map<string, string[][]>>;
  bgGridsRef: React.MutableRefObject<Map<string, string[][]>>;
  editedKeysRef: React.MutableRefObject<Set<string>>;
  /** Set to true whenever the *current* key receives an edit; the
   *  caller resets it (via `resetHistory`) when a key is loaded. Enables
   *  the "cleared by undo" branch of the dirty check. */
  currentRoomTouchedRef: React.MutableRefObject<boolean>;
  savedUndoIndexRef: React.MutableRefObject<number>;
  /** The key the undo/redo stacks describe, or null when they're empty. Any
   *  dirty check that reads the undo depth must first confirm the stack
   *  belongs to the key it's judging -- the stacks survive a key switch until
   *  the caller's `resetHistory` effect runs. */
  historyKeyRef: React.MutableRefObject<string | null>;
  /** Included in the canvas `viewKey` so a wholesale grid rewrite (palette
   *  delete, restore) re-applies the zoom policy and drops the selection. */
  gridsVersion: number;
  bumpGridsVersion: () => void;

  // ---- History reset + save signalling ----
  resetHistory: () => void;
  markSaved: () => void;

  // ---- Layer view + link ----
  layerView: "fg" | "bg" | "both";
  setLayerView: React.Dispatch<React.SetStateAction<"fg" | "bg" | "both">>;
  effectiveLayerView: "fg" | "bg" | "both";
  showsBothLayers: boolean;
  linkLayers: boolean;
  setLinkLayers: React.Dispatch<React.SetStateAction<boolean>>;

  // ---- Grid overlay + zoom + tool ----
  showTileGrid: boolean;
  setShowTileGrid: React.Dispatch<React.SetStateAction<boolean>>;
  showRoomGrid: boolean;
  setShowRoomGrid: React.Dispatch<React.SetStateAction<boolean>>;
  zoom: number | null;
  setZoom: React.Dispatch<React.SetStateAction<number | null>>;
  tool: Tool;
  setTool: React.Dispatch<React.SetStateAction<Tool>>;

  // ---- Primary / secondary tile ----
  primary: string | null;
  secondary: string | null;
  setPrimary: React.Dispatch<React.SetStateAction<string | null>>;
  setSecondary: React.Dispatch<React.SetStateAction<string | null>>;

  // ---- Undo state ----
  undoLen: number;
  redoLen: number;
  undo: () => void;
  redo: () => void;

  // ---- Selection ----
  selection: Selection | null;
  setSelection: React.Dispatch<React.SetStateAction<Selection | null>>;
  extraSelectionRects: Selection[] | undefined;

  // ---- Derived data for TileCanvas ----
  fgCols: number;
  combinedGrid: string[][] | null;
  currentFgGrid: string[][] | null;
  currentBgGrid: string[][] | null;
  canvasSections:
    | { colStart: number; colEnd: number; label?: string }[]
    | undefined;

  // ---- Callbacks wired straight into TileCanvas ----
  handlePaint: (
    row: number,
    col: number,
    oldName: string,
    newName: string,
  ) => void;
  handleStrokeEnd: () => void;
  canPaintCell: (row: number, col: number) => boolean;
  formatHover: (
    row: number,
    col: number,
    name: string,
  ) => string | null;
  mirrorCell: () => null;
  onPick: (name: string, kind: "primary" | "secondary") => void;
  commitMarqueeMove: (
    from: Selection,
    targetRow: number,
    targetCol: number,
  ) => void;

  // ---- Marquee ops for direct invocation (right-click menus etc) ----
  commitMarqueeCopy: () => Promise<void>;
  commitMarqueeCut: () => Promise<void>;
  commitMarqueePaste: () => Promise<void>;
  commitMarqueeErase: (sel: Selection) => void;

  // ---- Low-level cell IO. Callers use these for wholesale rewrites
  //      like palette delete or save-payload construction. ----
  readLayerCell: (
    layer: CanvasLayer,
    row: number,
    gridCol: number,
  ) => string;
  writeLayerCell: (
    layer: CanvasLayer,
    row: number,
    gridCol: number,
    newName: string,
  ) => boolean;
  /** Read/write an arbitrary authored cell, whichever grid it lives in.
   *  Writes go through the undo stack exactly like a paint does. */
  readCell: (cell: RoutedCell) => string;
  writeCell: (cell: RoutedCell, newName: string) => boolean;
  /** Authored cell under a canvas coord, honouring the active router. */
  routeCell: (row: number, col: number) => RoutedCell | null;

  // ---- Layer routing helpers ----
  canvasToLayer: (
    col: number,
  ) => { layer: CanvasLayer; gridCol: number } | null;
  layerToCanvasCol: (
    layer: CanvasLayer,
    gridCol: number,
  ) => number | null;
}

/**
 * Owns the "hot path" state for a level editor's canvas: fg/bg grids,
 * undo history, marquee selection + operations, tool + view state, and
 * the paint pipeline. Editors compose it into their shell.
 */
export function useLevelCanvas(
  params: UseLevelCanvasParams,
): UseLevelCanvasReturn {
  const {
    currentKey,
    isDual,
    palette,
    cellRouter = null,
    hasSettingsOverride,
    onEditedKeysChanged,
    toast,
    mirrored = false,
  } = params;

  // ---------------------------------------------------------------------
  // State + refs
  // ---------------------------------------------------------------------
  const canvasRef = useRef<TileCanvasHandle | null>(null);
  const gridsRef = useRef<Map<string, string[][]>>(new Map());
  const bgGridsRef = useRef<Map<string, string[][]>>(new Map());
  const editedKeysRef = useRef<Set<string>>(new Set());
  const currentRoomTouchedRef = useRef(false);
  const savedUndoIndexRef = useRef(0);

  const undoStack = useRef<Stroke[]>([]);
  const redoStack = useRef<Stroke[]>([]);
  const strokeBuffer = useRef<PaintEdit[]>([]);
  /** Keys THIS history scope is responsible for having marked edited. A key
   *  already flagged before the scope opened (edited in another room, or
   *  before the last room switch) never lands here, so undoing back to the
   *  start of the scope can't clear a pip the scope didn't set. */
  const scopeKeysRef = useRef<Set<string>>(new Set());
  /** The room the undo/redo stacks currently describe, or null when they're
   *  empty. The stacks outlive a room switch by one effect pass -- the caller
   *  resets them from its own `currentKey` effect, which runs after this
   *  hook's reconcile effect -- so without this, the outgoing room's undo
   *  depth reads as "the room you just clicked into has unsaved strokes" and
   *  marks it dirty. See `reconcileEditedKeys`. */
  const historyKeyRef = useRef<string | null>(null);
  const [undoLen, setUndoLen] = useState(0);
  const [redoLen, setRedoLen] = useState(0);

  const [gridsVersion, setGridsVersion] = useState(0);
  const bumpGridsVersion = useCallback(() => {
    setGridsVersion((v) => v + 1);
  }, []);

  const [layerView, setLayerView] = useState<"fg" | "bg" | "both">("both");
  const [linkLayers, setLinkLayers] = useState(false);
  const [showTileGrid, setShowTileGrid] = useState(true);
  const [showRoomGrid, setShowRoomGrid] = useState(true);
  const [zoom, setZoom] = useState<number | null>(null);
  const [tool, setTool] = useState<Tool>("brush");
  const [primary, setPrimary] = useState<string | null>(null);
  const [secondary, setSecondary] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);

  // ---------------------------------------------------------------------
  // Derived layer state
  // ---------------------------------------------------------------------
  const currentFgGrid = useMemo<string[][] | null>(() => {
    if (!currentKey) return null;
    return gridsRef.current.get(currentKey) ?? null;
    // gridsVersion invalidates when grids are rewritten in place (palette
    // delete). currentKey changes when the caller opens a different grid.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentKey, gridsVersion]);

  const currentBgGrid = useMemo<string[][] | null>(() => {
    if (!currentKey) return null;
    return bgGridsRef.current.get(currentKey) ?? null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentKey, gridsVersion]);

  const fgCols = currentFgGrid?.[0]?.length ?? 0;

  const effectiveLayerView: "fg" | "bg" | "both" = isDual ? layerView : "fg";
  const showsBothLayers = effectiveLayerView === "both";

  // ---------------------------------------------------------------------
  // Layer routing
  // ---------------------------------------------------------------------
  // Mirror translation: converts between display gridCol (what the user
  // clicks / sees) and authored gridCol (what's stored in the grid).
  // When mirrored is false this is the identity.
  const flipGridCol = useCallback(
    (gridCol: number) => (mirrored ? fgCols - 1 - gridCol : gridCol),
    [mirrored, fgCols],
  );

  const canvasToLayer = useCallback(
    (col: number): { layer: CanvasLayer; gridCol: number } | null => {
      if (!showsBothLayers) {
        return {
          layer: effectiveLayerView === "bg" ? "background" : "foreground",
          gridCol: flipGridCol(col),
        };
      }
      if (col < fgCols) return { layer: "foreground", gridCol: flipGridCol(col) };
      if (col < fgCols + DUAL_GAP_COLS) return null;
      return {
        layer: "background",
        gridCol: flipGridCol(col - fgCols - DUAL_GAP_COLS),
      };
    },
    [effectiveLayerView, showsBothLayers, fgCols, flipGridCol],
  );

  const layerToCanvasCol = useCallback(
    (layer: CanvasLayer, gridCol: number): number | null => {
      const displayCol = flipGridCol(gridCol);
      if (!showsBothLayers) {
        const shown = effectiveLayerView === "bg" ? "background" : "foreground";
        return layer === shown ? displayCol : null;
      }
      if (layer === "foreground") return displayCol;
      return fgCols + DUAL_GAP_COLS + displayCol;
    },
    [effectiveLayerView, showsBothLayers, fgCols, flipGridCol],
  );

  // ---------------------------------------------------------------------
  // Cell routing
  //
  // Canvas coords in, authored cells out. Without a router this is just
  // "the current key, at the layer this column belongs to"; with one, each
  // canvas region can belong to a different grid entirely.
  // ---------------------------------------------------------------------
  const routeCell = useCallback(
    (row: number, col: number): RoutedCell | null => {
      if (cellRouter) return cellRouter.toCell(row, col);
      if (!currentKey) return null;
      const hit = canvasToLayer(col);
      if (!hit) return null;
      return { key: currentKey, layer: hit.layer, row, col: hit.gridCol };
    },
    [cellRouter, currentKey, canvasToLayer],
  );

  const unrouteCell = useCallback(
    (cell: RoutedCell): { row: number; col: number } | null => {
      if (cellRouter) return cellRouter.toCanvas(cell);
      if (cell.key !== currentKey) return null;
      const col = layerToCanvasCol(cell.layer, cell.col);
      return col === null ? null : { row: cell.row, col };
    },
    [cellRouter, currentKey, layerToCanvasCol],
  );

  const otherLayer = (layer: CanvasLayer): CanvasLayer =>
    layer === "foreground" ? "background" : "foreground";

  /** Link-layers mirrors every write onto the other layer of the same room.
   *  It's a property of the ONE room the canvas is showing, so it stays off
   *  in a routed (multi-room) view, where "the other layer" differs
   *  room-by-room and most slots have no second layer at all. */
  const linkActive = isDual && linkLayers && !cellRouter;

  // Reverse each row of a layer for display. Used to render the mirrored
  // authored grid; writes still go through `flipGridCol` at paint time so
  // the underlying storage stays canonical.
  const mirrorLayer = useCallback(
    (grid: string[][]) => (mirrored ? grid.map((row) => row.slice().reverse()) : grid),
    [mirrored],
  );

  const combinedGrid = useMemo<string[][] | null>(() => {
    if (!currentFgGrid) return null;
    const fg = mirrorLayer(currentFgGrid);
    if (effectiveLayerView === "fg") return fg;
    if (effectiveLayerView === "bg") {
      return mirrorLayer(
        currentBgGrid ?? currentFgGrid.map((row) => row.map(() => "")),
      );
    }
    if (!currentBgGrid) return fg;
    const bg = mirrorLayer(currentBgGrid);
    const gap = Array<string>(DUAL_GAP_COLS).fill("");
    return fg.map((row, r) => [
      ...row,
      ...gap,
      ...(bg[r] ?? row.map(() => "")),
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentFgGrid, currentBgGrid, effectiveLayerView, gridsVersion, mirrorLayer]);

  const canvasSections = useMemo(() => {
    if (!showsBothLayers) return undefined;
    return [
      { colStart: 0, colEnd: fgCols, label: "Foreground" },
      {
        colStart: fgCols + DUAL_GAP_COLS,
        colEnd: fgCols + DUAL_GAP_COLS + fgCols,
        label: "Background",
      },
    ];
  }, [showsBothLayers, fgCols]);

  const canPaintCell = useCallback(
    (row: number, col: number) => routeCell(row, col) !== null,
    [routeCell],
  );

  const formatHover = useCallback(
    (row: number, col: number, name: string): string | null => {
      const cell = routeCell(row, col);
      if (!cell) return null;
      if (!isDual) return `(${cell.col}, ${cell.row}) ${name}`;
      const label = cell.layer === "foreground" ? "Foreground" : "Background";
      return `${label} (${cell.col}, ${cell.row}) ${name}`;
    },
    [routeCell, isDual],
  );

  const mirrorCell = useCallback(() => null, []);

  // Extra selection rects: reflect the primary selection on the other
  // half when link is on AND both layers are visible.
  const extraSelectionRects = useMemo<Selection[] | undefined>(() => {
    if (!selection || !linkActive || !showsBothLayers) {
      return undefined;
    }
    const cLeft = Math.min(selection.col0, selection.col1);
    const cRight = Math.max(selection.col0, selection.col1);
    const offset = fgCols + DUAL_GAP_COLS;
    if (cRight < fgCols) {
      return [
        {
          row0: selection.row0,
          row1: selection.row1,
          col0: cLeft + offset,
          col1: cRight + offset,
        },
      ];
    }
    if (cLeft >= fgCols + DUAL_GAP_COLS) {
      return [
        {
          row0: selection.row0,
          row1: selection.row1,
          col0: cLeft - offset,
          col1: cRight - offset,
        },
      ];
    }
    return undefined;
  }, [selection, linkActive, showsBothLayers, fgCols]);

  // ---------------------------------------------------------------------
  // Cell IO
  // ---------------------------------------------------------------------
  const writeCell = useCallback(
    (cell: RoutedCell, newName: string): boolean => {
      const map =
        cell.layer === "foreground" ? gridsRef.current : bgGridsRef.current;
      const grid = map.get(cell.key);
      if (!grid || grid[cell.row]?.[cell.col] === undefined) return false;
      const prev = grid[cell.row][cell.col];
      if (prev === newName) return false;
      grid[cell.row][cell.col] = newName;
      strokeBuffer.current.push({
        key: cell.key,
        row: cell.row,
        col: cell.col,
        oldName: prev,
        newName,
        layer: cell.layer,
      });
      if (!editedKeysRef.current.has(cell.key)) {
        editedKeysRef.current.add(cell.key);
        // Only a key THIS scope flagged is a key this scope may later
        // un-flag; see scopeKeysRef.
        scopeKeysRef.current.add(cell.key);
        onEditedKeysChanged?.();
      }
      if (cell.key === currentKey) currentRoomTouchedRef.current = true;
      // Every stroke that reaches the undo stack originates here, so this is
      // the one place that knows which scope the stack belongs to.
      historyKeyRef.current = currentKey;
      const at = unrouteCell(cell);
      if (at) canvasRef.current?.setTile(at.row, at.col, newName);
      return true;
    },
    [currentKey, unrouteCell, onEditedKeysChanged],
  );

  const readCell = useCallback((cell: RoutedCell): string => {
    const map =
      cell.layer === "foreground" ? gridsRef.current : bgGridsRef.current;
    return map.get(cell.key)?.[cell.row]?.[cell.col] ?? "";
  }, []);

  // Canvas-space wrappers. Marquee ops work in these terms so a selection
  // that spans several rooms lands each cell in the right grid.
  const readCanvasCell = useCallback(
    (row: number, col: number, useOtherLayer = false): string => {
      const cell = routeCell(row, col);
      if (!cell) return "";
      return readCell(
        useOtherLayer ? { ...cell, layer: otherLayer(cell.layer) } : cell,
      );
    },
    [routeCell, readCell],
  );

  const writeCanvasCell = useCallback(
    (row: number, col: number, name: string, useOtherLayer = false): boolean => {
      const cell = routeCell(row, col);
      if (!cell) return false;
      return writeCell(
        useOtherLayer ? { ...cell, layer: otherLayer(cell.layer) } : cell,
        name,
      );
    },
    [routeCell, writeCell],
  );

  // Current-key-relative IO, kept for callers doing wholesale rewrites of
  // the open grid (palette delete, save-payload construction).
  const writeLayerCell = useCallback(
    (
      layer: CanvasLayer,
      row: number,
      gridCol: number,
      newName: string,
    ): boolean => {
      if (!currentKey) return false;
      return writeCell({ key: currentKey, layer, row, col: gridCol }, newName);
    },
    [currentKey, writeCell],
  );

  const readLayerCell = useCallback(
    (layer: CanvasLayer, row: number, gridCol: number): string => {
      if (!currentKey) return "";
      return readCell({ key: currentKey, layer, row, col: gridCol });
    },
    [currentKey, readCell],
  );

  // ---------------------------------------------------------------------
  // Paint pipeline
  // ---------------------------------------------------------------------
  const handlePaint = useCallback(
    (row: number, combinedCol: number, _oldName: string, newName: string) => {
      const cell = routeCell(row, combinedCol);
      if (!cell) return;
      writeCell(cell, newName);
      if (linkActive) {
        writeCell({ ...cell, layer: otherLayer(cell.layer) }, newName);
      }
    },
    [routeCell, writeCell, linkActive],
  );

  const handleStrokeEnd = useCallback(() => {
    if (strokeBuffer.current.length === 0) return;
    undoStack.current.push(strokeBuffer.current);
    strokeBuffer.current = [];
    redoStack.current = [];
    setUndoLen(undoStack.current.length);
    setRedoLen(0);
  }, []);

  // Ref shim for handleStrokeEnd so marquee helpers don't rebuild on
  // every linkLayers/layerView flip while still calling the latest
  // version. handlePaint isn't wrapped because marquee ops call
  // writeLayerCell directly (per-layer semantics) rather than routing
  // through handlePaint's link-mirror path.
  const handleStrokeEndRef = useRef<(() => void) | null>(null);
  const callHandleStrokeEnd = useCallback(() => {
    handleStrokeEndRef.current?.();
  }, []);
  useEffect(() => {
    handleStrokeEndRef.current = handleStrokeEnd;
  }, [handleStrokeEnd]);

  const applyStroke = useCallback(
    (stroke: Stroke, direction: "undo" | "redo") => {
      const iter = direction === "undo" ? [...stroke].reverse() : stroke;
      for (const edit of iter) {
        const map =
          edit.layer === "foreground"
            ? gridsRef.current
            : bgGridsRef.current;
        const grid = map.get(edit.key);
        if (!grid) continue;
        const target = direction === "undo" ? edit.oldName : edit.newName;
        if (grid[edit.row]?.[edit.col] !== undefined) {
          grid[edit.row][edit.col] = target;
        }
        const at = unrouteCell(edit);
        if (at) canvasRef.current?.setTile(at.row, at.col, target);
      }
    },
    [unrouteCell],
  );

  const reconcileEditedKeys = useCallback(() => {
    if (cellRouter) {
      // A routed scope edits many rooms through one undo stack, so "which
      // rooms are dirty" is exactly "which rooms are touched by the strokes
      // between the last-saved depth and where the stack sits now". Undoing
      // back past a room's last stroke drops its pip; redoing brings it back.
      const live = new Set<string>();
      const depth = undoStack.current.length;
      const saved = savedUndoIndexRef.current;
      for (let i = Math.min(saved, depth); i < depth; i++) {
        for (const edit of undoStack.current[i]) live.add(edit.key);
      }
      // Undone back BELOW the save point counts too: those rooms no longer
      // match what's on disk either. The strokes in question are the top
      // `saved - depth` entries of the redo stack.
      for (let i = 0; i < saved - depth; i++) {
        const stroke = redoStack.current[redoStack.current.length - 1 - i];
        if (!stroke) break;
        for (const edit of stroke) live.add(edit.key);
      }
      let changed = false;
      for (const key of scopeKeysRef.current) {
        const shouldBePresent =
          live.has(key) || (hasSettingsOverride?.(key) ?? false);
        const wasPresent = editedKeysRef.current.has(key);
        if (shouldBePresent && !wasPresent) {
          editedKeysRef.current.add(key);
          changed = true;
        } else if (!shouldBePresent && wasPresent) {
          editedKeysRef.current.delete(key);
          changed = true;
        }
      }
      if (changed) onEditedKeysChanged?.();
      return;
    }
    if (!currentKey) return;
    // Only trust the undo depth when the stack actually describes this room.
    // On a room switch this effect re-runs (currentKey is a dep) before the
    // caller's resetHistory lands, and the outgoing room's strokes would
    // otherwise mark the incoming room dirty.
    const strokesDirty =
      historyKeyRef.current === currentKey &&
      undoStack.current.length !== savedUndoIndexRef.current;
    const settingsSet = hasSettingsOverride?.(currentKey) ?? false;
    const wasPresent = editedKeysRef.current.has(currentKey);
    const shouldBePresent = strokesDirty || settingsSet;
    if (shouldBePresent && !wasPresent) {
      editedKeysRef.current.add(currentKey);
      onEditedKeysChanged?.();
    } else if (
      !shouldBePresent &&
      wasPresent &&
      currentRoomTouchedRef.current
    ) {
      editedKeysRef.current.delete(currentKey);
      onEditedKeysChanged?.();
    }
  }, [cellRouter, currentKey, hasSettingsOverride, onEditedKeysChanged]);

  const undo = useCallback(() => {
    const stroke = undoStack.current.pop();
    if (!stroke) return;
    applyStroke(stroke, "undo");
    redoStack.current.push(stroke);
    setUndoLen(undoStack.current.length);
    setRedoLen(redoStack.current.length);
    reconcileEditedKeys();
  }, [applyStroke, reconcileEditedKeys]);

  const redo = useCallback(() => {
    const stroke = redoStack.current.pop();
    if (!stroke) return;
    applyStroke(stroke, "redo");
    undoStack.current.push(stroke);
    setUndoLen(undoStack.current.length);
    setRedoLen(redoStack.current.length);
    reconcileEditedKeys();
  }, [applyStroke, reconcileEditedKeys]);

  // Also reconcile whenever a paint stroke commits so the pip clears on
  // undo-to-baseline without waiting for the next undo/redo.
  useEffect(() => {
    reconcileEditedKeys();
  }, [undoLen, reconcileEditedKeys]);

  const resetHistory = useCallback(() => {
    undoStack.current = [];
    redoStack.current = [];
    strokeBuffer.current = [];
    savedUndoIndexRef.current = 0;
    currentRoomTouchedRef.current = false;
    historyKeyRef.current = null;
    scopeKeysRef.current = new Set();
    setUndoLen(0);
    setRedoLen(0);
  }, []);

  const markSaved = useCallback(() => {
    savedUndoIndexRef.current = undoStack.current.length;
    strokeBuffer.current = [];
  }, []);

  // ---------------------------------------------------------------------
  // Marquee ops
  // ---------------------------------------------------------------------
  /** Snapshot a canvas-space rect. `useOtherLayer` reads each cell's
   *  opposite layer instead, which is how the linked copy grabs the
   *  background half without assuming the selection sits on the fg side. */
  const snapshotRect = useCallback(
    (
      rTop: number,
      cLeft: number,
      rows: number,
      cols: number,
      useOtherLayer = false,
    ): string[][] => {
      const out: string[][] = [];
      for (let r = 0; r < rows; r++) {
        const row: string[] = [];
        for (let c = 0; c < cols; c++) {
          row.push(readCanvasCell(rTop + r, cLeft + c, useOtherLayer));
        }
        out.push(row);
      }
      return out;
    },
    [readCanvasCell],
  );

  const serializeSelection = useCallback(
    (sel: Selection): string => {
      const rTop = Math.min(sel.row0, sel.row1);
      const rBot = Math.max(sel.row0, sel.row1);
      const cLeft = Math.min(sel.col0, sel.col1);
      const cRight = Math.max(sel.col0, sel.col1);
      const rows = rBot - rTop + 1;
      const cols = cRight - cLeft + 1;
      // "fg"/"bg" in the payload mean "the layer the selection was on" and
      // "the other one" -- a paste re-anchors both against wherever it
      // lands rather than hard-coding front and back.
      const payload = linkActive
        ? {
            kind: "modlunky2-region",
            version: 2,
            width: cols,
            height: rows,
            fg: snapshotRect(rTop, cLeft, rows, cols),
            bg: snapshotRect(rTop, cLeft, rows, cols, true),
          }
        : {
            kind: "modlunky2-region",
            version: 1,
            width: cols,
            height: rows,
            cells: snapshotRect(rTop, cLeft, rows, cols),
          };
      return JSON.stringify(payload);
    },
    [snapshotRect, linkActive],
  );

  const commitMarqueeCopy = useCallback(async () => {
    if (!selection) return;
    try {
      await writeClipboardText(serializeSelection(selection));
      toast.success("Copied selection.");
    } catch (err) {
      toast.error(`Copy failed: ${extractMessage(err)}`);
    }
  }, [selection, serializeSelection, toast]);

  const commitMarqueeErase = useCallback(
    (sel: Selection) => {
      const rTop = Math.min(sel.row0, sel.row1);
      const rBot = Math.max(sel.row0, sel.row1);
      const cLeft = Math.min(sel.col0, sel.col1);
      const cRight = Math.max(sel.col0, sel.col1);
      const eraseName = palette.find((p) => p.name === "empty")?.name ?? "";
      for (let r = rTop; r <= rBot; r++) {
        for (let c = cLeft; c <= cRight; c++) {
          writeCanvasCell(r, c, eraseName);
          if (linkActive) writeCanvasCell(r, c, eraseName, true);
        }
      }
      callHandleStrokeEnd();
    },
    [palette, writeCanvasCell, linkActive, callHandleStrokeEnd],
  );

  const commitMarqueeCut = useCallback(async () => {
    if (!selection) return;
    await commitMarqueeCopy();
    commitMarqueeErase(selection);
  }, [selection, commitMarqueeCopy, commitMarqueeErase]);

  const commitMarqueePaste = useCallback(async () => {
    if (!currentKey) return;
    let text = "";
    try {
      text = await readClipboardText();
    } catch (err) {
      toast.error(`Read clipboard failed: ${extractMessage(err)}`);
      return;
    }
    let payload: {
      kind?: string;
      version?: number;
      width?: number;
      height?: number;
      cells?: string[][];
      fg?: string[][];
      bg?: string[][];
    };
    try {
      payload = JSON.parse(text);
    } catch {
      toast.error("Clipboard is not a modlunky2 region.");
      return;
    }
    if (!payload || payload.kind !== "modlunky2-region") {
      toast.error("Clipboard is not a modlunky2 region.");
      return;
    }
    const anchor = selection
      ? {
          row: Math.min(selection.row0, selection.row1),
          col: Math.min(selection.col0, selection.col1),
        }
      : canvasRef.current?.getHoverCell() ?? { row: 0, col: 0 };
    const paletteSet = new Set(palette.map((p) => p.name));
    const fallback = paletteSet.has("empty") ? "empty" : "";
    const sanitize = (name: unknown): string => {
      if (typeof name !== "string") return fallback;
      if (name === "" || paletteSet.has(name)) return name;
      return fallback;
    };
    // Cells land relative to the anchor in CANVAS space, so a paste that
    // runs off the end of a room (or across a spacer) drops the cells with
    // nowhere to go instead of folding them into the wrong grid.
    const writeGrid = (cells: string[][], useOtherLayer = false) => {
      for (let r = 0; r < cells.length; r++) {
        const row = cells[r];
        if (!Array.isArray(row)) continue;
        for (let c = 0; c < row.length; c++) {
          writeCanvasCell(
            anchor.row + r,
            anchor.col + c,
            sanitize(row[c]),
            useOtherLayer,
          );
        }
      }
    };
    if (Array.isArray(payload.fg) || Array.isArray(payload.bg)) {
      if (Array.isArray(payload.fg)) writeGrid(payload.fg);
      if (Array.isArray(payload.bg)) writeGrid(payload.bg, true);
    } else if (Array.isArray(payload.cells)) {
      writeGrid(payload.cells);
      if (linkActive) writeGrid(payload.cells, true);
    } else {
      toast.error("Clipboard is not a modlunky2 region.");
      return;
    }
    callHandleStrokeEnd();
    toast.success("Pasted selection.");
  }, [
    currentKey,
    selection,
    palette,
    writeCanvasCell,
    linkActive,
    callHandleStrokeEnd,
    toast,
  ]);

  const commitMarqueeMove = useCallback(
    (from: Selection, targetRow: number, targetCol: number) => {
      const rTop = Math.min(from.row0, from.row1);
      const rBot = Math.max(from.row0, from.row1);
      const cLeft = Math.min(from.col0, from.col1);
      const cRight = Math.max(from.col0, from.col1);
      const width = cRight - cLeft + 1;
      const height = rBot - rTop + 1;
      if (targetRow === rTop && targetCol === cLeft) return;
      const eraseName = palette.find((p) => p.name === "empty")?.name ?? "";
      // Lift, clear, drop -- in that order, so a move onto overlapping
      // ground doesn't erase what it just wrote.
      const passes = linkActive ? [false, true] : [false];
      const snapshots = passes.map((useOther) =>
        snapshotRect(rTop, cLeft, height, width, useOther),
      );
      for (let r = 0; r < height; r++) {
        for (let c = 0; c < width; c++) {
          for (const useOther of passes) {
            writeCanvasCell(rTop + r, cLeft + c, eraseName, useOther);
          }
        }
      }
      passes.forEach((useOther, i) => {
        const snap = snapshots[i];
        for (let r = 0; r < height; r++) {
          for (let c = 0; c < width; c++) {
            writeCanvasCell(targetRow + r, targetCol + c, snap[r][c], useOther);
          }
        }
      });
      callHandleStrokeEnd();
      const next: Selection = {
        row0: targetRow,
        col0: targetCol,
        row1: targetRow + height - 1,
        col1: targetCol + width - 1,
      };
      setSelection(next);
      canvasRef.current?.setSelection(next);
    },
    [palette, snapshotRect, writeCanvasCell, linkActive, callHandleStrokeEnd],
  );

  const onPick = useCallback(
    (name: string, kind: "primary" | "secondary") => {
      if (kind === "primary") setPrimary(name);
      else setSecondary(name);
    },
    [],
  );

  // ---------------------------------------------------------------------
  // Keyboard shortcuts (canvas-scoped).
  //
  // - B / G / U / E / I / M: tool switch
  // - Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y: undo / redo
  // - Ctrl+C / Ctrl+X / Ctrl+V: marquee clipboard (only while tool==marquee)
  // - Delete: erase selection (marquee only)
  // - Escape: clear selection
  //
  // Editors keep their own top-level keydown listener for Ctrl+S and any
  // mode-specific shortcuts (Tab for room/level in Vanilla) and DO NOT
  // need to duplicate this logic.
  // ---------------------------------------------------------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const inText =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (inText) return;
      const isCtrl = e.ctrlKey || e.metaKey;
      if (isCtrl) {
        if (e.code === "KeyZ") {
          e.preventDefault();
          if (e.shiftKey) redo();
          else undo();
        } else if (e.code === "KeyY") {
          e.preventDefault();
          redo();
        } else if (e.code === "KeyC" && tool === "marquee" && selection) {
          e.preventDefault();
          void commitMarqueeCopy();
        } else if (e.code === "KeyX" && tool === "marquee" && selection) {
          e.preventDefault();
          void commitMarqueeCut();
        } else if (e.code === "KeyV" && tool === "marquee") {
          e.preventDefault();
          void commitMarqueePaste();
        }
        return;
      }
      if (e.altKey || e.shiftKey) return;
      if (e.code === "KeyB") setTool("brush");
      else if (e.code === "KeyG") setTool("bucket");
      else if (e.code === "KeyU") setTool("rect");
      else if (e.code === "KeyE") setTool("eraser");
      else if (e.code === "KeyI") setTool("eyedropper");
      else if (e.code === "KeyM") setTool("marquee");
      else if (e.code === "Delete" && tool === "marquee" && selection) {
        e.preventDefault();
        commitMarqueeErase(selection);
      } else if (e.code === "Escape" && selection) {
        e.preventDefault();
        setSelection(null);
        canvasRef.current?.setSelection(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    undo,
    redo,
    tool,
    selection,
    commitMarqueeCopy,
    commitMarqueeCut,
    commitMarqueePaste,
    commitMarqueeErase,
  ]);

  // Clear selection on grid switch. Reset layerView to default so a
  // freshly-loaded grid doesn't inherit the previous one's preference.
  useEffect(() => {
    setSelection(null);
    setLayerView("both");
    // resetHistory is called from the caller inside its load effect so
    // the two lifecycles stay explicit.
  }, [currentKey]);

  return {
    canvasRef,
    gridsRef,
    bgGridsRef,
    editedKeysRef,
    currentRoomTouchedRef,
    savedUndoIndexRef,
    historyKeyRef,
    gridsVersion,
    bumpGridsVersion,
    resetHistory,
    markSaved,

    layerView,
    setLayerView,
    effectiveLayerView,
    showsBothLayers,
    linkLayers,
    setLinkLayers,

    showTileGrid,
    setShowTileGrid,
    showRoomGrid,
    setShowRoomGrid,
    zoom,
    setZoom,
    tool,
    setTool,

    primary,
    secondary,
    setPrimary,
    setSecondary,

    undoLen,
    redoLen,
    undo,
    redo,

    selection,
    setSelection,
    extraSelectionRects,

    fgCols,
    combinedGrid,
    currentFgGrid,
    currentBgGrid,
    canvasSections,

    handlePaint,
    handleStrokeEnd,
    canPaintCell,
    formatHover,
    mirrorCell,
    onPick,
    commitMarqueeMove,

    commitMarqueeCopy,
    commitMarqueeCut,
    commitMarqueePaste,
    commitMarqueeErase,

    readLayerCell,
    writeLayerCell,
    readCell,
    writeCell,
    routeCell,
    canvasToLayer,
    layerToCanvasCol,
  };
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
