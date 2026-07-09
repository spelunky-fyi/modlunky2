// Editor-wide settings. Everything here persists across every pack the user
// opens, in the shared modlunky config.json. Kept clearly distinct from
// pack-scoped (Sequence) and level-scoped (Level, Resize) modals so the
// information hierarchy stays obvious.
//
// The same modal opens from three places, differentiated by `context`:
//   - "main"    (Level Editor tab): shows everything.
//   - "custom"  (Custom editor window): shows everything.
//   - "vanilla" (Vanilla editor window): hides Save formats, which only apply
//     to custom levels.
// The Canvas section (zoom / clamp / grid) is global and shown everywhere.

import { useMemo, useState } from "react";
import { CircleCheck, Plus, Trash2 } from "lucide-react";
import {
  BUILT_IN_SAVE_FORMATS,
  MAX_ZOOM_PCT,
  MIN_ZOOM_PCT,
  addCustomSaveFormat,
  isBuiltInSaveFormat,
  removeCustomSaveFormat,
  setDefaultSaveFormat,
  type CustomLevelSaveFormat,
  type EditorPrefs,
  type ZoomMode,
} from "../../lib/commands";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import { NewSaveFormatModal } from "./NewSaveFormatModal";
import "./EditorSettingsModal.css";

export type SettingsContext = "main" | "custom" | "vanilla";

interface Props {
  onClose: () => void;
  /** Which surface opened the modal; controls whether Save formats show. */
  context: SettingsContext;
  /** Global editor preferences and a persist-on-change updater. */
  prefs: EditorPrefs;
  onChangePrefs: (patch: Partial<EditorPrefs>) => void;
  /** Save-format management. Required when `context` shows the section
   *  ("main" | "custom"); omitted for "vanilla". */
  userFormats?: CustomLevelSaveFormat[];
  defaultFormat?: CustomLevelSaveFormat | null;
  onFormatsChanged?: () => void | Promise<void>;
}

// Order matters: "Fixed" is last so its inline controls extend the row to the
// right without reflowing anything below.
const ZOOM_MODES: { id: ZoomMode; label: string; help: string }[] = [
  {
    id: "fit",
    label: "Fit",
    help: "Fit the whole room in view each time you open one.",
  },
  {
    id: "remember",
    label: "Last used",
    help: "Open at 100% the first time, then keep your zoom as you move between rooms and files.",
  },
  {
    id: "fixed",
    label: "Fixed",
    help: "Always open at a set zoom level.",
  },
];

const ZOOM_PRESETS = [50, 100, 200];

function clampPct(n: number): number {
  if (!Number.isFinite(n)) return 100;
  return Math.max(MIN_ZOOM_PCT, Math.min(MAX_ZOOM_PCT, Math.round(n)));
}

