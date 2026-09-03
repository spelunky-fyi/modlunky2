import { invoke } from "@tauri-apps/api/core";
import type { Mod, ModProblem } from "../types/mods";
import type { ConfigPatch, SharedConfig } from "../types/config";
import type { DirectoryKind } from "../types/paths";
import type { SetupStatus } from "../types/setup";
import type { PlaylunkyReleaseInfo } from "../types/playlunky";
import type { PlaylunkyOptions } from "../types/playlunkyOptions";

export async function appVersion(): Promise<string> {
  return invoke<string>("app_version");
}

/** Modlunky2 self-version state. `latest === null` means the GitHub
 *  latest-release request failed (offline, rate-limited); `checkError`
 *  then carries why, so the UI can distinguish "couldn't check" from
 *  "up to date". `releasePageUrl` is a fallback when the in-place swap
 *  fails and the user needs to grab the exe manually. */
export interface ModlunkyVersionInfo {
  current: string;
  latest: string | null;
  updateAvailable: boolean;
  releasePageUrl: string;
  checkError: string | null;
}

export async function getModlunkyVersion(): Promise<ModlunkyVersionInfo> {
  return invoke<ModlunkyVersionInfo>("get_modlunky_version");
}

/** Renames the current exe to `<name>.backup.exe`, downloads the
 *  latest release exe over the original path, spawns it, exits us.
 *  Errors surface any file-system or download failure; the caller
 *  can point the user at `releasePageUrl` for manual recovery. */
export async function installUpdate(): Promise<void> {
  return invoke("install_update");
}

/// What the app still needs configured: the install directory, extracted
/// assets, and a spelunky.fyi token. One call so a tab can decide what to
/// render without chaining three.
export async function getSetupStatus(): Promise<SetupStatus> {
  return invoke<SetupStatus>("get_setup_status");
}

export async function listMods(): Promise<Mod[]> {
  return invoke<Mod[]>("list_mods");
}

/// Reads the mods folder direct from disk (or asks Rust's mod cache to
/// re-scan first), bypassing whatever the cache had. Use for the Refresh
/// button and after operations that touch the mods dir outside the
/// cache-managed flow (e.g. Level Editor's Create Pack).
export async function refreshMods(): Promise<Mod[]> {
  return invoke<Mod[]>("refresh_mods");
}

export async function getLoadOrder(): Promise<string[]> {
  return invoke<string[]>("get_load_order");
}

export async function setLoadOrder(active: string[]): Promise<void> {
  return invoke<void>("set_load_order", { active });
}

export async function getModLogo(id: string): Promise<string | null> {
  return invoke<string | null>("get_mod_logo", { id });
}

export async function removeMod(id: string): Promise<void> {
  return invoke<void>("remove_mod", { id });
}

export async function openModFolder(id: string): Promise<void> {
  return invoke<void>("open_mod_folder", { id });
}

/// Inspects one mod's files for defects that would break the game, caching
/// the result. Scoped to a single pack: cheap for one, prohibitive for the
/// several hundred a heavy user has installed.
export async function checkMod(id: string): Promise<ModProblem[]> {
  return invoke<ModProblem[]>("check_mod", { id });
}

/// Stars or unstars a mod. Stored per install alongside the mods themselves,
/// not in the shared config, because a mod id only means something relative
/// to one install's Packs folder.
export async function setModFavorite(
  id: string,
  favorite: boolean,
): Promise<void> {
  return invoke<void>("set_mod_favorite", { id, favorite });
}

export async function updateMod(id: string): Promise<Mod> {
  return invoke<Mod>("update_mod", { id });
}

export async function installFromFyi(
  code: string,
  overwrite: boolean,
): Promise<Mod> {
  return invoke<Mod>("install_from_fyi", { code, overwrite });
}

export async function installFromLocal(
  sourcePath: string,
  destId: string,
  overwrite: boolean,
): Promise<Mod> {
  return invoke<Mod>("install_from_local", {
    sourcePath,
    destId,
    overwrite,
  });
}

export async function listPackIds(): Promise<string[]> {
  return invoke<string[]>("list_pack_ids");
}

export async function rebuildMods(): Promise<void> {
  return invoke<void>("rebuild_mods");
}

/// spelunky.fyi push-install WebSocket lifecycle: kebab-case matches
/// the Rust `ConnectionStatus` enum's serde rename.
export type FyiWsStatus = "disconnected" | "connecting" | "connected";

export async function getFyiWsStatus(): Promise<FyiWsStatus> {
  return invoke<FyiWsStatus>("get_fyi_ws_status");
}

export async function refreshFyiWs(): Promise<void> {
  return invoke<void>("refresh_fyi_ws");
}

/// One line captured by the Rust-side tracing tap. camelCase matches
/// the log_buffer::LogEntry serde rename.
export interface LogEntry {
  /** Monotonic per-session sequence for dedupe. */
  seq: number;
  /** Unix millis. */
  tsMs: number;
  /** "trace" | "debug" | "info" | "warn" | "error". */
  level: LogLevel;
  target: string;
  message: string;
}

export type LogLevel = "trace" | "debug" | "info" | "warn" | "error";

export async function getRecentLogs(limit?: number): Promise<LogEntry[]> {
  return invoke<LogEntry[]>("get_recent_logs", { limit: limit ?? null });
}

export async function clearLogs(): Promise<void> {
  return invoke<void>("clear_logs");
}

export async function openLogsWindow(): Promise<void> {
  return invoke<void>("open_logs_window");
}

/// One entry in the Rust-side toast ring buffer, populated by the main
/// window's ToastProvider so the standalone Logs window can render the
/// full session's toast history even though the ref lives in the main
/// window's React tree.
export interface ToastRecord {
  id: string;
  variant: "info" | "success" | "warning" | "error";
  message: string;
  tsMs: number;
}

export async function recordToast(entry: ToastRecord): Promise<void> {
  return invoke<void>("record_toast", { entry });
}

export async function getRecentToasts(): Promise<ToastRecord[]> {
  return invoke<ToastRecord[]>("get_recent_toasts");
}

export async function clearToasts(): Promise<void> {
  return invoke<void>("clear_toasts");
}

export async function checkFyiUpdates(): Promise<number> {
  return invoke<number>("check_fyi_updates");
}

/* ---- Browsing the spelunky.fyi directory ----
 *
 * These come straight from ml2_mods, which deserializes them from the site's
 * API and hands them on untouched, so they keep the wire format's snake_case
 * exactly as `Manifest` in types/mods.ts does. Only DTOs the app crate defines
 * itself (BrowseArgs, LinkStart, LinkResult below) are camelCase.
 */

export interface FyiUser {
  username: string;
}

export interface FyiModFile {
  id: string;
  created_at: string;
  filename: string;
  downloads: number;
  download_url: string;
}

export interface PreviewImage {
  id: string;
  created_at: string;
  image_url: string;
}

/** One card in the browse grid. Deliberately has no `details`: mod markdown is
 *  never rendered in-app, it opens on the website via `web_url`. */
export interface ModListing {
  id: string;
  slug: string;
  name: string;
  description: string;
  web_url: string;
  submitter: FyiUser;
  collaborators: FyiUser[];
  mod_type: number | null;
  mod_type_display: string | null;
  game: number;
  game_display: string;
  /** The author's upload, or null. Prefer `logo_url`. */
  logo: string | null;
  /** Always set: the logo, or the spelunkicon generated from the slug. */
  logo_url: string;
  adult_content: boolean;
  favorited: boolean;
  downloads: number;
  rating_avg: number;
  rating_count: number;
  comment_count: number;
  favorites_count: number;
  created_at: string;
  listed_at: string | null;
  updated_at: string;
  latest_file: FyiModFile | null;
  /** Present because the browse command always asks for it. Carrying these on
   *  the listing is what lets the detail pane render screenshots with no
   *  second request. */
  preview_images: PreviewImage[];
}

export interface BrowsePage {
  count: number;
  next: string | null;
  previous: string | null;
  results: ModListing[];
}

/** Defined by the app crate, so camelCase. `game` is not a field: Modlunky is a
 *  Spelunky 2 tool and pins it rather than offering a control nobody wants. */
export interface BrowseArgs {
  q?: string;
  modType?: number;
  favorite?: boolean;
  rated?: string;
  orderBy?: string;
  limit?: number;
  offset?: number;
}

export interface BrowseChoice {
  value: string;
  label: string;
}

export interface ModTypeChoice {
  value: number;
  label: string;
  help_text: string;
}

/** The filter bar's options, fetched rather than hardcoded so a new mod type on
 *  the site shows up here without a Modlunky release. */
export interface BrowseOptions {
  game: number | null;
  mod_types: ModTypeChoice[];
  order_by: BrowseChoice[];
  default_order_by: string;
  rated: BrowseChoice[];
  allow_adult: boolean;
  hide_ratings: boolean;
}

/** Why a browse call failed. Tagged so the UI can offer a fix rather than
 *  matching on message text, which breaks the next time someone rewords one.
 *
 *  `needsAccount` means nothing is configured; `unauthorized` means something is
 *  and the site refused it, which is what a reset token looks like from here. */
