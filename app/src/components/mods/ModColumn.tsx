import { useEffect, useState, type MouseEvent, type ReactNode } from "react";
import { CSS } from "@dnd-kit/utilities";
import { useSortable } from "@dnd-kit/sortable";
import {
  ArrowUp,
  Folder,
  GripVertical,
  Loader2,
  Trash2,
  Users,
} from "lucide-react";
import type { Mod } from "../../types/mods";
import { openCharacterChooserWindow } from "../../lib/commands";
import { useModLogo } from "../../hooks/useModLogo";
import "./ModColumn.css";

interface ModColumnProps {
  title: string;
  mods: Mod[];
  toggleLabel: string;
  onToggle: (id: string) => void;
  onDelete: (mod: Mod) => void;
  onOpenFolder: (id: string) => void;
  onUpdate: (mod: Mod) => void;
  updatingIds: Set<string>;
  sortable?: boolean;
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
  updatingIds,
  sortable = false,
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
                  onContextMenu={openMenu}
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
                  onContextMenu={openMenu}
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
  onDelete: (mod: Mod) => void;
  onOpenFolder: (id: string) => void;
  onUpdate: (mod: Mod) => void;
  onContextMenu: (mod: Mod, e: MouseEvent) => void;
  isUpdating: boolean;
}

function PlainRow({
  mod,
  toggleLabel,
  onToggle,
  onDelete,
  onOpenFolder,
  onUpdate,
  onContextMenu,
  isUpdating,
}: RowProps) {
  return (
    <li
      className={`mod-row${isUpdating ? " is-updating" : ""}`}
      onContextMenu={(e) => onContextMenu(mod, e)}
    >
      <ModLogo mod={mod} />
      <RowBody mod={mod} />
      <RowActions
        mod={mod}
        toggleLabel={toggleLabel}
        onToggle={onToggle}
        onDelete={onDelete}
        onOpenFolder={onOpenFolder}
        onUpdate={onUpdate}
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
  onContextMenu,
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
      <RowBody mod={mod} />
      <RowActions
        mod={mod}
        toggleLabel={toggleLabel}
        onToggle={onToggle}
        onDelete={onDelete}
        onOpenFolder={onOpenFolder}
        onUpdate={onUpdate}
        isUpdating={isUpdating}
      />
    </li>
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

function RowBody({ mod }: { mod: Mod }) {
  return (
    <div className="mod-row-body">
      <div className="mod-row-title">{mod.manifest?.name ?? mod.id}</div>
      <div className="mod-row-meta">{mod.manifest?.slug ?? mod.id}</div>
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
  isUpdating,
}: Omit<RowProps, "onContextMenu">) {
  return (
    <div className="mod-row-actions">
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
      <button
        type="button"
        className="mod-row-icon-btn mod-row-icon-danger"
        aria-label="Delete"
        title="Delete"
        onClick={() => onDelete(mod)}
      >
        <Trash2 size={14} aria-hidden="true" />
      </button>
    </div>
  );
}

