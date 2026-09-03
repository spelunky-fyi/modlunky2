// The editor's sections, one per group of fields.
//
// Each takes the slice of state it owns and a setter for it, so a
// keystroke in the journal does not re-render the deaths grid. The shell
// in SaveEditorModal owns the whole draft and hands out the slices.

import { memo, useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";

import type {
  CampEdit,
  CharacterEdit,
  EditableSave,
  JournalSectionEdit,
  LastRunEdit,
  ProfileEdit,
  ThemeEdit,
  UnlocksEdit,
  WorldDeathsEdit,
} from "../../../lib/commands";
import {
  BigNumberField,
  CheckField,
  Field,
  NumberField,
  SectionHead,
  SelectField,
  TimeField,
} from "./fields";

/** The worlds, as the game numbers them. */
const WORLDS = [
  "Dwelling",
  "Jungle / Volcana",
  "Olmec's Lair",
  "Tide Pool / Temple",
  "Ice Caves",
  "Neo Babylon",
  "Sunken City",
  "Cosmic Ocean",
];

/** The pets, in the order the save stores their rescue counts. */
const PETS = ["Monty", "Percy", "Poochi"] as const;

/** Camp tutorial steps, as the save numbers them. */
const TUTORIAL_STEPS = [
  "Not started",
  "Step 1",
  "Step 2",
  "Step 3",
  "Finished",
];

// -- profile ---------------------------------------------------------------

export const ProfileSection = memo(function ProfileSection({
  value,
  original,
  camp,
  originalCamp,
  onChange,
  onCampChange,
}: {
  value: ProfileEdit;
  original: ProfileEdit;
  camp: CampEdit;
  originalCamp: CampEdit;
  onChange: (next: ProfileEdit) => void;
  onCampChange: (next: CampEdit) => void;
}) {
  const set = <K extends keyof ProfileEdit>(key: K, next: ProfileEdit[K]) =>
    onChange({ ...value, [key]: next });
  const dirty = (key: keyof ProfileEdit) => value[key] !== original[key];

  // Realistic frame counts are tiny, but the field is 64-bit and losing
  // precision silently would be worse than showing a raw number.
  const totalFramesFit = Number.isSafeInteger(Number(value.timeTotal));

  return (
    <>
      <SectionHead
        title="Player profile"
        blurb="Details that show up in your profile in game."
      />

      {/* Grouped by what each number is about rather than by the order
          the file happens to store them in. A flat grid of thirteen
          counters gives no clue that three of them are wins and three
          are times. */}
      <FieldRow label="Runs">
        <NumberField
          label="Plays"
          value={value.plays}
          onChange={(n) => set("plays", n)}
          dirty={dirty("plays")}
        />
        <NumberField
          label="Deaths"
          value={value.deaths}
          onChange={(n) => set("deaths", n)}
          dirty={dirty("deaths")}
        />
      </FieldRow>

      <FieldRow label="Wins">
        <NumberField
          label="Normal"
          value={value.winsNormal}
          onChange={(n) => set("winsNormal", n)}
          dirty={dirty("winsNormal")}
        />
        <NumberField
          label="Hard"
          value={value.winsHard}
          onChange={(n) => set("winsHard", n)}
          dirty={dirty("winsHard")}
        />
        <NumberField
          label="Cosmic Ocean"
          value={value.winsSpecial}
          onChange={(n) => set("winsSpecial", n)}
          dirty={dirty("winsSpecial")}
        />
      </FieldRow>

      <FieldRow label="Money">
        <NumberField
          label="Best run"
          value={value.scoreTop}
          onChange={(n) => set("scoreTop", n)}
          dirty={dirty("scoreTop")}
        />
        <BigNumberField
          label="Lifetime total"
          value={value.scoreTotal}
          onChange={(n) => set("scoreTotal", n)}
          dirty={dirty("scoreTotal")}
        />
      </FieldRow>

      <FieldRow label="Deepest reached">
        <SelectField
          label="World"
          value={Math.min(8, Math.max(1, value.deepestArea)) - 1}
          options={WORLDS}
          onChange={(index) => set("deepestArea", index + 1)}
          dirty={dirty("deepestArea")}
        />
        <NumberField
          label="Level"
          value={value.deepestLevel}
          onChange={(n) => set("deepestLevel", n)}
          min={1}
          max={99}
          dirty={dirty("deepestLevel")}
        />
      </FieldRow>

      <FieldRow label="Times" hint="h:mm:ss.mmm, or empty for no time.">
        <TimeField
          label="Best run"
          frames={value.timeBest}
          onChange={(n) => set("timeBest", n)}
          dirty={dirty("timeBest")}
        />
        {totalFramesFit ? (
          <TimeField
            label="Played in total"
            frames={Number(value.timeTotal)}
            onChange={(n) => set("timeTotal", String(n))}
            dirty={dirty("timeTotal")}
          />
        ) : (
          <BigNumberField
            label="Played in total (frames)"
            value={value.timeTotal}
            onChange={(n) => set("timeTotal", n)}
            dirty={dirty("timeTotal")}
            hint="Too large to show as a clock, so this is the raw frame count."
          />
        )}
        <TimeField
          label="Camp tutorial"
          frames={value.timeTutorial}
          onChange={(n) => set("timeTutorial", n)}
          dirty={dirty("timeTutorial")}
        />
      </FieldRow>

      {/* Pets live here rather than with the characters: they are a
          lifetime count like everything else on this tab, and the game
          shows them nowhere at all. */}
      <FieldRow label="Pets rescued">
        {PETS.map((pet, index) => (
          <NumberField
            key={pet}
            label={pet}
            value={camp.petsRescued[index]}
            max={255}
            dirty={camp.petsRescued[index] !== originalCamp.petsRescued[index]}
            onChange={(next) => {
              const pets = [...camp.petsRescued] as CampEdit["petsRescued"];
              pets[index] = next;
              onCampChange({ ...camp, petsRescued: pets });
            }}
          />
        ))}
      </FieldRow>
    </>
  );
});

// -- progress --------------------------------------------------------------

export const ProgressSection = memo(function ProgressSection({
  value,
  original,
  shortcutStates,
  onChange,
}: {
  value: UnlocksEdit;
  original: UnlocksEdit;
  shortcutStates: string[];
  onChange: (next: UnlocksEdit) => void;
}) {
  const set = <K extends keyof UnlocksEdit>(key: K, next: UnlocksEdit[K]) =>
    onChange({ ...value, [key]: next });
  const dirty = (key: keyof UnlocksEdit) => value[key] !== original[key];

  return (
    <>
      <SectionHead title="Progress" />

      <div className="ed-checks">
        <CheckField
          label="Normal ending"
          checked={value.completedNormal}
          onChange={(v) => set("completedNormal", v)}
          dirty={dirty("completedNormal")}
        />
        <CheckField
          label="Ironman"
          checked={value.completedIronman}
          onChange={(v) => set("completedIronman", v)}
          dirty={dirty("completedIronman")}
        />
        <CheckField
          label="Hard ending"
          checked={value.completedHard}
          onChange={(v) => set("completedHard", v)}
          dirty={dirty("completedHard")}
        />
        <CheckField
          label="Seeded runs unlocked"
          checked={value.seededUnlocked}
          onChange={(v) => set("seededUnlocked", v)}
          dirty={dirty("seededUnlocked")}
        />
        <CheckField
          label="Profile seen"
          checked={value.profileSeen}
          onChange={(v) => set("profileSeen", v)}
          dirty={dirty("profileSeen")}
        />
      </div>

      <div className="ed-grid">
        <SelectField
          label="Shortcuts"
          value={Math.min(
            shortcutStates.length - 1,
            Math.max(0, value.shortcuts),
          )}
          options={shortcutStates}
          onChange={(n) => set("shortcuts", n)}
          dirty={dirty("shortcuts")}
        />
        <SelectField
          label="Tutorial"
          value={Math.min(4, Math.max(0, value.tutorialState))}
          options={TUTORIAL_STEPS}
          onChange={(n) => set("tutorialState", n)}
          dirty={dirty("tutorialState")}
        />
      </div>
    </>
  );
});

// -- journal ---------------------------------------------------------------

export const JournalSection = memo(function JournalSection({
  sections,
  original,
  onChange,
}: {
  sections: JournalSectionEdit[];
  original: JournalSectionEdit[];
  onChange: (next: JournalSectionEdit[]) => void;
}) {
  const [activeKey, setActiveKey] = useState(sections[0]?.key ?? "places");
  const [query, setQuery] = useState("");

  const index = sections.findIndex((section) => section.key === activeKey);
  const section = sections[index];
  const before = original[index];
  if (!section) return null;

  const needle = query.trim().toLowerCase();
  const rows = section.entries
    .map((entry, entryIndex) => ({ entry, entryIndex }))
    .filter(({ entry }) => entry.name.toLowerCase().includes(needle));

  const update = (
    entryIndex: number,
    patch: Partial<JournalSectionEdit["entries"][number]>,
  ) => {
    const entries = section.entries.slice();
    entries[entryIndex] = { ...entries[entryIndex], ...patch };
    const next = sections.slice();
    next[index] = { ...section, entries };
    onChange(next);
  };

  /** Sets every entry currently visible, so a filter scopes the action. */
  const setAllVisible = (discovered: boolean) => {
    const entries = section.entries.slice();
    for (const { entryIndex } of rows) {
      entries[entryIndex] = { ...entries[entryIndex], discovered };
    }
    const next = sections.slice();
    next[index] = { ...section, entries };
    onChange(next);
  };

  const found = section.entries.filter((entry) => entry.discovered).length;

  return (
    <>
      <SectionHead title="Journal" />

      <div className="ed-tabs" role="tablist">
        {sections.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={tab.key === activeKey}
            className={`ed-tab${tab.key === activeKey ? " on" : ""}`}
            onClick={() => setActiveKey(tab.key)}
          >
            {tab.label}
            <span>
              {tab.entries.filter((entry) => entry.discovered).length}/
              {tab.entries.length}
            </span>
          </button>
        ))}
      </div>

      <div className="ed-toolbar">
        <div className="ed-search">
          <Search size={14} aria-hidden="true" />
          <input
            type="search"
            value={query}
            placeholder={`Filter ${section.label.toLowerCase()}`}
            aria-label={`Filter ${section.label}`}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <span className="ed-toolbar-count">
          {found} of {section.entries.length} discovered
        </span>
        <button
          type="button"
          className="saves-btn"
          onClick={() => setAllVisible(true)}
        >
          Discover {needle ? "shown" : "all"}
        </button>
        <button
          type="button"
          className="saves-btn"
          onClick={() => setAllVisible(false)}
        >
          Clear {needle ? "shown" : "all"}
        </button>
      </div>

      {section.hasKills && (
        <div className="ed-journal-head">
          <span />
          <span>Killed</span>
          <span>Killed by</span>
        </div>
      )}

      <ul className="ed-journal">
        {rows.map(({ entry, entryIndex }) => {
          const was = before?.entries[entryIndex];
          return (
            <li
              key={entry.name + String(entryIndex)}
              className={section.hasKills ? "with-kills" : undefined}
            >
              <CheckField
                label={entry.name}
                checked={entry.discovered}
                dirty={was ? entry.discovered !== was.discovered : false}
                onChange={(discovered) => update(entryIndex, { discovered })}
              />
              {section.hasKills && (
                <>
                  <CountInput
                    label={`Times you killed ${entry.name}`}
                    value={entry.killed ?? 0}
                    dirty={Boolean(was) && entry.killed !== was?.killed}
                    onChange={(killed) => update(entryIndex, { killed })}
                  />
                  <CountInput
                    label={`Times ${entry.name} killed you`}
                    value={entry.killedBy ?? 0}
                    dirty={Boolean(was) && entry.killedBy !== was?.killedBy}
                    onChange={(killedBy) => update(entryIndex, { killedBy })}
                  />
                </>
              )}
            </li>
          );
        })}
      </ul>
      {rows.length === 0 && (
        <p className="ed-note">Nothing matches "{query}".</p>
      )}
    </>
  );
});

