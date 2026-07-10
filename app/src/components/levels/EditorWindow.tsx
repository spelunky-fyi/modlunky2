// Content for the separate editor window opened by open_level_editor_window.
// Vanilla mode delegates to VanillaEditor (per-file, per-template, per-room
// editing). Custom mode edits a single flat .lvl file with its own palette.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BUILT_IN_SAVE_FORMATS,
  addCustomSaveFormat,
  buildTileNameAtlas,
  editorModeLabel,
  getBiomeBackground,
  getCosmicBackdrop,
  getCosmicSubthemeDecoration,
  getDefaultSaveFormat,
  listCustomSaveFormats,
  listShortCodes,
  loadCustomConfig,
  loadCustomLevel,
  saveCustomConfig,
  saveCustomLevel,
  type CustomLevelData,
  type CustomLevelPaletteEntry,
  type CustomLevelSaveFormat,
  type EditorAtlas,
  type EditorMode,
  type LevelConfiguration,
  type LevelConfigurations,
  type TileSprite,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import { AddTileModal } from "./AddTileModal";
import { EditorBottomBar } from "./EditorBottomBar";
import { EditorTopBar } from "./EditorTopBar";
import {
  Expand,
  Keyboard,
  ListOrdered,
  Settings,
  Settings2,
} from "lucide-react";
import { EditorSettingsModal } from "./EditorSettingsModal";
import { ExtractRequiredGate } from "./ExtractRequiredGate";
import { KeyboardShortcutsModal } from "./KeyboardShortcutsModal";
import {
  LevelConfigPanel,
  COSMIC_OCEAN_THEME,
  defaultConfigEntry,
} from "./LevelConfigPanel";
import { NewSaveFormatModal } from "./NewSaveFormatModal";
import { PaletteSidebarSection } from "./PaletteSidebarSection";
import { ResizeLevelModal, type ResizePlan } from "./ResizeLevelModal";
import { LevelFileTree } from "./LevelFileTree";
import { SequencePanel } from "./SequencePanel";
import { TileCanvas } from "./TileCanvas";
import { VanillaEditor } from "./VanillaEditor";
import { useEditorPrefs } from "./hooks/useEditorPrefs";
import { useCloseGuard } from "./hooks/useCloseGuard";
import { useLevelCanvas } from "./hooks/useLevelCanvas";
import { usePaletteEditor } from "./hooks/usePaletteEditor";
import { biomeForThemeId, DEFAULT_BIOME } from "./biomes";
import "./EditorWindow.css";

const TILE_DISPLAY_SIZE = 48;

interface Props {
  pack: string;
  mode: EditorMode;
}

export function EditorWindow({ pack, mode }: Props) {
  // Both editors call get_tile_sprite / build_editor_atlas, which resolve
  // against Data/Textures under the extracted dir. Without extracted
  // assets, every tile renders as a placeholder and the whole UI reads
  // as broken. Gate the entire editor body on the presence check so
  // users see actionable copy instead.
  return (
    <ExtractRequiredGate>
      {mode === "vanilla" ? (
        <VanillaEditor pack={pack} />
      ) : (
        <CustomEditor pack={pack} />
      )}
    </ExtractRequiredGate>
  );
}

