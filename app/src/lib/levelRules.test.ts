import { describe, expect, it } from "vitest";

import { foldSavedRules, type LevelRules } from "./levelRules";
import type { RulesEntry } from "./commands";

const entry = (name: string, value: string): RulesEntry => ({
  name,
  value,
  comment: null,
});

const loaded = (): LevelRules => ({
  levelSettings: [entry("back_room_chance", "0")],
  levelChances: [entry("arrowtrap_chance", "35")],
  monsterChances: [entry("frog", "30")],
});

describe("foldSavedRules", () => {
  /** The reported bug: edit a rule, save, and the panel shows the old value
   *  again because the loaded copy was never updated to match the file. */
  it("adopts a saved section so the panel keeps showing the new value", () => {
    const saved = { levelSettings: [entry("back_room_chance", "100")] };

    const next = foldSavedRules(loaded(), saved);

    expect(next.levelSettings).toEqual([entry("back_room_chance", "100")]);
  });

  /** The payload omits sections the user didn't touch, and the backend leaves
   *  those alone on disk. Overwriting them here would show the user something
   *  the file doesn't say. */
  it("leaves sections the save didn't include exactly as they were", () => {
    const before = loaded();

    const next = foldSavedRules(before, {
      levelSettings: [entry("back_room_chance", "100")],
    });

    expect(next.levelChances).toEqual(before.levelChances);
    expect(next.monsterChances).toEqual(before.monsterChances);
  });

  it("can adopt every section at once", () => {
    const saved = {
      levelSettings: [entry("a", "1")],
      levelChances: [entry("b", "2")],
      monsterChances: [entry("c", "3")],
    };

    expect(foldSavedRules(loaded(), saved)).toMatchObject(saved);
  });

  /** Deleting every row in a section is a real edit, and an empty array is
   *  meaningfully different from an absent one. Treating it as "nothing was
   *  sent" would resurrect the deleted rows in the UI. */
  it("adopts an emptied section rather than treating it as absent", () => {
    const next = foldSavedRules(loaded(), { levelChances: [] });

    expect(next.levelChances).toEqual([]);
  });

  it("returns the level untouched when there was nothing to save", () => {
    const before = loaded();
    expect(foldSavedRules(before, null)).toEqual(before);
  });

  it("preserves unrelated fields on the level", () => {
    const before = { ...loaded(), name: "dwelling.lvl", templates: [] };

    const next = foldSavedRules(before, { levelSettings: [entry("x", "1")] });

    expect(next.name).toBe("dwelling.lvl");
    expect(next.templates).toEqual([]);
  });
});
