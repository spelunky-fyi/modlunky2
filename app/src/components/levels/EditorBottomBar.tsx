// Bottom bar that sits directly under the room canvas. Left half is a
// photoshop-style zoom widget (out / editable text / in / fit) that stays in
// sync with the TileCanvas's actual zoom via `zoom` prop + `onSetZoom`
// callback. Right half is the current room's template-settings flags,
// rendered inline as compact checkboxes so they don't eat vertical space in
// the sidebar.

import { useEffect, useRef, useState } from "react";
import {
  FlipHorizontal2,
  Frame,
  Grid3x3,
  Link2,
  Link2Off,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  TEMPLATE_SETTING_HINTS,
  TEMPLATE_SETTING_LABELS,
  TEMPLATE_SETTING_NAMES,
  type TemplateSettingName,
} from "../../lib/commands";
import "./EditorBottomBar.css";

interface Props {
  /** Current zoom as a multiplier (1 = 100%). Null = no canvas mounted yet. */
  zoom: number | null;
  /** Whether the room-settings section applies (a room is open). */
  roomOpen: boolean;
  /** Whether the current room has locally-modified settings. */
  roomSettingsEdited: boolean;
  /** Active setting names on the current room. */
  roomSettings: TemplateSettingName[];
  /** Whether the current room is dual (has both layers). Layer-view toggle
   *  + link toggle only make sense when true. */
  isDual?: boolean;
  /** Current layer-link state. Only used when isDual is true. */
  linkLayers?: boolean;
  /** Which layer(s) the canvas is showing. Only used when isDual is true. */
  layerView?: "fg" | "bg" | "both";
  /** Fine per-tile grid overlay visible. */
  showTileGrid?: boolean;
  /** Room-boundary grid overlay visible. */
  showRoomGrid?: boolean;
  onSetZoom: (zoom: number) => void;
  onZoomToFit: () => void;
  onToggleSetting: (name: TemplateSettingName, next: boolean) => void;
  onToggleLinkLayers?: () => void;
  onSetLayerView?: (view: "fg" | "bg" | "both") => void;
  onSetShowTileGrid?: (next: boolean) => void;
  onSetShowRoomGrid?: (next: boolean) => void;
  /** Mirror-preview affordance. `mode` picks the copy: "off" hides the
   *  button entirely, "flip" shows a togglable preview (game may or may
   *  not mirror at runtime), "onlyflip" indicates the game always
   *  mirrors so we suggest keeping it on. */
  mirrorMode?: "off" | "flip" | "onlyflip";
  mirrored?: boolean;
  onSetMirrored?: (next: boolean) => void;
  /** How multi-cell sprites render on the canvas. "natural" lets them
   *  overflow their placement cell (matches the game); "cell" clamps to
   *  a single cell so authors can see the anchor. */
  renderMode?: "natural" | "cell";
  onSetRenderMode?: (next: "natural" | "cell") => void;
  /** Rendered at the right edge of the top row, right of Link Layers and
   *  right-aligned via margin-left auto. Meant for pack-level "settings"
   *  affordances (Level config, Sequence) that need to stay visually
   *  separate from the paint toolbar. */
  trailingActions?: React.ReactNode;
}

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 8;
const ZOOM_STEP = 1.25;

