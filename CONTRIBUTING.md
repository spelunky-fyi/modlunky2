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

## Development setup

You need [Rust](https://www.rust-lang.org/tools/install) (stable, MSRV listed in
the workspace `Cargo.toml`) and [Node.js](https://nodejs.org/) (any current LTS).

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

### Build a release exe

One command runs the whole pipeline (frontend build, Tauri release build, copy
into `release/`):

```console
node scripts/build-release.mjs
# or, from app/:
npm run release
```

Output lands at `release/modlunky2.exe` (~17 MB). Env override:

- `MODLUNKY2_SKIP_TAURI=1`, reuse the existing Tauri release exe and re-run
  just the copy step. Only useful when iterating on the release script
  itself.

### Bump the version

```console
cd app
npm run bump patch            # 2.0.0 -> 2.0.1
npm run bump minor            # 2.0.0 -> 2.1.0
npm run bump major            # 2.0.0 -> 3.0.0
npm run bump 2.1.5            # explicit
```

Touches `package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, and
both lockfiles. A bump landed on `main` triggers a draft GitHub release with the
built exe attached, ready for you to publish.

## Style

- Rust: `cargo fmt --all` is enforced in CI.
- TypeScript: `tsc --noEmit` should pass; there's no separate linter.
