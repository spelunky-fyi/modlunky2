import { describe, expect, it } from "vitest";
import type { ConstellationStar } from "../../../lib/commands";
import {
  coreRadius,
  markRadius,
  spreadOf,
  toScreen,
} from "./ConstellationView";

describe("toScreen", () => {
  // Stored x grows leftward. Confirmed by plotting a real five-star chart
  // against a screenshot of the same save in game.
  it("flips the x axis", () => {
    expect(toScreen({ x: 1, y: 1 })).toEqual({ x: -1, y: 1 });
    expect(toScreen({ x: -0.5, y: 0.25 })).toEqual({ x: 0.5, y: 0.25 });
  });

  // Scale is how far apart the stars are drawn, not how large they are.
  // Setting a chart to 0.1 in game collapses it onto a single point;
  // raising it spreads the same stars across the frame.
  it("spreads the stars by the chart's scale", () => {
    expect(toScreen({ x: 1, y: 2 }, 3)).toEqual({ x: -3, y: 6 });
    expect(toScreen({ x: 1, y: 2 }, 0.5)).toEqual({ x: -0.5, y: 1 });
  });

  it("leaves positions alone at a scale of one", () => {
    expect(toScreen({ x: 0.7, y: -0.3 }, 1)).toEqual({ x: -0.7, y: -0.3 });
  });
});

describe("spreadOf", () => {
  // The inverse is used to turn a pointer position back into a stored
  // coordinate, so a zero would divide by zero and put every dragged star
  // at infinity.
  it("never returns zero", () => {
    expect(spreadOf(0)).toBeGreaterThan(0);
    expect(spreadOf(-5)).toBeGreaterThan(0);
    expect(spreadOf(Number.NaN)).toBeGreaterThan(0);
  });

  it("passes a real scale through", () => {
    // The range the game's own charts sit in.
    expect(spreadOf(3.16)).toBeCloseTo(3.16);
    expect(spreadOf(3.82)).toBeCloseTo(3.82);
  });

  // A star dragged to a screen position and read back has to land where
  // it was put, whatever the scale.
  it("round-trips a position through the spread", () => {
    for (const scale of [0.1, 1, 1.99, 3.6]) {
      const stored = { x: 0.42, y: -0.17 };
      const screen = toScreen(stored, scale);
      const spread = spreadOf(scale);
      expect(-screen.x / spread).toBeCloseTo(stored.x);
      expect(screen.y / spread).toBeCloseTo(stored.y);
    }
  });
});

/** A star with the game's usual livery, overridden per test. */
function star(over: Partial<ConstellationStar> = {}): ConstellationStar {
  return {
    kind: 0,
    x: 0,
    y: 0,
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
    ...over,
  };
}

describe("markRadius", () => {
  // The editor's grab area comes from this. A star drawn four times
  // normal size needs a target to match; a fixed one leaves the biggest
  // stars with the smallest targets, which is exactly backwards.
  it("grows with the star's size", () => {
    const small = markRadius(star({ size: 0.9 }), 1);
    const big = markRadius(star({ size: 4 }), 1);
    expect(big).toBeGreaterThan(small * 3);
  });

  it("is never smaller than the core it wraps", () => {
    for (const kind of [0, 1, 2, 5]) {
      const s = star({ kind, size: 1.2 });
      expect(markRadius(s, 1)).toBeGreaterThanOrEqual(coreRadius(s, 1));
    }
  });

  // Kind 1 and kind 2 are different sprites: 1's points are short and
  // subtle, 2's are longer and the core is heavier.
  it("makes the kind-2 sparkle larger than the kind-1 one", () => {
    const subtle = markRadius(star({ kind: 1 }), 1);
    const bold = markRadius(star({ kind: 2 }), 1);
    expect(bold).toBeGreaterThan(subtle);
    // ...and both reach past a plain orb.
    expect(subtle).toBeGreaterThan(markRadius(star({ kind: 0 }), 1));
  });

  it("treats kinds 3 and up as the same sprite as 2", () => {
    const two = markRadius(star({ kind: 2 }), 1);
    for (const kind of [3, 5, 8]) {
      expect(markRadius(star({ kind }), 1)).toBeCloseTo(two);
    }
  });

  // The rings are drawn outside the core, so they extend what has to be
  // clickable.
  it("reaches past the rings when a star wears them", () => {
    const plain = markRadius(star(), 1);
    expect(markRadius(star({ canisRing: true }), 1)).toBeGreaterThan(plain);
    expect(markRadius(star({ fidelisRing: true }), 1)).toBeGreaterThan(
      markRadius(star({ canisRing: true }), 1),
    );
  });

  // Marks are sized against the frame so they stay constant on screen.
  it("scales with the frame", () => {
    const one = markRadius(star(), 1);
    expect(markRadius(star(), 3)).toBeCloseTo(one * 3);
  });
});

describe("a star sized to nothing", () => {
  // The game draws nothing for a size of zero, so neither may we: a
  // floor here would show an invisible star as an ordinary one.
  it("draws nothing", () => {
    expect(coreRadius(star({ size: 0 }), 1)).toBe(0);
    expect(markRadius(star({ size: 0 }), 1)).toBe(0);
  });

  it("draws nothing whatever kind or rings it wears", () => {
    for (const kind of [0, 1, 2]) {
      expect(markRadius(star({ size: 0, kind }), 1)).toBe(0);
    }
    expect(
      markRadius(star({ size: 0, canisRing: true, fidelisRing: true }), 1),
    ).toBe(0);
  });

  // A size that is not a number at all is a different case: that is a
  // broken value rather than a deliberate one, so it falls back to a
  // visible star instead of vanishing.
  it("still shows a star for a size that is not a number", () => {
    expect(coreRadius(star({ size: Number.NaN }), 1)).toBeGreaterThan(0);
  });

  it("draws nothing for a negative size", () => {
    expect(markRadius(star({ size: -3 }), 1)).toBe(0);
  });
});

describe("the rings", () => {
  // Measured off screenshots at size 4 and size 1: in game the rings hug
  // the star as thick bands, close enough that a kind-2 sparkle's points
  // reach past them.
  it("sit just outside the core, not far beyond it", () => {
    const s = star({ canisRing: true, fidelisRing: true, size: 4 });
    const core = coreRadius(s, 1);
    const reach = markRadius(s, 1) / core;
    expect(reach).toBeGreaterThan(1.5);
    expect(reach).toBeLessThan(2.2);
  });

  it("puts the Fidelis ring outside the Canis one", () => {
    const canis = markRadius(star({ canisRing: true }), 1);
    const fidelis = markRadius(star({ fidelisRing: true }), 1);
    expect(fidelis).toBeGreaterThan(canis);
  });

  // The kind-2 sparkle is what reads as spiky on a ringed star, so its
  // points have to clear both rings.
  it("is cleared by a kind-2 star's points", () => {
    const ringed = star({ kind: 2, canisRing: true, fidelisRing: true });
    const core = coreRadius(ringed, 1);
    // The spike reach, not the ring reach, decides the mark's extent.
    expect(markRadius(ringed, 1) / core).toBeGreaterThan(
      markRadius(star({ kind: 0, fidelisRing: true }), 1) /
        coreRadius(star({ kind: 0, fidelisRing: true }), 1),
    );
  });
});
