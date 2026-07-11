import {
  createContext,
  memo,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Copy,
  CopyPlus,
  GripVertical,
  SquareArrowOutUpRight,
  Trash2,
} from "lucide-react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  getFirstCollision,
  pointerWithin,
  rectIntersection,
  useDroppable,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Modal } from "../shared/Modal";
import type {
  EditorAtlas,
  EditorAtlasTile,
  VanillaLevelData,
} from "../../lib/commands";
import "./RoomManagerModal.css";

type PurgeScope = "rooms" | "templates" | "both";
type Template = VanillaLevelData["templates"][number];
type Room = Template["rooms"][number];

interface RoomManagerModalProps {
  open: boolean;
  onClose: () => void;
  templates: VanillaLevelData["templates"];
  atlas: EditorAtlas | null;
  /** Current foreground (tile-name grid) for a room, reading any live edits. */
  fgFor: (templateName: string, roomIndex: number) => string[][];
  onEditTemplateComment: (templateName: string, comment: string) => void;
  onEditRoomComment: (
    templateName: string,
    roomIndex: number,
    comment: string,
  ) => void;
  onJumpToRoom: (templateName: string, roomIndex: number) => void;
  /** Copy a room to the clipboard. `append` (Shift-click) adds to the existing
   *  clipboard rooms instead of replacing them. */
  onCopyRoom: (templateName: string, roomIndex: number, append: boolean) => void;
  /** Delete a single room. On a template's last room this clears it to a blank
   *  room instead of removing it (a template keeps at least one room). */
  onDeleteRoom: (templateName: string, roomIndex: number) => void;
  /** Delete every room in a template, leaving one blank room. */
  onDeleteAllRooms: (templateName: string) => void;
  /** Reorder a room within its template or move it to another. `toIdx` is the
   *  insertion index in the destination after removal from the source. */
  onMoveRoom: (
    fromTpl: string,
    fromIdx: number,
    toTpl: string,
    toIdx: number,
  ) => void;
  onPurgeComments: (scope: PurgeScope) => void;
}

// A room's stable drag identity for the length of one drag: its origin
// template + index. Template names can't contain '#', so the last '#' splits
// name from index. During a drag these ids get shuffled between containers
// while `uidMeta` still resolves each back to its original room content.
const roomUid = (templateName: string, roomIndex: number) =>
  `${templateName}#${roomIndex}`;

interface UidMeta {
  templateName: string;
  roomIndex: number;
  room: Room;
  width: number;
  height: number;
}

// containerName -> ordered room uids. Mirrors `templates` when idle; during a
// drag it reorders live so the dragged card sits where it will land.
type ItemMap = Record<string, string[]>;
const buildItems = (templates: Template[]): ItemMap =>
  Object.fromEntries(
    templates.map((t) => [
      t.name,
      t.rooms.map((_, i) => roomUid(t.name, i)),
    ]),
  );

interface RoomManagerCtxValue {
  atlasImg: HTMLImageElement | null;
  tileByName: Map<string, EditorAtlasTile>;
  fgFor: (templateName: string, roomIndex: number) => string[][];
  shiftHeld: boolean;
  armedDelete: string | null;
  arm: (id: string) => void;
  disarm: () => void;
  onJumpToRoom: (templateName: string, roomIndex: number) => void;
  onCopyRoom: (templateName: string, roomIndex: number, append: boolean) => void;
  onDeleteRoom: (templateName: string, roomIndex: number) => void;
  onEditRoomComment: (
    templateName: string,
    roomIndex: number,
    comment: string,
  ) => void;
  /** Rooms in a template, by original name; drives the "last room clears
   *  instead of deletes" hint. */
  roomCountOf: (templateName: string) => number;
  /** True while dragging and this template can't accept the dragged room. */
  isInvalidTarget: (templateName: string) => boolean;
}

const RoomManagerCtx = createContext<RoomManagerCtxValue | null>(null);
const useRoomManagerCtx = () => {
  const ctx = useContext(RoomManagerCtx);
  if (!ctx) throw new Error("RoomManagerCtx missing");
  return ctx;
};

