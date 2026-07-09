import { useCallback, useEffect, useRef, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { Download, Radio, ScrollText, Settings } from "lucide-react";
import { ModsPage } from "./components/mods/ModsPage";
import { ExtractPage } from "./components/extract/ExtractPage";
import { OverlunkyPage } from "./components/overlunky/OverlunkyPage";
import { TrackersPage } from "./components/trackers/TrackersPage";
import { LevelsPage } from "./components/levels/LevelsPage";
import { EditorWindow } from "./components/levels/EditorWindow";
import { CharacterChooser } from "./components/characters/CharacterChooser";
import { SettingsModal } from "./components/settings/SettingsModal";
import { ToastProvider } from "./components/shared/Toast";
import { LogsWindow } from "./components/shared/LogsWindow";
import { FolderMenu } from "./components/shared/FolderMenu";
import {
  appVersion,
  getConfig,
  getFyiWsStatus,
  getModlunkyVersion,
  installUpdate,
  openLogsWindow,
  refreshFyiWs,
  type FyiWsStatus,
  type ModlunkyVersionInfo,
  setConfig,
  type EditorMode,
} from "./lib/commands";
import { useToast } from "./components/shared/Toast";

interface EditorWindowRoute {
  kind: "editor";
  pack: string;
  mode: EditorMode;
}

interface LogsWindowRoute {
  kind: "logs";
}

interface CharactersWindowRoute {
  kind: "characters";
  /** Scope to a single pack (per-pack variant), or null for the global view. */
  pack: string | null;
}

type WindowRoute =
  | EditorWindowRoute
  | LogsWindowRoute
  | CharactersWindowRoute;

// Rust injects one of these into the target window before any of the app's
// own JS runs, so we can pick the shell synchronously at first render. See
// level_editor::open_level_editor_window, log_buffer::open_logs_window, and
// characters::open_character_chooser_window.
declare global {
  interface Window {
    __editorContext?: { pack?: string; mode?: string };
    __logsContext?: { kind?: string };
    __charChooserContext?: { kind?: string; pack?: string };
  }
}

function readRoute(): WindowRoute | null {
  if (window.__logsContext?.kind === "logs") {
    return { kind: "logs" };
  }
  if (window.__charChooserContext?.kind === "characters") {
    return { kind: "characters", pack: window.__charChooserContext.pack ?? null };
  }
  const ctx = window.__editorContext;
  if (ctx && ctx.pack && ctx.mode) {
    const mode: EditorMode | null =
      ctx.mode === "vanilla" || ctx.mode === "custom" ? ctx.mode : null;
    if (mode) {
      return { kind: "editor", pack: ctx.pack, mode };
    }
  }
  return null;
}

type Tab = "mods" | "overlunky" | "extract" | "levels" | "trackers";

const TABS: { id: Tab; label: string }[] = [
  { id: "mods", label: "Mods" },
  { id: "overlunky", label: "Overlunky" },
  { id: "extract", label: "Extract Assets" },
  { id: "levels", label: "Level Editor" },
  { id: "trackers", label: "Trackers" },
];

function App() {
  const route = readRoute();
  return (
    <ToastProvider>
      {route?.kind === "editor" ? (
        <EditorWindow pack={route.pack} mode={route.mode} />
      ) : route?.kind === "logs" ? (
        <LogsWindow />
      ) : route?.kind === "characters" ? (
        <CharacterChooser pack={route.pack} />
      ) : (
        <AppShell />
      )}
    </ToastProvider>
  );
}

/** Guard so a corrupted config value can't crash the shell on load. */
function isTab(value: string | null | undefined): value is Tab {
  return (
    value === "mods" ||
    value === "overlunky" ||
    value === "extract" ||
    value === "levels" ||
    value === "trackers"
  );
}

function AppShell() {
  const [activeTab, setActiveTab] = useState<Tab>("mods");
  const [version, setVersion] = useState("");
  const [versionInfo, setVersionInfo] = useState<ModlunkyVersionInfo | null>(null);
  const [updating, setUpdating] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [fyiStatus, setFyiStatus] = useState<FyiWsStatus>("disconnected");
  const [fyiConfigured, setFyiConfigured] = useState<boolean>(false);
  const toast = useToast();
  // Only start writing lastTab after the first restore so the write we
  // fire on mount doesn't overwrite the value the user picked previously
  // with the default we're rendering now.
  const [restoredTab, setRestoredTab] = useState(false);

  useEffect(() => {
    appVersion().then(setVersion).catch(() => setVersion(""));
    // Latest-version check is best-effort. Failure just leaves the
    // banner hidden; user can still see their current version.
    const check = () =>
      getModlunkyVersion()
        .then(setVersionInfo)
        .catch(() => setVersionInfo(null));
    void check();
    // Repoll every 30 min so long-lived sessions surface the update
    // pill without needing an app restart. Matches Python's periodic
    // check_for_updates loop.
    const timer = window.setInterval(check, 30 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, []);

  // spelunky.fyi push-install status: initial fetch + live updates.
  useEffect(() => {
    void getFyiWsStatus().then(setFyiStatus).catch(() => {});
    const unlisten = listen<FyiWsStatus>("fyi-ws-status", (event) => {
      setFyiStatus(event.payload);
    });
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, []);

  const refreshFyiConfigured = useCallback(() => {
    getConfig()
      .then((cfg) =>
        setFyiConfigured(Boolean(cfg.spelunkyFyiApiToken?.trim())),
      )
      .catch(() => setFyiConfigured(false));
  }, []);

  useEffect(() => {
    refreshFyiConfigured();
  }, [refreshFyiConfigured]);

  const onUpdate = useCallback(async () => {
    if (updating) return;
    setUpdating(true);
    try {
      await installUpdate();
      // Success spawns the new exe + asks Tauri to exit; we don't
      // usually reach any code past this line, but leaving the
      // spinner up is nicer than a flash of idle UI.
    } catch (err) {
      // Fall back to the GitHub release page so the user has a
      // manual escape hatch when the in-place swap failed (locked
      // file, AV quarantine, etc.).
      toast.error(extractMessage(err));
      if (versionInfo?.releasePageUrl) {
        try {
          await openUrl(versionInfo.releasePageUrl);
        } catch {
          // openUrl already threw once; ignore the second failure.
        }
      }
      setUpdating(false);
    }
  }, [updating, versionInfo, toast]);

  // Restore the previous tab on mount. Silent on failure: an unreadable
  // config just leaves the default tab active.
  useEffect(() => {
    getConfig()
      .then((cfg) => {
        if (isTab(cfg.lastTab)) setActiveTab(cfg.lastTab);
      })
      .catch(() => {})
      .finally(() => setRestoredTab(true));
  }, []);

  // Reveal the window once the tab restore lands, so the user never sees
  // the default tab flash to the saved tab. Backstop: if getConfig hangs
  // for more than a beat, show the window anyway (with whatever tab we
  // ended up on) rather than leave the user with no window at all.
  const shownRef = useRef(false);
  const revealWindow = useCallback(() => {
    if (shownRef.current) return;
    shownRef.current = true;
    void getCurrentWindow().show();
  }, []);
  useEffect(() => {
    if (restoredTab) revealWindow();
  }, [restoredTab, revealWindow]);
  useEffect(() => {
    const timer = window.setTimeout(revealWindow, 750);
    return () => window.clearTimeout(timer);
  }, [revealWindow]);

  // Persist tab changes after the initial restore lands.
  useEffect(() => {
    if (!restoredTab) return;
    void setConfig({ lastTab: activeTab }).catch(() => {});
  }, [activeTab, restoredTab]);

  return (
    <div className="app">
      <nav className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab-bar-tab${activeTab === tab.id ? " active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
        <span className="tab-bar-divider" />
        {versionInfo?.updateAvailable && versionInfo.latest && (
          <button
            className={`update-pill${updating ? " updating" : ""}`}
            onClick={onUpdate}
            disabled={updating}
            title={`Update to ${versionInfo.latest}`}
          >
            <Download size={13} aria-hidden="true" />
            <span>{updating ? "Updating..." : `Update to ${versionInfo.latest}`}</span>
          </button>
        )}
        {fyiConfigured && (
          <button
            type="button"
            className={`fyi-status fyi-status-${fyiStatus}`}
            title={fyiStatusTitle(fyiStatus)}
            aria-label={`spelunky.fyi ${fyiStatusTitle(fyiStatus)}. Click to reconnect.`}
            onClick={() => {
              void refreshFyiWs().catch((err) =>
                toast.error(`Reconnect failed: ${extractMessage(err)}`),
              );
            }}
          >
            <Radio size={12} aria-hidden="true" />
            <span className="fyi-status-label">{FYI_STATUS_LABEL[fyiStatus]}</span>
          </button>
        )}
        {version && <span className="app-version">v{version}</span>}
        <FolderMenu />
        <button
          className="icon-button"
          aria-label="Logs"
          title="View logs and toast history"
          onClick={() => {
            void openLogsWindow().catch((err) =>
              toast.error(`Couldn't open logs window: ${extractMessage(err)}`),
            );
          }}
        >
          <ScrollText size={18} aria-hidden="true" />
        </button>
        <button
          className="icon-button"
          aria-label="Settings"
          title="Settings"
          onClick={() => setSettingsOpen(true)}
        >
          <Settings size={18} aria-hidden="true" />
        </button>
      </nav>
      <main
        className={`tab-content${activeTab === "levels" || activeTab === "trackers" ? " tab-content-fullbleed" : ""}`}
      >
        {activeTab === "mods" && <ModsPage />}
        {activeTab === "overlunky" && <OverlunkyPage />}
        {activeTab === "extract" && <ExtractPage />}
        {activeTab === "levels" && <LevelsPage />}
        {activeTab === "trackers" && <TrackersPage />}
      </main>
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => refreshFyiConfigured()}
      />
    </div>
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

const FYI_STATUS_LABEL: Record<FyiWsStatus, string> = {
  disconnected: "Offline",
  connecting: "Connecting…",
  connected: "Live",
};

function fyiStatusTitle(status: FyiWsStatus): string {
  switch (status) {
    case "connected":
      return "spelunky.fyi push installs are live. Click 'Install in modlunky2' on any mod page to trigger an install here. (Click here to force a reconnect.)";
    case "connecting":
      return "Connecting to spelunky.fyi… (Click here to restart the attempt.)";
    case "disconnected":
      return "Not connected to spelunky.fyi. Click to retry, or check your API token in Settings.";
  }
}

export default App;
