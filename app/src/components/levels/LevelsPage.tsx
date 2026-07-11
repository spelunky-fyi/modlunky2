// The Level Editor tab is a splash + launcher. Editing happens in a
// separate Tauri window opened via `open_level_editor_window`.
// See project_level_editor_plan memory for the wider IA.

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, FilePlus2, FolderOpen, Settings, X } from "lucide-react";
import {
  createLevelPack,
  editorModeLabel,
  extractedAssetsAvailable,
  getDefaultSaveFormat,
  listCustomSaveFormats,
  listRecentPacks,
  openLevelEditorWindow,
  pushRecentPack,
  removeRecentPack,
  type CustomLevelSaveFormat,
  type EditorMode,
} from "../../lib/commands";
import { useToast } from "../shared/Toast";
import { useEditorPrefs } from "./hooks/useEditorPrefs";
import { EditorSettingsModal } from "./EditorSettingsModal";
import { PackPickerModal } from "./PackPickerModal";
import { CreatePackModal } from "./CreatePackModal";
import splashImg from "../../assets/leveleditor.png";
import "./LevelsPage.css";

type ModalState =
  | { kind: "none" }
  | { kind: "pick"; mode: EditorMode }
  | { kind: "create" };

type ContextMenu = {
  mode: EditorMode;
  pack: string;
  x: number;
  y: number;
};

