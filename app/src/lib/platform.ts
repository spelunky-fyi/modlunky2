// Which OS the app is running on.
//
// Modlunky2 ships on Windows and runs natively on Linux, and a few places in
// the UI have to differ: options that only mean something on one of them, and
// example paths that would be nonsense on the other.
//
// `platform()` from the OS plugin is synchronous, because the plugin injects
// the value when the webview starts rather than going over IPC. That matters:
// it can be read during the first render, so nothing has to flicker or hold a
// loading state to find out what OS it's on.
//
// Everything goes through this module rather than importing the plugin
// directly, the same way `commands.ts` owns the IPC surface, so the set of
// platform branches in the app stays greppable.

import { platform } from "@tauri-apps/plugin-os";

/** Read once: it can't change while the app is running. */
const current = platform();

export const isWindows = current === "windows";
export const isLinux = current === "linux";
export const isMacOS = current === "macos";

/** For display, e.g. in a hint explaining why an option is unavailable. */
export const platformName = isWindows
  ? "Windows"
  : isLinux
    ? "Linux"
    : isMacOS
      ? "macOS"
      : current;

/**
 * Example install directory for the platform, used as placeholder text. Both
 * are only defaults; the Browse button and Steam auto-detection are how the
 * path normally gets set.
 */
export const installDirPlaceholder = isWindows
  ? "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Spelunky 2"
  : "~/.local/share/Steam/steamapps/common/Spelunky 2";

/**
 * Whether desktop shortcuts are supported. Currently Windows-only: the backend
 * writes a `.lnk`, which is a Windows format. Linux would need a `.desktop`
 * file whose `Exec=` line goes through Proton, which doesn't exist yet.
 */
export const supportsDesktopShortcut = isWindows;