export type BrowseError =
  | { kind: "needsAccount"; message: string }
  | { kind: "unauthorized"; message: string }
  | { kind: "failed"; message: string };

/** Narrows an unknown caught from a browse command. Anything that isn't one of
 *  our tagged shapes (a panic, a serialization failure) becomes `failed`, so
 *  callers always have something to render. */
export function asBrowseError(err: unknown): BrowseError {
  if (
    typeof err === "object" &&
    err !== null &&
    "kind" in err &&
    typeof (err as { kind: unknown }).kind === "string"
  ) {
    const tagged = err as BrowseError;
    if (
      tagged.kind === "needsAccount" ||
      tagged.kind === "unauthorized" ||
      tagged.kind === "failed"
    ) {
      return tagged;
    }
  }
  return { kind: "failed", message: String(err) };
}

/** True when an error from *any* command means the site refused our
 *  credentials. Install errors come back as ManagerError, which is tagged
 *  differently from BrowseError, so both spellings are checked here rather
 *  than at each call site. */
export function isAuthFailure(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  if ("Unauthorized" in err) return true; // ManagerError, from installs
  return (err as { kind?: unknown }).kind === "unauthorized";
}

export async function browseMods(args: BrowseArgs = {}): Promise<BrowsePage> {
  return invoke<BrowsePage>("browse_mods", { args });
}

export async function browseModOptions(): Promise<BrowseOptions> {
  return invoke<BrowseOptions>("browse_mod_options");
}

/** Asks the site whether the configured token still works. Resolves on
 *  success, rejects with a {@link BrowseError} otherwise.
 *
 *  There is no passive way to know a token has been reset on the website, so
 *  without this the first sign is a failed install. */
export async function verifyFyiAccount(): Promise<void> {
  return invoke<void>("verify_fyi_account");
}

/** App-crate DTO, so camelCase. */
export interface InstalledFyiMod {
  slug: string;
  hasUpdate: boolean;
}

/** What's already on disk, for the Installed and Update badges. The one thing
 *  a browse tab can show that the website cannot. */
export async function installedFyiMods(): Promise<InstalledFyiMod[]> {
  return invoke<InstalledFyiMod[]>("installed_fyi_mods");
}

/* ---- Linking a spelunky.fyi account ---- */

export interface LinkStart {
  /** Open this, and show it too: opening a browser fails on a Steam Deck in
   *  Game Mode, so the user needs something they can copy. */
  url: string;
  port: number;
}

export type LinkResult =
  | { status: "linked"; username: string }
  | { status: "failed"; message: string }
  | { status: "cancelled" };

/** Event name carrying a {@link LinkResult} when an attempt finishes. */
export const ACCOUNT_LINK_EVENT = "account-link";

/** Starts a link and returns immediately. The outcome arrives later on
 *  {@link ACCOUNT_LINK_EVENT}, so the caller should be listening first. */
export async function startAccountLink(): Promise<LinkStart> {
  return invoke<LinkStart>("start_account_link");
}

export async function cancelAccountLink(): Promise<void> {
  return invoke<void>("cancel_account_link");
}

export async function clearPlaylunkyCache(): Promise<void> {
  return invoke<void>("clear_playlunky_cache");
}

export async function listInstalledPlaylunky(): Promise<string[]> {
  return invoke<string[]>("list_installed_playlunky");
}

export async function listPlaylunkyReleases(
  force = false,
): Promise<PlaylunkyReleaseInfo[]> {
  return invoke<PlaylunkyReleaseInfo[]>("list_playlunky_releases", { force });
}

export async function downloadPlaylunkyVersion(tag: string): Promise<void> {
  return invoke<void>("download_playlunky_version", { tag });
}

export async function removePlaylunkyVersion(tag: string): Promise<void> {
  return invoke<void>("remove_playlunky_version", { tag });
}

export async function launchPlaylunky(): Promise<void> {
  return invoke<void>("launch_playlunky");
}

/** Launches the game with neither Playlunky nor Overlunky attached. */
export async function launchVanilla(): Promise<void> {
  return invoke<void>("launch_vanilla");
}

/** Starts the game with the requested tools, and remembers the choice.
 *  The backend owns the mapping from "which tools" to "which launcher",
 *  including that Playlunky + Overlunky is one launch rather than two.
 *  With Playlunky selected and nothing installed, it downloads nightly
 *  first, so this can take a while on a fresh setup. */
export async function launchGame(
  withPlaylunky: boolean,
  withOverlunky: boolean,
): Promise<void> {
  return invoke<void>("launch_game", { withPlaylunky, withOverlunky });
}

export async function getPlaylunkyOptions(): Promise<PlaylunkyOptions> {
  return invoke<PlaylunkyOptions>("get_playlunky_options");
}

export async function setPlaylunkyOptions(
  options: PlaylunkyOptions,
): Promise<void> {
  return invoke<void>("set_playlunky_options", { options });
}

export async function syncDesktopShortcut(): Promise<void> {
  return invoke<void>("sync_desktop_shortcut");
}

export interface ExtractOptions {
  extractWav: boolean;
  extractOgg: boolean;
  reuseExtracted: boolean;
  generateStringHashes: boolean;
  createEntitySprites: boolean;
}

export async function listExtractableExes(): Promise<string[]> {
  return invoke<string[]>("list_extractable_exes");
}

export async function extractAssets(
  exeRelative: string,
  options: ExtractOptions,
): Promise<void> {
  return invoke<void>("extract_assets", {
    exeRelative,
    options,
  });
}

export interface ExtractStatus {
  phase: string;
  done: number | null;
  total: number | null;
}

/** Snapshot of the currently-running extract, or null if idle. Used by the
 *  ExtractPage's mount to resume progress after nav-away-and-back. */
export async function getExtractStatus(): Promise<ExtractStatus | null> {
  return invoke<ExtractStatus | null>("get_extract_status");
}

/** True iff `Mods/Extracted/Data/Textures/` under the install dir is
 *  non-empty. Editors gate their UI on this: sprite lookups without
 *  extracted assets return placeholders for every tile. */
export async function extractedAssetsAvailable(): Promise<boolean> {
  return invoke<boolean>("extracted_assets_available");
}

export type OverlunkyLaunchMode = "inject" | "launchGame" | "update";

export async function isOverlunkyInstalled(): Promise<boolean> {
  return invoke<boolean>("is_overlunky_installed");
}

export async function downloadOverlunky(): Promise<void> {
  return invoke<void>("download_overlunky");
}

export async function launchOverlunky(
  mode: OverlunkyLaunchMode,
): Promise<void> {
  return invoke<void>("launch_overlunky", { mode });
}

export async function getConfig(): Promise<SharedConfig> {
  return invoke<SharedConfig>("get_config");
}

export async function setConfig(patch: ConfigPatch): Promise<void> {
  return invoke<void>("set_config", { patch });
}

export async function guessInstallDir(): Promise<string | null> {
  return invoke<string | null>("guess_install_dir");
}

export async function openDirectory(kind: DirectoryKind): Promise<void> {
  return invoke<void>("open_directory", { kind });
}

export interface EditorAtlasTile {
  name: string;
  x: number;
  y: number;
  w: number;
  h: number;
  /** Sprite's natural footprint in grid cells. >1 means the tile draws
   *  wider or taller than a single cell. */
  natWCells: number;
  natHCells: number;
  /** Anchor offsets in grid cells. Positive x shifts the sprite LEFT of
   *  its placement cell; positive y shifts it UP. Zero for tiles without
   *  an explicit anchor (they draw with the placement cell as the
   *  sprite's top-left corner). Derived from Python's draw_mode table. */
  anchorXCells: number;
  anchorYCells: number;
}

export interface EditorAtlas {
  pngDataUrl: string;
  width: number;
  height: number;
  tileSize: number;
  tiles: EditorAtlasTile[];
}

export async function buildEditorAtlas(biome: string): Promise<EditorAtlas> {
  return invoke<EditorAtlas>("build_editor_atlas", { biome });
}

export type EditorMode = "vanilla" | "custom";

export function editorModeLabel(mode: EditorMode): string {
  return mode === "vanilla" ? "Vanilla" : "Custom";
}

export async function listLevelPacks(mode: EditorMode): Promise<string[]> {
  return invoke<string[]>("list_level_packs", { mode });
}

export async function createLevelPack(
  name: string,
  mode: EditorMode,
): Promise<string> {
  return invoke<string>("create_level_pack", { name, mode });
}

export async function openLevelEditorWindow(
  pack: string,
  mode: EditorMode,
): Promise<void> {
  return invoke<void>("open_level_editor_window", { pack, mode });
}

/** Opens a read-only preview window pinned to one vanilla room. Re-opening the
 *  same room focuses its existing window. */
export async function openRoomPreviewWindow(
  pack: string,
  fileName: string,
  template: string,
  roomIndex: number,
): Promise<void> {
  return invoke<void>("open_room_preview_window", {
    pack,
    fileName,
    template,
    roomIndex,
  });
}

// --- Character chooser -----------------------------------------------------

/** How confident detection is that a file is a character sheet. */
export type CharacterConfidence = "definite" | "likely" | "possible";

