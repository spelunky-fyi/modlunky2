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
//  4. Linux only: strips the host-managed graphics libraries that
//     linuxdeploy bundles into the AppImage, then repacks it. See
//     `stripHostManagedLibs` for why this is not optional.
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
  appendFileSync,
  chmodSync,
  closeSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  readSync,
  readdirSync,
  rmSync,
  statSync,
  unlinkSync,
  writeFileSync,
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

/** Runs a command and returns its stdout, dying if it fails. */
function capture(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, { encoding: "utf8", ...opts });
  if (res.status !== 0) {
    die(`${cmd} exited with status ${res.status}\n${res.stderr ?? ""}`);
  }
  return res.stdout;
}

function step(label, fn) {
  log("");
  log(c.cyan(label));
  fn();
}

// Libraries that must come from the host, never from the bundle.
//
// linuxdeploy drags these in via GTK's `im-wayland*` input-method modules,
// and its AppRun wrapper puts `$APPDIR/usr/lib` ahead of every system path
// in LD_LIBRARY_PATH. That makes our copy win over the host's -- which is
// backwards, because we do NOT bundle libEGL/libGL/libgbm/libdrm (correctly:
// they have to match the host's driver stack). So the host's Mesa loads, and
// then resolves libwayland against OUR build-machine copy.
//
// On any distro whose Mesa is meaningfully newer than the Ubuntu 22.04 we
// build on, that pairing fails EGL initialization outright:
//
//   Could not create default EGL display: EGL_BAD_PARAMETER. Aborting...
//
// and the app runs on with no window ever appearing. Steam Deck / SteamOS
// hits this reliably (issue #1376). Wayland's ABI is backward compatible, so
// letting the host's newer library serve our older bundled WebKit is both
// safe and the whole point -- the reverse is what breaks. These libraries are
// on the AppImage project's own excludelist for exactly this reason.
//
// The `im-wayland*` modules that pull them in are themselves dead weight:
// linuxdeploy's GTK hook forces GDK_BACKEND=x11, so a Wayland input method
// can never load.
const HOST_MANAGED_LIBS = [
  /^libwayland-client\.so\./,
  /^libwayland-cursor\.so\./,
  /^libwayland-egl\.so\./,
  /^libwayland-server\.so\./,
  /^im-wayland.*\.so$/,
];

/** Every file under `dir`, recursively, as absolute paths. */
function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

/**
 * Unpacks the AppImage, deletes the host-managed libraries, and repacks it
 * in place.
 *
 * Repacking is done with squashfs-tools rather than appimagetool so the
 * build doesn't depend on tooling Tauri fetched for its own use. An AppImage
 * is just [runtime ELF][squashfs], so preserving the original runtime byte
 * for byte and swapping the filesystem behind it keeps the result a valid
 * AppImage, self-update path and all. The new filesystem reuses the original's
 * compressor and block size so the artifact stays the size it was.
 */
function stripHostManagedLibs(appimage) {
  for (const tool of ["unsquashfs", "mksquashfs"]) {
    const found = spawnSync("command", ["-v", tool], {
      shell: true,
      stdio: "ignore",
    });
    if (found.status !== 0) {
      die(`${tool} not found; install squashfs-tools to build the AppImage`);
    }
  }

  const offset = capture(appimage, ["--appimage-offset"]).trim();
  const superblock = capture("unsquashfs", ["-s", "-o", offset, appimage]);
  const comp = /^Compression\s+(\S+)/m.exec(superblock)?.[1];
  const block = /^Block size\s+(\d+)/m.exec(superblock)?.[1];
  if (!comp || !block) {
    die(`couldn't read the squashfs superblock of ${appimage}`);
  }
  log(`  squashfs: offset=${offset} compression=${comp} block=${block}`);

  const work = join(dirname(appimage), "repack");
  const appdir = join(work, "AppDir");
  const runtime = join(work, "runtime.bin");
  const fs = join(work, "filesystem.squashfs");
  rmSync(work, { recursive: true, force: true });
  mkdirSync(work, { recursive: true });

  run("unsquashfs", ["-q", "-d", appdir, "-o", offset, appimage]);

  let removed = 0;
  for (const file of walk(appdir)) {
    const name = file.slice(file.lastIndexOf("/") + 1);
    if (!HOST_MANAGED_LIBS.some((re) => re.test(name))) continue;
    unlinkSync(file);
    log(`  stripped ${file.slice(appdir.length + 1)}`);
    removed += 1;
  }
  if (removed === 0) {
    // Not fatal on its own, but it means linuxdeploy changed what it bundles
    // and this step is now silently doing nothing. Say so loudly.
    log(c.yellow("  warning: no host-managed libs found; has linuxdeploy changed?"));
  }

  // Keep the original runtime: it carries the AppImage magic, the update
  // information, and the self-extraction logic. Only the filesystem changes.
  const fd = openSync(appimage, "r");
  const head = Buffer.alloc(Number(offset));
  readSync(fd, head, 0, head.length, 0);
  closeSync(fd);
  writeFileSync(runtime, head);

  // mksquashfs defaults to zstd level 15, which is weaker than what
  // appimagetool packed the original with: repacking at the default grows the
  // artifact by ~1.2% even though this step only ever deletes files. Level 19
  // lands within a rounding error of the original for ~12s of build time (22
  // buys a further 8 KB and isn't worth it). Guarded on the compressor, since
  // 19 is out of range for gzip's 1-9.
  const level = comp === "zstd" ? ["-Xcompression-level", "19"] : [];
  run("mksquashfs", [
    appdir,
    fs,
    "-root-owned",
    "-noappend",
    "-quiet",
    "-comp",
    comp,
    "-b",
    block,
    ...level,
  ]);

  copyFileSync(runtime, appimage);
  appendFileSync(appimage, readFileSync(fs));
  // copyFileSync carries the source file's mode across, and `runtime` was
  // written as a plain data file. Without this the artifact is a perfectly
  // valid AppImage that nobody can execute.
  chmodSync(appimage, 0o755);
  rmSync(work, { recursive: true, force: true });
}

// --- 1. Ensure node_modules -------------------------------------------
step("[1/4] ensuring node_modules is present...", () => {
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
  log(c.yellow("[2/4] tauri release build: skipped (MODLUNKY2_SKIP_TAURI)"));
  if (!findBuiltArtifact()) {
    die("TAURI skip requested but there's no existing build output to reuse");
  }
} else {
  step(`[2/4] tauri app release build (npx ${TAURI_ARGS.join(" ")})...`, () => {
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
step("[3/4] publishing to release/...", () => {
  if (!existsSync(RELEASE_DIR)) {
    mkdirSync(RELEASE_DIR, { recursive: true });
  }
  copyFileSync(built, FINAL_ARTIFACT);
});

// --- 4. Strip host-managed libs ---------------------------------------
// Deliberately operates on the published copy rather than Tauri's build
// output: that keeps the source artifact pristine, so re-running with
// MODLUNKY2_SKIP_TAURI strips a fresh copy instead of repacking one that
// was already stripped.
if (IS_WINDOWS) {
  log("");
  log(c.yellow("[4/4] AppImage lib strip: skipped (Windows ships a bare exe)"));
} else {
  step("[4/4] stripping host-managed libs from the AppImage...", () => {
    stripHostManagedLibs(FINAL_ARTIFACT);
  });
}

const sizeMb = (statSync(FINAL_ARTIFACT).size / 1024 / 1024).toFixed(2);
log("");
log(c.green("== done =="));
log(c.green(`output: ${FINAL_ARTIFACT} (${sizeMb} MB)`));
