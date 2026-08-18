/** Why the Spelunky 2 install directory isn't usable. The two failures need
 *  different advice: one is "you haven't set this yet", the other is "what
 *  you set has gone away", which usually means a moved game or an unplugged
 *  drive. */
export type InstallDirState = "unset" | "missing" | "ok";

/** Everything the UI gates on, in one round trip. */
export interface SetupStatus {
  installDir: InstallDirState;
  /** The configured path even when it's missing, so the UI can name what it
   *  went looking for instead of just saying "not found". */
  installDirPath: string | null;
  /** Whether Mods/Extracted has textures in it. The level editors need them. */
  assetsExtracted: boolean;
  /** Whether a spelunky.fyi token is set. Never required: local mods work
   *  without one, it only gates installing from the site and update checks. */
  hasApiToken: boolean;
  /** Whether the mod manager is running. Distinct from `installDir`: it is
   *  only built at startup or by an explicit rebuild, so a launch with no
   *  folder leaves it down even once a folder is chosen. */
  modsReady: boolean;
}

/** The three things a user has to set up, in the order they matter. */
export type SetupRequirement = "installDir" | "assets" | "apiToken";

/** Whether `status` satisfies `req`. */
export function isSatisfied(
  status: SetupStatus,
  req: SetupRequirement,
): boolean {
  switch (req) {
    case "installDir":
      return status.installDir === "ok";
    case "assets":
      return status.assetsExtracted;
    case "apiToken":
      return status.hasApiToken;
  }
}

/** The first unmet requirement, or null when everything `reqs` needs is set.
 *
 *  Ordered rather than "all unmet at once" on purpose: assets can't be
 *  extracted without a game folder, so showing both at once would present a
 *  step the user can't act on yet. */
export function firstUnmet(
  status: SetupStatus,
  reqs: SetupRequirement[],
): SetupRequirement | null {
  const order: SetupRequirement[] = ["installDir", "assets", "apiToken"];
  for (const req of order) {
    if (reqs.includes(req) && !isSatisfied(status, req)) return req;
  }
  return null;
}
