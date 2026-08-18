import { describe, expect, it } from "vitest";

import { normalizeTheme } from "./theme";

describe("normalizeTheme", () => {
  it("recognises light", () => {
    expect(normalizeTheme("light")).toBe("light");
  });

  /** Read from both the Rust config and a localStorage mirror that the
   *  pre-paint script in index.html writes, so a stale or hand-edited value
   *  has to land somewhere sane rather than on an undefined theme. Dark is
   *  the default and matches the Rust side. */
  it("treats everything else as dark", () => {
    expect(normalizeTheme("dark")).toBe("dark");
    expect(normalizeTheme(null)).toBe("dark");
    expect(normalizeTheme(undefined)).toBe("dark");
    expect(normalizeTheme("")).toBe("dark");
    expect(normalizeTheme("Light")).toBe("dark");
    expect(normalizeTheme("solarized")).toBe("dark");
  });
});
