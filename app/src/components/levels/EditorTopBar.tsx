// Shared top bar for the level editors. Owns the title area, the
// primary/secondary tile indicators, the tool strip, undo/redo, and the
// Restore + Save buttons. Editor-specific widgets (Vanilla's Room/Level
// view toggle, future Custom-only knobs) come in through the `centerExtras`
// slot so both editors line up without either owning the layout.

import {
  BoxSelect,
  Eraser,
  PaintBucket,
  Paintbrush,
  Pipette,
  Square,
} from "lucide-react";
import type { Tool } from "./TileCanvas";

interface Props {
  /** Full title area content (pack + editor label + optional file/room). */
  title: React.ReactNode;
  primary: string | null;
  secondary: string | null;
  tool: Tool;
  onSetTool: (t: Tool) => void;
  undoLen: number;
  redoLen: number;
  onUndo: () => void;
  onRedo: () => void;
  /** True when Restore + Save should be enabled. Callers usually AND their
   *  dirty flag with a "has a file open" check and pass the result. */
  canSave: boolean;
  saving: boolean;
  onRestore?: () => void;
  onSave: () => void;
  /** Rendered between the tile indicators and the tool strip. Vanilla uses
   *  this for its Room/Level view toggle. */
  centerExtras?: React.ReactNode;
  /** Rendered between Redo and Restore. For editor-specific knobs. */
  rightExtras?: React.ReactNode;
  /** Rendered after Save, at the far right. Meant for editor-wide shell
   *  actions (e.g. the settings gear) that need to stay visually
   *  separate from the per-session toolbar and per-file save. */
  farRightExtras?: React.ReactNode;
}

function ToolButton({
  active,
  onSelect,
  title,
  label,
  children,
}: {
  active: boolean;
  onSelect: () => void;
  title: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      className={`editor-tool-btn${active ? " active" : ""}`}
      onClick={onSelect}
      onMouseDown={(e) => e.preventDefault()}
      title={title}
      aria-label={label}
      aria-pressed={active}
    >
      {children}
    </button>
  );
}

export function EditorTopBar({
  title,
  primary,
  secondary,
  tool,
  onSetTool,
  undoLen,
  redoLen,
  onUndo,
  onRedo,
  canSave,
  saving,
  onRestore,
  onSave,
  centerExtras,
  rightExtras,
  farRightExtras,
}: Props) {
  return (
    <header className="editor-window-topbar">
      <div className="editor-window-title">{title}</div>
      <div className="editor-window-toolbar">
        <div className="editor-window-current-tiles">
          <span className="editor-window-tile-slot primary">
            <span className="editor-window-tile-key">L</span>
            <span className="editor-window-tile-name">
              {primary ?? "unset"}
            </span>
          </span>
          <span className="editor-window-tile-slot secondary">
            <span className="editor-window-tile-key">R</span>
            <span className="editor-window-tile-name">
              {secondary ?? "unset"}
            </span>
          </span>
        </div>
        {centerExtras}
        <div
          className="editor-window-tools"
          role="toolbar"
          aria-label="Paint tools"
        >
          <ToolButton
            active={tool === "brush"}
            onSelect={() => onSetTool("brush")}
            title="Brush (B)"
            label="Brush"
          >
            <Paintbrush size={16} aria-hidden="true" />
          </ToolButton>
          <ToolButton
            active={tool === "bucket"}
            onSelect={() => onSetTool("bucket")}
            title="Bucket fill (G)"
            label="Bucket"
          >
            <PaintBucket size={16} aria-hidden="true" />
          </ToolButton>
          <ToolButton
            active={tool === "rect"}
            onSelect={() => onSetTool("rect")}
            title="Rectangle (U)"
            label="Rectangle"
          >
            <Square size={16} aria-hidden="true" />
          </ToolButton>
          <ToolButton
            active={tool === "eraser"}
            onSelect={() => onSetTool("eraser")}
            title="Eraser (E)"
            label="Eraser"
          >
            <Eraser size={16} aria-hidden="true" />
          </ToolButton>
          <ToolButton
            active={tool === "eyedropper"}
            onSelect={() => onSetTool("eyedropper")}
            title="Eyedropper (I)"
            label="Eyedropper"
          >
            <Pipette size={16} aria-hidden="true" />
          </ToolButton>
          <ToolButton
            active={tool === "marquee"}
            onSelect={() => onSetTool("marquee")}
            title="Marquee select (M). Ctrl+C copy, Ctrl+X cut, Ctrl+V paste, Del erase, drag inside to move."
            label="Marquee"
          >
            <BoxSelect size={16} aria-hidden="true" />
          </ToolButton>
        </div>
        <div className="editor-window-history">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onUndo}
            disabled={undoLen === 0}
            title="Undo (Ctrl+Z)"
          >
            Undo
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onRedo}
            disabled={redoLen === 0}
            title="Redo (Ctrl+Shift+Z)"
          >
            Redo
          </button>
        </div>
        {rightExtras}
        {onRestore && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onRestore}
            disabled={!canSave || saving}
            title="Discard unsaved changes and reload from disk"
          >
            Restore
          </button>
        )}
        <button
          type="button"
          className="btn btn-primary"
          onClick={onSave}
          disabled={!canSave || saving}
          title="Save (Ctrl+S)"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        {farRightExtras}
      </div>
    </header>
  );
}
