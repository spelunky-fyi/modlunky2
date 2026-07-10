// Custom-editor file browser: lists .lvl files in the pack, opens a right-
// click menu with rename + delete, and offers a "+ New level" affordance
// that pops a small modal for name/width/height. All disk-touching ops go
// through the backend commands so backups + validation stay authoritative
// in Rust.

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";
import { Plus } from "lucide-react";
import {
  BUILT_IN_SAVE_FORMATS,
  LEVEL_SEQUENCE_FORMAT,
  createCustomLevel,
  deleteCustomLevel,
  listCustomLevels,
  openLevelFile,
  openLevelFileWith,
  renameCustomLevel,
  type CustomLevelSaveFormat,
} from "../../lib/commands";
import { useFloatingMenu } from "../../hooks/useFloatingMenu";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import { THEMES } from "./LevelConfigPanel";
import "./LevelFileTree.css";

export interface CreateLevelExtras {
  /** Theme integer chosen in the create dialog. Maps to LevelConfiguration
   *  entries the parent will drop into level_configuration.ls. */
  theme: number;
  /** True when the user asked for this level to land in the pack's
   *  playthrough sequence, false when it should just live in
   *  all_configurations. */
  addToSequence: boolean;
  /** Save format the file was created under. Parent stashes this in its
   *  detected-formats map so subsequent saves use the same pattern
   *  without another round-trip through load. */
  saveFormat: CustomLevelSaveFormat;
}

interface Props {
  pack: string;
  selected: string | null;
  onSelect: (fileName: string) => void;
  /** Fires after a delete lands so the parent can drop editor state tied to
   *  the removed file (unsaved edits go with it). */
  onDeleted?: (fileName: string) => void;
  /** Fires after a rename lands so the parent can point its selectedFile at
   *  the new name if the removed one was open. */
  onRenamed?: (oldName: string, newName: string) => void;
  /** Fires after createCustomLevel lands so the parent can seed a config
   *  entry (with the chosen theme) and optionally queue the new file into
   *  the pending sequence. */
  onCreated?: (fileName: string, extras: CreateLevelExtras) => void;
  /** Whether the pack already has a non-empty sequence. Drives the default
   *  state of the "Add to sequence" checkbox: on when a sequence exists,
   *  off when the pack has no playthrough yet. */
  packHasSequence?: boolean;
  /** User-defined save formats to union with the built-ins in the New
   *  Level modal's format picker. Parent owns the fetch so a single
   *  refresh updates every consumer. */
  userFormats?: CustomLevelSaveFormat[];
  /** Editor-wide default format. Preselects the New Level picker so the
   *  usual case ("keep using what I use") is one click. */
  defaultFormat?: CustomLevelSaveFormat | null;
}

type MenuState = {
  file: string;
  x: number;
  y: number;
};

type PendingOp =
  | { kind: "create" }
  | { kind: "rename"; file: string; initialValue: string }
  | { kind: "delete"; file: string };

