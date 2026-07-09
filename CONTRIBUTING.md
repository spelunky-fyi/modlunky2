# Contributing to modlunky2

## Discussion

Most discussion happens in the [Spelunky Community Discord server](https://discord.gg/spelunky-community):

- `#s2-modding-help` - get help using or making mods
- `#s2-modding-tooldevs` - discuss development, bug fixes, or new features

Before starting substantial changes, please raise them in `#s2-modding-tooldevs`.

## Bugs

Before reporting, check
[existing issues](https://github.com/spelunky-fyi/modlunky2/issues) to see
whether yours has been reported.

## Repo layout

See [ARCHITECTURE.md](ARCHITECTURE.md) for how the pieces fit together.

- `app/`, the Tauri 2 app.
  - `app/src/`, React + TypeScript frontend (Vite).
  - `app/src-tauri/`, Rust backend that hosts the WebView, tauri commands,
    and window management.
  - `app/obs-source/`, static HTML/JS pages the backend serves as OBS
    Browser Sources for the trackers.
- `crates/`, shared Rust workspace crates the Tauri app depends on. Includes
  `ml2_mem` (game process reader), `ml2_trackers` (RunState + tracker logic),
  `ml2_levels` (level file format), `ml2_sprites` (atlas builder / merger),
  `ml2_mods`, and friends.
- `scripts/`, dev-only Node helpers: release build (`build-release.mjs`) +
  entity ID codegen (`dump-entity-types.mjs`).
- `CHANGELOG.md`, the user-facing change log (see [Changelog](#changelog)).

## Development setup

You need:

- [Rust](https://www.rust-lang.org/tools/install). The MSRV is pinned in the
  workspace `Cargo.toml` (`rust-version`, currently **1.94**), and CI runs on
  exactly that toolchain. `stable` is fine for day-to-day work; see
  [Checks](#checks) for reproducing CI's clippy results precisely.
- [Node.js](https://nodejs.org/) (any current LTS).

```console
cd app
npm install
```

### Run in dev mode

Runs the Vite dev server + Tauri app with hot-reload on both sides.

```console
cd app
npm run tauri dev
```

The Rust side rebuilds on `src-tauri/**` changes; the frontend hot-reloads on
`src/**` changes.

### Build a release exe (for local testing)

To build the shipped-style binary yourself, for example to test the optimized
release build, run the full pipeline (frontend build, Tauri release build, copy
into `release/`):

```console
node scripts/build-release.mjs
# or, from app/:
npm run release
```

Output lands at `release/modlunky2.exe`. This is only for local testing;
publishing a release is automated. (see [Releases](#releases)).

## Working in the codebase

### Adding a Tauri command

A backend command takes two edits to become callable from the frontend:

1. Write the `#[tauri::command]` in `app/src-tauri/src/`, and register it in the
   `tauri::generate_handler!` list in `app/src-tauri/src/lib.rs`.
2. Add a typed wrapper in `app/src/lib/commands.ts`. That file is the single
   source of truth for the IPC surface the React code calls.

Keep the argument and return types in sync on both sides. Values cross the wire
as camelCase, so Rust structs use `#[serde(rename_all = "camelCase")]`.

### Trackers (OBS pages)

The pages under `app/obs-source/` are embedded into the exe at compile time
(`include_dir!`), so editing them needs a Rust rebuild to take effect. They do
not hot-reload the way `app/src/` does.

## Checks

CI (`.github/workflows/rust-test.yml`) runs on the pinned MSRV toolchain and
fails on any of the following, so run them locally before pushing.

Rust, from the repo root:

```console
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --all-targets --locked
```

Frontend, from `app/`:

```console
npx tsc --noEmit
```

Notes:

- **Clippy is enforced** with `-D warnings`, so any warning fails CI.
  `cargo clippy --fix` applies most mechanical lints for you.
- Frontend type-checking is enforced through the release build (`npm run build`
  runs `tsc` before Vite), so a type error fails the build job. `npx tsc
--noEmit` is the fast local check. There is no ESLint.
- `--locked` requires `Cargo.lock` to be committed and current. If you
  intentionally changed dependencies, drop `--locked`, then commit the updated
  lockfile.
- CI pins to a single Rust version (currently 1.94) so lint results are
  deterministic across contributors. To reproduce CI's clippy exactly, install
  that toolchain and prefix commands with it:
  `rustup toolchain install 1.94`, then `cargo +1.94 clippy ...`.
- Doc-only changes (`**/*.md`) skip the Rust and build workflows.

## Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/). Add an
entry for every user-facing change under the top `## [Unreleased]` heading, in
the matching group:

- **Added** - new features.
- **Changed** - changes to existing behavior.
- **Fixed** - bug fixes.

Write for users, not implementers: say what changed and why it matters, not
which function moved. Internal-only work (refactors, tests, CI) doesn't need an
entry.

Cutting a release moves the `[Unreleased]` items into a new dated
`## [x.y.z] - YYYY-MM-DD` section (see [Releases](#releases)).

## Before opening a PR

PRs target `main`. Please make sure:

- [ ] `cargo fmt --all` has been run
- [ ] `cargo clippy --workspace --all-targets --locked -- -D warnings` is clean
- [ ] `cargo test --workspace --all-targets --locked` passes
- [ ] `npx tsc --noEmit` passes (from `app/`)
- [ ] `CHANGELOG.md` has an `[Unreleased]` entry for any user-facing change

## Releases

Publishing a release is mostly automated: a version bump
landing on `main` makes CI build the exe and open a _draft_ GitHub release, which
a maintainer then publishes. You do not build or upload the exe by hand (see
[Build a release exe](#build-a-release-exe-for-local-testing) for the local
testing build, which is a separate thing).

To cut a release:

1. Bump the version:

   ```console
   cd app
   npm run bump patch            # 2.0.0 -> 2.0.1
   npm run bump minor            # 2.0.0 -> 2.1.0
   npm run bump major            # 2.0.0 -> 3.0.0
   npm run bump 2.1.5            # explicit
   ```

   This updates `package.json`, `src-tauri/Cargo.toml`,
   `src-tauri/tauri.conf.json`, and both lockfiles.

2. In `CHANGELOG.md`, rename the top `## [Unreleased]` heading to
   `## [x.y.z] - YYYY-MM-DD` (matching the bumped version and today's date), and
   add a fresh empty `## [Unreleased]` above it. This dated section becomes the
   release notes in step 4, so make sure it reads well.

3. Commit both, and push to `main`.

4. `.github/workflows/build.yml` sees the version change, builds the release exe,
   and opens a **draft** GitHub release with the exe attached. The draft body is
   filled from this version's `CHANGELOG.md` section, followed by GitHub's
   auto-generated "What's Changed" PR list.

5. Review the draft on the repo's Releases page and publish it.
