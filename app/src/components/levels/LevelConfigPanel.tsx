// Level Configuration panel: edits the current file's entry in the pack's
// level_configuration.ls, plus surfaces the .lvl file's grid dimensions
// with a resize control. Panel is dense on purpose so the modal stays
// scannable; overrides are laid out in two columns instead of one long
// vertical list, and mutually-exclusive flags collapse into a segmented
// control.

import { useMemo } from "react";
import type {
  CustomLevelSaveFormat,
  LevelConfiguration,
} from "../../lib/commands";
import "./LevelConfigPanel.css";

interface Props {
  entry: LevelConfiguration;
  onChange: (next: LevelConfiguration) => void;
  /** True iff the file appears in the pack's playthrough sequence. When
   *  false the Identity, Layer overrides, and Behavior sections collapse
   *  to a single note, since Playlunky only reads those fields for
   *  sequence entries and would silently ignore edits otherwise. */
  inSequence: boolean;
  /** Format the file's on-disk templates were recognised as. Null when
   *  load couldn't detect one (recovery flow handles that separately). */
  detectedFormat?: CustomLevelSaveFormat | null;
  /** Override that will be used on next save instead of `detectedFormat`.
   *  Null means "use whatever was detected." */
  overrideFormat?: CustomLevelSaveFormat | null;
  /** All formats the user can pick between. Union of built-ins + editor
   *  user-defined. Owner (CustomEditor) already de-dupes by name. */
  availableFormats?: CustomLevelSaveFormat[];
  onOverrideFormat?: (next: CustomLevelSaveFormat | null) => void;
}

/** Theme integers are the game's internal theme IDs, so LevelConfiguration
 *  values map straight to what the runtime reads. Order matters: callers
 *  reference by id, not by position. */
export const THEMES: Array<{ id: number; label: string }> = [
  { id: 1, label: "Dwelling" },
  { id: 2, label: "Jungle" },
  { id: 3, label: "Volcana" },
  { id: 4, label: "Olmec" },
  { id: 5, label: "Tide Pool" },
  { id: 6, label: "Temple" },
  { id: 7, label: "Ice Caves" },
  { id: 8, label: "Neo Babylon" },
  { id: 9, label: "Sunken City" },
  { id: 10, label: "Cosmic Ocean" },
  { id: 11, label: "City of Gold" },
  { id: 12, label: "Duat" },
  { id: 13, label: "Abzu" },
  { id: 14, label: "Tiamat" },
  { id: 15, label: "Eggplant World" },
  { id: 16, label: "Hundun" },
  { id: 17, label: "Base Camp" },
];

export const COSMIC_OCEAN_THEME = 10;

/** CO subthemes for the main Level Theme when it's set to Cosmic Ocean.
 *  Python's `subtheme_combobox` accepts every biome here (line 279 of
 *  level_configuration_panel.py). */
const CO_SUBTHEMES: Array<{ id: number; label: string }> = [
  { id: 1, label: "Dwelling" },
  { id: 2, label: "Jungle" },
  { id: 3, label: "Volcana" },
  { id: 4, label: "Olmec" },
  { id: 5, label: "Tide Pool" },
  { id: 6, label: "Temple" },
  { id: 7, label: "Ice Caves" },
  { id: 8, label: "Neo Babylon" },
  { id: 9, label: "Sunken City" },
  { id: 11, label: "City of Gold" },
  { id: 12, label: "Duat" },
  { id: 13, label: "Abzu" },
  { id: 14, label: "Tiamat" },
  { id: 15, label: "Eggplant World" },
  { id: 16, label: "Hundun" },
  { id: 17, label: "Base Camp" },
];

/** CO subthemes for the Background layer specifically (Python's
 *  `background_subtheme_combobox`, line 587). The game only accepts a
 *  narrow subset here, so we do NOT reuse the main-theme CO list. */
const BG_CO_SUBTHEMES: Array<{ id: number; label: string }> = [
  { id: 1, label: "Dwelling" },
  { id: 2, label: "Jungle" },
  { id: 3, label: "Volcana" },
  { id: 5, label: "Tide Pool" },
  { id: 6, label: "Temple" },
  { id: 7, label: "Ice Caves" },
  { id: 8, label: "Neo Babylon" },
  { id: 9, label: "Sunken City" },
];