export function EditorSettingsModal({
  onClose,
  context,
  prefs,
  onChangePrefs,
  userFormats = [],
  defaultFormat = null,
  onFormatsChanged,
}: Props) {
  const toast = useToast();
  const [newFormatOpen, setNewFormatOpen] = useState(false);

  const showSaveFormats = context !== "vanilla";

  const allFormats = useMemo(
    () => [...BUILT_IN_SAVE_FORMATS, ...userFormats],
    [userFormats],
  );
  const takenNames = useMemo(() => allFormats.map((f) => f.name), [allFormats]);
  const effectiveDefault: CustomLevelSaveFormat =
    defaultFormat ?? BUILT_IN_SAVE_FORMATS[0];

  const handlePickDefault = async (fmt: CustomLevelSaveFormat) => {
    try {
      await setDefaultSaveFormat(fmt);
      await onFormatsChanged?.();
    } catch (err) {
      toast.error(`Failed to set default: ${extractMessage(err)}`);
    }
  };

  const handleDelete = async (fmt: CustomLevelSaveFormat) => {
    try {
      await removeCustomSaveFormat(fmt.name);
      // If we just removed the default, clear it so the editor falls back to
      // its LevelSequence built-in default until the user picks another.
      if (defaultFormat?.name === fmt.name) {
        await setDefaultSaveFormat(null);
      }
      await onFormatsChanged?.();
    } catch (err) {
      toast.error(`Failed to delete: ${extractMessage(err)}`);
    }
  };

  const handleCreated = async (fmt: CustomLevelSaveFormat) => {
    try {
      await addCustomSaveFormat(fmt);
      setNewFormatOpen(false);
      await onFormatsChanged?.();
    } catch (err) {
      toast.error(`Failed to add: ${extractMessage(err)}`);
    }
  };

  return (
    <>
      <Modal open onClose={onClose} title="Editor settings" size="md">
        <div className="editor-settings">
          <p className="editor-settings-hint">
            Editor-wide preferences, shared across every pack and saved
            between sessions.
          </p>

          <section className="editor-settings-section">
            <header className="editor-settings-section-head">
              <div>
                <div className="editor-settings-section-titlerow">
                  <span className="editor-settings-section-title">Canvas</span>
                  <span className="editor-settings-scope">All editors</span>
                </div>
                <div className="editor-settings-section-sub">
                  Zoom, clamp, and grid defaults.
                </div>
              </div>
            </header>

            <div className="editor-settings-field">
              <span className="editor-settings-label">Default zoom</span>
              <div className="editor-settings-zoom-row">
                <div
                  className="editor-settings-segmented"
                  role="radiogroup"
                  aria-label="Default zoom"
                >
                  {ZOOM_MODES.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      role="radio"
                      aria-checked={prefs.zoomMode === m.id}
                      className={`editor-settings-seg${prefs.zoomMode === m.id ? " active" : ""}`}
                      onClick={() => onChangePrefs({ zoomMode: m.id })}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                {prefs.zoomMode === "fixed" && (
                  <div className="editor-settings-fixed-zoom">
                    <input
                      type="number"
                      min={MIN_ZOOM_PCT}
                      max={MAX_ZOOM_PCT}
                      value={prefs.fixedZoomPct}
                      onChange={(e) =>
                        onChangePrefs({
                          fixedZoomPct: clampPct(Number(e.target.value)),
                        })
                      }
                      aria-label="Fixed zoom percent"
                    />
                    <span className="editor-settings-pct">%</span>
                    {ZOOM_PRESETS.map((p) => (
                      <button
                        key={p}
                        type="button"
                        className={`editor-settings-preset${prefs.fixedZoomPct === p ? " active" : ""}`}
                        onClick={() => onChangePrefs({ fixedZoomPct: p })}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <p className="editor-settings-help">
                {ZOOM_MODES.find((m) => m.id === prefs.zoomMode)?.help}
              </p>
            </div>

            <label className="editor-settings-check">
              <input
                type="checkbox"
                checked={prefs.clampRender}
                onChange={(e) => onChangePrefs({ clampRender: e.target.checked })}
              />
              <span>Clamp sprites to their placement cell</span>
            </label>
            <label className="editor-settings-check">
              <input
                type="checkbox"
                checked={prefs.showTileGrid}
                onChange={(e) => onChangePrefs({ showTileGrid: e.target.checked })}
              />
              <span>Show tile grid</span>
            </label>
            <label className="editor-settings-check">
              <input
                type="checkbox"
                checked={prefs.showRoomGrid}
                onChange={(e) => onChangePrefs({ showRoomGrid: e.target.checked })}
              />
              <span>Show room grid</span>
            </label>
          </section>

          {showSaveFormats && (
            <section className="editor-settings-section">
              <header className="editor-settings-section-head">
                <div>
                  <div className="editor-settings-section-titlerow">
                    <span className="editor-settings-section-title">
                      Save formats
                    </span>
                    <span className="editor-settings-scope custom">
                      Custom editor only
                    </span>
                  </div>
                  <div className="editor-settings-section-sub">
                    How setroom templates are named on disk. Click a row to
                    set the default for new levels.
                  </div>
                </div>
                <button
                  type="button"
                  className="editor-settings-add-btn"
                  onClick={() => setNewFormatOpen(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  <span>New format</span>
                </button>
              </header>
              <ul className="save-format-list">
                {allFormats.map((f) => {
                  const isBuiltIn = isBuiltInSaveFormat(f);
                  const isDefault = effectiveDefault.name === f.name;
                  return (
                    <li
                      key={f.name}
                      className={`save-format-row${isDefault ? " default" : ""}`}
                    >
                      <button
                        type="button"
                        className="save-format-row-body"
                        onClick={() => {
                          if (!isDefault) void handlePickDefault(f);
                        }}
                        title={
                          isDefault
                            ? "Editor default"
                            : "Click to set as editor default"
                        }
                      >
                        <span className="save-format-row-checkicon">
                          {isDefault && (
                            <CircleCheck size={16} aria-hidden="true" />
                          )}
                        </span>
                        <div className="save-format-row-meta">
                          <span className="save-format-row-name">{f.name}</span>
                          <span className="save-format-row-tags">
                            <code>{f.room_template_format}</code>
                            {isBuiltIn && (
                              <span className="save-format-tag builtin">
                                Built-in
                              </span>
                            )}
                            {!isBuiltIn && (
                              <span className="save-format-tag custom">
                                Custom
                              </span>
                            )}
                            {f.include_vanilla_setrooms && (
                              <span className="save-format-tag mirrors">
                                Emits mirrors
                              </span>
                            )}
                          </span>
                        </div>
                      </button>
                      {!isBuiltIn && (
                        <button
                          type="button"
                          className="save-format-row-delete"
                          onClick={() => void handleDelete(f)}
                          title="Delete this format"
                          aria-label={`Delete ${f.name}`}
                        >
                          <Trash2 size={14} aria-hidden="true" />
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </div>
      </Modal>
      {newFormatOpen && (
        <NewSaveFormatModal
          existingNames={takenNames}
          onClose={() => setNewFormatOpen(false)}
          onSubmit={handleCreated}
        />
      )}
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
