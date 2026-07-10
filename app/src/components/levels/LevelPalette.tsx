import { useMemo, useState } from "react";
import { GripVertical, Trash2 } from "lucide-react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { CSS } from "@dnd-kit/utilities";
import type {
  CustomLevelPaletteEntry,
  EditorAtlas,
} from "../../lib/commands";
import "./LevelPalette.css";

interface Props {
  palette: CustomLevelPaletteEntry[];
  atlas: EditorAtlas | null;
  /** Extra swatches for tiles added after the atlas was built. Keyed by
   *  tile name, value is a PNG data URL from `getTileSprite`. Beats the
   *  atlas lookup so newly-added tiles show their real preview. */
  swatchOverrides?: Map<string, string>;
  primaryName: string | null;
  secondaryName: string | null;
  /** Left-click sets primary, right-click sets secondary. */
  onSelectPrimary: (name: string) => void;
  onSelectSecondary: (name: string) => void;
  /** Called when the user clicks the "Add tile" button; parent opens the
   *  modal. */
  onOpenAddTile?: () => void;
  /** Commit a new palette order after the user drags a row. The parent
   *  owns the palette state; we just report the reordered array. */
  onReorder?: (next: CustomLevelPaletteEntry[]) => void;
  /** Delete a palette entry. Only fires from the trash button in reorder
   *  mode; the parent is responsible for confirming and replacing any
   *  live uses of the tile in the grid. */
  onDelete?: (name: string) => void;
  /** Controlled reorder mode. The parent owns the toggle so its icon
   *  can live in a shared header (alongside conflicts / help). Omit
   *  to keep the palette in normal pick-tile mode. */
  reorderMode?: boolean;
  /** Icon-only, wrapping layout for a dense palette. The caller already
   *  suppresses this while reordering, so drag/delete keep the full rows. */
  dense?: boolean;
}

interface SwatchStyle {
  style: React.CSSProperties;
}

export function LevelPalette({
  palette,
  atlas,
  swatchOverrides,
  primaryName,
  secondaryName,
  onSelectPrimary,
  onSelectSecondary,
  onOpenAddTile,
  onReorder,
  onDelete,
  reorderMode: reorderModeProp,
  dense = false,
}: Props) {
  const [filter, setFilter] = useState("");
  // Reorder mode is now driven externally so the toggle icon can live
  // in a shared header alongside conflicts / help. Callers who want
  // reorder wire `reorderMode` + `onSetReorderMode`; otherwise the
  // palette stays in the normal pick-tile mode.
  const reorderMode = reorderModeProp ?? false;

  const uvByName = useMemo(() => {
    const map = new Map<string, { x: number; y: number; w: number; h: number }>();
    if (atlas) {
      for (const t of atlas.tiles) {
        map.set(t.name, { x: t.x, y: t.y, w: t.w, h: t.h });
      }
    }
    return map;
  }, [atlas]);

  const filterLower = filter.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      filterLower
        ? palette.filter((p) => p.name.toLowerCase().includes(filterLower))
        : palette,
    [palette, filterLower],
  );

  const swatchStyleFor = (entry: CustomLevelPaletteEntry): SwatchStyle => {
    const swatchSize = 40;
    const override = swatchOverrides?.get(entry.name);
    if (override) {
      return {
        style: {
          backgroundImage: `url(${override})`,
          backgroundSize: `${swatchSize}px ${swatchSize}px`,
          backgroundRepeat: "no-repeat",
          width: swatchSize,
          height: swatchSize,
        },
      };
    }
    const uv = uvByName.get(entry.name);
    if (uv && atlas) {
      // Multi-cell tiles (nat_w or nat_h > 1) have uv.w / uv.h bigger
      // than a single cell in the atlas. Fit the whole natural sprite
      // inside the swatch instead of scaling by width alone, so a
      // 1x2 or 2x2 tile isn't clipped or squashed vertically.
      const scale = Math.min(swatchSize / uv.w, swatchSize / uv.h);
      return {
        style: {
          backgroundImage: `url(${atlas.pngDataUrl})`,
          backgroundPosition: `-${uv.x * scale}px -${uv.y * scale}px`,
          backgroundSize: `${atlas.width * scale}px ${atlas.height * scale}px`,
          backgroundRepeat: "no-repeat",
          width: swatchSize,
          height: swatchSize,
        },
      };
    }
    return { style: { width: swatchSize, height: swatchSize } };
  };

  // dnd-kit uses stable string IDs. Tile-code chars are unique per palette
  // so they make a natural id.
  const items = palette.map((p) => p.code);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !onReorder) return;
    const from = items.indexOf(String(active.id));
    const to = items.indexOf(String(over.id));
    if (from < 0 || to < 0) return;
    onReorder(arrayMove(palette, from, to));
  };

  return (
    <div className="level-palette-wrap">
      <div className="level-palette-header">
        <input
          type="text"
          className="level-palette-search"
          placeholder={
            reorderMode ? "Reorder mode, filter disabled" : "Filter tiles..."
          }
          value={reorderMode ? "" : filter}
          onChange={(e) => setFilter(e.target.value)}
          disabled={reorderMode}
        />
      </div>

      {palette.length === 0 && (
        <div className="level-palette-empty">
          No tile codes in this level yet. Add one below.
        </div>
      )}

      {palette.length > 0 && filtered.length === 0 && (
        <div className="level-palette-empty">
          No tiles match &quot;{filter}&quot;.
        </div>
      )}

      {filtered.length > 0 && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          modifiers={[restrictToVerticalAxis]}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={items}
            strategy={verticalListSortingStrategy}
          >
            <ul className={`level-palette${dense ? " dense" : ""}`}>
              {palette.map((entry) => {
                if (
                  filterLower &&
                  !entry.name.toLowerCase().includes(filterLower)
                ) {
                  return null;
                }
                return (
                  // Key by code+name, not code alone: a level can carry two
                  // entries sharing a tile code (a code collision), which
                  // would otherwise be duplicate React keys.
                  <PaletteRow
                    key={`${entry.code}-${entry.name}`}
                    entry={entry}
                    reorderMode={reorderMode && !!onReorder}
                    swatch={swatchStyleFor(entry)}
                    isPrimary={primaryName === entry.name}
                    isSecondary={secondaryName === entry.name}
                    onSelectPrimary={onSelectPrimary}
                    onSelectSecondary={onSelectSecondary}
                    onDelete={onDelete}
                  />
                );
              })}
            </ul>
          </SortableContext>
        </DndContext>
      )}

      {onOpenAddTile && (
        <button
          type="button"
          className="level-palette-add-button"
          onClick={onOpenAddTile}
        >
          + Add tile...
        </button>
      )}
    </div>
  );
}