export function LevelFileTree({
  pack,
  selected,
  onSelect,
  onDeleted,
  onRenamed,
  onCreated,
  packHasSequence = false,
  userFormats = [],
  defaultFormat = null,
}: Props) {
  const toast = useToast();
  const [files, setFiles] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [menu, setMenu] = useState<MenuState | null>(null);
  const [op, setOp] = useState<PendingOp | null>(null);

  const refresh = useCallback(() => {
    setError(null);
    listCustomLevels(pack)
      .then(setFiles)
      .catch((err) => setError(extractMessage(err)));
  }, [pack]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (error) {
    return <div className="level-tree-error">{error}</div>;
  }

  return (
    <div className="level-tree-wrap">
      <div className="level-tree-header">
        <span className="level-tree-title">Levels</span>
        <button
          type="button"
          className="level-tree-new"
          onClick={() => setOp({ kind: "create" })}
          title="Create a new blank .lvl in this pack"
        >
          <Plus size={12} aria-hidden="true" />
          <span>New</span>
        </button>
      </div>
      {files === null ? (
        <div className="level-tree-status">Loading levels...</div>
      ) : files.length === 0 ? (
        <div className="level-tree-status">
          No .lvl files yet. Click <strong>+ New</strong> above to create one.
        </div>
      ) : (
        <ul className="level-tree">
          {files.map((f) => (
            <li key={f}>
              <button
                type="button"
                className={`level-tree-item${selected === f ? " selected" : ""}`}
                onClick={() => onSelect(f)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  setMenu({ file: f, x: e.clientX, y: e.clientY });
                }}
              >
                {f}
              </button>
            </li>
          ))}
        </ul>
      )}
      {menu && (
        <TreeContextMenu
          menu={menu}
          onClose={() => setMenu(null)}
          onOpen={() => {
            const file = menu.file;
            setMenu(null);
            void openLevelFile(pack, file).catch((err) =>
              toast.error(`Couldn't open: ${extractMessage(err)}`),
            );
          }}
          onOpenWith={() => {
            const file = menu.file;
            setMenu(null);
            void openLevelFileWith(pack, file).catch((err) =>
              toast.error(`Couldn't open: ${extractMessage(err)}`),
            );
          }}
          onRename={() => {
            setOp({
              kind: "rename",
              file: menu.file,
              initialValue: menu.file,
            });
            setMenu(null);
          }}
          onDelete={() => {
            setOp({ kind: "delete", file: menu.file });
            setMenu(null);
          }}
        />
      )}
      {op?.kind === "create" && (
        <CreateLevelModal
          packHasSequence={packHasSequence}
          userFormats={userFormats}
          defaultFormat={defaultFormat}
          onClose={() => setOp(null)}
          onSubmit={async ({
            fileName,
            widthRooms,
            heightRooms,
            theme,
            addToSequence,
            saveFormat,
          }) => {
            try {
              const created = await createCustomLevel(
                pack,
                fileName,
                widthRooms,
                heightRooms,
                saveFormat.room_template_format,
              );
              toast.success(`Created ${created}.`);
              refresh();
              // Fire onCreated BEFORE onSelect so the parent seeds the
              // config entry with the chosen theme before the load kicks
              // in; otherwise the freshly-open Level panel would flash
              // the default Dwelling theme for a beat.
              onCreated?.(created, { theme, addToSequence, saveFormat });
              onSelect(created);
              setOp(null);
            } catch (err) {
              toast.error(`Create failed: ${extractMessage(err)}`);
            }
          }}
        />
      )}
      {op?.kind === "rename" && (
        <RenameLevelModal
          initialValue={op.initialValue}
          onClose={() => setOp(null)}
          onSubmit={async (newName) => {
            try {
              const landed = await renameCustomLevel(
                pack,
                op.file,
                newName,
              );
              toast.success(`Renamed to ${landed}.`);
              refresh();
              onRenamed?.(op.file, landed);
              if (selected === op.file) onSelect(landed);
              setOp(null);
            } catch (err) {
              toast.error(`Rename failed: ${extractMessage(err)}`);
            }
          }}
        />
      )}
      {op?.kind === "delete" && (
        <ConfirmDeleteModal
          fileName={op.file}
          onClose={() => setOp(null)}
          onConfirm={async () => {
            try {
              await deleteCustomLevel(pack, op.file);
              toast.success(`Deleted ${op.file}.`);
              refresh();
              onDeleted?.(op.file);
              setOp(null);
            } catch (err) {
              toast.error(`Delete failed: ${extractMessage(err)}`);
            }
          }}
        />
      )}
    </div>
  );
}

// --- Right-click menu ------------------------------------------------------

function TreeContextMenu({
  menu,
  onClose,
  onOpen,
  onOpenWith,
  onRename,
  onDelete,
}: {
  menu: MenuState;
  onClose: () => void;
  onOpen: () => void;
  onOpenWith: () => void;
  onRename: () => void;
  onDelete: () => void;
}) {
  const { menuRef, pos } = useFloatingMenu(menu.x, menu.y, onClose);
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
          title="Open this file with the default program"
        >
          Open
        </button>
        <button
          type="button"
          className="tree-menu-item"
          onClick={onOpenWith}
          title="Pick a program to open this file with"
        >
          Open with...
        </button>
        <div className="tree-menu-sep" />
        <button
          type="button"
          className="tree-menu-item"
          onClick={onRename}
        >
          Rename...
        </button>
        <div className="tree-menu-sep" />
        <button
          type="button"
          className="tree-menu-item danger"
          onClick={onDelete}
        >
          Delete
        </button>
      </div>
    </>
  );
}

