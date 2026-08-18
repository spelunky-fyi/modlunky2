import { describe, expect, it } from "vitest";

import {
  DEFAULT_TOAST_LEVEL,
  normalizeToastLevel,
  shouldPopToast,
} from "./toastLevel";

describe("normalizeToastLevel", () => {
  it("passes through every valid level", () => {
    for (const level of ["info", "success", "warning", "error"] as const) {
      expect(normalizeToastLevel(level)).toBe(level);
    }
  });

  /** The value comes out of a user-editable JSON config, so anything at all
   *  can turn up here. It must never propagate an invalid level into the
   *  rank comparison, where it would make `shouldPopToast` return undefined
   *  comparisons and silently swallow every toast. */
  it("falls back to the default for anything else", () => {
    expect(normalizeToastLevel(null)).toBe(DEFAULT_TOAST_LEVEL);
    expect(normalizeToastLevel(undefined)).toBe(DEFAULT_TOAST_LEVEL);
    expect(normalizeToastLevel("")).toBe(DEFAULT_TOAST_LEVEL);
    expect(normalizeToastLevel("WARNING")).toBe(DEFAULT_TOAST_LEVEL);
    expect(normalizeToastLevel("critical")).toBe(DEFAULT_TOAST_LEVEL);
  });
});

describe("shouldPopToast", () => {
  it("pops anything at or above the threshold", () => {
    expect(shouldPopToast("error", "warning")).toBe(true);
    expect(shouldPopToast("warning", "warning")).toBe(true);
  });

  it("holds back anything below it", () => {
    expect(shouldPopToast("success", "warning")).toBe(false);
    expect(shouldPopToast("info", "warning")).toBe(false);
  });

  it("pops everything at the lowest threshold", () => {
    for (const variant of ["info", "success", "warning", "error"] as const) {
      expect(shouldPopToast(variant, "info")).toBe(true);
    }
  });

  it("pops only errors at the highest threshold", () => {
    expect(shouldPopToast("error", "error")).toBe(true);
    expect(shouldPopToast("warning", "error")).toBe(false);
  });

  /** The documented default: warnings and errors interrupt, the rest just
   *  land in the log. */
  it("keeps routine confirmations out of the way by default", () => {
    expect(shouldPopToast("success", DEFAULT_TOAST_LEVEL)).toBe(false);
    expect(shouldPopToast("error", DEFAULT_TOAST_LEVEL)).toBe(true);
  });
});