export function EditorBottomBar({
  zoom,
  roomOpen,
  roomSettingsEdited,
  roomSettings,
  isDual = false,
  linkLayers = false,
  layerView = "both",
  showTileGrid = true,
  showRoomGrid = true,
  onSetZoom,
  onZoomToFit,
  onToggleSetting,
  onToggleLinkLayers,
  onSetLayerView,
  onSetShowTileGrid,
  onSetShowRoomGrid,
  mirrorMode = "off",
  mirrored = false,
  onSetMirrored,
  renderMode = "natural",
  onSetRenderMode,
  trailingActions,
}: Props) {
  const zoomPct = zoom == null ? null : Math.round(zoom * 100);
  const [zoomInput, setZoomInput] = useState<string>(
    zoomPct == null ? "" : `${zoomPct}%`,
  );
  const [zoomFocused, setZoomFocused] = useState(false);

  // Sync the text input with prop changes unless the user is currently
  // editing it (mid-typing).
  useEffect(() => {
    if (zoomFocused) return;
    setZoomInput(zoomPct == null ? "" : `${zoomPct}%`);
  }, [zoomPct, zoomFocused]);

  const commitZoom = (raw: string) => {
    const stripped = raw.trim().replace(/%$/, "");
    const parsed = Number(stripped);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      // Reset to the current zoom on invalid input.
      setZoomInput(zoomPct == null ? "" : `${zoomPct}%`);
      return;
    }
    const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, parsed / 100));
    onSetZoom(next);
  };

  const zoomOut = () => {
    if (zoom == null) return;
    onSetZoom(Math.max(ZOOM_MIN, zoom / ZOOM_STEP));
  };
  const zoomIn = () => {
    if (zoom == null) return;
    onSetZoom(Math.min(ZOOM_MAX, zoom * ZOOM_STEP));
  };

  const activeSet = new Set(roomSettings);

  return (
    <div className="editor-bottombar">
      <div className="editor-bottombar-zoom">
        <button
          type="button"
          className="editor-bottombar-icon-btn"
          onClick={zoomOut}
          disabled={zoom == null || zoom <= ZOOM_MIN + 1e-6}
          title="Zoom out"
          aria-label="Zoom out"
        >
          <ZoomOut size={14} aria-hidden="true" />
        </button>
        <input
          type="text"
          className="editor-bottombar-zoom-input"
          value={zoomInput}
          onChange={(e) => setZoomInput(e.target.value)}
          onFocus={(e) => {
            setZoomFocused(true);
            e.target.select();
          }}
          onBlur={(e) => {
            setZoomFocused(false);
            commitZoom(e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              (e.target as HTMLInputElement).blur();
            } else if (e.key === "Escape") {
              setZoomInput(zoomPct == null ? "" : `${zoomPct}%`);
              (e.target as HTMLInputElement).blur();
            }
          }}
          disabled={zoom == null}
          spellCheck={false}
          aria-label="Zoom percent"
        />
        <button
          type="button"
          className="editor-bottombar-icon-btn"
          onClick={zoomIn}
          disabled={zoom == null || zoom >= ZOOM_MAX - 1e-6}
          title="Zoom in"
          aria-label="Zoom in"
        >
          <ZoomIn size={14} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="editor-bottombar-fit"
          onClick={onZoomToFit}
          disabled={zoom == null}
          title="Fit room to view"
        >
          Fit
        </button>
      </div>

      {(onSetShowTileGrid || onSetShowRoomGrid) && (
        <GridSettingsPopover
          showTileGrid={showTileGrid}
          showRoomGrid={showRoomGrid}
          onSetShowTileGrid={onSetShowTileGrid}
          onSetShowRoomGrid={onSetShowRoomGrid}
        />
      )}

      {isDual && onSetLayerView && (
        <div
          className="editor-bottombar-layerview"
          role="group"
          aria-label="Layers to show"
        >
          {(
            [
              { key: "fg", label: "FG", title: "Foreground only" },
              { key: "bg", label: "BG", title: "Background only" },
              { key: "both", label: "Both", title: "Side by side" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.key}
              type="button"
              className={`editor-bottombar-layerview-btn${layerView === opt.key ? " active" : ""}`}
              onClick={() => onSetLayerView(opt.key)}
              onMouseDown={(e) => e.preventDefault()}
              title={opt.title}
              aria-pressed={layerView === opt.key}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {isDual && onToggleLinkLayers && (
        <button
          type="button"
          className={`editor-bottombar-link${linkLayers ? " active" : ""}`}
          onClick={onToggleLinkLayers}
          onMouseDown={(e) => e.preventDefault()}
          title={
            linkLayers
              ? "Layers linked, paints mirror between foreground and background"
              : "Link layers, mirror paints between foreground and background"
          }
          aria-pressed={linkLayers}
        >
          {linkLayers ? (
            <Link2 size={14} aria-hidden="true" />
          ) : (
            <Link2Off size={14} aria-hidden="true" />
          )}
          <span>Layers</span>
        </button>
      )}



      {onSetRenderMode && (
        <button
          type="button"
          className={`editor-bottombar-link${renderMode === "cell" ? " active" : ""}`}
          onClick={() =>
            onSetRenderMode(renderMode === "natural" ? "cell" : "natural")
          }
          onMouseDown={(e) => e.preventDefault()}
          title={
            renderMode === "cell"
              ? "Sprites clamped to their placement cell so anchor positions are visible. Click to render at natural size."
              : "Sprites render at natural size, extending into neighbouring cells. Click to clamp every sprite to its placement cell."
          }
          aria-pressed={renderMode === "cell"}
        >
          <Frame size={14} aria-hidden="true" />
          <span>Clamp</span>
        </button>
      )}
      {mirrorMode !== "off" && onSetMirrored && (
        <button
          type="button"
          className={`editor-bottombar-link${mirrored ? " active" : ""}`}
          onClick={() => onSetMirrored(!mirrored)}
          onMouseDown={(e) => e.preventDefault()}
          title={
            mirrorMode === "onlyflip"
              ? "Only-flip: game always renders this room mirrored. Toggle off to edit the un-mirrored source."
              : "Flip: game may render this room mirrored at runtime. Toggle to preview."
          }
          aria-pressed={mirrored}
        >
          <FlipHorizontal2 size={14} aria-hidden="true" />
          <span>{mirrorMode === "onlyflip" ? "Mirrored" : "Preview flip"}</span>
        </button>
      )}

      {trailingActions && (
        <div className="editor-bottombar-trailing">{trailingActions}</div>
      )}

      {roomOpen && (
        <div className="editor-bottombar-settings">
          <span className="editor-bottombar-settings-label">
            Room Flags
            {roomSettingsEdited && (
              <span className="editor-bottombar-settings-dirty">•</span>
            )}
          </span>
          {TEMPLATE_SETTING_NAMES.map((name) => {
            const checked = activeSet.has(name);
            return (
              <label
                key={name}
                className={`editor-bottombar-setting${checked ? " on" : ""}`}
                title={TEMPLATE_SETTING_HINTS[name]}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => onToggleSetting(name, e.target.checked)}
                />
                <span>{TEMPLATE_SETTING_LABELS[name]}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface GridSettingsProps {
  showTileGrid: boolean;
  showRoomGrid: boolean;
  onSetShowTileGrid?: (next: boolean) => void;
  onSetShowRoomGrid?: (next: boolean) => void;
}

// Grid overlay settings popover. Opens on the button, closes on outside
// click / Escape. Two independent checkboxes for the fine tile grid and
// the heavier room boundary grid.
function GridSettingsPopover({
  showTileGrid,
  showRoomGrid,
  onSetShowTileGrid,
  onSetShowRoomGrid,
}: GridSettingsProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="editor-bottombar-grid-wrap" ref={wrapRef}>
      <button
        type="button"
        className={`editor-bottombar-grid-btn${open ? " active" : ""}`}
        onClick={() => setOpen((v) => !v)}
        onMouseDown={(e) => e.preventDefault()}
        title="Grid overlay settings"
        aria-expanded={open}
      >
        <Grid3x3 size={14} aria-hidden="true" />
        <span>Grid</span>
      </button>
      {open && (
        <div className="editor-bottombar-grid-menu" role="menu">
          {onSetShowTileGrid && (
            <label className="editor-bottombar-grid-item">
              <input
                type="checkbox"
                checked={showTileGrid}
                onChange={(e) => onSetShowTileGrid(e.target.checked)}
              />
              <span>Show tile grid</span>
            </label>
          )}
          {onSetShowRoomGrid && (
            <label className="editor-bottombar-grid-item">
              <input
                type="checkbox"
                checked={showRoomGrid}
                onChange={(e) => onSetShowRoomGrid(e.target.checked)}
              />
              <span>Show room grid</span>
            </label>
          )}
        </div>
      )}
    </div>
  );
}

