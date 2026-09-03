// The visual constellation editor.
//
// A constellation is the one part of a save that is a picture rather than
// a number, and typing coordinates into a form to change a picture is a
// bad joke. So this draws the chart and lets you move it.
//
// Three things shape the layout:
//
// **One view, always the real one.** The canvas uses the viewer's own
// renderer, so what you see while dragging is what the game will draw.
//
// **Tools, not modifier keys.** Adding, moving, joining and erasing are
// four buttons, because a hidden modifier gives no clue that joining
// stars is even possible and no feedback when it misses.
//
// **The inspector sits beside the canvas**, not under it. A star's color
// and size are judged by looking at the star, so changing them must not
// scroll it off screen.
//
// Coordinates match the file: x increases to the left, y downward, and
// both span roughly -1.35 to 1.35. `toScreen` from the viewer is the one
// place the axis flip lives.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Eraser, Link2, MousePointer2, Plus, Scan, Trash2 } from "lucide-react";

import type { Constellation, ConstellationStar } from "../../../lib/commands";
import {
  ConstellationScene,
  GAME_FRAME_WIDTH,
  frameOf,
  markRadius,
  spreadOf,
  toScreen,
  viewBox,
  type View,
} from "../charts/ConstellationView";
import { SectionHead } from "./fields";

/** The file has room for this many; the game's own charts use far fewer. */
const MAX_STARS = 45;
const MAX_LINES = 90;

/** How far out a star may be dragged. The game's charts stay well inside. */
const LIMIT = 2.5;

/**
 * How far the pointer must travel before a click becomes a drag.
 *
 * A pointer drifts a pixel or two between press and release, and without
 * a threshold every one of those pixels is written to the save just for
 * selecting a star.
 */
const DRAG_THRESHOLD_PX = 4;

/**
 * Smallest grab area, as a fraction of the frame's height.
 *
 * A star can be drawn a pixel wide, and one that small still has to be
 * clickable. Expressed against the frame rather than in view units so it
 * stays the same size on screen however the frame is zoomed.
 */
const MIN_HIT = 0.028;

/** What a click on the canvas does. */
type Tool = "move" | "add" | "join" | "erase";

const TOOLS: { id: Tool; label: string; hint: string; Icon: typeof Plus }[] = [
  {
    id: "move",
    label: "Move",
    hint: "Drag a star to move it",
    Icon: MousePointer2,
  },
  { id: "add", label: "Add", hint: "Click the sky to add a star", Icon: Plus },
  {
    id: "join",
    label: "Join",
    hint: "Click two stars to join or unjoin them",
    Icon: Link2,
  },
  {
    id: "erase",
    label: "Erase",
    hint: "Click a star or a join to remove it",
    Icon: Eraser,
  },
];

/**
 * A new star, in the game's own livery.
 *
 * White core, dim green halo, no rings: the ordinary star that every
 * observed constellation is made almost entirely of. Starting from
 * anything else would mean every added star needed correcting.
 */
function newStar(x: number, y: number): ConstellationStar {
  return {
    kind: 0,
    x,
    y,
    size: 1,
    red: 1,
    green: 1,
    blue: 1,
    alpha: 1,
    haloRed: 0.12,
    haloGreen: 0.42,
    haloBlue: 0,
    haloAlpha: 1,
    canisRing: false,
    fidelisRing: false,
    unknown: 0,
  };
}

/** An empty chart, for a save that has never finished the Cosmic Ocean. */
const EMPTY: Constellation = {
  stars: [],
  lines: [],
  scale: 1,
  lineRedIntensity: 0,
};

export function ConstellationEditor({
  value,
  original,
  editable,
  onChange,
}: {
  value: Constellation | null;
  original: Constellation | null;
  /** False when this build cannot locate the block in this save's version. */
  editable: boolean;
  onChange: (next: Constellation | null) => void;
}) {
  if (!editable) {
    return (
      <>
        <SectionHead title="Constellation" />
        <p className="ed-note">
          This build cannot locate the constellation in a save of this version,
          so it will not risk writing over the wrong bytes. Everything else on
          this save is still editable.
        </p>
      </>
    );
  }
  return (
    <Editor chart={value ?? EMPTY} original={original} onChange={onChange} />
  );
}

