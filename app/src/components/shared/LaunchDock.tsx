// The global launch dock: a fixed footer, present on every tab, that owns
// starting the game.
//
// It replaces three scattered entry points. Playlunky had a Play button in a
// footer on the Mods tab, Overlunky had a "Launch vanilla with Overlunky"
// card on its own tab, launching with both meant finding a toggle inside the
// Playlunky Options modal, and launching the game plain wasn't possible at
// all. The Overlunky tab even carried a footnote telling you which modal to go
// open, which is a good sign the shape was wrong.
//
// Two independent toggles cover all four combinations, and the button spells
// out the result rather than leaving it to be inferred from which chips look
// lit. The button sits on the right and never moves: Playlunky's contextual
// controls appear and disappear on the left, so the thing you're aiming at
// stays put whatever the state.

import { useCallback, useEffect, useState } from "react";
import { HelpCircle, Package, Play, Settings } from "lucide-react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { useToast } from "./Toast";
import {
  getConfig,
  getPlaylunkyOptions,
  launchGame,
  listInstalledPlaylunky,
  setConfig,
  setPlaylunkyOptions,
} from "../../lib/commands";
import { Switch } from "./Switch";
import { PlaylunkyOptionsModal } from "../mods/PlaylunkyOptionsModal";
import { PlaylunkyVersionsModal } from "../mods/PlaylunkyVersionsModal";
import "./LaunchDock.css";

/// Matches `playlunky::NIGHTLY_TAG`. Shown as the pending selection before
/// anything is installed, since that's what launching will fetch.
const NIGHTLY_TAG = "nightly";

/// What the version control shows before anything is installed: launching
/// fetches nightly, so say that rather than leaving the control blank.
const PENDING_VERSION = `${NIGHTLY_TAG}`;

const PLAYLUNKY_WIKI_URL = "https://github.com/spelunky-fyi/Playlunky/wiki";

