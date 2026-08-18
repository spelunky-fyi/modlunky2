export interface SharedConfig {
  installDir: string | null;
  spelunkyFyiRoot: string | null;
  spelunkyFyiApiToken: string | null;
  playlunkyVersion: string | null;
  playlunkyConsole: boolean;
  /** Whether the launch dock has Overlunky selected. Named for its original
   *  meaning (pass --overlunky to Playlunky), which is still what it does
   *  when Playlunky is also selected. */
  playlunkyOverlunky: boolean;
  /** Whether the launch dock has Playlunky selected. Defaults to true. */
  launchWithPlaylunky: boolean;
  commandPrefix: string | null;
  playlunkyShortcut: boolean;
  /** Tab id last active in the app shell (mods / overlunky / extract /
   *  levels / trackers). Null on first launch or after config reset. */
  lastTab: string | null;
  /** How the Mods page orders its inactive list: "name" | "installed" |
   *  "used". Null until the user picks one. Global rather than per-install
   *  because it names no particular mod; the per-install half (favorites,
   *  usage history) lives beside the mods themselves. */
  modSort: string | null;
  /** Whether that sort runs largest-first. Null means "never set", which
   *  matters because the sensible default differs per field. */
  modSortDesc: boolean | null;
  /** Whether the Mods page is showing only favorites. */
  modFavoritesOnly: boolean;
  /** How tightly the Mods page packs rows: "comfortable" | "compact" |
   *  "dense". Null until the user picks one. */
  modDensity: string | null;
  /** Which source the Install dialog opens on: "fyi" | "file". Null until the
   *  user has installed something. */
  modInstallSource: string | null;
  /** Port the tracker HTTP + WS server binds on. Defaults to 9526
   *  (matches Python's api-port) when the field is missing. */
  trackerServerPort: number;
  /** Whether the tracker server auto-starts on app boot. */
  trackerServerAutoStart: boolean;
  /** UI color theme for the whole app: "dark" (default) or "light". */
  theme: string;
  /** Minimum severity that pops a floating toast: "info" | "success" |
   *  "warning" | "error". Quieter ones still land in the toast log. Defaults
   *  to "warning". */
  toastLevel: string;
}

export interface ConfigPatch {
  installDir?: string;
  spelunkyFyiRoot?: string;
  spelunkyFyiApiToken?: string;
  playlunkyVersion?: string;
  playlunkyConsole?: boolean;
  playlunkyOverlunky?: boolean;
  launchWithPlaylunky?: boolean;
  commandPrefix?: string;
  playlunkyShortcut?: boolean;
  /** Tab id to persist; pass "" to clear. */
  lastTab?: string;
  /** "name" | "installed" | "used". */
  modSort?: string;
  modSortDesc?: boolean;
  modFavoritesOnly?: boolean;
  /** "comfortable" | "compact" | "dense". */
  modDensity?: string;
  /** "fyi" | "file". */
  modInstallSource?: string;
  trackerServerPort?: number;
  trackerServerAutoStart?: boolean;
  /** "dark" | "light". Pass to persist the app's color theme. */
  theme?: string;
  /** "info" | "success" | "warning" | "error". Minimum toast severity. */
  toastLevel?: string;
}