/** The `char_<color>.json` metadata a mod can ship. */
export interface CharacterMeta {
  fullName: string | null;
  shortName: string | null;
  color: string | null;
  gender: string | null;
}

/** One discovered character-sheet file inside a pack. */
export interface CharacterCandidate {
  packId: string;
  /** Forward-slash path of the PNG relative to the pack root. */
  relPath: string;
  fileName: string;
  /** True `_full` nature by dimensions (2048x2224), not the filename. */
  isFull: boolean;
  /** The filename's `_full` suffix disagrees with the dimensions. */
  nameMismatch: boolean;
  width: number;
  height: number;
  /** Whether the dimensions match a real char sheet. */
  dimsOk: boolean;
  /** Known slot color it currently occupies (`char_<color>`), or null. */
  detectedColor: string | null;
  confidence: CharacterConfidence;
  /** Paired metadata sidecar (`char_<color>.json` or `.name`), if found. */
  metaRelPath: string | null;
  metadata: CharacterMeta | null;
  /** Whether the pack is active in the load order. */
  active: boolean;
  /** Load-order position (lower wins a slot conflict); null when inactive. */
  loadRank: number | null;
  /** User flagged this file as "not a character" so it stays hidden. */
  ignored: boolean;
  /** User confirmed a "possible" file is a character (promoted to the pool). */
  confirmed: boolean;
  /** If the chooser renamed this file, the path it was originally shipped
   *  under (so the UI can show it's assigned and offer restore). */
  originalRelPath: string | null;
  /** The chooser disabled this file (renamed it out of its slot). */
  userDisabled: boolean;
  /** The chooser unassigned this file (removed from a slot, kept available). */
  userUnassigned: boolean;
}

/** A vanilla character slot. */
export interface CharacterSlot {
  color: string;
  fullName: string;
  shortName: string;
}

export interface CharactersResponse {
  slots: CharacterSlot[];
  candidates: CharacterCandidate[];
}

/** Discover character-sheet candidates. Scans only active mods by default;
 *  `includeInactive` widens to all packs, or `packId` scopes to one pack. */
export async function getCharacters(
  includeInactive = false,
  packId: string | null = null,
): Promise<CharactersResponse> {
  return invoke<CharactersResponse>("get_characters", {
    includeInactive,
    packId,
  });
}

/** Portrait preview of a candidate sheet (cropped from the mod's own file). */
export async function getCharacterPreview(
  packId: string,
  relPath: string,
): Promise<string> {
  return invoke<string>("get_character_preview", { packId, relPath });
}

/** Portrait of the vanilla character a slot replaces, cropped/cached from the
 *  user's extracted assets. Null when assets were never extracted. */
export async function getVanillaCharacterPreview(
  color: string,
): Promise<string | null> {
  return invoke<string | null>("get_vanilla_character_preview", { color });
}

/** Opens the character chooser window. Pass a pack id to scope it to a single
 *  pack (the per-pack variant); omit for the global active-mods view. */
export async function openCharacterChooserWindow(
  pack: string | null = null,
): Promise<void> {
  return invoke<void>("open_character_chooser_window", { pack });
}

/** Flag (or un-flag) a pack file as "not a character" so the chooser hides it. */
export async function setCharacterIgnored(
  packId: string,
  relPath: string,
  ignored: boolean,
): Promise<void> {
  return invoke<void>("set_character_ignored", { packId, relPath, ignored });
}

/** Confirm (or un-confirm) that a "possible" file is a character, promoting it
 *  out of the review bucket into the usable pool. */
export async function setCharacterConfirmed(
  packId: string,
  relPath: string,
  confirmed: boolean,
): Promise<void> {
  return invoke<void>("set_character_confirmed", {
    packId,
    relPath,
    confirmed,
  });
}

/** Assign a character sheet to a slot: renames the PNG (+ sidecar) to the
 *  canonical `char_<color>` path. Also fixes `_full` naming when the target
 *  color is the file's own. */
export async function assignCharacter(
  packId: string,
  relPath: string,
  color: string,
): Promise<void> {
  return invoke<void>("assign_character", { packId, relPath, color });
}

/** Disable a character sheet (rename it out of its slot so it stops loading). */
export async function disableCharacter(
  packId: string,
  relPath: string,
): Promise<void> {
  return invoke<void>("disable_character", { packId, relPath });
}

/** Unassign a character sheet: remove it from its slot but keep it available
 *  in the pool (`char_unassigned<N>`) rather than disabling it. */
export async function unassignCharacter(
  packId: string,
  relPath: string,
): Promise<void> {
  return invoke<void>("unassign_character", { packId, relPath });
}

/** Restore a renamed/disabled character to the path it shipped under. */
export async function restoreCharacter(
  packId: string,
  relPath: string,
): Promise<void> {
  return invoke<void>("restore_character", { packId, relPath });
}

/** Ordered list of packs the user has recently opened in the given editor
 *  mode, most-recent first. Capped at 5 on the backend. */
export async function listRecentPacks(mode: EditorMode): Promise<string[]> {
  return invoke<string[]>("list_recent_packs", { mode });
}

/** Bumps a pack to the head of the recents list for the given mode.
 *  Idempotent: existing entries move to the front instead of duplicating. */
export async function pushRecentPack(
  mode: EditorMode,
  pack: string,
): Promise<void> {
  return invoke<void>("push_recent_pack", { mode, pack });
}

/** Removes a pack from the recents list for the given mode. */
export async function removeRecentPack(
  mode: EditorMode,
  pack: string,
): Promise<void> {
  return invoke<void>("remove_recent_pack", { mode, pack });
}

/** State of the LevelSequence Lua library inside a pack. */
export interface LevelSequenceStatus {
  /** True if `<pack>/LevelSequence/` exists on disk. */
  folderExists: boolean;
  /** Version tag we installed (e.g. "v3.0"). Null when the folder exists
   *  but no version marker is present (typically because it was managed
   *  outside the editor, e.g. via git). */
  installedVersion: string | null;
}

export async function getLevelSequenceStatus(
  pack: string,
): Promise<LevelSequenceStatus> {
  return invoke<LevelSequenceStatus>("get_level_sequence_status", { pack });
}

/** Fetches the latest published tag of the LevelSequence library from
 *  GitHub. Callers compare against `LevelSequenceStatus.installedVersion`
 *  to decide whether an update is available. */
export async function checkLatestLevelSequence(): Promise<string> {
  return invoke<string>("check_latest_level_sequence");
}

/** Downloads and installs the latest LevelSequence release into the
 *  pack. Returns the tag that landed on disk. */
export async function installLevelSequence(pack: string): Promise<string> {
  return invoke<string>("install_level_sequence", { pack });
}

export interface CustomLevelPaletteEntry {
  name: string;
  code: string;
  comment: string | null;
}

export interface CustomLevelData {
  fileName: string;
  widthRooms: number;
  heightRooms: number;
  widthTiles: number;
  heightTiles: number;
  foreground: string[][];
  /** Same shape as `foreground`. Cells the author never touched in the back
   *  layer come back as empty strings; those cells stay unsaved when the
   *  file round-trips through save_custom_level. */
  background: string[][];
  palette: CustomLevelPaletteEntry[];
  /** The save format the file was recognised as. Null means load couldn't
   *  detect any known format; the recovery flow uses `suggestedFormat`
   *  to prefill the "define a format" dialog. */
  detectedFormat: CustomLevelSaveFormat | null;
  /** Best-guess template pattern derived from the file's actual template
   *  names. Only populated when `detectedFormat` is null. */
  suggestedFormat: string | null;
  /** Theme id inferred from the (0,0) setroom template's biome-name
   *  comment. Populated when that comment is a recognised biome name
   *  (e.g. `"cave"`, `"jungle"`). Used as the default theme for files
   *  with no `level_configuration.ls` entry, so an authored theme
   *  survives the round trip through a file that never entered the
   *  sequence config. Null when detection failed. */
  detectedTheme: number | null;
}

export async function listCustomLevels(pack: string): Promise<string[]> {
  return invoke<string[]>("list_custom_levels", { pack });
}

/** Opens a pack's .lvl file with the OS default program (on Windows, the
 *  "how do you want to open this?" prompt when no default is set). */
export async function openLevelFile(
  pack: string,
  fileName: string,
): Promise<void> {
  return invoke<void>("open_level_file", { pack, fileName });
}

/** Opens a pack's .lvl file in an external program the user picks. On Windows
 *  this shows the native "Open with" chooser; elsewhere the OS default
 *  handler. An escape hatch for files the built-in editor can't handle. */
export async function openLevelFileWith(
  pack: string,
  fileName: string,
): Promise<void> {
  return invoke<void>("open_level_file_with", { pack, fileName });
}

export async function loadCustomLevel(
  pack: string,
  fileName: string,
  /** Ordered list of formats to try when detecting which naming scheme
   *  the file uses. Callers usually pass `[defaultFormat, ...userDefined,
   *  ...builtIn]` so the pack's preference wins. */
  knownFormats: CustomLevelSaveFormat[],
): Promise<CustomLevelData> {
  return invoke<CustomLevelData>("load_custom_level", {
    pack,
    fileName,
    knownFormats,
  });
}