function CustomEditor({ pack }: { pack: string }) {
  const toast = useToast();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [level, setLevel] = useState<CustomLevelData | null>(null);
  const [palette, setPalette] = useState<CustomLevelPaletteEntry[]>([]);
  const [atlas, setAtlas] = useState<EditorAtlas | null>(null);
  const [loading, setLoading] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pendingFile, setPendingFile] = useState<string | null>(null);
  const [pendingRestore, setPendingRestore] = useState(false);
  const [pendingSave, setPendingSave] = useState(false);
  // App-wide editor preferences (zoom mode, clamp, grid defaults). Persisted,
  // so they survive reopening the window and app restarts. Held here and
  // threaded down to the canvas, bottom bar, and settings modal.
  const { prefs, updatePrefs } = useEditorPrefs();
  const renderMode = prefs.clampRender ? "cell" : "natural";
  const [bgUrl, setBgUrl] = useState<string | null>(null);
  // Bundled Cosmic Ocean starfield backdrop. Fetched once per session; the
  // canvas only tiles it when the current file's LevelConfiguration.theme
  // resolves to Cosmic Ocean (theme id 10).
  const [cosmicBackdropUrl, setCosmicBackdropUrl] = useState<string | null>(
    null,
  );
  // Per-subtheme decoration crop from Data/Textures/deco_cosmic.png, used to
  // scatter Python's 31 rotated/scaled shapes over the starfield when the
  // background is Cosmic Ocean. Null when either background isn't CO or the
  // extract is missing (backdrop still tiles without decos).
  const [cosmicDecoUrl, setCosmicDecoUrl] = useState<string | null>(null);
  // Bumped whenever the file is reloaded so the load effect re-runs. The
  // Restore action uses this to blow away in-memory edits and re-fetch.
  const [reloadTick, setReloadTick] = useState(0);
  // Level Config / Sequence / Resize live in floating modals so the sidebar
  // stays dedicated to the palette. Track which (if any) is open. The
  // `settings` and `help` values are editor-wide (top bar); everything
  // else is per-file or per-pack.
  const [openModal, setOpenModal] = useState<
    "config" | "sequence" | "resize" | "settings" | "help" | null
  >(null);

  const paletteChangedSinceSave = useRef(false);
  const shortCodesRef = useRef<string[] | null>(null);
  // Biome the current atlas was built for. Written by both the load
  // effect (initial build) and the retint effect (post-load theme
  // changes) so a redundant retint at the same biome is skipped.
  const atlasBiomeRef = useRef<string | null>(null);
  // File the current atlas was built for. On a file switch `currentBiome`
  // updates a render before `level`/`atlas` do, so the retint effect could
  // otherwise rebuild from the previous file's data and clobber the incoming
  // atlas; skipping while this doesn't match `selectedFile` avoids that.
  const atlasFileRef = useRef<string | null>(null);
  const [, setEditedTick] = useState(0);

  // Whole pack's level_configuration.ls, loaded once per pack open. Panel
  // edits mutate a per-file overlay (`configEdits`) so the user can
  // discard-on-restore without losing untouched entries. Save flushes the
  // overlay back into `config` and writes the merged file to disk.
  const [config, setConfig] = useState<LevelConfigurations | null>(null);
  const [configEdits, setConfigEdits] = useState<Map<string, LevelConfiguration>>(
    () => new Map(),
  );
  // Pending sequence order (file_names). Null means the user hasn't touched
  // the sequence, so save leaves the disk order intact. Non-null is the
  // full replacement order.
  const [pendingSequence, setPendingSequence] = useState<string[] | null>(
    null,
  );

  // Current file's LevelConfiguration entry. Preference: local edits >
  // config.sequence > config.all_configurations > synthesized default.
  // Null when no file is open. Hoisted above the atlas + bg effects
  // because they consume the derived biome below.
  const currentConfigEntry = useMemo<LevelConfiguration | null>(() => {
    if (!selectedFile) return null;
    const edited = configEdits.get(selectedFile);
    if (edited) return edited;
    const fromDisk = findConfigEntry(config, selectedFile);
    if (fromDisk) return fromDisk;
    // Files with no config entry get a synthesized default. Prefer the
    // theme id we recovered from the (0,0) template comment so an
    // authored theme survives even when the file was never added to
    // the sequence config.
    const fallback = defaultConfigEntry(selectedFile);
    if (level?.detectedTheme != null) {
      fallback.theme = level.detectedTheme;
    }
    return fallback;
  }, [selectedFile, config, configEdits, level]);

  // Layer override resolution mirrors Python's
  // `custom_level_editor.py:701`:
  //   bg_theme    = lvl_background_theme       ?? lvl_theme
  //   bg_subtheme = lvl_background_subtheme    ?? lvl_subtheme
  // where `lvl_background_subtheme` is what the config stores as
  // `background_texture_theme` (see the assignment at line 380 in
  // Python). Background_texture_theme is the SUBTHEME channel, not a
  // fallback in the same chain as background_theme.
  const backgroundThemeId =
    currentConfigEntry?.background_theme ?? currentConfigEntry?.theme;
  const backgroundSubthemeId =
    currentConfigEntry?.background_texture_theme ??
    currentConfigEntry?.subtheme;
  const floorThemeId =
    currentConfigEntry?.floor_theme ?? currentConfigEntry?.theme;

  // Biome the background PNG is looked up under. Cosmic Ocean recurses
  // on the subtheme so `background_texture_theme` (Python's
  // "background subtheme") selects the underlying biome art when the
  // main background layer is CO.
  const backgroundBiome = useMemo(
    () =>
      backgroundThemeId != null
        ? biomeForThemeId(backgroundThemeId, backgroundSubthemeId)
        : DEFAULT_BIOME,
    [backgroundThemeId, backgroundSubthemeId],
  );

  // Biome the floor-tinted sprite atlas is built for. Also feeds the
  // AddTile dialog's preview so authors see the same tint that will
  // ship at save time.
  const currentBiome = useMemo(
    () =>
      floorThemeId != null
        ? biomeForThemeId(floorThemeId, currentConfigEntry?.subtheme)
        : DEFAULT_BIOME,
    [floorThemeId, currentConfigEntry?.subtheme],
  );

  // Cosmic Ocean backdrop follows the *effective background* theme:
  // setting the base theme to Dwelling but the Background override to
  // Cosmic Ocean still shows the starfield, and vice versa. Matches
  // Python's `draw_background(bg_theme, bg_subtheme)` in
  // `level_canvas.py`.
  const isCosmicBackground = backgroundThemeId === COSMIC_OCEAN_THEME;

  // Refetch the biome background whenever the effective background
  // biome changes (theme edit, background-layer override, file
  // switch). Swallow errors so a missing PNG (Extract Assets not run
  // yet) leaves the previous URL in place instead of blanking the
  // canvas.
  useEffect(() => {
    let cancelled = false;
    getBiomeBackground(backgroundBiome)
      .then((url) => {
        if (!cancelled) setBgUrl(url);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [backgroundBiome]);

  /**
   * Wrapper around `setPendingSequence` that collapses a pending order
   * back to `null` when it ends up matching the on-disk sequence. Without
   * this, an add-then-remove (or any sequence of moves that cancels out)
   * leaves a non-null pendingSequence value equal to the original, which
   * would still flag the pack as dirty and re-write the same order to
   * disk on next save.
   */
  const updatePendingSequence = useCallback(
    (next: string[] | null) => {
      if (next === null) {
        setPendingSequence(null);
        return;
      }
      const disk = config?.sequence.map((e) => e.file_name) ?? [];
      if (
        next.length === disk.length &&
        next.every((f, i) => disk[i] === f)
      ) {
        setPendingSequence(null);
      } else {
        setPendingSequence(next);
      }
    },
    [config],
  );

  // Editor-wide save format inventory. `userFormats` is what
  // list_custom_save_formats returns (persisted across every pack in the
  // shared config.json); `defaultFormat` is the editor-wide preferred
  // format for new levels + detection hints. Both refresh on demand
  // whenever the Editor Settings modal mutates them.
  const [userFormats, setUserFormats] = useState<CustomLevelSaveFormat[]>([]);
  const [defaultFormat, setDefaultFormat] =
    useState<CustomLevelSaveFormat | null>(null);

  // Effective format detected for each open file, plus (when nothing
  // matched) the suggested pattern for the recovery flow. Keyed by file
  // name so it survives file switches.
  const [detectedFormats, setDetectedFormats] = useState<
    Map<string, CustomLevelSaveFormat>
  >(() => new Map());
  const [suggestedFormats, setSuggestedFormats] = useState<
    Map<string, string>
  >(() => new Map());
  // Per-file save format overrides. If the user picks a different format
  // in the Level modal to convert on next save, it lands here.
  const [formatOverrides, setFormatOverrides] = useState<
    Map<string, CustomLevelSaveFormat>
  >(() => new Map());
  // True while the New Save Format modal is open for the currently-open
  // file's recovery flow. Distinct from the settings-driven "add new
  // format" modal so users can cancel the recovery without stopping the
  // load process.
  const [recoveryOpen, setRecoveryOpen] = useState(false);

  // Open a recovery modal automatically the first time a file that
  // couldn't be recognised gets selected. Users can dismiss and re-open
  // via a subtle prompt in the Level modal; the flag flips off after
  // dismiss so we don't nag them on every mouse move.
  useEffect(() => {
    if (!selectedFile) return;
    if (detectedFormats.has(selectedFile)) return;
    if (!suggestedFormats.has(selectedFile)) return;
    setRecoveryOpen(true);
  }, [selectedFile, detectedFormats, suggestedFormats]);

  const refreshEditorFormats = useCallback(async () => {
    try {
      const [uf, df] = await Promise.all([
        listCustomSaveFormats(),
        getDefaultSaveFormat(),
      ]);
      setUserFormats(uf);
      setDefaultFormat(df);
    } catch (err) {
      toast.error(`Format list load failed: ${extractMessage(err)}`);
    }
  }, [toast]);

  useEffect(() => {
    void refreshEditorFormats();
  }, [refreshEditorFormats]);

  // Ordered list of formats handed to load for detection. Default first
  // (if any), then user-defined, then built-ins. De-dupes by name so a
  // default that IS a built-in doesn't appear twice.
  const knownFormatsForLoad = useMemo<CustomLevelSaveFormat[]>(() => {
    const seen = new Set<string>();
    const out: CustomLevelSaveFormat[] = [];
    const push = (f: CustomLevelSaveFormat) => {
      if (seen.has(f.name)) return;
      seen.add(f.name);
      out.push(f);
    };
    if (defaultFormat) push(defaultFormat);
    for (const f of userFormats) push(f);
    for (const f of BUILT_IN_SAVE_FORMATS) push(f);
    return out;
  }, [defaultFormat, userFormats]);

  // Shared canvas: grids, undo, tools, marquee, view + link, zoom,
  // primary/secondary, keyboard shortcuts. Custom levels ARE dual: every
  // room the game generates has a back layer even if the author never
  // touches it, so the editor exposes fg + bg + Link the same way Vanilla
  // does. Rooms save without the bg block when the back layer is untouched
  // (see save_custom_level_sync), so passing isDual=true has no cost for
  // single-layer packs.
  const canvas = useLevelCanvas({
    currentKey: selectedFile,
    isDual: true,
    palette,
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

  // Grid visibility and clamp now live in `prefs` (the hook's own grid state
  // is unused here). Initial-zoom policy for the canvas: fit-to-view, a fixed
  // percent, or "remember" (carry the current zoom across room/file switches).
  const zoomFit = prefs.zoomMode === "fit";
  const initialZoom =
    prefs.zoomMode === "fixed"
      ? prefs.fixedZoomPct / 100
      : prefs.zoomMode === "remember"
        ? (zoom ?? 1)
        : 1;

  const recomputeDirty = useCallback(() => {
    setDirty(
      editedKeysRef.current.size > 0 ||
        paletteChangedSinceSave.current ||
        configEdits.size > 0 ||
        pendingSequence !== null,
    );
  }, [editedKeysRef, configEdits, pendingSequence]);

  // Palette editor: owns swatch overrides, reorder mode, help modal
  // open state, pending delete, and the delete-flow callbacks that
  // walk the canvas grid refs. Both editors share this hook; the parent
  // keeps `palette + setPalette` (needed by useLevelCanvas) and
  // `paletteChangedSinceSave` (read by recomputeDirty above).
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
    currentKey: selectedFile,
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

  // Bundled Cosmic Ocean backdrop is app-shipped, so fetch it once at
  // mount and reuse across file switches. Theme check on the canvas
  // prop gates whether it renders.
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

  // CO subtheme decoration crop. Refetches when the effective subtheme
  // changes; unlike the bundled backdrop this comes from
  // Data/Textures/deco_cosmic.png in the user's extract, so it may be
  // absent (and we degrade to the plain starfield). Only fetched when
  // background is CO so we don't hit disk for non-CO files.
  useEffect(() => {
    if (!isCosmicBackground) {
      setCosmicDecoUrl(null);
      return;
    }
    const sub = backgroundSubthemeId ?? 1;
    let cancelled = false;
    getCosmicSubthemeDecoration(sub)
      .then((url) => {
        if (!cancelled) setCosmicDecoUrl(url);
      })
      .catch(() => {
        if (!cancelled) setCosmicDecoUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isCosmicBackground, backgroundSubthemeId]);

  useEffect(() => {
    let cancelled = false;
    listShortCodes()
      .then((codes) => {
        if (!cancelled) shortCodesRef.current = codes;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Load the pack's level_configuration.ls once. Reloads whenever
  // reloadTick bumps so the Restore action pulls a fresh copy alongside
  // the .lvl reload.
  useEffect(() => {
    let cancelled = false;
    loadCustomConfig(pack)
      .then((c) => {
        if (cancelled) return;
        setConfig(c);
        setConfigEdits(new Map());
        setPendingSequence(null);
      })
      .catch((err) => {
        if (!cancelled) toast.error(`Config load failed: ${extractMessage(err)}`);
      });
    return () => {
      cancelled = true;
    };
  }, [pack, reloadTick, toast]);

  const trySelectFile = useCallback(
    (f: string) => {
      if (f === selectedFile) return;
      // Only file-scoped work (canvas paints + palette additions) actually
      // gets discarded when the selection changes; config-panel edits are
      // keyed by filename and survive the switch, and pending sequence
      // reorders are pack-scoped. So don't gate navigation on those two,
      // just on the paint state we'd otherwise blow away in the load
      // effect below.
      const fileScopedDirty =
        editedKeysRef.current.size > 0 || paletteChangedSinceSave.current;
      if (fileScopedDirty) {
        setPendingFile(f);
        return;
      }
      setSelectedFile(f);
    },
    [selectedFile, editedKeysRef],
  );

  const confirmDiscardAndSwitch = () => {
    if (!pendingFile) return;
    // Only discard the file-scoped work the switch would lose (the load
    // effect wipes editedKeys / grids / palette-change flag on file
    // change). Pack-scoped edits (config panel, pending sequence) are
    // deliberately left intact so users don't lose sequence work by
    // navigating away from an unrelated dirty file.
    setSelectedFile(pendingFile);
    setPendingFile(null);
  };
  const cancelSwitch = () => setPendingFile(null);

  // Intercept the window's OS close button so unsaved work in ANY of the
  // pack-scoped dirty inputs (canvas, palette, config panel, pending
  // sequence) shows a discard/cancel prompt instead of silently
  // vanishing.
  const closeGuard = useCloseGuard(dirty);

  // Load the selected file. Also rebuilds the atlas for its palette.
  useEffect(() => {
    if (!selectedFile) {
      setLevel(null);
      setAtlas(null);
      setPalette([]);
      setPrimary(null);
      setSecondary(null);
      setDirty(false);
      pal.resetForFileLoad();
      gridsRef.current.clear();
      bgGridsRef.current.clear();
      editedKeysRef.current.clear();
      resetHistory();
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLevel(null);
    setAtlas(null);
    setDirty(false);
    pal.resetForFileLoad();
    gridsRef.current.clear();
    bgGridsRef.current.clear();
    editedKeysRef.current.clear();
    resetHistory();
    (async () => {
      try {
        const data = await loadCustomLevel(
          pack,
          selectedFile,
          knownFormatsForLoad,
        );
        if (cancelled) return;
        setLevel(data);
        setPalette(data.palette);
        // Remember detection so the Level modal can show the current
        // format and Save can send it through. suggestedFormats feeds
        // the recovery flow when detection failed.
        setDetectedFormats((prev) => {
          const out = new Map(prev);
          if (data.detectedFormat) {
            out.set(selectedFile, data.detectedFormat);
          } else {
            out.delete(selectedFile);
          }
          return out;
        });
        setSuggestedFormats((prev) => {
          const out = new Map(prev);
          if (data.suggestedFormat) {
            out.set(selectedFile, data.suggestedFormat);
          } else {
            out.delete(selectedFile);
          }
          return out;
        });
        // Seed both layer grids under the file-name key so the hook's
        // currentFgGrid / currentBgGrid memos have something to hand to the
        // canvas. Bump gridsVersion so those memos (cached on currentKey +
        // gridsVersion) invalidate; currentKey doesn't change between
        // file-pick and load-complete in Custom.
        gridsRef.current.set(
          selectedFile,
          data.foreground.map((row) => row.slice()),
        );
        bgGridsRef.current.set(
          selectedFile,
          data.background.map((row) => row.slice()),
        );
        bumpGridsVersion();
        const uniqNames = new Set<string>();
        for (const p of data.palette) uniqNames.add(p.name);
        for (const row of data.foreground) {
          for (const name of row) {
            if (name) uniqNames.add(name);
          }
        }
        for (const row of data.background) {
          for (const name of row) {
            if (name) uniqNames.add(name);
          }
        }
        if (uniqNames.size === 0) {
          setAtlas(null);
          atlasBiomeRef.current = null;
          atlasFileRef.current = selectedFile;
        } else {
          // Derive the atlas biome from the freshly-loaded data, NOT from
          // the enclosing render's `currentBiome`. The closure captured
          // `currentBiome` while `level` still held the PREVIOUS file's
          // detectedTheme, so using it here would tint file A's atlas
          // with file B's biome until the user switches files a second
          // time. Priority mirrors the currentConfigEntry chain:
          // user edits > sequence entry > all_configurations entry >
          // file's own detected_theme > Dwelling.
          const configEntry =
            configEdits.get(selectedFile) ??
            findConfigEntry(config, selectedFile) ??
            null;
          const atlasThemeId =
            configEntry?.floor_theme ??
            configEntry?.theme ??
            data.detectedTheme ??
            1;
          const atlasBiome = biomeForThemeId(
            atlasThemeId,
            configEntry?.subtheme,
          );
          const a = await buildTileNameAtlas(
            Array.from(uniqNames),
            atlasBiome,
          );
          if (cancelled) return;
          atlasBiomeRef.current = atlasBiome;
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
        if (!cancelled) {
          toast.error(`Load failed: ${extractMessage(err)}`);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // reloadTick is a bump-to-refetch signal; ESLint can't tell that.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pack, selectedFile, toast, resetHistory, reloadTick]);

  // Rebuild the atlas whenever the effective floor biome changes AFTER
  // a load has already settled -- e.g. the user picks a different
  // theme in the config panel. The load effect handles the initial
  // build inline so first-click-after-selection doesn't tint with the
  // previous file's biome; this one covers the post-load edits.
  //
  // Guarded on `level && atlas` so it doesn't fire during the load
  // window (the load effect owns the atlas until it settles) or on
  // empty-palette files that skipped atlas construction entirely.
  // The biome ref short-circuits a redundant rebuild when the load
  // effect already produced the atlas at the same biome.
  useEffect(() => {
    if (!selectedFile || !level || !atlas) return;
    // Skip while the atlas belongs to a different file (a load is in flight);
    // the load effect owns cross-file rebuilds.
    if (atlasFileRef.current !== selectedFile) return;
    if (atlasBiomeRef.current === currentBiome) return;
    let cancelled = false;
    (async () => {
      const uniqNames = new Set<string>();
      for (const p of palette) uniqNames.add(p.name);
      for (const row of level.foreground) {
        for (const name of row) if (name) uniqNames.add(name);
      }
      for (const row of level.background) {
        for (const name of row) if (name) uniqNames.add(name);
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
    // Palette membership is tracked by the load + edit effects; only
    // biome flips + explicit reloadTick bumps trigger a retint here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBiome]);

  const save = useCallback(async () => {
    if (saving) return;
    // Pending config / sequence edits can exist without any file open (the
    // Sequence modal is pack-scoped), so save runs whenever ANY of the
    // dirty inputs are live, not only when a file is loaded.
    const hasConfigWork = configEdits.size > 0 || pendingSequence !== null;
    const hasLevelWork = selectedFile !== null && gridsRef.current.has(selectedFile);
    if (!hasConfigWork && !hasLevelWork) return;
    setSaving(true);
    try {
      // .lvl save runs first when a file is open. If it fails we bail out
      // before touching level_configuration.ls so we don't half-commit.
      if (hasLevelWork && selectedFile) {
        const fg = gridsRef.current.get(selectedFile);
        // A file that was never dual on disk still has a bg map entry (all
        // empty strings) because the load effect seeds both grids in
        // lockstep. Falling back to an empty grid keeps a corrupted state
        // from crashing the save; the backend treats every cell as
        // untouched.
        const bg = bgGridsRef.current.get(selectedFile) ?? [];
        if (fg) {
          // Look up the effective theme so the backend can auto-emit
          // vanilla-format setroom mirrors on special (boss / CO adjacent)
          // themes. Preference: local edit > disk sequence > all_configurations.
          const themeForSave: number | null =
            configEdits.get(selectedFile)?.theme ??
            findConfigEntry(config, selectedFile)?.theme ??
            null;
          // Effective save format: user override wins (converts on next
          // save), else the detected format from load. Null tells Rust to
          // auto-detect on unrecognised files.
          const effectiveFormat: CustomLevelSaveFormat | null =
            formatOverrides.get(selectedFile) ??
            detectedFormats.get(selectedFile) ??
            null;
          await saveCustomLevel(
            pack,
            selectedFile,
            fg,
            bg,
            palette,
            themeForSave,
            effectiveFormat,
          );
        }
      }
      // Merge any config edits or a pending sequence into the pack's config
      // and write it out. Done AFTER the .lvl save so a level save that
      // fails doesn't roll back the config write, and vice versa.
      if (hasConfigWork && config) {
        const merged = mergeConfigEdits(config, configEdits, pendingSequence);
        await saveCustomConfig(pack, merged);
        setConfig(merged);
        setConfigEdits(new Map());
        setPendingSequence(null);
      }
      editedKeysRef.current.clear();
      setEditedTick((t) => t + 1);
      paletteChangedSinceSave.current = false;
      markSaved();
      setDirty(false);
      toast.success(
        selectedFile ? `Saved ${selectedFile}.` : "Saved sequence.",
      );
    } catch (err) {
      toast.error(`Save failed: ${extractMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }, [
    pack,
    selectedFile,
    palette,
    saving,
    toast,
    gridsRef,
    bgGridsRef,
    editedKeysRef,
    markSaved,
    config,
    configEdits,
    pendingSequence,
    detectedFormats,
    formatOverrides,
  ]);

  const confirmRestore = () => {
    setPendingRestore(false);
    setConfigEdits(new Map());
    setPendingSequence(null);
    setReloadTick((t) => t + 1);
  };
  const cancelRestore = () => setPendingRestore(false);

  useEffect(() => {
    // Custom-only shortcuts. Tool / undo / marquee shortcuts live in the
    // shared canvas hook so both editors handle them identically.
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }
      const isCtrl = e.ctrlKey || e.metaKey;
      if (isCtrl && e.code === "KeyS") {
        e.preventDefault();
        if (dirty) setPendingSave(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save]);

  // Reconcile dirty whenever the hook signals an edit-key change (via
  // editedTick) or the palette changes since save.
  useEffect(() => {
    recomputeDirty();
  }, [recomputeDirty, undoLen]);

  /**
   * Adds a tile from the modal. Extends the canvas's texture map + palette's
   * swatch map without rebuilding the shared atlas, so add-tile stays snappy
   * on large levels.
   */
  const handleAddTile = useCallback(
    async (name: string, preview: TileSprite) => {
      setAddOpen(false);
      if (!name) return;
      if (palette.some((p) => p.name === name)) {
        toast.error(`"${name}" is already in the palette.`);
        return;
      }
      const used = new Set(palette.map((p) => p.code));
      const pool = shortCodesRef.current;
      const code = pool?.find((c) => !used.has(c));
      if (!code) {
        toast.error("No free tile-code characters left in this level.");
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
    [palette, toast, canvasRef, setPrimary, recomputeDirty],
  );

  const tilesForCanvas = useMemo(() => {
    if (!selectedFile) return [] as string[][];
    return combinedGrid ?? gridsRef.current.get(selectedFile) ?? [];
    // combinedGrid is memoized off gridsVersion + currentKey inside the hook;
    // its identity change is what actually drives the canvas re-render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFile, combinedGrid]);

  const handleConfigChange = useCallback(
    (next: LevelConfiguration) => {
      if (!selectedFile) return;
      setConfigEdits((prev) => {
        const out = new Map(prev);
        out.set(selectedFile, next);
        return out;
      });
    },
    [selectedFile],
  );

  /**
   * Resize the open level per-side. Each side delta is in rooms; positive
   * grows that side with empty tiles, negative crops that side's tiles.
   * Padding a side effectively shifts every existing tile away from it by
   * that many rooms of tiles; cropping bites into the source from that
   * side. Undefined-out-of-source cells fall back to empty strings.
   */
  const handleResize = useCallback(
    (plan: ResizePlan) => {
      if (!selectedFile || !level) return;
      const padTopTiles = plan.padTopRooms * 8;
      const padBottomTiles = plan.padBottomRooms * 8;
      const padLeftTiles = plan.padLeftRooms * 10;
      const padRightTiles = plan.padRightRooms * 10;
      const targetW = level.widthTiles + padLeftTiles + padRightTiles;
      const targetH = level.heightTiles + padTopTiles + padBottomTiles;
      const applyToGrid = (
        grid: string[][] | undefined,
      ): string[][] | null => {
        if (!grid) return null;
        const out: string[][] = [];
        for (let r = 0; r < targetH; r++) {
          const srcRow = r - padTopTiles;
          const src = grid[srcRow];
          const row: string[] = new Array(targetW);
          for (let c = 0; c < targetW; c++) {
            const srcCol = c - padLeftTiles;
            row[c] = src?.[srcCol] ?? "";
          }
          out.push(row);
        }
        return out;
      };
      const newFg = applyToGrid(gridsRef.current.get(selectedFile));
      const newBg = applyToGrid(bgGridsRef.current.get(selectedFile));
      if (newFg) gridsRef.current.set(selectedFile, newFg);
      if (newBg) bgGridsRef.current.set(selectedFile, newBg);
      const newWidthRooms = level.widthRooms + plan.padLeftRooms + plan.padRightRooms;
      const newHeightRooms = level.heightRooms + plan.padTopRooms + plan.padBottomRooms;
      setLevel((prev) =>
        prev
          ? {
              ...prev,
              widthRooms: newWidthRooms,
              heightRooms: newHeightRooms,
              widthTiles: targetW,
              heightTiles: targetH,
              foreground: newFg ?? prev.foreground,
              background: newBg ?? prev.background,
            }
          : prev,
      );
      editedKeysRef.current.add(selectedFile);
      currentRoomTouchedRef.current = true;
      setEditedTick((t) => t + 1);
      bumpGridsVersion();
      recomputeDirty();
      setOpenModal(null);
      toast.success(`Resized to ${newWidthRooms}x${newHeightRooms} rooms.`);
    },
    [
      selectedFile,
      level,
      gridsRef,
      bgGridsRef,
      editedKeysRef,
      currentRoomTouchedRef,
      bumpGridsVersion,
      recomputeDirty,
      toast,
    ],
  );

  // Nudge recomputeDirty whenever any pack-scoped dirty input changes so
  // the top-bar Save button and dirty pip flip on/off in step with the
  // Sequence + Level panel edits. Level-canvas edits already reach dirty
  // via the hook's onEditedKeysChanged callback.
  useEffect(() => {
    recomputeDirty();
  }, [configEdits, pendingSequence, recomputeDirty]);

  return (
    <div className="editor-window">
      <EditorTopBar
        title={
          <>
            <span className="editor-window-pack">{pack}</span>
            <span className="editor-window-mode">
              {dirty && <span className="editor-window-dirty">•</span>}
              {editorModeLabel("custom")} Editor
              {selectedFile ? ` - ${selectedFile}` : ""}
              {level
                ? ` [${level.widthTiles}×${level.heightTiles}]`
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
        canSave={dirty}
        saving={saving}
        onRestore={() => setPendingRestore(true)}
        onSave={() => setPendingSave(true)}
        farRightExtras={
          <>
            <button
              type="button"
              className="editor-window-gear"
              onClick={() => setOpenModal("help")}
              title="Keyboard shortcuts"
              aria-label="Keyboard shortcuts"
            >
              <Keyboard size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="editor-window-gear"
              onClick={() => setOpenModal("settings")}
              title="Editor settings"
              aria-label="Editor settings"
            >
              <Settings size={16} aria-hidden="true" />
            </button>
          </>
        }
      />
      <div className="editor-window-body">
        <aside className="editor-window-sidebar editor-window-sidebar-left custom-left">
          <div className="custom-left-scroll">
            <LevelFileTree
              pack={pack}
              selected={selectedFile}
              onSelect={trySelectFile}
              userFormats={userFormats}
              defaultFormat={defaultFormat}
              packHasSequence={
                (pendingSequence ?? config?.sequence.map((e) => e.file_name) ?? [])
                  .length > 0
              }
              onCreated={(fileName, { theme, addToSequence, saveFormat }) => {
                // Seed the config edit map with a fresh entry that carries
                // the theme picked in the create dialog. Doing this via
                // configEdits (instead of writing to disk here) means the
                // new-level config lands on the next Save alongside any
                // other pending edits, so the user has one atomic commit.
                const entry: LevelConfiguration = {
                  ...defaultConfigEntry(fileName),
                  theme,
                };
                setConfigEdits((prev) => {
                  const out = new Map(prev);
                  out.set(fileName, entry);
                  return out;
                });
                if (addToSequence) {
                  setPendingSequence((prev) => {
                    const base =
                      prev ?? config?.sequence.map((e) => e.file_name) ?? [];
                    // Idempotent: skip if the file is already queued.
                    if (base.includes(fileName)) return base;
                    return [...base, fileName];
                  });
                }
                // Seed the file's detected format so the very first save
                // uses the same pattern the user picked in the create
                // dialog, without needing another load round-trip.
                setDetectedFormats((prev) => {
                  const out = new Map(prev);
                  out.set(fileName, saveFormat);
                  return out;
                });
              }}
              onDeleted={(file) => {
                // If the file the user just deleted was open in the editor,
                // clear the canvas + level state so we don't try to save
                // against a missing file. Drop it out of the hook's grid
                // maps too so a same-named recreate doesn't inherit stale
                // in-memory content.
                if (selectedFile === file) {
                  setSelectedFile(null);
                }
                gridsRef.current.delete(file);
                bgGridsRef.current.delete(file);
                editedKeysRef.current.delete(file);
              }}
              onRenamed={(oldName, newName) => {
                // Follow the hook's per-key grid maps to the new name so the
                // open canvas keeps its in-flight edits. Same for editedKeys
                // so the dirty pip doesn't spuriously flip off.
                const fg = gridsRef.current.get(oldName);
                const bg = bgGridsRef.current.get(oldName);
                if (fg) {
                  gridsRef.current.set(newName, fg);
                  gridsRef.current.delete(oldName);
                }
                if (bg) {
                  bgGridsRef.current.set(newName, bg);
                  bgGridsRef.current.delete(oldName);
                }
                if (editedKeysRef.current.delete(oldName)) {
                  editedKeysRef.current.add(newName);
                }
              }}
            />
          </div>
          <div className="custom-left-footer">
            <button
              type="button"
              className="custom-left-sequence-btn"
              onClick={() => setOpenModal("sequence")}
              title="Reorder the pack's playthrough"
            >
              <ListOrdered size={14} aria-hidden="true" />
              <span>Sequence</span>
              {pendingSequence !== null && (
                <span className="editor-bottombar-action-dirty">•</span>
              )}
            </button>
          </div>
        </aside>
        <main className="editor-window-canvas">
          {!selectedFile && (
            <div className="editor-window-status">
              Pick a .lvl file from the left to open it.
            </div>
          )}
          {selectedFile && loading && (
            <div className="editor-window-status">Loading {selectedFile}...</div>
          )}
          {selectedFile && !loading && level && atlas && combinedGrid && (
            <div className="editor-canvas-wrap">
              <div className="editor-canvas-surface">
                <TileCanvas
                  ref={canvasRef}
                  viewKey={`custom-${pack}-${selectedFile}-${atlas.tiles.length}-${effectiveLayerView}-v${canvas.gridsVersion}`}
                  atlas={atlas}
                  tiles={tilesForCanvas}
                  tileDisplaySize={TILE_DISPLAY_SIZE}
                  primary={primary}
                  secondary={secondary}
                  tool={tool}
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
                  eraseName={
                    palette.find((p) => p.name === "empty")?.name ?? ""
                  }
                  onPick={canvasOnPick}
                  mirrorCell={mirrorCell}
                  onSelectionChange={setSelection}
                  onMoveSelection={commitMarqueeMove}
                  extraSelectionRects={extraSelectionRects}
                  showTileGrid={prefs.showTileGrid}
                  showRoomGrid={prefs.showRoomGrid}
                  renderMode={renderMode}
                />
              </div>
              <EditorBottomBar
                zoom={zoom}
                roomOpen={false}
                roomSettingsEdited={false}
                roomSettings={[]}
                isDual
                linkLayers={linkLayers}
                layerView={effectiveLayerView}
                showTileGrid={prefs.showTileGrid}
                showRoomGrid={prefs.showRoomGrid}
                onSetZoom={(z) => canvasRef.current?.setZoom(z)}
                onZoomToFit={() => canvasRef.current?.zoomToFit()}
                onToggleSetting={() => {
                  /* Custom has no template flags; roomOpen=false hides
                     the settings section entirely. */
                }}
                onToggleLinkLayers={() => setLinkLayers((v) => !v)}
                onSetLayerView={setLayerView}
                onSetShowTileGrid={(v) => updatePrefs({ showTileGrid: v })}
                onSetShowRoomGrid={(v) => updatePrefs({ showRoomGrid: v })}
                renderMode={renderMode}
                onSetRenderMode={(m) =>
                  updatePrefs({ clampRender: m === "cell" })
                }
                trailingActions={
                  <>
                    <button
                      type="button"
                      className="editor-bottombar-action"
                      onClick={() => setOpenModal("resize")}
                      disabled={!selectedFile || !level}
                      title={
                        selectedFile
                          ? "Resize the level grid"
                          : "Open a level to resize it"
                      }
                    >
                      <Expand size={14} aria-hidden="true" />
                      <span>Resize</span>
                    </button>
                    <button
                      type="button"
                      className="editor-bottombar-action"
                      onClick={() => setOpenModal("config")}
                      disabled={!selectedFile}
                      title={
                        selectedFile
                          ? "Level configuration for the open file"
                          : "Open a level to edit its config"
                      }
                    >
                      <Settings2 size={14} aria-hidden="true" />
                      <span>Level</span>
                      {selectedFile && configEdits.has(selectedFile) && (
                        <span className="editor-bottombar-action-dirty">•</span>
                      )}
                    </button>
                  </>
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
            helpMode="custom"
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
          onClose={() => setAddOpen(false)}
          onSubmit={handleAddTile}
        />
      )}
      {openModal === "config" && selectedFile && currentConfigEntry && (
        <Modal
          open
          onClose={() => setOpenModal(null)}
          title={`Level configuration - ${selectedFile}`}
          size="md"
        >
          <LevelConfigPanel
            entry={currentConfigEntry}
            onChange={handleConfigChange}
            inSequence={
              (pendingSequence ??
                config?.sequence.map((e) => e.file_name) ??
                []).includes(selectedFile)
            }
            detectedFormat={detectedFormats.get(selectedFile) ?? null}
            overrideFormat={formatOverrides.get(selectedFile) ?? null}
            availableFormats={knownFormatsForLoad}
            onOverrideFormat={(next) => {
              setFormatOverrides((prev) => {
                const out = new Map(prev);
                if (next) {
                  out.set(selectedFile, next);
                } else {
                  out.delete(selectedFile);
                }
                return out;
              });
            }}
          />
        </Modal>
      )}
      {openModal === "resize" && selectedFile && level && (
        <ResizeLevelModal
          currentWidthRooms={level.widthRooms}
          currentHeightRooms={level.heightRooms}
          onClose={() => setOpenModal(null)}
          onApply={handleResize}
        />
      )}
      {openModal === "settings" && (
        <EditorSettingsModal
          context="custom"
          prefs={prefs}
          onChangePrefs={updatePrefs}
          userFormats={userFormats}
          defaultFormat={defaultFormat}
          onFormatsChanged={refreshEditorFormats}
          onClose={() => setOpenModal(null)}
        />
      )}
      {openModal === "help" && (
        <KeyboardShortcutsModal onClose={() => setOpenModal(null)} />
      )}
      {recoveryOpen && selectedFile && (
        <NewSaveFormatModal
          suggestedFormat={suggestedFormats.get(selectedFile) ?? null}
          existingNames={[
            ...BUILT_IN_SAVE_FORMATS.map((f) => f.name),
            ...userFormats.map((f) => f.name),
          ]}
          onClose={() => setRecoveryOpen(false)}
          onSubmit={async (fmt) => {
            try {
              await addCustomSaveFormat(fmt);
              await refreshEditorFormats();
              setRecoveryOpen(false);
              // Bump the reload tick so the load effect re-runs against
              // the freshly-expanded known_formats list and picks up the
              // pattern we just defined.
              setReloadTick((t) => t + 1);
              toast.success(`Added ${fmt.name}. Reloading...`);
            } catch (err) {
              toast.error(`Failed to add: ${extractMessage(err)}`);
            }
          }}
        />
      )}
      {openModal === "sequence" && (
        <Modal
          open
          onClose={() => setOpenModal(null)}
          title="Level sequence"
          size="lg"
        >
          <SequencePanel
            pack={pack}
            config={config}
            pendingSequence={pendingSequence}
            onChangePendingSequence={updatePendingSequence}
            currentFileName={selectedFile}
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
            You have unsaved edits in this pack. Close anyway? Your edits
            will be lost.
          </p>
        </Modal>
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
          onClose={cancelRestore}
          title="Discard changes?"
          size="sm"
          footer={
            <div className="editor-confirm-footer">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={cancelRestore}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={confirmRestore}
              >
                Discard and reload
              </button>
            </div>
          }
        >
          <p className="editor-confirm-body">
            Discard every unsaved edit in <code>{selectedFile}</code> and
            reload the file from disk?
          </p>
        </Modal>
      )}
    </div>
  );
}

/**
 * Look up a LevelConfiguration for a specific file. Sequence entries win
 * over all_configurations because a sequence entry is the playthrough
 * source-of-truth; a stray all_configurations entry with the same file is
 * treated as an out-of-band draft that the sequence version overrides.
 */
function findConfigEntry(
  config: LevelConfigurations | null,
  fileName: string,
): LevelConfiguration | null {
  if (!config) return null;
  const inSeq = config.sequence.find((e) => e.file_name === fileName);
  if (inSeq) return inSeq;
  const all = config.all_configurations ?? {};
  for (const e of Object.values(all)) {
    if (e.file_name === fileName) return e;
  }
  return null;
}

/**
 * Apply per-file edits and an optional new sequence back into the pack's
 * config. Order of operations:
 *
 *   1. Start with the disk sequence + all_configurations.
 *   2. Overlay per-file edits into whichever collection currently holds
 *      them (existing sequence entry, existing all_configurations entry,
 *      else a fresh all_configurations entry).
 *   3. If pendingSequence is non-null, rebuild sequence[] from it, pulling
 *      each entry from (in order of preference) the just-updated sequence,
 *      the all_configurations map, or a synthesized default. Entries in
 *      all_configurations that end up in the new sequence are removed from
 *      there so the same file isn't tracked twice.
 */
function mergeConfigEdits(
  config: LevelConfigurations,
  edits: Map<string, LevelConfiguration>,
  pendingSequence: string[] | null,
): LevelConfigurations {
  let sequence = config.sequence.slice();
  const allConfigurations = { ...(config.all_configurations ?? {}) };
  for (const [fileName, entry] of edits) {
    const seqIdx = sequence.findIndex((e) => e.file_name === fileName);
    if (seqIdx >= 0) {
      sequence[seqIdx] = entry;
      continue;
    }
    const allKey = Object.keys(allConfigurations).find(
      (k) => allConfigurations[k].file_name === fileName,
    );
    if (allKey) {
      allConfigurations[allKey] = entry;
    } else {
      allConfigurations[entry.identifier] = entry;
    }
  }
  if (pendingSequence !== null) {
    const nextSequence: LevelConfiguration[] = [];
    for (const fileName of pendingSequence) {
      const existing = sequence.find((e) => e.file_name === fileName);
      if (existing) {
        nextSequence.push(existing);
        continue;
      }
      const allKey = Object.keys(allConfigurations).find(
        (k) => allConfigurations[k].file_name === fileName,
      );
      if (allKey) {
        nextSequence.push(allConfigurations[allKey]);
        delete allConfigurations[allKey];
        continue;
      }
      // File is on disk but has no entry yet. Synthesize a sane default so
      // the sequence line item still has an identifier + theme; the user
      // can refine in the Level tab.
      nextSequence.push(
        edits.get(fileName) ?? {
          identifier: fileName.replace(/\.lvl$/i, "").replace(/[^A-Za-z0-9_]/g, "_").toLowerCase(),
          name: fileName.replace(/\.lvl$/i, ""),
          file_name: fileName,
          theme: 1,
        },
      );
    }
    // Any file that was in the disk sequence but got dropped from the
    // pending order goes to all_configurations so its per-entry settings
    // aren't lost.
    for (const dropped of sequence) {
      if (
        !pendingSequence.includes(dropped.file_name) &&
        !allConfigurations[dropped.identifier]
      ) {
        allConfigurations[dropped.identifier] = dropped;
      }
    }
    sequence = nextSequence;
  }
  return {
    sequence,
    all_configurations: allConfigurations,
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