export function LevelsPage() {
  const toast = useToast();
  const [modal, setModal] = useState<ModalState>({ kind: "none" });
  const [recents, setRecents] = useState<Record<EditorMode, string[]>>({
    vanilla: [],
    custom: [],
  });
  const [menu, setMenu] = useState<ContextMenu | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Global editor preferences, editable from here as well as the editor
  // windows (all share the same persisted config).
  const { prefs, updatePrefs } = useEditorPrefs();

  // Save-format inventory for the settings modal. The splash shows the same
  // full settings as the Custom editor, so it manages formats too.
  const [userFormats, setUserFormats] = useState<CustomLevelSaveFormat[]>([]);
  const [defaultFormat, setDefaultFormat] =
    useState<CustomLevelSaveFormat | null>(null);
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
  // Both editor windows and the create-pack flow reach through
  // Mods/Extracted/Data/Textures for sprites. If that dir is empty
  // there's nothing to render, so short-circuit at the entry point:
  // dim the splash, show a banner, and neuter every action instead of
  // spawning an editor window that would just show its own gate.
  const [assetsReady, setAssetsReady] = useState<boolean | null>(null);
  const refreshAssetsReady = useCallback(() => {
    extractedAssetsAvailable()
      .then((ok) => setAssetsReady(ok))
      .catch(() => setAssetsReady(false));
  }, []);
  useEffect(() => {
    refreshAssetsReady();
  }, [refreshAssetsReady]);

  const refreshRecents = useCallback(async () => {
    try {
      const [vanilla, custom] = await Promise.all([
        listRecentPacks("vanilla"),
        listRecentPacks("custom"),
      ]);
      setRecents({ vanilla, custom });
    } catch (err) {
      toast.error(`Recents load failed: ${extractMessage(err)}`);
    }
  }, [toast]);

  useEffect(() => {
    void refreshRecents();
  }, [refreshRecents]);

  const disabled = assetsReady === false;
  const openPicker = (mode: EditorMode) => {
    if (disabled) return;
    setModal({ kind: "pick", mode });
  };
  const openCreate = () => {
    if (disabled) return;
    setModal({ kind: "create" });
  };
  const closeModal = () => setModal({ kind: "none" });

  const launch = async (pack: string, mode: EditorMode) => {
    if (disabled) return;
    try {
      await openLevelEditorWindow(pack, mode);
      // Record after the launch succeeds so a bad open doesn't crowd the
      // list with packs that don't work.
      await pushRecentPack(mode, pack);
      await refreshRecents();
      closeModal();
    } catch (err) {
      toast.error(`Couldn't open editor: ${extractMessage(err)}`);
    }
  };

  const handleCreate = async (name: string, mode: EditorMode) => {
    try {
      const sanitized = await createLevelPack(name, mode);
      toast.success(`Created pack "${sanitized}".`);
      await openLevelEditorWindow(sanitized, mode);
      await pushRecentPack(mode, sanitized);
      await refreshRecents();
      closeModal();
    } catch (err) {
      toast.error(`Couldn't create pack: ${extractMessage(err)}`);
    }
  };

  const handleRemoveRecent = async (mode: EditorMode, pack: string) => {
    try {
      await removeRecentPack(mode, pack);
      await refreshRecents();
    } catch (err) {
      toast.error(`Couldn't remove: ${extractMessage(err)}`);
    }
    setMenu(null);
  };

  return (
    <div
      className="levels-splash dark-scope"
      style={{ backgroundImage: `url(${splashImg})` }}
    >
      <div className="levels-splash-tint" />
      {disabled && (
        <ExtractRequiredBanner onRefresh={refreshAssetsReady} />
      )}
      <div
        className={`levels-splash-inner${disabled ? " disabled" : ""}`}
        aria-disabled={disabled || undefined}
      >
        <header className="levels-splash-header">
          <button
            type="button"
            className="levels-new-pack-btn"
            onClick={openCreate}
            disabled={disabled}
          >
            <FilePlus2 size={16} aria-hidden="true" />
            <span>New Pack</span>
          </button>
          {/* Settings stay reachable even without extracts: zoom/clamp/grid
              are global and don't need assets. */}
          <button
            type="button"
            className="levels-settings-btn"
            onClick={() => setSettingsOpen(true)}
            title="Editor settings"
            aria-label="Editor settings"
          >
            <Settings size={16} aria-hidden="true" />
            <span>Settings</span>
          </button>
        </header>
        <div className="levels-columns">
          <EditorColumn
            mode="vanilla"
            recents={recents.vanilla}
            disabled={disabled}
            onOpen={() => openPicker("vanilla")}
            onLaunchRecent={(pack) => void launch(pack, "vanilla")}
            onContext={(pack, x, y) => {
              if (disabled) return;
              setMenu({ mode: "vanilla", pack, x, y });
            }}
          />
          <EditorColumn
            mode="custom"
            recents={recents.custom}
            disabled={disabled}
            onOpen={() => openPicker("custom")}
            onLaunchRecent={(pack) => void launch(pack, "custom")}
            onContext={(pack, x, y) => {
              if (disabled) return;
              setMenu({ mode: "custom", pack, x, y });
            }}
          />
        </div>
      </div>
      {modal.kind === "pick" && (
        <PackPickerModal
          mode={modal.mode}
          onPick={(pack) => void launch(pack, modal.mode)}
          onClose={closeModal}
        />
      )}
      {modal.kind === "create" && (
        <CreatePackModal
          onSubmit={(name, mode) => void handleCreate(name, mode)}
          onClose={closeModal}
        />
      )}
      {menu && (
        <RecentContextMenu
          menu={menu}
          onClose={() => setMenu(null)}
          onRemove={() => void handleRemoveRecent(menu.mode, menu.pack)}
        />
      )}
      {settingsOpen && (
        <EditorSettingsModal
          context="main"
          prefs={prefs}
          onChangePrefs={updatePrefs}
          userFormats={userFormats}
          defaultFormat={defaultFormat}
          onFormatsChanged={refreshEditorFormats}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </div>
  );
}

// --- Extract-required banner ------------------------------------------------

/** Sticky banner across the top of the splash. Rendered only when the
 *  install's Mods/Extracted directory is empty. The recheck button lets
 *  users kick the presence check after running Extract without needing
 *  to leave the tab. */
function ExtractRequiredBanner({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="levels-extract-banner" role="alert">
      <AlertTriangle size={16} aria-hidden="true" />
      <div className="levels-extract-banner-copy">
        <div className="levels-extract-banner-title">
          Run Extract Assets first
        </div>
        <div className="levels-extract-banner-body">
          The level editor renders tiles from{" "}
          <code>Mods/Extracted/Data/Textures/</code> and that folder is
          empty. Head to the Extract Assets tab, click Extract, then come
          back.
        </div>
      </div>
      <button
        type="button"
        className="levels-extract-banner-btn"
        onClick={onRefresh}
      >
        Check again
      </button>
    </div>
  );
}

// --- Column -----------------------------------------------------------------

interface ColumnProps {
  mode: EditorMode;
  recents: string[];
  disabled: boolean;
  onOpen: () => void;
  onLaunchRecent: (pack: string) => void;
  onContext: (pack: string, x: number, y: number) => void;
}

function EditorColumn({
  mode,
  recents,
  disabled,
  onOpen,
  onLaunchRecent,
  onContext,
}: ColumnProps) {
  const description =
    mode === "vanilla"
      ? "Modify the base game's .lvl files inside a pack."
      : "Make non-procedural levels with LevelSequence.";

  return (
    <section className="levels-column">
      <header className="levels-column-header">
        <h2 className="levels-column-title">{editorModeLabel(mode)}</h2>
        <p className="levels-column-desc">{description}</p>
      </header>
      <button
        type="button"
        className="levels-column-open-btn"
        onClick={onOpen}
        disabled={disabled}
      >
        <FolderOpen size={16} aria-hidden="true" />
        <span>Open pack...</span>
      </button>
      <div className="levels-column-recents">
        <div className="levels-column-recents-title">Recent</div>
        {recents.length === 0 ? (
          <div className="levels-column-recents-empty">
            No recently opened packs yet.
          </div>
        ) : (
          <ul className="levels-column-recents-list">
            {recents.map((pack) => (
              <li key={pack}>
                <button
                  type="button"
                  className="levels-recent-item"
                  onClick={() => onLaunchRecent(pack)}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    onContext(pack, e.clientX, e.clientY);
                  }}
                  title={`Open ${pack}`}
                  disabled={disabled}
                >
                  {pack}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

// --- Right-click menu -------------------------------------------------------

function RecentContextMenu({
  menu,
  onClose,
  onRemove,
}: {
  menu: ContextMenu;
  onClose: () => void;
  onRemove: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div className="levels-recent-menu-backdrop" onClick={onClose} />
      <div
        className="levels-recent-menu"
        style={{ left: menu.x, top: menu.y }}
        role="menu"
      >
        <button
          type="button"
          className="levels-recent-menu-item"
          onClick={onRemove}
        >
          <X size={14} aria-hidden="true" />
          <span>Remove from recents</span>
        </button>
      </div>
    </>
  );
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