/**
 * A bare number cell, for the dense grids where a labelled field will not
 * fit.
 *
 * Keeps its own draft, like `NumberField`, so the box can be emptied and
 * retyped. Bound straight to the value it would snap to 0 on the first
 * backspace and commit that, quietly zeroing a count the user only meant
 * to edit.
 */
function CountInput({
  label,
  value,
  dirty,
  onChange,
}: {
  label: string;
  value: number;
  dirty?: boolean;
  onChange: (next: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  const committed = useRef(value);
  useEffect(() => {
    if (value !== committed.current) {
      committed.current = value;
      setDraft(String(value));
    }
  }, [value]);

  const parsed = Number(draft);
  const valid = draft.trim() !== "" && Number.isInteger(parsed) && parsed >= 0;

  return (
    <input
      type="text"
      inputMode="numeric"
      aria-label={label}
      className={`ed-input tiny${valid ? "" : " invalid"}${dirty ? " dirty" : ""}`}
      value={draft}
      onChange={(e) => {
        const next = e.target.value;
        setDraft(next);
        const n = Number(next);
        if (next.trim() !== "" && Number.isInteger(n) && n >= 0) {
          const clamped = Math.min(n, 2147483647);
          committed.current = clamped;
          onChange(clamped);
        }
      }}
      onBlur={() => {
        if (!valid) setDraft(String(committed.current));
      }}
    />
  );
}

// -- characters ------------------------------------------------------------

export const CharactersSection = memo(function CharactersSection({
  characters,
  original,
  onCharactersChange,
}: {
  characters: CharacterEdit[];
  original: CharacterEdit[];
  onCharactersChange: (next: CharacterEdit[]) => void;
}) {
  const unlocked = characters.filter((character) => character.unlocked).length;

  const setCharacter = (index: number, patch: Partial<CharacterEdit>) => {
    const next = characters.slice();
    next[index] = { ...next[index], ...patch };
    onCharactersChange(next);
  };

  const setAll = (value: boolean) =>
    onCharactersChange(
      characters.map((character) => ({ ...character, unlocked: value })),
    );

  return (
    <>
      <SectionHead
        title="Characters"
        aside={
          <div className="ed-head-actions">
            <span className="ed-toolbar-count">{unlocked} / 20 unlocked</span>
            <button
              type="button"
              className="saves-btn"
              onClick={() => setAll(true)}
            >
              Unlock all
            </button>
            <button
              type="button"
              className="saves-btn"
              onClick={() => setAll(false)}
            >
              Lock all
            </button>
          </div>
        }
      />

      <div className="ed-journal-head one">
        <span />
        <span>Deaths</span>
      </div>
      <ul className="ed-journal characters">
        {characters.map((character, index) => {
          const was = original[index];
          return (
            <li key={character.name}>
              <CheckField
                label={character.name}
                checked={character.unlocked}
                dirty={was ? character.unlocked !== was.unlocked : false}
                onChange={(v) => setCharacter(index, { unlocked: v })}
              />
              <CountInput
                label={`Deaths as ${character.name}`}
                value={character.deaths}
                dirty={Boolean(was) && character.deaths !== was?.deaths}
                onChange={(deaths) => setCharacter(index, { deaths })}
              />
            </li>
          );
        })}
      </ul>
    </>
  );
});

// -- last run --------------------------------------------------------------

export const LastRunSection = memo(function LastRunSection({
  value,
  original,
  camp,
  originalCamp,
  themeNames,
  stickerNames,
  firstCharacterEntity,
  characters,
  onChange,
  onCampChange,
}: {
  value: LastRunEdit;
  original: LastRunEdit;
  camp: CampEdit;
  originalCamp: CampEdit;
  /** Theme id to name, for the picker. */
  themeNames: ThemeEdit[];
  stickerNames: Record<string, string>;
  firstCharacterEntity: number;
  characters: CharacterEdit[];
  onChange: (next: LastRunEdit) => void;
  onCampChange: (next: CampEdit) => void;
}) {
  const set = <K extends keyof LastRunEdit>(key: K, next: LastRunEdit[K]) =>
    onChange({ ...value, [key]: next });

  const themeOptions = useMemo(
    () => themeNames.map((theme) => `${theme.id}. ${theme.name}`),
    [themeNames],
  );

  /** Names a sticker: characters from the roster, everything else from
   *  the map the backend sent for the ids this save already held. */
  const nameSticker = (entityType: number): string | null => {
    const characterIndex = entityType - firstCharacterEntity;
    if (characterIndex >= 0 && characterIndex < characters.length) {
      return characters[characterIndex].name;
    }
    return stickerNames[String(entityType)] ?? null;
  };

  return (
    <>
      <SectionHead title="Last run" />
      <div className="ed-grid">
        <NumberField
          label="World"
          value={value.world}
          min={1}
          max={8}
          dirty={value.world !== original.world}
          onChange={(n) => set("world", n)}
          hint={value.world === 8 ? "Shown in game as 7." : undefined}
        />
        <NumberField
          label="Level"
          value={value.level}
          min={1}
          max={99}
          dirty={value.level !== original.level}
          onChange={(n) => set("level", n)}
        />
        <SelectField
          label="Theme"
          value={Math.max(
            0,
            themeNames.findIndex((theme) => theme.id === value.theme),
          )}
          options={themeOptions}
          dirty={value.theme !== original.theme}
          onChange={(index) => set("theme", themeNames[index]?.id ?? 1)}
        />
        <NumberField
          label="Money"
          value={value.score}
          dirty={value.score !== original.score}
          onChange={(n) => set("score", n)}
        />
        <TimeField
          label="Time"
          frames={value.time}
          dirty={value.time !== original.time}
          onChange={(n) => set("time", Math.max(0, n))}
        />
        <Field
          label="Last daily"
          hint="Eight digits, YYYYMMDD. Empty for never."
        >
          <input
            type="text"
            inputMode="numeric"
            className={`ed-input${
              isDailyValid(camp.lastDaily) ? "" : " invalid"
            }${camp.lastDaily !== originalCamp.lastDaily ? " dirty" : ""}`}
            value={camp.lastDaily ?? ""}
            maxLength={8}
            placeholder="20260128"
            onChange={(e) => {
              const raw = e.target.value.trim();
              onCampChange({ ...camp, lastDaily: raw === "" ? null : raw });
            }}
          />
        </Field>
      </div>

      <SectionHead
        title="Stickers"
        aside={
          <button
            type="button"
            className="saves-btn"
            disabled={value.stickers.length >= 20}
            onClick={() => set("stickers", [...value.stickers, 0])}
          >
            Add sticker
          </button>
        }
      />
      {value.stickers.length === 0 ? (
        <p className="ed-note">No stickers.</p>
      ) : (
        <ul className="ed-stickers">
          {value.stickers.map((entityType, index) => {
            const name = nameSticker(entityType);
            return (
              <li key={index}>
                <CountInput
                  label={`Sticker ${index + 1} entity type`}
                  value={entityType}
                  onChange={(next) => {
                    const stickers = value.stickers.slice();
                    stickers[index] = next;
                    set("stickers", stickers);
                  }}
                />
                <span className="ed-sticker-name">
                  {name ?? <em>Entity {entityType}</em>}
                </span>
                <button
                  type="button"
                  className="ed-icon-btn"
                  aria-label={`Remove sticker ${index + 1}`}
                  onClick={() =>
                    set(
                      "stickers",
                      value.stickers.filter((_, i) => i !== index),
                    )
                  }
                >
                  <X size={14} aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
});

/** The game reads these eight bytes as a date, so anything else is refused. */
function isDailyValid(raw: string | null): boolean {
  return raw === null || raw === "" || /^\d{8}$/.test(raw);
}

// -- deaths by level -------------------------------------------------------

export const DeathsSection = memo(function DeathsSection({
  worlds,
  original,
  onChange,
}: {
  worlds: WorldDeathsEdit[];
  original: WorldDeathsEdit[];
  onChange: (next: WorldDeathsEdit[]) => void;
}) {
  const total = worlds.reduce(
    (sum, world) => sum + world.levels.reduce((a, b) => a + b, 0),
    0,
  );

  const setLevel = (worldIndex: number, levelIndex: number, next: number) => {
    const copy = worlds.slice();
    const levels = copy[worldIndex].levels.slice();
    levels[levelIndex] = next;
    copy[worldIndex] = { ...copy[worldIndex], levels };
    onChange(copy);
  };

  return (
    <>
      <SectionHead
        title="Deaths by level"
        aside={
          <span className="ed-toolbar-count">
            {total.toLocaleString()} in total
          </span>
        }
      />

      {worlds.map((world, worldIndex) => (
        <section key={world.world} className="ed-world">
          <h4>
            {world.world}. {world.name}
            <span>
              {world.levels.reduce((a, b) => a + b, 0).toLocaleString()}
            </span>
          </h4>
          <div className="ed-levels">
            {world.levels.map((deaths, levelIndex) => {
              const was = original[worldIndex]?.levels[levelIndex];
              return (
                <label key={levelIndex} className="ed-level">
                  <span>
                    {world.world}-{world.firstLevel + levelIndex}
                  </span>
                  <CountInput
                    label={`Deaths at ${world.world}-${world.firstLevel + levelIndex}`}
                    value={deaths}
                    dirty={was !== undefined && deaths !== was}
                    onChange={(next) => setLevel(worldIndex, levelIndex, next)}
                  />
                </label>
              );
            })}
          </div>
        </section>
      ))}
    </>
  );
});

/** A labelled group of fields.
 *
 *  The label sits beside the row rather than above it, so a tab of five
 *  groups reads as five things rather than as a wall of inputs with
 *  headings between them. */
function FieldRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="ed-row">
      <div className="ed-row-label">
        <h4>{label}</h4>
        {hint && <p>{hint}</p>}
      </div>
      <div className="ed-row-fields">{children}</div>
    </section>
  );
}

/** Shared by the shell, so the rail and the panel agree on the list. */
export type SectionKey =
  | "profile"
  | "progress"
  | "journal"
  | "characters"
  | "lastRun"
  | "deaths"
  | "constellation";

export const SECTIONS: { key: SectionKey; label: string }[] = [
  { key: "profile", label: "Profile" },
  { key: "progress", label: "Progress" },
  { key: "journal", label: "Journal" },
  { key: "characters", label: "Characters" },
  { key: "lastRun", label: "Last run" },
  { key: "deaths", label: "Deaths" },
  { key: "constellation", label: "Constellation" },
];

export type { EditableSave };
