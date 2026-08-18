// Stands in for a tab that can't work yet, explaining what's missing and
// taking the user straight to where they fix it.
//
// Generalises the idea behind ExtractRequiredGate to all three prerequisites.
// The point is that nothing should be discovered by failure: a tab that needs
// a game folder says so up front instead of rendering normally and erroring
// on every action.

import type { ReactNode } from "react";
import { FolderSearch, PackageOpen } from "lucide-react";
import { guessInstallDir, setConfig } from "../../lib/commands";
import { useToast } from "./Toast";
import { useSetup } from "./SetupContext";
import { firstUnmet, type SetupRequirement } from "../../types/setup";
import "./SetupGate.css";

interface Props {
  /** What this area needs. Only the first unmet one is shown: assets can't be
   *  extracted before there's a game folder to extract from. */
  requires: SetupRequirement[];
  children: ReactNode;
}

export function SetupGate({ requires, children }: Props) {
  const { status } = useSetup();
  // Render nothing rather than a setup screen until the status is known, so a
  // configured user never sees a flash of "you need to set this up".
  if (!status) return null;
  const missing = firstUnmet(status, requires);
  if (!missing) return <>{children}</>;
  return <SetupPrompt requirement={missing} />;
}

function SetupPrompt({ requirement }: { requirement: SetupRequirement }) {
  const { status, refresh, openSettings, goToExtract } = useSetup();
  const toast = useToast();

  const findItForMe = async () => {
    try {
      const found = await guessInstallDir();
      if (!found) {
        toast.warning("Couldn't find Spelunky 2. Set the folder in Settings.");
        openSettings("installDir");
        return;
      }
      await setConfig({ installDir: found });
      await refresh();
      toast.success(`Found Spelunky 2 at ${found}.`);
    } catch (err) {
      toast.error(`Couldn't set the folder: ${extractMessage(err)}`);
      openSettings("installDir");
    }
  };

  if (requirement === "installDir") {
    const movedAway = status?.installDir === "missing";
    return (
      <Prompt
        icon={<FolderSearch size={30} aria-hidden="true" />}
        title={
          movedAway
            ? "Can't find your Spelunky 2 folder"
            : "Where is Spelunky 2 installed?"
        }
        body={
          movedAway ? (
            <>
              <p>
                Your settings have it configured at{" "}
                <code>{status?.installDirPath}</code> but we can't find it
                there.
              </p>
              <p className="setup-gate-note">
                Please check that the folder exists and contains{" "}
                <code>Spel2.exe</code>, or set the correct folder in Settings.
              </p>
            </>
          ) : (
            <>
              <p>
                We need to know where Spelunky 2 is installed. Modlunky cannot
                work without it. You'll need to configure the folder before you
                can continue.
              </p>
              <p className="setup-gate-note">
                It's the folder containing <code>Spel2.exe</code>, usually under{" "}
                <code>steamapps/common/Spelunky 2</code>.
              </p>
            </>
          )
        }
        actions={
          <>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void findItForMe()}
            >
              I'm feeling lucky
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => openSettings("installDir")}
            >
              Configure it myself
            </button>
          </>
        }
      />
    );
  }

  if (requirement === "assets") {
    return (
      <Prompt
        icon={<PackageOpen size={30} aria-hidden="true" />}
        title="Extract the game's assets first"
        body={
          <>
            <p>The level editor requires assets from the game.</p>
            <p className="setup-gate-note">
              Head over to the Extract Assets tab and hit Extract on the{" "}
              <code>Spel2.exe</code>. It's a one time requirement and just takes
              a few minutes.
            </p>
          </>
        }
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={goToExtract}
          >
            Go to Extract Assets
          </button>
        }
      />
    );
  }

  // Anything else (today: apiToken) is optional by definition, so it gets a
  // banner rather than a barricade. Failing open matters: a bug that added a
  // non-blocking requirement to a tab's `requires` should not lock someone out
  // of that tab.
  return null;
}

function Prompt({
  icon,
  title,
  body,
  actions,
}: {
  icon: ReactNode;
  title: string;
  body: ReactNode;
  actions: ReactNode;
}) {
  return (
    <div className="setup-gate">
      <div className="setup-gate-card">
        <div className="setup-gate-icon">{icon}</div>
        <h2 className="setup-gate-title">{title}</h2>
        <div className="setup-gate-body">{body}</div>
        <div className="setup-gate-actions">{actions}</div>
      </div>
    </div>
  );
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const value of Object.values(err)) {
      if (typeof value === "string") return value;
    }
    return JSON.stringify(err);
  }
  return String(err);
}
