import { useCallback, useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { listen } from "@tauri-apps/api/event";
import {
  BookOpen,
  Cog,
  Download,
  Package,
  Play,
  Zap,
} from "lucide-react";
import {
  downloadOverlunky,
  isOverlunkyInstalled,
  launchOverlunky,
  type OverlunkyLaunchMode,
} from "../../lib/commands";
import { useToast } from "../shared/Toast";
import "./OverlunkyPage.css";

interface DownloadProgress {
  phase: "downloading" | "extracting" | "done";
  done: number;
  total: number | null;
}

const README_URL = "https://github.com/spelunky-fyi/overlunky#readme";

export function OverlunkyPage() {
  const toast = useToast();
  const [installed, setInstalled] = useState<boolean | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [launching, setLaunching] = useState<OverlunkyLaunchMode | null>(null);
  const [progress, setProgress] = useState<DownloadProgress | null>(null);

  useEffect(() => {
    const unlisten = listen<DownloadProgress>(
      "overlunky-download-progress",
      (event) => {
        setProgress(event.payload);
      },
    );
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const ok = await isOverlunkyInstalled();
      setInstalled(ok);
    } catch (err) {
      toast.error(`Couldn't check Overlunky status: ${extractMessage(err)}`);
      setInstalled(false);
    }
  }, [toast]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleDownload = async () => {
    setDownloading(true);
    setProgress(null);
    try {
      await downloadOverlunky();
      toast.success(installed ? "Overlunky updated." : "Overlunky downloaded.");
      await refresh();
    } catch (err) {
      toast.error(`Download failed: ${extractMessage(err)}`);
    } finally {
      setDownloading(false);
      setProgress(null);
    }
  };

  const handleLaunch = async (mode: OverlunkyLaunchMode) => {
    setLaunching(mode);
    try {
      await launchOverlunky(mode);
      toast.success("Overlunky launched.");
    } catch (err) {
      toast.error(`Launch failed: ${extractMessage(err)}`);
    } finally {
      setLaunching(null);
    }
  };

  const handleDocs = async () => {
    try {
      await openUrl(README_URL);
    } catch (err) {
      toast.error(`Couldn't open browser: ${extractMessage(err)}`);
    }
  };

  const busy = downloading || launching !== null;
  const canLaunch = installed === true && !busy;

  const installStatus: "checking" | "installed" | "missing" =
    installed === null ? "checking" : installed ? "installed" : "missing";
  const installStatusLabel =
    installStatus === "checking"
      ? "Checking install..."
      : installStatus === "installed"
        ? "WHIP build installed"
        : "Not installed";
  const installActionLabel = downloading
    ? "Downloading..."
    : installStatus === "installed"
      ? "Update"
      : "Install";

  return (
    <div className="ovl-page">
      <header className="ovl-header">
        <div className="ovl-header-copy">
          <h2 className="ovl-title">Overlunky</h2>
          <p className="ovl-subtitle">
An overlay for Spelunky 2 to help you with modding, exploring the depths of the game and practicing with tools like spawning arbitrary items, warping to levels and teleporting made by the cool people from the <a href="https://discord.gg/spelunky-community" target="_blank" rel="noopener noreferrer">Spelunky Community Discord</a>.</p>
        </div>
        <button
          type="button"
          className="btn btn-ghost ovl-docs-btn"
          onClick={() => void handleDocs()}
        >
          <BookOpen size={14} aria-hidden="true" />
          <span>Documentation</span>
        </button>
      </header>

      <div className="ovl-body">
        {/* --- Install strip ------------------------------------------ */}
        <section className={`ovl-install ovl-install-${installStatus}`}>
          <div className="ovl-install-glyph">
            <Package size={22} aria-hidden="true" />
          </div>
          <div className="ovl-install-copy">
            <div className="ovl-install-label">{installStatusLabel}</div>
            <div className="ovl-install-hint">
              {installStatus === "installed"
                ? "Pull the latest WHIP build from GitHub."
                : installStatus === "missing"
                  ? "Download the WHIP build from GitHub to enable inject and launch."
                  : "Scanning your install directory for an existing WHIP build."}
            </div>
          </div>
          <div className="ovl-install-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void handleDownload()}
              disabled={busy || installStatus === "checking"}
            >
              <Download size={14} aria-hidden="true" />
              <span>{installActionLabel}</span>
            </button>
            {installed && (
              <button
                type="button"
                className="ovl-inline-btn"
                onClick={() => void handleLaunch("update")}
                disabled={busy}
                title="Open Overlunky's built-in updater UI"
              >
                <Cog size={12} aria-hidden="true" />
                <span>
                  {launching === "update"
                    ? "Opening updater..."
                    : "Reconfigure auto-updater"}
                </span>
              </button>
            )}
          </div>
          {downloading && progress && (
            <DownloadProgressBar progress={progress} />
          )}
        </section>

        {/* --- Launch grid -------------------------------------------- */}
        <section className="ovl-launch-grid">
          <LaunchCard
            icon={<Zap size={26} aria-hidden="true" />}
            title="Inject into a running game"
            hint="Attach to Spel2.exe that's already running."
            buttonLabel={launching === "inject" ? "Launching..." : "Inject"}
            disabled={!canLaunch}
            onClick={() => void handleLaunch("inject")}
          />
          <LaunchCard
            icon={<Play size={26} aria-hidden="true" />}
            title="Launch vanilla with Overlunky"
            hint="Starts a fresh Spel2.exe with Overlunky already attached, no timing race."
            buttonLabel={
              launching === "launchGame" ? "Launching..." : "Launch"
            }
            disabled={!canLaunch}
            onClick={() => void handleLaunch("launchGame")}
          />
        </section>

        <p className="ovl-footnote">
          To launch Overlunky with Playlunky instead, toggle "Launch
          Overlunky alongside Playlunky" in the Playlunky Options modal.
        </p>
      </div>
    </div>
  );
}

interface LaunchCardProps {
  icon: React.ReactNode;
  title: string;
  hint: string;
  buttonLabel: string;
  disabled: boolean;
  onClick: () => void;
}

function LaunchCard({
  icon,
  title,
  hint,
  buttonLabel,
  disabled,
  onClick,
}: LaunchCardProps) {
  return (
    <div className="ovl-launch-card">
      <div className="ovl-launch-icon">{icon}</div>
      <div className="ovl-launch-title">{title}</div>
      <div className="ovl-launch-hint">{hint}</div>
      <button
        type="button"
        className="btn btn-primary ovl-launch-btn"
        onClick={onClick}
        disabled={disabled}
      >
        {buttonLabel}
      </button>
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

function DownloadProgressBar({ progress }: { progress: DownloadProgress }) {
  const label =
    progress.phase === "extracting"
      ? "Extracting..."
      : progress.phase === "done"
        ? "Done"
        : progress.total
          ? `${formatMiB(progress.done)} / ${formatMiB(progress.total)}`
          : `${formatMiB(progress.done)} downloaded`;
  const pct =
    progress.phase === "downloading" && progress.total && progress.total > 0
      ? Math.min(100, Math.round((progress.done / progress.total) * 100))
      : progress.phase === "done"
        ? 100
        : null;
  return (
    <div className="ovl-progress">
      <div className="ovl-progress-track" aria-hidden="true">
        <div
          className={`ovl-progress-fill${pct === null ? " ovl-progress-fill-indeterminate" : ""}`}
          style={pct === null ? undefined : { width: `${pct}%` }}
        />
      </div>
      <div className="ovl-progress-label">{label}</div>
    </div>
  );
}

function formatMiB(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