export async function saveCustomLevel(
  pack: string,
  fileName: string,
  foreground: string[][],
  background: string[][],
  palette: CustomLevelPaletteEntry[],
  /** LevelConfiguration.theme for this file. Pass null when the pack has
   *  no config entry yet; that skips the special-theme vanilla-setroom
   *  mirror emission on the Rust side. */
  theme: number | null,
  /** Setroom template naming scheme + mirror policy for the write. Pass
   *  null to keep the backend's legacy auto-detect (underscore vs dash)
   *  which is how the initial rewrite worked. Callers that know the
   *  format always pass Some so `convert format` and Vanilla-format
   *  packs land on the right template names. */
  saveFormat: CustomLevelSaveFormat | null,
): Promise<void> {
  return invoke<void>("save_custom_level", {
    pack,
    fileName,
    foreground,
    background,
    palette,
    theme,
    saveFormat,
  });
}

// level_configuration.ls uses snake_case field names on disk to match the
// tkinter app's serde-python output, and we pass them through unchanged for
// full pack interoperability. Do NOT camelCase these.
export interface LevelConfiguration {
  identifier: string;
  name: string;
  file_name: string;
  theme: number;
  subtheme?: number;
  /** Only used for Cosmic Ocean levels. */
  width?: number;
  /** Only used for Cosmic Ocean levels. */
  height?: number;
  border_theme?: number;
  loop?: boolean;
  dont_loop?: boolean;
  border_entity_theme?: number;
  floor_theme?: number;
  background_theme?: number;
  background_texture_theme?: number;
  music_theme?: number;
  skip_co_fixes?: boolean;
  spawn_door_jellyfish?: boolean;
}

export interface LevelConfigurations {
  sequence: LevelConfiguration[];
  all_configurations?: Record<string, LevelConfiguration>;
}

export async function loadCustomConfig(
  pack: string,
): Promise<LevelConfigurations> {
  return invoke<LevelConfigurations>("load_custom_config", { pack });
}

export async function saveCustomConfig(
  pack: string,
  config: LevelConfigurations,
): Promise<void> {
  return invoke<void>("save_custom_config", { pack, config });
}

/**
 * Save format for a custom .lvl. Determines how setroom templates are
 * named on disk. Uses snake_case field names so the wire type round-trips
 * with tkinter's `CustomLevelSaveFormat` and its serde_python JSON, same
 * pattern as [[LevelConfiguration]].
 */
export interface CustomLevelSaveFormat {
  name: string;
  /** Template string with `{y}` and `{x}` placeholders. Both must appear
   *  exactly once. Common values are `setroom{y}_{x}` for LevelSequence
   *  packs and `setroom{y}-{x}` for Vanilla replacement mods. */
  room_template_format: string;
  /** Only meaningful on save: whether to also emit dash-format setroom
   *  mirrors on the boss / special themes vanilla's engine reads out of
   *  the old naming. Off for Vanilla format (main templates ARE the dash
   *  mirrors already); on for LevelSequence unless the author opts out. */
  include_vanilla_setrooms: boolean;
}

/** Modern LevelSequence pack format. Recommended for new packs. */
export const LEVEL_SEQUENCE_FORMAT: CustomLevelSaveFormat = {
  name: "LevelSequence",
  room_template_format: "setroom{y}_{x}",
  include_vanilla_setrooms: true,
};

/** Vanilla setroom format. Retained for compatibility with old-style
 *  replacement mods that predate LevelSequence. Warning label matches
 *  Python's UI wording. */
export const VANILLA_SETROOM_FORMAT: CustomLevelSaveFormat = {
  name: "Vanilla setroom [warning]",
  room_template_format: "setroom{y}-{x}",
  include_vanilla_setrooms: false,
};

/** Two built-in formats. User-defined formats come from
 *  `listCustomSaveFormats` and get unioned with these at the UI layer. */
export const BUILT_IN_SAVE_FORMATS: readonly CustomLevelSaveFormat[] = [
  LEVEL_SEQUENCE_FORMAT,
  VANILLA_SETROOM_FORMAT,
];

/** True iff the format's name matches one of the built-ins. */
export function isBuiltInSaveFormat(f: CustomLevelSaveFormat): boolean {
  return BUILT_IN_SAVE_FORMATS.some((b) => b.name === f.name);
}

/** User-authored setroom template formats persisted in the shared
 *  config.json. Built-ins live in the frontend so we don't over-sync. */
export async function listCustomSaveFormats(): Promise<
  CustomLevelSaveFormat[]
> {
  return invoke<CustomLevelSaveFormat[]>("list_custom_save_formats");
}

export async function addCustomSaveFormat(
  format: CustomLevelSaveFormat,
): Promise<void> {
  return invoke<void>("add_custom_save_format", { format });
}

export async function removeCustomSaveFormat(name: string): Promise<void> {
  return invoke<void>("remove_custom_save_format", { name });
}

/** Pack-wide default. Falls back to LEVEL_SEQUENCE_FORMAT at the UI when
 *  the backend returns null (no default set yet). */
export async function getDefaultSaveFormat(): Promise<CustomLevelSaveFormat | null> {
  return invoke<CustomLevelSaveFormat | null>("get_default_save_format");
}

export async function setDefaultSaveFormat(
  format: CustomLevelSaveFormat | null,
): Promise<void> {
  return invoke<void>("set_default_save_format", { format });
}

/** How the canvas zooms when a room first renders. */
export type ZoomMode = "fit" | "fixed" | "remember";

/** App-wide level-editor UI preferences, shared by both editors and the
 *  splash settings. Persisted as one object in the shared config.json. */
export interface EditorPrefs {
  zoomMode: ZoomMode;
  /** Percent zoom used when zoomMode is "fixed". */
  fixedZoomPct: number;
  clampRender: boolean;
  showTileGrid: boolean;
  showRoomGrid: boolean;
  /** Collapse the palette to icon-only swatches that wrap into a dense grid.
   *  Shared by both editors; reorder mode ignores it and stays expanded. */
  paletteDense: boolean;
  /** Whether saving pops a confirmation dialog first. Default true. */
  confirmSave: boolean;
  /** Whether adding a room from the context menu pops a confirmation dialog
   *  first. Default true. */
  confirmAddRoom: boolean;
}

export const DEFAULT_EDITOR_PREFS: EditorPrefs = {
  zoomMode: "fit",
  fixedZoomPct: 100,
  clampRender: false,
  showTileGrid: true,
  showRoomGrid: true,
  paletteDense: false,
  confirmSave: true,
  confirmAddRoom: true,
};

/** Canvas zoom limits (scale factor), mirrored from TileCanvas so the
 *  settings UI can clamp the Fixed-zoom percent to a valid range. */
export const MIN_ZOOM_PCT = 25;
export const MAX_ZOOM_PCT = 800;

export async function getEditorPrefs(): Promise<EditorPrefs> {
  return invoke<EditorPrefs>("get_editor_prefs");
}

export async function setEditorPrefs(prefs: EditorPrefs): Promise<void> {
  return invoke<void>("set_editor_prefs", { prefs });
}

/**
 * Creates a blank .lvl in the pack. Returns the on-disk file name after
 * the backend's validation (e.g. `.lvl` extension added if missing).
 */
export async function createCustomLevel(
  pack: string,
  fileName: string,
  widthRooms: number,
  heightRooms: number,
  roomTemplateFormat: string,
): Promise<string> {
  return invoke<string>("create_custom_level", {
    pack,
    fileName,
    widthRooms,
    heightRooms,
    roomTemplateFormat,
  });
}

/**
 * Renames a level file in the pack. Returns the sanitized new name that
 * ended up on disk.
 */
export async function renameCustomLevel(
  pack: string,
  oldFileName: string,
  newFileName: string,
): Promise<string> {
  return invoke<string>("rename_custom_level", {
    pack,
    oldFileName,
    newFileName,
  });
}

/**
 * Deletes a level file after making a timestamped backup under
 * `Mods/Backups/<pack>/`.
 */
export async function deleteCustomLevel(
  pack: string,
  fileName: string,
): Promise<void> {
  return invoke<void>("delete_custom_level", { pack, fileName });
}

// Rust enum variants come across as camelCase per `#[serde(rename_all = ...)]`.
export type VanillaLevelSource = "vanilla" | "modded" | "custom";

export interface VanillaLevelListEntry {
  fileName: string;
  source: VanillaLevelSource;
}

export interface VanillaRoom {
  settings: string[];
  foreground: string[][];
  background: string[][];
  width: number;
  height: number;
  comment: string | null;
  isDual: boolean;
}

export interface VanillaTemplate {
  name: string;
  comment: string | null;
  rooms: VanillaRoom[];
}

export interface RulesEntry {
  name: string;
  value: string;
  comment: string | null;
}

export interface EditedRules {
  levelSettings?: RulesEntry[];
  levelChances?: RulesEntry[];
  monsterChances?: RulesEntry[];
}

