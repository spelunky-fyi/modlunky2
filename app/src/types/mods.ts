// Mirrors the Rust structs in ml2_mods/src/data.rs plus the ModDto join
// added in the Tauri app crate. Kept close to the wire format so serde
// output maps directly.

export interface ManifestModFile {
  id: string;
  created_at: string;
  download_url: string;
}

export interface Manifest {
  name: string;
  slug: string;
  description: string;
  logo: string | null;
  mod_file: ManifestModFile;
}

export interface Mod {
  id: string;
  manifest: Manifest | null;
  hasUpdate: boolean;
  /** Folder mtime, ms since epoch. 0 when it couldn't be read. Installing and
   *  updating both replace the folder, so this reads as "when it landed". */
  modifiedAt: number;
  /** When the mod was last loaded into a running game, or null if it hasn't
   *  been since the app started recording. Not the same as `modifiedAt`:
   *  installing a mod isn't using it. */
  lastUsedAt: number | null;
  favorite: boolean;
}

/** What the inactive list is ordered by. Each field has its own natural
 *  direction (names read A-Z, dates read newest-first), so the default for
 *  `descending` depends on which one is picked. */
export type ModSort = "name" | "installed" | "used";

export const MOD_SORTS: ModSort[] = ["name", "installed", "used"];

export function isModSort(value: unknown): value is ModSort {
  return MOD_SORTS.includes(value as ModSort);
}

export const MOD_SORT_LABELS: Record<ModSort, string> = {
  name: "Name",
  installed: "Recently installed",
  used: "Recently used",
};

/** Alphabetical reads A-Z; both date sorts read newest-first. */
export function defaultDescending(sort: ModSort): boolean {
  return sort !== "name";
}

/** How tightly the mod rows are packed. Applies to both columns: it's about
 *  how much of the list fits on screen, which isn't a per-column concern. */
export type ModDensity = "comfortable" | "compact" | "dense";

export const MOD_DENSITIES: ModDensity[] = ["comfortable", "compact", "dense"];

export const DEFAULT_MOD_DENSITY: ModDensity = "comfortable";

export function isModDensity(value: unknown): value is ModDensity {
  return MOD_DENSITIES.includes(value as ModDensity);
}

export const MOD_DENSITY_LABELS: Record<ModDensity, string> = {
  comfortable: "Comfortable",
  compact: "Compact",
  dense: "Dense",
};

export type ManagerErrorKind =
  | "ModExistsError"
  | "ModNotFoundError"
  | "ModNonDirectoryError"
  | "ManifestParseError"
  | "SourceError"
  | "DestinationError"
  | "ChannelError"
  | "UnknownError";

export type ManagerError = { [K in ManagerErrorKind]?: string };