export function LaunchDock() {
  const toast = useToast();
  const [withPlaylunky, setWithPlaylunky] = useState(true);
  const [withOverlunky, setWithOverlunky] = useState(false);
  const [installed, setInstalled] = useState<string[]>([]);
  const [version, setVersion] = useState<string>("");
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [launching, setLaunching] = useState(false);
  // Playlunky's own speedrun flag, surfaced here because it changes what a
  // launch does. It lives in playlunky.ini rather than modlunky's config, so
  // it loads and saves separately from everything else on this row.
  const [speedrun, setSpeedrun] = useState(false);
  const [speedrunBusy, setSpeedrunBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [cfg, tags, opts] = await Promise.all([
        getConfig(),
        listInstalledPlaylunky(),
        getPlaylunkyOptions(),
      ]);
      setWithPlaylunky(cfg.launchWithPlaylunky);
      setWithOverlunky(cfg.playlunkyOverlunky);
      setInstalled(tags);
      setSpeedrun(opts.general.speedrunMode);
      const persisted = cfg.playlunkyVersion ?? "";
      // Nothing installed yet is fine and not an error state: launching picks
      // up nightly and downloads it. Show that as the pending selection so the
      // dock says what's about to happen.
      setVersion(
        persisted && tags.includes(persisted) ? persisted : NIGHTLY_TAG,
      );
    } catch (err) {
      toast.error(`Couldn't load launch settings: ${extractMessage(err)}`);
    }
  }, [toast]);

  useEffect(() => {
    void reload();
  }, [reload]);

  // Persist eagerly rather than only on launch, so the choice survives a
  // restart even if the user never presses the button this session.
  const toggle = async (tool: "playlunky" | "overlunky", next: boolean) => {
    if (tool === "playlunky") setWithPlaylunky(next);
    else setWithOverlunky(next);
    try {
      await setConfig(
        tool === "playlunky"
          ? { launchWithPlaylunky: next }
          : { playlunkyOverlunky: next },
      );
    } catch (err) {
      // Roll back so the dock never claims a state the backend will not use.
      if (tool === "playlunky") setWithPlaylunky(!next);
      else setWithOverlunky(!next);
      toast.error(`Couldn't save that: ${extractMessage(err)}`);
    }
  };

  const handleVersionChange = async (tag: string) => {
    setVersion(tag);
    try {
      await setConfig({ playlunkyVersion: tag });
    } catch (err) {
      toast.error(`Couldn't save version: ${extractMessage(err)}`);
    }
  };

  const handleSpeedrunToggle = async (next: boolean) => {
    // Optimistic so the switch responds instantly. Read-modify-write against
    // the ini keeps concurrent edits in the options modal safe.
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

  const handleGuide = async () => {
    try {
      await openUrl(PLAYLUNKY_WIKI_URL);
    } catch (err) {
      toast.error(`Couldn't open browser: ${extractMessage(err)}`);
    }
  };

  const handleLaunch = async () => {
    setLaunching(true);
    // A first launch has to fetch Playlunky before it can start anything, so
    // say so rather than leaving the button spinning with no explanation.
    if (withPlaylunky && installed.length === 0) {
      toast.info(
        `Downloading Playlunky ${NIGHTLY_TAG}, this may take a moment…`,
      );
    }
    try {
      await launchGame(withPlaylunky, withOverlunky);
      toast.success(`Launching ${longDescribe(withPlaylunky, withOverlunky)}.`);
      await reload();
    } catch (err) {
      toast.error(`Launch failed: ${extractMessage(err)}`);
    } finally {
      setLaunching(false);
    }
  };

  return (
    <footer className="launch-dock">
      {/* Playlunky's settings, kept visible rather than behind a menu: they're
          here to be one click away, which a menu costs. They stay enabled when
          Playlunky is switched off, too. Downloading a version, changing an
          option or opening the guide are all reasonable things to do while the
          next launch happens to be vanilla, and the switch beside the button
          already says what will actually run.

          This group is the only thing allowed to shrink, so a narrow window
          clips it instead of letting it collide with the launch button. */}
      <div className="launch-dock-settings">
        <select
          className="launch-dock-version"
          value={installed.length === 0 ? PENDING_VERSION : version}
          disabled={installed.length === 0}
          onChange={(e) => void handleVersionChange(e.target.value)}
          aria-label="Playlunky version"
          title={
            installed.length === 0
              ? "Playlunky isn't installed yet. Launching downloads nightly automatically."
              : "Playlunky version to launch"
          }
        >
          {installed.length === 0 ? (
            <option value={PENDING_VERSION}>{PENDING_VERSION}</option>
          ) : (
            installed.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))
          )}
        </select>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setVersionsOpen(true)}
          title="Install or remove Playlunky versions"
        >
          <Package size={14} aria-hidden="true" /> Manage
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setOptionsOpen(true)}
          title="Playlunky options"
        >
          <Settings size={14} aria-hidden="true" /> Options
        </button>
        {/* Icon-only: the guide is the least-used control here and the one
            that can most afford to give up its width. */}
        <button
          type="button"
          className="btn btn-ghost launch-dock-icon-btn"
          onClick={() => void handleGuide()}
          title="Open the Playlunky wiki"
          aria-label="Open the Playlunky wiki"
        >
          <HelpCircle size={15} aria-hidden="true" />
        </button>
        <Switch
          label="Speedrun"
          checked={speedrun}
          disabled={speedrunBusy}
          onChange={(v) => void handleSpeedrunToggle(v)}
          title="Playlunky's speedrun mode"
        />
      </div>

      {/* The action cluster. The toggles sit against the button rather than
          across the bar from it, so what's selected is readable in the same
          glance as the thing that acts on it, and the label can stay short. */}
      <div className="launch-dock-action">
        <Switch
          label="Playlunky"
          checked={withPlaylunky}
          onChange={(v) => void toggle("playlunky", v)}
        />
        <Switch
          label="Overlunky"
          checked={withOverlunky}
          onChange={(v) => void toggle("overlunky", v)}
        />
        <button
          type="button"
          className="launch-dock-play"
          onClick={() => void handleLaunch()}
          disabled={launching}
        >
          <Play size={16} fill="currentColor" aria-hidden="true" />
          {launching
            ? "Launching…"
            : `Launch ${describe(withPlaylunky, withOverlunky)}`}
        </button>
      </div>

      <PlaylunkyVersionsModal
        open={versionsOpen}
        onClose={() => setVersionsOpen(false)}
        activeVersion={installed.length > 0 ? version : null}
        onSetActive={(tag) => void handleVersionChange(tag)}
        onChanged={() => void reload()}
      />
      <PlaylunkyOptionsModal
        open={optionsOpen}
        onClose={() => {
          setOptionsOpen(false);
          void reload();
        }}
      />
    </footer>
  );
}

/// Short tag for what will launch. The switches sit right beside the button,
/// so this only has to confirm the combination, not describe it: a full
/// sentence made the button wide enough to collide with everything else at the
/// window's minimum width.
function describe(playlunky: boolean, overlunky: boolean): string {
  if (playlunky && overlunky) return "(PL+OL)";
  if (playlunky) return "(PL)";
  if (overlunky) return "(OL)";
  return "(Vanilla)";
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

/// Spelled out for the toast, which has no switches next to it to give the
/// abbreviations context.
function longDescribe(playlunky: boolean, overlunky: boolean): string {
  if (playlunky && overlunky) return "with Playlunky + Overlunky";
  if (playlunky) return "with Playlunky";
  if (overlunky) return "with Overlunky";
  return "Spelunky 2";
}
