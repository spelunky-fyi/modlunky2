import { useEffect, useState, type MouseEvent, type ReactNode } from "react";
import { CSS } from "@dnd-kit/utilities";
import { useSortable } from "@dnd-kit/sortable";
import {
  ArrowUp,
  Folder,
  GripVertical,
  Loader2,
  Star,
  TriangleAlert,
  Trash2,
  Users,
} from "lucide-react";
import type { Mod } from "../../types/mods";
import { describeProblem } from "../../types/mods";
import { openCharacterChooserWindow } from "../../lib/commands";
import { useModLogo } from "../../hooks/useModLogo";
import "./ModColumn.css";

interface ModColumnProps {
  title: string;
  mods: Mod[];
  toggleLabel: string;
  onToggle: (id: string) => void;
  /** Omit to hide the delete affordance entirely. Left off the active column
   *  so a mod the game is currently loading can't be deleted out from under
   *  it in one click; disabling it first is the deliberate extra step. */
  onDelete?: (mod: Mod) => void;
  onOpenFolder: (id: string) => void;
  onUpdate: (mod: Mod) => void;
  onToggleFavorite: (mod: Mod) => void;
  /** Re-runs the file check for one mod. Needed because the cached result
   *  behind the badge can outlive the problem: editing a file in place
   *  doesn't change the pack folder's mtime, so fixing the file wouldn't
   *  clear the badge on its own. */
  onRecheck: (mod: Mod) => void;
  checkingIds: Set<string>;
  updatingIds: Set<string>;
  sortable?: boolean;
  /** Extra line under the mod name explaining its position in the current
   *  order. Only supplied when the sort is on something the row doesn't
   *  otherwise show, so a value the list is sorted by is never invisible. */
  detail?: (mod: Mod) => string | null;
  emptyMessage: string;
  /** Optional control rendered on the right of the column header. */
  headerAction?: ReactNode;
}

export function ModColumn({
  title,
  mods,
  toggleLabel,
  onToggle,
  onDelete,
  onOpenFolder,
  onUpdate,
  onToggleFavorite,
  onRecheck,
  checkingIds,
  updatingIds,
  sortable = false,
  detail,
  emptyMessage,
  headerAction,
}: ModColumnProps) {
  const [menu, setMenu] = useState<{ mod: Mod; x: number; y: number } | null>(
    null,
  );

  const openMenu = (mod: Mod, e: MouseEvent) => {
    e.preventDefault();
    setMenu({ mod, x: e.clientX, y: e.clientY });
  };

  useEffect(() => {
    if (!menu) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenu(null);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menu]);

  return (
    <section className="mod-column">
      <header className="mod-column-header">
        <span className="mod-column-title">{title}</span>
        <span className="mod-column-count">{mods.length}</span>
        {headerAction}
      </header>
      <div className="mod-column-body">
        {mods.length === 0 ? (
          <div className="mod-column-empty">{emptyMessage}</div>
        ) : (
          <ul className="mod-column-list">
            {mods.map((mod) =>
              sortable ? (
                <SortableRow
                  key={mod.id}
                  mod={mod}
                  toggleLabel={toggleLabel}
                  onToggle={onToggle}
                  onDelete={onDelete}
                  onOpenFolder={onOpenFolder}
                  onUpdate={onUpdate}
                  onToggleFavorite={onToggleFavorite}
                  onRecheck={onRecheck}
                  onContextMenu={openMenu}
                  detail={detail}
                  isChecking={checkingIds.has(mod.id)}
                  isUpdating={updatingIds.has(mod.id)}
                />
              ) : (
                <PlainRow
                  key={mod.id}
                  mod={mod}
                  toggleLabel={toggleLabel}
                  onToggle={onToggle}
                  onDelete={onDelete}
                  onOpenFolder={onOpenFolder}
                  onUpdate={onUpdate}
                  onToggleFavorite={onToggleFavorite}
                  onRecheck={onRecheck}
                  onContextMenu={openMenu}
                  detail={detail}
                  isChecking={checkingIds.has(mod.id)}
                  isUpdating={updatingIds.has(mod.id)}
                />
              ),
            )}
          </ul>
        )}
      </div>
      {menu && (
        <>
          <div
            className="mod-ctx-backdrop"
            onClick={() => setMenu(null)}
            onContextMenu={(e) => {
              e.preventDefault();
              setMenu(null);
            }}
          />
          <div
            className="mod-ctx-menu"
            style={{
              left: Math.min(menu.x, window.innerWidth - 220),
              top: Math.min(menu.y, window.innerHeight - 80),
            }}
            role="menu"
          >
            <button
              type="button"
              className="mod-ctx-item"
              onClick={() => {
                void openCharacterChooserWindow(menu.mod.id);
                setMenu(null);
              }}
            >
              <Users size={14} aria-hidden="true" />
              Set characters…
            </button>
          </div>
        </>
      )}
    </section>
  );
}

