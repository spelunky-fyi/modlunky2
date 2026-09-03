// Draws a Cosmic Ocean constellation the way the game does.
//
// This one is not a chart, so it does not follow the chart rules: it is a
// picture of the save's own data, and its colors come from the file
// rather than from a palette. Using the app's chart hue here would
// misrepresent what is actually stored.
//
// The save gives each star a color and a separate halo color. In the
// game's own constellations the star is white and the halo is a dim green
// (around 0.12, 0.42, 0), and what you see is a *white* star with a faint
// green glow around it. Drawing the halo as a flat disc gets that badly
// wrong: it reads as a green blob with a white speck in it. The halo has
// to fall off to nothing, which is what the per-star gradient below is
// for.
//
// The stored colors are not the whole story, though. Each star also has
// a `kind`, and the game draws some kinds as an entirely different mark.
// A star with `kind = 2` renders as a large magenta four-pointed sparkle
// even though its stored colors are the same white-and-green as every
// other star, so the kind must select a sprite that supplies its own
// appearance. `STAR_KINDS` below is what is actually known, from
// comparing real saves against screenshots of them; see its docs for
// which kinds those are.
//
// Coordinate space: the save stores x increasing to the *left* and y
// increasing downward, spanning about -1.35 to 1.35 on both axes. Negating
// x is what turns stored coordinates into screen ones. That was confirmed
// by plotting a real five-star chart against a screenshot of the same save
// in game.

import { useId, useMemo } from "react";
import type { Constellation, ConstellationStar } from "../../../lib/commands";
import "./charts.css";

/**
 * How much empty sky to leave around the stars, as a fraction of the
 * chart's own size.
 *
 * The game leaves a comparable margin: in a screenshot of a real
 * five-star chart the stars spanned about 78% of the frame.
 */
const MARGIN = 0.14;

/**
 * Smallest frame to draw, in stored units.
 *
 * A constellation of two nearby stars would otherwise be magnified until
 * they filled the card, which reads as a much bigger chart than it is.
 */
const MIN_EXTENT = 0.6;

/** The game draws the chart in a 16:9 window. */
const ASPECT = 16 / 9;

/**
 * Where the two rings sit, as multiples of the core radius.
 *
 * In game they hug the star: thick bands just outside the core, close
 * enough that a kind-2 sparkle's points reach past them. Measured off
 * screenshots of a save wearing both rings, at size 4 and again at size 1.
 */
const CANIS_RING = 1.45;
const FIDELIS_RING = 1.85;
/** Ring thickness, also relative to the core, so they read as bands. */
const RING_WEIGHT = 0.3;

/** How one kind of star is drawn. */
interface StarStyle {
  shape: "orb" | "sparkle";
  /**
   * Color the sprite multiplies the star's own color by, or null for a
   * sprite that adds no color of its own.
   */
  tint: [number, number, number] | null;
  /** Size relative to an ordinary star of the same stored size. */
  weight: number;
  /** Spike length, as a multiple of the core radius. Zero for an orb. */
  spike: number;
}

/**
 * What `kind` selects.
 *
 * Established by setting all nine kinds on one save and looking at the
 * result in game, twice - once with the stars left white and once with
 * every star set to pure red:
 *
 * - **0** is a plain round orb with no spikes.
 * - **1** is a four-pointed sparkle that adds no color: white stars stay
 *   white. Its points are short and subtle, and the whole mark is only a
 *   little larger than an orb of the same size.
 * - **2 and up** are a *different, larger* sparkle with a magenta tint:
 *   longer points and a heavier core. 3 through 8 are indistinguishable
 *   from 2, so either one sprite serves them all or the rest are
 *   placeholders.
 *
 * The tint *multiplies* the star's own color rather than replacing it,
 * which is why a white star of kind 2 comes out magenta (1,1,1 x 1,0,1)
 * while a red one stays red (1,0,0 x 1,0,1).
 */
function styleFor(star: ConstellationStar): StarStyle {
  if (star.kind <= 0) {
    return { shape: "orb", tint: null, weight: 1, spike: 0 };
  }
  if (star.kind === 1) {
    // Points that barely clear the core: inside the rings, when a star
    // wears them.
    return { shape: "sparkle", tint: null, weight: 1, spike: 1.45 };
  }
  // Points that reach past both rings, which is how a kind-2 star reads
  // as spiky even when ringed.
  return { shape: "sparkle", tint: [1, 0, 1], weight: 1.1, spike: 2.35 };
}

