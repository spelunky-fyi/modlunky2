import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ReactElement,
} from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  BoxSelect,
  Eraser,
  PaintBucket,
  Paintbrush,
  Pipette,
  Square,
  type LucideProps,
} from "lucide-react";
import {
  Application,
  Container,
  Graphics,
  Rectangle,
  Sprite,
  Texture,
  TilingSprite,
} from "pixi.js";
import type { EditorAtlas } from "../../lib/commands";
import "./TileCanvas.css";

interface Props {
  atlas: EditorAtlas;
  /** 2D grid of tile names. Rows are outer, cols are inner. Paints update
   *  sprites in place and fire `onPaint`. Changing the grid's dimensions
   *  rebuilds the world; changing only its contents reconciles cell-by-cell. */
  tiles: string[][];
  /** Identifies what the canvas is currently showing (room, file, layer
   *  view). The canvas does NOT remount between subjects -- it reuses one
   *  PixiJS Application so switching rooms doesn't flash an empty canvas --
   *  so this is what tells it to re-apply the initial-zoom policy and drop
   *  the marquee selection, the two things a remount used to reset for free.
   *  Any stable string works; only equality matters. */
  viewKey?: string;
  /** Display size in CSS pixels per tile at 100% zoom. */
  tileDisplaySize?: number;
  /** Name of the tile painted on left-click. If null, painting is disabled. */
  primary?: string | null;
  /** Name of the tile painted on right-click. */
  secondary?: string | null;
  /** Fired for every distinct tile mutation during a stroke, with the tile
   *  that WAS there and the tile that just replaced it. */
  onPaint?: (row: number, col: number, oldName: string, newName: string) => void;
  /** Fires once when a paint stroke finishes (mouse up), even if the stroke
   *  didn't mutate anything. Parent uses this to close out an undo entry. */
  onStrokeEnd?: () => void;
  /** PNG data URL for a biome background image. Tiles behind the sprites at
   *  one-room-per-repeat, aspect force-fit to `roomTileWidth * roomTileHeight`
   *  tiles regardless of the source PNG's native dimensions (matches
   *  Python's `level_canvas.py::draw_background`, since bg_cave.png ships
   *  at 1280x720 -- not a square texture). */
  backgroundImageUrl?: string | null;
  /** Cosmic Ocean starfield backdrop. When set, gets tiled BEHIND the biome
   *  background at Python's aspect ratio + per-row X-shift so the CO editor
   *  matches the tkinter app's look. Data URL for the bundled
   *  `resources/backdrops/cosmos.png`. Omit / null on non-CO levels. */
  cosmicBackdropUrl?: string | null;
  /** Cosmic Ocean subtheme decoration crop (512x512 slice of
   *  Data/Textures/deco_cosmic.png keyed by the level's CO subtheme).
   *  When set, TileCanvas scatters 31 rotated + scaled copies over the
   *  starfield, matching Python's `level_canvas.py::draw_background` CO
   *  branch. Positions randomize per canvas mount, the same way Python
   *  reseeds `co_bg_locations` each time it constructs a canvas. Null
   *  when either the level isn't CO or the extract lacks deco_cosmic.png. */
  cosmicSubthemeDecoUrl?: string | null;
  /** Fine per-tile grid overlay (thin white lines every cell). */
  showTileGrid?: boolean;
  /** Room-boundary grid overlay (thicker green lines every roomTileWidth
   *  x roomTileHeight cells). */
  showRoomGrid?: boolean;
  /** Room boundaries appear every N tiles horizontally. */
  roomTileWidth?: number;
  /** Room boundaries appear every N tiles vertically. */
  roomTileHeight?: number;
  /** Fires whenever the zoom level changes (mouse wheel, imperative setZoom). */
  onZoomChange?: (zoom: number) => void;
  /** Initial-zoom policy applied when a room first renders. When true
   *  (default), fit-to-view. When false, start at `initialZoom` (a scale
   *  factor, centered). Read when the canvas first builds and on every
   *  `viewKey` change; changing it alone has no effect until then. */
  zoomFit?: boolean;
  /** Scale factor to start at when `zoomFit` is false (e.g. 1 = 100%). */
  initialZoom?: number;
  /** If provided, cells for which this returns false silently no-op instead
   *  of accepting a paint. Used by the dual-canvas host to block paints in
   *  the spacer columns between the fg and bg halves. */
  canPaintCell?: (row: number, col: number) => boolean;
  /** Override the hover HUD's coord/name display. Receives raw canvas coords
   *  and the current tile name; returns whatever should appear in the HUD.
   *  Return null to hide the coords entirely (useful over spacer regions). */
  formatHover?: (row: number, col: number, name: string) => string | null;
  /** Independent grid sections rendered side by side in the same canvas. When
   *  provided, biome background, grid lines, and room-boundary lines are
   *  drawn per-section instead of spanning the whole width, so the spacer
   *  columns between sections read as clearly separate rooms. Each section
   *  can also carry a label that renders as world content below it. Omit for
   *  a single-section grid (the default). */
  sections?: Array<{ colStart: number; colEnd: number; label?: string }>;
  /** Small HTML labels centered over a rectangular region of the grid (in
   *  tile coords). Used by the dual level view to badge rooms that render
   *  empty on the background side because they have no `!dual` layer. Track
   *  with pan/zoom just like section labels. */
  badges?: Array<{
    row: number;
    col: number;
    width: number;
    height: number;
    text: string;
  }>;
  /** Which paint tool is active. Defaults to brush (per-cell drag). */
  tool?: Tool;
  /** When true, paint is disabled and clicks fire `onCellClick` instead.
   *  Used by the whole-level view to browse rooms without editing them. */
  readOnly?: boolean;
  /** Fires on left-click when readOnly is set. row/col are grid coords. */
  onCellClick?: (row: number, col: number) => void;
  /** Tile name written by the eraser tool. Typically the palette's "empty"
   *  entry; falls back to "" (blank cell / no sprite) when omitted. */
  eraseName?: string;
  /** Fires when the eyedropper picks a tile. `kind` is "primary" for left
   *  click, "secondary" for right click. Name may be "" for a blank cell. */
  onPick?: (name: string, kind: "primary" | "secondary") => void;
  /** When set, every paint at (row, col) is also applied at the returned
   *  mirror coord (or skipped if it returns null). Used by the dual-layer
   *  Link-layers toggle to mirror fg edits into bg (and vice versa) so
   *  users can build both layers in lockstep. */
  mirrorCell?: (row: number, col: number) => { row: number; col: number } | null;
  /** Fires whenever the marquee selection changes (drag, clear, or set by
   *  the parent). Null means "no selection." */
  onSelectionChange?: (sel: Selection | null) => void;
  /** Fires when a marquee move gesture commits (mouseup after dragging an
   *  existing selection). The parent applies the actual grid mutation and
   *  updates the canvas via setTile; TileCanvas just reports the intent. */
  onMoveSelection?: (from: Selection, targetRow: number, targetCol: number) => void;
  /** Extra non-interactive selection outlines drawn alongside the active
   *  marquee. Used by the layer-link view to reflect the primary selection
   *  onto the other layer's half of the canvas so users see it applies to
   *  both. */
  extraSelectionRects?: Selection[];
  /** How to render sprites that are larger than a single grid cell.
   *  - "natural" (default): sprite renders at its atlas-recorded natural
   *    size, anchored to the placement cell's bottom-left, so multi-cell
   *    tiles overflow up and to the right into their neighbours (matches
   *    how the game draws them).
   *  - "cell": sprite is clamped to exactly one cell, so authors see the
   *    single cell the tile is placed in without any overflow. */
  renderMode?: "natural" | "cell";
}

interface HoverInfo {
  row: number;
  col: number;
  name: string;
}

/** Paint tool.
 *  - brush: per-cell drag with primary/secondary color.
 *  - bucket: 4-connected flood fill on click.
 *  - rect: click-drag box committed on release.
 *  - eraser: brush that writes `eraseName` (typically "empty" or "").
 *  - eyedropper: click picks the tile under the cursor into primary/
 *    secondary instead of painting.
 *  - marquee: rectangular selection; supports move + Ctrl+C/X/V clipboard
 *    integration via the parent. Click outside the selection to start a
 *    new one; click inside to drag-move it. */
export type Tool =
  | "brush"
  | "bucket"
  | "rect"
  | "eraser"
  | "eyedropper"
  | "marquee";

/** Selection rect in combined-grid coords. Inclusive both ends. */
export interface Selection {
  row0: number;
  col0: number;
  row1: number;
  col1: number;
}

