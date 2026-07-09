// Both editor windows need extracted game assets to render sprites; without
// them every tile shows a placeholder and painting is confusingly useless.
// This gate wraps the editor body and short-circuits to a friendly "extract
// first" screen when the check fails.
//
// The gate opens as a separate Tauri window (level editors are their own
// windows), so it can't switch tabs directly. Instead it explains what to
// do and provides a button that opens the main window's Mods folder for
// convenience.

import { useEffect, useState } from "react";
import { AlertTriangle, PackageOpen, RefreshCw } from "lucide-react";
import { extractedAssetsAvailable, openDirectory } from "../../lib/commands";
import "./ExtractRequiredGate.css";

interface Props {
  children: React.ReactNode;
}

type CheckState = "checking" | "ready" | "missing";

export function ExtractRequiredGate({ children }: Props) {
  const [state, setState] = useState<CheckState>("checking");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    extractedAssetsAvailable()
      .then((ok) => {
        if (cancelled) return;
        setState(ok ? "ready" : "missing");
      })
      .catch(() => {
        if (!cancelled) setState("missing");
      });
    return () => {
      cancelled = true;
    };
  }, [refreshTick]);

  if (state === "checking") {
    // Blank body during the check. This is fast (single fs::read_dir on the
    // Rust side) so a spinner would be more distraction than help.
    return null;
  }

  if (state === "missing") {
    return (
      <div className="extract-required">
        <div className="extract-required-card">
          <div className="extract-required-icon">
            <AlertTriangle size={32} aria-hidden="true" />
          </div>
          <h1 className="extract-required-title">Extract game assets first</h1>
          <p className="extract-required-body">
            The level editor renders each tile using sprites from
            <code>Mods/Extracted/Data/Textures/</code>, and that folder is
            empty (or the install directory isn't set). Run{" "}
            <strong>Extract Assets</strong> from the main window before
            editing a level. This is a one-time step per game version.
          </p>
          <div className="extract-required-actions">
            <button
              type="button"
              className="btn btn-primary extract-required-btn"
              onClick={() => {
                void openDirectory("packs");
              }}
              title="Open the Mods folder in Explorer"
            >
              <PackageOpen size={14} aria-hidden="true" />
              <span>Open Mods folder</span>
            </button>
            <button
              type="button"
              className="btn btn-ghost extract-required-btn"
              onClick={() => setRefreshTick((t) => t + 1)}
              title="Recheck after running Extract in the main window"
            >
              <RefreshCw size={14} aria-hidden="true" />
              <span>Check again</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
