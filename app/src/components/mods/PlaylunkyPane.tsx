import { useCallback, useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { ask } from "@tauri-apps/plugin-dialog";
import { BookOpen, Play, Settings } from "lucide-react";
import { useToast } from "../shared/Toast";
import {
  downloadPlaylunkyVersion,
  getConfig,
  getPlaylunkyOptions,
  launchPlaylunky,
  listInstalledPlaylunky,
  setConfig,
  setPlaylunkyOptions,
} from "../../lib/commands";

const PLAYLUNKY_WIKI_URL = "https://github.com/spelunky-fyi/Playlunky/wiki";
import { PlaylunkyOptionsModal } from "./PlaylunkyOptionsModal";
import { PlaylunkyVersionsModal } from "./PlaylunkyVersionsModal";
import "./PlaylunkyPane.css";

interface PlaylunkyPaneProps {
  activeCount: number;
}

export function PlaylunkyPane({ activeCount }: PlaylunkyPaneProps) {
  const toast = useToast();
  const [installed, setInstalled] = useState<string[]>([]);
  const [version, setVersion] = useState<string>("");
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [speedrun, setSpeedrun] = useState(false);
  const [speedrunBusy, setSpeedrunBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [tags, cfg, opts] = await Promise.all([
        listInstalledPlaylunky(),
        getConfig(),
        getPlaylunkyOptions(),
      ]);
      setInstalled(tags);
      setSpeedrun(opts.general.speedrunMode);
      const persisted = cfg.playlunkyVersion ?? "";
      // Fall back to the first installed version if the persisted one is
      // missing (never selected after a first install) or gone (uninstalled
      // outside the app, moved, etc).
      if (persisted && tags.includes(persisted)) {
        setVersion(persisted);
      } else if (tags.length > 0) {
        // Persist the fallback: launch reads the config, not this UI state, so
        // showing "nightly" here without saving it left the backend with no
        // selected version and launches failed with "no Playlunky version
        // selected" even though the dropdown looked correct.
        setVersion(tags[0]);
        try {
          await setConfig({ playlunkyVersion: tags[0] });
        } catch {
          // Non-fatal; the dropdown still shows it and an explicit pick will
          // persist it.
        }
      } else {
        setVersion("");
      }
    } catch (err) {
      toast.error(`Couldn't load Playlunky info: ${extractMessage(err)}`);
    }
  }, [toast]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleVersionChange = async (tag: string) => {
    setVersion(tag);
    try {
      await setConfig({ playlunkyVersion: tag });
    } catch (err) {
      toast.error(`Couldn't save version: ${extractMessage(err)}`);
    }
  };

  const handlePlay = async () => {
    // Nightly / stable check for updates before spawning so this can take
    // a beat. Nudge the user so they know something's happening.
    toast.info("Preparing Playlunky…");
    try {
      await launchPlaylunky();
      toast.success(`Launching Playlunky ${version}.`);
    } catch (err) {
      const message = extractMessage(err);
      const missingTag = parseNotInstalledSentinel(message);
      if (missingTag) {
        await recoverMissingPlaylunky(missingTag);
        return;
      }
      toast.error(`Launch failed: ${message}`);
    }
  };

  const recoverMissingPlaylunky = async (tag: string) => {
    // Common cause: antivirus quarantines playlunky_launcher.exe after we
    // drop it on disk. Offer a one-click reinstall + relaunch.
    const yes = await ask(
      `Playlunky ${tag} is missing on disk (antivirus may have quarantined it). ` +
        `Redownload and launch now?`,
      { title: "Reinstall Playlunky", kind: "warning" },
    );
    if (!yes) return;
    toast.info(`Reinstalling Playlunky ${tag}…`);
    try {
      await downloadPlaylunkyVersion(tag);
      await reload();
      await launchPlaylunky();
      toast.success(`Launching Playlunky ${tag}.`);
    } catch (err) {
      toast.error(`Reinstall failed: ${extractMessage(err)}`);
    }
  };

  const handleOptions = () => setOptionsOpen(true);

  const handleGuide = async () => {
    try {
      await openUrl(PLAYLUNKY_WIKI_URL);
    } catch (err) {
      toast.error(`Couldn't open browser: ${extractMessage(err)}`);
    }
  };

  const handleSpeedrunToggle = async (next: boolean) => {
    // Optimistic update so the checkbox responds instantly. Read-modify-
    // write against the ini keeps any concurrent user edits in the modal
    // safe. Roll back and toast on failure.
    setSpeedrun(next);
    setSpeedrunBusy(true);
    try {
      const opts = await getPlaylunkyOptions();
      opts.general.speedrunMode = next;
      await setPlaylunkyOptions(opts);
    } catch (err) {
      setSpeedrun(!next);
      toast.error(`Couldn't save Speedrun mode: ${extractMessage(err)}`);
    } finally {
      setSpeedrunBusy(false);
    }
  };

  const playDisabled = activeCount === 0 || !version;

  return (
    <footer className="playlunky-pane">
      <div className="playlunky-config">
        <label className="playlunky-version">
          <span>Playlunky</span>
          {installed.length === 0 ? (
            <button
              type="button"
              className="btn btn-ghost playlunky-empty-btn"
              onClick={() => setVersionsOpen(true)}
            >
              Install a version{"…"}
            </button>
          ) : (
            <select
              value={version}
              onChange={(e) => void handleVersionChange(e.target.value)}
            >
              {installed.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          )}
        </label>
        {installed.length > 0 && (
          <button
            type="button"
            className="btn btn-ghost playlunky-manage-btn"
            onClick={() => setVersionsOpen(true)}
            title="Manage installed Playlunky versions"
          >
            Manage
          </button>
        )}
        <button
          type="button"
          className="btn btn-ghost playlunky-options-btn"
          onClick={handleOptions}
          title="Playlunky options"
          aria-label="Playlunky options"
        >
          <Settings size={14} aria-hidden="true" /> Options
        </button>
        <button
          type="button"
          className="btn btn-ghost playlunky-options-btn"
          onClick={() => void handleGuide()}
          title="Open the Playlunky wiki"
          aria-label="Open the Playlunky wiki"
        >
          <BookOpen size={14} aria-hidden="true" /> Guide
        </button>
      </div>
      <div className="playlunky-play-group">
        <label className="playlunky-speedrun">
          <input
            type="checkbox"
            checked={speedrun}
            onChange={(e) => void handleSpeedrunToggle(e.target.checked)}
            disabled={speedrunBusy}
          />
          <span>Speedrun mode</span>
        </label>
        <button
          type="button"
          className="btn btn-play"
          onClick={() => void handlePlay()}
          disabled={playDisabled}
        >
          <Play size={16} fill="currentColor" aria-hidden="true" /> Play
        </button>
      </div>

      <PlaylunkyVersionsModal
        open={versionsOpen}
        onClose={() => setVersionsOpen(false)}
        activeVersion={version || null}
        onSetActive={(tag) => void handleVersionChange(tag)}
        onChanged={() => void reload()}
      />
      <PlaylunkyOptionsModal
        open={optionsOpen}
        onClose={() => {
          setOptionsOpen(false);
          // Refetch so the pane's Speedrun checkbox reflects whatever
          // the user changed inside the modal.
          void reload();
        }}
      />
    </footer>
  );
}

function extractMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err && typeof err === "object") {
    for (const v of Object.values(err)) {
      if (typeof v === "string") return v;
    }
    return JSON.stringify(err);
  }
  return String(err);
}

/// Backend sentinel: `PLAYLUNKY_NOT_INSTALLED:<tag>`. Returns the tag if the
/// error matches, null otherwise.
function parseNotInstalledSentinel(message: string): string | null {
  const prefix = "PLAYLUNKY_NOT_INSTALLED:";
  return message.startsWith(prefix) ? message.slice(prefix.length) : null;
}