interface RowProps {
  mod: Mod;
  toggleLabel: string;
  onToggle: (id: string) => void;
  onDelete?: (mod: Mod) => void;
  onOpenFolder: (id: string) => void;
  onUpdate: (mod: Mod) => void;
  onToggleFavorite: (mod: Mod) => void;
  onRecheck: (mod: Mod) => void;
  onContextMenu: (mod: Mod, e: MouseEvent) => void;
  detail?: (mod: Mod) => string | null;
  isChecking: boolean;
  isUpdating: boolean;
}

function PlainRow({
  mod,
  toggleLabel,
  onToggle,
  onDelete,
  onOpenFolder,
  onUpdate,
  onToggleFavorite,
  onRecheck,
  onContextMenu,
  detail,
  isChecking,
  isUpdating,
}: RowProps) {
  return (
    <li
      className={`mod-row${isUpdating ? " is-updating" : ""}`}
      onContextMenu={(e) => onContextMenu(mod, e)}
    >
      <ModLogo mod={mod} />
      <RowBody mod={mod} detail={detail} />
      <ProblemBadge mod={mod} onRecheck={onRecheck} isChecking={isChecking} />
      <RowActions
        mod={mod}
        toggleLabel={toggleLabel}
        onToggle={onToggle}
        onDelete={onDelete}
        onOpenFolder={onOpenFolder}
        onUpdate={onUpdate}
        onToggleFavorite={onToggleFavorite}
        isUpdating={isUpdating}
      />
    </li>
  );
}

function SortableRow({
  mod,
  toggleLabel,
  onToggle,
  onDelete,
  onOpenFolder,
  onUpdate,
  onToggleFavorite,
  onRecheck,
  onContextMenu,
  detail,
  isChecking,
  isUpdating,
}: RowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: mod.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : undefined,
    zIndex: isDragging ? 1 : undefined,
  };

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`mod-row mod-row-sortable${isDragging ? " is-dragging" : ""}${isUpdating ? " is-updating" : ""}`}
      onContextMenu={(e) => onContextMenu(mod, e)}
    >
      <button
        type="button"
        className="mod-row-handle"
        aria-label="Reorder"
        {...attributes}
        {...listeners}
      >
        <GripVertical size={14} aria-hidden="true" />
      </button>
      <ModLogo mod={mod} />
      <RowBody mod={mod} detail={detail} />
      <ProblemBadge mod={mod} onRecheck={onRecheck} isChecking={isChecking} />
      <RowActions
        mod={mod}
        toggleLabel={toggleLabel}
        onToggle={onToggle}
        onDelete={onDelete}
        onOpenFolder={onOpenFolder}
        onUpdate={onUpdate}
        onToggleFavorite={onToggleFavorite}
        isUpdating={isUpdating}
      />
    </li>
  );
}

/**
 * Warns that a mod has files that can break the game.
 *
 * Clickable, and that isn't decoration: the finding behind it is cached, and
 * the cache can't see someone fixing the file in a text editor, because
 * editing a file's contents doesn't change the mtime of the folder above it.
 * So the user needs a way to say "I fixed it, look again".
 */
