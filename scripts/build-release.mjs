#!/usr/bin/env node
// Build the release artifact for whichever platform this is running on.
//
// One command that runs the whole pipeline:
//  1. Ensure node_modules is present.
//  2. `npx tauri build` (drives Vite via tauri.conf.json's
//     beforeBuildCommand, embeds the frontend, produces the release
//     binary). Windows skips bundling and ships the bare exe; Linux
//     bundles an AppImage, because the Linux binary links ~200 MB of
//     system libraries (WebKitGTK above all) and a bare binary would
//     fail on any machine missing them.
//  3. Copies the result into `release/` under a stable, unversioned
//     name. Cargo emits `modlunky2-app[.exe]` and Tauri emits a
//     version-stamped `Modlunky2_<version>_amd64.AppImage`; both get
//     renamed on copy, because the updater looks the asset up by a
//     fixed name and every release has to answer to the same one.
//
// The artifact is the whole distribution: it self-updates in-place via
// `updater.rs` (rename current -> .backup, download, spawn, exit). No
// wrapper launcher, no cache extraction.
//
// Env override (rare):
//   MODLUNKY2_SKIP_TAURI=1  reuse the existing build output (useful
//                           when only icons/config changed)
//
// Usage:
//   node scripts/build-release.mjs
//   npm run release            (via package.json alias)

import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  statSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TAURI_DIR = join(REPO_ROOT, "app");
// This is a Cargo workspace, so builds emit under the workspace
// target dir at the repo root, not under each crate's own directory.
const WORKSPACE_RELEASE = join(REPO_ROOT, "target", "release");
const RELEASE_DIR = join(REPO_ROOT, "release");

const IS_WINDOWS = process.platform === "win32";
const IS_LINUX = process.platform === "linux";

if (!IS_WINDOWS && !IS_LINUX) {
  process.stderr.write(
    `error: no release build defined for ${process.platform}\n`,
  );
  process.exit(1);
}

// Windows ships the bare exe, so bundling is skipped entirely. Linux needs the
// AppImage, which is the only format that keeps the "one file, drop it
// anywhere, self-updates" shape once WebKitGTK has to come along.
const TAURI_ARGS = IS_WINDOWS
  ? ["tauri", "build", "--no-bundle"]
  : ["tauri", "build", "--bundles", "appimage"];

// Where Tauri leaves its output, and what we rename it to. The AppImage name
// carries the version, so it's found by extension rather than spelled out;
// that also means a Tauri naming change doesn't silently break the copy.
const APPIMAGE_DIR = join(WORKSPACE_RELEASE, "bundle", "appimage");
const FINAL_NAME = IS_WINDOWS ? "modlunky2.exe" : "modlunky2-x86_64.AppImage";
const FINAL_ARTIFACT = join(RELEASE_DIR, FINAL_NAME);

/** The freshly built artifact, or null when it isn't where we expect. */
function findBuiltArtifact() {
  if (IS_WINDOWS) {
    const exe = join(WORKSPACE_RELEASE, "modlunky2-app.exe");
    return existsSync(exe) ? exe : null;
  }
  if (!existsSync(APPIMAGE_DIR)) return null;
  const hit = readdirSync(APPIMAGE_DIR).find((f) => f.endsWith(".AppImage"));
  return hit ? join(APPIMAGE_DIR, hit) : null;
}

const c = {
  cyan: (s) => `\x1b[36m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
};

function log(msg) {
  process.stdout.write(msg + "\n");
}

function die(msg) {
  process.stderr.write(c.red("error: ") + msg + "\n");
  process.exit(1);
}

function run(cmd, args, opts = {}) {
  log(c.dim(`  $ ${cmd} ${args.join(" ")}`));
  const res = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: true,
    ...opts,
  });
  if (res.status !== 0) {
    die(`${cmd} exited with status ${res.status}`);
  }
}

function step(label, fn) {
  log("");
  log(c.cyan(label));
  fn();
}

// --- 1. Ensure node_modules -------------------------------------------
step("[1/3] ensuring node_modules is present...", () => {
  if (!existsSync(join(TAURI_DIR, "node_modules"))) {
    log("  node_modules missing; running npm install");
    run("npm", ["install"], { cwd: TAURI_DIR });
  } else {
    log("  node_modules present, skipping install");
  }
});

// --- 2. Tauri app -----------------------------------------------------
// `npx tauri build --no-bundle` runs the Vite frontend build (via the
// beforeBuildCommand in tauri.conf.json), embeds `frontendDist` into
// the exe, and produces a release binary. Raw `cargo build --release`
// skips the CLI-side asset registration step that maps
// `http://tauri.localhost/*` to the embedded bundle, which manifests
// as "localhost refused to connect" in the WebView. Skipping the
// bundle target keeps us from generating an NSIS/MSI we don't ship.
if (process.env.MODLUNKY2_SKIP_TAURI) {
  log(c.yellow("[2/3] tauri release build: skipped (MODLUNKY2_SKIP_TAURI)"));
  if (!findBuiltArtifact()) {
    die("TAURI skip requested but there's no existing build output to reuse");
  }
} else {
  step(`[2/3] tauri app release build (npx ${TAURI_ARGS.join(" ")})...`, () => {
    run("npx", TAURI_ARGS, { cwd: TAURI_DIR });
  });
}
const built = findBuiltArtifact();
if (!built) {
  die(
    IS_WINDOWS
      ? `Tauri exe not found under ${WORKSPACE_RELEASE} after build`
      : `No .AppImage found under ${APPIMAGE_DIR} after build`,
  );
}

// --- 3. Publish -------------------------------------------------------
// Rename on copy so the shipped filename is stable across releases,
// matching the asset name in GitHub releases + the name `updater.rs`
// looks for. Tauri's own AppImage filename carries the version, which
// would break that lookup on every release.
step("[3/3] publishing to release/...", () => {
  if (!existsSync(RELEASE_DIR)) {
    mkdirSync(RELEASE_DIR, { recursive: true });
  }
  copyFileSync(built, FINAL_ARTIFACT);
});

const sizeMb = (statSync(FINAL_ARTIFACT).size / 1024 / 1024).toFixed(2);
log("");
log(c.green("== done =="));
log(c.green(`output: ${FINAL_ARTIFACT} (${sizeMb} MB)`));