/** Multiplies a stored color by a sprite's tint. */
function tinted(
  rgbValues: [number, number, number],
  tint: [number, number, number] | null,
): [number, number, number] {
  if (!tint) return rgbValues;
  return [
    rgbValues[0] * tint[0],
    rgbValues[1] * tint[1],
    rgbValues[2] * tint[2],
  ];
}

interface ConstellationViewProps {
  constellation: Constellation;
  /** Rendered height in px. Width follows the 16:9 the game draws at. */
  height?: number;
  /** Accessible description; the picture carries no text of its own. */
  label?: string;
}

export function ConstellationView({
  constellation,
  height = 220,
  label,
}: ConstellationViewProps) {
  const { stars, lines } = constellation;

  // Fit the frame to the stars rather than assuming how much of the
  // coordinate space they use. A fixed frame either clips a chart that
  // spreads wider than expected, or strands a small one in the middle of
  // a lot of empty sky, and the game generates both.
  const view = useMemo(
    () => fitView(stars.map((star) => toScreen(star, constellation.scale))),
    [stars, constellation.scale],
  );

  const description =
    label ??
    `A constellation of ${stars.length} star${stars.length === 1 ? "" : "s"}` +
      (lines.length > 0 ? ` joined by ${lines.length} lines.` : ".");

  return (
    <div className="constellation" style={{ height }}>
      <svg
        viewBox={viewBox(view)}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={description}
      >
        <ConstellationScene constellation={constellation} view={view} />
      </svg>
    </div>
  );
}

/**
 * Stored coordinates to screen ones.
 *
 * Stored x grows leftward, hence the negation. The chart's `scale`
 * multiplies the positions: it is how far apart the stars are drawn, not
 * how large they are. Setting it to 0.1 collapses a whole constellation
 * onto a single point, and the game's own charts sit around 3.5.
 */
export function toScreen(
  point: { x: number; y: number },
  scale = 1,
): { x: number; y: number } {
  const spread = spreadOf(scale);
  return { x: -point.x * spread, y: point.y * spread };
}

/** Guards a stored scale that would divide by zero on the way back. */
export function spreadOf(scale: number): number {
  if (!Number.isFinite(scale) || scale <= 0) return MIN_SPREAD;
  return Math.max(MIN_SPREAD, scale);
}

/** Below this the stars are a single point and dragging cannot work. */
const MIN_SPREAD = 0.01;

/**
 * The frame the game draws a constellation in, in scaled units.
 *
 * Calibrated from game-generated charts: their stored positions reach
 * about +/-1.42 and their scale sits between 3.16 and 3.82, and in a
 * screenshot of one such chart the stars spanned roughly 78% of the
 * frame's width. That puts the frame at about 13 units across.
 *
 * Approximate, and only used where the framing itself matters - the
 * editor, which claims to draw what the game will. The gallery fits to
 * its content instead, because there the job is to show a chart legibly
 * rather than to reproduce a game window.
 */
export const GAME_FRAME_WIDTH = 13;

/** The `viewBox` string for a frame. */
export function viewBox(view: View): string {
  return `${view.centerX - view.viewWidth / 2} ${
    view.centerY - view.viewHeight / 2
  } ${view.viewWidth} ${view.viewHeight}`;
}

/**
 * The constellation itself: sky, joins, halos, cores.
 *
 * Split out of [`ConstellationView`] so the editor can draw the same
 * marks inside its own `<svg>` and overlay handles on top. That is what
 * lets the editor show the real thing while you are editing it, instead
 * of making you toggle to a preview to find out what you just made.
 *
 * Takes the frame rather than computing one, because an editor's frame
 * has to stay put while stars move inside it.
 */