/** Border theme override (Python `border_theme_combobox`, line 443).
 *  Only these five distinct border-art themes are meaningful. "Normal"
 *  is Dwelling under the hood (the generic caves border). */
const BORDER_THEMES: Array<{ id: number; label: string }> = [
  { id: 1, label: "Normal" },
  { id: 7, label: "Ice Caves" },
  { id: 10, label: "Cosmic Ocean" },
  { id: 12, label: "Duat" },
  { id: 14, label: "Tiamat" },
];

/** Border-entity override (Python `border_entity_theme_combobox`,
 *  line 510). Only four entity types spawn as border walls. */
const BORDER_ENTITY_THEMES: Array<{ id: number; label: string }> = [
  { id: 1, label: "Hard" },
  { id: 8, label: "Metal" },
  { id: 12, label: "Dust" },
  { id: 9, label: "Guts" },
];

/** Build a default entry for a file that isn't in the config yet. Identifier
 *  is the file stem lowercased with non-alphanumerics dropped so it stays
 *  Lua-friendly if a sequence script tries to look it up. */
export function defaultConfigEntry(fileName: string): LevelConfiguration {
  const stem = fileName.replace(/\.lvl$/i, "");
  const identifier = stem.replace(/[^A-Za-z0-9_]/g, "_").toLowerCase();
  return {
    identifier,
    name: stem,
    file_name: fileName,
    theme: 1,
  };
}

/** Optional theme dropdown ("Same as theme" == undefined) used for the
 *  floor / background / border / music theme rows. Each row supplies its
 *  own allowed-values list because Python restricts border/border-entity
 *  to a small subset while floor/background/music accept all 17 biomes. */
function ThemeSelect({
  value,
  onChange,
  themes,
  fallbackLabel,
}: {
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  themes: ReadonlyArray<{ id: number; label: string }>;
  fallbackLabel: string;
}) {
  return (
    <select
      value={value == null ? "" : String(value)}
      onChange={(e) => {
        const raw = e.target.value;
        onChange(raw === "" ? undefined : Number(raw));
      }}
    >
      <option value="">{fallbackLabel}</option>
      {themes.map((t) => (
        <option key={t.id} value={t.id}>
          {t.label}
        </option>
      ))}
    </select>
  );
}

