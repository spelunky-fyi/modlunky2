// Read-only preview window pinned to a single vanilla room. Opened from the
// editor's room context menu ("Open preview") so the room can be referenced --
// e.g. on a second monitor -- while editing elsewhere. It loads from disk and
// reloads when the editor saves (the `vanilla-level-saved` event), so it shows
// the last saved state, never live unsaved edits. Multiple previews coexist;
// re-opening the same room focuses its existing window (handled in Rust).

import { useEffect, useMemo, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { RefreshCw, TriangleAlert } from "lucide-react";
import {
  buildTileNameAtlas,
  getBiomeBackground,
  getCosmicBackdrop,
  getCosmicSubthemeDecoration,
  loadVanillaLevel,
  type EditorAtlas,
  type VanillaLevelData,
} from "../../lib/commands";
import { biomeForLevelFilename, biomeForThemeId } from "./biomes";
import { COSMIC_OCEAN_THEME } from "./LevelConfigPanel";
import { ExtractRequiredGate } from "./ExtractRequiredGate";
import { TileCanvas } from "./TileCanvas";
import "./RoomPreviewWindow.css";

/** Blank spacer columns between the fg and bg halves in the "both" view. Kept
 *  in sync with the editor's dual view (useLevelCanvas DUAL_GAP_COLS). */
const DUAL_GAP_COLS = 2;

type LayerView = "fg" | "bg" | "both";
type Room = VanillaLevelData["templates"][number]["rooms"][number];

interface Props {
  pack: string;
  file: string;
  template: string;
  roomIndex: number;
}

interface Loaded {
  room: Room;
  atlas: EditorAtlas;
  bgUrl: string | null;
  cosmicBackdropUrl: string | null;
  cosmicDecoUrl: string | null;
  isCosmic: boolean;
}

export function RoomPreviewWindow(props: Props) {
  return (
    <ExtractRequiredGate>
      <RoomPreview {...props} />
    </ExtractRequiredGate>
  );
}

function RoomPreview({ pack, file, template, roomIndex }: Props) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadTick, setReloadTick] = useState(0);
  const [layerView, setLayerView] = useState<LayerView>("fg");
  const [showTileGrid, setShowTileGrid] = useState(true);
  const [showRoomGrid, setShowRoomGrid] = useState(true);
  // Default the layer view once, then leave the user's choice alone across
  // reloads (a save shouldn't snap them back to "both").
  const initializedLayer = useRef(false);
  // Room count in the template at first open. The preview pins a positional
  // slot (template#index), so if the count changes later (a room was added or
  // deleted), the slot may now hold a different room -- warn about it. Reorders
  // that don't change the count aren't detectable here; the room comment in the
  // header is the cue for those.
  const openRoomCount = useRef<number | null>(null);
  const [structureChanged, setStructureChanged] = useState(false);
  // Bump so the canvas re-fits and drops any stale state on a reload / layer
  // switch (same idea as the editor's viewKey).
  const viewKey = `${pack}-${file}-${template}-${roomIndex}-${layerView}-v${reloadTick}`;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const data = await loadVanillaLevel(pack, file);
        if (cancelled) return;
        const tpl = data.templates.find((t) => t.name === template);
        const room = tpl?.rooms[roomIndex];
        if (!tpl || !room) {
          // The pinned slot no longer exists (template renamed/deleted, or the
          // room count shrank below this index). Nothing meaningful to show --
          // close the window rather than leave a dead pane open.
          void getCurrentWindow().close();
          return;
        }

        // Track structural change against the count at first open (see ref).
        if (openRoomCount.current == null) {
          openRoomCount.current = tpl.rooms.length;
        } else if (tpl.rooms.length !== openRoomCount.current) {
          setStructureChanged(true);
        }

        const theme = data.detectedTheme;
        const subtheme = data.detectedSubtheme;
        const biome =
          theme != null
            ? biomeForThemeId(theme, subtheme ?? undefined)
            : biomeForLevelFilename(file);
        const isCosmic = theme === COSMIC_OCEAN_THEME;

        // Every tile name the room can reference, so the atlas resolves them
        // all: the pack palette, inherited dependency palettes, and the room's
        // own fg/bg cells.
        const names = new Set<string>();
        for (const p of data.palette) names.add(p.name);
        for (const dep of data.dependencyPalettes ?? []) {
          for (const e of dep.palette) names.add(e.name);
        }
        for (const row of room.foreground) {
          for (const n of row) if (n) names.add(n);
        }
        for (const row of room.background) {
          for (const n of row) if (n) names.add(n);
        }
        const atlas = await buildTileNameAtlas(Array.from(names), biome);
        if (cancelled) return;

        const bgUrl = isCosmic
          ? null
          : await getBiomeBackground(biome).catch(() => null);
        const cosmicBackdropUrl = isCosmic
          ? await getCosmicBackdrop().catch(() => null)
          : null;
        const cosmicDecoUrl = isCosmic
          ? await getCosmicSubthemeDecoration(subtheme ?? 1).catch(() => null)
          : null;
        if (cancelled) return;

        setLoaded({ room, atlas, bgUrl, cosmicBackdropUrl, cosmicDecoUrl, isCosmic });
        // Default the layer view on first load: a room with no back layer can
        // only show fg; otherwise start side-by-side so both are visible. On
        // reloads keep the user's choice, but drop to fg if the room lost its
        // back layer.
        if (!initializedLayer.current) {
          setLayerView(room.isDual ? "both" : "fg");
          initializedLayer.current = true;
        } else if (!room.isDual) {
          setLayerView("fg");
        }
        setLoading(false);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pack, file, template, roomIndex, reloadTick]);

  // Reload when the editor saves this file, so the preview tracks the latest
  // saved state without a manual refresh.
  useEffect(() => {
    const unlisten = listen<{ pack?: string; file?: string }>(
      "vanilla-level-saved",
      (event) => {
        if (event.payload.pack === pack && event.payload.file === file) {
          setReloadTick((t) => t + 1);
        }
      },
    );
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, [pack, file]);

  const isDual = !!loaded?.room.isDual;
  const { tiles, sections } = useMemo(() => {
    if (!loaded) return { tiles: [] as string[][], sections: undefined };
    return buildCombined(loaded.room, isDual ? layerView : "fg");
  }, [loaded, layerView, isDual]);

  return (
    <div className="room-preview">
      <header className="room-preview-header">
        <div className="room-preview-title">
          <span className="room-preview-crumb">{pack}</span>
          <span className="room-preview-sep">/</span>
          <span className="room-preview-crumb">{file}</span>
          <span className="room-preview-sep">/</span>
          <span className="room-preview-room">
            {template} #{roomIndex}
          </span>
          {loaded?.room.comment && (
            <span className="room-preview-comment" title={loaded.room.comment}>
              {loaded.room.comment}
            </span>
          )}
        </div>
        <div className="room-preview-controls">
          {isDual && (
            <div
              className="room-preview-segmented"
              role="group"
              aria-label="Layer"
            >
              {(["fg", "bg", "both"] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  className={`room-preview-seg${layerView === v ? " active" : ""}`}
                  onClick={() => setLayerView(v)}
                >
                  {v === "fg" ? "FG" : v === "bg" ? "BG" : "Both"}
                </button>
              ))}
            </div>
          )}
          <button
            type="button"
            className={`room-preview-toggle${showTileGrid ? " active" : ""}`}
            onClick={() => setShowTileGrid((s) => !s)}
            title="Toggle tile grid"
          >
            Grid
          </button>
          <button
            type="button"
            className={`room-preview-toggle${showRoomGrid ? " active" : ""}`}
            onClick={() => setShowRoomGrid((s) => !s)}
            title="Toggle room boundary"
          >
            Room
          </button>
          <button
            type="button"
            className="room-preview-toggle"
            onClick={() => setReloadTick((t) => t + 1)}
            title="Reload from disk"
            aria-label="Reload from disk"
          >
            <RefreshCw size={13} aria-hidden="true" />
          </button>
        </div>
      </header>

      {structureChanged && (
        <div className="room-preview-banner">
          <TriangleAlert size={13} aria-hidden="true" />
          <span>
            The level's rooms changed since this preview opened, so this slot
            may now be a different room. Reopen from the editor to be sure.
          </span>
          <button
            type="button"
            className="room-preview-banner-dismiss"
            onClick={() => setStructureChanged(false)}
            aria-label="Dismiss"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="room-preview-body">
        {error ? (
          <div className="room-preview-status room-preview-error">{error}</div>
        ) : loading || !loaded ? (
          <div className="room-preview-status">Loading...</div>
        ) : (
          <TileCanvas
            key={viewKey}
            atlas={loaded.atlas}
            tiles={tiles}
            sections={sections}
            readOnly
            backgroundImageUrl={loaded.isCosmic ? null : loaded.bgUrl}
            cosmicBackdropUrl={loaded.isCosmic ? loaded.cosmicBackdropUrl : null}
            cosmicSubthemeDecoUrl={loaded.isCosmic ? loaded.cosmicDecoUrl : null}
            showTileGrid={showTileGrid}
            showRoomGrid={showRoomGrid}
            zoomFit
          />
        )}
      </div>

      <footer className="room-preview-footer">
        Showing the last saved state. Ctrl+scroll to zoom, middle-drag to pan.
      </footer>
    </div>
  );
}

/** Builds the tile grid (and section ranges for the side-by-side "both" view)
 *  for the requested layer. Mirrors the editor's combined-grid derivation for
 *  a single room. */
function buildCombined(
  room: Room,
  view: LayerView,
): {
  tiles: string[][];
  sections:
    | Array<{ colStart: number; colEnd: number; label?: string }>
    | undefined;
} {
  const fg = room.foreground;
  const cols = fg[0]?.length ?? 0;
  // Normalize bg to the fg shape so "both" lines up even when a non-dual room
  // ships an empty background.
  const bg =
    room.background.length === fg.length && room.background[0]?.length === cols
      ? room.background
      : fg.map((r) => r.map(() => ""));

  if (view === "fg") return { tiles: fg, sections: undefined };
  if (view === "bg") return { tiles: bg, sections: undefined };

  const tiles = fg.map((row, r) => [
    ...row,
    ...new Array<string>(DUAL_GAP_COLS).fill(""),
    ...(bg[r] ?? new Array<string>(cols).fill("")),
  ]);
  const sections = [
    { colStart: 0, colEnd: cols, label: "Foreground" },
    {
      colStart: cols + DUAL_GAP_COLS,
      colEnd: cols + DUAL_GAP_COLS + cols,
      label: "Background",
    },
  ];
  return { tiles, sections };
}