export function RoomManagerModal({
  open,
  onClose,
  templates,
  atlas,
  fgFor,
  onEditTemplateComment,
  onEditRoomComment,
  onJumpToRoom,
  onCopyRoom,
  onDeleteRoom,
  onDeleteAllRooms,
  onMoveRoom,
  onPurgeComments,
}: RoomManagerModalProps) {
  const [confirmingPurge, setConfirmingPurge] = useState(false);
  // Two-click delete confirmation. `armedDelete` holds the id of the delete
  // button waiting for its second click (`room:tpl#idx` or `all:tpl`); the
  // first click arms it, the second commits. Auto-disarms after a few seconds
  // and whenever the modal closes so a stale armed button can't bite later.
  const [armedDelete, setArmedDelete] = useState<string | null>(null);
  const armTimer = useRef<number | null>(null);
  // Stable identities so the shared context (below) stays referentially stable
  // across the many re-renders a drag triggers.
  const arm = useCallback((id: string) => {
    setArmedDelete(id);
    if (armTimer.current != null) window.clearTimeout(armTimer.current);
    armTimer.current = window.setTimeout(() => setArmedDelete(null), 3000);
  }, []);
  const disarm = useCallback(() => {
    setArmedDelete(null);
    if (armTimer.current != null) window.clearTimeout(armTimer.current);
    armTimer.current = null;
  }, []);
  useEffect(() => {
    if (!open) disarm();
  }, [open]);
  useEffect(() => () => disarm(), []);
  // Track Shift so each room's copy icon can preview the append action. The
  // click handler reads e.shiftKey directly, so the action stays correct even
  // if this state lags.
  const [shiftHeld, setShiftHeld] = useState(false);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: KeyboardEvent) => {
      if (e.key === "Shift") setShiftHeld(true);
    };
    const onUp = (e: KeyboardEvent) => {
      if (e.key === "Shift") setShiftHeld(false);
    };
    const onBlur = () => setShiftHeld(false);
    window.addEventListener("keydown", onDown);
    window.addEventListener("keyup", onUp);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("keyup", onUp);
      window.removeEventListener("blur", onBlur);
    };
  }, [open]);

  // Decode the packed atlas PNG once so every room preview can blit from it.
  const [atlasImg, setAtlasImg] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!open || !atlas) {
      setAtlasImg(null);
      return;
    }
    let cancelled = false;
    const img = new Image();
    img.onload = () => {
      if (!cancelled) setAtlasImg(img);
    };
    img.src = atlas.pngDataUrl;
    return () => {
      cancelled = true;
    };
  }, [open, atlas]);

  const tileByName = useMemo(() => {
    const m = new Map<string, EditorAtlasTile>();
    atlas?.tiles.forEach((t) => m.set(t.name, t));
    return m;
  }, [atlas]);

  // Reset the purge confirmation whenever the modal is (re)opened.
  useEffect(() => {
    if (!open) setConfirmingPurge(false);
  }, [open]);

  // --- Drag and drop (multi-container sortable) ---
  const sensors = useSensors(
    // A small distance threshold so clicks on the drag handle's neighbours
    // (jump / copy / delete) aren't swallowed as drags.
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  // uid -> origin room. Stable through a drag because `templates` only changes
  // when a move commits (which ends the drag), so it always resolves a uid to
  // the room content to render, even after the uid is shuffled to another
  // container.
  const uidMeta = useMemo(() => {
    const m = new Map<string, UidMeta>();
    for (const t of templates) {
      t.rooms.forEach((room, i) => {
        m.set(roomUid(t.name, i), {
          templateName: t.name,
          roomIndex: i,
          room,
          width: room.width,
          height: room.height,
        });
      });
    }
    return m;
  }, [templates]);

  const [items, setItems] = useState<ItemMap>(() => buildItems(templates));
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  // Re-sync from props whenever the underlying data changes, so a committed
  // move (or any external edit) refreshes the arrangement. Keyed on
  // `templates` only, NOT activeId: a drop sets `items` to the final order and
  // ends the drag, and the committed data lands a beat later; re-syncing on
  // the activeId change in between would snap back to the old order and flash.
  // The drag-end / cancel / no-op paths resync explicitly when needed.
  //
  // useLayoutEffect (not useEffect) so the re-sync runs before paint: moving a
  // template's only room out leaves its local `items` list momentarily empty
  // until the committed blank room arrives via `templates`, and a passive
  // effect would paint that empty frame first.
  useLayoutEffect(() => {
    if (activeIdRef.current) return;
    setItems(buildItems(templates));
  }, [templates]);

  const lastOverId = useRef<string | null>(null);
  const recentlyMovedToNewContainer = useRef(false);
  useEffect(() => {
    // The collision strategy leans on this to hold a stable target for one
    // frame after a cross-container transfer; clear it once the move renders.
    requestAnimationFrame(() => {
      recentlyMovedToNewContainer.current = false;
    });
  }, [items]);

  const findContainer = (id: string, map: ItemMap): string | undefined => {
    if (id in map) return id;
    return Object.keys(map).find((k) => map[k].includes(id));
  };

  // pointerWithin first so hovering a specific card targets THAT card (drop
  // anywhere, not just the end); when a container itself is the hit, retarget
  // to its closest card so cross-container inserts land at a real position.
  const collisionDetection: CollisionDetection = (args) => {
    const pointer = pointerWithin(args);
    const intersections = pointer.length > 0 ? pointer : rectIntersection(args);
    let overId = getFirstCollision(intersections, "id");
    if (overId != null) {
      const overStr = String(overId);
      if (overStr in items) {
        const containerItems = items[overStr];
        if (containerItems.length > 0) {
          const closest = closestCenter({
            ...args,
            droppableContainers: args.droppableContainers.filter(
              (c) => c.id !== overStr && containerItems.includes(String(c.id)),
            ),
          })[0]?.id;
          if (closest != null) overId = closest;
        }
      }
      lastOverId.current = String(overId);
      return [{ id: overId }];
    }
    if (recentlyMovedToNewContainer.current) lastOverId.current = activeId;
    return lastOverId.current != null ? [{ id: lastOverId.current }] : [];
  };
  const activeInfo = activeId ? (uidMeta.get(activeId) ?? null) : null;

  const isInvalidTarget = useCallback(
    (templateName: string) => {
      if (!activeInfo || templateName === activeInfo.templateName) return false;
      const first = templates.find((t) => t.name === templateName)?.rooms[0];
      if (!first) return false;
      return (
        first.width !== activeInfo.width || first.height !== activeInfo.height
      );
    },
    [activeInfo, templates],
  );

  // Can the dragged room move into this container right now? Blocks only size
  // mismatches. Emptying the source is allowed: the move leaves a blank room
  // behind (like deleting a template's last room). Enforced during the drag so
  // an invalid target simply never accepts the card.
  const canDropInto = (destContainer: string, activeUid: string) => {
    const meta = uidMeta.get(activeUid);
    if (!meta) return false;
    if (destContainer === meta.templateName) return true;
    const destFirst = templates.find((t) => t.name === destContainer)
      ?.rooms[0];
    if (destFirst && (destFirst.width !== meta.width || destFirst.height !== meta.height)) {
      return false;
    }
    return true;
  };

  const onDragStart = (e: DragStartEvent) => {
    setActiveId(String(e.active.id));
    disarm();
  };

  const onDragOver = (e: DragOverEvent) => {
    const { active, over } = e;
    if (!over) return;
    const activeUid = String(active.id);
    const overStr = String(over.id);
    const activeContainer = findContainer(activeUid, items);
    const overContainer = findContainer(overStr, items);
    if (!activeContainer || !overContainer) return;
    if (activeContainer === overContainer) return; // same-container: on drag end
    if (!canDropInto(overContainer, activeUid)) return;

    setItems((prev) => {
      const activeItems = prev[activeContainer];
      const overItems = prev[overContainer];
      if (!activeItems || !overItems) return prev;
      const overIndex = overItems.indexOf(overStr);
      let newIndex: number;
      if (overStr in prev) {
        newIndex = overItems.length; // dropped on the container: append
      } else {
        const rect = active.rect.current.translated;
        const isBelow =
          rect && over.rect && rect.top > over.rect.top + over.rect.height / 2;
        newIndex =
          overIndex >= 0
            ? overIndex + (isBelow ? 1 : 0)
            : overItems.length;
      }
      recentlyMovedToNewContainer.current = true;
      return {
        ...prev,
        [activeContainer]: activeItems.filter((id) => id !== activeUid),
        [overContainer]: [
          ...overItems.slice(0, newIndex),
          activeUid,
          ...overItems.slice(newIndex),
        ],
      };
    });
  };

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    const activeUid = String(active.id);
    const activeContainer = findContainer(activeUid, items);
    if (!activeContainer) {
      setActiveId(null);
      return;
    }
    // Finalize a same-container reorder (onDragOver only handles transfers).
    let finalItems = items;
    if (over) {
      const overStr = String(over.id);
      if (
        !(overStr in items) &&
        findContainer(overStr, items) === activeContainer
      ) {
        const arr = items[activeContainer];
        const from = arr.indexOf(activeUid);
        const to = arr.indexOf(overStr);
        if (from !== -1 && to !== -1 && from !== to) {
          finalItems = {
            ...items,
            [activeContainer]: arrayMove(arr, from, to),
          };
          setItems(finalItems);
        }
      }
    }
    setActiveId(null);

    const toTpl = Object.keys(finalItems).find((k) =>
      finalItems[k].includes(activeUid),
    );
    const meta = uidMeta.get(activeUid);
    if (!toTpl || !meta) return;
    const toIdx = finalItems[toTpl].indexOf(activeUid);
    if (meta.templateName === toTpl && meta.roomIndex === toIdx) {
      // No effective change; snap the local arrangement back to the data.
      setItems(buildItems(templates));
      return;
    }
    onMoveRoom(meta.templateName, meta.roomIndex, toTpl, toIdx);
  };

  const onDragCancel = () => {
    setItems(buildItems(templates));
    setActiveId(null);
  };

  const roomCountByTemplate = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of templates) m[t.name] = t.rooms.length;
    return m;
  }, [templates]);
  const roomCountOf = useCallback(
    (name: string) => roomCountByTemplate[name] ?? 0,
    [roomCountByTemplate],
  );

  const roomCount = templates.reduce((n, t) => n + t.rooms.length, 0);

  const purge = (scope: PurgeScope) => {
    onPurgeComments(scope);
    setConfirmingPurge(false);
  };

  // Memoized so a drag (which re-renders this component on every pointer move
  // via setItems) doesn't hand every RoomCard a fresh context value and force
  // the whole grid to re-render. During a drag none of these deps change, so
  // only the cards dnd-kit actually moves re-render.
  const ctx: RoomManagerCtxValue = useMemo(
    () => ({
      atlasImg,
      tileByName,
      fgFor,
      shiftHeld,
      armedDelete,
      arm,
      disarm,
      onJumpToRoom,
      onCopyRoom,
      onDeleteRoom,
      onEditRoomComment,
      roomCountOf,
      isInvalidTarget,
    }),
    [
      atlasImg,
      tileByName,
      fgFor,
      shiftHeld,
      armedDelete,
      arm,
      disarm,
      onJumpToRoom,
      onCopyRoom,
      onDeleteRoom,
      onEditRoomComment,
      roomCountOf,
      isInvalidTarget,
    ],
  );

  return (
    <Modal open={open} onClose={onClose} title="Rooms & comments" size="xl">
      <div className="rm-toolbar">
        <span className="rm-toolbar-info">
          {templates.length} template{templates.length === 1 ? "" : "s"} ·{" "}
          {roomCount} room{roomCount === 1 ? "" : "s"}
        </span>
        {confirmingPurge ? (
          <div className="rm-purge-confirm">
            <span className="rm-purge-label">Remove all</span>
            <button
              type="button"
              className="rm-purge-choice"
              onClick={() => purge("rooms")}
            >
              Room comments
            </button>
            <button
              type="button"
              className="rm-purge-choice"
              onClick={() => purge("templates")}
            >
              Template comments
            </button>
            <button
              type="button"
              className="rm-purge-choice"
              onClick={() => purge("both")}
            >
              Both
            </button>
            <button
              type="button"
              className="rm-purge-cancel"
              onClick={() => setConfirmingPurge(false)}
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="rm-purge-btn"
            onClick={() => setConfirmingPurge(true)}
          >
            <Trash2 size={14} aria-hidden="true" />
            Remove comments...
          </button>
        )}
      </div>

      <RoomManagerCtx.Provider value={ctx}>
        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={onDragStart}
          onDragOver={onDragOver}
          onDragEnd={onDragEnd}
          onDragCancel={onDragCancel}
        >
          <div className="rm-body">
            {templates.length === 0 && (
              <div className="rm-empty">This file has no templates.</div>
            )}
            {templates.map((tpl) => (
              <TemplateSection
                key={tpl.name}
                tpl={tpl}
                roomUids={items[tpl.name] ?? []}
                uidMeta={uidMeta}
                onEditTemplateComment={onEditTemplateComment}
                onDeleteAllRooms={onDeleteAllRooms}
              />
            ))}
          </div>
          {/* No drop animation: the reordered layout is already correct when
              the drag ends, so animating the floating clone back to a slot
              only reads as the card "flying back" before the state catches
              up. Dropping it instantly settles in place. */}
          <DragOverlay dropAnimation={null}>
            {activeInfo ? (
              <div className="rm-room-card rm-room-card-overlay">
                <div className="rm-room-preview-wrap dark-scope">
                  <RoomFgPreview
                    grid={fgFor(activeInfo.templateName, activeInfo.roomIndex)}
                    atlasImg={atlasImg}
                    tileByName={tileByName}
                  />
                  <span className="rm-room-label">
                    room {activeInfo.roomIndex}
                  </span>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </RoomManagerCtx.Provider>
    </Modal>
  );
}

const TemplateSection = memo(function TemplateSection({
  tpl,
  roomUids,
  uidMeta,
  onEditTemplateComment,
  onDeleteAllRooms,
}: {
  tpl: Template;
  roomUids: string[];
  uidMeta: Map<string, UidMeta>;
  onEditTemplateComment: (templateName: string, comment: string) => void;
  onDeleteAllRooms: (templateName: string) => void;
}) {
  const { armedDelete, arm, disarm, isInvalidTarget } = useRoomManagerCtx();
  // Droppable so rooms can be dropped into this template's empty space (past
  // the last card) and so empty containers still accept a drop.
  const { setNodeRef } = useDroppable({ id: tpl.name });
  const invalid = isInvalidTarget(tpl.name);
  const allId = `all:${tpl.name}`;
  const allArmed = armedDelete === allId;

  return (
    <section
      className={`rm-template${invalid ? " rm-template-invalid" : ""}`}
      ref={setNodeRef}
    >
      <div className="rm-template-head">
        <span className="rm-template-name">{tpl.name}</span>
        <span className="rm-template-count">{tpl.rooms.length}</span>
        {tpl.rooms.length > 0 && (
          <button
            type="button"
            className={`rm-template-delete${allArmed ? " armed" : ""}`}
            title={
              allArmed
                ? "Click again to delete every room"
                : "Delete all rooms (kept as one blank room)"
            }
            onClick={() => {
              if (allArmed) {
                disarm();
                onDeleteAllRooms(tpl.name);
              } else {
                arm(allId);
              }
            }}
          >
            <Trash2 size={13} aria-hidden="true" />
            {allArmed ? "Delete all rooms?" : "Delete all rooms"}
          </button>
        )}
      </div>
      <CommentInput
        className="rm-template-comment"
        value={tpl.comment}
        placeholder="Template comment"
        onCommit={(c) => onEditTemplateComment(tpl.name, c)}
      />
      {roomUids.length > 0 && (
        <SortableContext items={roomUids} strategy={rectSortingStrategy}>
          <div className="rm-room-grid">
            {roomUids.map((uid) => {
              const meta = uidMeta.get(uid);
              if (!meta) return null;
              return (
                <RoomCard
                  key={uid}
                  uid={uid}
                  templateName={meta.templateName}
                  roomIndex={meta.roomIndex}
                  room={meta.room}
                />
              );
            })}
          </div>
        </SortableContext>
      )}
    </section>
  );
});

// Thin sortable wrapper. useSortable subscribes to dnd-kit's context, which
// updates on EVERY pointer move, so this re-renders constantly during a drag
// (across every mounted card). Keep it as light as possible -- just the
// transform + drag handle -- and push all the heavy content into the memoized
// RoomCardBody, which has stable props + stable context so it skips those
// re-renders entirely. With hundreds of rooms this is the difference between
// reconciling bare divs and reconciling full card subtrees per frame.
const RoomCard = memo(function RoomCard({
  uid,
  templateName,
  roomIndex,
  room,
}: {
  uid: string;
  templateName: string;
  roomIndex: number;
  room: Room;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: uid });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rm-room-card${isDragging ? " dragging" : ""}`}
    >
      <button
        type="button"
        className="rm-room-drag"
        title="Drag to reorder or move to another template"
        aria-label="Drag room"
        {...attributes}
        {...listeners}
      >
        <GripVertical size={13} aria-hidden="true" />
      </button>
      <RoomCardBody
        templateName={templateName}
        roomIndex={roomIndex}
        room={room}
      />
    </div>
  );
});

const RoomCardBody = memo(function RoomCardBody({
  templateName,
  roomIndex,
  room,
}: {
  templateName: string;
  roomIndex: number;
  room: Room;
}) {
  const {
    atlasImg,
    tileByName,
    fgFor,
    shiftHeld,
    armedDelete,
    arm,
    disarm,
    onJumpToRoom,
    onCopyRoom,
    onDeleteRoom,
    onEditRoomComment,
    roomCountOf,
  } = useRoomManagerCtx();
  const isLastRoom = roomCountOf(templateName) <= 1;
  const deleteId = `room:${templateName}#${roomIndex}`;
  const deleteArmed = armedDelete === deleteId;

  return (
    <>
      <div className="rm-room-preview-wrap dark-scope">
        <button
          type="button"
          className="rm-room-jump"
          title={`Jump to room ${roomIndex}`}
          onClick={() => onJumpToRoom(templateName, roomIndex)}
        >
          <RoomFgPreview
            grid={fgFor(templateName, roomIndex)}
            atlasImg={atlasImg}
            tileByName={tileByName}
          />
          <span className="rm-room-label">
            room {roomIndex}
            <SquareArrowOutUpRight
              size={11}
              aria-hidden="true"
              className="rm-room-jump-icon"
            />
          </span>
        </button>
        <button
          type="button"
          className="rm-room-copy"
          title={
            shiftHeld
              ? "Add room to clipboard"
              : "Copy room (hold Shift to add to clipboard)"
          }
          onClick={(e) => onCopyRoom(templateName, roomIndex, e.shiftKey)}
        >
          {shiftHeld ? (
            <CopyPlus size={13} aria-hidden="true" />
          ) : (
            <Copy size={13} aria-hidden="true" />
          )}
        </button>
        <button
          type="button"
          className={`rm-room-delete${deleteArmed ? " armed" : ""}`}
          title={
            deleteArmed
              ? isLastRoom
                ? "Click again to clear this room"
                : "Click again to delete this room"
              : isLastRoom
                ? "Clear room (blanks the template's last room)"
                : "Delete room"
          }
          onClick={() => {
            if (deleteArmed) {
              disarm();
              onDeleteRoom(templateName, roomIndex);
            } else {
              arm(deleteId);
            }
          }}
        >
          <Trash2 size={13} aria-hidden="true" />
        </button>
      </div>
      <CommentInput
        className="rm-room-comment"
        value={room.comment}
        placeholder="comment"
        onCommit={(c) => onEditRoomComment(templateName, roomIndex, c)}
      />
    </>
  );
});

