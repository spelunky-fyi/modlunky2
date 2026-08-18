// Setup state, plus the two ways to act on it.
//
// The status itself is easy; the routing is the point. A gate that says "set
// your install directory in Settings" is still a dead end if the user has to
// go find Settings. Opening the modal and switching tabs are both App-level
// powers, so App publishes them here and any gate, however deep, can offer a
// button that actually goes somewhere.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getSetupStatus, rebuildMods } from "../../lib/commands";
import type { SetupStatus } from "../../types/setup";

/** Which Settings field the user was sent to fix. Arriving at a wall of
 *  settings with no idea which one you came for is its own dead end, so the
 *  reason for the trip travels with it. */
export type SettingsFocus = "installDir" | "apiToken";

interface SetupContextValue {
  /** Null until the first fetch lands, so gates can hold off rather than
   *  flashing a setup screen at someone who is already set up. */
  status: SetupStatus | null;
  /** Re-read after something that might have fixed a requirement. */
  refresh: () => Promise<void>;
  openSettings: (focus?: SettingsFocus) => void;
  goToExtract: () => void;
}

const SetupCtx = createContext<SetupContextValue | null>(null);

export function useSetup(): SetupContextValue {
  const ctx = useContext(SetupCtx);
  if (!ctx) throw new Error("SetupProvider missing");
  return ctx;
}

export function SetupProvider({
  children,
  openSettings,
  goToExtract,
}: {
  children: ReactNode;
  openSettings: (focus?: SettingsFocus) => void;
  goToExtract: () => void;
}) {
  const [status, setStatus] = useState<SetupStatus | null>(null);

  /**
   * Re-reads setup state, starting the mod subsystem first if it needs it.
   *
   * The subsystem is only built at startup or by an explicit rebuild, so a
   * launch with no install folder leaves it down permanently: choosing a
   * folder afterwards updates the config and nothing else, and every mod
   * command keeps failing until something rebuilds. Doing it here rather than
   * at each call site means it holds for every route to setting a folder, the
   * ones that exist today and the ones added later.
   *
   * It happens *before* the new status is published, so the Mods tab's gate
   * can't open onto a manager that isn't running yet.
   */
  const refresh = useCallback(async () => {
    try {
      const next = await getSetupStatus();
      if (next.installDir === "ok" && !next.modsReady) {
        try {
          await rebuildMods();
        } catch {
          // Leave it to the page's own error state, which can retry. Refusing
          // to publish the status would strand the user behind the gate.
        }
      }
      setStatus(next);
    } catch {
      // A failed status read shouldn't gate anything: better to let the user
      // through to a real error than to trap them behind a setup screen we
      // can't justify.
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <SetupCtx.Provider value={{ status, refresh, openSettings, goToExtract }}>
      {children}
    </SetupCtx.Provider>
  );
}