interface CanvasState {
  cancelled: boolean;
  app: Application | null;
  world: Container | null;
  canvas: HTMLCanvasElement | null;
  resizeObserver: ResizeObserver | null;
  sprites: (Sprite | null)[][];
  textures: Map<string, Texture>;
  grid: string[][];
  tileDisplaySize: number;
  /** Extra world height reserved below the grid for section labels. Added
   *  into fit calculations so labels stay visible at fit-to-view zoom. */
  worldExtraBottom: number;
  /** Wired inside setup() so the ref-based imperative handle can reach
   *  the marquee selection without leaking Pixi state to React. */
  selectionApi: {
    get: () => Selection | null;
    set: (sel: Selection | null) => void;
  } | null;
  /** Grid overlay Graphics kept on state so the tile-grid / room-grid
   *  visibility toggles don't need to rebuild the whole canvas. */
  fineGrid: Graphics | null;
  roomGrid: Graphics | null;
  /** Monotonic id for the newest world build. An async build that finds its
   *  token superseded drops its work instead of swapping in a stale world. */
  buildToken: number;
  /** Number of world builds that have started and not yet swapped in. */
  buildsInFlight: number;
  /** A `viewKey` change asked for the initial-zoom policy, but a rebuild may
   *  still be in flight; fit-to-view has to measure the incoming room, not
   *  the outgoing one, so the request waits for the build to land. */
  zoomPolicyPending: boolean;
}

export interface TileCanvasHandle {
  /** Replace the tile at (row, col) without emitting onPaint. Used by undo/redo
   *  to rewind sprites while the parent's grid ref is being adjusted. */
  setTile(row: number, col: number, name: string): void;
  /** Add a new named texture to the canvas without rebuilding. Data URL is
   *  loaded as an HTMLImage then wrapped in a PixiJS texture. Used by the
   *  add-tile flow so growing the palette doesn't trigger a canvas rebuild. */
  addTexture(name: string, pngDataUrl: string): Promise<void>;
  /** Set the world zoom directly. Zooms around the canvas center. */
  setZoom(zoom: number): void;
  /** Fit the whole grid into the visible area at max legible size. */
  zoomToFit(): void;
  /** Current marquee selection in combined-grid coords, or null. */
  getSelection(): Selection | null;
  /** Programmatic selection change. Pass null to clear. */
  setSelection(sel: Selection | null): void;
  /** Cell at the current pointer position, or null when off-canvas. */
  getHoverCell(): { row: number; col: number } | null;
}

function safeDestroy(app: Application) {
  try {
    app.destroy(
      { removeView: true },
      { children: true, texture: false, textureSource: false },
    );
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[TileCanvas] destroy() threw", err);
  }
}

// Decoded images, keyed by URL. The editor rebuilds its world every time the
// user switches room, toggles the layer view, or resizes the grid, and each
// rebuild wants the same handful of images (the atlas, a biome backdrop, the
// cosmic starfield). Decoding them once is what lets a rebuild run start to
// finish without yielding, which in turn is what keeps the swap inside a
// single frame. The cache is small and bounded (one atlas plus a few
// backdrops per session) and lives as long as the editor.
const decodedImages = new Map<string, HTMLImageElement>();
const decodingImages = new Map<string, Promise<HTMLImageElement>>();

/** Decoded image for `url`, or undefined if it hasn't been loaded yet. */
function peekImage(url: string): HTMLImageElement | undefined {
  return decodedImages.get(url);
}

/** Decode `url`, reusing an in-flight or completed decode when there is one. */
function loadImage(url: string): Promise<HTMLImageElement> {
  const decoded = decodedImages.get(url);
  if (decoded) return Promise.resolve(decoded);
  const inFlight = decodingImages.get(url);
  if (inFlight) return inFlight;
  const promise = new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      decodedImages.set(url, img);
      decodingImages.delete(url);
      resolve(img);
    };
    img.onerror = (e) => {
      decodingImages.delete(url);
      reject(new Error(`image failed to decode: ${String(e)}`));
    };
    img.src = url;
  });
  decodingImages.set(url, promise);
  return promise;
}