export interface DependencyPalette {
  /** Sister-location file name, e.g. "junglearea.lvl". Palette section
   *  header. */
  fileName: string;
  /** Whether this sister came from the pack (Modded) or extracts
   *  (Vanilla). Hint for the section header. */
  source: VanillaLevelSource;
  /** The sister's tile-code entries. */
  palette: CustomLevelPaletteEntry[];
}

export interface VanillaLevelData {
  fileName: string;
  source: VanillaLevelSource;
  templates: VanillaTemplate[];
  palette: CustomLevelPaletteEntry[];
  levelSettings: RulesEntry[];
  levelChances: RulesEntry[];
  monsterChances: RulesEntry[];
  /** Every sister-location file's palette. Rendered as separate sections
   *  below the main palette. Also feeds collision-aware code allocation
   *  so a fresh tilecode won't collide with an inherited code. */
  dependencyPalettes: DependencyPalette[];
  /** Theme id from the file's tool-owned comment marker, if the author set
   *  one. `null` means fall back to the filename-derived biome. */
  detectedTheme: number | null;
  /** Subtheme id from the same marker (only meaningful for Cosmic Ocean). */
  detectedSubtheme: number | null;
}

export interface EditedRoom {
  foreground: string[][];
  background: string[][];
  /** Lowercase template-setting names. Fully replaces the room's settings
   *  on save; ship the current in-memory list even for untouched rooms. */
  settings: string[];
  comment: string | null;
}

/** The eight template-setting flags a room can carry. Wire format is
 *  lowercase to match ml2_levels::TemplateSetting::as_str. */
export const TEMPLATE_SETTING_NAMES = [
  "ignore",
  "flip",
  "onlyflip",
  "dual",
  "rare",
  "hard",
  "liquid",
  "purge",
] as const;

export type TemplateSettingName = (typeof TEMPLATE_SETTING_NAMES)[number];

export const TEMPLATE_SETTING_LABELS: Record<TemplateSettingName, string> = {
  ignore: "Ignore",
  flip: "Flip",
  onlyflip: "Only flip",
  dual: "Dual",
  rare: "Rare",
  hard: "Hard",
  liquid: "Liquid",
  purge: "Purge",
};

export const TEMPLATE_SETTING_HINTS: Record<TemplateSettingName, string> = {
  ignore: "Skip this room. Useful as a scratchpad the game won't spawn.",
  flip: "Also produce a mirrored variant.",
  onlyflip: "Replace with the mirrored variant (original is ignored).",
  dual: "Two-layer room (foreground + background painted separately).",
  rare: "Only about a 5% chance of spawning.",
  hard: "Only appears in the second two levels of the area.",
  liquid: "Room contains liquid; counts toward the liquid budget.",
  purge: "Force-purge any entities the room replaces.",
};

export interface EditedTemplate {
  name: string;
  comment: string | null;
  rooms: EditedRoom[];
}

export async function listVanillaLevels(
  pack: string,
): Promise<VanillaLevelListEntry[]> {
  return invoke<VanillaLevelListEntry[]>("list_vanilla_levels", { pack });
}

export async function loadVanillaLevel(
  pack: string,
  fileName: string,
): Promise<VanillaLevelData> {
  return invoke<VanillaLevelData>("load_vanilla_level", { pack, fileName });
}

export async function saveVanillaLevel(
  pack: string,
  fileName: string,
  editedTemplates: EditedTemplate[],
  palette: CustomLevelPaletteEntry[],
  editedRules: EditedRules | null = null,
  // Desired per-file theme override. `theme = null` clears any marker (reset
  // to the filename-derived biome); the backend only rewrites the file's top
  // comment when this differs from what's already stored.
  theme: number | null = null,
  subtheme: number | null = null,
): Promise<void> {
  return invoke<void>("save_vanilla_level", {
    pack,
    fileName,
    editedTemplates,
    palette,
    editedRules,
    theme,
    subtheme,
  });
}

export async function listValidLevelSettings(): Promise<string[]> {
  return invoke<string[]>("list_valid_level_settings");
}

export async function listValidLevelChances(): Promise<string[]> {
  return invoke<string[]>("list_valid_level_chances");
}

export async function listValidMonsterChances(): Promise<string[]> {
  return invoke<string[]>("list_valid_monster_chances");
}

export async function buildTileNameAtlas(
  names: string[],
  biome: string | null = null,
): Promise<EditorAtlas> {
  return invoke<EditorAtlas>("build_tile_name_atlas", { names, biome });
}

export async function listShortCodes(): Promise<string[]> {
  return invoke<string[]>("list_short_codes");
}

export async function listValidTileCodes(): Promise<string[]> {
  return invoke<string[]>("list_valid_tile_codes");
}

export async function getBiomeBackground(biome: string): Promise<string> {
  return invoke<string>("get_biome_background", { biome });
}

/** Bundled Cosmic Ocean starfield backdrop as a data URL. Never fails; the
 *  PNG is compiled into the app so no game extract is required. Layered
 *  behind the biome background when the current level's theme is Cosmic
 *  Ocean. Matches Python's `static/images/cosmos.png`. */
export async function getCosmicBackdrop(): Promise<string> {
  return invoke<string>("get_cosmic_backdrop");
}

/** Per-subtheme Cosmic Ocean decoration crop from
 *  `Data/Textures/deco_cosmic.png` (512x512, PNG data URL). Python's editor
 *  scatters this crop as 31 rotated/scaled sprites over the starfield when
 *  the background theme is Cosmic Ocean; TileCanvas does the same when it's
 *  provided. Returns null if the extract hasn't produced deco_cosmic.png
 *  yet, in which case the backdrop still tiles but decorations are omitted. */
export async function getCosmicSubthemeDecoration(
  subthemeId: number,
): Promise<string | null> {
  return invoke<string | null>("get_cosmic_subtheme_decoration", {
    subthemeId,
  });
}

export interface TileSprite {
  pngDataUrl: string;
  tileSize: number;
}

export async function getTileSprite(
  name: string,
  biome: string | null = null,
): Promise<TileSprite> {
  return invoke<TileSprite>("get_tile_sprite", { name, biome });
}

export interface NaturalTileSprite {
  pngDataUrl: string;
  tileSize: number;
  natWCells: number;
  natHCells: number;
  anchorXCells: number;
  anchorYCells: number;
}

/** Renders a tile at its natural multi-cell size plus its footprint/anchor
 *  metadata, so the add-tile flow can draw a new multi-cell tile correctly
 *  without waiting for a full atlas rebuild. */
export async function getTileSpriteNatural(
  name: string,
  biome: string | null = null,
): Promise<NaturalTileSprite> {
  return invoke<NaturalTileSprite>("get_tile_sprite_natural", { name, biome });
}

export interface NamedTileSprite {
  name: string;
  pngDataUrl: string;
  tileSize: number;
}

/** Renders a batch of tiles to individual sprite data URLs in one call
 *  (one shared sheet load for the whole batch). Used by the add-tile
 *  dropdown to fetch a windowed set of swatches as you scroll. */
export async function renderTileSprites(
  names: string[],
  biome: string | null = null,
): Promise<NamedTileSprite[]> {
  return invoke<NamedTileSprite[]>("render_tile_sprites", { names, biome });
}

// ---------------------------------------------------------------------
// Trackers
// ---------------------------------------------------------------------

export interface TrackerServerStatus {
  running: boolean;
  /** Bound port when running, else null. */
  port: number | null;
}

/** TrackerPayload envelope matching the Rust `TrackerPayload` enum.
 *  Discriminated by `type`; every WS message from the server also uses
 *  this shape. */
export type TrackerPayload =
  | { type: "Empty" }
  | { type: "Detached" }
  | { type: "Category"; data: { text: string; final_death: boolean } }
  | {
    type: "Pacifist";
    data: { text: string; broken: boolean; kills_total: number };
  }
  | { type: "Timer"; data: { text: string } }
  | { type: "Gem"; data: { text: string } }
  | { type: "PacinoGolf"; data: { text: string } }
  | { type: "Co"; data: { text: string } }
  | { type: "Failure"; data: string };

export interface CategoryTrackerConfig {
  /** Whether the modifier labels (No%, No Gold, etc) always appear or
   *  only after the run passes the "clearly not that category" gate.
   *  Serialized to kebab-case on-disk to match Python. */
  "always-show-modifiers": boolean;
  "excluded-categories": SaveableCategory[];
}

export type SaveableCategory = "No%" | "No Gold" | "Pacifist" | "Score";

export interface PacifistTrackerConfig {
  /** When true, the broken label reads `MURDERED n!` with the running
   *  kill count. When false it just says `MURDERER!`. Kebab-case on
   *  disk to match Python. */
  "show-kill-count": boolean;
}

/** Six booleans matching Python's TimerTrackerConfig. Defaults live
 *  on the Rust side (total/level/last-level on, rest off) and are
 *  serialized with skip_if_default so unchanged users have no
 *  `trackers.timer` block in modlunky2.json. */
export interface TimerTrackerConfig {
  "show-total": boolean;
  "show-level": boolean;
  "show-last-level": boolean;
  "show-tutorial": boolean;
  "show-session": boolean;
  "show-ils": boolean;
}

