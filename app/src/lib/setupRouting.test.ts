import { describe, expect, it } from "vitest";

import {
  firstUnmet,
  isSatisfied,
  type SetupStatus,
} from "../types/setup";

const status = (over: Partial<SetupStatus> = {}): SetupStatus => ({
  installDir: "ok",
  installDirPath: "D:/Spelunky 2",
  assetsExtracted: true,
  hasApiToken: true,
  modsReady: true,
  ...over,
});

describe("isSatisfied", () => {
  it("treats a missing folder as unsatisfied, not just an unset one", () => {
    expect(isSatisfied(status({ installDir: "missing" }), "installDir")).toBe(
      false,
    );
    expect(isSatisfied(status({ installDir: "unset" }), "installDir")).toBe(
      false,
    );
    expect(isSatisfied(status(), "installDir")).toBe(true);
  });

  it("reads the other two straight off the status", () => {
    expect(isSatisfied(status({ assetsExtracted: false }), "assets")).toBe(false);
    expect(isSatisfied(status({ hasApiToken: false }), "apiToken")).toBe(false);
  });
});

describe("firstUnmet", () => {
  it("is null when everything asked for is satisfied", () => {
    expect(firstUnmet(status(), ["installDir", "assets"])).toBeNull();
  });

  /** The ordering is the whole point: you can't extract assets out of a game
   *  folder you haven't chosen, so asking for both at once would put a step
   *  in front of the user that they can't act on. */
  it("asks for the install folder before the assets it comes from", () => {
    const s = status({ installDir: "unset", assetsExtracted: false });
    expect(firstUnmet(s, ["installDir", "assets"])).toBe("installDir");
  });

  it("moves on to assets once the folder is set", () => {
    const s = status({ assetsExtracted: false });
    expect(firstUnmet(s, ["installDir", "assets"])).toBe("assets");
  });

  /** A tab only gates on what it actually needs. The Mods tab works fine
   *  without extracted assets, so an unextracted install must not stop it. */
  it("ignores requirements the caller didn't ask for", () => {
    const s = status({ assetsExtracted: false, hasApiToken: false });
    expect(firstUnmet(s, ["installDir"])).toBeNull();
  });

  it("gates nothing for a tab that requires nothing", () => {
    const s = status({ installDir: "unset", assetsExtracted: false });
    expect(firstUnmet(s, [])).toBeNull();
  });
});