export const TileCanvas = forwardRef<TileCanvasHandle, Props>(function TileCanvas(
  {
    atlas,
    tiles,
    viewKey,
    tileDisplaySize = 24,
    primary,
    secondary,
    onPaint,
    onStrokeEnd,
    backgroundImageUrl,
    cosmicBackdropUrl,
    cosmicSubthemeDecoUrl,
    showTileGrid = true,
    showRoomGrid = true,
    roomTileWidth = 10,
    roomTileHeight = 8,
    onZoomChange,
    zoomFit = true,
    initialZoom = 1,
    canPaintCell,
    formatHover,
    sections,
    badges,
    tool = "brush",
    readOnly = false,
    onCellClick,
    eraseName = "",
    onPick,
    mirrorCell,
    onSelectionChange,
    onMoveSelection,
    extraSelectionRects,
    renderMode = "natural",
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<CanvasState | null>(null);
  const zoomRef = useRef(1);
  const offsetRef = useRef({ x: 0, y: 0 });
  const labelElsRef = useRef<Map<number, HTMLDivElement>>(new Map());
  const badgeElsRef = useRef<Map<number, HTMLDivElement>>(new Map());
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Pan cursor cue. "none" -> tool cursor; "ready" -> space held, open hand;
  // "active" -> mid-drag with space or middle-mouse, closed hand. Driven by
  // the setup effect's key/mouse handlers; kept as React state so the render
  // path can swap the container's CSS cursor accordingly.
  const [panCursor, setPanCursor] = useState<"none" | "ready" | "active">(
    "none",
  );

  // Props the world build reads. The build effect below only re-runs when the
  // atlas changes, so its closure over these props goes stale immediately;
  // everything it needs comes through a ref instead. Declared ahead of every
  // effect that reads them so React commits the sync first.
  const tilesRef = useRef(tiles);
  const tileDisplaySizeRef = useRef(tileDisplaySize);
  const backgroundImageUrlRef = useRef(backgroundImageUrl);
  const cosmicBackdropUrlRef = useRef(cosmicBackdropUrl);
  const cosmicSubthemeDecoUrlRef = useRef(cosmicSubthemeDecoUrl);
  const roomTileWidthRef = useRef(roomTileWidth);
  const roomTileHeightRef = useRef(roomTileHeight);
  const sectionsRef = useRef(sections);
  const badgesRef = useRef(badges);
  const showTileGridRef = useRef(showTileGrid);
  const showRoomGridRef = useRef(showRoomGrid);
  const zoomFitRef = useRef(zoomFit);
  const initialZoomRef = useRef(initialZoom);
  useEffect(() => {
    tilesRef.current = tiles;
    tileDisplaySizeRef.current = tileDisplaySize;
    backgroundImageUrlRef.current = backgroundImageUrl;
    cosmicBackdropUrlRef.current = cosmicBackdropUrl;
    cosmicSubthemeDecoUrlRef.current = cosmicSubthemeDecoUrl;
    roomTileWidthRef.current = roomTileWidth;
    roomTileHeightRef.current = roomTileHeight;
    sectionsRef.current = sections;
    badgesRef.current = badges;
    showTileGridRef.current = showTileGrid;
    showRoomGridRef.current = showRoomGrid;
    zoomFitRef.current = zoomFit;
    initialZoomRef.current = initialZoom;
  });

  /** Rebuilds the world container in place. Set by the build effect. */
  const buildWorldRef = useRef<(() => Promise<void>) | null>(null);
  /** Re-applies the initial-zoom policy. Set by the build effect. */
  const applyZoomPolicyRef = useRef<(() => void) | null>(null);

  // Position HTML section labels in the DOM to match their world anchor
  // point (centered horizontally under each section). Called from every
  // world-transform update so pan/zoom drags the labels along with the
  // sprites while keeping them rendered as crisp HTML text.
  const positionLabels = () => {
    const local = stateRef.current;
    if (!local || !local.canvas) return;
    const ts = local.tileDisplaySize;
    const gridPxH = local.grid.length * ts;
    // Read through refs: the build effect calls this from a closure that only
    // gets rebuilt on atlas change, so the props would be stale.
    const sections = sectionsRef.current;
    const badges = badgesRef.current;
    if (sections) {
      sections.forEach((section, i) => {
        if (!section.label) return;
        const el = labelElsRef.current.get(i);
        if (!el) return;
        const worldX = ((section.colStart + section.colEnd) / 2) * ts;
        const worldY = gridPxH + ts * 0.35;
        const screenX = worldX * zoomRef.current + offsetRef.current.x;
        const screenY = worldY * zoomRef.current + offsetRef.current.y;
        el.style.left = `${screenX}px`;
        el.style.top = `${screenY}px`;
      });
    }
    if (badges) {
      badges.forEach((badge, i) => {
        const el = badgeElsRef.current.get(i);
        if (!el) return;
        const worldX = (badge.col + badge.width / 2) * ts;
        const worldY = (badge.row + badge.height / 2) * ts;
        const screenX = worldX * zoomRef.current + offsetRef.current.x;
        const screenY = worldY * zoomRef.current + offsetRef.current.y;
        el.style.left = `${screenX}px`;
        el.style.top = `${screenY}px`;
      });
    }
  };

  // Lookup for each atlas tile's natural cell footprint AND anchor
  // offset. Built once per atlas prop change so sprite creation stays
  // O(1). Sprites not in the map (dynamically-added palette swatches)
  // fall back to 1x1 with a top-left anchor.
  const natCellsByName = useMemo(() => {
    const map = new Map<
      string,
      { w: number; h: number; ax: number; ay: number }
    >();
    if (atlas) {
      for (const t of atlas.tiles) {
        map.set(t.name, {
          w: t.natWCells,
          h: t.natHCells,
          ax: t.anchorXCells,
          ay: t.anchorYCells,
        });
      }
    }
    return map;
  }, [atlas]);
  const renderModeRef = useRef(renderMode);
  useEffect(() => {
    renderModeRef.current = renderMode;
    // Relayout every mounted sprite so the toggle is instant. Skips
    // sprites that are already gone (blank cells) since they have no
    // rendered representation to update.
    const local = stateRef.current;
    if (!local) return;
    const ts = local.tileDisplaySize;
    for (let r = 0; r < local.sprites.length; r++) {
      for (let c = 0; c < local.sprites[r].length; c++) {
        const s = local.sprites[r][c];
        if (!s) continue;
        const name = local.grid[r]?.[c] ?? "";
        applySpriteLayout(s, s.texture, r, c, ts, name);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renderMode]);
  const natCellsRef = useRef(natCellsByName);
  useEffect(() => {
    natCellsRef.current = natCellsByName;
  }, [natCellsByName]);

  const primaryRef = useRef(primary);
  const secondaryRef = useRef(secondary);
  const onPaintRef = useRef(onPaint);
  const onStrokeEndRef = useRef(onStrokeEnd);
  const onZoomChangeRef = useRef(onZoomChange);
  const canPaintCellRef = useRef(canPaintCell);
  const formatHoverRef = useRef(formatHover);
  const toolRef = useRef<Tool>(tool);
  const readOnlyRef = useRef(readOnly);
  const onCellClickRef = useRef(onCellClick);
  const eraseNameRef = useRef(eraseName);
  const onPickRef = useRef(onPick);
  const mirrorCellRef = useRef(mirrorCell);
  const onSelectionChangeRef = useRef(onSelectionChange);
  const onMoveSelectionRef = useRef(onMoveSelection);
  const extraSelectionRectsRef = useRef<Selection[] | undefined>(
    extraSelectionRects,
  );
  useEffect(() => {
    canPaintCellRef.current = canPaintCell;
  }, [canPaintCell]);
  useEffect(() => {
    formatHoverRef.current = formatHover;
  }, [formatHover]);
  useEffect(() => {
    toolRef.current = tool;
  }, [tool]);
  useEffect(() => {
    readOnlyRef.current = readOnly;
  }, [readOnly]);
  useEffect(() => {
    onCellClickRef.current = onCellClick;
  }, [onCellClick]);
  useEffect(() => {
    eraseNameRef.current = eraseName;
  }, [eraseName]);
  useEffect(() => {
    onPickRef.current = onPick;
  }, [onPick]);
  useEffect(() => {
    mirrorCellRef.current = mirrorCell;
  }, [mirrorCell]);
  useEffect(() => {
    onSelectionChangeRef.current = onSelectionChange;
  }, [onSelectionChange]);
  useEffect(() => {
    onMoveSelectionRef.current = onMoveSelection;
  }, [onMoveSelection]);
  // Sync the extra-selection-rects ref, then repaint the marquee overlay
  // (setup guards against missing selectionApi so it's safe if the canvas
  // is still mounting).
  useEffect(() => {
    extraSelectionRectsRef.current = extraSelectionRects;
    stateRef.current?.selectionApi?.set(
      stateRef.current.selectionApi.get(),
    );
  }, [extraSelectionRects]);
  // Toggle grid overlay visibility on prop change without touching the
  // setup lifecycle. Guarded because setup runs async so the graphics may
  // not be attached yet on the first render.
  useEffect(() => {
    const local = stateRef.current;
    if (local?.fineGrid) local.fineGrid.visible = showTileGrid;
  }, [showTileGrid]);
  useEffect(() => {
    const local = stateRef.current;
    if (local?.roomGrid) local.roomGrid.visible = showRoomGrid;
  }, [showRoomGrid]);
  useEffect(() => {
    onZoomChangeRef.current = onZoomChange;
  }, [onZoomChange]);
  useEffect(() => {
    primaryRef.current = primary;
  }, [primary]);
  useEffect(() => {
    secondaryRef.current = secondary;
  }, [secondary]);
  useEffect(() => {
    onPaintRef.current = onPaint;
  }, [onPaint]);
  useEffect(() => {
    onStrokeEndRef.current = onStrokeEnd;
  }, [onStrokeEnd]);

  // Positions and scales a sprite to reflect its natural cell footprint
  // and the active render mode. Extracted so setTileInternal and the
  // initial draw loop apply the same layout logic.
  const applySpriteLayout = (
    sprite: Sprite,
    tex: Texture,
    row: number,
    col: number,
    ts: number,
    name: string,
  ) => {
    const mode = renderModeRef.current;
    const nat = natCellsRef.current.get(name) ?? {
      w: 1,
      h: 1,
      ax: 0,
      ay: 0,
    };
    if (mode === "natural") {
      // Natural render: sprite drawn at its atlas-native resolution and
      // positioned by the per-tile anchor (ported from Python's
      // draw_mode table). ax = cells to shift LEFT of the placement
      // cell, ay = cells to shift UP. Tiles without an explicit mode
      // have ax=ay=0, so they draw with the placement cell as their
      // top-left corner.
      sprite.scale.set(
        (nat.w * ts) / tex.frame.width,
        (nat.h * ts) / tex.frame.height,
      );
      sprite.x = (col - nat.ax) * ts;
      sprite.y = (row - nat.ay) * ts;
    } else {
      // Cell mode: sprite forced into a single cell regardless of natural
      // dimensions, so authors can see exactly which cell a tile is
      // anchored to. Preserves the placement cell as the top-left.
      sprite.scale.set(ts / tex.frame.width, ts / tex.frame.height);
      sprite.x = col * ts;
      sprite.y = row * ts;
    }
  };

  // Silent mutation used by undo/redo. Refreshes the internal grid and the
  // rendered sprite without notifying the parent.
  const setTileInternal = (row: number, col: number, name: string) => {
    const local = stateRef.current;
    if (!local || !local.world) return;
    if (row < 0 || row >= local.grid.length) return;
    const rowArr = local.grid[row];
    if (!rowArr || col < 0 || col >= rowArr.length) return;
    if (rowArr[col] === name) return;
    const tex = local.textures.get(name);
    if (!tex && name !== "") return;
    rowArr[col] = name;
    let sprite = local.sprites[row][col];
    if (!tex) {
      if (sprite) {
        local.world.removeChild(sprite);
        sprite.destroy();
        local.sprites[row][col] = null;
      }
      return;
    }
    if (sprite) {
      sprite.texture = tex;
      // Reapply layout: a texture swap can change natural dimensions, so
      // position and scale need to follow.
      applySpriteLayout(sprite, tex, row, col, local.tileDisplaySize, name);
    } else {
      sprite = new Sprite(tex);
      applySpriteLayout(sprite, tex, row, col, local.tileDisplaySize, name);
      local.world.addChild(sprite);
      local.sprites[row][col] = sprite;
    }
  };

  const addTextureInternal = async (name: string, dataUrl: string) => {
    const local = stateRef.current;
    if (!local || !local.world) return;
    if (local.textures.has(name)) return;
    const img = new Image();
    img.src = dataUrl;
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = (e) =>
        reject(new Error(`tile sprite failed to decode: ${String(e)}`));
    });
    if (local.cancelled) return;
    const tex = Texture.from(img);
    local.textures.set(name, tex);
  };

  // Imperative zoom helpers used by the bottom-bar zoom controls. Kept as
  // closures inside the ref so they see whatever `stateRef.current` points to
  // at call time (the canvas may not have finished setup on first render).
  const setZoomImperative = (nextZoom: number) => {
    const local = stateRef.current;
    if (!local || !local.world || !local.canvas) return;
    const cw = local.canvas.width;
    const ch = local.canvas.height;
    // Anchor the zoom around the visible center of the canvas.
    const oldZoom = zoomRef.current;
    const clamped = Math.max(0.25, Math.min(8, nextZoom));
    if (clamped === oldZoom) return;
    const wx = (cw / 2 - offsetRef.current.x) / oldZoom;
    const wy = (ch / 2 - offsetRef.current.y) / oldZoom;
    offsetRef.current = {
      x: cw / 2 - wx * clamped,
      y: ch / 2 - wy * clamped,
    };
    zoomRef.current = clamped;
    local.world.scale.set(clamped);
    local.world.position.set(offsetRef.current.x, offsetRef.current.y);
    positionLabels();
    onZoomChangeRef.current?.(clamped);
  };

  const zoomToFitImperative = () => {
    const local = stateRef.current;
    if (!local || !local.world || !local.canvas) return;
    const rows = local.grid.length;
    const cols = local.grid[0]?.length ?? 0;
    if (rows === 0 || cols === 0) return;
    const gridPxW = cols * local.tileDisplaySize;
    const gridPxH = rows * local.tileDisplaySize;
    const worldH = gridPxH + local.worldExtraBottom;
    const cw = local.canvas.width;
    const ch = local.canvas.height;
    // Leave a small margin so the room boundary isn't glued to the edge.
    const margin = 24;
    const fitZoom = Math.min(
      (cw - margin * 2) / gridPxW,
      (ch - margin * 2) / worldH,
    );
    const clamped = Math.max(0.25, Math.min(8, fitZoom));
    zoomRef.current = clamped;
    offsetRef.current = {
      x: (cw - gridPxW * clamped) / 2,
      y: (ch - worldH * clamped) / 2,
    };
    local.world.scale.set(clamped);
    local.world.position.set(offsetRef.current.x, offsetRef.current.y);
    positionLabels();
    onZoomChangeRef.current?.(clamped);
  };

  const hoverRef = useRef<{ row: number; col: number } | null>(null);

  useImperativeHandle(
    ref,
    () => ({
      setTile: (row, col, name) => setTileInternal(row, col, name),
      addTexture: (name, dataUrl) => addTextureInternal(name, dataUrl),
      setZoom: (zoom) => setZoomImperative(zoom),
      zoomToFit: () => zoomToFitImperative(),
      getSelection: () => stateRef.current?.selectionApi?.get() ?? null,
      setSelection: (sel) => stateRef.current?.selectionApi?.set(sel),
      getHoverCell: () => hoverRef.current,
    }),
    [],
  );

  useEffect(() => {
    const parent = containerRef.current;
    if (!parent) return;

    // Overlay graphics outlive individual world rebuilds: they carry live
    // gesture state (rect preview, marquee selection, move ghost), so each
    // new world container re-parents them rather than recreating them.
    const rectPreview = new Graphics();
    rectPreview.eventMode = "none";
    rectPreview.visible = false;
    const marqueeOverlay = new Graphics();
    marqueeOverlay.eventMode = "none";
    marqueeOverlay.visible = false;
    const moveGhost = new Graphics();
    moveGhost.eventMode = "none";
    moveGhost.visible = false;

    const local: CanvasState = {
      cancelled: false,
      app: null,
      world: null,
      canvas: null,
      resizeObserver: null,
      sprites: [],
      textures: new Map(),
      grid: tilesRef.current.map((row) => row.slice()),
      tileDisplaySize: tileDisplaySizeRef.current,
      worldExtraBottom: 0,
      selectionApi: null,
      fineGrid: null,
      roomGrid: null,
      buildToken: 0,
      buildsInFlight: 0,
      zoomPolicyPending: false,
    };
    stateRef.current = local;
    setError(null);

    const applyTransform = () => {
      if (!local.world) return;
      local.world.scale.set(zoomRef.current);
      local.world.position.set(offsetRef.current.x, offsetRef.current.y);
      positionLabels();
    };

    // Initial-zoom policy (see zoomFit / initialZoom props). Fit-to-view is
    // the default so opening a room shows the whole room instead of a 100%
    // zoom that overflows anything larger than a single 10x8 room. A fixed
    // or remembered zoom starts at the caller's requested scale instead.
    const applyZoomPolicy = () => {
      if (!local.world) return;
      const rows = local.grid.length;
      const cols = local.grid[0]?.length ?? 0;
      const gridPxW = cols * local.tileDisplaySize;
      const gridPxH = rows * local.tileDisplaySize;
      const worldH = gridPxH + local.worldExtraBottom;
      const cw = parent.clientWidth;
      const ch = parent.clientHeight;
      const margin = 24;
      let startZoom: number;
      if (zoomFitRef.current) {
        const fitZoom = Math.min(
          (cw - margin * 2) / Math.max(1, gridPxW),
          (ch - margin * 2) / Math.max(1, worldH),
        );
        startZoom = clamp(fitZoom, 0.25, 8);
      } else {
        startZoom = clamp(initialZoomRef.current, 0.25, 8);
      }
      offsetRef.current = {
        x: (cw - gridPxW * startZoom) / 2,
        y: (ch - worldH * startZoom) / 2,
      };
      zoomRef.current = startZoom;
      applyTransform();
      onZoomChangeRef.current?.(startZoom);
    };

    // Fit-to-view has to measure the room it's about to show, so a zoom
    // request raised while a rebuild is still in flight waits for that
    // rebuild to swap in. `buildWorld` drains the request on its way out.
    const maybeApplyZoomPolicy = () => {
      if (local.buildsInFlight > 0 || !local.zoomPolicyPending) return;
      local.zoomPolicyPending = false;
      applyZoomPolicy();
    };

    applyZoomPolicyRef.current = () => {
      local.zoomPolicyPending = true;
      maybeApplyZoomPolicy();
    };

    // One-time Application setup: decode the atlas, create the WebGL context,
    // slice the per-tile textures. Deliberately separate from buildWorld so
    // room switches reuse all of it. Spinning up a context per room switch
    // costs tens of milliseconds AND leaks toward the browser's hard cap on
    // live contexts, so the canvas holds exactly one for its whole lifetime.
    const ensureApp = async (): Promise<boolean> => {
      if (local.app) return true;

      const img = await loadImage(atlas.pngDataUrl);
      if (local.cancelled) return false;

      let attempt = 0;
      while (
        (parent.clientWidth === 0 || parent.clientHeight === 0) &&
        attempt < 20
      ) {
        await new Promise((r) => setTimeout(r, 16));
        attempt++;
        if (local.cancelled) return false;
      }

      const app = new Application();
      await app.init({
        width: Math.max(parent.clientWidth, 1),
        height: Math.max(parent.clientHeight, 1),
        background: 0x101418,
        antialias: false,
      });
      if (local.cancelled) {
        safeDestroy(app);
        return false;
      }
      local.app = app;
      local.canvas = app.canvas;
      parent.appendChild(app.canvas);

      const ro = new ResizeObserver(() => {
        if (local.cancelled || !local.app) return;
        const w = Math.max(parent.clientWidth, 1);
        const h = Math.max(parent.clientHeight, 1);
        local.app.renderer.resize(w, h);
      });
      ro.observe(parent);
      local.resizeObserver = ro;

      const baseTexture = Texture.from(img);
      for (const tile of atlas.tiles) {
        const frame = new Rectangle(tile.x, tile.y, tile.w, tile.h);
        local.textures.set(
          tile.name,
          new Texture({ source: baseTexture.source, frame }),
        );
      }
      return true;
    };

    // Assemble a fresh world container from the live props and swap it in for
    // the old one. Every image is awaited up front, so the assemble-and-swap
    // below runs to completion without yielding: the outgoing room stays on
    // screen until the incoming one is fully built, and the two never share a
    // frame. This is what the React `key` remount used to do, minus throwing
    // away the Application (and with it, a black frame's worth of nothing).
    const buildWorld = async () => {
      const token = ++local.buildToken;
      local.buildsInFlight++;
      try {
        if (!(await ensureApp())) return;
        if (local.cancelled || local.buildToken !== token) return;

        const app = local.app;
        if (!app) return;

        // Shadow the props with their ref values: this effect only re-runs on
        // atlas change, so the destructured props above are stale by now.
        const backgroundImageUrl = backgroundImageUrlRef.current;
        const cosmicBackdropUrl = cosmicBackdropUrlRef.current;
        const cosmicSubthemeDecoUrl = cosmicSubthemeDecoUrlRef.current;
        const roomTileWidth = roomTileWidthRef.current;
        const roomTileHeight = roomTileHeightRef.current;
        const sections = sectionsRef.current;
        const showTileGrid = showTileGridRef.current;
        const showRoomGrid = showRoomGridRef.current;

        // Decode anything we haven't seen before. After the first room in a
        // level this is always empty, which is what makes later rebuilds
        // synchronous. A backdrop that fails to decode is skipped below
        // rather than taking the whole room down with it.
        const undecoded = [
          backgroundImageUrl,
          cosmicBackdropUrl,
          cosmicSubthemeDecoUrl,
        ].filter((url): url is string => !!url && !peekImage(url));
        if (undecoded.length > 0) {
          await Promise.all(
            undecoded.map((url) =>
              loadImage(url).catch((err: unknown) => {
                // eslint-disable-next-line no-console
                console.warn("[TileCanvas] backdrop failed to decode", err);
                return null;
              }),
            ),
          );
          if (local.cancelled || local.buildToken !== token) return;
        }

        local.tileDisplaySize = tileDisplaySizeRef.current;
        local.grid = tilesRef.current.map((row) => row.slice());

        const world = new Container();

        const rows = local.grid.length;
        const cols = local.grid[0]?.length ?? 0;
        const gridPxW = cols * local.tileDisplaySize;
        const gridPxH = rows * local.tileDisplaySize;

        // Sections are the contiguous painted regions. Callers can slice the
        // grid into two (or more) sub-grids with blank spacer columns between
        // them; without a sections prop we treat the whole grid as one.
        const effectiveSections =
          sections && sections.length > 0
            ? sections
            : [{ colStart: 0, colEnd: cols }];

        // Cosmic Ocean backdrop, when set, gets tiled across the full grid
        // width (not per-section) since CO levels don't render a biome
        // background at all in the tkinter editor. Placement matches
        // Python's `level_canvas.py:draw_background` exactly: step every 4
        // rooms horizontally / 3 rooms vertically, with a per-row X shift
        // of `((y ^ 8) * 8) % 30` game-tiles so the starfield reads as a
        // continuous tilt rather than a hard grid. Native cosmos.png is
        // authored at 30 image-pixels per game-tile.
        // Both the cosmos starfield and the CO subtheme decorations
        // render into a masked container so any tile-scale overflow gets
        // clipped to the grid bounds. Python gets this for free from the
        // tk canvas widget's own clip; PixiJS doesn't, so without this
        // the starfield sprites (each ~40 tiles wide, stepped every 40
        // tiles) spill past the last room, and the deco decorations do
        // the same at the grid's right and bottom edges.
        let coLayer: Container | null = null;
        const ensureCoLayer = () => {
          if (coLayer) return coLayer;
          const container = new Container();
          const maskRect = new Graphics();
          maskRect.rect(0, 0, gridPxW, gridPxH);
          maskRect.fill({ color: 0xffffff });
          container.addChild(maskRect);
          container.mask = maskRect;
          coLayer = container;
          world.addChildAt(container, 0);
          return container;
        };

        const cosmosImg = cosmicBackdropUrl
          ? peekImage(cosmicBackdropUrl)
          : undefined;
        if (cosmosImg) {
          const layer = ensureCoLayer();
          const tex = Texture.from(cosmosImg);
          const ts = local.tileDisplaySize;
          const cosmosNativeTilePx = 30;
          const spriteW = (tex.width * ts) / cosmosNativeTilePx;
          const spriteH = (tex.height * ts) / cosmosNativeTilePx;
          const stepX = 4 * roomTileWidth * ts;
          const stepY = 3 * roomTileHeight * ts;
          const nCols = 1 + Math.ceil(gridPxW / stepX);
          const nRows = 1 + Math.ceil(gridPxH / stepY);
          for (let y = 0; y < nRows; y++) {
            const shift = (((y ^ 8) * 8) % 30) * ts;
            for (let x = 0; x < nCols; x++) {
              const sprite = new Sprite(tex);
              sprite.width = spriteW;
              sprite.height = spriteH;
              sprite.x = x * stepX - shift;
              sprite.y = y * stepY;
              sprite.eventMode = "none";
              layer.addChild(sprite);
            }
          }
        }

        // Cosmic Ocean subtheme decorations: 31 scattered sprites drawn
        // OVER the starfield but under the tiles. Layout mirrors Python's
        // `level_canvas.py::draw_background` CO branch (see co_bg_locations
        // in __init__): 1 fixed sprite at game-tile (11, 6) rotated 40 deg
        // at 1x scale, plus 30 random sprites with pos in ([0, 80], [0,
        // 120]) tiles, rotation in [0, 360) deg, scale in [0.75, 1.25].
        // Sprites past 5 tiles beyond the grid are skipped, again matching
        // Python. Positions randomize per world build (Python does the same
        // by reseeding `co_bg_locations` in every canvas ctor).
        //
        // Added after the starfield so the decorations sit over it; both land
        // in the same masked container.
        const decoImg = cosmicSubthemeDecoUrl
          ? peekImage(cosmicSubthemeDecoUrl)
          : undefined;
        if (decoImg) {
          const layer = ensureCoLayer();
          const tex = Texture.from(decoImg);
          const ts = local.tileDisplaySize;
          const gridTilesW = cols;
          const gridTilesH = rows;
          const basePx = 8 * ts;
          type Placement = {
            x: number;
            y: number;
            rotation: number;
            size: number;
          };
          const placements: Placement[] = [
            { x: 11, y: 6, rotation: 40, size: 1 },
          ];
          for (let i = 0; i < 30; i++) {
            placements.push({
              x: Math.random() * 80,
              y: Math.random() * 120,
              rotation: Math.random() * 360,
              size: 0.75 + Math.random() * 0.5,
            });
          }
          for (const p of placements) {
            if (p.x - 5 > gridTilesW || p.y - 5 > gridTilesH) continue;
            const sprite = new Sprite(tex);
            sprite.anchor.set(0.5, 0.5);
            sprite.width = basePx * p.size;
            sprite.height = basePx * p.size;
            sprite.rotation = (p.rotation * Math.PI) / 180;
            sprite.x = p.x * ts;
            sprite.y = p.y * ts;
            sprite.eventMode = "none";
            layer.addChild(sprite);
          }
        }

        // Layer 0: biome background tiled behind each section only, so the
        // spacer columns between sections stay bare and read as a gap.
        //
        // Python's `level_canvas.py::draw_background` force-resizes the
        // PNG to exactly `zoom * 10` by `zoom * 8` (one room), breaking
        // the source aspect ratio so the biome art fills each room
        // regardless of the on-disk texture dimensions
        // (bg_cave.png ships as 1280x720, not a square). We match that
        // by driving `tileScale.x` / `tileScale.y` off the room extents
        // so one texture repeat = one room = 10x8 tiles.
        const bgImg = backgroundImageUrl
          ? peekImage(backgroundImageUrl)
          : undefined;
        if (bgImg) {
          const tex = Texture.from(bgImg);
          const roomPxW = roomTileWidth * local.tileDisplaySize;
          const roomPxH = roomTileHeight * local.tileDisplaySize;
          for (const section of effectiveSections) {
            const secW =
              (section.colEnd - section.colStart) * local.tileDisplaySize;
            const tiling = new TilingSprite({
              texture: tex,
              width: secW,
              height: gridPxH,
            });
            tiling.x = section.colStart * local.tileDisplaySize;
            tiling.y = 0;
            tiling.tileScale.set(roomPxW / tex.width, roomPxH / tex.height);
            world.addChildAt(tiling, 0);
          }
        }

        local.sprites = Array.from({ length: rows }, () =>
          new Array<Sprite | null>(cols).fill(null),
        );
        let missing = 0;
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const name = local.grid[r][c];
            const tex = local.textures.get(name);
            if (!tex) {
              missing++;
              continue;
            }
            const sprite = new Sprite(tex);
            applySpriteLayout(sprite, tex, r, c, local.tileDisplaySize, name);
            world.addChild(sprite);
            local.sprites[r][c] = sprite;
          }
        }

        // Grid overlay on top of the tiles so the fine lines are visible
        // through any pixel-art the sprites carry. Every-tile lines are
        // thin and faint; room-boundary lines are thicker and brighter
        // so they read as room dividers rather than tile divisions.
        // Drawn per-section so the spacer columns between sections don't
        // get any grid lines and read as blank space, not room content.
        // Both graphics are always built so toggling visibility later
        // doesn't need a canvas rebuild.
        {
          const fine = new Graphics();
          const room = new Graphics();
          for (const section of effectiveSections) {
            const secX0 = section.colStart * local.tileDisplaySize;
            const secX1 = section.colEnd * local.tileDisplaySize;
            for (let x = section.colStart; x <= section.colEnd; x++) {
              const px = x * local.tileDisplaySize;
              fine.moveTo(px, 0).lineTo(px, gridPxH);
            }
            for (let y = 0; y <= rows; y++) {
              const py = y * local.tileDisplaySize;
              fine.moveTo(secX0, py).lineTo(secX1, py);
            }
            for (
              let x = section.colStart;
              x <= section.colEnd;
              x += roomTileWidth
            ) {
              const px = x * local.tileDisplaySize;
              room.moveTo(px, 0).lineTo(px, gridPxH);
            }
            for (let y = 0; y <= rows; y += roomTileHeight) {
              const py = y * local.tileDisplaySize;
              room.moveTo(secX0, py).lineTo(secX1, py);
            }
          }
          // pixelLine keeps the stroke at the given DEVICE-pixel width no
          // matter what the world scale is, so a 1px grid stays 1px on
          // screen at any zoom instead of dropping out below 100% when the
          // logical width scales under one device pixel.
          fine.stroke({
            color: 0xffffff,
            alpha: 0.14,
            width: 1,
            pixelLine: true,
          });
          fine.eventMode = "none";
          world.addChild(fine);
          room.stroke({
            color: 0x40ff70,
            alpha: 0.55,
            width: 2,
            pixelLine: true,
          });
          room.eventMode = "none";
          world.addChild(room);
          // Apply the current prop-driven visibility. A separate effect
          // will pick up changes without touching the setup lifecycle.
          fine.visible = showTileGrid;
          room.visible = showRoomGrid;
          local.fineGrid = fine;
          local.roomGrid = room;
        }

        // Rectangle-tool preview overlay lives at the top of the world so
        // it draws above the sprites and grid but is otherwise hidden until
        // a rect stroke starts.
        world.addChild(rectPreview);
        world.addChild(marqueeOverlay);
        world.addChild(moveGhost);

        // Section labels are rendered as HTML overlays (see JSX below) rather
        // than Pixi Text so they stay crisp at any zoom. We reserve some
        // world-space below the grid so fit-to-view leaves room for them.
        const anyLabels = effectiveSections.some((s) => !!s.label);
        local.worldExtraBottom = anyLabels ? local.tileDisplaySize * 1.4 : 0;
        // eslint-disable-next-line no-console
        console.info(
          `[TileCanvas] atlas=${atlas.width}x${atlas.height} tiles=${atlas.tiles.length} grid=${cols}x${rows} rendered=${rows * cols - missing}/${rows * cols} canvas=${app.canvas.width}x${app.canvas.height}`,
        );

        // Swap the finished world in for the outgoing one, synchronously, so
        // only the new state is ever rendered. The overlays get re-parented
        // first: destroying the old container with `children: true` would
        // take them with it. Textures are shared with `local.textures` (and
        // with the next world), so they explicitly survive the teardown.
        const previous = local.world;
        if (previous) {
          previous.removeChild(rectPreview, marqueeOverlay, moveGhost);
          app.stage.removeChild(previous);
          previous.destroy({
            children: true,
            texture: false,
            textureSource: false,
          });
        }
        app.stage.addChild(world);
        local.world = world;
        applyTransform();
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("[TileCanvas] world build failed", err);
        if (!local.cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        local.buildsInFlight--;
      }
      // A zoom request that arrived mid-build (a `viewKey` change racing this
      // rebuild) has been waiting for the new extents. Drain it now.
      maybeApplyZoomPolicy();
    };
    buildWorldRef.current = buildWorld;

    local.zoomPolicyPending = true;
    void buildWorld();

    let dragging = false;
    /** Active gesture. Captures the tool at mousedown so switching tools
     *  mid-drag doesn't split behavior. `null` = no gesture. */
    let painting: {
      kind: "primary" | "secondary";
      tool: Tool;
      startRow: number;
      startCol: number;
    } | null = null;
    let dragStart = { x: 0, y: 0 };
    let offsetStart = { x: 0, y: 0 };
    let spaceDown = false;
    // Grid extents are read live rather than captured: the world now rebuilds
    // in place on a dimension change instead of remounting the component, so
    // a `rows`/`cols` snapshot taken here would go stale under the handlers.
    const gridRows = () => local.grid.length;
    const gridCols = () => local.grid[0]?.length ?? 0;
    // Selection state. `selection` is the currently committed rect (null =
    // no selection). `marqueeGesture` is any in-flight marquee mouse drag:
    // "create" while defining a new rect, "move" while dragging an existing
    // selection to a new location.
    let selection: Selection | null = null;
    let marqueeGesture:
      | { mode: "create"; startRow: number; startCol: number }
      | {
          mode: "move";
          origin: Selection;
          startRow: number;
          startCol: number;
          curRow: number;
          curCol: number;
        }
      | null = null;

    const drawSelectionOverlay = () => {
      marqueeOverlay.clear();
      const ts = local.tileDisplaySize;
      let any = false;
      const drawRect = (sel: Selection, dim: boolean) => {
        const x = Math.min(sel.col0, sel.col1) * ts;
        const y = Math.min(sel.row0, sel.row1) * ts;
        const w = (Math.abs(sel.col1 - sel.col0) + 1) * ts;
        const h = (Math.abs(sel.row1 - sel.row0) + 1) * ts;
        marqueeOverlay.rect(x, y, w, h);
        marqueeOverlay.stroke({
          color: 0xffd85a,
          alpha: dim ? 0.55 : 0.95,
          width: 2,
          pixelLine: true,
        });
        any = true;
      };
      if (selection) drawRect(selection, false);
      const extras = extraSelectionRectsRef.current;
      if (extras) {
        for (const sel of extras) drawRect(sel, true);
      }
      marqueeOverlay.visible = any;
    };
    const drawMoveGhost = (
      origin: Selection,
      targetRow: number,
      targetCol: number,
    ) => {
      moveGhost.clear();
      const ts = local.tileDisplaySize;
      const w = (Math.abs(origin.col1 - origin.col0) + 1) * ts;
      const h = (Math.abs(origin.row1 - origin.row0) + 1) * ts;
      moveGhost.rect(targetCol * ts, targetRow * ts, w, h);
      moveGhost.fill({ color: 0xffd85a, alpha: 0.1 });
      moveGhost.stroke({
        color: 0xffd85a,
        alpha: 0.95,
        width: 2,
        pixelLine: true,
      });
      moveGhost.visible = true;
    };
    const inSelection = (row: number, col: number) => {
      if (!selection) return false;
      const rTop = Math.min(selection.row0, selection.row1);
      const rBot = Math.max(selection.row0, selection.row1);
      const cLeft = Math.min(selection.col0, selection.col1);
      const cRight = Math.max(selection.col0, selection.col1);
      return row >= rTop && row <= rBot && col >= cLeft && col <= cRight;
    };
    local.selectionApi = {
      get: () => (selection ? { ...selection } : null),
      set: (sel) => {
        selection = sel ? { ...sel } : null;
        drawSelectionOverlay();
      },
    };

    const paintAt = (
      row: number,
      col: number,
      kind: "primary" | "secondary",
      allowMirror = true,
    ) => {
      if (!local.world) return;
      if (row < 0 || row >= gridRows() || col < 0 || col >= gridCols()) return;
      if (canPaintCellRef.current && !canPaintCellRef.current(row, col)) return;
      // Eraser overrides the color choice; primary/secondary otherwise.
      const rawName =
        kind === "primary" ? primaryRef.current : secondaryRef.current;
      const name =
        toolRef.current === "eraser"
          ? eraseNameRef.current ?? ""
          : rawName ?? null;
      if (name == null) return;
      const oldName = local.grid[row][col];
      // Emit onPaint even for no-op cells so the parent's layer-link
      // logic can mirror to the other layer regardless of whether the
      // visible cell already matched. Only skip the sprite work when
      // there's nothing to draw.
      const same = oldName === name;
      if (!same) {
        const tex = name === "" ? null : local.textures.get(name);
        // Reject unknown non-blank tiles; blank ("") always erases.
        if (name !== "" && !tex) return;
        local.grid[row][col] = name;
        const sprite = local.sprites[row][col];
        if (!tex) {
          if (sprite) {
            local.world.removeChild(sprite);
            sprite.destroy();
            local.sprites[row][col] = null;
          }
        } else if (sprite) {
          sprite.texture = tex;
          applySpriteLayout(sprite, tex, row, col, local.tileDisplaySize, name);
        } else {
          const next = new Sprite(tex);
          applySpriteLayout(next, tex, row, col, local.tileDisplaySize, name);
          local.world.addChild(next);
          local.sprites[row][col] = next;
        }
      }
      onPaintRef.current?.(row, col, oldName, name);
      if (allowMirror && mirrorCellRef.current) {
        const m = mirrorCellRef.current(row, col);
        if (m) paintAt(m.row, m.col, kind, false);
      }
    };

    const pointerToTile = (clientX: number, clientY: number) => {
      const rect = parent.getBoundingClientRect();
      const cx = clientX - rect.left;
      const cy = clientY - rect.top;
      const worldX = (cx - offsetRef.current.x) / zoomRef.current;
      const worldY = (cy - offsetRef.current.y) / zoomRef.current;
      const col = Math.floor(worldX / local.tileDisplaySize);
      const row = Math.floor(worldY / local.tileDisplaySize);
      return { row, col };
    };

    // Bucket fill: replace the 4-connected region of the same tile at (r0,c0)
    // with the primary/secondary color. Emits paint events per cell so undo
    // sees one stroke of many edits.
    const floodFill = (
      r0: number,
      c0: number,
      kind: "primary" | "secondary",
    ) => {
      const rows = gridRows();
      const cols = gridCols();
      if (r0 < 0 || r0 >= rows || c0 < 0 || c0 >= cols) return;
      if (canPaintCellRef.current && !canPaintCellRef.current(r0, c0)) return;
      const originalName = local.grid[r0]?.[c0] ?? "";
      const newName =
        kind === "primary" ? primaryRef.current : secondaryRef.current;
      if (!newName || newName === originalName) return;
      const stack: Array<[number, number]> = [[r0, c0]];
      while (stack.length) {
        const cell = stack.pop();
        if (!cell) break;
        const [r, c] = cell;
        if (r < 0 || r >= rows || c < 0 || c >= cols) continue;
        // Compare against originalName; once painted, the cell no longer
        // matches so we won't re-visit it.
        if (local.grid[r]?.[c] !== originalName) continue;
        if (canPaintCellRef.current && !canPaintCellRef.current(r, c)) continue;
        paintAt(r, c, kind);
        stack.push([r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]);
      }
    };

    // Rectangle fill: overwrite every cell inside the axis-aligned box
    // between two corners with the primary/secondary color.
    const rectFill = (
      r0: number,
      c0: number,
      r1: number,
      c1: number,
      kind: "primary" | "secondary",
    ) => {
      const rTop = Math.max(0, Math.min(r0, r1));
      const rBot = Math.min(gridRows() - 1, Math.max(r0, r1));
      const cLeft = Math.max(0, Math.min(c0, c1));
      const cRight = Math.min(gridCols() - 1, Math.max(c0, c1));
      for (let r = rTop; r <= rBot; r++) {
        for (let c = cLeft; c <= cRight; c++) {
          paintAt(r, c, kind);
        }
      }
    };

    // Redraw the rectangle preview outline for the current gesture.
    const drawRectPreview = (
      r0: number,
      c0: number,
      r1: number,
      c1: number,
    ) => {
      const ts = local.tileDisplaySize;
      const rTop = Math.max(0, Math.min(r0, r1));
      const rBot = Math.min(gridRows() - 1, Math.max(r0, r1));
      const cLeft = Math.max(0, Math.min(c0, c1));
      const cRight = Math.min(gridCols() - 1, Math.max(c0, c1));
      const x = cLeft * ts;
      const y = rTop * ts;
      const w = (cRight - cLeft + 1) * ts;
      const h = (rBot - rTop + 1) * ts;
      rectPreview.clear();
      rectPreview.rect(x, y, w, h);
      rectPreview.fill({ color: 0x58c8e0, alpha: 0.18 });
      rectPreview.stroke({
        color: 0x7be0f7,
        alpha: 0.9,
        width: 2,
        pixelLine: true,
      });
      rectPreview.visible = true;
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== "Space") return;
      const active = document.activeElement;
      // Leave text fields alone so users can still type spaces.
      if (
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active instanceof HTMLElement && active.isContentEditable)
      ) {
        return;
      }
      // Toolbar buttons keep focus after a mouse click, and the browser's
      // default action on Space is to re-fire that button. Blur it and
      // swallow the event so Space is purely a pan modifier here.
      if (active instanceof HTMLButtonElement) active.blur();
      e.preventDefault();
      if (!spaceDown) {
        spaceDown = true;
        // Mid-drag with the middle mouse button already showed "active";
        // don't downgrade it to "ready" just because space came in on top.
        setPanCursor((prev) => (prev === "active" ? "active" : "ready"));
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        spaceDown = false;
        // If the space-drag pan is still in flight, hold the closed-hand
        // cursor until the mouseup fires. Otherwise drop back to the tool
        // cursor.
        setPanCursor((prev) => (prev === "active" ? "active" : "none"));
      }
    };
    const onWindowBlur = () => {
      // Alt-tab away while holding space can leave the key stuck otherwise.
      spaceDown = false;
      setPanCursor("none");
    };
    const onMouseDown = (e: MouseEvent) => {
      if (e.button === 1 || (e.button === 0 && spaceDown)) {
        e.preventDefault();
        dragging = true;
        dragStart = { x: e.clientX, y: e.clientY };
        offsetStart = { ...offsetRef.current };
        setPanCursor("active");
        return;
      }
      const rows = gridRows();
      const cols = gridCols();
      if (readOnlyRef.current) {
        if (e.button === 0) {
          e.preventDefault();
          const { row, col } = pointerToTile(e.clientX, e.clientY);
          if (row >= 0 && row < rows && col >= 0 && col < cols) {
            onCellClickRef.current?.(row, col);
          }
        }
        return;
      }
      if (toolRef.current === "eyedropper") {
        if (e.button === 0 || e.button === 2) {
          e.preventDefault();
          const { row, col } = pointerToTile(e.clientX, e.clientY);
          if (row < 0 || row >= rows || col < 0 || col >= cols) return;
          const name = local.grid[row]?.[col] ?? "";
          onPickRef.current?.(name, e.button === 0 ? "primary" : "secondary");
        }
        return;
      }
      if (toolRef.current === "marquee") {
        if (e.button !== 0) return;
        e.preventDefault();
        const { row, col } = pointerToTile(e.clientX, e.clientY);
        if (row < 0 || row >= rows || col < 0 || col >= cols) return;
        if (selection && inSelection(row, col)) {
          // Click inside the current selection starts a move gesture.
          marqueeGesture = {
            mode: "move",
            origin: { ...selection },
            startRow: row,
            startCol: col,
            curRow: Math.min(selection.row0, selection.row1),
            curCol: Math.min(selection.col0, selection.col1),
          };
          drawMoveGhost(selection, marqueeGesture.curRow, marqueeGesture.curCol);
        } else {
          // Otherwise start a fresh selection rect.
          marqueeGesture = { mode: "create", startRow: row, startCol: col };
          selection = { row0: row, col0: col, row1: row, col1: col };
          drawSelectionOverlay();
          onSelectionChangeRef.current?.(selection);
        }
        return;
      }
      const kind: "primary" | "secondary" | null =
        e.button === 0 ? "primary" : e.button === 2 ? "secondary" : null;
      if (!kind) return;
      // Non-eraser tools need a color picked; the eraser overrides with
      // `eraseName` and works regardless of primary/secondary state.
      if (toolRef.current !== "eraser") {
        const chosen =
          kind === "primary" ? primaryRef.current : secondaryRef.current;
        if (!chosen) return;
      }
      e.preventDefault();
      const { row, col } = pointerToTile(e.clientX, e.clientY);
      const activeTool = toolRef.current;
      painting = { kind, tool: activeTool, startRow: row, startCol: col };
      if (activeTool === "brush" || activeTool === "eraser") {
        paintAt(row, col, kind);
      } else if (activeTool === "bucket") {
        // Bucket is a one-shot: fill immediately, commit the stroke,
        // clear the gesture so hover reads normally on the next move.
        floodFill(row, col, kind);
        onStrokeEndRef.current?.();
        painting = null;
      } else if (activeTool === "rect") {
        drawRectPreview(row, col, row, col);
      }
    };
    const onMouseMove = (e: MouseEvent) => {
      if (dragging) {
        offsetRef.current = {
          x: offsetStart.x + (e.clientX - dragStart.x),
          y: offsetStart.y + (e.clientY - dragStart.y),
        };
        applyTransform();
        return;
      }
      const rows = gridRows();
      const cols = gridCols();
      const { row, col } = pointerToTile(e.clientX, e.clientY);
      if (painting) {
        if (painting.tool === "brush" || painting.tool === "eraser") {
          paintAt(row, col, painting.kind);
        } else if (painting.tool === "rect") {
          drawRectPreview(painting.startRow, painting.startCol, row, col);
        }
      }
      if (marqueeGesture) {
        if (marqueeGesture.mode === "create") {
          const r = Math.max(0, Math.min(rows - 1, row));
          const c = Math.max(0, Math.min(cols - 1, col));
          selection = {
            row0: marqueeGesture.startRow,
            col0: marqueeGesture.startCol,
            row1: r,
            col1: c,
          };
          drawSelectionOverlay();
          onSelectionChangeRef.current?.(selection);
        } else {
          const dr = row - marqueeGesture.startRow;
          const dc = col - marqueeGesture.startCol;
          const origTop = Math.min(
            marqueeGesture.origin.row0,
            marqueeGesture.origin.row1,
          );
          const origLeft = Math.min(
            marqueeGesture.origin.col0,
            marqueeGesture.origin.col1,
          );
          marqueeGesture.curRow = origTop + dr;
          marqueeGesture.curCol = origLeft + dc;
          drawMoveGhost(
            marqueeGesture.origin,
            marqueeGesture.curRow,
            marqueeGesture.curCol,
          );
        }
      }
      if (row >= 0 && row < rows && col >= 0 && col < cols) {
        setHover({ row, col, name: local.grid[row]?.[col] ?? "" });
        hoverRef.current = { row, col };
      } else {
        setHover(null);
        hoverRef.current = null;
      }
    };
    const onMouseUp = (e: MouseEvent) => {
      if (dragging) {
        dragging = false;
        // Space might still be held after a middle-mouse pan release, or
        // released mid-drag; either way, land on the right cursor.
        setPanCursor(spaceDown ? "ready" : "none");
      }
      if (painting) {
        if (painting.tool === "rect") {
          const { row, col } = pointerToTile(e.clientX, e.clientY);
          rectFill(
            painting.startRow,
            painting.startCol,
            row,
            col,
            painting.kind,
          );
          rectPreview.clear();
          rectPreview.visible = false;
        }
        painting = null;
        onStrokeEndRef.current?.();
      }
      if (marqueeGesture) {
        if (marqueeGesture.mode === "move") {
          // Actual grid mutation happens in the parent (needs layer /
          // grid-map access). We just report the move intent and hide the
          // ghost; parent will update tiles via setTile.
          const g = marqueeGesture;
          moveGhost.clear();
          moveGhost.visible = false;
          onMoveSelectionRef.current?.(g.origin, g.curRow, g.curCol);
        }
        marqueeGesture = null;
      }
    };
    const onContextMenu = (e: MouseEvent) => {
      e.preventDefault();
    };
    const onWheel = (e: WheelEvent) => {
      // Ctrl + wheel zooms at the cursor. Everything else pans: touchpad
      // two-finger drag lands as (deltaX, deltaY) both non-zero so we
      // pan freely; mouse wheel lands as deltaY-only so it scrolls
      // vertically, and Shift + mouse wheel swaps that to horizontal.
      if (e.ctrlKey) {
        e.preventDefault();
        const rect = parent.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;
        const oldZoom = zoomRef.current;
        const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        const newZoom = clamp(oldZoom * factor, 0.25, 8);
        const wx = (cx - offsetRef.current.x) / oldZoom;
        const wy = (cy - offsetRef.current.y) / oldZoom;
        offsetRef.current = {
          x: cx - wx * newZoom,
          y: cy - wy * newZoom,
        };
        zoomRef.current = newZoom;
        applyTransform();
        onZoomChangeRef.current?.(newZoom);
        return;
      }
      e.preventDefault();
      // Some browsers pre-swap deltaX and deltaY when Shift is held on a
      // mouse wheel (Chromium does, Safari doesn't). If we get a Shift
      // event where deltaX is still 0, do the swap ourselves so behavior
      // is consistent across engines. Touchpad events already have both
      // axes populated so leave those alone even under Shift.
      let dx = e.deltaX;
      let dy = e.deltaY;
      if (e.shiftKey && dx === 0 && dy !== 0) {
        dx = dy;
        dy = 0;
      }
      offsetRef.current = {
        x: offsetRef.current.x - dx,
        y: offsetRef.current.y - dy,
      };
      applyTransform();
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onWindowBlur);
    parent.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    parent.addEventListener("contextmenu", onContextMenu);
    parent.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      local.cancelled = true;
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onWindowBlur);
      parent.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      parent.removeEventListener("contextmenu", onContextMenu);
      parent.removeEventListener("wheel", onWheel);
      local.resizeObserver?.disconnect();
      if (local.canvas && local.canvas.parentElement === parent) {
        parent.removeChild(local.canvas);
      }
      if (local.app) {
        safeDestroy(local.app);
      }
      local.app = null;
      local.world = null;
      local.canvas = null;
      local.resizeObserver = null;
      local.sprites = [];
      local.textures.clear();
      buildWorldRef.current = null;
      applyZoomPolicyRef.current = null;
    };
    // Only the atlas rebuilds the Application. Grid dimensions, backdrops and
    // room extents rebuild the world in place via the effect below -- tearing
    // the WebGL context down and back up on a room switch is what used to
    // black the canvas out between rooms.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atlas]);

  // Structural rebuild. Anything that changes the *shape* of the world --
  // grid dimensions, backdrops, room extents, section layout, tile size --
  // reassembles the world container against the surviving Application. Pure
  // content changes skip this and fall through to the sprite reconcile below,
  // which is cheaper still. Neither path destroys anything the user can see.
  const sectionsKey = useMemo(
    () => JSON.stringify(sections ?? null),
    [sections],
  );
  useEffect(() => {
    const local = stateRef.current;
    // Before the Application exists, the build effect's own initial
    // `buildWorld()` is already queued and will read these same props.
    if (!local || !local.app) return;
    void buildWorldRef.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    tiles.length,
    tiles[0]?.length,
    tileDisplaySize,
    backgroundImageUrl,
    cosmicBackdropUrl,
    cosmicSubthemeDecoUrl,
    roomTileWidth,
    roomTileHeight,
    sectionsKey,
  ]);

  // A `viewKey` change means the canvas is now showing a different subject
  // (room, file, layer view). Remounting used to reset the view and drop the
  // selection as a side effect of the component being destroyed; now that it
  // survives, both have to be asked for. Runs after the structural effect
  // above, so `zoomFit` measures the room that's actually on screen.
  useEffect(() => {
    const local = stateRef.current;
    // The initial build applies the zoom policy itself.
    if (!local || !local.world) return;
    local.selectionApi?.set(null);
    setHover(null);
    hoverRef.current = null;
    applyZoomPolicyRef.current?.();
  }, [viewKey]);

  // Reconcile rendered sprites when the `tiles` prop content changes WITHOUT
  // a dimension change: painting updates sprites imperatively (it doesn't move
  // this prop), so what lands here is a same-size content swap. Two cases:
  // the flip / mirror preview toggle, which reverses each row, and -- since
  // the canvas stopped remounting per room -- switching to another room of
  // the same dimensions, which is the overwhelmingly common one. Diffs
  // against local.grid so only the cells that actually differ get touched.
  useEffect(() => {
    const local = stateRef.current;
    if (!local || !local.world) return;
    if (tiles.length !== local.grid.length) return;
    for (let r = 0; r < tiles.length; r++) {
      const incoming = tiles[r];
      const current = local.grid[r];
      if (!incoming || !current || incoming.length !== current.length) return;
      for (let c = 0; c < incoming.length; c++) {
        if (incoming[c] !== current[c]) {
          setTileInternal(r, c, incoming[c]);
        }
      }
    }
    // setTileInternal reads live state through stateRef; only `tiles` drives
    // this reconcile.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tiles]);

  const canvasCursor = (() => {
    if (panCursor === "active") return "grabbing";
    if (panCursor === "ready") return "grab";
    return readOnly ? "pointer" : cursorForTool(tool);
  })();

  return (
    <div
      className="tile-canvas"
      ref={containerRef}
      style={{ cursor: canvasCursor }}
    >
      <div className="tile-canvas-hud">
        {hover && (() => {
          const text = formatHover
            ? formatHover(hover.row, hover.col, hover.name)
            : `(${hover.col}, ${hover.row}) ${hover.name}`;
          return text == null ? null : <span>{text}</span>;
        })()}
      </div>
      {sections?.map((section, i) =>
        section.label ? (
          <div
            key={i}
            ref={(el) => {
              if (el) labelElsRef.current.set(i, el);
              else labelElsRef.current.delete(i);
            }}
            className="tile-canvas-section-label"
          >
            {section.label}
          </div>
        ) : null,
      )}
      {badges?.map((badge, i) => (
        <div
          key={`badge-${i}`}
          ref={(el) => {
            if (el) badgeElsRef.current.set(i, el);
            else badgeElsRef.current.delete(i);
          }}
          className="tile-canvas-empty-badge"
        >
          {badge.text}
        </div>
      ))}
      {error && <div className="tile-canvas-error">Canvas error: {error}</div>}
    </div>
  );
});

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