export interface GemTrackerConfig {
  "show-total-gem-count": boolean;
  "show-colored-gem-count": boolean;
  "show-diamond-count": boolean;
  "show-yem-count": boolean;
  "show-diamond-percentage": boolean;
}

export interface PacinoGolfTrackerConfig {
  "show-total-strokes": boolean;
  "show-resource-strokes": boolean;
  "show-treasure-strokes": boolean;
  "show-pacifist-strokes": boolean;
}

/** Serialized as the same string values Python used
 *  ("Full theme names", "Short theme names", ...). Kept literal so a
 *  modlunky2.json round-trips exactly. */
export type ThemeNameStyle =
  | "Full theme names"
  | "Short theme names"
  | "Two-letter theme names"
  | "No theme names";

export interface CoTrackerConfig {
  "theme-name-style": ThemeNameStyle;
  "show-run-stats": boolean;
  "show-session-stats": boolean;
  "show-header": boolean;
}

/** Generic config read: the caller narrows via the type arg. Backed
 *  by the Rust-side `get_tracker_config` command, which returns the
 *  slot's config as a serde_json::Value. */
export async function getTrackerConfig<T>(slug: string): Promise<T> {
  return invoke<T>("get_tracker_config", { slug });
}

/** Generic config write. Persists to modlunky2.json under
 *  `trackers.<slug>` (stripping fields matching defaults) + pushes to
 *  the tick task through the slot's watch channel. */
export async function setTrackerConfig(
  slug: string,
  config: unknown,
): Promise<void> {
  return invoke("set_tracker_config", { slug, config });
}

export async function startTrackerServer(
  port?: number,
): Promise<TrackerServerStatus> {
  return invoke<TrackerServerStatus>("start_tracker_server", {
    port: port ?? null,
  });
}

export async function stopTrackerServer(): Promise<TrackerServerStatus> {
  return invoke<TrackerServerStatus>("stop_tracker_server");
}

export async function getTrackerServerStatus(): Promise<TrackerServerStatus> {
  return invoke<TrackerServerStatus>("get_tracker_server_status");
}

/** Why the trackers can't read the game, when it's something the user can fix
 *  (on Linux, the ptrace restriction). Null when they're reading fine, and
 *  also when the game just isn't running, which the trackers already show on
 *  their own. Deliberately not part of the tracker payload, since that
 *  renders in OBS. */
export async function getTrackerAttachProblem(): Promise<string | null> {
  return invoke<string | null>("get_tracker_attach_problem");
}

/** Peek the current payload for `slug`. Every tracker's variant is
 *  in the TrackerPayload union so the caller narrows on `.type`. */
export async function getTrackerPayload(slug: string): Promise<TrackerPayload> {
  return invoke<TrackerPayload>("get_tracker_payload", { slug });
}

/** Opens the always-on-top native tracker window for the named
 *  tracker (`"category"`, `"pacifist"`, etc). Errors when the server
 *  isn't running because the URL wouldn't resolve. */
export async function openTrackerWindow(tracker: string): Promise<void> {
  return invoke("open_tracker_window", { tracker });
}

export interface WindowConfig {
  /** CSS color the OBS pages use as their background. Chroma-key
   *  this in OBS to overlay the tracker over the game feed. */
  colorKey: string;
  fontFamily: string;
  fontSize: number;
  fontColor: string;
  /** Text-outline width in px; 0 = no outline. Applies to every tracker. */
  strokeWidth: number;
  strokeColor: string;
}

export async function getWindowConfig(): Promise<WindowConfig> {
  return invoke<WindowConfig>("get_window_config");
}

/** Font family names installed on the user's system, for the font picker. */
export async function listSystemFonts(): Promise<string[]> {
  return invoke<string[]>("list_system_fonts");
}

export async function setWindowConfig(config: WindowConfig): Promise<void> {
  return invoke("set_window_config", { config });
}

/** Native-window setting: whether popped-out tracker windows stay
 *  above other windows. The setter persists to config and also flips
 *  the flag on every already-open tracker window, so the change is
 *  visible without reopening them. */
export async function getTrackerAlwaysOnTop(): Promise<boolean> {
  return invoke<boolean>("get_tracker_always_on_top");
}

export async function setTrackerAlwaysOnTop(value: boolean): Promise<void> {
  return invoke("set_tracker_always_on_top", { value });
}

export interface FileOutputSettings {
  /** Optional override for where tracker text files land. When null
   *  we fall back to `{install-dir}/Mods/Modlunky2/trackers`. */
  outputDir: string | null;
  /** When true, opening a tracker window also mirrors its display to
   *  `{outputDir}/{slug}.txt` for as long as the window stays open. */
  enabled: boolean;
}

export async function getFileSettings(): Promise<FileOutputSettings> {
  return invoke<FileOutputSettings>("get_file_settings");
}

export async function setFileSettings(
  settings: FileOutputSettings,
): Promise<void> {
  return invoke("set_file_settings", { settings });
}

/** Opens the tracker output folder in Explorer / Finder. Errors when
 *  no install-dir + no override is configured. */
export async function openTrackerFileDir(): Promise<void> {
  return invoke("open_tracker_file_dir");
}

/** Absolute path the given tracker's file writer writes to, e.g.
 *  `.../trackers/category.txt`. Used by the copy-to-clipboard button
 *  on each tracker card. */
export async function getTrackerFilePath(tracker: string): Promise<string> {
  return invoke<string>("get_tracker_file_path", { tracker });
}

/** One row per tracker slug that currently has any state on the
 *  refcount registry. Trackers with zero consumers and no tick task
 *  ever spawned won't appear until the first attach. */
export interface ConsumerSnapshot {
  slug: string;
  consumers: number;
  /** True while the producer tick task is alive. Normally implied by
   *  `consumers > 0`; the two disagreeing points to a leaked guard. */
  tickRunning: boolean;
}

export async function getTrackerDiagnostics(): Promise<ConsumerSnapshot[]> {
  return invoke<ConsumerSnapshot[]>("get_tracker_diagnostics");
}

// --- Saves -----------------------------------------------------------------

/** One journal category's completion, from a save's summary. */
export interface JournalProgress {
  category: string;
  discovered: number;
  total: number;
}

/** Deaths in one world, with the per-level breakdown behind the total. */
export interface WorldDeaths {
  /** 1..8. */
  world: number;
  /** Display name, e.g. "Jungle / Volcana". */
  name: string;
  /** Deaths per level, starting at level 1. */
  levels: number[];
  total: number;
}

/** How the last run ended. */
export interface LastRun {
  world: number;
  level: number;
  theme: number;
  themeName: string;
  score: number;
  timeFrames: number;
  timeMillis: number;
}

/** Everything the app knows about a save without holding the save itself.
 *  Produced by `ml2_save::SaveSummary`; also stored alongside every
 *  archived save so lists and charts never reparse the `.sav` files. */
export interface SaveSummary {
  /** Save-format version from the file header (25, 26 and 30 seen so far). */
  version: number;
  /** Whether the stored checksum matched when this was taken. */
  checksumValid: boolean;
  /** Sum of the death histogram. Should equal `deaths`. */
  deathcountTotal: number;

  plays: number;
  deaths: number;
  winsNormal: number;
  winsHard: number;
  winsSpecial: number;
  scoreTotal: number;
  scoreTop: number;
  timeTotalFrames: number;
  timeTotalMillis: number;
  /** 0 when there is no recorded best time. */
  timeBestFrames: number;
  timeBestMillis: number;

  deepestArea: number;
  deepestLevel: number;
  charactersUnlocked: number;
  shortcuts: number;
  shortcutsLabel: string;
  completedNormal: boolean;
  completedIronman: boolean;
  completedHard: boolean;
  seededUnlocked: boolean;
  /** Rescue counts for Monty, Percy and Poochi. */
  petsRescued: [number, number, number];
  /** Star count, or null when this save version's constellation block
   *  could not be located. `0` means there is no constellation yet. */
  constellationStars: number | null;
  /** The constellation itself, absent when there isn't one. Stored in
   *  snapshot sidecars only once the save is pruned, so an old chart
   *  outlives the save it came from. */
  constellation?: Constellation;

  journal: JournalProgress[];
  journalDiscovered: number;
  journalTotal: number;
  worldDeaths: WorldDeaths[];
  characterDeaths: number[];
  lastRun: LastRun;
}

/** The live `savegame.sav` in the install directory. */
export interface SaveStatus {
  path: string | null;
  exists: boolean;
  modifiedAtMs: number | null;
  fileSize: number | null;
  /** Null when the save is missing or could not be read. */
  summary: SaveSummary | null;
  /** Why it could not be read. A corrupt save is the case the Saves tab
   *  exists for, so the reason is shown rather than swallowed. */
  error: string | null;
}

/** Which of the two on-disk libraries an archived save is filed under.
 *  `managed` is what the user made and is never pruned; `snapshots` is
 *  automatic history, which a retention policy may thin by generation -
 *  keeping so many hourly, daily, weekly, monthly and yearly - rather
 *  than simply oldest-first. Pruning drops the save file and keeps the
 *  record, so the stats and the constellation survive. */
