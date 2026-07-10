// Vanilla-mode editor: pick a base-game .lvl (optionally already modded in
// this pack), drill into its templates + rooms, paint one room at a time
// on the canvas, save back to the pack's Data/Levels/. Preserves everything
// this UI doesn't touch (settings/chances/monsters/section comments/other
// templates/alternate rooms not currently open).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  readText as readClipboardText,
  writeText as writeClipboardText,
} from "@tauri-apps/plugin-clipboard-manager";
import {
  ChevronDown,
  ChevronsDownUp,
  ChevronsUpDown,
  FolderOpen,
  Keyboard,
  Palette,
  Settings,
  Settings2,
} from "lucide-react";
import {
  buildTileNameAtlas,
  editorModeLabel,
  getBiomeBackground,
  getCosmicBackdrop,
  getCosmicSubthemeDecoration,
  listShortCodes,
  listVanillaLevels,
  loadVanillaLevel,
  openLevelFile,
  openLevelFileWith,
  openModFolder,
  saveVanillaLevel,
  TEMPLATE_SETTING_HINTS,
  TEMPLATE_SETTING_LABELS,
  type CustomLevelPaletteEntry,
  type TemplateSettingName,
  type EditedRules,
  type EditedTemplate,
  type EditorAtlas,
  type RulesEntry,
  type TileSprite,
  type VanillaLevelData,
  type VanillaLevelListEntry,
} from "../../lib/commands";
import { useFloatingMenu } from "../../hooks/useFloatingMenu";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import { AddTileModal } from "./AddTileModal";
import { ConflictsModal, type TilecodeConflict } from "./ConflictsModal";
import { EditorBottomBar } from "./EditorBottomBar";
import { EditorTopBar } from "./EditorTopBar";
import { KeyboardShortcutsModal } from "./KeyboardShortcutsModal";
import { EditorSettingsModal } from "./EditorSettingsModal";
import { PaletteSidebarSection } from "./PaletteSidebarSection";
import { RoomManagerModal } from "./RoomManagerModal";
import { coerceSettings } from "./RoomSettingsPanel";
import { RulesPanel } from "./RulesPanel";
import { TileCanvas } from "./TileCanvas";
import { useEditorPrefs } from "./hooks/useEditorPrefs";
import { useCloseGuard } from "./hooks/useCloseGuard";
import { DUAL_GAP_COLS, useLevelCanvas } from "./hooks/useLevelCanvas";
import { usePaletteEditor } from "./hooks/usePaletteEditor";
import {
  biomeForLevelFilename,
  biomeForThemeId,
  BIOME_LABEL,
  THEME_ID_FOR_BIOME,
  DEFAULT_BIOME,
} from "./biomes";
import { THEMES, COSMIC_OCEAN_THEME } from "./LevelConfigPanel";
import lvlIcon from "../../assets/lvl.png";
import lvlModdedIcon from "../../assets/lvl_modded.png";
import lvlCustomIcon from "../../assets/lvl_custom.png";
import "./EditorWindow.css";
import "./VanillaEditor.css";

interface Props {
  pack: string;
}

interface RoomKey {
  templateName: string;
  roomIndex: number;
}

function keyEq(a: RoomKey | null, b: RoomKey | null) {
  if (!a || !b) return false;
  return a.templateName === b.templateName && a.roomIndex === b.roomIndex;
}

/** A per-file theme override sourced from the file's top-comment marker.
 *  `subtheme` is only meaningful when `theme` is Cosmic Ocean. */
interface ThemeOverride {
  theme: number;
  subtheme: number | null;
}

/** Value-equality for two overrides (or null). Used to flag dirty and to
 *  seed/reset the on-disk baseline. */
function sameOverride(
  a: ThemeOverride | null,
  b: ThemeOverride | null,
): boolean {
  if (a === null || b === null) return a === b;
  return a.theme === b.theme && (a.subtheme ?? null) === (b.subtheme ?? null);
}

/** Theme implied purely by a file's name, when the name carries more than a
 *  bare biome. Currently that's the `cosmicocean_*` base-game files, which
 *  are Cosmic Ocean levels whose subtheme is the biome they mimic -- so they
 *  should render the CO starfield + the subtheme's floor art without needing
 *  an explicit marker. Everything else returns null (the caller falls back to
 *  the plain filename biome). */
function filenameThemeOverride(fileName: string): ThemeOverride | null {
  if (!fileName.toLowerCase().startsWith("cosmicocean_")) return null;
  const subtheme = THEME_ID_FOR_BIOME[biomeForLevelFilename(fileName)];
  return { theme: COSMIC_OCEAN_THEME, subtheme: subtheme ?? 1 };
}

/** Public label for the theme a file resolves to on its own (marker aside):
 *  the CO label for `cosmicocean_*` files, else the biome's public name.
 *  Shown as the "Auto" option so it reads "Dwelling", not the internal
 *  "cave". */
function filenameThemeLabel(fileName: string): string {
  const fnTheme = filenameThemeOverride(fileName);
  if (fnTheme) {
    return THEMES.find((t) => t.id === fnTheme.theme)?.label ?? "-";
  }
  return BIOME_LABEL[biomeForLevelFilename(fileName)];
}

/** Icon for a file's provenance: modded (pack override), custom (pack-only,
 *  non-vanilla), or plain vanilla. */
function iconForSource(source: VanillaLevelListEntry["source"]): string {
  if (source === "modded") return lvlModdedIcon;
  if (source === "custom") return lvlCustomIcon;
  return lvlIcon;
}

/** Tooltip line explaining a file's provenance in the picker. */
function titleForSource(source: VanillaLevelListEntry["source"]): string {
  if (source === "modded") return "Modded - this pack overrides this file.";
  if (source === "custom") {
    return "Custom - a pack-only level with no vanilla original.";
  }
  return "Vanilla - save will create a pack override.";
}

function Caret({ open }: { open: boolean }) {
  return (
    <ChevronDown
      className={`vanilla-caret${open ? " open" : ""}`}
      size={12}
      aria-hidden="true"
    />
  );
}