// Custom canvas cursors built from the same lucide-react icons used in the
// toolbar so the cursor matches what the user just clicked. Each cursor is
// the icon rendered TWICE at module load: once as a thick black outline for
// readability on light biomes, then again as a thinner white overlay for
// dark biomes. Hotspots point at the tool's "tip".
function buildToolCursor(
  icon: ReactElement<LucideProps>,
  hotX: number,
  hotY: number,
): string {
  // Lucide icons put stroke color on the outer <svg>, not on child paths.
  // Strip the wrapper to get bare shapes, then draw them twice inside our
  // own <g> groups so a black outline underlays a white overlay for
  // readability on any biome background.
  const shapes = extractInner(renderToStaticMarkup(icon));
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">` +
    `<g stroke="black" stroke-width="4">${shapes}</g>` +
    `<g stroke="white" stroke-width="2">${shapes}</g>` +
    `</svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}") ${hotX} ${hotY}, crosshair`;
}

// Strip the outer <svg ...> ... </svg> so we can nest two renders in one.
function extractInner(svg: string): string {
  return svg.replace(/^<svg[^>]*>/, "").replace(/<\/svg>$/, "");
}

const CURSOR_BRUSH = buildToolCursor(<Paintbrush />, 3, 21);
const CURSOR_BUCKET = buildToolCursor(<PaintBucket />, 6, 19);
const CURSOR_RECT = buildToolCursor(<Square />, 4, 6);
const CURSOR_ERASER = buildToolCursor(<Eraser />, 4, 20);
const CURSOR_EYEDROPPER = buildToolCursor(<Pipette />, 4, 20);
const CURSOR_MARQUEE = buildToolCursor(<BoxSelect />, 4, 4);

function cursorForTool(tool: Tool): string {
  switch (tool) {
    case "brush":
      return CURSOR_BRUSH;
    case "bucket":
      return CURSOR_BUCKET;
    case "rect":
      return CURSOR_RECT;
    case "eraser":
      return CURSOR_ERASER;
    case "eyedropper":
      return CURSOR_EYEDROPPER;
    case "marquee":
      return CURSOR_MARQUEE;
    default:
      return "crosshair";
  }
}
