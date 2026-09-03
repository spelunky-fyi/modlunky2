import { describe, expect, it } from "vitest";
import { forEachStrokeCell } from "./strokeLine";

function cells(r0: number, c0: number, r1: number, c1: number) {
  const out: Array<[number, number]> = [];
  forEachStrokeCell(r0, c0, r1, c1, (row, col) => out.push([row, col]));
  return out;
}

describe("forEachStrokeCell", () => {
  it("visits nothing when the pointer hasn't left the cell", () => {
    expect(cells(3, 4, 3, 4)).toEqual([]);
  });

  it("visits only the destination for an adjacent cell", () => {
    expect(cells(3, 4, 3, 5)).toEqual([[3, 5]]);
  });

  it("fills the gap left by a fast horizontal drag", () => {
    expect(cells(2, 0, 2, 4)).toEqual([
      [2, 1],
      [2, 2],
      [2, 3],
      [2, 4],
    ]);
  });

  it("fills the gap left by a fast vertical drag", () => {
    expect(cells(0, 7, 3, 7)).toEqual([
      [1, 7],
      [2, 7],
      [3, 7],
    ]);
  });

  // The reported bug: bottom-left to top-right in one fast flick left a
  // diagonal of isolated tiles.
  it("leaves no gaps on a diagonal", () => {
    expect(cells(6, 0, 0, 6)).toEqual([
      [5, 1],
      [4, 2],
      [3, 3],
      [2, 4],
      [1, 5],
      [0, 6],
    ]);
  });

  it("walks backwards just as well", () => {
    expect(cells(0, 6, 6, 0)).toEqual([
      [1, 5],
      [2, 4],
      [3, 3],
      [4, 2],
      [5, 1],
      [6, 0],
    ]);
  });

  it("steps one cell at a time on a shallow line", () => {
    const path = cells(0, 0, 2, 9);
    // Every step moves to a 4- or 8-neighbour: no jumps.
    for (let i = 1; i < path.length; i++) {
      const [pr, pc] = path[i - 1];
      const [r, c] = path[i];
      expect(Math.abs(r - pr)).toBeLessThanOrEqual(1);
      expect(Math.abs(c - pc)).toBeLessThanOrEqual(1);
    }
    expect(path.at(-1)).toEqual([2, 9]);
  });

  it("never revisits a cell", () => {
    const path = cells(0, 0, 11, 29);
    const seen = new Set(path.map(([r, c]) => `${r},${c}`));
    expect(seen.size).toBe(path.length);
  });

  it("reaches the end from negative (off-grid) coords", () => {
    const path = cells(-3, -3, 2, 2);
    expect(path.at(-1)).toEqual([2, 2]);
    expect(path).toHaveLength(5);
  });

  it("stays bounded when the pointer jumps in from far away", () => {
    const path = cells(0, 0, 0, 100000);
    expect(path.length).toBeLessThanOrEqual(4096);
  });
});
