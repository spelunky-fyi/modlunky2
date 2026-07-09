import { useEffect, useMemo, useState } from "react";
import { ask } from "@tauri-apps/plugin-dialog";
import { Modal } from "../shared/Modal";
import { useToast } from "../shared/Toast";
import {
  clearPlaylunkyCache,
  getConfig,
  getPlaylunkyOptions,
  setConfig,
  setPlaylunkyOptions,
  syncDesktopShortcut,
} from "../../lib/commands";
import type { PlaylunkyOptions } from "../../types/playlunkyOptions";
import "./PlaylunkyOptionsModal.css";

interface PlaylunkyOptionsModalProps {
  open: boolean;
  onClose: () => void;
}

interface LauncherFlags {
  console: boolean;
  overlunky: boolean;
  shortcut: boolean;
}

type Status = "loading" | "idle" | "saving";

export function PlaylunkyOptionsModal({
  open,
  onClose,
}: PlaylunkyOptionsModalProps) {
  const toast = useToast();
  const [initial, setInitial] = useState<PlaylunkyOptions | null>(null);
  const [options, setOptions] = useState<PlaylunkyOptions | null>(null);
  const [initialFlags, setInitialFlags] = useState<LauncherFlags>({
    console: false,
    overlunky: false,
    shortcut: false,
  });
  const [flags, setFlags] = useState<LauncherFlags>({
    console: false,
    overlunky: false,
    shortcut: false,
  });
  const [status, setStatus] = useState<Status>("loading");
  const [clearingCache, setClearingCache] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setStatus("loading");
    Promise.all([getPlaylunkyOptions(), getConfig()])
      .then(([opts, cfg]) => {
        if (cancelled) return;
        setInitial(opts);
        setOptions(opts);
        const loadedFlags: LauncherFlags = {
          console: cfg.playlunkyConsole,
          overlunky: cfg.playlunkyOverlunky,
          shortcut: cfg.playlunkyShortcut,
        };
        setInitialFlags(loadedFlags);
        setFlags(loadedFlags);
        setStatus("idle");
      })
      .catch((err) => {
        if (cancelled) return;
        toast.error(`Couldn't read Playlunky options: ${extractMessage(err)}`);
        setStatus("idle");
      });
    return () => {
      cancelled = true;
    };
  }, [open, toast]);

  const optionsDirty = useMemo(
    () => JSON.stringify(options) !== JSON.stringify(initial),
    [options, initial],
  );
  const flagsDirty = useMemo(
    () =>
      flags.console !== initialFlags.console ||
      flags.overlunky !== initialFlags.overlunky ||
      flags.shortcut !== initialFlags.shortcut,
    [flags, initialFlags],
  );
  const dirty = optionsDirty || flagsDirty;

  const handleSave = async () => {
    if (!options) return;
    setStatus("saving");
    try {
      if (optionsDirty) {
        await setPlaylunkyOptions(options);
        setInitial(options);
      }
      if (flagsDirty) {
        await setConfig({
          playlunkyConsole: flags.console,
          playlunkyOverlunky: flags.overlunky,
          playlunkyShortcut: flags.shortcut,
        });
        setInitialFlags(flags);
      }
      // Keep the desktop shortcut in sync every save, since launch flags,
      // command_prefix, or the selected version may have changed.
      await syncDesktopShortcut().catch(() => {
        // Non-fatal; a missing shortcut is not worth blocking the save.
      });
      toast.success("Playlunky options saved.");
      onClose();
    } catch (err) {
      toast.error(`Save failed: ${extractMessage(err)}`);
    } finally {
      setStatus("idle");
    }
  };

  const handleClose = () => {
    if (status === "saving") return;
    onClose();
  };

  const handleClearCache = async () => {
    const yes = await ask(
      "Clear Playlunky's cache at Mods/Packs/.db? Playlunky will rebuild it on the next launch.",
      { title: "Clear cache", kind: "warning" },
    );
    if (!yes) return;
    setClearingCache(true);
    try {
      await clearPlaylunkyCache();
      toast.success("Playlunky cache cleared.");
    } catch (err) {
      toast.error(`Clear failed: ${extractMessage(err)}`);
    } finally {
      setClearingCache(false);
    }
  };

  const canSave = dirty && status === "idle" && options !== null;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Playlunky options"
      size="lg"
      footer={
        <>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={handleClose}
            disabled={status === "saving"}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void handleSave()}
            disabled={!canSave}
          >
            {status === "saving" ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      {status === "loading" || !options ? (
        <p className="plo-hint">Loading…</p>
      ) : (
        <div className="plo-form">
          <Section title="Launcher">
            <Toggle
              label="Show Playlunky console window"
              value={flags.console}
              onChange={(v) => setFlags((f) => ({ ...f, console: v }))}
            />
            <Toggle
              label="Launch Overlunky alongside Playlunky"
              value={flags.overlunky}
              onChange={(v) => setFlags((f) => ({ ...f, overlunky: v }))}
            />
            <Toggle
              label="Keep a Play Spelunky 2 shortcut on the desktop"
              value={flags.shortcut}
              onChange={(v) => setFlags((f) => ({ ...f, shortcut: v }))}
            />
          </Section>

          <Section title="General">
            <Toggle
              label="Enable loose file warning"
              value={options.general.enableLooseFileWarning}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, enableLooseFileWarning: v },
                })
              }
            />
            <Toggle
              label="Disable asset caching"
              value={options.general.disableAssetCaching}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, disableAssetCaching: v },
                })
              }
            />
            <Toggle
              label="Speedrun mode"
              value={options.general.speedrunMode}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, speedrunMode: v },
                })
              }
            />
            <Toggle
              label="Block save game"
              value={options.general.blockSaveGame}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, blockSaveGame: v },
                })
              }
            />
            <Toggle
              label="Allow save game mods"
              value={options.general.allowSaveGameMods}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, allowSaveGameMods: v },
                })
              }
            />
            <Toggle
              label="Disable Steam achievements"
              value={options.general.disableSteamAchievements}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, disableSteamAchievements: v },
                })
              }
            />
            <Toggle
              label="Use Playlunky save"
              value={options.general.usePlaylunkySave}
              onChange={(v) =>
                setOptions({
                  ...options,
                  general: { ...options.general, usePlaylunkySave: v },
                })
              }
            />
          </Section>

          <Section title="Script">
            <Toggle
              label="Enable developer mode"
              value={options.script.enableDeveloperMode}
              onChange={(v) =>
                setOptions({
                  ...options,
                  script: { ...options.script, enableDeveloperMode: v },
                })
              }
            />
            <Toggle
              label="Enable developer console"
              value={options.script.enableDeveloperConsole}
              onChange={(v) =>
                setOptions({
                  ...options,
                  script: { ...options.script, enableDeveloperConsole: v },
                })
              }
            />
            <NumberField
              label="Console history size"
              value={options.script.consoleHistorySize}
              onChange={(v) =>
                setOptions({
                  ...options,
                  script: { ...options.script, consoleHistorySize: v },
                })
              }
            />
          </Section>

          <Section title="Audio">
            <Toggle
              label="Enable loose audio files"
              value={options.audio.enableLooseAudioFiles}
              onChange={(v) =>
                setOptions({
                  ...options,
                  audio: { ...options.audio, enableLooseAudioFiles: v },
                })
              }
            />
            <Toggle
              label="Cache decoded audio files"
              value={options.audio.cacheDecodedAudioFiles}
              onChange={(v) =>
                setOptions({
                  ...options,
                  audio: { ...options.audio, cacheDecodedAudioFiles: v },
                })
              }
            />
            <Toggle
              label="Synchronous update"
              value={options.audio.synchronousUpdate}
              onChange={(v) =>
                setOptions({
                  ...options,
                  audio: { ...options.audio, synchronousUpdate: v },
                })
              }
            />
          </Section>

          <Section title="Sprite">
            <Toggle
              label="Random character select"
              value={options.sprite.randomCharacterSelect}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, randomCharacterSelect: v },
                })
              }
            />
            <Toggle
              label="Link related files"
              value={options.sprite.linkRelatedFiles}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, linkRelatedFiles: v },
                })
              }
            />
            <Toggle
              label="Generate character journal stickers"
              value={options.sprite.generateCharacterJournalStickers}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: {
                    ...options.sprite,
                    generateCharacterJournalStickers: v,
                  },
                })
              }
            />
            <Toggle
              label="Generate character journal entries"
              value={options.sprite.generateCharacterJournalEntries}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: {
                    ...options.sprite,
                    generateCharacterJournalEntries: v,
                  },
                })
              }
            />
            <Toggle
              label="Generate sticker pixel art"
              value={options.sprite.generateStickerPixelArt}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, generateStickerPixelArt: v },
                })
              }
            />
            <Toggle
              label="Enable sprite hot loading"
              value={options.sprite.enableSpriteHotLoading}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, enableSpriteHotLoading: v },
                })
              }
            />
            <NumberField
              label="Sprite hot load delay (ms)"
              value={options.sprite.spriteHotLoadDelay}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, spriteHotLoadDelay: v },
                })
              }
            />
            <Toggle
              label="Enable customizable sheets"
              value={options.sprite.enableCustomizableSheets}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, enableCustomizableSheets: v },
                })
              }
            />
            <Toggle
              label="Enable luminance scaling"
              value={options.sprite.enableLuminanceScaling}
              onChange={(v) =>
                setOptions({
                  ...options,
                  sprite: { ...options.sprite, enableLuminanceScaling: v },
                })
              }
            />
          </Section>

          <Section title="Cache" full>
            <p className="plo-danger-hint">
              Playlunky keeps a cache under Mods/Packs/.db to speed up
              subsequent launches. Clearing it forces a rebuild on the
              next launch.
            </p>
            <button
              type="button"
              className="btn btn-ghost plo-danger-btn"
              onClick={() => void handleClearCache()}
              disabled={clearingCache || status === "saving"}
            >
              {clearingCache ? "Clearing…" : "Clear Playlunky cache"}
            </button>
          </Section>
        </div>
      )}
    </Modal>
  );
}

function Section({
  title,
  children,
  full,
}: {
  title: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <section className={`plo-section${full ? " plo-section-full" : ""}`}>
      <h3 className="plo-section-title">{title}</h3>
      <div className="plo-section-body">{children}</div>
    </section>
  );
}

function Toggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="plo-toggle">
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="plo-number">
      <span>{label}</span>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(e) => {
          const n = parseInt(e.target.value, 10);
          onChange(Number.isFinite(n) && n >= 0 ? n : 0);
        }}
      />
    </label>
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
