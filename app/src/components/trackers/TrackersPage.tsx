// Trackers page: two-column layout matching the Python tracker tab's
// spirit but with the sidebar rethought as three stacked config
// sections (Browser Source, Window, File).
//
// Left column = one card per tracker with its Python icon + name +
// action buttons (Window / Browser / File). Right sidebar = shared
// settings that apply to every tracker at once.
//
// Every source consumes the same WebSocket push stream so there's no
// polling: Browser is your OBS Browser Source URL, Window is a native
// WebviewWindow at the same URL (for OBS Window Capture), File is a
// text file the server writes on payload change (for OBS Text
// Source). File output + a few sidebar fields are placeholders here;
// wired up in T3e.

import { useCallback, useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import {
  Activity,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FileText,
  HelpCircle,
  MonitorPlay,
  Server,
} from "lucide-react";
import {
  getConfig,
  getFileSettings,
  getTrackerAlwaysOnTop,
  getTrackerConfig,
  getTrackerDiagnostics,
  getTrackerFilePath,
  getTrackerServerStatus,
  getWindowConfig,
  listSystemFonts,
  type CategoryTrackerConfig,
  type CoTrackerConfig,
  type ConsumerSnapshot,
  type GemTrackerConfig,
  type PacinoGolfTrackerConfig,
  type ThemeNameStyle,
  openTrackerFileDir,
  openTrackerWindow,
  type PacifistTrackerConfig,
  type SaveableCategory,
  setConfig,
  setFileSettings,
  setTrackerAlwaysOnTop,
  setTrackerConfig,
  setWindowConfig,
  type TimerTrackerConfig,
  startTrackerServer,
  stopTrackerServer,
  type FileOutputSettings,
  type TrackerServerStatus,
  type WindowConfig,
} from "../../lib/commands";
import { useToast } from "../shared/Toast";
import { Modal } from "../shared/Modal";
import categoryIcon from "../../assets/tracker_category.png";
import pacifistIcon from "../../assets/tracker_pacifist.png";
import timerIcon from "../../assets/tracker_timer.png";
import gemIcon from "../../assets/tracker_gem.png";
import golfIcon from "../../assets/tracker_golf.png";
import coIcon from "../../assets/tracker_co.png";
import "./TrackersPage.css";

const DEFAULT_PORT = 9526;

/// Chroma-key presets Python offered (Magenta / Green / Blue) plus
/// a "Custom" slot the user fills in via the hex field. Green is
/// the default because most modern OBS chroma-key filters ship with
/// it as the preset.
const COLOR_PRESETS: { label: string; value: string }[] = [
  { label: "Green", value: "#00ff00" },
  { label: "Magenta", value: "#ff00ff" },
  { label: "Blue", value: "#0000ff" },
];

const FONT_FAMILIES = [
  "Helvetica",
  "Arial",
  "Verdana",
  "Segoe UI",
  "Tahoma",
  "Georgia",
  "Times New Roman",
];

/// Each entry is one tracker. `defaultConfig` seeds the state before
/// the initial load lands; `renderSettings` provides the inline row
/// under the card (null for trackers without user-facing knobs). The
/// TRACKERS list is the only per-tracker source of truth on the
/// frontend, backend equivalence lives in `TrackersState::new`.
interface TrackerDef<C> {
  /** Route slug for both the WebSocket path and the HTML file
   *  name (`category` -> `/category.html` + `/ws/category`). */
  slug: string;
  name: string;
  iconSrc: string;
  /** True when the ml2_trackers side has an implementation shipped. */
  available: boolean;
  /** When true the tracker never spawns a file-mirror task; keep the
   *  Copy Path button hidden. Currently only Timer (payload changes
   *  every frame so mirroring to disk would rewrite ~60x/sec). Must
   *  stay in sync with TrackerTicker::never_writes_file on the Rust
   *  side. */
  neverWritesFile?: boolean;
  defaultConfig: C;
  renderSettings?: (config: C, onChange: (next: C) => void) => React.ReactNode;
}

// `TrackerDef<any>` here is deliberate: the array holds heterogeneous
// generic instances, and the per-tracker renderSettings casts through
// its own concrete config type. Callers never see the any at use
// sites, just `renderSettings(config, onChange)`.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const TRACKERS: TrackerDef<any>[] = [
  {
    slug: "category",
    name: "Category",
    iconSrc: categoryIcon,
    available: true,
    defaultConfig: {
      "always-show-modifiers": false,
      "excluded-categories": [],
    } as CategoryTrackerConfig,
    renderSettings: (config, onChange) => (
      <CategorySettings config={config} onChange={onChange} />
    ),
  },
  {
    slug: "pacifist",
    name: "Pacifist",
    iconSrc: pacifistIcon,
    available: true,
    defaultConfig: { "show-kill-count": false } as PacifistTrackerConfig,
    renderSettings: (config, onChange) => (
      <PacifistSettings config={config} onChange={onChange} />
    ),
  },
  {
    slug: "timer",
    name: "Timer",
    iconSrc: timerIcon,
    available: true,
    neverWritesFile: true,
    defaultConfig: {
      "show-total": true,
      "show-level": true,
      "show-last-level": true,
      "show-tutorial": false,
      "show-session": false,
      "show-ils": false,
    } as TimerTrackerConfig,
    renderSettings: (config, onChange) => (
      <TimerSettings config={config} onChange={onChange} />
    ),
  },
  {
    slug: "gem",
    name: "Gems",
    iconSrc: gemIcon,
    available: true,
    defaultConfig: {
      "show-total-gem-count": true,
      "show-colored-gem-count": false,
      "show-diamond-count": false,
      "show-yem-count": false,
      "show-diamond-percentage": false,
    } as GemTrackerConfig,
    renderSettings: (config, onChange) => (
      <GemSettings config={config} onChange={onChange} />
    ),
  },
  {
    slug: "pacino-golf",
    name: "Pacino Golf",
    iconSrc: golfIcon,
    available: true,
    defaultConfig: {
      "show-total-strokes": true,
      "show-resource-strokes": false,
      "show-treasure-strokes": false,
      "show-pacifist-strokes": false,
    } as PacinoGolfTrackerConfig,
    renderSettings: (config, onChange) => (
      <GolfSettings config={config} onChange={onChange} />
    ),
  },
  {
    slug: "co",
    name: "CO Tracker",
    iconSrc: coIcon,
    available: true,
    defaultConfig: {
      "theme-name-style": "Full theme names",
      "show-run-stats": true,
      "show-session-stats": true,
      "show-header": true,
    } as CoTrackerConfig,
    renderSettings: (config, onChange) => (
      <CoSettings config={config} onChange={onChange} />
    ),
  },
];

