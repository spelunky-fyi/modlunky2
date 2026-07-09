export interface SharedConfig {
  installDir: string | null;
  spelunkyFyiRoot: string | null;
  spelunkyFyiApiToken: string | null;
  playlunkyVersion: string | null;
  playlunkyConsole: boolean;
  playlunkyOverlunky: boolean;
  commandPrefix: string | null;
  playlunkyShortcut: boolean;
  /** Tab id last active in the app shell (mods / overlunky / extract /
   *  levels / trackers). Null on first launch or after config reset. */
  lastTab: string | null;
  /** Port the tracker HTTP + WS server binds on. Defaults to 9526
   *  (matches Python's api-port) when the field is missing. */
  trackerServerPort: number;
  /** Whether the tracker server auto-starts on app boot. */
  trackerServerAutoStart: boolean;
}

export interface ConfigPatch {
  installDir?: string;
  spelunkyFyiRoot?: string;
  spelunkyFyiApiToken?: string;
  playlunkyVersion?: string;
  playlunkyConsole?: boolean;
  playlunkyOverlunky?: boolean;
  commandPrefix?: string;
  playlunkyShortcut?: boolean;
  /** Tab id to persist; pass "" to clear. */
  lastTab?: string;
  trackerServerPort?: number;
  trackerServerAutoStart?: boolean;
}
