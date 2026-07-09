import { useEffect, useMemo, useRef, useState } from "react";
import { Copy, CopyPlus, SquareArrowOutUpRight, Trash2 } from "lucide-react";
import { Modal } from "../shared/Modal";
import type { EditorAtlas, EditorAtlasTile, VanillaLevelData } from "../../lib/commands";
import "./RoomManagerModal.css";

type PurgeScope = "rooms" | "templates" | "both";

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
  onPurgeComments: (scope: PurgeScope) => void;
}

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
  onPurgeComments,
}: RoomManagerModalProps) {
  const [confirmingPurge, setConfirmingPurge] = useState(false);
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

  const roomCount = templates.reduce((n, t) => n + t.rooms.length, 0);

  const purge = (scope: PurgeScope) => {
    onPurgeComments(scope);
    setConfirmingPurge(false);
  };

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

      <div className="rm-body">
        {templates.length === 0 && (
          <div className="rm-empty">This file has no templates.</div>
        )}
        {templates.map((tpl) => (
          <section className="rm-template" key={tpl.name}>
            <div className="rm-template-head">
              <span className="rm-template-name">{tpl.name}</span>
              <span className="rm-template-count">{tpl.rooms.length}</span>
            </div>
            <CommentInput
              className="rm-template-comment"
              value={tpl.comment}
              placeholder="Template comment"
              onCommit={(c) => onEditTemplateComment(tpl.name, c)}
            />
            {tpl.rooms.length > 0 && (
              <div className="rm-room-grid">
                {tpl.rooms.map((room, idx) => (
                  <div className="rm-room-card" key={idx}>
                    <div className="rm-room-preview-wrap">
                      <button
                        type="button"
                        className="rm-room-jump"
                        title={`Jump to room ${idx}`}
                        onClick={() => onJumpToRoom(tpl.name, idx)}
                      >
                        <RoomFgPreview
                          grid={fgFor(tpl.name, idx)}
                          atlasImg={atlasImg}
                          tileByName={tileByName}
                        />
                        <span className="rm-room-label">
                          room {idx}
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
                        onClick={(e) =>
                          onCopyRoom(tpl.name, idx, e.shiftKey)
                        }
                      >
                        {shiftHeld ? (
                          <CopyPlus size={13} aria-hidden="true" />
                        ) : (
                          <Copy size={13} aria-hidden="true" />
                        )}
                      </button>
                    </div>
                    <CommentInput
                      className="rm-room-comment"
                      value={room.comment}
                      placeholder="comment"
                      onCommit={(c) => onEditRoomComment(tpl.name, idx, c)}
                    />
                  </div>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
    </Modal>
  );
}

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
function RoomFgPreview({
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
}
