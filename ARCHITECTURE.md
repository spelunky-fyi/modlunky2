# Architecture

modlunky2 is a desktop app for managing Spelunky 2 mods, editing
levels, extracting game assets, and running OBS trackers. It's a **Tauri 2** app:
a React/TypeScript frontend in a WebView talking to a Rust backend over Tauri's
IPC, with a workspace of shared Rust crates.

```
+-------------------------------------------------------------------+
|  Tauri process (one exe)                                          |
|                                                                   |
|   WebView (per window)               Rust backend                 |
|   +----------------------+           +------------------------+   |
|   | React + TypeScript   |  invoke   | tauri commands         |   |
|   | (app/src)            | --------> | (app/src-tauri/src)    |   |
|   |  - shells / tabs     | <-------- |  mods, level_editor,   |   |
|   |  - lib/commands.ts   |  events   |  characters, trackers, |   |
|   +----------------------+           |  extract, config, ...  |   |
|                                      +-----------+------------+   |
|                                                  |                |
|                                      +-----------v------------+   |
|                                      | workspace crates       |   |
|                                      | (crates/ml2_*)         |   |
|                                      +-----------+------------+   |
+--------------------------------------------------|----------------+
                                                   |
         +--------------------+------------------- + -----------+-----------------+
         v                    v                                 v                 v
   Spelunky 2 process    Filesystem                       spelunky.fyi      External tools
   (memory reads)        (Mods/, config.json,             (HTTP + WS)       (Playlunky,
                          extracted assets)                                  Overlunky)
```

## Windows

One Rust process drives several WebView windows. The main window and its
children all load the **same** frontend bundle; each one picks a "shell" at
first render from a `window.__*Context` object injected via the window's
`initialization_script` (see `readRoute()` in `app/src/App.tsx`). Tracker
windows are the exception: they load the localhost OBS page, not the app bundle.

```
main window -- spawns --> editor windows      (Vanilla / Custom .lvl editors)
            -- spawns --> character chooser window
            -- spawns --> logs window
            -- opens  --> tracker windows       (load http://127.0.0.1:<port>/<tracker>.html)
```

## Frontend (`app/src`)

- `App.tsx` - routes to the tabbed `AppShell` (the main window) or a dedicated
  window shell (editor / characters / logs).
- `components/` - one folder per feature: `mods`, `levels`, `trackers`,
  `characters`, `extract`, `overlunky`, `settings`, `shared`.
- `lib/commands.ts` - **the IPC boundary.** Every backend call is a typed
  wrapper around `invoke("...")` here; treat it as the single source of truth
  for what the backend exposes.
- Level rendering uses a PixiJS canvas (`components/levels/TileCanvas.tsx`).

## Backend (`app/src-tauri/src`)

- `lib.rs` - `run()` builds the Tauri app: sets up tracing, manages `AppState`,
  spawns the mods subsystem, and registers every command in one
  `tauri::generate_handler!` list. New commands must be added here.
- `state.rs` - `AppState`: mod-manager handles, the "updates available" set, the
  trackers subsystem, extract status, and the spelunky.fyi websocket slot.
- Command modules map to frontend features: `mods`, `level_editor`,
  `characters`, `trackers/`, `extract`, `playlunky`, `overlunky`, `config`,
  `fonts`, `updater`, `fyi_ws` (live install-from-web link), `log_buffer` /
  `toast_buffer` (in-memory capture surfaced to the UI / logs window).

## Shared crates (`crates/`)

Game/format logic lives here so it's testable without the app.

| Crate               | Purpose                                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `ml2_mem`           | Read structured game state from the running process (`#[offset]` structs).                                                      |
| `ml2_mem_derive`    | Proc-macros (`MemStruct`) powering the above.                                                                                   |
| `ml2_trackers`      | Game-state model + tracker logic (RunState) on top of `ml2_mem`; produces the data trackers display.                            |
| `ml2_types`         | Shared entity / game data types.                                                                                                |
| `ml2_levels`        | `.lvl` file parser + serializer (cp1252 plain-text format).                                                                     |
| `ml2_sprites`       | Sprite-sheet splitter/merger; builds per-entity atlases from unpacked textures. Data-driven loader/merger tables under `data/`. |
| `ml2_entity_data`   | Bundled `entities.json` / `textures.json` metadata consumed by `ml2_sprites`.                                                   |
| `ml2_assets`        | Extract game assets from `Spel2.exe` (zip / soundbank / fsb5).                                                                  |
| `ml2_chacha`        | ChaCha-derived cipher for decrypting Spelunky 2 assets.                                                                         |
| `ml2_vorbis_header` | Reconstruct OGG/Vorbis headers for extracted audio.                                                                             |
| `ml2_mods`          | Mod management: local disk (install / update / delete) + the spelunky.fyi remote API (ModManager + ModCache).                   |
| `ml2_net`           | Shared networking helpers (retry/backoff) for the fyi client.                                                                   |

## Key data flows

### Trackers

A single axum server binds `127.0.0.1:<port>` and serves the OBS pages
(`app/obs-source/`, embedded via `include_dir!`) plus a WebSocket per tracker.

```
Spel2 process --read--> tick task ----> watch<Payload> ----> axum server (127.0.0.1:port)
 (ml2_mem)            (ml2_trackers)                            |  /ws/<slug>
                                                                v
                          +-------------------------+-----------+-------------+
                          v                         v                         v
                   Tauri window              OBS Browser Source          text file
                   (tracker.html)            (same tracker.html)         (OBS Text source)
```

Memory reads only run while at least one WebSocket client is connected
(refcounted per tracker slug), so an idle server costs nothing. Styling flows
the other way via `/api/window-config`. Adding a tracker is ~one line in
`TrackersState::new`.

### Level editor

```
.lvl file --parse--> tilecodes --+
(ml2_levels)                     |   biome atlas (name -> sprite)
                                 +-> (ml2_sprites) --> PixiJS canvas (frontend)
                                                             |
                                          edits --serialize--+--> .lvl file (ml2_levels)
```

The Vanilla (base-game overrides) and Custom (pack) editors share the palette
and canvas; `level_editor.rs` bridges the crates and the frontend.

### Mods & launch

`ml2_mods` manages `Mods/Packs/` on disk and the spelunky.fyi API. The mods page
lists / toggles / updates packs; `load_order.txt` (first-wins) drives Playlunky.
`playlunky.rs` / `overlunky.rs` shell out to those external tools.

### Asset extraction

`ml2_assets` unpacks `Spel2.exe` (decrypting via `ml2_chacha`); `ml2_sprites`
then merges the textures into the per-entity sheets the level editor renders.

## Config & on-disk state

- `config.json` at `%LOCALAPPDATA%\spelunky.fyi\modlunky2\config.json`. Keys are
  kebab-case on disk, camelCase over the IPC wire.
- Modlunky-local per-pack state under `Mods/.ml/pack-metadata/<id>/`.
- Extracted assets live under the configured install dir.

## Where to start reading

- Backend entry + command list: `app/src-tauri/src/lib.rs`.
- Frontend entry + window routing: `app/src/App.tsx`.
- The IPC surface: `app/src/lib/commands.ts`.
- Build, checks, and release flow: [`CONTRIBUTING.md`](CONTRIBUTING.md).