export function LevelConfigPanel({
  entry,
  onChange,
  inSequence,
  detectedFormat = null,
  overrideFormat = null,
  availableFormats = [],
  onOverrideFormat,
}: Props) {
  const isCO = entry.theme === COSMIC_OCEAN_THEME;

  const patch = useMemo(
    () =>
      <K extends keyof LevelConfiguration>(
        key: K,
        v: LevelConfiguration[K],
      ) => {
        onChange({ ...entry, [key]: v });
      },
    [entry, onChange],
  );

  // Loop mode is a tri-state derived from the two mutually-exclusive
  // booleans on the entry. Rendering as a segmented control means the user
  // can only pick one at a time.
  const loopMode: "auto" | "loop" | "no-loop" = entry.loop
    ? "loop"
    : entry.dont_loop
      ? "no-loop"
      : "auto";
  const setLoopMode = (mode: "auto" | "loop" | "no-loop") => {
    onChange({
      ...entry,
      loop: mode === "loop" ? true : undefined,
      dont_loop: mode === "no-loop" ? true : undefined,
    });
  };

  return (
    <div className="level-config">
      {/* --- Save format (on-disk template shape, unaffected by
             sequence membership) ------------------------------------- */}
      {onOverrideFormat && availableFormats.length > 0 && (
        <section className="level-config-section">
          <div className="level-config-section-title">Save format</div>
          <div className="level-config-hint-inline">
            On-disk template shape. Applies to the .lvl file at save time
            regardless of whether the level is in the pack's sequence.
            Detected:{" "}
            {detectedFormat ? (
              <code>{detectedFormat.name}</code>
            ) : (
              <em>unknown</em>
            )}
            .
          </div>
          <label className="level-config-field">
            <span className="level-config-label">Format</span>
            <select
              value={
                overrideFormat
                  ? overrideFormat.name
                  : detectedFormat
                    ? detectedFormat.name
                    : ""
              }
              onChange={(e) => {
                const pick = availableFormats.find(
                  (f) => f.name === e.target.value,
                );
                if (!pick) return;
                // Match against detected -> clear override (no conversion
                // needed); otherwise store the override.
                if (detectedFormat && pick.name === detectedFormat.name) {
                  onOverrideFormat(null);
                } else {
                  onOverrideFormat(pick);
                }
              }}
            >
              {availableFormats.map((f) => (
                <option key={f.name} value={f.name}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
          {overrideFormat && (
            <div className="level-config-hint-inline level-config-convert-note">
              Save will convert every template to{" "}
              <code>{overrideFormat.room_template_format}</code>.
            </div>
          )}
        </section>
      )}

      {/* --- Theme + CO extras (persisted via the (0,0) template
             comment, so this works for any file regardless of
             sequence membership) --------------------------------- */}
      <section className="level-config-section">
        <div className="level-config-section-title">Theme</div>
        <div className="level-config-grid theme-row">
          <label className="level-config-field">
            <span className="level-config-label">Theme</span>
            <select
              value={String(entry.theme)}
              onChange={(e) => patch("theme", Number(e.target.value))}
            >
              {THEMES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          {isCO && (
            <>
              <label className="level-config-field">
                <span className="level-config-label">CO subtheme</span>
                <select
                  value={
                    entry.subtheme == null ? "" : String(entry.subtheme)
                  }
                  onChange={(e) => {
                    const raw = e.target.value;
                    patch(
                      "subtheme",
                      raw === "" ? undefined : Number(raw),
                    );
                  }}
                >
                  <option value="">Random</option>
                  {CO_SUBTHEMES.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="level-config-field">
                <span className="level-config-label">CO Width</span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={entry.width ?? ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    patch(
                      "width",
                      v === "" ? undefined : Math.max(1, Number(v)),
                    );
                  }}
                />
              </label>
              <label className="level-config-field">
                <span className="level-config-label">CO Height</span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={entry.height ?? ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    patch(
                      "height",
                      v === "" ? undefined : Math.max(1, Number(v)),
                    );
                  }}
                />
              </label>
            </>
          )}
        </div>
      </section>

      {/* --- Level sequence settings ----------------------------------
             When off-sequence Playlunky ignores these, so we collapse
             the whole block to a single explanatory section instead
             of showing disabled inputs. */}
      {!inSequence ? (
        <section className="level-config-section">
          <div className="level-config-section-title">
            Level sequence settings
          </div>
          <div className="level-config-hint-inline">
            No settings available: this file isn't in the pack's level
            sequence, so Playlunky won't read identity, layer
            overrides, or loop behavior at runtime. Add it via the
            Sequence panel to configure them.
          </div>
        </section>
      ) : (
        <>
          {/* --- Identity -------------------------------------------- */}
          <section className="level-config-section">
            <div className="level-config-section-title">Identity</div>
            <div className="level-config-grid two-col">
              <label className="level-config-field">
                <span className="level-config-label">Display name</span>
                <input
                  type="text"
                  value={entry.name}
                  onChange={(e) => patch("name", e.target.value)}
                />
              </label>
              <div className="level-config-field">
                <span className="level-config-label">Identifier</span>
                <code
                  className="level-config-readonly"
                  title="Auto-derived from the file name. Lua sequence scripts look levels up by this. Rename the file to change it."
                >
                  {entry.identifier}
                </code>
              </div>
            </div>
          </section>

          {/* --- Layer overrides -------------------------------------
                 Value sets mirror Python's individual comboboxes: floor/
                 background/music accept any biome, border has 5 art
                 themes, border entity has 4 wall entity types, and the
                 background CO subtheme only appears when Background is
                 set to Cosmic Ocean. Background sits last so its
                 conditional subtheme row doesn't push other fields
                 around when it appears. */}
          <section className="level-config-section">
            <div className="level-config-section-title">Layer overrides</div>
            <div className="level-config-grid two-col">
              <label className="level-config-field">
                <span className="level-config-label">Floor</span>
                <ThemeSelect
                  value={entry.floor_theme}
                  onChange={(v) => patch("floor_theme", v)}
                  themes={THEMES}
                  fallbackLabel="Default"
                />
              </label>
              <label className="level-config-field">
                <span className="level-config-label">Music</span>
                <ThemeSelect
                  value={entry.music_theme}
                  onChange={(v) => patch("music_theme", v)}
                  themes={THEMES}
                  fallbackLabel="Default"
                />
              </label>
              <label className="level-config-field">
                <span className="level-config-label">Border</span>
                <ThemeSelect
                  value={entry.border_theme}
                  onChange={(v) => patch("border_theme", v)}
                  themes={BORDER_THEMES}
                  fallbackLabel="Default"
                />
              </label>
              <label className="level-config-field">
                <span className="level-config-label">Border entity</span>
                <ThemeSelect
                  value={entry.border_entity_theme}
                  onChange={(v) => patch("border_entity_theme", v)}
                  themes={BORDER_ENTITY_THEMES}
                  fallbackLabel="Default"
                />
              </label>
              <label className="level-config-field">
                <span className="level-config-label">Background</span>
                <ThemeSelect
                  value={entry.background_theme}
                  onChange={(v) => {
                    // Drop the CO subtheme when leaving Cosmic Ocean
                    // (Python clears it in save; see custom_level_editor
                    // line 1266 - 1268).
                    if (v !== COSMIC_OCEAN_THEME) {
                      onChange({
                        ...entry,
                        background_theme: v,
                        background_texture_theme: undefined,
                      });
                    } else {
                      patch("background_theme", v);
                    }
                  }}
                  themes={THEMES}
                  fallbackLabel="Default"
                />
              </label>
              {entry.background_theme === COSMIC_OCEAN_THEME && (
                <label className="level-config-field">
                  <span className="level-config-label">
                    Background CO subtheme
                  </span>
                  <select
                    value={
                      entry.background_texture_theme == null
                        ? ""
                        : String(entry.background_texture_theme)
                    }
                    onChange={(e) => {
                      const raw = e.target.value;
                      patch(
                        "background_texture_theme",
                        raw === "" ? undefined : Number(raw),
                      );
                    }}
                  >
                    <option value="">Default</option>
                    {BG_CO_SUBTHEMES.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          </section>

          {/* --- Behavior ------------------------------------------- */}
          <section className="level-config-section">
            <div className="level-config-section-title">Behavior</div>
            <div className="level-config-field">
              <span className="level-config-label">Loop mode</span>
              <div className="level-config-segment" role="radiogroup">
                {(
                  [
                    {
                      id: "auto",
                      label: "Auto",
                      hint: "Default game behavior",
                    },
                    {
                      id: "loop",
                      label: "Force loop",
                      hint: "Overrides to loop",
                    },
                    {
                      id: "no-loop",
                      label: "Prevent loop",
                      hint: "Overrides to end",
                    },
                  ] as const
                ).map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    role="radio"
                    aria-checked={loopMode === opt.id}
                    className={`level-config-segment-btn${loopMode === opt.id ? " active" : ""}`}
                    onClick={() => setLoopMode(opt.id)}
                    title={opt.hint}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="level-config-flags">
              <label className="level-config-flag">
                <input
                  type="checkbox"
                  checked={!!entry.spawn_door_jellyfish}
                  onChange={(e) =>
                    patch(
                      "spawn_door_jellyfish",
                      e.target.checked || undefined,
                    )
                  }
                />
                <span>Spawn door jellyfish</span>
              </label>
              <label className="level-config-flag">
                <input
                  type="checkbox"
                  checked={!!entry.skip_co_fixes}
                  onChange={(e) =>
                    patch("skip_co_fixes", e.target.checked || undefined)
                  }
                />
                <span>Skip Cosmic Ocean fixes</span>
              </label>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
