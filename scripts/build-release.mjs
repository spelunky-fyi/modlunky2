#!/usr/bin/env node
// Build a release-ready modlunky2.exe.
//
// One command that runs the whole pipeline:
//  1. Ensure node_modules is present.
//  2. `npx tauri build --no-bundle` (drives Vite via tauri.conf.json's
//     beforeBuildCommand, embeds the frontend, produces the release
//     binary).
//  3. Copies the release binary to `release/modlunky2.exe`. The
//     Cargo binary is called `modlunky2-app.exe`; we rename on
//     copy so the shipped filename matches what GitHub releases
//     expect + what users install.
//
// The Tauri exe is now the whole distribution: it self-updates
// in-place via `updater.rs` (rename current -> .backup, download,
// spawn, exit). No wrapper launcher, no cache extraction.
//
// Env override (rare):
//   MODLUNKY2_SKIP_TAURI=1  reuse existing target/release/
//                           modlunky2-app.exe (useful when only
//                           icons/config changed)
//
// Usage:
//   node scripts/build-release.mjs
//   npm run release            (via package.json alias)

import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TAURI_DIR = join(REPO_ROOT, "app");
// This is a Cargo workspace, so builds emit under the workspace
// target dir at the repo root, not under each crate's own directory.
const WORKSPACE_RELEASE = join(REPO_ROOT, "target", "release");
const TAURI_EXE = join(WORKSPACE_RELEASE, "modlunky2-app.exe");
const RELEASE_DIR = join(REPO_ROOT, "release");
const FINAL_EXE = join(RELEASE_DIR, "modlunky2.exe");

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
  if (!existsSync(TAURI_EXE)) {
    die(`TAURI skip requested but no existing exe at ${TAURI_EXE}`);
  }
} else {
  step("[2/3] tauri app release build (npx tauri build --no-bundle)...", () => {
    run("npx", ["tauri", "build", "--no-bundle"], { cwd: TAURI_DIR });
  });
}
if (!existsSync(TAURI_EXE)) {
  die(`Tauri exe not found at ${TAURI_EXE} after build`);
}

// --- 3. Publish -------------------------------------------------------
// Rename on copy so the shipped filename is `modlunky2.exe`, matching
// the asset name in GitHub releases + the self-update download URL.
step("[3/3] publishing to release/...", () => {
  if (!existsSync(RELEASE_DIR)) {
    mkdirSync(RELEASE_DIR, { recursive: true });
  }
  copyFileSync(TAURI_EXE, FINAL_EXE);
});

const sizeMb = (statSync(FINAL_EXE).size / 1024 / 1024).toFixed(2);
log("");
log(c.green("== done =="));
log(c.green(`output: ${FINAL_EXE} (${sizeMb} MB)`));