export function VanillaEditor({ pack }: Props) {
  const toast = useToast();
  const [files, setFiles] = useState<VanillaLevelListEntry[] | null>(null);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  // Per-file theme override, read from / written to the file's top-comment
  // marker (Rust `parse_theme_marker`). `null` means "no override" -- fall
  // back to the filename-derived biome. Seeded on load from the file's
  // detected marker; edited via the Theme modal. `loadedThemeOverrideRef`
  // holds the on-disk baseline so we can flag dirty and let the backend skip
  // rewriting the comment when nothing changed.
  const [themeOverride, setThemeOverride] = useState<ThemeOverride | null>(
    null,
  );
  const loadedThemeOverrideRef = useRef<ThemeOverride | null>(null);
  const [themeModalOpen, setThemeModalOpen] = useState(false);
  // Bundled Cosmic Ocean starfield backdrop (fetched once) + the per-subtheme
  // decoration crop (refetched per subtheme). Only used when the effective
  // theme is Cosmic Ocean; mirrors the custom editor's CO pipeline.
  const [cosmicBackdropUrl, setCosmicBackdropUrl] = useState<string | null>(
    null,
  );
  const [cosmicDecoUrl, setCosmicDecoUrl] = useState<string | null>(null);

  // Effective theme for the open file: an explicit marker override wins;
  // otherwise the filename may still imply one (the `cosmicocean_*` base-game
  // files are Cosmic Ocean). `null` means "no theme identity" -> use the plain
  // filename biome below.
  const effectiveTheme = useMemo<ThemeOverride | null>(() => {
    if (!selectedFile) return null;
    return themeOverride ?? filenameThemeOverride(selectedFile);
  }, [selectedFile, themeOverride]);

  // Biome that drives the (non-CO) background PNG, biome-tinted floor sprites,
  // and the AddTile preview. Derived from the effective theme when there is
  // one (for Cosmic Ocean that resolves to the subtheme's art), else the plain
  // filename guess. "cave" when no file is open.
  const currentBiome = useMemo(() => {
    if (!selectedFile) return DEFAULT_BIOME;
    if (effectiveTheme) {
      return biomeForThemeId(
        effectiveTheme.theme,
        effectiveTheme.subtheme ?? undefined,
      );
    }
    return biomeForLevelFilename(selectedFile);
  }, [selectedFile, effectiveTheme]);

  // When the effective theme is Cosmic Ocean the canvas swaps the tiled biome
  // background for the starfield + subtheme decorations.
  const isCosmicBackground = effectiveTheme?.theme === COSMIC_OCEAN_THEME;
  const cosmicSubthemeId = effectiveTheme?.subtheme ?? null;
  const [level, setLevel] = useState<VanillaLevelData | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<RoomKey | null>(null);
  // Palette list. Owned by the parent because useLevelCanvas reads it too;
  // usePaletteEditor takes it as an input and owns everything else
  // palette-related (swatch overrides, reorder mode, delete flow).
  const [palette, setPalette] = useState<CustomLevelPaletteEntry[]>([]);
  const [atlas, setAtlas] = useState<EditorAtlas | null>(null);
  const [loading, setLoading] = useState(false);
  // Baseline pixels per tile at 100% zoom. Kept as a fixed default now that
  // the bottom-bar zoom widget covers user-facing sizing; a higher baseline
  // means less upscaling and sharper sprites when zooming in.
  const tileDisplaySize = 48;
  const [dirty, setDirty] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pendingFile, setPendingFile] = useState<string | null>(null);
  const [filePickerOpen, setFilePickerOpenRaw] = useState(false);
  const [bgUrl, setBgUrl] = useState<string | null>(null);
  // Rules working copies. `null` means "unchanged from load"; anything else
  // is an in-memory edit that gets sent as an `editedRules` payload on save.
  const [rulesEdits, setRulesEdits] = useState<{
    levelSettings: RulesEntry[] | null;
    levelChances: RulesEntry[] | null;
    monsterChances: RulesEntry[] | null;
  }>({
    levelSettings: null,
    levelChances: null,
    monsterChances: null,
  });
  const [rulesModalOpen, setRulesModalOpen] = useState(false);
  // "room" shows a single room; "level" tiles every fixed-grid room (setroom,
  // challenge, or Palace of Pleasure) in its (Y, X) grid position on one
  // read-only canvas for a whole-level overview.
  const [viewMode, setViewMode] = useState<"room" | "level">("room");
  const [pendingRestore, setPendingRestore] = useState(false);
  const [pendingSave, setPendingSave] = useState(false);
  // App-wide editor preferences (zoom mode, clamp, grid defaults). Persisted,
  // so they survive reopening the window and app restarts. Threaded down to
  // the canvas, bottom bar, and settings modal.
  const { prefs, updatePrefs } = useEditorPrefs();
  const renderMode = prefs.clampRender ? "cell" : "natural";
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [roomManagerOpen, setRoomManagerOpen] = useState(false);
  const [conflictsOpen, setConflictsOpen] = useState(false);
  // When strict (dependency-aware) allocation is exhausted but a code
  // still exists that only collides with a sister file, we defer the
  // operation and ask the user to confirm the collision risk.
  const [pendingCollision, setPendingCollision] = useState<
    | {
        kind: "add";
        name: string;
        preview: TileSprite;
        code: string;
      }
    | {
        kind: "adopt";
        sourceFileName: string;
        entry: CustomLevelPaletteEntry;
        code: string;
      }
    | null
  >(null);
  const [helpOpen, setHelpOpen] = useState(false);
  // Bumping this triggers a fresh load of the current file from disk,
  // discarding every in-memory edit. Used by the Restore action.
  const [reloadTick, setReloadTick] = useState(0);
  // Floating right-click menu state for the rooms tree. `null` when closed.
  type TreeMenu =
    | { kind: "template"; templateName: string; x: number; y: number }
    | {
        kind: "room";
        templateName: string;
        roomIndex: number;
        x: number;
        y: number;
      };
  const [treeMenu, setTreeMenu] = useState<TreeMenu | null>(null);
  // Right-click menu on the file switcher (escape hatch to open the current
  // .lvl in an external program).
  const [fileMenu, setFileMenu] = useState<{ x: number; y: number } | null>(
    null,
  );
  // Rooms currently on the clipboard, peeked when a room context menu opens so
  // "Add to clipboard" only appears when there's already something to add to.
  const [clipboardRoomCount, setClipboardRoomCount] = useState<number | null>(
    null,
  );
  // Modal-driven template/room operations. Each holds the source
  // identifiers plus whichever fields the modal needs to prompt for.
  type PendingTreeOp =
    | { kind: "addTemplate" }
    | {
        kind: "renameTemplate";
        templateName: string;
        initialValue: string;
      }
    | {
        kind: "editTemplateComment";
        templateName: string;
        initialValue: string;
      }
    | { kind: "deleteTemplate"; templateName: string }
    | { kind: "deleteAllRooms"; templateName: string }
    | { kind: "addRoom"; templateName: string }
    | {
        kind: "editRoomComment";
        templateName: string;
        roomIndex: number;
        initialValue: string;
      }
    | { kind: "deleteRoom"; templateName: string; roomIndex: number };
  const [pendingTreeOp, setPendingTreeOp] = useState<PendingTreeOp | null>(
    null,
  );

  // Every time we open the picker, refresh the file list so newly-saved
  // pack overrides show their modded icon without waiting for a save round-trip.
  const openFilePicker = useCallback(() => {
    listVanillaLevels(pack)
      .then(setFiles)
      .catch((err) => setFilesError(extractMessage(err)));
    setFilePickerOpenRaw(true);
  }, [pack]);
  const setFilePickerOpen = setFilePickerOpenRaw;
  // Per-room template-settings overrides. Only rooms the user has touched
  // land here; save uses these to signal "replace settings on this room",
  // and leaves the original settings intact otherwise.
  const settingsRef = useRef<Map<string, string[]>>(new Map());
  // Bumped whenever editedKeysRef mutates so consumers rendering off the ref
  // (like the rooms tree pips) re-render. Refs alone don't invalidate React.
  const [, setEditedTick] = useState(0);
  // True if the palette's shape (list, ordering, codes, comments) changed
  // since the last save. Parent-owned so recomputeDirty can read it and
  // usePaletteEditor can mutate it without a cyclic dep between the two.
  const paletteChangedSinceSave = useRef(false);
  const shortCodesRef = useRef<string[] | null>(null);
  // Biome the current atlas was tinted for. Lets the retint effect skip a
  // rebuild when the effective biome hasn't actually changed (e.g. the load
  // effect already built it at this biome).
  const atlasBiomeRef = useRef<string | null>(null);
  // File the current atlas was built for. On a file switch `currentBiome`
  // updates a render before `level`/`atlas` do, so the retint effect could
  // otherwise fire on the previous file's data and clobber the incoming
  // atlas. Skipping while this doesn't match `selectedFile` leaves the build
  // to the load effect, which owns cross-file loads.
  const atlasFileRef = useRef<string | null>(null);

  const roomKey = (k: RoomKey) => `${k.templateName}#${k.roomIndex}`;

  // Bump this on every settings toggle to force the panel to re-render.
  // Refs alone don't trigger renders.
  const [settingsTick, setSettingsTick] = useState(0);

  const currentRoomData = useMemo(() => {
    if (!level || !selectedRoom) return null;
    const tpl = level.templates.find(
      (t) => t.name === selectedRoom.templateName,
    );
    return tpl?.rooms[selectedRoom.roomIndex] ?? null;
  }, [level, selectedRoom]);

  const currentSettings = useMemo<string[]>(() => {
    if (!selectedRoom) return [];
    const key = roomKey(selectedRoom);
    const overridden = settingsRef.current.get(key);
    if (overridden) return overridden;
    return currentRoomData?.settings ?? [];
    // settingsTick invalidates the memo when the user toggles a setting.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRoom, currentRoomData, settingsTick]);

  const currentSettingsEdited = useMemo(() => {
    if (!selectedRoom) return false;
    return settingsRef.current.has(roomKey(selectedRoom));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRoom, settingsTick]);

  const isDual = currentSettings.includes("dual");
  const isFlip = currentSettings.includes("flip");
  const isOnlyFlip = currentSettings.includes("onlyflip");
  // Per-room mirror-preview toggle. ONLYFLIP rooms start mirrored (since
  // that's how the game plays them), FLIP rooms start un-mirrored (opt-in
  // preview), everything else has no mirror.
  const [flipPreviewByRoom, setFlipPreviewByRoom] = useState<
    Map<string, boolean>
  >(() => new Map());
  const currentMirrorState = useMemo(() => {
    if (!selectedRoom) return false;
    const key = roomKey(selectedRoom);
    if (flipPreviewByRoom.has(key)) return flipPreviewByRoom.get(key)!;
    return isOnlyFlip;
  }, [selectedRoom, flipPreviewByRoom, isOnlyFlip]);
  const setCurrentMirror = useCallback(
    (next: boolean) => {
      if (!selectedRoom) return;
      const key = roomKey(selectedRoom);
      setFlipPreviewByRoom((prev) => {
        const out = new Map(prev);
        out.set(key, next);
        return out;
      });
    },
    [selectedRoom],
  );

  // Shared canvas state: grids, undo, marquee, tools, view + link, zoom,
  // primary/secondary, keyboard shortcuts. Everything Vanilla and Custom
  // agree on lives in one hook so both editors share the same paint
  // pipeline and behave consistently.
  const canvas = useLevelCanvas({
    currentKey: selectedRoom ? roomKey(selectedRoom) : null,
    isDual,
    mirrored: currentMirrorState,
    palette,
    // Vanilla stores per-room template-flag overrides in settingsRef; the
    // hook consults this so the dirty pip reconciliation doesn't clear a
    // room that's only dirty from a settings toggle (no strokes).
    hasSettingsOverride: useCallback(
      (key: string) => settingsRef.current.has(key),
      [],
    ),
    // Bump the tree tick so pips repaint when the hook's editedKeys set
    // changes (undo-to-baseline clears it, a new paint adds it).
    onEditedKeysChanged: useCallback(() => {
      setEditedTick((t) => t + 1);
    }, []),
    toast,
  });

  const {
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
    setLayerView,
    effectiveLayerView,
    linkLayers,
    setLinkLayers,
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
    setSelection,
    extraSelectionRects,
    combinedGrid,
    canvasSections,
    handlePaint,
    handleStrokeEnd,
    canPaintCell,
    formatHover,
    mirrorCell,
    onPick: canvasOnPick,
    commitMarqueeMove,
  } = canvas;

  // Grid visibility and clamp live in `prefs` (the hook's own grid state is
  // unused here). Initial-zoom policy for the canvas: fit-to-view, a fixed
  // percent, or "remember" (carry the current zoom across room/file switches).
  const zoomFit = prefs.zoomMode === "fit";
  const initialZoom =
    prefs.zoomMode === "fixed"
      ? prefs.fixedZoomPct / 100
      : prefs.zoomMode === "remember"
        ? (zoom ?? 1)
        : 1;

  useEffect(() => {
    let cancelled = false;
    listShortCodes()
      .then((c) => {
        if (!cancelled) shortCodesRef.current = c;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Refetch the biome background whenever the current file's biome
  // changes. Cheap for a cached extract; if the target biome PNG is
  // missing (or the extract hasn't run yet) we swallow and let the
  // previous URL keep rendering.
  useEffect(() => {
    let cancelled = false;
    getBiomeBackground(currentBiome)
      .then((url) => {
        if (!cancelled) setBgUrl(url);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [currentBiome]);

  // Cosmic Ocean starfield backdrop is app-bundled, so fetch it once at mount
  // and reuse across files. The canvas only renders it when the effective
  // theme is CO.
  useEffect(() => {
    let cancelled = false;
    getCosmicBackdrop()
      .then((url) => {
        if (!cancelled) setCosmicBackdropUrl(url);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Per-subtheme CO decoration crop from the user's extract. Refetches when
  // the effective subtheme changes; absent extracts degrade to the plain
  // starfield. Only fetched when the background is CO so we don't hit disk for
  // ordinary files.
  useEffect(() => {
    if (!isCosmicBackground) {
      setCosmicDecoUrl(null);
      return;
    }
    let cancelled = false;
    getCosmicSubthemeDecoration(cosmicSubthemeId ?? 1)
      .then((url) => {
        if (!cancelled) setCosmicDecoUrl(url);
      })
      .catch(() => {
        if (!cancelled) setCosmicDecoUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isCosmicBackground, cosmicSubthemeId]);

  useEffect(() => {
    let cancelled = false;
    setFilesError(null);
    listVanillaLevels(pack)
      .then((f) => {
        if (!cancelled) setFiles(f);
      })
      .catch((err) => {
        if (!cancelled) setFilesError(extractMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [pack]);

  const trySelectFile = useCallback(
    (f: string) => {
      if (f === selectedFile) {
        setFilePickerOpen(false);
        return;
      }
      if (dirty) {
        setPendingFile(f);
        setFilePickerOpen(false);
        return;
      }
      setSelectedFile(f);
      setFilePickerOpen(false);
    },
    [dirty, selectedFile],
  );

  const confirmDiscardAndSwitch = () => {
    if (!pendingFile) return;
    setSelectedFile(pendingFile);
    setPendingFile(null);
  };

  const cancelSwitch = () => setPendingFile(null);

  // Intercept the window's OS close button so unsaved edits show a
  // discard/cancel prompt instead of silently vanishing.
  const closeGuard = useCloseGuard(dirty);

  const currentFileSource = useMemo(
    () => files?.find((f) => f.fileName === selectedFile)?.source ?? null,
    [files, selectedFile],
  );

  useEffect(() => {
    if (!selectedFile) {
      setLevel(null);
      setAtlas(null);
      setPalette([]);
      setPrimary(null);
      setSecondary(null);
      setSelectedRoom(null);
      setDirty(false);
      gridsRef.current.clear();
      bgGridsRef.current.clear();
      settingsRef.current.clear();
      editedKeysRef.current.clear();
      resetHistory();
      pal.resetForFileLoad();
      setRulesEdits({
        levelSettings: null,
        levelChances: null,
        monsterChances: null,
      });
      setThemeOverride(null);
      loadedThemeOverrideRef.current = null;
      atlasBiomeRef.current = null;
      atlasFileRef.current = null;
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLevel(null);
    setAtlas(null);
    setDirty(false);
    gridsRef.current.clear();
    bgGridsRef.current.clear();
    settingsRef.current.clear();
    editedKeysRef.current.clear();
    setRulesEdits({
      levelSettings: null,
      levelChances: null,
      monsterChances: null,
    });
    resetHistory();
    pal.resetForFileLoad();
    (async () => {
      try {
        const data = await loadVanillaLevel(pack, selectedFile);
        if (cancelled) return;
        setLevel(data);
        setPalette(data.palette);
        // Seed the per-file theme override from the file's marker (if any).
        // Baseline mirrors it so an untouched save is a no-op and the dirty
        // pip stays off.
        const initialOverride: ThemeOverride | null =
          data.detectedTheme != null
            ? {
                theme: data.detectedTheme,
                subtheme: data.detectedSubtheme ?? null,
              }
            : null;
        setThemeOverride(initialOverride);
        loadedThemeOverrideRef.current = initialOverride;
        // Biome for the initial atlas comes from the freshly-loaded data, not
        // the render's `currentBiome` (which still reflects the previous file
        // until the state above commits). Mirrors CustomEditor's inline
        // atlas-biome derivation.
        const loadBiome =
          initialOverride != null
            ? biomeForThemeId(
                initialOverride.theme,
                initialOverride.subtheme ?? undefined,
              )
            : biomeForLevelFilename(selectedFile);
        // Snapshot every room's grids (fg + bg) so the user can jump
        // between rooms and layers freely without losing edits. Backgrounds
        // that arrive empty get a same-shape zero grid so the canvas can
        // paint on them once the user activates the Dual setting.
        for (const tpl of data.templates) {
          for (let idx = 0; idx < tpl.rooms.length; idx++) {
            const room = tpl.rooms[idx];
            const key = roomKey({ templateName: tpl.name, roomIndex: idx });
            const fg = room.foreground.map((row) => row.slice());
            gridsRef.current.set(key, fg);
            const bg =
              room.background.length > 0
                ? room.background.map((row) => row.slice())
                : room.foreground.map((row) => row.map(() => ""));
            bgGridsRef.current.set(key, bg);
          }
        }
        // Invalidate the hook's grid memos even when the new file's first
        // room happens to share the previous selection's `template#index`
        // key. Without this bump, `currentKey` is unchanged, so combinedGrid
        // keeps returning the PREVIOUS file's cached grid until the user
        // switches rooms (which finally moves currentKey). Mirrors the custom
        // editor's load path.
        bumpGridsVersion();
        const firstTemplate = data.templates[0];
        const firstRoom = firstTemplate?.rooms[0];
        if (firstTemplate && firstRoom) {
          setSelectedRoom({
            templateName: firstTemplate.name,
            roomIndex: 0,
          });
        }
        const uniqNames = new Set<string>();
        for (const p of data.palette) uniqNames.add(p.name);
        for (const tpl of data.templates) {
          for (const c of tpl.rooms) {
            for (const row of c.foreground) {
              for (const n of row) if (n) uniqNames.add(n);
            }
          }
        }
        // Include dependency palette names so their swatches render in
        // the palette panel even before an adoption happens.
        for (const dep of data.dependencyPalettes ?? []) {
          for (const e of dep.palette) uniqNames.add(e.name);
        }
        if (uniqNames.size === 0) {
          setAtlas(null);
          atlasBiomeRef.current = null;
          atlasFileRef.current = selectedFile;
        } else {
          const a = await buildTileNameAtlas(Array.from(uniqNames), loadBiome);
          if (cancelled) return;
          atlasBiomeRef.current = loadBiome;
          atlasFileRef.current = selectedFile;
          setAtlas(a);
        }
        // Default left click to the first paintable (non-empty) tile and
        // right click to "empty" so erasing works right away. `prev ??`
        // preserves an active selection across file switches.
        const firstPaintable = data.palette.find(
          (p) => p.name !== "empty",
        )?.name;
        const emptyName =
          data.palette.find((p) => p.name === "empty")?.name ?? null;
        setPrimary(
          (prev) => prev ?? firstPaintable ?? data.palette[0]?.name ?? null,
        );
        setSecondary((prev) => prev ?? emptyName);
      } catch (err) {
        if (!cancelled) toast.error(`Load failed: ${extractMessage(err)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // reloadTick is a bump-to-refetch signal; ESLint can't tell it's used
    // deliberately for its identity change. currentBiome is intentionally NOT
    // a dep: the initial atlas biome is derived inline from `data`, and later
    // biome changes are handled by the retint effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pack, selectedFile, toast, resetHistory, reloadTick]);

  // When the user switches rooms, drop the per-room undo history so
  // undo doesn't accidentally paint over the wrong room. Cross-room
  // undo is a follow-up. The hook takes care of clearing selection and
  // resetting layerView on the same currentKey change.
  useEffect(() => {
    resetHistory();
  }, [selectedRoom, resetHistory]);

  // Retint the atlas when the effective biome changes AFTER load -- e.g. the
  // user picks a different theme in the Theme modal. The load effect owns the
  // initial build (so first paint isn't tinted with the previous file's
  // biome); this covers post-load theme edits. Guarded on level+atlas so it
  // doesn't fire mid-load or on empty-palette files, and short-circuits when
  // the atlas is already at this biome.
  useEffect(() => {
    if (!selectedFile || !level || !atlas) return;
    // Skip while the atlas belongs to a different file: a file switch is in
    // flight and the load effect owns that rebuild. Firing here would tint
    // the previous file's tiles and clobber the incoming atlas.
    if (atlasFileRef.current !== selectedFile) return;
    if (atlasBiomeRef.current === currentBiome) return;
    let cancelled = false;
    (async () => {
      const uniqNames = new Set<string>();
      for (const p of palette) uniqNames.add(p.name);
      for (const tpl of level.templates) {
        for (const r of tpl.rooms) {
          for (const row of r.foreground) {
            for (const n of row) if (n) uniqNames.add(n);
          }
        }
      }
      for (const dep of level.dependencyPalettes ?? []) {
        for (const e of dep.palette) uniqNames.add(e.name);
      }
      if (uniqNames.size === 0) return;
      const next = await buildTileNameAtlas(
        Array.from(uniqNames),
        currentBiome,
      );
      if (cancelled) return;
      atlasBiomeRef.current = currentBiome;
      setAtlas(next);
    })();
    return () => {
      cancelled = true;
    };
    // Only biome flips drive a retint; palette membership is tracked by the
    // load + palette-edit paths.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBiome]);

  const recomputeDirty = useCallback(() => {
    if (selectedRoom) {
      const key = roomKey(selectedRoom);
      // Undo depth only counts when the history belongs to this room; the
      // stacks outlive a room switch until resetHistory runs.
      const strokesDirty =
        historyKeyRef.current === key &&
        undoLen !== savedUndoIndexRef.current;
      const settingsSet = settingsRef.current.has(key);
      const wasPresent = editedKeysRef.current.has(key);
      const shouldBePresent = strokesDirty || settingsSet;
      if (shouldBePresent && !wasPresent) {
        editedKeysRef.current.add(key);
        setEditedTick((t) => t + 1);
      } else if (
        !shouldBePresent &&
        wasPresent &&
        currentRoomTouchedRef.current
      ) {
        editedKeysRef.current.delete(key);
        setEditedTick((t) => t + 1);
      }
    }
    const anyEdits = editedKeysRef.current.size > 0;
    const rulesDirty =
      rulesEdits.levelSettings !== null ||
      rulesEdits.levelChances !== null ||
      rulesEdits.monsterChances !== null;
    const themeDirty = !sameOverride(
      themeOverride,
      loadedThemeOverrideRef.current,
    );
    setDirty(
      anyEdits || rulesDirty || paletteChangedSinceSave.current || themeDirty,
    );
  }, [
    rulesEdits,
    themeOverride,
    selectedRoom,
    undoLen,
    editedKeysRef,
    currentRoomTouchedRef,
    savedUndoIndexRef,
    historyKeyRef,
  ]);

  // Palette editor: owns swatch overrides, reorder mode, help modal open
  // state, pending delete, and the delete-flow callbacks that walk the
  // canvas grid refs. Both editors share this hook; the parent keeps
  // `palette + setPalette` (needed by useLevelCanvas) and
  // `paletteChangedSinceSave` (needed by recomputeDirty above).
  const pal = usePaletteEditor({
    palette,
    setPalette,
    paletteChangedSinceSave,
    refs: {
      gridsRef,
      bgGridsRef,
      editedKeysRef,
      currentRoomTouchedRef,
    },
    currentKey: selectedRoom ? roomKey(selectedRoom) : null,
    primary,
    secondary,
    setPrimary,
    setSecondary,
    resetHistory,
    bumpGridsVersion,
    recomputeDirty,
    selectedKey: selectedFile,
    toast,
  });
  const { setSwatchOverrides } = pal;

  const levelViewData = useMemo(() => {
    if (viewMode !== "level" || !level) return null;
    // Read live grid contents from gridsRef when present so unsaved edits
    // show up in the mosaic; fall back to the on-disk foreground otherwise.
    // gridsVersion invalidates when grid content is rewritten in place.
    void gridsVersion;
    // Fixed-grid template families that place a room at `<family><y>-<x>`:
    // vanilla setrooms plus the challenge and Palace of Pleasure grids. All
    // three share the same 8-row x 10-col room geometry, so one mosaic covers
    // any of them. (Matches the Python editor's BaseTemplate set.)
    const setroomRe = /^(?:setroom|challenge_|palaceofpleasure_)(\d+)-(\d+)$/;
    type Placement = {
      templateName: string;
      roomIndex: number;
      row: number;
      col: number;
      fg: string[][];
      bg: string[][] | null;
    };
    const placements: Placement[] = [];
    let maxRowExcl = 0;
    let maxColExcl = 0;
    for (const tpl of level.templates) {
      const m = tpl.name.match(setroomRe);
      if (!m) continue;
      const y = Number(m[1]);
      const x = Number(m[2]);
      // The game skips room variants flagged `!ignore` and uses the next one.
      // Mirror that here: pick the first non-ignored room, or drop the slot
      // entirely if every variant is ignored.
      const roomIdx = tpl.rooms.findIndex((room, i) => {
        const s =
          settingsRef.current.get(
            roomKey({ templateName: tpl.name, roomIndex: i }),
          ) ?? room.settings;
        return !s.includes("ignore");
      });
      if (roomIdx === -1) continue;
      const original = tpl.rooms[roomIdx];
      if (!original) continue;
      const key = roomKey({ templateName: tpl.name, roomIndex: roomIdx });
      const rawFg = gridsRef.current.get(key) ?? original.foreground;
      const bgRaw = bgGridsRef.current.get(key) ?? original.background;
      // Only surface the bg layer for dual rooms; other rooms may have a
      // stale zero-filled bg from the load path that we shouldn't show.
      const effectiveSettings =
        settingsRef.current.get(key) ?? original.settings;
      const roomIsDual = effectiveSettings.includes("dual");
      const rawBgLayer = roomIsDual && bgRaw.length > 0 ? bgRaw : null;
      // A few Palace of Pleasure grid rooms play with their front/back layers
      // reversed (to line up with the setrooms they connect to), so the front
      // half should show the back layer and vice versa. Only meaningful when
      // the room is dual.
      const layersReversed = REVERSED_ROOMS.has(tpl.name) && rawBgLayer !== null;
      const baseFg = layersReversed ? rawBgLayer! : rawFg;
      const rawBg = layersReversed ? rawFg : rawBgLayer;
      // `!onlyflip` rooms only ever play mirrored, so show them mirrored here:
      // reverse each row's column order (both layers), matching the game and
      // the old Python editor. No per-sprite flip, just tile order.
      const isOnlyFlipRoom = effectiveSettings.includes("onlyflip");
      const fg = isOnlyFlipRoom
        ? baseFg.map((row) => [...row].reverse())
        : baseFg;
      const bg =
        rawBg && isOnlyFlipRoom
          ? rawBg.map((row) => [...row].reverse())
          : rawBg;
      const rows = fg.length;
      const cols = fg[0]?.length ?? 0;
      const rowStart = y * 8;
      const colStart = x * 10;
      placements.push({
        templateName: tpl.name,
        roomIndex: roomIdx,
        row: rowStart,
        col: colStart,
        fg,
        bg,
      });
      maxRowExcl = Math.max(maxRowExcl, rowStart + rows);
      maxColExcl = Math.max(maxColExcl, colStart + cols);
    }
    if (placements.length === 0 || maxRowExcl === 0 || maxColExcl === 0) {
      return null;
    }
    const fgMosaic: string[][] = Array.from({ length: maxRowExcl }, () =>
      new Array<string>(maxColExcl).fill(""),
    );
    const bgMosaic: string[][] = Array.from({ length: maxRowExcl }, () =>
      new Array<string>(maxColExcl).fill(""),
    );
    // Maps a cell in the fg mosaic back to the template it belongs to so a
    // click can jump straight to the source room.
    const lookup: (string | null)[][] = Array.from({ length: maxRowExcl }, () =>
      new Array<string | null>(maxColExcl).fill(null),
    );
    let anyBg = false;
    for (const p of placements) {
      const rows = p.fg.length;
      const cols = p.fg[0]?.length ?? 0;
      for (let r = 0; r < rows; r++) {
        const dstRow = p.row + r;
        if (dstRow >= maxRowExcl) continue;
        const bgRow = p.bg?.[r];
        for (let c = 0; c < cols; c++) {
          const dstCol = p.col + c;
          if (dstCol >= maxColExcl) continue;
          fgMosaic[dstRow][dstCol] = p.fg[r][c];
          lookup[dstRow][dstCol] = p.templateName;
          if (bgRow) {
            bgMosaic[dstRow][dstCol] = bgRow[c] ?? "";
            if (bgRow[c]) anyBg = true;
          }
        }
      }
    }
    // Stitch fg + gap + bg into one combined grid when any room is dual.
    // Otherwise skip the gap entirely so single-layer levels stay compact.
    const combined = anyBg
      ? fgMosaic.map((row, r) => [
          ...row,
          ...new Array<string>(DUAL_GAP_COLS).fill(""),
          ...bgMosaic[r],
        ])
      : fgMosaic;
    // In the dual view, rooms without a `!dual` layer contribute nothing to
    // the background half. Badge each one so an empty region reads as
    // "intentionally single-layer" rather than a missing/broken room.
    const badges = anyBg
      ? placements
          .filter((p) => p.bg === null)
          .map((p) => ({
            row: p.row,
            col: maxColExcl + DUAL_GAP_COLS + p.col,
            width: p.fg[0]?.length ?? 0,
            height: p.fg.length,
            text: "No dual layer",
          }))
      : [];
    return {
      combined,
      lookup,
      fgCols: maxColExcl,
      hasBg: anyBg,
      badges,
    };
  }, [viewMode, level, gridsVersion, gridsRef, bgGridsRef]);

  const handleLevelCellClick = useCallback(
    (row: number, col: number) => {
      if (!levelViewData) return;
      // In dual level-view the combined grid is [fg | gap | bg]. Both
      // halves are the same shape and lookup is keyed on fg coords, so
      // translate a bg-side click back to its fg column before probing.
      let fgCol = col;
      if (levelViewData.hasBg) {
        if (col < levelViewData.fgCols) fgCol = col;
        else if (col < levelViewData.fgCols + DUAL_GAP_COLS) return;
        else fgCol = col - levelViewData.fgCols - DUAL_GAP_COLS;
      }
      const templateName = levelViewData.lookup[row]?.[fgCol];
      if (!templateName) return;
      setSelectedRoom({ templateName, roomIndex: 0 });
      setViewMode("room");
    },
    [levelViewData],
  );

  const handleToggleSetting = useCallback(
    (setting: string, next: boolean) => {
      if (!selectedRoom) return;
      const key = roomKey(selectedRoom);
      // Start from either the override or the original room's settings.
      const base =
        settingsRef.current.get(key) ?? currentRoomData?.settings ?? [];
      const set = new Set(base);
      if (next) set.add(setting);
      else set.delete(setting);
      // If the resulting flag set matches the room's on-disk settings, drop
      // the override entirely so the pip clears and save doesn't ship a
      // no-op change. Otherwise store it and mark the room touched.
      const original = currentRoomData?.settings ?? [];
      const originalSet = new Set(original);
      const matchesOriginal =
        set.size === originalSet.size &&
        [...set].every((s) => originalSet.has(s));
      if (matchesOriginal) {
        settingsRef.current.delete(key);
      } else {
        settingsRef.current.set(key, Array.from(set));
      }
      currentRoomTouchedRef.current = true;
      setSettingsTick((t) => t + 1);
      recomputeDirty();
    },
    // recomputeDirty identity churns whenever rulesEdits changes; this
    // callback only closes over refs + selectedRoom, so we intentionally
    // don't rebind on every recomputeDirty change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedRoom, currentRoomData, currentRoomTouchedRef],
  );

  const save = useCallback(async () => {
    if (!selectedFile || !level) return;
    if (saving) return;
    setSaving(true);
    try {
      // Group edited rooms by template so we only send the ones that
      // changed. For each template, produce a rooms array padded with
      // nulls up to the max room index that was edited; the backend fills
      // Ship the FULL templates list every save. Every template's rooms
      // are hydrated from gridsRef/bgGridsRef/settingsRef (with the in-memory
      // level state as a fallback for rooms the user never touched) so
      // add/delete/rename operations round-trip without needing per-op
      // signaling.
      const edited: EditedTemplate[] = level.templates.map((tpl) => ({
        name: tpl.name,
        comment: tpl.comment,
        rooms: tpl.rooms.map((room, idx) => {
          const key = roomKey({ templateName: tpl.name, roomIndex: idx });
          const fg = gridsRef.current.get(key) ?? room.foreground;
          const bgGrid = bgGridsRef.current.get(key);
          const settings = settingsRef.current.get(key) ?? room.settings;
          const isDual = settings.includes("dual");
          // Only emit a bg layer when the room is dual. A non-dual room ships
          // an empty background so removing dual actually drops the second
          // layer on disk (otherwise the old bg lingers and the game reads the
          // room as dual again on reload).
          const background = isDual ? (bgGrid ?? room.background) : [];
          return {
            foreground: fg,
            background,
            settings,
            comment: room.comment,
          };
        }),
      }));
      const editedRulesPayload: EditedRules | null =
        rulesEdits.levelSettings ||
        rulesEdits.levelChances ||
        rulesEdits.monsterChances
          ? {
              levelSettings: rulesEdits.levelSettings ?? undefined,
              levelChances: rulesEdits.levelChances ?? undefined,
              monsterChances: rulesEdits.monsterChances ?? undefined,
            }
          : null;
      await saveVanillaLevel(
        pack,
        selectedFile,
        edited,
        palette,
        editedRulesPayload,
        themeOverride?.theme ?? null,
        themeOverride?.subtheme ?? null,
      );
      // The override just landed on disk; make it the new baseline so the
      // dirty pip clears and the next save is a no-op unless it changes again.
      loadedThemeOverrideRef.current = themeOverride;
      // Fold the just-saved settings overrides into the in-memory level before
      // clearing the ref, so the room-list badges and room panel keep showing
      // the saved flags. Otherwise the ref is cleared against the stale loaded
      // settings and the UI reverts until the file is reloaded. Snapshot first
      // because setLevel's updater runs after settingsRef is cleared below.
      const savedSettings = new Map(settingsRef.current);
      if (savedSettings.size > 0) {
        // Removing dual drops the back layer: wipe the in-memory bg grid for
        // any room that lost dual while still holding bg content, so toggling
        // dual back on starts from an empty layer (the payload already omitted
        // it from disk). Bump the grids version so the canvas memos refresh.
        let clearedBg = false;
        for (const [key, s] of savedSettings) {
          if (s.includes("dual")) continue;
          const bg = bgGridsRef.current.get(key);
          if (bg?.some((r) => r.some((c) => c))) {
            const fg = gridsRef.current.get(key);
            if (fg) bgGridsRef.current.set(key, fg.map((r) => r.map(() => "")));
            clearedBg = true;
          }
        }
        setLevel((prev) =>
          prev
            ? {
                ...prev,
                templates: prev.templates.map((tpl) => ({
                  ...tpl,
                  rooms: tpl.rooms.map((room, idx) => {
                    const override = savedSettings.get(`${tpl.name}#${idx}`);
                    if (!override) return room;
                    const isDualRoom = override.includes("dual");
                    return {
                      ...room,
                      settings: override,
                      isDual: isDualRoom,
                      background: isDualRoom ? room.background : [],
                    };
                  }),
                })),
              }
            : prev,
        );
        if (clearedBg) bumpGridsVersion();
      }
      editedKeysRef.current.clear();
      setEditedTick((t) => t + 1);
      settingsRef.current.clear();
      paletteChangedSinceSave.current = false;
      // Hook snapshots its own undo depth as "clean" and clears its
      // in-progress stroke buffer.
      markSaved();
      setRulesEdits({
        levelSettings: null,
        levelChances: null,
        monsterChances: null,
      });
      setDirty(false);
      toast.success(`Saved ${selectedFile}.`);
      // Refresh the file list so a first-time save flips Vanilla → Modded.
      listVanillaLevels(pack)
        .then(setFiles)
        .catch(() => {});
    } catch (err) {
      toast.error(`Save failed: ${extractMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }, [
    pack,
    selectedFile,
    level,
    palette,
    saving,
    toast,
    rulesEdits,
    themeOverride,
  ]);

  const handleRulesChange = useCallback(
    (
      kind: "levelSettings" | "levelChances" | "monsterChances",
      next: RulesEntry[],
    ) => {
      setRulesEdits((prev) => ({ ...prev, [kind]: next }));
    },
    [],
  );

  // rulesEdits is a piece of state, so recomputeDirty needs to run whenever
  // it changes, not just when handlers explicitly call it.
  useEffect(() => {
    recomputeDirty();
  }, [rulesEdits, recomputeDirty]);

  const effectiveRules = useMemo(
    () => ({
      levelSettings: rulesEdits.levelSettings ?? level?.levelSettings ?? [],
      levelChances: rulesEdits.levelChances ?? level?.levelChances ?? [],
      monsterChances: rulesEdits.monsterChances ?? level?.monsterChances ?? [],
    }),
    [rulesEdits, level],
  );

  // Vanilla-only shortcuts. Tool / undo / marquee shortcuts live in the
  // shared canvas hook so both editors handle them identically.
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
      if (isCtrl && e.code === "KeyS") {
        e.preventDefault();
        if (dirty) setPendingSave(true);
      } else if (!isCtrl && !e.altKey && !e.shiftKey && e.code === "Tab") {
        e.preventDefault();
        setViewMode((m) => (m === "room" ? "level" : "room"));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save]);

  // Aggregates every code used by the current palette AND every sister
  // location, so a fresh allocation never collides with a code the game
  // would already see through vanilla inheritance.
  const collectUsedCodes = useCallback((): Set<string> => {
    const used = new Set(palette.map((p) => p.code));
    for (const dep of level?.dependencyPalettes ?? []) {
      for (const entry of dep.palette) used.add(entry.code);
    }
    return used;
  }, [palette, level]);

  const handleAddTile = useCallback(
    async (name: string, preview: TileSprite) => {
      setAddOpen(false);
      if (!name) return;
      if (palette.some((p) => p.name === name)) {
        toast.error(`"${name}" is already in the palette.`);
        return;
      }
      const pool = shortCodesRef.current;
      const localCodes = new Set(palette.map((p) => p.code));
      // Inheritance-friendly allocation: if any sister file already
      // declares this exact name (e.g. the user typed "floor" and
      // generic.lvl also declares "floor"), reuse that sister's code so
      // the game sees consistent bindings across the load chain. Only
      // valid when the code is still free in this file's palette.
      let code: string | undefined;
      for (const dep of level?.dependencyPalettes ?? []) {
        const match = dep.palette.find((e) => e.name === name);
        if (match && !localCodes.has(match.code)) {
          code = match.code;
          break;
        }
      }
      if (!code) {
        const used = collectUsedCodes();
        code = pool?.find((c) => !used.has(c));
      }
      if (!code) {
        // No non-conflicting code available. Fall back to any code not
        // already used by *this file* (may collide with a sister),
        // deferring the actual add until the user confirms.
        const loose = pool?.find((c) => !localCodes.has(c));
        if (!loose) {
          toast.error("No free tile-code characters left in this level.");
          return;
        }
        setPendingCollision({ kind: "add", name, preview, code: loose });
        return;
      }
      try {
        await canvasRef.current?.addTexture(name, preview.pngDataUrl);
      } catch (err) {
        toast.error(`Add failed: ${extractMessage(err)}`);
        return;
      }
      setPalette((prev) => [...prev, { name, code, comment: null }]);
      setSwatchOverrides((prev) => {
        const next = new Map(prev);
        next.set(name, preview.pngDataUrl);
        return next;
      });
      setPrimary(name);
      paletteChangedSinceSave.current = true;
      recomputeDirty();
    },
    [palette, level, collectUsedCodes, toast, recomputeDirty],
  );

  const confirmCollisionAdd = useCallback(async () => {
    const pending = pendingCollision;
    if (!pending) return;
    setPendingCollision(null);
    if (pending.kind === "add") {
      try {
        await canvasRef.current?.addTexture(
          pending.name,
          pending.preview.pngDataUrl,
        );
      } catch (err) {
        toast.error(`Add failed: ${extractMessage(err)}`);
        return;
      }
      setPalette((prev) => [
        ...prev,
        { name: pending.name, code: pending.code, comment: null },
      ]);
      setSwatchOverrides((prev) => {
        const next = new Map(prev);
        next.set(pending.name, pending.preview.pngDataUrl);
        return next;
      });
      setPrimary(pending.name);
      paletteChangedSinceSave.current = true;
      recomputeDirty();
      toast.success(
        `Added "${pending.name}" using a code that may collide with a sister file.`,
      );
    } else {
      setPalette((prev) => [
        ...prev,
        {
          name: pending.entry.name,
          code: pending.code,
          comment: pending.entry.comment ?? null,
        },
      ]);
      setPrimary(pending.entry.name);
      paletteChangedSinceSave.current = true;
      recomputeDirty();
      toast.success(
        `Adopted "${pending.entry.name}" using a code that may collide with a sister file.`,
      );
    }
  }, [pendingCollision, toast, setPrimary, recomputeDirty]);

  // Walk the current palette and flag every entry whose code is also
  // used by a sister-location file with a different name. Same-name reuse
  // is normal (inheritance); it's the char-vs-different-name pair the game
  // will get wrong at load time.
  const conflicts = useMemo(() => {
    const out: {
      name: string;
      code: string;
      otherName: string;
      otherFile: string;
    }[] = [];
    for (const entry of palette) {
      for (const dep of level?.dependencyPalettes ?? []) {
        const clash = dep.palette.find(
          (e) => e.code === entry.code && e.name !== entry.name,
        );
        if (clash) {
          out.push({
            name: entry.name,
            code: entry.code,
            otherName: clash.name,
            otherFile: dep.fileName,
          });
        }
      }
    }
    return out;
  }, [palette, level]);

  const conflictingCurrentNames = useMemo(
    () => new Set(conflicts.map((c) => c.name)),
    [conflicts],
  );

  // Core reassignment: picks fresh non-colliding codes for every current
  // palette entry whose name is in `namesToFix`. Shared between the
  // per-row Resolve and Resolve-all paths so their allocation logic stays
  // in one place.
  const reassignConflictingNames = useCallback(
    (namesToFix: Set<string>): number => {
      if (namesToFix.size === 0) return 0;
      const pool = shortCodesRef.current;
      if (!pool) {
        toast.error("Short-code pool not loaded yet; try again in a moment.");
        return 0;
      }
      let resolved = 0;
      let ran = 0;
      setPalette((prev) => {
        // Seed with every used code across current + sisters so we don't
        // reassign into another collision. Reserve each newly-chosen code
        // as we go.
        const used = new Set(prev.map((p) => p.code));
        for (const dep of level?.dependencyPalettes ?? []) {
          for (const e of dep.palette) used.add(e.code);
        }
        return prev.map((entry) => {
          if (!namesToFix.has(entry.name)) return entry;
          used.delete(entry.code);
          const fresh = pool.find((c) => !used.has(c));
          if (!fresh) {
            ran++;
            return entry;
          }
          used.add(fresh);
          resolved++;
          return { ...entry, code: fresh };
        });
      });
      if (resolved > 0) {
        paletteChangedSinceSave.current = true;
        recomputeDirty();
      }
      if (ran > 0) {
        toast.error(
          `Ran out of free tile-code characters; ${ran} conflict${ran === 1 ? "" : "s"} still unresolved.`,
        );
      }
      return resolved;
    },
    [level, recomputeDirty, toast],
  );

  const resolveOneConflict = useCallback(
    (conflict: TilecodeConflict) => {
      const n = reassignConflictingNames(new Set([conflict.name]));
      if (n > 0) {
        toast.success(
          `Reassigned "${conflict.name}" to avoid ${conflict.otherFile}.`,
        );
      }
    },
    [reassignConflictingNames, toast],
  );

  const resolveAllConflicts = useCallback(() => {
    if (conflicts.length === 0) return;
    const n = reassignConflictingNames(conflictingCurrentNames);
    if (n > 0) {
      toast.success(`Resolved ${n} tilecode conflict${n === 1 ? "" : "s"}.`);
    }
  }, [conflicts, conflictingCurrentNames, reassignConflictingNames, toast]);

  // Bring a tile from a sister-location palette into the current file.
  // Reuse the parent's code when it's free everywhere; otherwise allocate
  // a fresh non-colliding code so the game doesn't see two names for the
  // same character.
  const handleAdoptDependencyTile = useCallback(
    (sourceFileName: string, entry: CustomLevelPaletteEntry) => {
      if (palette.some((p) => p.name === entry.name)) {
        toast.error(`"${entry.name}" is already in the palette.`);
        return;
      }
      const used = collectUsedCodes();
      const parentCodeCollides = Array.from(
        level?.dependencyPalettes ?? [],
      ).some((dep) => {
        if (dep.fileName === sourceFileName) return false;
        return dep.palette.some(
          (e) => e.code === entry.code && e.name !== entry.name,
        );
      });
      let chosenCode: string | null = null;
      if (!parentCodeCollides && !palette.some((p) => p.code === entry.code)) {
        chosenCode = entry.code;
      } else {
        const pool = shortCodesRef.current;
        chosenCode = pool?.find((c) => !used.has(c)) ?? null;
      }
      if (!chosenCode) {
        const pool = shortCodesRef.current;
        const localUsed = new Set(palette.map((p) => p.code));
        const loose = pool?.find((c) => !localUsed.has(c));
        if (!loose) {
          toast.error("No free tile-code characters left in this level.");
          return;
        }
        setPendingCollision({
          kind: "adopt",
          sourceFileName,
          entry,
          code: loose,
        });
        return;
      }
      setPalette((prev) => [
        ...prev,
        { name: entry.name, code: chosenCode!, comment: entry.comment ?? null },
      ]);
      setPrimary(entry.name);
      paletteChangedSinceSave.current = true;
      recomputeDirty();
      toast.success(`Adopted "${entry.name}" from ${sourceFileName}.`);
    },
    [palette, level, collectUsedCodes, setPrimary, recomputeDirty, toast],
  );

  const confirmRestore = useCallback(() => {
    setPendingRestore(false);
    // The load effect resets every scratch ref and re-fetches the file, so
    // bumping the tick is enough to blow away all unsaved state.
    setReloadTick((t) => t + 1);
    toast.success(`Restored ${selectedFile} from disk.`);
  }, [selectedFile, toast]);

  // Helper: rewrite ref-keyed maps so all keys for a template pick up a new
  // name. Used by rename. Preserves whatever the current room grids are.
  const renameTemplateKeys = useCallback((oldName: string, newName: string) => {
    const rename = <T,>(map: Map<string, T>) => {
      for (const k of Array.from(map.keys())) {
        if (k.startsWith(`${oldName}#`)) {
          const idx = k.slice(oldName.length + 1);
          const v = map.get(k)!;
          map.delete(k);
          map.set(`${newName}#${idx}`, v);
        }
      }
    };
    rename(gridsRef.current);
    rename(bgGridsRef.current);
    rename(settingsRef.current);
    const nextEdited = new Set<string>();
    for (const k of editedKeysRef.current) {
      if (k.startsWith(`${oldName}#`)) {
        nextEdited.add(`${newName}#${k.slice(oldName.length + 1)}`);
      } else {
        nextEdited.add(k);
      }
    }
    editedKeysRef.current = nextEdited;
  }, []);

  const dropTemplateKeys = useCallback((templateName: string) => {
    const drop = <T,>(map: Map<string, T>) => {
      for (const k of Array.from(map.keys())) {
        if (k.startsWith(`${templateName}#`)) map.delete(k);
      }
    };
    drop(gridsRef.current);
    drop(bgGridsRef.current);
    drop(settingsRef.current);
    for (const k of Array.from(editedKeysRef.current)) {
      if (k.startsWith(`${templateName}#`)) editedKeysRef.current.delete(k);
    }
  }, []);

  const commitAddTemplate = useCallback(
    (name: string, width: number, height: number) => {
      if (!level) return;
      const trimmed = name.trim();
      if (!trimmed) return;
      if (level.templates.some((t) => t.name === trimmed)) {
        toast.error(`Template "${trimmed}" already exists.`);
        return;
      }
      const cols = Math.max(1, Math.floor(width));
      const rows = Math.max(1, Math.floor(height));
      const emptyName = palette.find((p) => p.name === "empty")?.name ?? "";
      const grid: string[][] = Array.from({ length: rows }, () =>
        new Array<string>(cols).fill(emptyName),
      );
      const newRoom = {
        settings: [] as string[],
        foreground: grid.map((row) => row.slice()),
        background: [] as string[][],
        width: cols,
        height: rows,
        comment: null,
        isDual: false,
      };
      setLevel({
        ...level,
        templates: [
          ...level.templates,
          { name: trimmed, comment: null, rooms: [newRoom] },
        ],
      });
      const key = `${trimmed}#0`;
      gridsRef.current.set(
        key,
        grid.map((r) => r.slice()),
      );
      bgGridsRef.current.set(
        key,
        grid.map((r) => r.map(() => "")),
      );
      editedKeysRef.current.add(key);
      setEditedTick((t) => t + 1);
      setSelectedRoom({ templateName: trimmed, roomIndex: 0 });
      setDirty(true);
      toast.success(`Added template "${trimmed}".`);
    },
    [level, palette, toast],
  );

  const commitRenameTemplate = useCallback(
    (oldName: string, newName: string) => {
      if (!level) return;
      const trimmed = newName.trim();
      if (!trimmed || trimmed === oldName) return;
      if (level.templates.some((t) => t.name === trimmed)) {
        toast.error(`Template "${trimmed}" already exists.`);
        return;
      }
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === oldName ? { ...t, name: trimmed } : t,
        ),
      });
      renameTemplateKeys(oldName, trimmed);
      // Mark every room of the renamed template as edited so the pip shows
      // and the file dirty flag flips.
      const renamedTpl = level.templates.find((t) => t.name === oldName);
      if (renamedTpl) {
        for (let i = 0; i < renamedTpl.rooms.length; i++) {
          editedKeysRef.current.add(`${trimmed}#${i}`);
        }
      }
      if (selectedRoom?.templateName === oldName) {
        setSelectedRoom({ ...selectedRoom, templateName: trimmed });
      }
      setEditedTick((t) => t + 1);
      setDirty(true);
      toast.success(`Renamed "${oldName}" to "${trimmed}".`);
    },
    [level, selectedRoom, renameTemplateKeys, toast],
  );

  const commitEditTemplateComment = useCallback(
    (templateName: string, next: string) => {
      if (!level) return;
      const cleaned = next.trim();
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName ? { ...t, comment: cleaned || null } : t,
        ),
      });
      // Mark first room as edited so the file shows dirty; comment lives on
      // the template but there's no other signal to hang the dirty flag on.
      editedKeysRef.current.add(`${templateName}#0`);
      setEditedTick((t) => t + 1);
      setDirty(true);
    },
    [level],
  );

  const commitDeleteTemplate = useCallback(
    (templateName: string) => {
      if (!level) return;
      const nextTemplates = level.templates.filter(
        (t) => t.name !== templateName,
      );
      setLevel({ ...level, templates: nextTemplates });
      dropTemplateKeys(templateName);
      if (selectedRoom?.templateName === templateName) {
        const first = nextTemplates[0];
        setSelectedRoom(
          first ? { templateName: first.name, roomIndex: 0 } : null,
        );
      }
      setEditedTick((t) => t + 1);
      setDirty(true);
      toast.success(`Removed template "${templateName}".`);
    },
    [level, selectedRoom, dropTemplateKeys, toast],
  );

  // Reduce a template to a single blank room. The editor requires every
  // template to keep at least one room (see commitDeleteRoom), so "delete all
  // rooms" resets to one empty room of the template's size rather than
  // leaving it empty. Distinct from commitDeleteTemplate, which drops the
  // template outright.
  const commitDeleteAllRooms = useCallback(
    (templateName: string) => {
      if (!level) return;
      const tpl = level.templates.find((t) => t.name === templateName);
      if (!tpl) return;
      const first = tpl.rooms[0];
      const cols = first?.width ?? 10;
      const rows = first?.height ?? 8;
      const emptyName = palette.find((p) => p.name === "empty")?.name ?? "";
      const grid: string[][] = Array.from({ length: rows }, () =>
        new Array<string>(cols).fill(emptyName),
      );
      const blankRoom = {
        settings: [] as string[],
        foreground: grid.map((row) => row.slice()),
        background: [] as string[][],
        width: cols,
        height: rows,
        comment: null,
        isDual: false,
      };
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName ? { ...t, rooms: [blankRoom] } : t,
        ),
      });
      // Drop every existing key for this template, then seed room 0 with the
      // blank grid so the refs match the new single-room layout.
      dropTemplateKeys(templateName);
      const key = `${templateName}#0`;
      gridsRef.current.set(
        key,
        grid.map((r) => r.slice()),
      );
      bgGridsRef.current.set(
        key,
        grid.map((r) => r.map(() => "")),
      );
      editedKeysRef.current.add(key);
      if (selectedRoom?.templateName === templateName) {
        setSelectedRoom({ templateName, roomIndex: 0 });
      }
      // Room 0's grid content changes to blank even when it was already the
      // selected room, so currentKey may not change; bump gridsVersion to
      // force the canvas memo to re-read the blanked grid.
      bumpGridsVersion();
      setEditedTick((t) => t + 1);
      setDirty(true);
      toast.success(`Cleared all rooms in "${templateName}".`);
    },
    [level, palette, selectedRoom, dropTemplateKeys, bumpGridsVersion, toast],
  );

  // Reorder a room within its template, or move it to another template.
  // `toIdx` is the insertion index in the destination AFTER the room is
  // removed from its source (arrayMove semantics for same-template moves).
  //
  // Room grid content lives in the positional ref maps (gridsRef etc., keyed
  // `template#index`) which save() reads, so a move has to renumber those
  // maps to match the new room order, not just reorder level.templates.
  const commitMoveRoom = useCallback(
    (fromTpl: string, fromIdx: number, toTpl: string, toIdx: number) => {
      if (!level) return;
      if (fromTpl === toTpl && fromIdx === toIdx) return;
      const a = level.templates.find((t) => t.name === fromTpl);
      const b = level.templates.find((t) => t.name === toTpl);
      if (!a || !b) return;
      const moved = a.rooms[fromIdx];
      if (!moved) return;

      if (fromTpl !== toTpl) {
        // Rooms in a template share one size. Block drops that don't match so
        // the game doesn't read a mis-sized room.
        const ref = b.rooms[0];
        if (ref && (ref.width !== moved.width || ref.height !== moved.height)) {
          toast.error(
            `Can't move a ${moved.width}x${moved.height} room into "${toTpl}" (its rooms are ${ref.width}x${ref.height}).`,
          );
          return;
        }
      }

      // An Origin points at where a destination slot's data currently lives.
      type Origin = { tpl: string; idx: number };
      let newAOrigins: Origin[];
      let newBOrigins: Origin[] | null;
      if (fromTpl === toTpl) {
        const origins: Origin[] = a.rooms.map((_, i) => ({
          tpl: fromTpl,
          idx: i,
        }));
        const [m] = origins.splice(fromIdx, 1);
        origins.splice(Math.max(0, Math.min(toIdx, origins.length)), 0, m);
        newAOrigins = origins;
        newBOrigins = null;
      } else {
        newAOrigins = a.rooms
          .map((_, i): Origin => ({ tpl: fromTpl, idx: i }))
          .filter((_, i) => i !== fromIdx);
        const bOrigins: Origin[] = b.rooms.map((_, i) => ({
          tpl: toTpl,
          idx: i,
        }));
        bOrigins.splice(Math.max(0, Math.min(toIdx, bOrigins.length)), 0, {
          tpl: fromTpl,
          idx: fromIdx,
        });
        newBOrigins = bOrigins;
      }

      const roomAt = (o: Origin) => (o.tpl === fromTpl ? a : b).rooms[o.idx];
      const newARooms = newAOrigins.map(roomAt);
      const newBRooms = newBOrigins ? newBOrigins.map(roomAt) : null;

      const affected = fromTpl === toTpl ? [fromTpl] : [fromTpl, toTpl];
      const orderByTpl: Record<string, Origin[]> = { [fromTpl]: newAOrigins };
      if (newBOrigins) orderByTpl[toTpl] = newBOrigins;

      // Renumber a positional map to the new order. Source and destination
      // key spaces overlap, so snapshot every origin value before deleting.
      const reshuffle = <T,>(map: Map<string, T>) => {
        const snap = new Map<string, T | undefined>();
        for (const tpl of affected) {
          for (const o of orderByTpl[tpl]) {
            const k = `${o.tpl}#${o.idx}`;
            if (!snap.has(k)) snap.set(k, map.get(k));
          }
        }
        for (const tpl of affected) {
          for (const k of Array.from(map.keys())) {
            if (k.startsWith(`${tpl}#`)) map.delete(k);
          }
        }
        for (const tpl of affected) {
          orderByTpl[tpl].forEach((o, p) => {
            const v = snap.get(`${o.tpl}#${o.idx}`);
            if (v !== undefined) map.set(`${tpl}#${p}`, v);
          });
        }
      };
      reshuffle(gridsRef.current);
      reshuffle(bgGridsRef.current);
      reshuffle(settingsRef.current);

      // Moving a template's only room out empties it. A template must keep at
      // least one room, so refill the source with a blank room of the same
      // size (mirrors deleting a template's last room).
      let finalARooms = newARooms;
      if (fromTpl !== toTpl && newARooms.length === 0) {
        const emptyName = palette.find((p) => p.name === "empty")?.name ?? "";
        const grid: string[][] = Array.from({ length: moved.height }, () =>
          new Array<string>(moved.width).fill(emptyName),
        );
        finalARooms = [
          {
            settings: [],
            foreground: grid.map((r) => r.slice()),
            background: [],
            width: moved.width,
            height: moved.height,
            comment: null,
            isDual: false,
          },
        ];
        gridsRef.current.set(
          `${fromTpl}#0`,
          grid.map((r) => r.slice()),
        );
        bgGridsRef.current.set(
          `${fromTpl}#0`,
          grid.map((r) => r.map(() => "")),
        );
      }

      // Every room in the affected templates shifted position, so re-mark
      // them all edited at their new keys and drop the old ones.
      for (const k of Array.from(editedKeysRef.current)) {
        if (affected.some((tpl) => k.startsWith(`${tpl}#`))) {
          editedKeysRef.current.delete(k);
        }
      }
      for (const tpl of affected) {
        const count =
          tpl === fromTpl ? finalARooms.length : orderByTpl[tpl].length;
        for (let p = 0; p < count; p++) {
          editedKeysRef.current.add(`${tpl}#${p}`);
        }
      }

      // Keep the canvas on whichever room the user had open.
      if (
        selectedRoom &&
        (selectedRoom.templateName === fromTpl ||
          selectedRoom.templateName === toTpl)
      ) {
        for (const tpl of affected) {
          const p = orderByTpl[tpl].findIndex(
            (o) =>
              o.tpl === selectedRoom.templateName &&
              o.idx === selectedRoom.roomIndex,
          );
          if (p !== -1) {
            setSelectedRoom({ templateName: tpl, roomIndex: p });
            break;
          }
        }
      }

      setLevel({
        ...level,
        templates: level.templates.map((t) => {
          if (t.name === fromTpl) return { ...t, rooms: finalARooms };
          if (newBRooms && t.name === toTpl) return { ...t, rooms: newBRooms };
          return t;
        }),
      });
      bumpGridsVersion();
      setEditedTick((t) => t + 1);
      setDirty(true);
    },
    [level, palette, selectedRoom, bumpGridsVersion, toast],
  );

  // Extract a room's current content (live grids/settings) as a clipboard
  // payload.
  const roomPayloadFor = useCallback(
    (templateName: string, roomIndex: number): RoomClip | null => {
      if (!level) return null;
      const tpl = level.templates.find((t) => t.name === templateName);
      const room = tpl?.rooms[roomIndex];
      if (!tpl || !room) return null;
      const key = `${templateName}#${roomIndex}`;
      const fg = gridsRef.current.get(key) ?? room.foreground;
      const settings = settingsRef.current.get(key) ?? room.settings;
      const isDual = settings.includes("dual");
      const bg = isDual ? (bgGridsRef.current.get(key) ?? room.background) : [];
      return { settings, comment: room.comment, foreground: fg, background: bg };
    },
    [level],
  );

  const commitCopyRoom = useCallback(
    async (templateName: string, roomIndex: number) => {
      const payload = roomPayloadFor(templateName, roomIndex);
      if (!payload) return;
      try {
        await writeRoomsToClipboard([payload]);
        toast.success(`Copied room ${roomIndex} of "${templateName}".`);
      } catch (err) {
        toast.error(`Copy failed: ${extractMessage(err)}`);
      }
    },
    [roomPayloadFor, toast],
  );

  const commitCopyAllRooms = useCallback(
    async (templateName: string) => {
      if (!level) return;
      const tpl = level.templates.find((t) => t.name === templateName);
      if (!tpl || tpl.rooms.length === 0) return;
      const payloads = tpl.rooms
        .map((_, i) => roomPayloadFor(templateName, i))
        .filter((p): p is RoomClip => p !== null);
      try {
        await writeRoomsToClipboard(payloads);
        toast.success(
          `Copied ${payloads.length} room${payloads.length === 1 ? "" : "s"} from "${templateName}".`,
        );
      } catch (err) {
        toast.error(`Copy failed: ${extractMessage(err)}`);
      }
    },
    [level, roomPayloadFor, toast],
  );

  // Append a room to whatever rooms are already on the clipboard (starting a
  // fresh set if it holds none), so rooms from different templates can be
  // gathered before a single paste.
  const commitAddRoomToClipboard = useCallback(
    async (templateName: string, roomIndex: number) => {
      const payload = roomPayloadFor(templateName, roomIndex);
      if (!payload) return;
      const existing = (await readRoomsFromClipboard()) ?? [];
      const next = [...existing, payload];
      try {
        await writeRoomsToClipboard(next);
        toast.success(`Added room to clipboard (${next.length} total).`);
      } catch (err) {
        toast.error(`Copy failed: ${extractMessage(err)}`);
      }
    },
    [roomPayloadFor, toast],
  );

  const commitPasteRooms = useCallback(
    async (templateName: string) => {
      if (!level) return;
      const tpl = level.templates.find((t) => t.name === templateName);
      if (!tpl) return;
      const clip = await readRoomsFromClipboard();
      if (!clip || clip.length === 0) {
        toast.error("Clipboard has no modlunky2 rooms.");
        return;
      }
      // Unknown tile names get pinned to "empty" (if present) or "" so a paste
      // into a foreign palette doesn't fail silently.
      const paletteSet = new Set(palette.map((p) => p.name));
      const fallback = paletteSet.has("empty") ? "empty" : "";
      const sanitizeRow = (row: string[]) =>
        row.map((n) => (paletteSet.has(n) ? n : fallback));
      const baseIdx = tpl.rooms.length;
      const newRooms = clip.map((r) => {
        const fg = r.foreground.map(sanitizeRow);
        const bg = r.background.map(sanitizeRow);
        return {
          settings: r.settings,
          foreground: fg,
          background: bg,
          width: fg[0]?.length ?? 0,
          height: fg.length,
          comment: r.comment,
          isDual: r.settings.includes("dual") || bg.length > 0,
        };
      });
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName
            ? { ...t, rooms: [...t.rooms, ...newRooms] }
            : t,
        ),
      });
      newRooms.forEach((nr, i) => {
        const key = `${templateName}#${baseIdx + i}`;
        gridsRef.current.set(
          key,
          nr.foreground.map((r) => r.slice()),
        );
        // Always populate a bg grid the size of fg so toggling dual on later
        // finds a canvas to paint on.
        const bgSized =
          nr.background.length > 0
            ? nr.background.map((r) => r.slice())
            : nr.foreground.map((r) => r.map(() => ""));
        bgGridsRef.current.set(key, bgSized);
        if (nr.settings.length > 0) {
          settingsRef.current.set(key, nr.settings.slice());
        }
        editedKeysRef.current.add(key);
      });
      setEditedTick((t) => t + 1);
      setSelectedRoom({ templateName, roomIndex: baseIdx });
      setDirty(true);
      toast.success(
        `Pasted ${newRooms.length} room${newRooms.length === 1 ? "" : "s"} into "${templateName}".`,
      );
    },
    [level, palette, toast],
  );

  // Peek the clipboard when a room context menu opens so the menu can offer
  // "Add to clipboard" only when rooms are already there.
  useEffect(() => {
    if (treeMenu?.kind !== "room") {
      setClipboardRoomCount(null);
      return;
    }
    let cancelled = false;
    void readRoomsFromClipboard().then((rooms) => {
      if (!cancelled) setClipboardRoomCount(rooms?.length ?? 0);
    });
    return () => {
      cancelled = true;
    };
  }, [treeMenu]);

  // Duplicate an existing room in place: same fg / bg / settings / comment,
  // appended to the template's rooms list.
  const commitDuplicateRoom = useCallback(
    (templateName: string, roomIndex: number) => {
      if (!level) return;
      const tpl = level.templates.find((t) => t.name === templateName);
      const room = tpl?.rooms[roomIndex];
      if (!tpl || !room) return;
      const key = `${templateName}#${roomIndex}`;
      const fg = (gridsRef.current.get(key) ?? room.foreground).map((row) =>
        row.slice(),
      );
      const bg = (bgGridsRef.current.get(key) ?? room.background).map((row) =>
        row.slice(),
      );
      const settings = (settingsRef.current.get(key) ?? room.settings).slice();
      const isDual = settings.includes("dual");
      const newRoom = {
        settings,
        foreground: fg,
        background: bg,
        width: room.width,
        height: room.height,
        comment: room.comment,
        isDual,
      };
      const newIdx = tpl.rooms.length;
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName ? { ...t, rooms: [...t.rooms, newRoom] } : t,
        ),
      });
      const newKey = `${templateName}#${newIdx}`;
      gridsRef.current.set(
        newKey,
        fg.map((r) => r.slice()),
      );
      bgGridsRef.current.set(
        newKey,
        bg.length > 0
          ? bg.map((r) => r.slice())
          : fg.map((r) => r.map(() => "")),
      );
      if (settings.length > 0) {
        settingsRef.current.set(newKey, settings.slice());
      }
      editedKeysRef.current.add(newKey);
      setEditedTick((t) => t + 1);
      setSelectedRoom({ templateName, roomIndex: newIdx });
      setDirty(true);
      toast.success(`Duplicated room ${roomIndex} of "${templateName}".`);
    },
    [level, toast],
  );

  const commitAddRoom = useCallback(
    (templateName: string) => {
      if (!level) return;
      const tpl = level.templates.find((t) => t.name === templateName);
      if (!tpl) return;
      // New room size matches the template's existing rooms so the game
      // treats it as a valid alternative.
      const first = tpl.rooms[0];
      const cols = first?.width ?? 10;
      const rows = first?.height ?? 8;
      const emptyName = palette.find((p) => p.name === "empty")?.name ?? "";
      const grid: string[][] = Array.from({ length: rows }, () =>
        new Array<string>(cols).fill(emptyName),
      );
      const newRoom = {
        settings: [] as string[],
        foreground: grid.map((row) => row.slice()),
        background: [] as string[][],
        width: cols,
        height: rows,
        comment: null,
        isDual: false,
      };
      const newIdx = tpl.rooms.length;
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName ? { ...t, rooms: [...t.rooms, newRoom] } : t,
        ),
      });
      const key = `${templateName}#${newIdx}`;
      gridsRef.current.set(
        key,
        grid.map((r) => r.slice()),
      );
      bgGridsRef.current.set(
        key,
        grid.map((r) => r.map(() => "")),
      );
      editedKeysRef.current.add(key);
      setEditedTick((t) => t + 1);
      setSelectedRoom({ templateName, roomIndex: newIdx });
      setDirty(true);
      toast.success(`Added room ${newIdx} to "${templateName}".`);
    },
    [level, palette, toast],
  );

  const commitDeleteRoom = useCallback(
    (templateName: string, roomIndex: number) => {
      if (!level) return;
      const tpl = level.templates.find((t) => t.name === templateName);
      if (!tpl) return;
      if (tpl.rooms.length <= 1) {
        // A template keeps at least one room, so deleting its only room
        // clears that room to blank rather than removing it (same result as
        // "Delete all rooms" on a single-room template).
        commitDeleteAllRooms(templateName);
        return;
      }
      // Drop the room and shift subsequent room keys down so refs still
      // line up with the new indices.
      const nextRooms = tpl.rooms.filter((_, i) => i !== roomIndex);
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName ? { ...t, rooms: nextRooms } : t,
        ),
      });
      const shift = <T,>(map: Map<string, T>) => {
        // Remove the deleted key, then renumber higher keys down by one.
        map.delete(`${templateName}#${roomIndex}`);
        for (let i = roomIndex + 1; i <= tpl.rooms.length; i++) {
          const from = `${templateName}#${i}`;
          const to = `${templateName}#${i - 1}`;
          const v = map.get(from);
          if (v !== undefined) {
            map.delete(from);
            map.set(to, v);
          }
        }
      };
      shift(gridsRef.current);
      shift(bgGridsRef.current);
      shift(settingsRef.current);
      // Same renumbering for editedKeysRef.
      const nextEdited = new Set<string>();
      for (const k of editedKeysRef.current) {
        if (!k.startsWith(`${templateName}#`)) {
          nextEdited.add(k);
          continue;
        }
        const idx = Number(k.slice(templateName.length + 1));
        if (idx === roomIndex) continue;
        if (idx > roomIndex) nextEdited.add(`${templateName}#${idx - 1}`);
        else nextEdited.add(k);
      }
      // Flag every remaining room of this template as edited so save picks
      // them up in the new positions.
      for (let i = 0; i < nextRooms.length; i++) {
        nextEdited.add(`${templateName}#${i}`);
      }
      editedKeysRef.current = nextEdited;
      if (
        selectedRoom?.templateName === templateName &&
        selectedRoom.roomIndex === roomIndex
      ) {
        setSelectedRoom({
          templateName,
          roomIndex: Math.min(roomIndex, nextRooms.length - 1),
        });
      } else if (
        selectedRoom?.templateName === templateName &&
        selectedRoom.roomIndex > roomIndex
      ) {
        setSelectedRoom({
          templateName,
          roomIndex: selectedRoom.roomIndex - 1,
        });
      }
      // Deleting the selected room clamps selection back to the same key
      // (e.g. room 0 -> room 0) while the shift moves different content under
      // it, so currentKey may not change; bump gridsVersion so the canvas
      // re-reads the grid now living at that key.
      bumpGridsVersion();
      setEditedTick((t) => t + 1);
      setDirty(true);
      toast.success(`Removed room ${roomIndex} from "${templateName}".`);
    },
    [level, selectedRoom, bumpGridsVersion, commitDeleteAllRooms, toast],
  );

  const commitEditRoomComment = useCallback(
    (templateName: string, roomIndex: number, next: string) => {
      if (!level) return;
      const cleaned = next.trim();
      setLevel({
        ...level,
        templates: level.templates.map((t) =>
          t.name === templateName
            ? {
                ...t,
                rooms: t.rooms.map((c, i) =>
                  i === roomIndex ? { ...c, comment: cleaned || null } : c,
                ),
              }
            : t,
        ),
      });
      editedKeysRef.current.add(`${templateName}#${roomIndex}`);
      setEditedTick((t) => t + 1);
      setDirty(true);
    },
    [level],
  );

  // Bulk-clear comments across the whole file: room comments, template
  // comments, or both. Save ships the full templates list, so setting the
  // dirty flag is enough for the cleared comments to persist on next save.
  const commitPurgeComments = useCallback(
    (scope: "rooms" | "templates" | "both") => {
      if (!level) return;
      const clearRooms = scope === "rooms" || scope === "both";
      const clearTemplates = scope === "templates" || scope === "both";
      setLevel({
        ...level,
        templates: level.templates.map((t) => ({
          ...t,
          comment: clearTemplates ? null : t.comment,
          rooms: clearRooms
            ? t.rooms.map((r) => (r.comment ? { ...r, comment: null } : r))
            : t.rooms,
        })),
      });
      setEditedTick((t) => t + 1);
      setDirty(true);
      const what =
        scope === "both"
          ? "room and template comments"
          : scope === "rooms"
            ? "room comments"
            : "template comments";
      toast.success(`Removed all ${what}.`);
    },
    [level, toast],
  );

  // Current foreground grid for a room, preferring live in-memory edits.
  const fgForRoom = useCallback(
    (templateName: string, roomIndex: number): string[][] => {
      const tpl = level?.templates.find((t) => t.name === templateName);
      const room = tpl?.rooms[roomIndex];
      if (!room) return [];
      return (
        gridsRef.current.get(`${templateName}#${roomIndex}`) ??
        room.foreground
      );
    },
    [level, gridsRef],
  );

  const trySelectRoom = (next: RoomKey) => {
    if (keyEq(selectedRoom, next)) return;
    setSelectedRoom(next);
  };

  return (
    <div className="editor-window">
      <EditorTopBar
        title={
          <>
            <span className="editor-window-pack">{pack}</span>
            <span className="editor-window-mode">
              {dirty && <span className="editor-window-dirty">•</span>}
              {editorModeLabel("vanilla")} Editor
              {selectedFile ? ` - ${selectedFile}` : ""}
              {selectedRoom
                ? ` [${selectedRoom.templateName} room ${selectedRoom.roomIndex}]`
                : ""}
            </span>
          </>
        }
        primary={primary}
        secondary={secondary}
        tool={tool}
        onSetTool={setTool}
        undoLen={undoLen}
        redoLen={redoLen}
        onUndo={undo}
        onRedo={redo}
        canSave={!!selectedFile && dirty}
        saving={saving}
        onRestore={() => setPendingRestore(true)}
        onSave={() => setPendingSave(true)}
        farRightExtras={
          <>
            <button
              type="button"
              className="editor-window-gear"
              onClick={() => {
                void openModFolder(pack).catch((e) =>
                  toast.error(`Couldn't open pack folder: ${String(e)}`),
                );
              }}
              title="Open pack folder"
              aria-label="Open pack folder"
            >
              <FolderOpen size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="editor-window-gear"
              onClick={() => setHelpOpen(true)}
              title="Keyboard shortcuts"
              aria-label="Keyboard shortcuts"
            >
              <Keyboard size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="editor-window-gear"
              onClick={() => setSettingsOpen(true)}
              title="Editor settings"
              aria-label="Editor settings"
            >
              <Settings size={16} aria-hidden="true" />
            </button>
          </>
        }
        centerExtras={
          <div
            className="editor-window-viewmode"
            role="group"
            aria-label="View"
          >
            <button
              type="button"
              className={`editor-viewmode-btn${viewMode === "room" ? " active" : ""}`}
              onClick={() => setViewMode("room")}
              onMouseDown={(e) => e.preventDefault()}
              title="Room view (Tab)"
              aria-pressed={viewMode === "room"}
            >
              Room
            </button>
            <button
              type="button"
              className={`editor-viewmode-btn${viewMode === "level" ? " active" : ""}`}
              onClick={() => setViewMode("level")}
              onMouseDown={(e) => e.preventDefault()}
              title="Whole-level view (Tab). Shows setroom, challenge, and Palace of Pleasure grids."
              aria-pressed={viewMode === "level"}
            >
              Level
            </button>
          </div>
        }
      />
      <div className="editor-window-body">
        <aside className="editor-window-sidebar editor-window-sidebar-left">
          <div className="vanilla-file-row">
            <button
              type="button"
              className="vanilla-file-switcher"
              onClick={openFilePicker}
              onContextMenu={(e) => {
                e.preventDefault();
                setFileMenu({ x: e.clientX, y: e.clientY });
              }}
            >
              {selectedFile ? (
                <>
                  <img
                    src={iconForSource(currentFileSource ?? "vanilla")}
                    alt=""
                    className="vanilla-file-icon"
                  />
                  <span className="vanilla-file-switcher-name">
                    {selectedFile}
                  </span>
                  <Caret open />
                </>
              ) : (
                <>
                  <span className="vanilla-file-switcher-name muted">
                    Pick a .lvl...
                  </span>
                  <Caret open />
                </>
              )}
            </button>
            {level && (
              <div className="vanilla-file-actions">
                <button
                  type="button"
                  className="vanilla-file-action"
                  onClick={() => setRulesModalOpen(true)}
                  title="Level rules (settings, chances, monsters)"
                  aria-label="Open level rules"
                >
                  <Settings2 size={14} aria-hidden="true" />
                  <span>Rules</span>
                </button>
                <button
                  type="button"
                  className={`vanilla-file-action${themeOverride ? " active" : ""}`}
                  onClick={() => setThemeModalOpen(true)}
                  title="Level theme (background + floor tint)"
                  aria-label="Open level theme"
                >
                  <Palette size={14} aria-hidden="true" />
                  <span>Theme</span>
                </button>
              </div>
            )}
          </div>
          <div className="editor-window-section-title editor-rooms-title">
            <span>Rooms</span>
            {level && (
              <button
                type="button"
                className="editor-rooms-manage"
                onClick={() => setRoomManagerOpen(true)}
                title="Manage rooms and comments"
              >
                Manage
              </button>
            )}
          </div>
          <VanillaRoomsTree
            templates={level?.templates ?? []}
            selected={selectedRoom}
            editedKeys={editedKeysRef.current}
            settingsOverrides={settingsRef.current}
            onSelect={trySelectRoom}
            onAddTemplate={
              level
                ? () => setPendingTreeOp({ kind: "addTemplate" })
                : undefined
            }
            onTemplateContextMenu={(name, e) =>
              setTreeMenu({
                kind: "template",
                templateName: name,
                x: e.clientX,
                y: e.clientY,
              })
            }
            onRoomContextMenu={(name, idx, e) =>
              setTreeMenu({
                kind: "room",
                templateName: name,
                roomIndex: idx,
                x: e.clientX,
                y: e.clientY,
              })
            }
          />
        </aside>
        <main className="editor-window-canvas">
          {!selectedFile && (
            <div className="editor-window-status">
              Pick a .lvl file from the left to open it.
            </div>
          )}
          {selectedFile && loading && (
            <div className="editor-window-status">
              Loading {selectedFile}...
            </div>
          )}
          {selectedFile && !loading && !selectedRoom && viewMode === "room" && (
            <div className="editor-window-status">
              Pick a room from the sidebar to open it.
            </div>
          )}
          {selectedFile &&
            !loading &&
            viewMode === "level" &&
            atlas &&
            (levelViewData ? (
              <div className="editor-canvas-wrap">
                <div className="editor-canvas-surface">
                  <TileCanvas
                    ref={canvasRef}
                    viewKey={`level-${pack}-${selectedFile}-${levelViewData.hasBg ? "dual" : "single"}-v${gridsVersion}`}
                    atlas={atlas}
                    tiles={levelViewData.combined}
                    tileDisplaySize={tileDisplaySize}
                    backgroundImageUrl={isCosmicBackground ? null : bgUrl}
                    cosmicBackdropUrl={
                      isCosmicBackground ? cosmicBackdropUrl : null
                    }
                    cosmicSubthemeDecoUrl={
                      isCosmicBackground ? cosmicDecoUrl : null
                    }
                    onZoomChange={setZoom}
                    zoomFit={zoomFit}
                    initialZoom={initialZoom}
                    showTileGrid={prefs.showTileGrid}
                    showRoomGrid={prefs.showRoomGrid}
                    readOnly
                    onCellClick={handleLevelCellClick}
                    renderMode={renderMode}
                    badges={levelViewData.badges}
                    sections={
                      levelViewData.hasBg
                        ? [
                            {
                              colStart: 0,
                              colEnd: levelViewData.fgCols,
                              label: "Foreground",
                            },
                            {
                              colStart: levelViewData.fgCols + DUAL_GAP_COLS,
                              colEnd:
                                levelViewData.fgCols +
                                DUAL_GAP_COLS +
                                levelViewData.fgCols,
                              label: "Background",
                            },
                          ]
                        : undefined
                    }
                  />
                </div>
                <EditorBottomBar
                  zoom={zoom}
                  roomOpen={false}
                  roomSettingsEdited={false}
                  roomSettings={[]}
                  showTileGrid={prefs.showTileGrid}
                  showRoomGrid={prefs.showRoomGrid}
                  onSetZoom={(z) => canvasRef.current?.setZoom(z)}
                  onZoomToFit={() => canvasRef.current?.zoomToFit()}
                  onToggleSetting={() => {}}
                  onSetShowTileGrid={(v) => updatePrefs({ showTileGrid: v })}
                  onSetShowRoomGrid={(v) => updatePrefs({ showRoomGrid: v })}
                  renderMode={renderMode}
                  onSetRenderMode={(m) =>
                    updatePrefs({ clampRender: m === "cell" })
                  }
                />
              </div>
            ) : (
              <div className="editor-window-status">
                No fixed-position room templates in this file. Level view is
                only useful for files that place rooms at fixed grid positions
                (setroom, challenge, or Palace of Pleasure).
              </div>
            ))}
          {selectedFile &&
            !loading &&
            viewMode === "room" &&
            selectedRoom &&
            atlas &&
            combinedGrid && (
              <div className="editor-canvas-wrap">
                <div className="editor-canvas-surface">
                  <TileCanvas
                    ref={canvasRef}
                    viewKey={`${pack}-${selectedFile}-${selectedRoom.templateName}-${selectedRoom.roomIndex}-${effectiveLayerView}-v${gridsVersion}`}
                    atlas={atlas}
                    tiles={combinedGrid}
                    tileDisplaySize={tileDisplaySize}
                    primary={primary}
                    secondary={secondary}
                    onPaint={handlePaint}
                    onStrokeEnd={handleStrokeEnd}
                    backgroundImageUrl={isCosmicBackground ? null : bgUrl}
                    cosmicBackdropUrl={
                      isCosmicBackground ? cosmicBackdropUrl : null
                    }
                    cosmicSubthemeDecoUrl={
                      isCosmicBackground ? cosmicDecoUrl : null
                    }
                    onZoomChange={setZoom}
                    zoomFit={zoomFit}
                    initialZoom={initialZoom}
                    canPaintCell={canPaintCell}
                    formatHover={formatHover}
                    sections={canvasSections}
                    showTileGrid={prefs.showTileGrid}
                    showRoomGrid={prefs.showRoomGrid}
                    tool={tool}
                    eraseName={
                      palette.find((p) => p.name === "empty")?.name ?? ""
                    }
                    onPick={canvasOnPick}
                    mirrorCell={mirrorCell}
                    onSelectionChange={setSelection}
                    onMoveSelection={commitMarqueeMove}
                    extraSelectionRects={extraSelectionRects}
                    renderMode={renderMode}
                  />
                </div>
                <EditorBottomBar
                  zoom={zoom}
                  roomOpen={!!selectedRoom && !!currentRoomData}
                  roomSettingsEdited={currentSettingsEdited}
                  roomSettings={coerceSettings(currentSettings)}
                  isDual={isDual}
                  linkLayers={linkLayers}
                  layerView={effectiveLayerView}
                  showTileGrid={prefs.showTileGrid}
                  showRoomGrid={prefs.showRoomGrid}
                  onSetZoom={(z) => canvasRef.current?.setZoom(z)}
                  onZoomToFit={() => canvasRef.current?.zoomToFit()}
                  onToggleSetting={(name, next) =>
                    handleToggleSetting(name, next)
                  }
                  onToggleLinkLayers={() => setLinkLayers((v) => !v)}
                  onSetLayerView={setLayerView}
                  onSetShowTileGrid={(v) => updatePrefs({ showTileGrid: v })}
                  onSetShowRoomGrid={(v) => updatePrefs({ showRoomGrid: v })}
                  mirrorMode={isOnlyFlip ? "onlyflip" : isFlip ? "flip" : "off"}
                  mirrored={currentMirrorState}
                  onSetMirrored={setCurrentMirror}
                  renderMode={renderMode}
                  onSetRenderMode={(m) =>
                    updatePrefs({ clampRender: m === "cell" })
                  }
                />
              </div>
            )}
        </main>
        <aside className="editor-window-sidebar editor-window-sidebar-right">
          <PaletteSidebarSection
            pal={pal}
            palette={palette}
            atlas={atlas}
            selectedFile={selectedFile}
            primary={primary}
            secondary={secondary}
            onSelectPrimary={setPrimary}
            onSelectSecondary={setSecondary}
            onOpenAddTile={level ? () => setAddOpen(true) : undefined}
            conflictCount={conflicts.length}
            onOpenConflicts={() => setConflictsOpen(true)}
            helpMode="vanilla"
            dense={prefs.paletteDense}
            onToggleDense={() =>
              updatePrefs({ paletteDense: !prefs.paletteDense })
            }
          />
        </aside>
      </div>
      {addOpen && (
        <AddTileModal
          existing={palette}
          biome={currentBiome}
          atlas={atlas}
          dependencyPalettes={level?.dependencyPalettes ?? []}
          onAdoptInherited={(source, entry) => {
            handleAdoptDependencyTile(source, entry);
            setAddOpen(false);
          }}
          onClose={() => setAddOpen(false)}
          onSubmit={handleAddTile}
        />
      )}
      {rulesModalOpen && level && (
        <Modal
          open
          onClose={() => setRulesModalOpen(false)}
          title={`Level rules${selectedFile ? `, ${selectedFile}` : ""}`}
          size="lg"
        >
          <RulesPanel
            levelSettings={effectiveRules.levelSettings}
            levelChances={effectiveRules.levelChances}
            monsterChances={effectiveRules.monsterChances}
            onChange={handleRulesChange}
          />
        </Modal>
      )}
      {themeModalOpen && level && selectedFile && (
        <Modal
          open
          onClose={() => setThemeModalOpen(false)}
          title={`Level theme - ${selectedFile}`}
          size="sm"
        >
          <VanillaThemePanel
            fileName={selectedFile}
            override={themeOverride}
            onChange={setThemeOverride}
          />
        </Modal>
      )}
      {filePickerOpen && (
        <Modal
          open
          onClose={() => setFilePickerOpen(false)}
          title="Open .lvl file"
          size="lg"
        >
          <VanillaFilePicker
            files={files}
            error={filesError}
            selected={selectedFile}
            onSelect={trySelectFile}
          />
        </Modal>
      )}
      {pendingFile !== null && (
        <Modal
          open
          onClose={cancelSwitch}
          title="Unsaved changes"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={cancelSwitch}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={confirmDiscardAndSwitch}
              >
                Discard and switch
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            You have unsaved edits in <code>{selectedFile}</code>. Open{" "}
            <code>{pendingFile}</code> anyway? Your edits will be lost.
          </p>
        </Modal>
      )}
      {closeGuard.showConfirm && (
        <Modal
          open
          onClose={closeGuard.onCancelClose}
          title="Close editor?"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={closeGuard.onCancelClose}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  void closeGuard.onConfirmClose();
                }}
              >
                Discard and close
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            You have unsaved edits in this pack. Close anyway? Your edits will
            be lost.
          </p>
        </Modal>
      )}
      {pendingCollision && (
        <Modal
          open
          onClose={() => setPendingCollision(null)}
          title="No non-conflicting codes left"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setPendingCollision(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void confirmCollisionAdd()}
              >
                Add anyway
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            Every remaining tile code is already used by a sister file (parent
            or peer level). Adding{" "}
            <code>
              {pendingCollision.kind === "add"
                ? pendingCollision.name
                : pendingCollision.entry.name}
            </code>{" "}
            with code <code>{pendingCollision.code}</code> may cause the game to
            render the wrong tile at that position when both files load
            together. Delete some tiles here to free up a non-conflicting code,
            or proceed anyway if you know the sister file won't be present.
          </p>
        </Modal>
      )}
      {conflictsOpen && (
        <ConflictsModal
          conflicts={conflicts}
          onClose={() => setConflictsOpen(false)}
          onResolveOne={resolveOneConflict}
          onResolveAll={resolveAllConflicts}
        />
      )}
      {pendingSave && (
        <Modal
          open
          onClose={() => setPendingSave(false)}
          title="Save changes"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setPendingSave(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setPendingSave(false);
                  void save();
                }}
                autoFocus
              >
                Save
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            Write all pending changes to disk?
          </p>
        </Modal>
      )}
      {pendingRestore && (
        <Modal
          open
          onClose={() => setPendingRestore(false)}
          title="Restore from disk"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setPendingRestore(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={confirmRestore}
              >
                Discard changes and reload
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            Reload <code>{selectedFile}</code> from disk? Every unsaved edit in
            every room will be lost.
          </p>
        </Modal>
      )}
      {helpOpen && (
        <KeyboardShortcutsModal
          showVanillaOnly
          onClose={() => setHelpOpen(false)}
        />
      )}
      {settingsOpen && (
        <EditorSettingsModal
          context="vanilla"
          prefs={prefs}
          onChangePrefs={updatePrefs}
          onClose={() => setSettingsOpen(false)}
        />
      )}
      {roomManagerOpen && level && (
        <RoomManagerModal
          open
          onClose={() => setRoomManagerOpen(false)}
          templates={level.templates}
          atlas={atlas}
          fgFor={fgForRoom}
          onEditTemplateComment={commitEditTemplateComment}
          onEditRoomComment={commitEditRoomComment}
          onJumpToRoom={(name, idx) => {
            setSelectedRoom({ templateName: name, roomIndex: idx });
            setViewMode("room");
            setRoomManagerOpen(false);
          }}
          onCopyRoom={(name, idx, append) => {
            if (append) void commitAddRoomToClipboard(name, idx);
            else void commitCopyRoom(name, idx);
          }}
          onDeleteRoom={commitDeleteRoom}
          onDeleteAllRooms={commitDeleteAllRooms}
          onMoveRoom={commitMoveRoom}
          onPurgeComments={commitPurgeComments}
        />
      )}
      {fileMenu && (
        <FileContextMenu
          x={fileMenu.x}
          y={fileMenu.y}
          fileName={selectedFile}
          onClose={() => setFileMenu(null)}
          onOpen={() => {
            if (!selectedFile) return;
            const file = selectedFile;
            setFileMenu(null);
            void openLevelFile(pack, file).catch((e) =>
              toast.error(`Couldn't open: ${String(e)}`),
            );
          }}
          onOpenWith={() => {
            if (!selectedFile) return;
            const file = selectedFile;
            setFileMenu(null);
            void openLevelFileWith(pack, file).catch((e) =>
              toast.error(`Couldn't open: ${String(e)}`),
            );
          }}
        />
      )}
      {treeMenu && (
        <TreeContextMenu
          menu={treeMenu}
          onClose={() => setTreeMenu(null)}
          templates={level?.templates ?? []}
          onOp={(op) => {
            setTreeMenu(null);
            setPendingTreeOp(op);
          }}
          clipboardRoomCount={clipboardRoomCount}
          onCopyRoom={(name, idx) => {
            void commitCopyRoom(name, idx);
          }}
          onCopyAllRooms={(name) => {
            void commitCopyAllRooms(name);
          }}
          onAddRoomToClipboard={(name, idx) => {
            void commitAddRoomToClipboard(name, idx);
          }}
          onPasteRoom={(name) => {
            void commitPasteRooms(name);
          }}
          onDuplicateRoom={(name, idx) => {
            commitDuplicateRoom(name, idx);
          }}
        />
      )}
      {pendingTreeOp && (
        <TreeOpModal
          op={pendingTreeOp}
          onClose={() => setPendingTreeOp(null)}
          onSubmitAddTemplate={(name, width, height) => {
            commitAddTemplate(name, width, height);
            setPendingTreeOp(null);
          }}
          onSubmitRenameTemplate={(oldName, newName) => {
            commitRenameTemplate(oldName, newName);
            setPendingTreeOp(null);
          }}
          onSubmitEditTemplateComment={(name, comment) => {
            commitEditTemplateComment(name, comment);
            setPendingTreeOp(null);
          }}
          onSubmitDeleteTemplate={(name) => {
            commitDeleteTemplate(name);
            setPendingTreeOp(null);
          }}
          onSubmitDeleteAllRooms={(name) => {
            commitDeleteAllRooms(name);
            setPendingTreeOp(null);
          }}
          onSubmitAddRoom={(name) => {
            commitAddRoom(name);
            setPendingTreeOp(null);
          }}
          onSubmitEditRoomComment={(name, idx, comment) => {
            commitEditRoomComment(name, idx, comment);
            setPendingTreeOp(null);
          }}
          onSubmitDeleteRoom={(name, idx) => {
            commitDeleteRoom(name, idx);
            setPendingTreeOp(null);
          }}
        />
      )}
    </div>
  );
}

