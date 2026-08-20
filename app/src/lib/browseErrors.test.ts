import { describe, expect, it } from "vitest";
import { asBrowseError, isAuthFailure } from "./commands";

/**
 * Two different Rust error types reach these helpers. Browse commands return
 * `BrowseError`, which serde tags internally as `{kind, message}`. Installs
 * return `ManagerError`, which serde tags externally as `{Unauthorized: "..."}`.
 * Nothing in the type system connects the two spellings to these checks, so a
 * rename on either side would silently stop offering the reconnect button and
 * start showing a raw error instead.
 */
describe("asBrowseError", () => {
  it("passes through each tagged kind", () => {
    for (const kind of ["needsAccount", "unauthorized", "failed"] as const) {
      expect(asBrowseError({ kind, message: "m" })).toEqual({
        kind,
        message: "m",
      });
    }
  });

  it("falls back to failed for anything unrecognised", () => {
    // A panic, a serialization failure, or a plain string from some other
    // command all have to render as something.
    expect(asBrowseError("boom").kind).toBe("failed");
    expect(asBrowseError(null).kind).toBe("failed");
    expect(asBrowseError({ kind: "somethingNew" }).kind).toBe("failed");
    expect(asBrowseError(new Error("nope")).kind).toBe("failed");
  });

  it("keeps the message when falling back", () => {
    expect(asBrowseError("boom").message).toContain("boom");
  });
});

describe("isAuthFailure", () => {
  it("recognises the browse shape", () => {
    expect(isAuthFailure({ kind: "unauthorized", message: "m" })).toBe(true);
  });

  it("recognises the install shape", () => {
    expect(isAuthFailure({ Unauthorized: "m" })).toBe(true);
  });

  it("does not fire on other failures", () => {
    expect(isAuthFailure({ kind: "failed", message: "m" })).toBe(false);
    expect(isAuthFailure({ kind: "needsAccount", message: "m" })).toBe(false);
    expect(isAuthFailure({ ModExistsError: "m" })).toBe(false);
    expect(isAuthFailure("Unauthorized")).toBe(false);
    expect(isAuthFailure(null)).toBe(false);
    expect(isAuthFailure(undefined)).toBe(false);
  });
});