function Editor({
  chart,
  original,
  onChange,
}: {
  chart: Constellation;
  original: Constellation | null;
  onChange: (next: Constellation | null) => void;
}) {
  const [tool, setTool] = useState<Tool>("move");
  const [selected, setSelected] = useState<number | null>(null);
  /** First star of a join in progress. */
  const [joinFrom, setJoinFrom] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  /** The star under the pointer, and where the press started. */
  const dragging = useRef<{
    index: number;
    fromX: number;
    fromY: number;
    moved: boolean;
  } | null>(null);

  // The game's own frame, not one fitted to the stars: fitting would
  // normalise `scale` away, showing an identical picture at 0.1 and at
  // 3.6. `Fit` is there for when a chart is pushed out of sight.
  //
  // Held in state rather than derived so it does not breathe in and out
  // while a star is being dragged.
  const [view, setView] = useState<View>(() => gameFrame());

  const changed = useMemo(
    () => JSON.stringify(chart) !== JSON.stringify(original ?? EMPTY),
    [chart, original],
  );

  const update = useCallback(
    (patch: Partial<Constellation>) => onChange({ ...chart, ...patch }),
    [chart, onChange],
  );

  const setStar = useCallback(
    (index: number, patch: Partial<ConstellationStar>) => {
      const stars = chart.stars.slice();
      stars[index] = { ...stars[index], ...patch };
      update({ stars });
    },
    [chart.stars, update],
  );

  /**
   * Turns a pointer position into stored coordinates.
   *
   * Via the SVG's own transform rather than the element's box. The canvas
   * carries `preserveAspectRatio` and a max height, so on a short window
   * the box is wider than the drawing and the picture is pillarboxed
   * inside it. Mapping against the box would then place every click and
   * drag off to one side.
   */
  const toStored = useCallback(
    (event: { clientX: number; clientY: number }) => {
      const svg = svgRef.current;
      const screenToView = svg?.getScreenCTM()?.inverse();
      if (!svg || !screenToView) return null;
      const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(
        screenToView,
      );
      // The inverse of `toScreen`: undo the axis flip and the spread.
      const spread = spreadOf(chart.scale);
      return { x: -point.x / spread, y: point.y / spread };
    },
    [chart.scale],
  );

  // Dragging listens on the window so the pointer can leave the canvas
  // mid-drag without the star sticking to the edge.
  useEffect(() => {
    const move = (event: PointerEvent) => {
      const drag = dragging.current;
      if (!drag) return;
      // Nothing moves until the pointer has genuinely travelled. A press
      // and release in the same place is a selection, not a nudge.
      if (!drag.moved) {
        const far =
          Math.hypot(event.clientX - drag.fromX, event.clientY - drag.fromY) >
          DRAG_THRESHOLD_PX;
        if (!far) return;
        drag.moved = true;
      }
      const at = toStored(event);
      if (!at) return;
      setStar(drag.index, { x: clamp(at.x), y: clamp(at.y) });
    };
    const up = () => {
      dragging.current = null;
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [setStar, toStored]);

  const removeStar = useCallback(
    (index: number) => {
      const stars = chart.stars.filter((_, i) => i !== index);
      // Joins are stored as star indices, so removing a star renumbers
      // every join past it. Dropping the ones that touched it and
      // shifting the rest is what keeps the file self-consistent.
      const lines = chart.lines
        .filter((line) => line.from !== index && line.to !== index)
        .map((line) => ({
          from: line.from > index ? line.from - 1 : line.from,
          to: line.to > index ? line.to - 1 : line.to,
        }));
      update({ stars, lines });
      setSelected(null);
      setJoinFrom(null);
    },
    [chart, update],
  );

  const toggleJoin = useCallback(
    (a: number, b: number) => {
      if (a === b) return;
      const existing = chart.lines.findIndex(
        (line) =>
          (line.from === a && line.to === b) ||
          (line.from === b && line.to === a),
      );
      if (existing >= 0) {
        update({ lines: chart.lines.filter((_, i) => i !== existing) });
      } else if (chart.lines.length < MAX_LINES) {
        update({ lines: [...chart.lines, { from: a, to: b }] });
      }
    },
    [chart.lines, update],
  );

  /** A click on a star, dispatched by the active tool. */
  const onStarDown = (index: number, event: React.PointerEvent) => {
    event.stopPropagation();
    setSelected(index);
    switch (tool) {
      case "move":
        dragging.current = {
          index,
          fromX: event.clientX,
          fromY: event.clientY,
          moved: false,
        };
        break;
      case "join":
        if (joinFrom === null) {
          setJoinFrom(index);
        } else {
          toggleJoin(joinFrom, index);
          setJoinFrom(null);
        }
        break;
      case "erase":
        removeStar(index);
        break;
      case "add":
        // Nothing: adding happens on the sky, and a star is not sky.
        break;
    }
  };

  /** A click on the sky. */
  const onSkyDown = (event: React.PointerEvent) => {
    if (tool === "join") {
      // Clicking away abandons a half-made join rather than leaving it
      // armed to catch the next star you meant only to look at.
      setJoinFrom(null);
      return;
    }
    if (tool !== "add") return;
    if (chart.stars.length >= MAX_STARS) return;
    const at = toStored(event);
    if (!at) return;
    update({ stars: [...chart.stars, newStar(clamp(at.x), clamp(at.y))] });
    setSelected(chart.stars.length);
  };

  const star = selected === null ? null : chart.stars[selected];
  const activeTool = TOOLS.find((entry) => entry.id === tool);

  return (
    <>
      <SectionHead
        title="Constellation"
        aside={
          <div className="ed-head-actions">
            <button
              type="button"
              className="saves-btn"
              title="Frame the stars"
              onClick={() => setView(fitTo(chart.stars, chart.scale))}
            >
              <Scan size={14} aria-hidden="true" /> Fit
            </button>
            <button
              type="button"
              className="saves-btn"
              disabled={chart.stars.length === 0}
              onClick={() => {
                onChange({ ...chart, stars: [], lines: [] });
                setSelected(null);
                setJoinFrom(null);
              }}
            >
              <Trash2 size={14} aria-hidden="true" /> Clear
            </button>
            {changed && (
              <button
                type="button"
                className="saves-btn"
                onClick={() => {
                  onChange(original);
                  setSelected(null);
                  setJoinFrom(null);
                }}
              >
                Revert chart
              </button>
            )}
          </div>
        }
      />

      <div className="ed-const">
        <div className="ed-const-main">
          <div className="ed-toolbar" role="group" aria-label="Tool">
            <div className="ed-segmented">
              {TOOLS.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  className={tool === entry.id ? "on" : undefined}
                  aria-pressed={tool === entry.id}
                  title={entry.hint}
                  onClick={() => {
                    setTool(entry.id);
                    setJoinFrom(null);
                  }}
                >
                  <entry.Icon size={13} aria-hidden="true" /> {entry.label}
                </button>
              ))}
            </div>
            <span className="ed-toolbar-count">
              {chart.stars.length} {chart.stars.length === 1 ? "star" : "stars"}
              , {chart.lines.length}{" "}
              {chart.lines.length === 1 ? "join" : "joins"}
            </span>
          </div>

          <div className="ed-canvas-frame">
            <svg
              ref={svgRef}
              className={`ed-canvas tool-${tool}`}
              viewBox={viewBox(view)}
              preserveAspectRatio="xMidYMid meet"
              role="application"
              aria-label="Constellation editor"
              tabIndex={0}
              onKeyDown={(e) => {
                if (
                  selected !== null &&
                  (e.key === "Delete" || e.key === "Backspace")
                ) {
                  e.preventDefault();
                  removeStar(selected);
                }
              }}
              onPointerDown={onSkyDown}
            >
              {/* The real thing, same renderer as the viewer. */}
              <ConstellationScene constellation={chart} view={view} />

              {/* Handles on top. Joins get their own hit targets so the
                  eraser can take one without taking a star. */}
              <g className="ed-handles">
                {chart.lines.map((line, index) => {
                  const from = chart.stars[line.from];
                  const to = chart.stars[line.to];
                  if (!from || !to) return null;
                  const a = toScreen(from, chart.scale);
                  const b = toScreen(to, chart.scale);
                  return (
                    <line
                      key={index}
                      className="ed-join-hit"
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      onPointerDown={(e) => {
                        if (tool !== "erase") return;
                        e.stopPropagation();
                        update({
                          lines: chart.lines.filter((_, i) => i !== index),
                        });
                      }}
                    />
                  );
                })}

                {chart.stars.map((s, index) => {
                  const { x, y } = toScreen(s, chart.scale);
                  const isSelected = selected === index;
                  const isJoinFrom = joinFrom === index;
                  // Both the grab area and the ring follow the mark, so a
                  // star drawn large is easy to hit and a tiny one still
                  // has a target big enough for a mouse.
                  const mark = markRadius(s, view.scale);
                  const hit = Math.max(MIN_HIT * view.viewHeight, mark * 1.1);
                  const ring = Math.max(hit * 0.85, mark * 1.2);
                  // A star sized to zero draws nothing at all in game, so
                  // the picture shows nothing. It still exists in the
                  // file and still has to be selectable, so the editor
                  // marks its place with an outline that is plainly a
                  // handle rather than a star.
                  const invisible = mark <= 0;
                  return (
                    <g
                      key={index}
                      className={`ed-star${isSelected ? " on" : ""}`}
                      onPointerDown={(e) => onStarDown(index, e)}
                    >
                      <circle cx={x} cy={y} r={hit} className="ed-star-hit" />
                      {invisible && (
                        <circle
                          cx={x}
                          cy={y}
                          r={hit * 0.5}
                          className="ed-star-ghost"
                        />
                      )}
                      {(isSelected || isJoinFrom) && (
                        <circle
                          cx={x}
                          cy={y}
                          r={ring}
                          className={`ed-star-ring${isJoinFrom ? " joining" : ""}`}
                        />
                      )}
                      <text
                        x={x}
                        y={y - ring - 0.012 * view.viewHeight}
                        className="ed-star-label"
                        style={{ fontSize: 0.028 * view.viewHeight }}
                      >
                        {index + 1}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>

          <p className="ed-note">
            {activeTool?.hint}
            {chart.stars.length >= MAX_STARS &&
              ` - at the file's limit of ${MAX_STARS} stars`}
            {tool === "join" &&
              joinFrom !== null &&
              ` - star ${joinFrom + 1} picked, now click another`}
          </p>
        </div>

        <aside className="ed-const-side">
          <h4 className="ed-side-head">Settings</h4>
          <SliderField
            label="Scale"
            value={chart.scale}
            min={0.1}
            max={4}
            step={0.01}
            onChange={(scale) => update({ scale })}
            hint="How far apart the stars are. Default: ~3.5."
          />
          <SliderField
            label="Join color"
            value={chart.lineRedIntensity}
            min={0}
            max={1}
            step={0.01}
            onChange={(lineRedIntensity) => update({ lineRedIntensity })}
            hint="From white to red."
          />

          {star && selected !== null ? (
            <StarInspector
              index={selected}
              star={star}
              onChange={(patch) => setStar(selected, patch)}
              onRemove={() => removeStar(selected)}
            />
          ) : (
            <p className="ed-note ed-side-empty">
              Click a star to change its settings.
            </p>
          )}
        </aside>
      </div>
    </>
  );
}

/** The panel for one selected star. */
function StarInspector({
  index,
  star,
  onChange,
  onRemove,
}: {
  index: number;
  star: ConstellationStar;
  onChange: (patch: Partial<ConstellationStar>) => void;
  onRemove: () => void;
}) {
  return (
    <section className="ed-inspector">
      <header>
        <h4>Star {index + 1}</h4>
        <button
          type="button"
          className="ed-icon-btn"
          aria-label={`Remove star ${index + 1}`}
          title="Remove this star"
          onClick={onRemove}
        >
          <Trash2 size={14} aria-hidden="true" />
        </button>
      </header>

      <SliderField
        label="Size"
        value={star.size}
        min={0}
        max={4}
        step={0.01}
        onChange={(size) => onChange({ size })}
      />
      <SliderField
        label="Kind"
        value={star.kind}
        min={0}
        max={2}
        step={1}
        onChange={(kind) => onChange({ kind })}
      />
      <ColorField
        label="Star"
        rgb={[star.red, star.green, star.blue]}
        alpha={star.alpha}
        onChange={([red, green, blue], alpha) =>
          onChange({ red, green, blue, alpha })
        }
      />
      <ColorField
        label="Halo"
        rgb={[star.haloRed, star.haloGreen, star.haloBlue]}
        alpha={star.haloAlpha}
        onChange={([haloRed, haloGreen, haloBlue], haloAlpha) =>
          onChange({ haloRed, haloGreen, haloBlue, haloAlpha })
        }
      />

      <label className="ed-check">
        <input
          type="checkbox"
          checked={star.canisRing}
          onChange={(e) => onChange({ canisRing: e.target.checked })}
        />
        <span className="ed-check-body">
          <span className="ed-check-label">Canis ring</span>
        </span>
      </label>
      <label className="ed-check">
        <input
          type="checkbox"
          checked={star.fidelisRing}
          onChange={(e) => onChange({ fidelisRing: e.target.checked })}
        />
        <span className="ed-check-body">
          <span className="ed-check-label">Fidelis ring</span>
        </span>
      </label>
    </section>
  );
}

/**
 * A float with a slider and the number beside it.
 *
 * `min` and `max` are what the game's own charts use, not a limit: the
 * range widens to include whatever the save holds. It has to, because a
 * range input reports its *clamped* value the moment it is touched - a
 * chart stored at 3.6 against a max of 3 would be rewritten to 3 by
 * anyone who nudged the control.
 */
function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  hint,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
  hint?: string;
}) {
  const ref = useNoWheel();
  const safe = Number.isFinite(value) ? value : min;
  const lo = Math.min(min, safe);
  const hi = Math.max(max, safe);
  const beyond = safe > max || safe < min;

  return (
    <div className="ed-field">
      <label>{label}</label>
      <div className="ed-slider">
        <input
          ref={ref}
          type="range"
          min={lo}
          max={hi}
          step={step}
          value={safe}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={label}
        />
        <span>{step >= 1 ? safe : safe.toFixed(2)}</span>
      </div>
      {hint && <p className="ed-hint">{hint}</p>}
      {beyond && (
        <p className="ed-hint">
          This save holds a value outside the expected range so the slider has
          been widened to reach it.
        </p>
      )}
    </div>
  );
}

/**
 * Keeps a scroll gesture from editing a value.
 *
 * A wheel over a range input can change it, turning "scroll down to see
 * the rings" into "rewrite this star's size". Preventing the default
 * stops the scroll too, so the gesture is passed to the panel instead.
 *
 * The listener must be attached natively: React registers `wheel`
 * passively, and a passive listener cannot call `preventDefault`.
 */
function useNoWheel() {
  const ref = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const scroller = el.closest<HTMLElement>(".ed-const-side, .ed-panel");
      scroller?.scrollBy({ top: event.deltaY });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);
  return ref;
}

/**
 * A color, stored as three floats.
 *
 * The native picker works in 8-bit channels, so a value round-trips as
 * n/255 rather than exactly what was there. That only matters for a
 * color the user actually touched, and the alternative is three number
 * boxes nobody can read as a color.
 */
function ColorField({
  label,
  rgb,
  alpha,
  onChange,
  hint,
}: {
  label: string;
  rgb: [number, number, number];
  alpha: number;
  onChange: (rgb: [number, number, number], alpha: number) => void;
  hint?: string;
}) {
  const alphaRef = useNoWheel();
  return (
    <div className="ed-field">
      <label>{label}</label>
      <div className="ed-color">
        <input
          type="color"
          value={toHex(rgb)}
          aria-label={label}
          onChange={(e) => onChange(fromHex(e.target.value), alpha)}
        />
        <input
          ref={alphaRef}
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={clampTo(alpha, 0, 1)}
          aria-label={`${label} opacity`}
          onChange={(e) => onChange(rgb, Number(e.target.value))}
        />
        <span>{Math.round(alpha * 100)}%</span>
      </div>
      {hint && <p className="ed-hint">{hint}</p>}
    </div>
  );
}

function toHex([r, g, b]: [number, number, number]): string {
  const part = (v: number) =>
    Math.round(clampTo(v, 0, 1) * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${part(r)}${part(g)}${part(b)}`;
}

function fromHex(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

function clamp(value: number): number {
  return clampTo(value, -LIMIT, LIMIT);
}

function clampTo(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

/** The game's own frame, centred on the origin. */
export function gameFrame(): View {
  return frameOf(0, 0, (GAME_FRAME_WIDTH * 9) / 16);
}

/**
 * Frames the stars, with room to spare.
 *
 * Deliberately looser than the viewer's fit: this one has to leave empty
 * sky to drop new stars into, and a frame drawn tight around the existing
 * chart gives you nowhere to put them. Never smaller than the game's own
 * frame, so fitting a tight cluster does not zoom in past what the game
 * would ever show.
 */
export function fitTo(stars: { x: number; y: number }[], scale: number): View {
  const frame = gameFrame();
  if (stars.length === 0) return frame;
  const points = stars.map((star) => toScreen(star, scale));
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const centerX = (Math.min(...xs) + Math.max(...xs)) / 2;
  const centerY = (Math.min(...ys) + Math.max(...ys)) / 2;
  const spanX = (Math.max(...xs) - Math.min(...xs)) * 1.4;
  const spanY = (Math.max(...ys) - Math.min(...ys)) * 1.4;
  const height = Math.max(frame.viewHeight, spanY, spanX / (16 / 9));
  return frameOf(centerX, centerY, height);
}
