// Resize modal for a custom level's grid. Per-side controls: each edge has
// a + and a - button that grows or shrinks that specific side by one room.
// No anchor concept; users directly say "add a room to the right" or
// "crop a row off the top." A small live preview shows the new dimensions
// alongside the original for reference.

import { useState } from "react";
import { Minus, Plus } from "lucide-react";
import { Modal } from "../shared/Modal";
import "./ResizeLevelModal.css";

/** Per-side deltas in units of rooms. Positive grows, negative shrinks. */
export interface ResizePlan {
  padTopRooms: number;
  padBottomRooms: number;
  padLeftRooms: number;
  padRightRooms: number;
}

interface Props {
  currentWidthRooms: number;
  currentHeightRooms: number;
  onClose: () => void;
  onApply: (plan: ResizePlan) => void;
}

const MIN_ROOMS = 1;
const MAX_ROOMS_W = 18;
const MAX_ROOMS_H = 15;

type Side = "top" | "bottom" | "left" | "right";

export function ResizeLevelModal({
  currentWidthRooms,
  currentHeightRooms,
  onClose,
  onApply,
}: Props) {
  // Per-side deltas start at zero. Each click adjusts by 1 room. The
  // resulting dimensions are the sums; we enforce min/max range on the
  // buttons so out-of-range deltas can't be entered.
  const [top, setTop] = useState(0);
  const [bottom, setBottom] = useState(0);
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(0);

  const newW = currentWidthRooms + left + right;
  const newH = currentHeightRooms + top + bottom;
  const noChange = top === 0 && bottom === 0 && left === 0 && right === 0;
  const isShrinking = top < 0 || bottom < 0 || left < 0 || right < 0;

  const canGrow = (side: Side): boolean => {
    switch (side) {
      case "top":
      case "bottom":
        return newH + 1 <= MAX_ROOMS_H;
      case "left":
      case "right":
        return newW + 1 <= MAX_ROOMS_W;
    }
  };
  const canShrink = (side: Side): boolean => {
    switch (side) {
      case "top":
      case "bottom":
        return newH - 1 >= MIN_ROOMS;
      case "left":
      case "right":
        return newW - 1 >= MIN_ROOMS;
    }
  };

  const bump = (side: Side, dir: 1 | -1) => {
    switch (side) {
      case "top":
        setTop((v) => v + dir);
        break;
      case "bottom":
        setBottom((v) => v + dir);
        break;
      case "left":
        setLeft((v) => v + dir);
        break;
      case "right":
        setRight((v) => v + dir);
        break;
    }
  };

  const reset = () => {
    setTop(0);
    setBottom(0);
    setLeft(0);
    setRight(0);
  };

  const handleApply = () => {
    if (noChange) return;
    onApply({
      padTopRooms: top,
      padBottomRooms: bottom,
      padLeftRooms: left,
      padRightRooms: right,
    });
  };

  const formatDelta = (v: number): string =>
    v === 0 ? "0" : v > 0 ? `+${v}` : `${v}`;

  return (
    <Modal
      open
      onClose={onClose}
      title="Resize level"
      size="md"
      footer={
        <div className="resize-modal-footer">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={reset}
            disabled={noChange}
          >
            Reset
          </button>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleApply}
            disabled={noChange}
          >
            Apply
          </button>
        </div>
      }
    >
      <div className="resize-modal">
        <p className="resize-modal-hint">
          Grow or shrink each side of the level. Plus adds a room; minus
          crops one. Each side works independently, so you can add rooms
          on the right while cropping some off the top.
        </p>

        <div className="resize-modal-grid">
          {/* Top edge controls: horizontal +/- row */}
          <div className="resize-modal-edge horizontal top">
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("top", 1)}
              disabled={!canGrow("top")}
              aria-label="Add row to top"
              title="Add a room row to the top"
            >
              <Plus size={14} aria-hidden="true" />
            </button>
            <span className="resize-modal-delta">{formatDelta(top)}</span>
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("top", -1)}
              disabled={!canShrink("top")}
              aria-label="Crop row from top"
              title="Crop a room row from the top"
            >
              <Minus size={14} aria-hidden="true" />
            </button>
          </div>

          {/* Left edge controls: vertical +/- column */}
          <div className="resize-modal-edge vertical left">
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("left", 1)}
              disabled={!canGrow("left")}
              aria-label="Add column to left"
              title="Add a room column to the left"
            >
              <Plus size={14} aria-hidden="true" />
            </button>
            <span className="resize-modal-delta">{formatDelta(left)}</span>
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("left", -1)}
              disabled={!canShrink("left")}
              aria-label="Crop column from left"
              title="Crop a room column from the left"
            >
              <Minus size={14} aria-hidden="true" />
            </button>
          </div>

          <div className="resize-modal-preview">
            <div className="resize-modal-preview-size">
              {newW} x {newH}
            </div>
            <div className="resize-modal-preview-orig">
              was {currentWidthRooms} x {currentHeightRooms}
            </div>
            <div className="resize-modal-preview-tiles">
              {newW * 10} x {newH * 8} tiles
            </div>
          </div>

          {/* Right edge controls: vertical +/- column */}
          <div className="resize-modal-edge vertical right">
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("right", 1)}
              disabled={!canGrow("right")}
              aria-label="Add column to right"
              title="Add a room column to the right"
            >
              <Plus size={14} aria-hidden="true" />
            </button>
            <span className="resize-modal-delta">{formatDelta(right)}</span>
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("right", -1)}
              disabled={!canShrink("right")}
              aria-label="Crop column from right"
              title="Crop a room column from the right"
            >
              <Minus size={14} aria-hidden="true" />
            </button>
          </div>

          {/* Bottom edge controls: horizontal +/- row */}
          <div className="resize-modal-edge horizontal bottom">
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("bottom", 1)}
              disabled={!canGrow("bottom")}
              aria-label="Add row to bottom"
              title="Add a room row to the bottom"
            >
              <Plus size={14} aria-hidden="true" />
            </button>
            <span className="resize-modal-delta">{formatDelta(bottom)}</span>
            <button
              type="button"
              className="resize-modal-btn"
              onClick={() => bump("bottom", -1)}
              disabled={!canShrink("bottom")}
              aria-label="Crop row from bottom"
              title="Crop a room row from the bottom"
            >
              <Minus size={14} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Always rendered so hiding/showing the message doesn't reposition
            the footer buttons out from under the user's cursor. */}
        <div
          className="resize-modal-warn"
          data-visible={isShrinking ? "true" : "false"}
        >
          Shrinking discards the tiles in the cropped rows or columns.
        </div>
      </div>
    </Modal>
  );
}
