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
}

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