interface PaletteRowProps {
  entry: CustomLevelPaletteEntry;
  reorderMode: boolean;
  swatch: SwatchStyle;
  isPrimary: boolean;
  isSecondary: boolean;
  onSelectPrimary: (name: string) => void;
  onSelectSecondary: (name: string) => void;
  onDelete?: (name: string) => void;
}

function PaletteRow({
  entry,
  reorderMode,
  swatch,
  isPrimary,
  isSecondary,
  onSelectPrimary,
  onSelectSecondary,
  onDelete,
}: PaletteRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: entry.code, disabled: !reorderMode });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : undefined,
    zIndex: isDragging ? 1 : undefined,
  };

  const classes = [
    "level-palette-item",
    isPrimary ? "primary" : "",
    isSecondary ? "secondary" : "",
    reorderMode ? "reorder" : "",
    isDragging ? "dragging" : "",
  ]
    .filter(Boolean)
    .join(" ");

  // In reorder mode the whole row is the drag handle (attributes+listeners
  // spread onto the li). Left/right click do nothing so a stray click can't
  // reassign the selection while the user is dragging things around.
  const rowProps = reorderMode
    ? { ...attributes, ...listeners }
    : {};

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={classes}
      {...rowProps}
    >
      {reorderMode && (
        <span
          className="level-palette-handle"
          aria-hidden="true"
        >
          <GripVertical size={14} aria-hidden="true" />
        </span>
      )}
      <button
        type="button"
        className="level-palette-swatch-btn"
        onClick={reorderMode ? undefined : () => onSelectPrimary(entry.name)}
        onContextMenu={(ev) => {
          ev.preventDefault();
          if (!reorderMode) onSelectSecondary(entry.name);
        }}
        onMouseDown={(ev) => {
          if (!reorderMode) ev.preventDefault();
        }}
        disabled={reorderMode}
        title={`${entry.name} (${entry.code})\nLeft-click: primary, right-click: secondary${entry.comment ? `\n${entry.comment}` : ""}`}
      >
        <span className="level-palette-swatch" style={swatch.style}>
          {isPrimary && (
            <span className="level-palette-badge primary">L</span>
          )}
          {isSecondary && (
            <span className="level-palette-badge secondary">R</span>
          )}
        </span>
        <span className="level-palette-meta">
          <span className="level-palette-name">{entry.name}</span>
          <span className="level-palette-code">{entry.code}</span>
        </span>
      </button>
      {reorderMode && onDelete && (
        <button
          type="button"
          className="level-palette-delete"
          onClick={() => onDelete(entry.name)}
          onMouseDown={(e) => e.preventDefault()}
          onPointerDown={(e) => e.stopPropagation()}
          title={`Delete ${entry.name}`}
          aria-label={`Delete ${entry.name}`}
        >
          <Trash2 size={14} aria-hidden="true" />
        </button>
      )}
    </li>
  );
}

