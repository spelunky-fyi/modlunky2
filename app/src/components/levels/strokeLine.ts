// Cell path between two sampled pointer positions.
//
// A mousemove reports where the pointer IS, not the path it took to get
// there. Drag a brush fast enough and consecutive samples land several tiles
// apart, so painting only the sampled cell leaves a dotted trail instead of a
// stroke. Walking the line between samples is what makes a drag continuous
// regardless of how fast it moves or how busy the frame was.

/** Upper bound on cells visited in one call. A pointer re-entering the canvas
 *  from far off-screen produces a very long line; the guard keeps that from
 *  becoming an unbounded loop on the paint hot path. Any real level grid is
 *  orders of magnitude smaller. */
const MAX_CELLS = 4096;

/**
 * Visits every cell on the line from (r0, c0) to (r1, c1), EXCLUDING the
 * start and INCLUDING the end. Integer Bresenham, so it never revisits a
 * cell and never leaves a diagonal gap.
 *
 * The start is excluded because it has always just been painted: a stroke
 * paints where it starts, then fills forward from there on each move.
 *
 * Coordinates may sit outside the grid. The path is computed in cell space
 * with no clamping, so callers get the geometrically correct line and drop
 * the cells that fall outside their own bounds -- clamping the endpoints
 * first would bend the line instead.
 */
export function forEachStrokeCell(
  r0: number,
  c0: number,
  r1: number,
  c1: number,
  visit: (row: number, col: number) => void,
): void {
  const dr = Math.abs(r1 - r0);
  const dc = Math.abs(c1 - c0);
  const stepR = r0 < r1 ? 1 : -1;
  const stepC = c0 < c1 ? 1 : -1;
  let err = dc - dr;
  let r = r0;
  let c = c0;
  for (let guard = 0; guard < MAX_CELLS; guard++) {
    if (r === r1 && c === c1) return;
    const e2 = 2 * err;
    if (e2 > -dr) {
      err -= dr;
      c += stepC;
    }
    if (e2 < dc) {
      err += dc;
      r += stepR;
    }
    visit(r, c);
  }
}