export function TrackersPage() {
  const [status, setStatus] = useState<TrackerServerStatus>({
    running: false,
    port: null,
  });
  const [portInput, setPortInput] = useState<string>(String(DEFAULT_PORT));
  const [autoStart, setAutoStart] = useState(false);
  const [windowConfig, setWindowConfigState] = useState<WindowConfig>({
    colorKey: "#00ff00",
    fontFamily: "Arial",
    fontSize: 24,
    fontColor: "#ffffff",
    strokeWidth: 0,
    strokeColor: "#000000",
  });
  const [alwaysOnTop, setAlwaysOnTopState] = useState(true);
  // Font families actually installed on this machine, loaded once. Falls back
  // to the built-in list until it arrives (or if enumeration fails).
  const [systemFonts, setSystemFonts] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    listSystemFonts()
      .then((fonts) => {
        if (!cancelled) setSystemFonts(fonts);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  const fontOptions = systemFonts.length > 0 ? systemFonts : FONT_FAMILIES;
  const [fileSettings, setFileSettingsState] = useState<FileOutputSettings>({
    outputDir: null,
    enabled: false,
  });
  // Configs are keyed by slug; seed with each tracker's defaultConfig
  // so the first render before the load resolves doesn't crash.
  const [trackerConfigs, setTrackerConfigs] = useState<Record<string, unknown>>(
    () => Object.fromEntries(TRACKERS.map((t) => [t.slug, t.defaultConfig])),
  );
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    (async () => {
      try {
        // Kick off the fixed-shape loads + every per-tracker config
        // load in a single Promise.all. The tracker configs land as
        // a Record<slug, config> so state gets one setter call.
        const trackerPromises = TRACKERS.map((t) =>
          getTrackerConfig<unknown>(t.slug).then((v) => [t.slug, v] as const),
        );
        const [cfg, current, wcfg, fcfg, aot, ...trackerEntries] =
          await Promise.all([
            getConfig(),
            getTrackerServerStatus(),
            getWindowConfig(),
            getFileSettings(),
            getTrackerAlwaysOnTop(),
            ...trackerPromises,
          ]);
        setPortInput(String(cfg.trackerServerPort || DEFAULT_PORT));
        setAutoStart(cfg.trackerServerAutoStart);
        setStatus(current);
        setWindowConfigState(wcfg);
        setFileSettingsState(fcfg);
        setAlwaysOnTopState(aot);
        setTrackerConfigs((prev) => ({
          ...prev,
          ...Object.fromEntries(trackerEntries),
        }));
      } catch (err) {
        toast.error(`Load failed: ${extractMessage(err)}`);
      }
    })();
  }, [toast]);

  const commitTrackerConfig = useCallback(
    async (slug: string, next: unknown) => {
      setTrackerConfigs((prev) => ({ ...prev, [slug]: next }));
      try {
        await setTrackerConfig(slug, next);
      } catch (err) {
        toast.error(`Save failed: ${extractMessage(err)}`);
      }
    },
    [toast],
  );

  const commitFileSettings = useCallback(
    async (next: FileOutputSettings) => {
      setFileSettingsState(next);
      try {
        await setFileSettings(next);
      } catch (err) {
        toast.error(`Save failed: ${extractMessage(err)}`);
      }
    },
    [toast],
  );

  const commitWindowConfig = useCallback(
    async (next: WindowConfig) => {
      setWindowConfigState(next);
      try {
        await setWindowConfig(next);
      } catch (err) {
        toast.error(`Save failed: ${extractMessage(err)}`);
      }
    },
    [toast],
  );

  const commitAlwaysOnTop = useCallback(
    async (next: boolean) => {
      setAlwaysOnTopState(next);
      try {
        await setTrackerAlwaysOnTop(next);
      } catch (err) {
        toast.error(`Save failed: ${extractMessage(err)}`);
      }
    },
    [toast],
  );

  const persistPort = useCallback(
    async (port: number) => {
      try {
        await setConfig({ trackerServerPort: port });
      } catch (err) {
        toast.error(`Save failed: ${extractMessage(err)}`);
      }
    },
    [toast],
  );

  const onStart = useCallback(async () => {
    const parsed = Number.parseInt(portInput, 10);
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > 65535) {
      toast.error("Port must be between 1 and 65535.");
      return;
    }
    setBusy(true);
    try {
      const next = await startTrackerServer(parsed);
      setStatus(next);
      await persistPort(parsed);
    } catch (err) {
      toast.error(`Start failed: ${extractMessage(err)}`);
    } finally {
      setBusy(false);
    }
  }, [portInput, persistPort, toast]);

  const onStop = useCallback(async () => {
    setBusy(true);
    try {
      const next = await stopTrackerServer();
      setStatus(next);
    } catch (err) {
      toast.error(`Stop failed: ${extractMessage(err)}`);
    } finally {
      setBusy(false);
    }
  }, [toast]);

  const onToggleAutoStart = useCallback(
    async (next: boolean) => {
      setAutoStart(next);
      try {
        await setConfig({ trackerServerAutoStart: next });
      } catch (err) {
        toast.error(`Save failed: ${extractMessage(err)}`);
        setAutoStart(!next);
      }
    },
    [toast],
  );

  const runningUrl =
    status.running && status.port ? `http://localhost:${status.port}/` : null;

  // Per-tracker action handlers. Wrapped in useCallback so the tracker
  // cards below don't re-render on every state change.
  const onWindow = useCallback(
    async (slug: string) => {
      try {
        await openTrackerWindow(slug);
      } catch (err) {
        toast.error(extractMessage(err));
      }
    },
    [toast],
  );
  const onBrowser = useCallback(
    async (slug: string) => {
      if (!status.running || !status.port) return;
      try {
        await openUrl(`http://localhost:${status.port}/${slug}.html`);
      } catch (err) {
        toast.error(extractMessage(err));
      }
    },
    [status, toast],
  );
  const onFile = useCallback(
    async (slug: string) => {
      try {
        const path = await getTrackerFilePath(slug);
        await writeText(path);
        toast.info(`Copied: ${path}`);
      } catch (err) {
        toast.error(extractMessage(err));
      }
    },
    [toast],
  );
  const onOpenFileDir = useCallback(async () => {
    try {
      await openTrackerFileDir();
    } catch (err) {
      toast.error(extractMessage(err));
    }
  }, [toast]);

  const toggleFileEnabled = useCallback(
    (on: boolean) => {
      void commitFileSettings({ ...fileSettings, enabled: on });
    },
    [fileSettings, commitFileSettings],
  );

  const chooseOutputDir = useCallback(async () => {
    try {
      const picked = await openDialog({
        directory: true,
        multiple: false,
        title: "Choose tracker output folder",
        defaultPath: fileSettings.outputDir ?? undefined,
      });
      if (typeof picked === "string" && picked.trim()) {
        void commitFileSettings({ ...fileSettings, outputDir: picked });
      }
    } catch (err) {
      toast.error(extractMessage(err));
    }
  }, [fileSettings, commitFileSettings, toast]);

  const clearOutputDir = useCallback(() => {
    void commitFileSettings({ ...fileSettings, outputDir: null });
  }, [fileSettings, commitFileSettings]);

  return (
    <div className="trackers-page">
      <div className="trackers-grid">
        <main className="trackers-main">
          <ul className="tracker-list">
            {TRACKERS.map((tracker) => (
              <TrackerCard
                key={tracker.slug}
                tracker={tracker}
                serverRunning={status.running}
                fileEnabled={fileSettings.enabled}
                onWindow={onWindow}
                onBrowser={onBrowser}
                onFile={onFile}
                settings={
                  tracker.renderSettings
                    ? tracker.renderSettings(
                        trackerConfigs[tracker.slug] ?? tracker.defaultConfig,
                        (next) => void commitTrackerConfig(tracker.slug, next),
                      )
                    : null
                }
              />
            ))}
          </ul>
        </main>

        <aside className="trackers-sidebar">
          <SidebarCard
            title="Tracker Server"
            icon={<Server size={16} aria-hidden="true" />}
            helpSize="lg"
            info={
              <div className="tracker-help-doc">
                <p>
                  The tracker server is a small HTTP + WebSocket service running
                  locally on your machine. A tracker is started once a window or
                  browser source connects to it.
                </p>

                <h3>Add a tracker to OBS</h3>
                <ol>
                  <li>
                    First you must start the tracker server. If the default port
                    conflict with another process/server on your machine choose
                    a different one.
                  </li>
                  <li>
                    Click the browser button to open the tracker in your default
                    browser. If it works, you can add it to OBS as a{" "}
                    <strong>Browser Source</strong> using the same URL.
                  </li>
                  <li>
                    You'll want to choose dimensions that fully contain the
                    tracker text. The default 800x200 is a good starting point
                    for most trackers, but you can resize the source in OBS to
                    fit your layout.
                  </li>
                </ol>

                <h3>Customize the look with CSS</h3>
                <p>
                  An OBS Browser Source has a <strong>Custom CSS</strong> box;
                  whatever you put there restyles the tracker live. The text
                  sits in an element with the class{" "}
                  <code>.tracker-content</code>.
                </p>
                <h4>Examples</h4>
                <p>
                  Change alignment on the page <code>body</code> so it applies
                  to any tracker, such as right-aligning the text when you want
                  the tracker on the right side of your layout:
                </p>
                <pre className="tracker-help-code">
                  <code>{`body {\n  text-align: right;\n}`}</code>
                </pre>
                <p>Recolor, resize, or outline the text:</p>
                <pre className="tracker-help-code">
                  <code>{`.tracker-content {\n  color: #ffd24a;\n  font-size: 56px;\n  -webkit-text-stroke: 2px #000;\n}`}</code>
                </pre>

                <p className="tracker-help-note">
                  <p>
                    <strong>Prefer a window?</strong>
                  </p>
                  <p>
                    Each tracker's <strong>Window</strong> button opens an
                    always-on-top window showing the exact same page if you
                    prefer to use a <strong>Window Capture</strong> source.
                  </p>
                </p>
              </div>
            }
          >
            {status.running ? (
              <>
                <div className="sidebar-status ok">
                  Running on port {status.port}
                </div>
                {runningUrl && (
                  <a
                    href={runningUrl}
                    className="sidebar-url"
                    onClick={(e) => {
                      e.preventDefault();
                      void openUrl(runningUrl);
                    }}
                  >
                    {runningUrl}
                  </a>
                )}
                <button
                  type="button"
                  className="btn btn-danger sidebar-action"
                  onClick={onStop}
                  disabled={busy}
                >
                  Stop server
                </button>
              </>
            ) : (
              <>
                <div className="sidebar-row">
                  <label className="sidebar-field">
                    <span className="sidebar-label">Port</span>
                    <input
                      type="text"
                      className="sidebar-input"
                      value={portInput}
                      onChange={(e) => setPortInput(e.target.value.trim())}
                      inputMode="numeric"
                      spellCheck={false}
                      aria-label="Server port"
                    />
                  </label>
                  <button
                    type="button"
                    className="btn btn-primary sidebar-action"
                    onClick={onStart}
                    disabled={busy}
                  >
                    Start server
                  </button>
                </div>
              </>
            )}
            <label className="sidebar-check">
              <input
                type="checkbox"
                checked={autoStart}
                onChange={(e) => onToggleAutoStart(e.target.checked)}
              />
              <span>Start server on app launch</span>
            </label>
          </SidebarCard>

          <SidebarCard
            title="Window"
            icon={<MonitorPlay size={16} aria-hidden="true" />}
            info={
              <div className="tracker-help-doc">
                <p>
                  These control how the tracker text looks in{" "}
                  <strong>both</strong> the popped-out Window and the OBS
                  Browser Source, they share one page.
                </p>
                <ul>
                  <li>
                    <strong>Chroma key</strong> - the solid background color.
                    Add a <strong>Chroma Key</strong> filter on the source in
                    OBS to key it out over your gameplay.
                  </li>
                  <li>
                    <strong>Text color</strong> and <strong>Outline</strong> -
                    fill color plus an optional outline, applied uniformly to
                    every tracker.
                  </li>
                  <li>
                    <strong>Font</strong> - the families installed on your
                    machine.
                  </li>
                </ul>
                <p className="tracker-help-note">
                  Want finer control? An OBS Browser Source&apos;s Custom CSS on{" "}
                  <code>.tracker-content</code> overrides all of this. See the
                  Tracker Server help for examples.
                </p>
              </div>
            }
          >
            <div className="sidebar-field">
              {/* A div, not a label: wrapping the preset buttons in a <label>
                made clicking the "Chroma key" text fire the first labelable
                child (the Green preset), snapping the color back to green. */}
              <span className="sidebar-label">Chroma key</span>
              <div className="color-preset-row">
                {COLOR_PRESETS.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    className={`color-preset${windowConfig.colorKey === preset.value ? " active" : ""}`}
                    style={{ backgroundColor: preset.value }}
                    onClick={() =>
                      void commitWindowConfig({
                        ...windowConfig,
                        colorKey: preset.value,
                      })
                    }
                    title={preset.label}
                    aria-label={preset.label}
                  />
                ))}
                <input
                  type="text"
                  className="sidebar-input color-hex-input"
                  value={windowConfig.colorKey}
                  onChange={(e) =>
                    setWindowConfigState({
                      ...windowConfig,
                      colorKey: e.target.value,
                    })
                  }
                  onBlur={() => void commitWindowConfig(windowConfig)}
                  spellCheck={false}
                  aria-label="Custom color hex"
                />
                <input
                  type="color"
                  className="color-picker-swatch"
                  value={sanitizeHex(windowConfig.colorKey)}
                  onChange={(e) =>
                    void commitWindowConfig({
                      ...windowConfig,
                      colorKey: e.target.value,
                    })
                  }
                  aria-label="Pick chroma-key color"
                  title="Pick a color"
                />
              </div>
            </div>
            <div className="sidebar-row">
              <label className="sidebar-field">
                <span className="sidebar-label">Font family</span>
                <select
                  className="sidebar-input"
                  value={
                    fontOptions.includes(windowConfig.fontFamily)
                      ? windowConfig.fontFamily
                      : "Custom"
                  }
                  onChange={(e) => {
                    if (e.target.value === "Custom") return;
                    void commitWindowConfig({
                      ...windowConfig,
                      fontFamily: e.target.value,
                    });
                  }}
                >
                  {fontOptions.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                  {!fontOptions.includes(windowConfig.fontFamily) && (
                    <option value="Custom">{windowConfig.fontFamily}</option>
                  )}
                </select>
              </label>
              <label className="sidebar-field font-size-field">
                <span className="sidebar-label">Size</span>
                <input
                  type="number"
                  min={8}
                  max={200}
                  className="sidebar-input"
                  value={windowConfig.fontSize}
                  onChange={(e) => {
                    const raw = Number.parseInt(e.target.value, 10);
                    if (!Number.isFinite(raw)) return;
                    setWindowConfigState({
                      ...windowConfig,
                      fontSize: raw,
                    });
                  }}
                  onBlur={() => void commitWindowConfig(windowConfig)}
                />
              </label>
            </div>
            <div className="sidebar-row">
              <div className="sidebar-field">
                <span className="sidebar-label">Text color</span>
                <div className="color-preset-row">
                  <input
                    type="text"
                    className="sidebar-input color-hex-input"
                    value={windowConfig.fontColor}
                    onChange={(e) =>
                      setWindowConfigState({
                        ...windowConfig,
                        fontColor: e.target.value,
                      })
                    }
                    onBlur={() => void commitWindowConfig(windowConfig)}
                    spellCheck={false}
                    aria-label="Text color hex"
                  />
                  <input
                    type="color"
                    className="color-picker-swatch"
                    value={sanitizeHex(windowConfig.fontColor)}
                    onChange={(e) =>
                      void commitWindowConfig({
                        ...windowConfig,
                        fontColor: e.target.value,
                      })
                    }
                    aria-label="Pick text color"
                    title="Pick text color"
                  />
                </div>
              </div>
            </div>
            <div className="sidebar-row">
              <label className="sidebar-field font-size-field">
                <span className="sidebar-label">Outline</span>
                <input
                  type="number"
                  min={0}
                  max={20}
                  className="sidebar-input"
                  value={windowConfig.strokeWidth}
                  onChange={(e) => {
                    const raw = Number.parseInt(e.target.value, 10);
                    if (!Number.isFinite(raw)) return;
                    setWindowConfigState({
                      ...windowConfig,
                      strokeWidth: Math.max(0, raw),
                    });
                  }}
                  onBlur={() => void commitWindowConfig(windowConfig)}
                  title="Text outline width in pixels (0 = none)"
                />
              </label>
              <div className="sidebar-field">
                <span className="sidebar-label">Outline color</span>
                <div className="color-preset-row">
                  <input
                    type="text"
                    className="sidebar-input color-hex-input"
                    value={windowConfig.strokeColor}
                    onChange={(e) =>
                      setWindowConfigState({
                        ...windowConfig,
                        strokeColor: e.target.value,
                      })
                    }
                    onBlur={() => void commitWindowConfig(windowConfig)}
                    spellCheck={false}
                    aria-label="Outline color hex"
                  />
                  <input
                    type="color"
                    className="color-picker-swatch"
                    value={sanitizeHex(windowConfig.strokeColor)}
                    onChange={(e) =>
                      void commitWindowConfig({
                        ...windowConfig,
                        strokeColor: e.target.value,
                      })
                    }
                    aria-label="Pick outline color"
                    title="Pick outline color"
                  />
                </div>
              </div>
            </div>
            <label className="sidebar-check">
              <input
                type="checkbox"
                checked={alwaysOnTop}
                onChange={(e) => void commitAlwaysOnTop(e.target.checked)}
              />
              <span>Keep tracker windows on top of other windows</span>
            </label>
          </SidebarCard>

          <SidebarCard
            title="File"
            icon={<FileText size={16} aria-hidden="true" />}
            info={
              <div className="tracker-help-doc">
                <p>
                  File output writes a tracker&apos;s current label to a text
                  file whenever it changes, so you can show it with a plain Text
                  source in OBS.
                </p>
                <ol>
                  <li>
                    Turn on file output and, if you like, choose an output
                    folder. The default is{" "}
                    <code>&lt;install&gt;/Mods/Modlunky2/trackers</code>.
                  </li>
                  <li>
                    Open a tracker&apos;s <strong>Window</strong> (or Browser)
                    so it starts writing <code>&lt;name&gt;.txt</code>.
                  </li>
                  <li>
                    In OBS add a <strong>Text (GDI+)</strong> source, check{" "}
                    <em>Read from file</em>, and point it at that{" "}
                    <code>.txt</code>.
                  </li>
                </ol>
              </div>
            }
          >
            <label className="sidebar-field">
              <span className="sidebar-label">Output folder</span>
              <div className="path-picker">
                <span
                  className={`path-picker-value${fileSettings.outputDir ? "" : " placeholder"}`}
                  title={fileSettings.outputDir ?? undefined}
                >
                  {fileSettings.outputDir ??
                    "(default: <install>/Mods/Modlunky2/trackers)"}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary path-picker-btn"
                  onClick={chooseOutputDir}
                >
                  Choose...
                </button>
                {fileSettings.outputDir && (
                  <button
                    type="button"
                    className="btn btn-ghost path-picker-btn"
                    onClick={clearOutputDir}
                    title="Reset to default"
                  >
                    Reset
                  </button>
                )}
              </div>
            </label>
            <label className="sidebar-check">
              <input
                type="checkbox"
                checked={fileSettings.enabled}
                onChange={(e) => toggleFileEnabled(e.target.checked)}
              />
              <span>Mirror tracker window to file while open</span>
            </label>
            <button
              type="button"
              className="btn btn-secondary sidebar-action"
              onClick={onOpenFileDir}
            >
              Open folder
            </button>
          </SidebarCard>

          <DiagnosticsCard />
        </aside>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------

interface TrackerCardProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  tracker: TrackerDef<any>;
  serverRunning: boolean;
  fileEnabled: boolean;
  onWindow: (slug: string) => void;
  onBrowser: (slug: string) => void;
  onFile: (slug: string) => void;
  /** Optional per-tracker settings body. When provided, the card
   *  grows a gear toggle in its action row that reveals this block
   *  underneath. Trackers with no config leave it null. */
  settings?: React.ReactNode;
}

