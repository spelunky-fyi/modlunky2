// Filename / theme-id → biome resolver. Ports Python's
// `src/modlunky2/ui/levels/shared/biomes.py::Biomes` so both editors
// (Vanilla + Custom) pick the right floor tint and background PNG.
// Strings match Python's BIOME constants byte-for-byte so
// `getBiomeBackground(biome)` and `buildTileNameAtlas(names, biome)`
// on the Rust side (`FLOOR_BIOMES` in `level_editor.rs`) accept them
// without translation.

export type Biome =
  | "cave"
  | "jungle"
  | "volcano"
  | "olmec"
  | "temple"
  | "tidepool"
  | "ice"
  | "babylon"
  | "sunken"
  | "beehive"
  | "gold"
  | "duat"
  | "eggplant"
  | "surface";

/** Fallback used when no matcher / mapping fires. Matches Python's
 *  behavior of ending `Biomes.get_biome_for_level` with `return
 *  BIOME.DWELLING`. */
export const DEFAULT_BIOME: Biome = "cave";

/** Public-facing name for each biome. `cave` is the internal id for the
 *  Dwelling theme, `volcano` for Volcana, etc.; the UI should never surface
 *  the internal strings. */
export const BIOME_LABEL: Record<Biome, string> = {
  cave: "Dwelling",
  jungle: "Jungle",
  volcano: "Volcana",
  olmec: "Olmec",
  temple: "Temple",
  tidepool: "Tide Pool",
  ice: "Ice Caves",
  babylon: "Neo Babylon",
  sunken: "Sunken City",
  beehive: "Beehive",
  gold: "City of Gold",
  duat: "Duat",
  eggplant: "Eggplant World",
  surface: "Base Camp",
};

/** Representative theme id (from `LevelConfigPanel.THEMES`) for each biome.
 *  Inverse of `biomeForThemeId` for the non-ambiguous cases; used to turn a
 *  filename-derived biome back into a theme id (e.g. resolving the Cosmic
 *  Ocean subtheme of a `cosmicocean_*` file). Biomes with no dedicated theme
 *  (beehive) map to their closest relative and never surface as a subtheme. */
export const THEME_ID_FOR_BIOME: Record<Biome, number> = {
  cave: 1,
  jungle: 2,
  volcano: 3,
  olmec: 4,
  tidepool: 5,
  temple: 6,
  ice: 7,
  babylon: 8,
  sunken: 9,
  gold: 11,
  duat: 12,
  eggplant: 15,
  surface: 17,
  beehive: 2,
};

/** Deathmatch arena filenames use a `dm{N}` prefix where N is a
 *  1-based index into this ordered biome list. Matches Python's
 *  `dm_themes` array in `Biomes.get_biome_for_level`. */
const DM_THEMES: Biome[] = [
  "cave",
  "jungle",
  "volcano",
  "tidepool",
  "temple",
  "ice",
  "babylon",
  "sunken",
];

/** Filename → biome. Direct port of Python's
 *  `Biomes.get_biome_for_level(lvl)` in
 *  `src/modlunky2/ui/levels/shared/biomes.py`. Case-insensitive on the
 *  matches Python does with `startswith`/`endswith`.
 *
 *  Returns "cave" for anything the matcher doesn't recognize (basecamp
 *  and unknown filenames both land here on purpose). */
export function biomeForLevelFilename(fileName: string): Biome {
  const lvl = fileName.toLowerCase();

  if (
    lvl.startsWith("challenge_sun") ||
    lvl.startsWith("sunken") ||
    lvl.startsWith("hundun") ||
    lvl.startsWith("ending_hard") ||
    lvl.endsWith("_sunkencity.lvl")
  ) {
    return "sunken";
  }
  if (
    lvl.startsWith("abzu.lvl") ||
    lvl.startsWith("lake") ||
    lvl.startsWith("tide") ||
    lvl.startsWith("end") ||
    lvl.endsWith("_tidepool.lvl")
  ) {
    return "tidepool";
  }
  if (
    lvl.startsWith("babylon") ||
    lvl.startsWith("hallofu") ||
    lvl.endsWith("_babylon.lvl") ||
    lvl.startsWith("palace") ||
    lvl.startsWith("tiamat")
  ) {
    return "babylon";
  }
  if (lvl.startsWith("basecamp")) return "cave";
  if (lvl.startsWith("beehive")) return "beehive";
  if (
    lvl.startsWith("blackmark") ||
    lvl.startsWith("jungle") ||
    lvl.startsWith("challenge_moon") ||
    lvl.endsWith("_jungle.lvl")
  ) {
    return "jungle";
  }
  if (
    lvl.startsWith("challenge_star") ||
    lvl.startsWith("temple") ||
    lvl.endsWith("_temple.lvl")
  ) {
    return "temple";
  }
  if (lvl.startsWith("city")) return "gold";
  if (lvl.startsWith("duat")) return "duat";
  if (lvl.startsWith("egg")) return "eggplant";
  if (lvl.startsWith("ice") || lvl.endsWith("_icecavesarea.lvl")) return "ice";
  if (lvl.startsWith("olmec")) return "olmec";
  if (lvl.startsWith("vlad")) return "volcano";
  if (lvl.startsWith("volcano") || lvl.endsWith("_volcano.lvl")) return "volcano";

  for (let i = 0; i < DM_THEMES.length; i++) {
    if (lvl.startsWith(`dm${i + 1}`)) return DM_THEMES[i];
  }

  return DEFAULT_BIOME;
}

/** Theme id (from `LevelConfigPanel.THEMES`) → biome. Ports Python's
 *  `Biomes.biome_for_theme(theme, subtheme)`. Abzu falls back to Tide
 *  Pool, Tiamat to Neo Babylon, Hundun to Sunken City (they render the
 *  same biome art in the tkinter editor). Cosmic Ocean uses its
 *  subtheme when provided; when the subtheme is missing or Cosmic
 *  Ocean itself, returns "cave" (Python's ultimate fallback). */
export function biomeForThemeId(
  themeId: number | undefined,
  subthemeId?: number,
): Biome {
  switch (themeId) {
    case 1:
      return "cave"; // Dwelling
    case 2:
      return "jungle"; // Jungle
    case 3:
      return "volcano"; // Volcana
    case 4:
      return "olmec"; // Olmec
    case 5:
    case 13:
      return "tidepool"; // Tide Pool / Abzu
    case 6:
      return "temple"; // Temple
    case 7:
      return "ice"; // Ice Caves
    case 8:
    case 14:
      return "babylon"; // Neo Babylon / Tiamat
    case 9:
    case 16:
      return "sunken"; // Sunken City / Hundun
    case 10: {
      // Cosmic Ocean: recurse on the subtheme, otherwise cave.
      if (subthemeId != null && subthemeId !== 10) {
        return biomeForThemeId(subthemeId);
      }
      return "cave";
    }
    case 11:
      return "gold"; // City of Gold
    case 12:
      return "duat"; // Duat
    case 15:
      return "eggplant"; // Eggplant World
    case 17:
      return "surface"; // Base Camp
    default:
      return "cave";
  }
}
