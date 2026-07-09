// Shared runtime that every tracker OBS page uses. Handles the
// connection dance, window-config fetch, Empty / Failure / Reload
// dispatch. The per-tracker page just calls `startTracker` with its
// slug + a payload renderer.
//
// Loaded before the tracker-specific script (see each tracker.html),
// so `window.startTracker` is defined by the time that script runs.
"use strict";

window.startTracker = function ({ slug, onPayload }) {
  const el = document.getElementById("text");
  const wsUrl = `ws://${window.location.host}/ws/${slug}`;
  let backoff = 500; // ms, doubles on each failure up to 8s

  async function applyWindowConfig() {
    try {
      const res = await fetch("/api/window-config");
      if (!res.ok) return;
      const cfg = await res.json();
      // Drive styling through CSS custom properties (not inline styles on the
      // element) so an OBS Browser Source's Custom CSS targeting
      // `.tracker-content` can still override these values by cascade order.
      const root = document.documentElement.style;
      if (cfg.colorKey) {
        root.setProperty("--chroma-key", cfg.colorKey);
      }
      if (cfg.fontFamily) {
        root.setProperty(
          "--tracker-font-family",
          `"${cfg.fontFamily}", system-ui, -apple-system, sans-serif`,
        );
      }
      if (cfg.fontSize) {
        root.setProperty("--tracker-font-size", `${cfg.fontSize}px`);
      }
      if (cfg.fontColor) {
        root.setProperty("--tracker-font-color", cfg.fontColor);
      }
      root.setProperty("--tracker-stroke-width", `${cfg.strokeWidth || 0}px`);
      if (cfg.strokeColor) {
        root.setProperty("--tracker-stroke-color", cfg.strokeColor);
      }
    } catch (err) {
      // Config fetch failure isn't fatal; page keeps default styling.
    }
  }

  function render(payload) {
    if (!payload || payload.type === "Empty") {
      el.textContent = "Waiting for Spelunky 2";
      el.classList.add("disconnected");
      el.classList.remove("final-death");
      return;
    }
    if (payload.type === "Detached") {
      el.textContent = "Spelunky 2 exited";
      el.classList.add("disconnected");
      el.classList.remove("final-death");
      return;
    }
    if (payload.type === "Failure") {
      el.textContent = payload.data || "Error";
      el.classList.remove("disconnected", "final-death");
      return;
    }
    if (payload.type === "Reload") {
      // Server bumped layout_version. Re-fetch and reapply window
      // config without touching the current tracker text.
      void applyWindowConfig();
      return;
    }
    // Any other tag is a tracker-specific payload. Clear the shared
    // "disconnected" class; onPayload owns the tracker's own state
    // classes (final-death, etc).
    el.classList.remove("disconnected");
    onPayload(payload.data || {}, el);
  }

  function connect() {
    const ws = new WebSocket(wsUrl);

    ws.addEventListener("open", () => {
      backoff = 500;
      // Reapply window config on every reconnect: if the server
      // restarted (settings change), the new values land here.
      void applyWindowConfig();
    });

    ws.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        render(payload);
      } catch (err) {
        // Ignore non-JSON messages (heartbeat pings are binary).
      }
    });

    ws.addEventListener("close", () => {
      el.classList.add("disconnected");
      el.textContent = "Disconnected";
      window.setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 8000);
    });

    ws.addEventListener("error", () => {
      // Close handler will fire right after; do the reconnect there
      // so we don't schedule two retries.
    });
  }

  void applyWindowConfig();
  connect();
};