export type SaveLibrary = "managed" | "snapshots";

/** Why a save was archived. */
export type SaveKind =
  | "manual"
  | "automatic"
  | "preRestore"
  | "preEdit"
  | "imported";

/** How many snapshots each rotation tier keeps.
 *
 *  The same generational scheme as `rotate-backups`: each tier keeps the
 *  newest snapshot from each of its most recent N buckets, and a snapshot
 *  survives if any tier wants it. Zero switches a tier off. */
export interface RetentionPolicy {
  hourly: number;
  daily: number;
  weekly: number;
  monthly: number;
  yearly: number;
}

/** Which automatic snapshots keep a restorable `.sav`.
 *
 *  Pruning never deletes a record: it drops the `.sav` and keeps the
 *  sidecar, with the summary and any constellation baked in. A pruned
 *  snapshot stops being restorable but stays a point on the stats charts. */
export interface RetentionSettings {
  /** Default. Nothing is ever pruned and `policy` is ignored. */
  keepAll: boolean;
  policy: RetentionPolicy;
}

/** What a policy would do to the snapshots already archived. */
export interface RetentionPreview {
  /** Snapshots that currently have a save. */
  restorable: number;
  /** How many would still have one afterwards. */
  kept: number;
  /** How many would lose their save on the next pass. */
  pruned: number;
  /** Records already reduced to history. Unaffected either way. */
  historyOnly: number;
}

/** An archived save, from either library. */
export interface StoredSave {
  id: string;
  /** Capture time, epoch milliseconds. */
  takenAtMs: number;
  description: string;
  kind: SaveKind;
  sourcePath: string;
  fileSize: number;
  sha256: string;
  /** Stats as of when it was archived. */
  summary: SaveSummary;
  library: SaveLibrary;
  /** Empty once the `.sav` has been pruned away. */
  path: string;
  /** False for a history-only record: its summary is kept for the stats
   *  charts, but there is no save left to restore. */
  restorable: boolean;
  /** Whether pruning has removed this record's `.sav`. */
  savePruned: boolean;
}

/** One stat that differs between two saves. */
export interface StatDelta {
  label: string;
  from: number;
  to: number;
}

/** What restoring an archived save would do to the live one. */
export interface RestorePreview {
  stored: StoredSave;
  comparison: {
    /** Stats that would go backwards. */
    regressions: StatDelta[];
    /** Stats that would go forwards. */
    advances: StatDelta[];
  };
  losesProgress: boolean;
  identical: boolean;
  /** False when there is no readable save to compare against, which makes
   *  the restore unconditionally safe. */
  hasCurrentSave: boolean;
}

/** Automatic snapshotter settings. Off by default, and keeps everything
 *  when on. */
export interface SnapshotSettings {
  enabled: boolean;
  intervalHours: number;
  retention: RetentionSettings;
}

export async function getSaveStatus(): Promise<SaveStatus> {
  return invoke<SaveStatus>("get_save_status");
}

export async function listManagedSaves(): Promise<StoredSave[]> {
  return invoke<StoredSave[]>("list_managed_saves");
}

export async function listSaveSnapshots(): Promise<StoredSave[]> {
  return invoke<StoredSave[]>("list_save_snapshots");
}

/** Archives the live save into the managed library. */
export async function createManagedSave(
  description: string,
): Promise<StoredSave> {
  return invoke<StoredSave>("create_managed_save", { description });
}

export async function renameStoredSave(
  id: string,
  description: string,
): Promise<StoredSave> {
  return invoke<StoredSave>("rename_stored_save", { id, description });
}

export async function deleteStoredSave(id: string): Promise<void> {
  return invoke("delete_stored_save", { id });
}

/** Reports what restoring would change, without changing anything. */
export async function previewSaveRestore(
  id: string,
): Promise<RestorePreview> {
  return invoke<RestorePreview>("preview_save_restore", { id });
}

/** Restores an archived save over the live one. Returns the pre-restore
 *  backup when one was taken, so the restore itself can be undone. */
export async function restoreStoredSave(
  id: string,
  backupFirst: boolean,
): Promise<StoredSave | null> {
  return invoke<StoredSave | null>("restore_stored_save", { id, backupFirst });
}

export async function openSavesFolder(library: SaveLibrary): Promise<void> {
  return invoke("open_saves_folder", { library });
}

export async function getSnapshotSettings(): Promise<SnapshotSettings> {
  return invoke<SnapshotSettings>("get_snapshot_settings");
}

export async function setSnapshotSettings(
  settings: SnapshotSettings,
): Promise<SnapshotSettings> {
  return invoke<SnapshotSettings>("set_snapshot_settings", { settings });
}

/** One journal entry, with whatever counters the game keeps for it. */
export interface EntryStat {
  /** Position in its category, from zero. The journal shows these from one. */
  index: number;
  name: string;
  discovered: boolean;
  /** Null for categories the game keeps no kill counters for (places,
   *  items, traps), as opposed to a zero that would look like data. */
  killed: number | null;
  killedBy: number | null;
}

/** One journal category and everything in it. */
export interface CategoryStats {
  /** Identifier: "places" | "bestiary" | "people" | "items" | "traps". */
  category: string;
  label: string;
  discovered: number;
  total: number;
  entries: EntryStat[];
}

export interface CharacterStat {
  index: number;
  name: string;
  unlocked: boolean;
  deaths: number;
}

export interface ThemeStat {
  /** The game's own 1-based theme id. */
  id: number;
  name: string;
  completed: boolean;
}

/** One sticker from the last run: the character played, or something
 *  they were carrying at the end. */
export interface Sticker {
  entityType: number;
  name: string;
  isCharacter: boolean;
}

/** The full per-entry view of a save. Much larger than `SaveSummary`, and
 *  built on demand rather than stored, which is what keeps the snapshot
 *  sidecars small enough to keep forever. */
export interface SaveStats {
  summary: SaveSummary;
  journal: CategoryStats[];
  characters: CharacterStat[];
  /** Every theme and whether it has been completed - recorded separately
   *  from the three ending flags. Not shown in the stats view: it
   *  duplicates the journal's places for the themes it is right about,
   *  and is silently wrong for the three it is not. Kept for the editor,
   *  which has to be able to set the flags whatever they mean. */
  themes: ThemeStat[];
  /** The characters in the four player slots, as last chosen. */
  players: string[];
  /** Camp tutorial progress, 0..=4. */
  tutorialState: number;
  timeTutorialMillis: number;
  /** Date of the last daily challenge played, `YYYYMMDD`. */
  lastDaily: string | null;
  /** The last run's stickers, named. */
  stickers: Sticker[];
}

/** One point on the stats history.
 *
 *  Deliberately not a whole `SaveSummary`: the charts plot a handful of
 *  scalars, and a summary is ~4 KB apiece, which at 500 snapshots was a
 *  2 MB payload to draw six lines from. */
export interface HistoryPoint {
  id: string;
  takenAtMs: number;
  description: string;
  library: SaveLibrary;
  /** False for a pruned snapshot. It still counts as a data point. */
  restorable: boolean;

  plays: number;
  deaths: number;
  /** Normal, hard and Cosmic Ocean wins added together. */
  wins: number;
  journalDiscovered: number;
  scoreTotal: number;
  timeTotalMillis: number;
  charactersUnlocked: number;
  deepestArea: number;
  deepestLevel: number;
}

/** Full per-entry stats for the live save. */
export async function getSaveStats(): Promise<SaveStats> {
  return invoke<SaveStats>("get_save_stats");
}

/** Full per-entry stats for one archived save. Fails for a pruned
 *  snapshot, which has only its summary left. */
export async function getStoredSaveStats(id: string): Promise<SaveStats> {
  return invoke<SaveStats>("get_stored_save_stats", { id });
}

/** Everything the Stats panel needs from the archive, in one pass.
 *
 *  Both halves come from walking every archived save, and walking one
 *  means parsing it, so they share a single listing rather than each
 *  paying for their own. */
export interface StatsOverview {
  /** Oldest first, which is the order a time axis wants. */
  history: HistoryPoint[];
  gallery: GalleryEntry[];
}

export async function getStatsOverview(): Promise<StatsOverview> {
  return invoke<StatsOverview>("get_stats_overview");
}

/** One star in a Cosmic Ocean constellation.
 *
 *  Positions are in the game's own space: x grows to the *left*, y grows
 *  downward, both spanning roughly -1.35 to 1.35. Color channels are
 *  0..1. Confirmed against a real save rendered beside a screenshot of
 *  the same chart in game. */
export interface ConstellationStar {
  kind: number;
  x: number;
  y: number;
  size: number;
  red: number;
  green: number;
  blue: number;
  alpha: number;
  /** The game's own charts use a green halo, around (0.12, 0.42, 0). */
  haloRed: number;
  haloGreen: number;
  haloBlue: number;
  haloAlpha: number;
  /** Orange ring, for Canis. */
  canisRing: boolean;
  /** Red ring, for Fidelis. */
  fidelisRing: boolean;
  unknown: number;
}

/** A line joining two stars, by index. */
export interface ConstellationLine {
  from: number;
  to: number;
}