// --- Modals ----------------------------------------------------------------

const MIN_ROOMS = 1;
const MAX_ROOMS_W = 18;
const MAX_ROOMS_H = 15;
const DEFAULT_ROOMS = 4;

function CreateLevelModal({
  packHasSequence,
  userFormats,
  defaultFormat,
  onClose,
  onSubmit,
}: {
  packHasSequence: boolean;
  userFormats: CustomLevelSaveFormat[];
  defaultFormat: CustomLevelSaveFormat | null;
  onClose: () => void;
  onSubmit: (v: {
    fileName: string;
    widthRooms: number;
    heightRooms: number;
    theme: number;
    addToSequence: boolean;
    saveFormat: CustomLevelSaveFormat;
  }) => void | Promise<void>;
}) {
  const [name, setName] = useState("");
  const [width, setWidth] = useState(DEFAULT_ROOMS);
  const [height, setHeight] = useState(DEFAULT_ROOMS);
  const [theme, setTheme] = useState<number>(1);
  // Default to on when the pack already has a playthrough (adding to an
  // existing sequence is the common flow); default to off when the pack
  // has no sequence yet, so a first-time-add doesn't accidentally seed
  // it before the author is ready.
  const [addToSequence, setAddToSequence] = useState<boolean>(packHasSequence);
  // Save format defaults to the editor-wide default (from Editor Settings)
  // when set, else the LevelSequence built-in.
  const [saveFormat, setSaveFormat] = useState<CustomLevelSaveFormat>(
    defaultFormat ?? LEVEL_SEQUENCE_FORMAT,
  );
  const allFormats = useMemo(
    () => [...BUILT_IN_SAVE_FORMATS, ...userFormats],
    [userFormats],
  );
  const nameRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    nameRef.current?.focus();
  }, []);
  const trimmed = name.trim();
  const invalid =
    !trimmed ||
    /[\\/]/.test(trimmed) ||
    trimmed.startsWith(".") ||
    (/\./.test(trimmed) && !trimmed.toLowerCase().endsWith(".lvl"));
  const validationError = useMemo(() => {
    if (!name) return null;
    if (!trimmed) return "Enter a file name.";
    if (/[\\/]/.test(trimmed)) return "Slashes aren't allowed in the name.";
    if (trimmed.startsWith(".")) return "Name can't start with a dot.";
    if (/\./.test(trimmed) && !trimmed.toLowerCase().endsWith(".lvl")) {
      return "File must end in .lvl (or have no extension).";
    }
    return null;
  }, [name, trimmed]);
  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (invalid) return;
    void onSubmit({
      fileName: trimmed,
      widthRooms: width,
      heightRooms: height,
      theme,
      addToSequence,
      saveFormat,
    });
  };
  return (
    <Modal open onClose={onClose} title="New level" size="sm">
      <form className="level-tree-form" onSubmit={handleSubmit}>
        <label className="tree-modal-label" htmlFor="new-level-name">
          Name
        </label>
        <input
          id="new-level-name"
          ref={nameRef}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. mylevel.lvl"
          spellCheck={false}
        />
        <div className="level-tree-form-row">
          <div className="level-tree-form-col">
            <label className="tree-modal-label" htmlFor="new-level-width">
              Width (rooms)
            </label>
            <input
              id="new-level-width"
              type="number"
              min={MIN_ROOMS}
              max={MAX_ROOMS_W}
              value={width}
              onChange={(e) =>
                setWidth(
                  Math.max(
                    MIN_ROOMS,
                    Math.min(MAX_ROOMS_W, Number(e.target.value) || 1),
                  ),
                )
              }
            />
          </div>
          <div className="level-tree-form-col">
            <label className="tree-modal-label" htmlFor="new-level-height">
              Height (rooms)
            </label>
            <input
              id="new-level-height"
              type="number"
              min={MIN_ROOMS}
              max={MAX_ROOMS_H}
              value={height}
              onChange={(e) =>
                setHeight(
                  Math.max(
                    MIN_ROOMS,
                    Math.min(MAX_ROOMS_H, Number(e.target.value) || 1),
                  ),
                )
              }
            />
          </div>
        </div>
        <label className="tree-modal-label" htmlFor="new-level-theme">
          Theme
        </label>
        <select
          id="new-level-theme"
          value={String(theme)}
          onChange={(e) => setTheme(Number(e.target.value))}
        >
          {THEMES.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
        <label className="tree-modal-label" htmlFor="new-level-format">
          Save format
        </label>
        <select
          id="new-level-format"
          value={saveFormat.name}
          onChange={(e) => {
            const next =
              allFormats.find((f) => f.name === e.target.value) ??
              LEVEL_SEQUENCE_FORMAT;
            setSaveFormat(next);
          }}
        >
          {allFormats.map((f) => (
            <option key={f.name} value={f.name}>
              {f.name}
            </option>
          ))}
        </select>
        {!saveFormat.include_vanilla_setrooms && (
          <div className="level-tree-form-hint level-tree-form-hint-warn">
            Boss themes (Ice Caves, Olmec, Tiamat...) will show default rooms
            instead of yours with this format. Only pick it if you're
            replacing a vanilla .lvl file directly.
          </div>
        )}
        <label className="level-tree-form-checkbox">
          <input
            type="checkbox"
            checked={addToSequence}
            onChange={(e) => setAddToSequence(e.target.checked)}
          />
          <span>
            Add to playthrough sequence
            <span className="level-tree-form-hint-inline">
              {addToSequence
                ? "This level will land at the end of the pack's play order."
                : "This level will be defined but not queued for playthrough."}
            </span>
          </span>
        </label>
        <p className="level-tree-form-hint">
          Rooms are 10x8 tiles. New levels start with hard-floor backgrounds
          and empty foregrounds. Config lands on next Save.
        </p>
        {validationError && (
          <div className="level-tree-form-error">{validationError}</div>
        )}
        <div className="level-tree-form-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={invalid}
          >
            Create
          </button>
        </div>
      </form>
    </Modal>
  );
}