export function ConstellationScene({
  constellation,
  view,
}: {
  constellation: Constellation;
  view: View;
}) {
  const gradientId = useId();
  const { stars, lines } = constellation;
  const { viewWidth, viewHeight, centerX, centerY, scale } = view;
  const place = (star: { x: number; y: number }) =>
    toScreen(star, constellation.scale);

  return (
    <>
      <defs>
        {/* The nebula wash the game draws behind the stars. Purely
            decorative, and deliberately dim so the stars carry the eye. */}
        <radialGradient id={`${gradientId}-sky`} cx="50%" cy="50%" r="75%">
          <stop offset="0%" stopColor="#101a2c" />
          <stop offset="55%" stopColor="#0a0f1c" />
          <stop offset="100%" stopColor="#04060c" />
        </radialGradient>
        {/* A small blur on the star core only, so it reads as a light
            source rather than a flat dot. Deliberately not applied to
            the halo: blurring a gradient that already falls off just
            smears its color further out. */}
        <filter
          id={`${gradientId}-core`}
          x="-150%"
          y="-150%"
          width="400%"
          height="400%"
        >
          <feGaussianBlur stdDeviation="0.01" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* One gradient per star, because each carries its own halo
            color. A glow has to fade to nothing at its edge; a flat
            disc of the halo color reads as a colored blob and buries
            the white star inside it. */}
        {stars.map((star, i) => {
          const style = styleFor(star);
          // A sparkle glows its own color; an orb glows the halo color
          // the save stores, which in the game's charts is a dim green.
          const color =
            style.shape === "sparkle"
              ? rgb(...tinted([star.red, star.green, star.blue], style.tint))
              : rgb(star.haloRed, star.haloGreen, star.haloBlue);
          // A sparkle's glow is its most visible part in game, so it
          // carries more of the star's presence than an orb's does.
          const strength =
            clamp01(star.haloAlpha) * (style.shape === "sparkle" ? 1.35 : 1);
          return (
            <radialGradient key={i} id={`${gradientId}-halo-${i}`}>
              <stop
                offset="0%"
                stopColor={color}
                stopOpacity={Math.min(1, 0.55 * strength)}
              />
              <stop
                offset="35%"
                stopColor={color}
                stopOpacity={Math.min(1, 0.22 * strength)}
              />
              <stop
                offset="70%"
                stopColor={color}
                stopOpacity={Math.min(1, 0.06 * strength)}
              />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </radialGradient>
          );
        })}
      </defs>

      <rect
        x={centerX - viewWidth / 2}
        y={centerY - viewHeight / 2}
        width={viewWidth}
        height={viewHeight}
        fill={`url(#${gradientId}-sky)`}
      />

      {/* Lines first, so the stars sit on top of their own joins. */}
      <g className="constellation-lines">
        {lines.map((line, i) => {
          const from = stars[line.from];
          const to = stars[line.to];
          if (!from || !to) return null;
          const a = place(from);
          const b = place(to);
          return (
            <line
              key={`${line.from}-${line.to}-${i}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={lineColor(constellation.lineRedIntensity)}
              strokeWidth={0.0075 * scale}
              strokeLinecap="round"
            />
          );
        })}
      </g>

      {/* Halos first and as their own layer, so a star's glow never
          washes over the neighbour's white core. */}
      <g>
        {stars.map((star, i) => {
          const { x, y } = place(star);
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r={haloRadius(star, scale)}
              fill={`url(#${gradientId}-halo-${i})`}
            />
          );
        })}
      </g>

      <g filter={`url(#${gradientId}-core)`}>
        {stars.map((star, i) => {
          const { x, y } = place(star);
          const style = styleFor(star);
          const radius = coreRadius(star, scale);
          const [cr, cg, cb] = tinted(
            [star.red, star.green, star.blue],
            style.tint,
          );
          const core = rgba(cr, cg, cb, star.alpha);
          return (
            <g key={i}>
              {style.shape === "sparkle" && (
                <path
                  d={sparklePath(x, y, radius * style.spike, radius * 0.55)}
                  fill={core}
                />
              )}
              <circle cx={x} cy={y} r={radius} fill={core} />
              {star.canisRing && (
                <circle
                  cx={x}
                  cy={y}
                  r={radius * CANIS_RING}
                  fill="none"
                  stroke="#e8a24a"
                  strokeWidth={radius * RING_WEIGHT}
                />
              )}
              {star.fidelisRing && (
                <circle
                  cx={x}
                  cy={y}
                  r={radius * FIDELIS_RING}
                  fill="none"
                  stroke="#c8402c"
                  strokeWidth={radius * RING_WEIGHT}
                />
              )}
            </g>
          );
        })}
      </g>
    </>
  );
}

/** The frame to draw a set of points in. */
export interface View {
  viewWidth: number;
  viewHeight: number;
  centerX: number;
  centerY: number;
  /** Frame size relative to a nominal one, so marks keep a constant size
   *  on screen however far the view is zoomed. */
  scale: number;
}

/** A 16:9 frame around `points`, with margin, never smaller than
 *  [`MIN_EXTENT`]. */
/**
 * Frame height that marks are sized against.
 *
 * `View.scale` is a frame's height over this, so a mark drawn at
 * `radius * scale` keeps a constant size on screen however far the view
 * is zoomed in or out.
 */
export const NOMINAL_HEIGHT = 2.1;

/** Builds a frame of a given height, centred on a point. */
export function frameOf(
  centerX: number,
  centerY: number,
  height: number,
): View {
  return {
    viewWidth: height * ASPECT,
    viewHeight: height,
    centerX,
    centerY,
    scale: height / NOMINAL_HEIGHT,
  };
}

export function fitView(points: { x: number; y: number }[]): View {
  const NOMINAL = NOMINAL_HEIGHT;
  if (points.length === 0) {
    return {
      viewWidth: NOMINAL * ASPECT,
      viewHeight: NOMINAL,
      centerX: 0,
      centerY: 0,
      scale: 1,
    };
  }

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const spanX = (maxX - minX) * (1 + MARGIN * 2);
  const spanY = (maxY - minY) * (1 + MARGIN * 2);

  // Grow whichever axis is short until the frame is 16:9, so the chart is
  // never stretched.
  const height = Math.max(MIN_EXTENT, spanY, spanX / ASPECT);
  return {
    viewWidth: height * ASPECT,
    viewHeight: height,
    centerX,
    centerY,
    scale: height / NOMINAL,
  };
}

/**
 * The white orb at a star's centre.
 *
 * Stored sizes hover around 1. This is what carries the star's color, so
 * it is sized to read as the star itself rather than as a dot inside a
 * colored cloud. `scale` keeps it a constant size on screen whatever the
 * frame ended up being.
 */
export function coreRadius(star: ConstellationStar, scale: number): number {
  const size = clampSize(star.size);
  // Deliberately no floor: a size of zero draws nothing, as in game. The
  // editor gives such a star a handle of its own rather than having the
  // picture lie about it.
  if (size <= 0) return 0;
  const weight = styleFor(star).weight;
  return Math.max(0.008, size * 0.035) * weight * scale;
}

/**
 * How far the star's drawn mark reaches, rings and spikes included.
 *
 * The editor sizes its hit target and selection ring from this, so that a
 * star drawn four times normal size gets a grab area to match.
 */
export function markRadius(star: ConstellationStar, scale: number): number {
  const style = styleFor(star);
  const core = coreRadius(star, scale);
  // Half the ring's thickness is drawn outside its radius, so it counts
  // toward how far the mark reaches.
  const reach = Math.max(
    1,
    style.spike,
    star.canisRing ? CANIS_RING + RING_WEIGHT / 2 : 0,
    star.fidelisRing ? FIDELIS_RING + RING_WEIGHT / 2 : 0,
  );
  return core * reach;
}

/** How far the glow reaches. Generous, because it fades to nothing. */
function haloRadius(star: ConstellationStar, scale: number): number {
  return coreRadius(star, scale) * 3;
}

/**
 * A four-pointed sparkle, spikes at up/down/left/right.
 *
 * `outer` is the spike length and `inner` the waist between them; a small
 * waist is what makes the spikes read as thin rays rather than as a
 * diamond.
 */
function sparklePath(
  cx: number,
  cy: number,
  outer: number,
  inner: number,
): string {
  const diagonal = inner * Math.SQRT1_2;
  const points: [number, number][] = [
    [cx, cy - outer],
    [cx + diagonal, cy - diagonal],
    [cx + outer, cy],
    [cx + diagonal, cy + diagonal],
    [cx, cy + outer],
    [cx - diagonal, cy + diagonal],
    [cx - outer, cy],
    [cx - diagonal, cy - diagonal],
  ];
  return `M${points.map(([x, y]) => `${x.toFixed(4)},${y.toFixed(4)}`).join("L")}Z`;
}

/**
 * Guards a stored size.
 *
 * Zero is meaningful and must survive: the game draws nothing at all for
 * it, and a save can hold one. Only a value that is not a number falls
 * back to 1.
 */
function clampSize(size: number): number {
  if (!Number.isFinite(size)) return 1;
  return Math.min(4, Math.max(0, size));
}

/** Clamps a stored 0..1 channel and builds an opaque CSS color. */
function rgb(r: number, g: number, b: number): string {
  const channel = (v: number) => Math.round(clamp01(v) * 255);
  return `rgb(${channel(r)}, ${channel(g)}, ${channel(b)})`;
}

/** Clamps a stored 0..1 channel and builds a CSS color with alpha. */
function rgba(r: number, g: number, b: number, a: number): string {
  const channel = (v: number) => Math.round(clamp01(v) * 255);
  return `rgba(${channel(r)}, ${channel(g)}, ${channel(b)}, ${clamp01(a).toFixed(3)})`;
}

/**
 * The connecting lines, tinted by the save's stored intensity.
 *
 * Zero draws them the usual near-white. The game raises this toward 1 as
 * NPC kills climb, taking the lines pink and then deep red for a
 * Criminalis ending, so the tint is real information rather than styling.
 */
function lineColor(intensity: number): string {
  const t = clamp01(intensity);
  const r = 240;
  const g = Math.round(238 - 150 * t);
  const b = Math.round(216 - 180 * t);
  return `rgba(${r}, ${g}, ${b}, 0.85)`;
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}