function ProblemBadge({
  mod,
  onRecheck,
  isChecking,
}: {
  mod: Mod;
  onRecheck: (mod: Mod) => void;
  isChecking: boolean;
}) {
  if (mod.problems.length === 0) return null;
  const summary = mod.problems.map(describeProblem).join("\n");
  return (
    <button
      type="button"
      className="mod-row-problem"
      onClick={() => onRecheck(mod)}
      disabled={isChecking}
      title={`${summary}

This can crash the game. Click to check again.`}
      aria-label={`${mod.problems.length} problem(s) found. Check again.`}
    >
      {isChecking ? (
        <Loader2 size={13} className="mod-row-spinner" aria-hidden="true" />
      ) : (
        <TriangleAlert size={13} aria-hidden="true" />
      )}
    </button>
  );
}

function ModLogo({ mod }: { mod: Mod }) {
  const url = useModLogo(mod.id);
  const initial = (mod.manifest?.name ?? mod.id).charAt(0).toUpperCase();
  return (
    <div className="mod-row-logo">
      {url ? (
        <img src={url} alt="" loading="lazy" />
      ) : (
        <span className="mod-row-logo-fallback" aria-hidden="true">
          {initial}
        </span>
      )}
    </div>
  );
}

function RowBody({
  mod,
  detail,
}: {
  mod: Mod;
  detail?: (mod: Mod) => string | null;
}) {
  const extra = detail?.(mod);
  return (
    <div className="mod-row-body">
      <div className="mod-row-title">{mod.manifest?.name ?? mod.id}</div>
      <div className="mod-row-meta">
        {/* Wrapped so the dense layout can drop the slug on its own and keep
            the sort detail, which is the half that's load-bearing there. */}
        <span className="mod-row-slug">{mod.manifest?.slug ?? mod.id}</span>
        {extra && <span className="mod-row-detail">{extra}</span>}
      </div>
    </div>
  );
}

function RowActions({
  mod,
  toggleLabel,
  onToggle,
  onDelete,
  onOpenFolder,
  onUpdate,
  onToggleFavorite,
  isUpdating,
  // The badge is rendered beside this group rather than inside it, so the
  // check-related props stop here.
}: Omit<RowProps, "onContextMenu" | "onRecheck" | "isChecking" | "detail">) {
  return (
    <div className="mod-row-actions">
      <button
        type="button"
        className={`mod-row-icon-btn mod-row-fav${mod.favorite ? " is-fav" : ""}`}
        aria-label={mod.favorite ? "Remove from favorites" : "Add to favorites"}
        aria-pressed={mod.favorite}
        title={mod.favorite ? "Remove from favorites" : "Add to favorites"}
        onClick={() => onToggleFavorite(mod)}
      >
        <Star
          size={14}
          aria-hidden="true"
          fill={mod.favorite ? "currentColor" : "none"}
        />
      </button>
      {(mod.hasUpdate || isUpdating) && (
        <button
          type="button"
          className={`mod-row-update${isUpdating ? " is-updating" : ""}`}
          onClick={() => onUpdate(mod)}
          disabled={isUpdating}
          title={isUpdating ? "Updating..." : "Update available"}
        >
          {isUpdating ? (
            <Loader2 size={12} className="mod-row-spinner" aria-hidden="true" />
          ) : (
            <ArrowUp size={12} aria-hidden="true" />
          )}
          {isUpdating ? "Updating..." : "Update"}
        </button>
      )}
      <button
        type="button"
        className="mod-row-toggle"
        onClick={() => onToggle(mod.id)}
      >
        {toggleLabel}
      </button>
      <button
        type="button"
        className="mod-row-icon-btn"
        aria-label="Open folder"
        title="Open folder"
        onClick={() => onOpenFolder(mod.id)}
      >
        <Folder size={14} aria-hidden="true" />
      </button>
      {onDelete && (
        <button
          type="button"
          className="mod-row-icon-btn mod-row-icon-danger"
          aria-label="Delete"
          title="Delete"
          onClick={() => onDelete(mod)}
        >
          <Trash2 size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