// Uncontrolled-ish comment field: local text while editing, committed on blur
// only when it actually changed. Re-syncs when the underlying value changes
// (e.g. a purge clears it) so the input reflects external edits.
function CommentInput({
  value,
  placeholder,
  className,
  onCommit,
}: {
  value: string | null;
  placeholder: string;
  className?: string;
  onCommit: (comment: string) => void;
}) {
  const [text, setText] = useState(value ?? "");
  useEffect(() => {
    setText(value ?? "");
  }, [value]);
  return (
    <input
      type="text"
      className={className}
      value={text}
      placeholder={placeholder}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => {
        const norm = text.trim();
        if ((norm || null) !== (value ?? null)) onCommit(norm);
      }}
    />
  );
}

// Small foreground-only thumbnail drawn straight from the packed atlas.
// Memoized: during a drag the props are stable (fgFor returns the grid's live
// array reference), so the canvas never redraws for cards that didn't change.
const RoomFgPreview = memo(function RoomFgPreview({
  grid,
  atlasImg,
  tileByName,
}: {
  grid: string[][];
  atlasImg: HTMLImageElement | null;
  tileByName: Map<string, EditorAtlasTile>;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const cols = grid[0]?.length ?? 0;
  const rows = grid.length;
  const cell = Math.max(
    2,
    Math.min(
      9,
      Math.floor(150 / Math.max(1, cols)),
      Math.floor(104 / Math.max(1, rows)),
    ),
  );
  const w = cols * cell;
  const h = rows * cell;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);
    if (!atlasImg) return;
    ctx.imageSmoothingEnabled = false;
    for (let r = 0; r < rows; r++) {
      const row = grid[r];
      for (let col = 0; col < row.length; col++) {
        const name = row[col];
        if (!name) continue;
        const t = tileByName.get(name);
        if (!t) continue;
        const dw = Math.max(1, t.natWCells) * cell;
        const dh = Math.max(1, t.natHCells) * cell;
        const dx = (col - t.anchorXCells) * cell;
        const dy = (r - t.anchorYCells) * cell;
        ctx.drawImage(atlasImg, t.x, t.y, t.w, t.h, dx, dy, dw, dh);
      }
    }
  }, [grid, atlasImg, tileByName, cell, w, h, rows]);

  if (w === 0 || h === 0) {
    return <div className="rm-preview-empty">empty</div>;
  }
  return (
    <canvas
      ref={ref}
      width={w}
      height={h}
      className="rm-preview-canvas"
      style={{ width: w, height: h }}
    />
  );
});