function TrackerCard({
  tracker,
  serverRunning,
  fileEnabled,
  onWindow,
  onBrowser,
  onFile,
  settings,
}: TrackerCardProps) {
  const disabled = !tracker.available;
  return (
    <li className={`tracker-card${disabled ? " disabled" : ""}`}>
      <div className="tracker-card-row">
        <img
          src={tracker.iconSrc}
          alt=""
          className="tracker-card-icon"
          draggable={false}
        />
        <div className="tracker-card-body">
          <div className="tracker-card-head">
            <span className="tracker-card-name">{tracker.name}</span>
            {disabled && <span className="tracker-card-soon">Coming soon</span>}
          </div>
          {settings && <div className="tracker-card-settings">{settings}</div>}
        </div>
        <div className="tracker-card-actions">
          <button
            type="button"
            className="tracker-action"
            onClick={() => onWindow(tracker.slug)}
            disabled={disabled || !serverRunning}
            title={
              !serverRunning
                ? "Start the server first."
                : `Open ${tracker.name} in a native window.`
            }
          >
            <MonitorPlay size={14} aria-hidden="true" />
            <span>Window</span>
          </button>
          <button
            type="button"
            className="tracker-action"
            onClick={() => onBrowser(tracker.slug)}
            disabled={disabled || !serverRunning}
            title={
              !serverRunning
                ? "Start the server first."
                : `Open ${tracker.name} in your default browser.`
            }
          >
            <ExternalLink size={14} aria-hidden="true" />
            <span>Browser</span>
          </button>
          {fileEnabled && !tracker.neverWritesFile && (
            <button
              type="button"
              className="tracker-action"
              onClick={() => onFile(tracker.slug)}
              disabled={disabled}
              title={`Copy the path to ${tracker.name}.txt to the clipboard.`}
            >
              <FileText size={14} aria-hidden="true" />
              <span>Copy path</span>
            </button>
          )}
        </div>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------

interface SidebarCardProps {
  title: string;
  icon?: React.ReactNode;
  /** Explanatory copy the user reveals with the `?` button on the
   *  header. Kept out of the body so the settings surface stays
   *  focused; hidden by default so returning users don't re-read
   *  the same paragraph on every visit. */
  info?: React.ReactNode;
  /** Size of the help modal. Defaults to `md`; content-heavy cards can bump
   *  it up so long docs breathe. */
  helpSize?: "sm" | "md" | "lg" | "xl";
  children: React.ReactNode;
}

function SidebarCard({
  title,
  icon,
  info,
  helpSize = "md",
  children,
}: SidebarCardProps) {
  const [infoOpen, setInfoOpen] = useState(false);
  return (
    <section className="sidebar-card">
      <div className="sidebar-card-title">
        <span className="sidebar-card-title-left">
          {icon}
          <span>{title}</span>
        </span>
        {info && (
          <button
            type="button"
            className={`sidebar-card-help${infoOpen ? " active" : ""}`}
            onClick={() => setInfoOpen(true)}
            title="Help"
            aria-label={`${title} help`}
          >
            <HelpCircle size={14} aria-hidden="true" />
          </button>
        )}
      </div>
      <div className="sidebar-card-body">{children}</div>
      {info && infoOpen && (
        <Modal
          open
          onClose={() => setInfoOpen(false)}
          title={title}
          size={helpSize}
        >
          <div className="tracker-help">{info}</div>
        </Modal>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------

/// Category tracker's inline settings body. Renders under the
/// Category card when the user opens the gear toggle. Two knobs:
/// `always_show_modifiers` (surface No%/No Gold/Pacifist before the
/// run has committed to a category) and `excluded_categories` (drop
/// specific labels from the tracker's output entirely).
const CATEGORY_OPTIONS: { value: SaveableCategory; label: string }[] = [
  { value: "No%", label: "No%" },
  { value: "No Gold", label: "No Gold" },
  { value: "Pacifist", label: "Pacifist" },
  { value: "Score", label: "Score" },
];

function CategorySettings({
  config,
  onChange,
}: {
  config: CategoryTrackerConfig;
  onChange: (next: CategoryTrackerConfig) => void;
}) {
  const excluded = new Set(config["excluded-categories"]);
  const toggle = (cat: SaveableCategory, on: boolean) => {
    const next = new Set(excluded);
    if (on) next.delete(cat);
    else next.add(cat);
    onChange({
      ...config,
      "excluded-categories": CATEGORY_OPTIONS.map((c) => c.value).filter((c) =>
        next.has(c),
      ),
    });
  };
  return (
    <div className="category-settings-row">
      <label className="sidebar-check">
        <input
          type="checkbox"
          checked={config["always-show-modifiers"]}
          onChange={(e) =>
            onChange({ ...config, "always-show-modifiers": e.target.checked })
          }
        />
        <span>Show all modifiers before 1-3</span>
      </label>
      <div className="category-settings-divider" aria-hidden="true" />
      {CATEGORY_OPTIONS.map((opt) => (
        <label key={opt.value} className="sidebar-check">
          <input
            type="checkbox"
            checked={!excluded.has(opt.value)}
            onChange={(e) => toggle(opt.value, e.target.checked)}
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------

/// Timer tracker settings. Six independent toggles matching Python's
/// "Timers shown" group.
const TIMER_OPTIONS: { key: keyof TimerTrackerConfig; label: string }[] = [
  { key: "show-total", label: "Total" },
  { key: "show-level", label: "Level" },
  { key: "show-last-level", label: "Last" },
  { key: "show-tutorial", label: "Tutorial" },
  { key: "show-session", label: "Session" },
  { key: "show-ils", label: "ILs" },
];

function TimerSettings({
  config,
  onChange,
}: {
  config: TimerTrackerConfig;
  onChange: (next: TimerTrackerConfig) => void;
}) {
  return (
    <div className="category-settings-row">
      {TIMER_OPTIONS.map((opt) => (
        <label key={opt.key} className="sidebar-check">
          <input
            type="checkbox"
            checked={config[opt.key]}
            onChange={(e) =>
              onChange({ ...config, [opt.key]: e.target.checked })
            }
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

/// Pacifist tracker's inline settings body. Just the single
/// `show-kill-count` toggle Python exposed.
function PacifistSettings({
  config,
  onChange,
}: {
  config: PacifistTrackerConfig;
  onChange: (next: PacifistTrackerConfig) => void;
}) {
  return (
    <div className="category-settings-row">
      <label className="sidebar-check">
        <input
          type="checkbox"
          checked={config["show-kill-count"]}
          onChange={(e) =>
            onChange({ ...config, "show-kill-count": e.target.checked })
          }
        />
        <span>Show kill count</span>
      </label>
    </div>
  );
}

// ---------------------------------------------------------------------

const GEM_OPTIONS: { key: keyof GemTrackerConfig; label: string }[] = [
  { key: "show-total-gem-count", label: "Total" },
  { key: "show-colored-gem-count", label: "Colored" },
  { key: "show-diamond-count", label: "Diamonds" },
  { key: "show-yem-count", label: "Yems" },
  { key: "show-diamond-percentage", label: "Diamond %" },
];

function GemSettings({
  config,
  onChange,
}: {
  config: GemTrackerConfig;
  onChange: (next: GemTrackerConfig) => void;
}) {
  return (
    <div className="category-settings-row">
      {GEM_OPTIONS.map((opt) => (
        <label key={opt.key} className="sidebar-check">
          <input
            type="checkbox"
            checked={config[opt.key]}
            onChange={(e) =>
              onChange({ ...config, [opt.key]: e.target.checked })
            }
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

const GOLF_OPTIONS: { key: keyof PacinoGolfTrackerConfig; label: string }[] = [
  { key: "show-total-strokes", label: "Total" },
  { key: "show-resource-strokes", label: "Resources" },
  { key: "show-treasure-strokes", label: "Treasure" },
  { key: "show-pacifist-strokes", label: "Kills" },
];

function GolfSettings({
  config,
  onChange,
}: {
  config: PacinoGolfTrackerConfig;
  onChange: (next: PacinoGolfTrackerConfig) => void;
}) {
  return (
    <div className="category-settings-row">
      {GOLF_OPTIONS.map((opt) => (
        <label key={opt.key} className="sidebar-check">
          <input
            type="checkbox"
            checked={config[opt.key]}
            onChange={(e) =>
              onChange({ ...config, [opt.key]: e.target.checked })
            }
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

const THEME_NAME_STYLES: ThemeNameStyle[] = [
  "Full theme names",
  "Short theme names",
  "Two-letter theme names",
  "No theme names",
];

type CoBoolKey = "show-run-stats" | "show-session-stats" | "show-header";
const CO_TOGGLES: { key: CoBoolKey; label: string }[] = [
  { key: "show-run-stats", label: "Run" },
  { key: "show-session-stats", label: "Session" },
  { key: "show-header", label: "Header" },
];

function CoSettings({
  config,
  onChange,
}: {
  config: CoTrackerConfig;
  onChange: (next: CoTrackerConfig) => void;
}) {
  return (
    <div className="category-settings-row">
      <label className="sidebar-check">
        <select
          className="sidebar-input"
          value={config["theme-name-style"]}
          onChange={(e) =>
            onChange({
              ...config,
              "theme-name-style": e.target.value as ThemeNameStyle,
            })
          }
        >
          {THEME_NAME_STYLES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <div className="category-settings-divider" aria-hidden="true" />
      {CO_TOGGLES.map((opt) => (
        <label key={opt.key} className="sidebar-check">
          <input
            type="checkbox"
            checked={config[opt.key]}
            onChange={(e) =>
              onChange({ ...config, [opt.key]: e.target.checked })
            }
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------

/// Live view of the tracker refcount registry. Collapsed by default;
/// while expanded polls `get_tracker_diagnostics` once a second so a
/// user can watch attach/detach in real time (open the window,
/// count should go 0 -> 1; add an OBS Browser Source, 1 -> 2; close
/// the window, 2 -> 1; etc).
function DiagnosticsCard() {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<ConsumerSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const snap = await getTrackerDiagnostics();
        if (!cancelled) {
          setRows(snap);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(extractMessage(err));
      }
    };
    void tick();
    const id = window.setInterval(tick, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [open]);

  return (
    <section className="sidebar-card">
      <button
        type="button"
        className="diagnostics-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="sidebar-card-title-left">
          <Activity size={16} aria-hidden="true" />
          <span>Diagnostics</span>
        </span>
        {open ? (
          <ChevronDown size={14} aria-hidden="true" />
        ) : (
          <ChevronRight size={14} aria-hidden="true" />
        )}
      </button>
      {open && (
        <div className="sidebar-card-body">
          {error && <div className="sidebar-status err">{error}</div>}
          {rows.length === 0 && !error ? (
            <p className="sidebar-hint">
              No active trackers. Open a Window or connect a Browser Source to
              see refcount changes here.
            </p>
          ) : (
            <table className="diagnostics-table">
              <thead>
                <tr>
                  <th>Tracker</th>
                  <th>Consumers</th>
                  <th>Tick</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.slug}>
                    <td>{r.slug}</td>
                    <td className="num">{r.consumers}</td>
                    <td className={r.tickRunning ? "yes" : "no"}>
                      {r.tickRunning ? "running" : "stopped"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------

/// input[type=color] insists on a `#rrggbb` value; user-typed hex may
/// omit the `#` or include shorthand. Falls back to green if the
/// input isn't parseable so the picker still opens instead of
/// hard-erroring.
function sanitizeHex(value: string): string {
  const trimmed = value.trim();
  const withHash = trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
  if (/^#[0-9a-fA-F]{6}$/.test(withHash)) return withHash.toLowerCase();
  if (/^#[0-9a-fA-F]{3}$/.test(withHash)) {
    // Expand shorthand `#abc` to `#aabbcc`.
    const [, a, b, c] = withHash.match(/^#(.)(.)(.)$/)!;
    return `#${a}${a}${b}${b}${c}${c}`.toLowerCase();
  }
  return "#00ff00";
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