function RenameLevelModal({
  initialValue,
  onClose,
  onSubmit,
}: {
  initialValue: string;
  onClose: () => void;
  onSubmit: (newName: string) => void | Promise<void>;
}) {
  const [name, setName] = useState(initialValue);
  const nameRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    nameRef.current?.focus();
    nameRef.current?.select();
  }, []);
  const trimmed = name.trim();
  const invalid =
    !trimmed ||
    trimmed === initialValue ||
    /[\\/]/.test(trimmed) ||
    trimmed.startsWith(".");
  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (invalid) return;
    void onSubmit(trimmed);
  };
  return (
    <Modal open onClose={onClose} title="Rename level" size="sm">
      <form className="level-tree-form" onSubmit={handleSubmit}>
        <label className="tree-modal-label" htmlFor="rename-level-name">
          New name
        </label>
        <input
          id="rename-level-name"
          ref={nameRef}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          spellCheck={false}
        />
        <p className="level-tree-form-hint">
          Renaming from <code>{initialValue}</code>. If you also have this
          level in the sequence, update the file name reference in the Level
          Configuration panel afterwards.
        </p>
        <div className="level-tree-form-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={invalid}
          >
            Rename
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmDeleteModal({
  fileName,
  onClose,
  onConfirm,
}: {
  fileName: string;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
}) {
  return (
    <Modal
      open
      onClose={onClose}
      title="Delete level?"
      size="sm"
      footer={
        <div className="level-tree-form-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void onConfirm()}
          >
            Delete
          </button>
        </div>
      }
    >
      <p className="editor-confirm-body">
        Delete <code>{fileName}</code>? A timestamped backup lands in{" "}
        <code>Mods/Backups/</code> so this isn't permanent.
      </p>
    </Modal>
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