export interface Constellation {
  stars: ConstellationStar[];
  lines: ConstellationLine[];
  scale: number;
  /** 0 draws the joins near-white; the game raises this toward 1 as NPC
   *  kills climb, taking them pink and then deep red. */
  lineRedIntensity: number;
}

/** One constellation in the gallery.
 *
 *  A save holds exactly one, and generating a new one overwrites it, so
 *  old charts only survive in whatever was archived while they were
 *  current. Identical charts across many snapshots are collapsed. */
export interface GalleryEntry {
  /** Shape signature, used to group duplicates. Also a stable key. */
  signature: string;
  constellation: Constellation;
  firstSeenMs: number;
  lastSeenMs: number;
  /** How many archived saves hold this same chart. */
  occurrences: number;
  sourceId: string | null;
  description: string;
  /** Whether the live save has this one right now. */
  isCurrent: boolean;
}



/** What a retention policy would do to the snapshots already archived.
 *  Writes nothing; this only reports, so the settings UI can show the
 *  effect before it is applied. */
export async function previewRetention(
  settings: RetentionSettings,
): Promise<RetentionPreview> {
  return invoke<RetentionPreview>("preview_retention", { settings });
}

/** Applies the saved retention policy to the snapshot library now, rather
 *  than waiting for the snapshotter's next capture. Returns how many
 *  snapshots lost their save file. */
export async function applyRetentionNow(): Promise<number> {
  return invoke<number>("apply_retention_now");
}


// --- The save editor -------------------------------------------------------

/** Which save the editor is pointed at. */
export type SaveRef = { kind: "live" } | { kind: "stored"; id: string };

/** The lifetime counters behind the game's profile screen. */
export interface ProfileEdit {
  plays: number;
  deaths: number;
  winsNormal: number;
  winsHard: number;
  winsSpecial: number;
  /** Lifetime money. A string because it is 64-bit in the file and a JSON
   *  number stops being exact past 2^53 - which is well inside what
   *  someone editing this field will try to type. */
  scoreTotal: string;
  scoreTop: number;
  /** Total frames played, a string for the same reason. */
  timeTotal: string;
  timeBest: number;
  timeTutorial: number;
  deepestArea: number;
  deepestLevel: number;
}

export interface UnlocksEdit {
  completedNormal: boolean;
  completedIronman: boolean;
  completedHard: boolean;
  profileSeen: boolean;
  seededUnlocked: boolean;
  /** Terra's quest, 0..=10. */
  shortcuts: number;
  /** Camp tutorial progress, 0..=4. */
  tutorialState: number;
}

export interface LastRunEdit {
  world: number;
  level: number;
  theme: number;
  score: number;
  /** Length of the run in frames. */
  time: number;
  /** Entity types of the run's stickers, empty slots dropped. */
  stickers: number[];
}

export interface CampEdit {
  /** Character index per player slot. */
  players: [number, number, number, number];
  /** Monty, Percy, Poochi. */
  petsRescued: [number, number, number];
  /** `YYYYMMDD`, or null for a save that has never played a daily. */
  lastDaily: string | null;
}

export interface JournalEntryEdit {
  name: string;
  discovered: boolean;
  /** Null for places, items and traps, which keep no kill counts. */
  killed: number | null;
  killedBy: number | null;
}

export interface JournalSectionEdit {
  key: string;
  label: string;
  hasKills: boolean;
  entries: JournalEntryEdit[];
}

export interface CharacterEdit {
  name: string;
  unlocked: boolean;
  deaths: number;
}

export interface WorldDeathsEdit {
  /** 1-based world number, as a player would say it. */
  world: number;
  name: string;
  /** Level number that `levels[0]` refers to.
   *
   *  Not always 1. The Cosmic Ocean is entered from 7-4, so its levels
   *  start at 5, and its last playable level is 98 - 99 is the closing
   *  cutscene, which you arrive at rather than survive. */
  firstLevel: number;
  /** Deaths at `firstLevel`, `firstLevel + 1`, and so on. */
  levels: number[];
}

/** The death counts for one world, on the way back.
 *
 *  Carries `firstLevel` rather than letting the backend re-derive it:
 *  the derivation depends on what the save holds, so zeroing a count
 *  could shift the range and land every edit a row off. */
export interface WorldDeathValues {
  world: number;
  firstLevel: number;
  levels: number[];
}

export interface ThemeEdit {
  id: number;
  name: string;
  completed: boolean;
}

/** Everything the editor can change, plus the labels it draws with. */
export interface EditableSave {
  path: string;
  version: number;
  /** False for a save whose checksum did not verify. Still editable -
   *  that is the save someone most needs an editor for. */
  checksumValid: boolean;
  profile: ProfileEdit;
  unlocks: UnlocksEdit;
  lastRun: LastRunEdit;
  camp: CampEdit;
  journal: JournalSectionEdit[];
  characters: CharacterEdit[];
  deaths: WorldDeathsEdit[];
  themes: ThemeEdit[];
  constellation: Constellation | null;
  /** False when this build cannot locate the constellation in this save's
   *  version, in which case it must not be written. */
  constellationEditable: boolean;
  /** The game's own labels for Terra's eleven states. */
  shortcutStates: string[];
  /** Names for the entity ids this save's stickers hold, keyed by id.
   *
   *  Stickers are raw entity types and the table that names them is far
   *  too large to send, so only the ids actually present are named. That
   *  covers reading and removing; an id typed by hand stays a number
   *  until it is saved. Playable characters are resolved from the
   *  character roster instead, via `firstCharacterEntity`. */
  stickerNames: Record<string, string>;
  /** Entity id of the first playable character, so a character sticker
   *  can be named from the roster already in this payload. */
  firstCharacterEntity: number;
}

export interface JournalSectionValues {
  key: string;
  discovered: boolean[];
  killed: number[];
  killedBy: number[];
}

export interface CharacterValues {
  unlocked: boolean;
  deaths: number;
}

/** The values to write back: the same shape as `EditableSave` without the
 *  labels, which are ours rather than the save's. */
export interface SaveEdits {
  profile: ProfileEdit;
  unlocks: UnlocksEdit;
  lastRun: LastRunEdit;
  camp: CampEdit;
  journal: JournalSectionValues[];
  characters: CharacterValues[];
  /** Deaths per world, each carrying the level its first entry means. */
  deaths: WorldDeathValues[];
  /** Completion flag per theme, 1-based ids in order. */
  themes: boolean[];
  /** Null leaves whatever chart the save has alone. */
  constellation: Constellation | null;
}

export interface EditResult {
  /** How many bytes of the file actually changed. Zero means the edits
   *  matched what was already there. */
  changedBytes: number;
  /** The archived copy of what was overwritten, when one was made. */
  backup: StoredSave | null;
  /** The save as it now stands, to rebase the editor on. */
  save: EditableSave;
}

/** Reads a save into the form the editor works on. */
export async function getEditableSave(source: SaveRef): Promise<EditableSave> {
  return invoke<EditableSave>("get_editable_save", { source });
}

/** Writes edits back to a save.
 *
 *  `backup` archives the file first, into the managed library where
 *  pruning cannot reach it. It is the only way back from a bad edit, so
 *  leave it on unless the user has said otherwise. */
export async function applySaveEdits(
  source: SaveRef,
  edits: SaveEdits,
  backup: boolean,
  description: string,
): Promise<EditResult> {
  return invoke<EditResult>("apply_save_edits", {
    source,
    edits,
    backup,
    description,
  });
}

/** An existing record already holding the exact bytes being imported. */
export interface DuplicateRecord {
  id: string;
  description: string;
  takenAtMs: number;
  kind: SaveKind;
}

/** A save file the user has pointed at, before anything is copied. */
export interface ImportPreview {
  path: string;
  fileName: string;
  fileSize: number;
  /** When the file was last written, epoch milliseconds. */
  modifiedAtMs: number | null;
  summary: SaveSummary | null;
  /** Why this file cannot be imported, if it cannot. A batch keeps going
   *  past one bad file rather than failing all of them. */
  error: string | null;
  /** False for a file whose checksum does not verify. Still importable -
   *  a copy of a damaged save is exactly what an archive is for. */
  checksumValid: boolean;
  /** The record already holding these exact bytes, if any. */
  duplicate: DuplicateRecord | null;
}

/** One file to copy in, with the name to file it under. */
export interface ImportItem {
  path: string;
  description: string;
}

export interface ImportFailure {
  path: string;
  error: string;
}

export interface ImportOutcome {
  imported: StoredSave[];
  /** One bad file does not stop the rest, so both halves come back. */
  failed: ImportFailure[];
}

/** Reads the save files the user picked. Copies nothing. */
export async function previewSaveImports(
  paths: string[],
): Promise<ImportPreview[]> {
  return invoke<ImportPreview[]>("preview_save_imports", { paths });
}

/** Copies save files into your saves. The originals are left where they
 *  are, and each is filed under the date it was last written. */
export async function importSaves(
  items: ImportItem[],
): Promise<ImportOutcome> {
  return invoke<ImportOutcome>("import_saves", { items });
}
