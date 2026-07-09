// Sidebar palette pane shared by the Vanilla and Custom editors.
//
// Renders:
//  - "Palette" title with reorder-lock + help buttons (and an optional
//    conflicts button for Vanilla only)
//  - Left/right hint under the title
//  - The LevelPalette itself, wired to the palette-editor hook
//  - The PaletteHelpModal when opened
//  - The delete-confirm modal when the hook has a pending delete
//
// AddTile is deliberately still parent-owned. Vanilla's version has
// inheritance-aware code allocation with a collision confirm flow that
// Custom doesn't need, so keeping handleAddTile in the parent avoids a
// forked add path in shared code.

import {
  AlertTriangle,
  HelpCircle,
  LayoutGrid,
  Lock,
  LockOpen,
} from "lucide-react";
import type {
  CustomLevelPaletteEntry,
  EditorAtlas,
} from "../../lib/commands";
import { LevelPalette } from "./LevelPalette";
import { Modal } from "../shared/Modal";
import { PaletteHelpModal } from "./PaletteHelpModal";
import type { PaletteEditor } from "./hooks/usePaletteEditor";

interface Props {
  pal: PaletteEditor;
  /** Palette list owned by the parent (needed by useLevelCanvas too). */
  palette: CustomLevelPaletteEntry[];
  atlas: EditorAtlas | null;
  /** Enables the reorder-lock button + the "Add tile" affordance. The
   *  vanilla editor uses "did the user pick a level file yet"; custom
   *  uses "is a level open right now". Same shape either way: null
   *  disables both. */
  selectedFile: string | null;
  primary: string | null;
  secondary: string | null;
  onSelectPrimary: (name: string) => void;
  onSelectSecondary: (name: string) => void;
  /** Parent-owned add flow. When omitted, the palette hides its "+"
   *  affordance (e.g. no file loaded yet). */
  onOpenAddTile?: () => void;
  /** Vanilla-only: number of sister-file tilecode conflicts. Non-empty
   *  renders an alert button next to the reorder-lock; clicking it
   *  invokes onOpenConflicts. Custom levels don't inherit from sister
   *  files, so this pair is unused there. */
  conflictCount?: number;
  onOpenConflicts?: () => void;
  /** Which set of help text the modal should show. Vanilla mentions
   *  sibling / parent files; custom omits that section entirely. */
  helpMode: "vanilla" | "custom";
  /** Persistent icon-only palette toggle (shared editor pref). Reorder mode
   *  ignores it and keeps the full rows so drag/delete stay usable. */
  dense: boolean;
  onToggleDense: () => void;
}

export function PaletteSidebarSection({
  pal,
  palette,
  atlas,
  selectedFile,
  primary,
  secondary,
  onSelectPrimary,
  onSelectSecondary,
  onOpenAddTile,
  conflictCount,
  onOpenConflicts,
  helpMode,
  dense,
  onToggleDense,
}: Props) {
  const {
    swatchOverrides,
    paletteHelpOpen,
    setPaletteHelpOpen,
    paletteReorderMode,
    setPaletteReorderMode,
    pendingPaletteDelete,
    setPendingPaletteDelete,
    handleReorder,
    handlePaletteDelete,
    confirmPaletteDelete,
  } = pal;

  return (
    <>
      <div className="editor-window-section-title editor-window-palette-title">
        <span>Palette</span>
        <div className="editor-window-palette-actions">
          {conflictCount !== undefined && conflictCount > 0 && onOpenConflicts && (
            <button
              type="button"
              className="editor-window-palette-icon"
              onClick={onOpenConflicts}
              title={`${conflictCount} tilecode conflict${conflictCount === 1 ? "" : "s"} with sister-location files. Click to review.`}
              aria-label={`Show ${conflictCount} tilecode conflict${conflictCount === 1 ? "" : "s"}`}
            >
              <AlertTriangle size={14} aria-hidden="true" />
            </button>
          )}
          <button
            type="button"
            className={`editor-window-palette-icon${dense ? " active" : ""}`}
            onClick={onToggleDense}
            onMouseDown={(e) => e.preventDefault()}
            title={
              dense
                ? "Expanded palette (show names)"
                : "Compact palette (icon-only, wraps)"
            }
            aria-pressed={dense}
          >
            <LayoutGrid size={14} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={`editor-window-palette-icon${paletteReorderMode ? " active" : ""}`}
            onClick={() => setPaletteReorderMode((v) => !v)}
            onMouseDown={(e) => e.preventDefault()}
            title={
              !selectedFile
                ? "Open a file to reorder its palette"
                : paletteReorderMode
                  ? "Exit reorder mode"
                  : "Enter reorder mode to drag tiles"
            }
            aria-pressed={paletteReorderMode}
            disabled={!selectedFile}
          >
            {paletteReorderMode ? (
              <LockOpen size={14} aria-hidden="true" />
            ) : (
              <Lock size={14} aria-hidden="true" />
            )}
          </button>
          <button
            type="button"
            className="editor-window-palette-icon"
            onClick={() => setPaletteHelpOpen(true)}
            title="How to use the palette"
            aria-label="Palette help"
          >
            <HelpCircle size={14} aria-hidden="true" />
          </button>
        </div>
      </div>
      <div className="editor-window-palette-hint">
        Left-click sets L (primary), right-click sets R (secondary).
      </div>
      <LevelPalette
        palette={palette}
        atlas={atlas}
        swatchOverrides={swatchOverrides}
        primaryName={primary}
        secondaryName={secondary}
        onSelectPrimary={onSelectPrimary}
        onSelectSecondary={onSelectSecondary}
        onOpenAddTile={onOpenAddTile}
        onReorder={handleReorder}
        onDelete={handlePaletteDelete}
        reorderMode={paletteReorderMode}
        dense={dense && !paletteReorderMode}
      />
      {paletteHelpOpen && (
        <PaletteHelpModal
          mode={helpMode}
          onClose={() => setPaletteHelpOpen(false)}
        />
      )}
      {pendingPaletteDelete && (
        <Modal
          open
          onClose={() => setPendingPaletteDelete(null)}
          title="Delete tile from palette"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setPendingPaletteDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={confirmPaletteDelete}
              >
                Delete and replace
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            <code>{pendingPaletteDelete.name}</code> is used in{" "}
            <strong>{pendingPaletteDelete.count}</strong> cell
            {pendingPaletteDelete.count === 1 ? "" : "s"} in this level.
            Deleting will replace every use with{" "}
            {pendingPaletteDelete.replacement ? (
              <>
                <code>{pendingPaletteDelete.replacement}</code>.
              </>
            ) : (
              <>an empty cell (no other palette entries remain).</>
            )}
          </p>
          <p className="editor-confirm-warn">
            This can't be undone. Save the file first if you want to keep
            the current state as a fallback.
          </p>
        </Modal>
      )}
    </>
  );
}
