import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import { Copy, Eraser, Search } from "lucide-react";
import {
  clearLogs,
  getRecentLogs,
  getRecentToasts,
  type LogEntry,
  type LogLevel,
  type ToastRecord,
} from "../../lib/commands";
import { useToast } from "./Toast";
import "./LogsWindow.css";

type Tab = "console" | "toasts";

const LEVEL_FILTERS: {
  label: string;
  match: (level: LogLevel) => boolean;
  value: string;
}[] = [
  { label: "All", match: () => true, value: "all" },
  {
    label: "Debug+",
    match: (l) => l !== "trace",
    value: "debug",
  },
  {
    label: "Info+",
    match: (l) => l === "info" || l === "warn" || l === "error",
    value: "info",
  },
  {
    label: "Warn+",
    match: (l) => l === "warn" || l === "error",
    value: "warn",
  },
  {
    label: "Error",
    match: (l) => l === "error",
    value: "error",
  },
];

/// Standalone window shell for logs. Opened from the main window via
/// `open_logs_window`; App.tsx routes to it when
/// `window.__logsContext.kind === "logs"`. Runs a full-page layout, no
/// Modal wrapper. Console tab tails the Rust ring buffer live; toast
/// tab polls the Rust-side ring buffer that ToastProvider populates.
export function LogsWindow() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("console");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [levelFilter, setLevelFilter] = useState("info");
  const [search, setSearch] = useState("");
  const [toasts, setToasts] = useState<ToastRecord[]>([]);

  // Initial snapshots.
  useEffect(() => {
    void getRecentLogs()
      .then(setLogs)
      .catch(() => setLogs([]));
    void getRecentToasts()
      .then(setToasts)
      .catch(() => setToasts([]));
  }, []);

  // Live-tail logs. Dedupe by seq: the initial snapshot can race the
  // live stream and land the same entry through both paths.
  useEffect(() => {
    const unlisten = listen<LogEntry>("log-line", (event) => {
      setLogs((current) => {
        if (
          current.length &&
          current[current.length - 1].seq >= event.payload.seq
        ) {
          return current;
        }
        return [...current, event.payload];
      });
    });
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, []);

  // Poll toast history while the toast tab is visible. Toasts don't
  // fire a dedicated event (they'd be low-volume anyway) so a 1s
  // poll is cheap enough to just do.
  useEffect(() => {
    if (tab !== "toasts") return;
    const t = window.setInterval(() => {
      void getRecentToasts()
        .then(setToasts)
        .catch(() => {});
    }, 1000);
    return () => window.clearInterval(t);
  }, [tab]);

  const filter = useMemo(
    () =>
      LEVEL_FILTERS.find((f) => f.value === levelFilter) ?? LEVEL_FILTERS[0],
    [levelFilter],
  );
  const query = search.trim().toLowerCase();
  const filteredLogs = useMemo(() => {
    return logs.filter((row) => {
      if (!filter.match(row.level)) return false;
      if (!query) return true;
      return (
        row.message.toLowerCase().includes(query) ||
        row.target.toLowerCase().includes(query)
      );
    });
  }, [logs, filter, query]);
  const filteredToasts = useMemo(() => {
    if (!query) return toasts;
    return toasts.filter((t) => t.message.toLowerCase().includes(query));
  }, [toasts, query]);

  const handleClear = useCallback(async () => {
    if (tab === "console") {
      try {
        await clearLogs();
        setLogs([]);
      } catch (err) {
        toast.error(`Couldn't clear logs: ${extractMessage(err)}`);
      }
    } else {
      // Toast tab: clear the local view only; the Rust ring buffer
      // still carries history for other windows.
      setToasts([]);
    }
  }, [tab, toast]);

  const handleCopy = useCallback(async () => {
    const text =
      tab === "console"
        ? filteredLogs.map(formatLogLine).join("\n")
        : filteredToasts.map(formatToastLine).join("\n");
    if (!text) return;
    try {
      await writeText(text);
      toast.success(
        `Copied ${tab === "console" ? filteredLogs.length : filteredToasts.length} lines.`,
      );
    } catch (err) {
      toast.error(`Copy failed: ${extractMessage(err)}`);
    }
  }, [tab, filteredLogs, filteredToasts, toast]);

  return (
    <div className="logs-window">
      <header className="logs-header">
        <div className="logs-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "console"}
            className={`logs-tab${tab === "console" ? " active" : ""}`}
            onClick={() => setTab("console")}
          >
            <span>Console</span>
            <span className="logs-tab-count">{logs.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "toasts"}
            className={`logs-tab${tab === "toasts" ? " active" : ""}`}
            onClick={() => setTab("toasts")}
          >
            <span>Toasts</span>
            <span className="logs-tab-count">{toasts.length}</span>
          </button>
        </div>
        <div className="logs-toolbar">
          <div className="logs-search">
            <Search size={13} aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter…"
              spellCheck={false}
              aria-label="Filter log lines"
            />
          </div>
          {tab === "console" && (
            <select
              className="logs-level"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              aria-label="Minimum level"
            >
              {LEVEL_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            className="btn btn-ghost logs-toolbar-btn"
            onClick={() => void handleCopy()}
            title="Copy visible rows to clipboard"
          >
            <Copy size={13} aria-hidden="true" />
            Copy
          </button>
          <button
            type="button"
            className="btn btn-ghost logs-toolbar-btn"
            onClick={() => void handleClear()}
            title={
              tab === "console"
                ? "Clear the ring buffer"
                : "Clear this window's view"
            }
          >
            <Eraser size={13} aria-hidden="true" />
            Clear
          </button>
        </div>
      </header>

      {tab === "console" ? (
        <ConsoleList entries={filteredLogs} />
      ) : (
        <ToastList entries={filteredToasts} />
      )}
    </div>
  );
}

function ConsoleList({ entries }: { entries: LogEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  const onScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 16;
    stickToBottomRef.current = atBottom;
  }, []);

  useEffect(() => {
    if (!stickToBottomRef.current || !scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [entries]);

  if (entries.length === 0) {
    return <div className="logs-empty">No matching log lines.</div>;
  }
  return (
    <div className="logs-list" ref={scrollRef} onScroll={onScroll}>
      {entries.map((row) => (
        <div key={row.seq} className={`logs-row logs-level-${row.level}`}>
          <span className="logs-time">{formatTime(row.tsMs)}</span>
          <span className={`logs-badge logs-badge-${row.level}`}>
            {row.level.toUpperCase()}
          </span>
          <span className="logs-target" title={row.target}>
            {shortTarget(row.target)}
          </span>
          <span className="logs-message">{row.message}</span>
        </div>
      ))}
    </div>
  );
}

function ToastList({ entries }: { entries: ToastRecord[] }) {
  if (entries.length === 0) {
    return <div className="logs-empty">No toasts this session.</div>;
  }
  return (
    <div className="logs-list">
      {entries
        .slice()
        .reverse()
        .map((row) => (
          <div key={row.id} className={`logs-row logs-variant-${row.variant}`}>
            <span className="logs-time">{formatTime(row.tsMs)}</span>
            <span className={`logs-badge logs-variant-${row.variant}`}>
              {row.variant.toUpperCase()}
            </span>
            <span className="logs-message">{row.message}</span>
          </div>
        ))}
    </div>
  );
}

function formatTime(ms: number): string {
  const d = new Date(ms);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  const mmm = String(d.getMilliseconds()).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${mmm}`;
}

function shortTarget(target: string): string {
  const parts = target.split("::");
  if (parts.length <= 2) return target;
  return `${parts[0]}::…::${parts[parts.length - 1]}`;
}

function formatLogLine(row: LogEntry): string {
  return `${formatTime(row.tsMs)} ${row.level.toUpperCase().padEnd(5)} ${row.target}: ${row.message}`;
}

function formatToastLine(row: ToastRecord): string {
  return `${formatTime(row.tsMs)} ${row.variant.toUpperCase().padEnd(7)} ${row.message}`;
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