// Right-click menu for the file switcher. A small escape hatch to open the
// current .lvl in an external program for anything the editor can't handle.
function FileContextMenu({
  x,
  y,
  fileName,
  onClose,
  onOpen,
  onOpenWith,
}: {
  x: number;
  y: number;
  fileName: string | null;
  onClose: () => void;
  onOpen: () => void;
  onOpenWith: () => void;
}) {
  const { menuRef, pos } = useFloatingMenu(x, y, onClose);
  return (
    <>
      <div
        ref={menuRef}
        className="tree-menu"
        style={{ left: pos.left, top: pos.top }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="tree-menu-item"
          onClick={onOpen}
          disabled={!fileName}
          title={
            fileName
              ? `Open ${fileName} with the default program`
              : "Pick a .lvl file first"
          }
        >
          Open
        </button>
        <button
          type="button"
          className="tree-menu-item"
          onClick={onOpenWith}
          disabled={!fileName}
          title={
            fileName
              ? `Pick a program to open ${fileName} with`
              : "Pick a .lvl file first"
          }
        >
          Open with...
        </button>
      </div>
    </>
  );
}

// Floating context menu positioned at the click point. Closes on any
// outside click, Esc, or scroll. Not a full popover system, just enough
// to route the user's right-click to an action.
function TreeContextMenu({
  menu,
  onClose,
  templates,
  clipboardRoomCount,
  onOp,
  onCopyRoom,
  onCopyAllRooms,
  onAddRoomToClipboard,
  onPasteRoom,
  onDuplicateRoom,
}: {
  menu:
    | { kind: "template"; templateName: string; x: number; y: number }
    | {
        kind: "room";
        templateName: string;
        roomIndex: number;
        x: number;
        y: number;
      };
  onClose: () => void;
  templates: VanillaLevelData["templates"];
  onOp: (
    op:
      | { kind: "addTemplate" }
      | { kind: "renameTemplate"; templateName: string; initialValue: string }
      | {
          kind: "editTemplateComment";
          templateName: string;
          initialValue: string;
        }
      | { kind: "deleteTemplate"; templateName: string }
      | { kind: "deleteAllRooms"; templateName: string }
      | { kind: "addRoom"; templateName: string }
      | {
          kind: "editRoomComment";
          templateName: string;
          roomIndex: number;
          initialValue: string;
        }
      | { kind: "deleteRoom"; templateName: string; roomIndex: number },
  ) => void;
  clipboardRoomCount: number | null;
  onCopyRoom: (templateName: string, roomIndex: number) => void;
  onCopyAllRooms: (templateName: string) => void;
  onAddRoomToClipboard: (templateName: string, roomIndex: number) => void;
  onPasteRoom: (templateName: string) => void;
  onDuplicateRoom: (templateName: string, roomIndex: number) => void;
}) {
  const tpl = templates.find((t) => t.name === menu.templateName);
  const room = menu.kind === "room" ? tpl?.rooms[menu.roomIndex] : undefined;
  const { menuRef, pos } = useFloatingMenu(menu.x, menu.y, onClose);
  return (
    <>
      <div
        ref={menuRef}
        className="tree-menu"
        style={{ left: pos.left, top: pos.top }}
        onClick={(e) => e.stopPropagation()}
      >
        {menu.kind === "template" && (
          <>
            <button
              type="button"
              className="tree-menu-item"
              onClick={() =>
                onOp({ kind: "addRoom", templateName: menu.templateName })
              }
            >
              Add room
            </button>
            {(tpl?.rooms.length ?? 0) > 0 && (
              <button
                type="button"
                className="tree-menu-item"
                onClick={() => {
                  onCopyAllRooms(menu.templateName);
                  onClose();
                }}
              >
                Copy all rooms
              </button>
            )}
            <button
              type="button"
              className="tree-menu-item"
              onClick={() => {
                onPasteRoom(menu.templateName);
                onClose();
              }}
            >
              Paste room(s)
            </button>
            <button
              type="button"
              className="tree-menu-item"
              onClick={() =>
                onOp({
                  kind: "renameTemplate",
                  templateName: menu.templateName,
                  initialValue: menu.templateName,
                })
              }
            >
              Rename...
            </button>
            <button
              type="button"
              className="tree-menu-item"
              onClick={() =>
                onOp({
                  kind: "editTemplateComment",
                  templateName: menu.templateName,
                  initialValue: tpl?.comment ?? "",
                })
              }
            >
              Edit comment...
            </button>
            <div className="tree-menu-sep" />
            {(tpl?.rooms.length ?? 0) > 0 && (
              <button
                type="button"
                className="tree-menu-item danger"
                onClick={() =>
                  onOp({
                    kind: "deleteAllRooms",
                    templateName: menu.templateName,
                  })
                }
              >
                Delete all rooms
              </button>
            )}
            <button
              type="button"
              className="tree-menu-item danger"
              onClick={() =>
                onOp({
                  kind: "deleteTemplate",
                  templateName: menu.templateName,
                })
              }
            >
              Delete template
            </button>
          </>
        )}
        {menu.kind === "room" && (
          <>
            <button
              type="button"
              className="tree-menu-item"
              onClick={() => {
                onCopyRoom(menu.templateName, menu.roomIndex);
                onClose();
              }}
            >
              Copy room
            </button>
            {clipboardRoomCount != null && clipboardRoomCount > 0 && (
              <button
                type="button"
                className="tree-menu-item"
                onClick={() => {
                  onAddRoomToClipboard(menu.templateName, menu.roomIndex);
                  onClose();
                }}
              >
                Add to clipboard ({clipboardRoomCount})
              </button>
            )}
            <button
              type="button"
              className="tree-menu-item"
              onClick={() => {
                onDuplicateRoom(menu.templateName, menu.roomIndex);
                onClose();
              }}
            >
              Duplicate room
            </button>
            <button
              type="button"
              className="tree-menu-item"
              onClick={() =>
                onOp({
                  kind: "editRoomComment",
                  templateName: menu.templateName,
                  roomIndex: menu.roomIndex,
                  initialValue: room?.comment ?? "",
                })
              }
            >
              Edit comment...
            </button>
            <div className="tree-menu-sep" />
            <button
              type="button"
              className="tree-menu-item danger"
              onClick={() =>
                onOp({
                  kind: "deleteRoom",
                  templateName: menu.templateName,
                  roomIndex: menu.roomIndex,
                })
              }
            >
              Delete room
            </button>
          </>
        )}
      </div>
    </>
  );
}

// One modal that switches on the pending-op kind. Keeps the modal shell
// consistent (title, footer buttons) and lets each op fill the body with
// whatever inputs it needs.
function TreeOpModal({
  op,
  onClose,
  onSubmitAddTemplate,
  onSubmitRenameTemplate,
  onSubmitEditTemplateComment,
  onSubmitDeleteTemplate,
  onSubmitDeleteAllRooms,
  onSubmitAddRoom,
  onSubmitEditRoomComment,
  onSubmitDeleteRoom,
}: {
  op:
    | { kind: "addTemplate" }
    | { kind: "renameTemplate"; templateName: string; initialValue: string }
    | {
        kind: "editTemplateComment";
        templateName: string;
        initialValue: string;
      }
    | { kind: "deleteTemplate"; templateName: string }
    | { kind: "deleteAllRooms"; templateName: string }
    | { kind: "addRoom"; templateName: string }
    | {
        kind: "editRoomComment";
        templateName: string;
        roomIndex: number;
        initialValue: string;
      }
    | { kind: "deleteRoom"; templateName: string; roomIndex: number };
  onClose: () => void;
  onSubmitAddTemplate: (name: string, width: number, height: number) => void;
  onSubmitRenameTemplate: (oldName: string, newName: string) => void;
  onSubmitEditTemplateComment: (name: string, comment: string) => void;
  onSubmitDeleteTemplate: (name: string) => void;
  onSubmitDeleteAllRooms: (name: string) => void;
  onSubmitAddRoom: (name: string) => void;
  onSubmitEditRoomComment: (
    name: string,
    roomIndex: number,
    comment: string,
  ) => void;
  onSubmitDeleteRoom: (name: string, roomIndex: number) => void;
}) {
  const initial =
    op.kind === "renameTemplate" ||
    op.kind === "editTemplateComment" ||
    op.kind === "editRoomComment"
      ? op.initialValue
      : "";
  const [value, setValue] = useState(initial);
  // New-template dimensions in tiles. Default 10x8 (single-room unit);
  // 30x8 / 10x16 / 30x16 / etc. are also valid via free-form input.
  const [addWidth, setAddWidth] = useState(10);
  const [addHeight, setAddHeight] = useState(8);

  const submit = () => {
    switch (op.kind) {
      case "addTemplate":
        onSubmitAddTemplate(value, addWidth, addHeight);
        break;
      case "renameTemplate":
        onSubmitRenameTemplate(op.templateName, value);
        break;
      case "editTemplateComment":
        onSubmitEditTemplateComment(op.templateName, value);
        break;
      case "editRoomComment":
        onSubmitEditRoomComment(op.templateName, op.roomIndex, value);
        break;
      case "addRoom":
        onSubmitAddRoom(op.templateName);
        break;
      case "deleteTemplate":
        onSubmitDeleteTemplate(op.templateName);
        break;
      case "deleteAllRooms":
        onSubmitDeleteAllRooms(op.templateName);
        break;
      case "deleteRoom":
        onSubmitDeleteRoom(op.templateName, op.roomIndex);
        break;
    }
  };

  const title = {
    addTemplate: "Add template",
    renameTemplate: `Rename "${op.kind === "renameTemplate" ? op.templateName : ""}"`,
    editTemplateComment: `Comment on "${op.kind === "editTemplateComment" ? op.templateName : ""}"`,
    editRoomComment: `Comment on "${op.kind === "editRoomComment" ? `${op.templateName}#${op.roomIndex}` : ""}"`,
    addRoom: `Add room to "${op.kind === "addRoom" ? op.templateName : ""}"`,
    deleteTemplate: "Delete template",
    deleteAllRooms: "Delete all rooms",
    deleteRoom: "Delete room",
  }[op.kind];

  const isDanger =
    op.kind === "deleteTemplate" ||
    op.kind === "deleteAllRooms" ||
    op.kind === "deleteRoom";
  const submitLabel = isDanger
    ? "Delete"
    : op.kind === "addRoom"
      ? "Add"
      : "Save";

  const needsText =
    op.kind === "addTemplate" ||
    op.kind === "renameTemplate" ||
    op.kind === "editTemplateComment" ||
    op.kind === "editRoomComment";

  return (
    <Modal
      open
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <div className="editor-confirm-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className={`btn ${isDanger ? "btn-danger" : "btn-primary"}`}
            onClick={submit}
          >
            {submitLabel}
          </button>
        </div>
      }
    >
      {op.kind === "addTemplate" && (
        <>
          <label className="tree-modal-label">Template name</label>
          <input
            type="text"
            className="tree-modal-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. setroom0-0"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          <label className="tree-modal-label" style={{ marginTop: 12 }}>
            Room size (tiles)
          </label>
          <div className="tree-modal-size-row">
            <input
              type="number"
              className="tree-modal-input tree-modal-size-input"
              min={1}
              max={200}
              value={addWidth}
              onChange={(e) =>
                setAddWidth(Math.max(1, Number(e.target.value) || 1))
              }
              aria-label="Width in tiles"
            />
            <span className="tree-modal-size-x">×</span>
            <input
              type="number"
              className="tree-modal-input tree-modal-size-input"
              min={1}
              max={200}
              value={addHeight}
              onChange={(e) =>
                setAddHeight(Math.max(1, Number(e.target.value) || 1))
              }
              aria-label="Height in tiles"
            />
          </div>
          <div className="tree-modal-presets">
            {(
              [
                { label: "10×8 single", w: 10, h: 8 },
                { label: "20×8 wide", w: 20, h: 8 },
                { label: "10×16 tall", w: 10, h: 16 },
                { label: "20×16 big", w: 20, h: 16 },
              ] as const
            ).map((p) => (
              <button
                key={p.label}
                type="button"
                className={`tree-modal-preset${addWidth === p.w && addHeight === p.h ? " active" : ""}`}
                onClick={() => {
                  setAddWidth(p.w);
                  setAddHeight(p.h);
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
          <p className="tree-modal-hint">
            Widerooms are 20×8, tallrooms 10×16. The game reads the template's
            stored size, so make sure it matches what the file expects.
          </p>
        </>
      )}
      {op.kind === "renameTemplate" && (
        <>
          <label className="tree-modal-label">New name</label>
          <input
            type="text"
            className="tree-modal-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
        </>
      )}
      {(op.kind === "editTemplateComment" || op.kind === "editRoomComment") && (
        <>
          <label className="tree-modal-label">Comment</label>
          <input
            type="text"
            className="tree-modal-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Leave blank to clear"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
        </>
      )}
      {op.kind === "addRoom" && (
        <p className="editor-confirm-body">
          Add another room to <code>{op.templateName}</code>? A blank room
          matching this template's existing size will be appended.
        </p>
      )}
      {op.kind === "deleteTemplate" && (
        <>
          <p className="editor-confirm-body">
            Delete template <code>{op.templateName}</code>? Every room in it
            will be removed.
          </p>
          <p className="editor-confirm-warn">
            This can't be undone. Save the file first if you want a backup.
          </p>
        </>
      )}
      {op.kind === "deleteAllRooms" && (
        <>
          <p className="editor-confirm-body">
            Delete every room in <code>{op.templateName}</code>? The template
            is kept with a single blank room.
          </p>
          <p className="editor-confirm-warn">
            This can't be undone. Save the file first if you want a backup.
          </p>
        </>
      )}
      {op.kind === "deleteRoom" && (
        <>
          <p className="editor-confirm-body">
            Delete room {op.roomIndex} from <code>{op.templateName}</code>?
          </p>
          <p className="editor-confirm-warn">
            This can't be undone. Save the file first if you want a backup.
          </p>
        </>
      )}
      {needsText && (
        <p className="tree-modal-hint" style={{ display: "none" }}>
          {/* keep type-narrowing simple */}
        </p>
      )}
    </Modal>
  );
}

/** Per-file theme picker for the vanilla editor. Writes to the file's
 *  top-comment marker via the parent's `themeOverride`. "Auto" clears the
 *  override so the biome falls back to the filename guess and the file keeps
 *  no marker at all. */
function VanillaThemePanel({
  fileName,
  override,
  onChange,
}: {
  fileName: string;
  override: ThemeOverride | null;
  onChange: (next: ThemeOverride | null) => void;
}) {
  const autoLabel = filenameThemeLabel(fileName);
  const isCosmic = override?.theme === COSMIC_OCEAN_THEME;
  const subthemeOptions = THEMES.filter((t) => t.id !== COSMIC_OCEAN_THEME);
  return (
    <div className="level-tree-form vanilla-theme-panel">
      <label className="tree-modal-label" htmlFor="vanilla-theme-select">
        Theme
      </label>
      <select
        id="vanilla-theme-select"
        value={override ? String(override.theme) : ""}
        onChange={(e) => {
          const v = e.target.value;
          if (v === "") {
            onChange(null);
          } else {
            onChange({
              theme: Number(v),
              subtheme: override?.subtheme ?? null,
            });
          }
        }}
      >
        <option value="">Auto (from filename: {autoLabel})</option>
        {THEMES.map((t) => (
          <option key={t.id} value={t.id}>
            {t.label}
          </option>
        ))}
      </select>
      {isCosmic && (
        <>
          <label className="tree-modal-label" htmlFor="vanilla-subtheme-select">
            Cosmic Ocean subtheme
          </label>
          <select
            id="vanilla-subtheme-select"
            value={override?.subtheme != null ? String(override.subtheme) : ""}
            onChange={(e) => {
              const v = e.target.value;
              onChange({
                theme: COSMIC_OCEAN_THEME,
                subtheme: v === "" ? null : Number(v),
              });
            }}
          >
            <option value="">-- none --</option>
            {subthemeOptions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </>
      )}
      <p className="level-tree-form-hint">
        Theme drives the background art and floor-tile tint. Vanilla files infer
        it from their filename; set it here for custom (pack-only) files.
        Choosing <strong>Auto</strong> removes the marker entirely, leaving
        nothing in the file.
      </p>
      {override && (
        <div className="level-tree-form-footer">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => onChange(null)}
          >
            Reset to filename default
          </button>
        </div>
      )}
    </div>
  );
}

function VanillaFilePicker({
  files,
  error,
  selected,
  onSelect,
}: {
  files: VanillaLevelListEntry[] | null;
  error: string | null;
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  const [filter, setFilter] = useState("");
  const [levelsOpen, setLevelsOpen] = useState(true);
  const [arenaOpen, setArenaOpen] = useState(false);

  if (error) return <div className="level-tree-error">{error}</div>;
  if (files === null)
    return <div className="level-tree-status">Loading...</div>;

  const filterLower = filter.trim().toLowerCase();
  const matches = (name: string) =>
    filterLower.length === 0 || name.toLowerCase().includes(filterLower);

  const mainFiles = files.filter(
    (f) => !f.fileName.startsWith("Arena/") && matches(f.fileName),
  );
  const arenaFiles = files.filter(
    (f) => f.fileName.startsWith("Arena/") && matches(f.fileName),
  );
  // Filtering auto-expands both groups so results are visible.
  const filtering = filterLower.length > 0;
  const levelsExpanded = filtering ? mainFiles.length > 0 : levelsOpen;
  const arenaExpanded = filtering ? arenaFiles.length > 0 : arenaOpen;

  return (
    <div className="vanilla-file-picker">
      <input
        type="text"
        className="vanilla-file-search"
        placeholder="Filter files..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        autoFocus
      />
      <div className="vanilla-file-picker-hint">
        <img src={lvlModdedIcon} alt="" className="vanilla-file-icon inline" />
        Already modded &nbsp;Â·&nbsp;
        <img src={lvlIcon} alt="" className="vanilla-file-icon inline" />
        Vanilla (save creates an override) &nbsp;Â·&nbsp;
        <img src={lvlCustomIcon} alt="" className="vanilla-file-icon inline" />
        Custom (pack-only, not a base-game file)
      </div>
      <div className="vanilla-file-picker-groups">
        <FilePickerGroup
          label="Levels"
          files={mainFiles}
          selected={selected}
          onSelect={onSelect}
          open={levelsExpanded}
          onToggle={() => setLevelsOpen((v) => !v)}
        />
        <FilePickerGroup
          label="Arena"
          files={arenaFiles}
          selected={selected}
          onSelect={onSelect}
          open={arenaExpanded}
          onToggle={() => setArenaOpen((v) => !v)}
        />
      </div>
    </div>
  );
}

function FilePickerGroup({
  label,
  files,
  selected,
  onSelect,
  open,
  onToggle,
}: {
  label: string;
  files: VanillaLevelListEntry[];
  selected: string | null;
  onSelect: (name: string) => void;
  open: boolean;
  onToggle: () => void;
}) {
  const modded = files.filter((f) => f.source === "modded").length;
  const custom = files.filter((f) => f.source === "custom").length;
  // Compact "N modded, M custom / total" summary; each tag is dropped when
  // its count is zero so an all-vanilla group just shows the total.
  const tags = [
    modded > 0 ? `${modded} modded` : null,
    custom > 0 ? `${custom} custom` : null,
  ].filter(Boolean);
  return (
    <section className="vanilla-file-group">
      <button
        type="button"
        className={`vanilla-file-group-header${open ? " open" : ""}`}
        onClick={onToggle}
      >
        <Caret open={open} />
        <span className="vanilla-file-group-label">{label}</span>
        <span className="vanilla-file-group-count">
          {tags.length > 0
            ? `${tags.join(", ")} / ${files.length}`
            : files.length}
        </span>
      </button>
      {open && files.length > 0 && (
        <ul className="vanilla-file-group-list">
          {files.map((f) => {
            const displayName = f.fileName.startsWith("Arena/")
              ? f.fileName.slice("Arena/".length)
              : f.fileName;
            return (
              <li key={f.fileName}>
                <button
                  type="button"
                  className={`vanilla-file-picker-item${selected === f.fileName ? " selected" : ""} ${f.source}`}
                  onClick={() => onSelect(f.fileName)}
                  title={`${f.fileName}\n${titleForSource(f.source)}`}
                >
                  <img
                    src={iconForSource(f.source)}
                    alt=""
                    className="vanilla-file-icon"
                  />
                  <span className="vanilla-file-picker-name">
                    {displayName}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {open && files.length === 0 && (
        <div className="vanilla-file-group-empty">No matches.</div>
      )}
    </section>
  );
}

function VanillaRoomsTree({
  templates,
  selected,
  editedKeys,
  settingsOverrides,
  onSelect,
  onTemplateContextMenu,
  onRoomContextMenu,
  onAddTemplate,
}: {
  templates: VanillaLevelData["templates"];
  selected: RoomKey | null;
  editedKeys: Set<string>;
  settingsOverrides: Map<string, string[]>;
  onSelect: (next: RoomKey) => void;
  onTemplateContextMenu?: (
    templateName: string,
    e: React.MouseEvent<HTMLElement>,
  ) => void;
  onRoomContextMenu?: (
    templateName: string,
    roomIndex: number,
    e: React.MouseEvent<HTMLElement>,
  ) => void;
  onAddTemplate?: () => void;
}) {
  const [filter, setFilter] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const filterLower = filter.trim().toLowerCase();
  const listRef = useRef<HTMLUListElement>(null);

  // --- Keyboard navigation of the rooms tree ---
  // The rendered buttons carry data-template (headers + rooms) and
  // data-room-index (rooms only). Up/Down walk the combined list of headers
  // and rooms in document (visual) order: only expanded, unfiltered rooms
  // exist in the DOM, so collapse/filter state and template boundaries are
  // respected for free. Landing on a room selects it so the canvas follows;
  // landing on a header only moves focus (the canvas stays put) so a
  // collapsed template is still reachable and can be re-opened with Right.
  // Left/Right collapse/expand the template.

  // Headers + rooms in document order. A comma selector returns matches in
  // document order regardless of the order the selectors are written.
  const navButtons = () =>
    Array.from(
      listRef.current?.querySelectorAll<HTMLButtonElement>(
        "button.vanilla-rooms-template, button.vanilla-rooms-room",
      ) ?? [],
    );

  const isRoomButton = (btn: HTMLButtonElement) =>
    btn.classList.contains("vanilla-rooms-room");

  const selectFromButton = (btn: HTMLButtonElement) => {
    const templateName = btn.dataset.template;
    const roomIndex = btn.dataset.roomIndex;
    if (templateName == null || roomIndex == null) return;
    onSelect({ templateName, roomIndex: Number(roomIndex) });
  };

  // Move focus to the adjacent tree button (header or room). Selecting only
  // when it's a room is what keeps focus from dragging the canvas onto a
  // header. Returns false at the ends so the key falls through.
  const focusAdjacent = (from: HTMLButtonElement, dir: 1 | -1) => {
    const items = navButtons();
    const idx = items.indexOf(from);
    if (idx === -1) return false;
    const next = items[idx + dir];
    if (!next) return false;
    next.focus();
    if (isRoomButton(next)) selectFromButton(next);
    return true;
  };

  const collapse = (name: string) =>
    setCollapsed((prev) => new Set(prev).add(name));
  const expand = (name: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.delete(name);
      return next;
    });

  const onRoomKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    switch (e.key) {
      case "ArrowDown":
      case "ArrowUp":
        if (focusAdjacent(e.currentTarget, e.key === "ArrowDown" ? 1 : -1))
          e.preventDefault();
        return;
      case "ArrowLeft": {
        // Collapse the parent template and retreat to its header. Focus the
        // header first: collapsing unmounts this room button. A filter forces
        // every template open, so collapse is a no-op then -- skip it.
        const templateName = e.currentTarget.dataset.template;
        if (templateName == null || filterLower.length > 0) return;
        e.preventDefault();
        // The header is the previous nav item at the top of the template; walk
        // back to the nearest one.
        const items = navButtons();
        for (let i = items.indexOf(e.currentTarget) - 1; i >= 0; i--) {
          if (!isRoomButton(items[i])) {
            items[i].focus();
            break;
          }
        }
        collapse(templateName);
        return;
      }
      default:
        return;
    }
  };

  const onTemplateKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    const templateName = e.currentTarget.dataset.template;
    if (templateName == null) return;
    const isCollapsed = collapsed.has(templateName) && filterLower.length === 0;
    switch (e.key) {
      case "ArrowDown":
      case "ArrowUp":
        if (focusAdjacent(e.currentTarget, e.key === "ArrowDown" ? 1 : -1))
          e.preventDefault();
        return;
      case "ArrowRight": {
        e.preventDefault();
        // Collapsed: open it (focus stays on the header). Already open: dive
        // into the first child room, but only if the next item really is this
        // template's room -- an empty template shouldn't leap into the next.
        if (isCollapsed) {
          expand(templateName);
          return;
        }
        const items = navButtons();
        const next = items[items.indexOf(e.currentTarget) + 1];
        if (
          next &&
          isRoomButton(next) &&
          next.dataset.template === templateName
        ) {
          next.focus();
          selectFromButton(next);
        }
        return;
      }
      case "ArrowLeft":
        if (isCollapsed || filterLower.length > 0) return;
        e.preventDefault();
        collapse(templateName);
        return;
      default:
        return;
    }
  };

  const toggle = (name: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  // Expand/collapse every template at once. When anything is open the button
  // collapses all; when everything is collapsed it expands all. A filter
  // force-expands every template regardless of this set, so the button has no
  // visible effect then and is disabled.
  const anyExpanded = templates.some((t) => !collapsed.has(t.name));
  const toggleAll = () =>
    setCollapsed(
      anyExpanded ? new Set(templates.map((t) => t.name)) : new Set(),
    );

  const filtered = filterLower
    ? templates.filter((t) => t.name.toLowerCase().includes(filterLower))
    : templates;

  return (
    <div className="vanilla-rooms">
      <div className="vanilla-rooms-toolbar">
        <input
          type="text"
          className="vanilla-file-search"
          placeholder="Filter rooms..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {templates.length > 0 && (
          <button
            type="button"
            className="vanilla-rooms-collapse-all"
            onClick={toggleAll}
            disabled={filterLower.length > 0}
            title={
              anyExpanded ? "Collapse all templates" : "Expand all templates"
            }
            aria-label={
              anyExpanded ? "Collapse all templates" : "Expand all templates"
            }
          >
            {anyExpanded ? (
              <ChevronsDownUp size={15} aria-hidden="true" />
            ) : (
              <ChevronsUpDown size={15} aria-hidden="true" />
            )}
          </button>
        )}
      </div>
      {templates.length === 0 ? (
        <div className="level-tree-status">No templates.</div>
      ) : (
        <ul className="vanilla-rooms-list" ref={listRef}>
          {filtered.map((tpl) => {
            const isExpanded =
              !collapsed.has(tpl.name) || filterLower.length > 0;
            const anyChildSelected = tpl.rooms.some((_, idx) =>
              keyEq(selected, { templateName: tpl.name, roomIndex: idx }),
            );
            const anyChildEdited = tpl.rooms.some((_, idx) =>
              editedKeys.has(`${tpl.name}#${idx}`),
            );
            const templateClass = [
              "vanilla-rooms-template",
              anyChildSelected ? "selected" : "",
              anyChildEdited ? "edited" : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <li key={tpl.name}>
                <button
                  type="button"
                  className={templateClass}
                  data-template={tpl.name}
                  onClick={() => toggle(tpl.name)}
                  onKeyDown={onTemplateKeyDown}
                  onContextMenu={(e) => {
                    if (!onTemplateContextMenu) return;
                    e.preventDefault();
                    onTemplateContextMenu(tpl.name, e);
                  }}
                  title={tpl.comment ?? tpl.name}
                >
                  <span className="vanilla-rooms-arrow">
                    <Caret open={isExpanded} />
                  </span>
                  <span className="vanilla-rooms-name">{tpl.name}</span>
                  {anyChildEdited && (
                    <span className="vanilla-rooms-edited">•</span>
                  )}
                  <span className="vanilla-rooms-count">
                    {tpl.rooms.length}
                  </span>
                </button>
                {isExpanded && (
                  <ul className="vanilla-rooms-children">
                    {tpl.rooms.map((c, idx) => {
                      const key = `${tpl.name}#${idx}`;
                      const isSelected = keyEq(selected, {
                        templateName: tpl.name,
                        roomIndex: idx,
                      });
                      const isEdited = editedKeys.has(key);
                      // Badge from the live (unsaved) settings override when
                      // present so toggling a flag updates the list immediately.
                      const override = settingsOverrides.get(key);
                      const effRoom = override
                        ? { settings: override, isDual: override.includes("dual") }
                        : c;
                      return (
                        <li key={idx}>
                          <button
                            type="button"
                            className={`vanilla-rooms-room${isSelected ? " selected" : ""}${isEdited ? " edited" : ""}`}
                            data-template={tpl.name}
                            data-room-index={idx}
                            onClick={() =>
                              onSelect({
                                templateName: tpl.name,
                                roomIndex: idx,
                              })
                            }
                            onContextMenu={(e) => {
                              if (!onRoomContextMenu) return;
                              e.preventDefault();
                              onRoomContextMenu(tpl.name, idx, e);
                            }}
                            onKeyDown={onRoomKeyDown}
                          >
                            <span
                              className="vanilla-rooms-room-label"
                              title={c.comment ?? `Room ${idx}`}
                            >
                              room {idx}
                            </span>
                            {roomTags(effRoom).map((tag) => (
                              <span
                                key={tag}
                                className={`vanilla-rooms-tag vanilla-rooms-tag-${tag}`}
                                title={`${TEMPLATE_SETTING_LABELS[tag]}: ${TEMPLATE_SETTING_HINTS[tag]}`}
                              >
                                {tag}
                              </span>
                            ))}
                            {isEdited && (
                              <span className="vanilla-rooms-edited">•</span>
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {onAddTemplate && (
        <button
          type="button"
          className="vanilla-rooms-add"
          onClick={onAddTemplate}
        >
          + New template...
        </button>
      )}
    </div>
  );
}

// Grid rooms the game draws with their front/back layers swapped so they line
// up with adjacent setrooms. Only the two Palace of Pleasure entries are
// fixed-grid `_{y}-{x}` rooms (the others are one-off templates that never
// appear in the mosaic), but the full set mirrors the Python editor for parity.
const REVERSED_ROOMS = new Set([
  "palaceofpleasure_1-1",
  "palaceofpleasure_3-2",
  "udjatentrance",
  "challenge_entrance",
  "blackmarket_exit",
]);

// Template settings shown as badges in the room list, in a stable display
// order regardless of the order they appear in the file. `dual` also covers
// rooms that carry a background layer without an explicit `\!dual` flag.
const ROOM_TAG_ORDER = [
  "dual",
  "flip",
  "onlyflip",
  "ignore",
  "rare",
  "hard",
  "liquid",
  "purge",
] as const;

function roomTags(room: {
  settings: string[];
  isDual: boolean;
}): TemplateSettingName[] {
  return ROOM_TAG_ORDER.filter(
    (tag) =>
      room.settings.includes(tag) || (tag === "dual" && room.isDual),
  );
}

// One room's portable content on the clipboard. Tile NAMES (not codes) so a
// paste into a file with a different palette still lands the right sprites when
// the names line up.
type RoomClip = {
  settings: string[];
  comment: string | null;
  foreground: string[][];
  background: string[][];
};

// Rooms are copied as an array so one clipboard entry can carry many rooms.
async function writeRoomsToClipboard(rooms: RoomClip[]): Promise<void> {
  await writeClipboardText(
    JSON.stringify({ kind: "modlunky2-rooms", version: 1, rooms }),
  );
}

function normalizeRoomClip(raw: unknown): RoomClip | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as {
    settings?: unknown;
    comment?: unknown;
    foreground?: unknown;
    background?: unknown;
  };
  if (!Array.isArray(r.foreground)) return null;
  const grid = (g: unknown): string[][] =>
    Array.isArray(g)
      ? g.map((row) => (Array.isArray(row) ? row.map((c) => String(c)) : []))
      : [];
  return {
    settings: Array.isArray(r.settings)
      ? r.settings.filter((s): s is string => typeof s === "string")
      : [],
    comment: typeof r.comment === "string" ? r.comment : null,
    foreground: grid(r.foreground),
    background: grid(r.background),
  };
}

// Reads room(s) off the clipboard. Accepts the multi-room `modlunky2-rooms`
// array and the legacy single `modlunky2-room` blob (wrapped to one). Returns
// null when the clipboard isn't modlunky2 rooms.
async function readRoomsFromClipboard(): Promise<RoomClip[] | null> {
  let text: string;
  try {
    text = await readClipboardText();
  } catch {
    return null;
  }
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch {
    return null;
  }
  if (!payload || typeof payload !== "object") return null;
  const p = payload as { kind?: string; rooms?: unknown };
  if (p.kind === "modlunky2-rooms" && Array.isArray(p.rooms)) {
    const out = p.rooms
      .map(normalizeRoomClip)
      .filter((r): r is RoomClip => r !== null);
    return out.length > 0 ? out : null;
  }
  if (p.kind === "modlunky2-room") {
    const one = normalizeRoomClip(payload);
    return one ? [one] : null;
  }
  return null;
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
