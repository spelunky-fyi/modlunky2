import { describe, expect, it } from "vitest";

import type { EditableSave } from "../../../lib/commands";
import { changedSections, toEdits } from "./SaveEditorModal";

/** A save with one of everything, small enough to assert against. */
function sample(): EditableSave {
  return {
    path: "C:\\Spelunky 2\\savegame.sav",
    version: 30,
    checksumValid: true,
    profile: {
      plays: 2530,
      deaths: 596,
      winsNormal: 9,
      winsHard: 2,
      winsSpecial: 4,
      scoreTotal: "8792470",
      scoreTop: 527225,
      timeTotal: "2635000",
      timeBest: 1980,
      timeTutorial: 1270,
      deepestArea: 8,
      deepestLevel: 99,
    },
    unlocks: {
      completedNormal: true,
      completedIronman: true,
      completedHard: true,
      profileSeen: true,
      seededUnlocked: true,
      shortcuts: 10,
      tutorialState: 4,
    },
    lastRun: {
      world: 8,
      level: 99,
      theme: 10,
      score: 4125,
      time: 4358,
      stickers: [199],
    },
    camp: {
      players: [5, 14, 16, 6],
      petsRescued: [3, 1, 0],
      lastDaily: "20260128",
    },
    journal: [
      {
        key: "places",
        label: "Places",
        hasKills: false,
        entries: [
          { name: "Dwelling", discovered: true, killed: null, killedBy: null },
          { name: "Jungle", discovered: false, killed: null, killedBy: null },
        ],
      },
      {
        key: "bestiary",
        label: "Bestiary",
        hasKills: true,
        entries: [
          { name: "Snake", discovered: true, killed: 40, killedBy: 3 },
          { name: "Spider", discovered: true, killed: 12, killedBy: 9 },
        ],
      },
    ],
    characters: [
      { name: "Ana Spelunky", unlocked: true, deaths: 20 },
      { name: "Margaret Tunnel", unlocked: false, deaths: 375 },
    ],
    deaths: [
      { world: 1, name: "Dwelling", firstLevel: 1, levels: [405, 38, 18, 26] },
      { world: 8, name: "Cosmic Ocean", firstLevel: 5, levels: [1, 0, 2] },
    ],
    themes: [
      { id: 1, name: "Dwelling", completed: true },
      { id: 10, name: "Cosmic Ocean", completed: false },
    ],
    constellation: null,
    constellationEditable: true,
    shortcutStates: ["None", "Met Terra"],
    stickerNames: { "199": "Liz Mutton" },
    firstCharacterEntity: 194,
  };
}

describe("toEdits", () => {
  it("flattens each journal category into parallel lists", () => {
    const edits = toEdits(sample());
    expect(edits.journal[0]).toEqual({
      key: "places",
      discovered: [true, false],
      killed: [],
      killedBy: [],
    });
    expect(edits.journal[1]).toEqual({
      key: "bestiary",
      discovered: [true, true],
      killed: [40, 12],
      killedBy: [3, 9],
    });
  });

  // A category with no counters must send nothing rather than zeroes: the
  // backend writes what it is given, and a list of zeroes aimed at a
  // category that later gained counters would erase them.
  it("sends no kill counts for a category that keeps none", () => {
    const edits = toEdits(sample());
    expect(edits.journal[0].killed).toHaveLength(0);
    expect(edits.journal[0].killedBy).toHaveLength(0);
  });

  // Each world carries the level its first entry means, so the backend
  // writes to the row the user actually typed in rather than assuming
  // every world starts at level 1.
  it("keeps each world's own level range with it", () => {
    expect(toEdits(sample()).deaths).toEqual([
      { world: 1, firstLevel: 1, levels: [405, 38, 18, 26] },
      { world: 8, firstLevel: 5, levels: [1, 0, 2] },
    ]);
  });

  it("reduces characters and themes to just their values", () => {
    const edits = toEdits(sample());
    expect(edits.characters).toEqual([
      { unlocked: true, deaths: 20 },
      { unlocked: false, deaths: 375 },
    ]);
    expect(edits.themes).toEqual([true, false]);
  });

  // The big counters are strings the whole way down; turning one into a
  // number anywhere in here would round it.
  it("leaves the 64-bit fields as strings", () => {
    const save = sample();
    save.profile.scoreTotal = "9007199254740995";
    expect(toEdits(save).profile.scoreTotal).toBe("9007199254740995");
  });
});

describe("changedSections", () => {
  it("finds nothing in an untouched draft", () => {
    const save = sample();
    expect(changedSections(save, sample()).size).toBe(0);
    expect(changedSections(save, save).size).toBe(0);
  });

  it("says nothing before the save has loaded", () => {
    expect(changedSections(null, null).size).toBe(0);
    expect(changedSections(sample(), null).size).toBe(0);
  });

  it("marks only the section that changed", () => {
    const draft = sample();
    draft.profile.plays = 2531;
    expect([...changedSections(draft, sample())]).toEqual(["profile"]);
  });

  // Theme flags are decoded and round-tripped but not editable: the
  // game's own bookkeeping for them is wrong for three themes, and where
  // it is right it duplicates the journal. Nothing can change them, so
  // nothing should claim they did.
  it("attributes theme flags to no section", () => {
    const draft = sample();
    draft.themes[1] = { ...draft.themes[1], completed: true };
    expect(changedSections(draft, sample()).size).toBe(0);
  });

  it("finds a change buried in a journal entry's kill count", () => {
    const draft = sample();
    draft.journal[1].entries[0] = {
      ...draft.journal[1].entries[0],
      killed: 41,
    };
    expect([...changedSections(draft, sample())]).toEqual(["journal"]);
  });

  // The camp is edited from two places - pet counts sit with the other
  // lifetime figures on the profile, the daily date with the last run -
  // so a change to it marks both rather than hiding one.
  it("marks both sections that can edit the camp", () => {
    const draft = sample();
    draft.camp = { ...draft.camp, lastDaily: "20260202" };
    const changed = changedSections(draft, sample());
    expect(changed.has("profile")).toBe(true);
    expect(changed.has("lastRun")).toBe(true);
    expect(changed.has("characters")).toBe(false);
  });

  it("marks the profile when a pet count changes", () => {
    const draft = sample();
    draft.camp = { ...draft.camp, petsRescued: [4, 1, 0] };
    expect(changedSections(draft, sample()).has("profile")).toBe(true);
  });

  it("notices a constellation appearing where there was none", () => {
    const draft = sample();
    draft.constellation = {
      stars: [],
      lines: [],
      scale: 1,
      lineRedIntensity: 0,
    };
    expect([...changedSections(draft, sample())]).toEqual(["constellation"]);
  });
});
